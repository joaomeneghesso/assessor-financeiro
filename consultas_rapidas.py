"""Consultas comuns sem rede; apenas intenção, nunca cálculo ou gravação.

``interpretar_consulta`` devolve a intenção (tipo de pergunta, categoria e
período). Os períodos próprios desta camada (``PERIODOS_PROPRIOS``) são
convertidos em meses por ``resolver_meses``, que recebe o "hoje" de quem chama.

Períodos reconhecidos:
- este mês (padrão), mês passado, este ano;
- "últimos N meses": o mês atual (até hoje) e os N-1 anteriores;
- um mês: "em julho", "julho de 2025", "2026-07";
- intervalo: "de julho a novembro", "entre julho e novembro", "julho até
  novembro", com ano opcional em cada ponta ("de julho de 2025 a março de 2026");
- um ano: "em 2025", "ano passado".
Mês sem ano é do ano corrente; num intervalo sem ano em que o mês inicial vem
depois do final ("de novembro a fevereiro"), o início fica no ano anterior.
"""
import re
import unicodedata

MESES = {
    'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'abril': 4, 'maio': 5, 'junho': 6,
    'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12,
}
_NUMEROS = {
    'um': 1, 'dois': 2, 'tres': 3, 'quatro': 4, 'cinco': 5, 'seis': 6, 'sete': 7,
    'oito': 8, 'nove': 9, 'dez': 10, 'onze': 11, 'doze': 12,
}
PERIODOS_PROPRIOS = {'ultimos_meses', 'proximos_meses', 'mes', 'intervalo', 'ano', 'ano_passado'}
LIMITE_MESES = 60

_MES = '(?:' + '|'.join(MESES) + ')'
_TOKEN = rf'(?:{_MES}(?: de 20\d{{2}})?|20\d{{2}}-(?:0[1-9]|1[0-2]))'
_N = r'(?:\d{1,2}|' + '|'.join(_NUMEROS) + ')'


def _normalizar(texto):
    text = ''.join(c for c in unicodedata.normalize('NFD', texto.lower()) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', text).strip(' .?!')


def _ler_token(token):
    """'julho' -> (7, None); 'julho de 2025' -> (7, 2025); '2026-07' -> (7, 2026)."""
    m = re.fullmatch(r'(20\d{2})-(\d{2})', token)
    if m:
        return int(m[2]), int(m[1])
    m = re.fullmatch(rf'({_MES})(?: de (20\d{{2}}))?', token)
    return MESES[m[1]], (int(m[2]) if m[2] else None)


def _extrair_periodo(text):
    """Acha UMA expressão de período, remove-a do texto e devolve (texto, período).

    Período ``None`` com texto ``None`` = expressão que esta camada não representa.
    """
    regras = [
        (rf'\b(?:(?:n?os|n?as|durante os|durante as) )?ultim[oa]s ({_N}) meses\b', 'ultimos_meses'),
        (rf'\b(?:(?:n?os|n?as|durante os|durante as|para os|pelos) )?proxim[oa]s ({_N}) meses\b', 'proximos_meses'),
        (rf'\b(?:(?:no periodo|no intervalo) )?entre ({_TOKEN}) e ({_TOKEN})\b', 'intervalo'),
        (rf'\b(?:(?:no periodo |no intervalo )?(?:de|desde|do mes de) )?({_TOKEN}) (?:a|ate|ao mes de) ({_TOKEN})\b', 'intervalo'),
        (r'\b(?:(?:no|do) )?mes passado\b', 'previous_month'),
        (r'\b(?:(?:no|do) )?(?:este|esse|neste|nesse) mes\b|\b(?:(?:no|do) )?mes atual\b', 'current_month'),
        (r'\b(?:(?:no|do) )?ano passado\b', 'ano_passado'),
        (r'\b(?:(?:no|do|em) )?(?:este|esse|neste|nesse) ano\b|\b(?:(?:no|do) )?ano atual\b', 'current_year'),
        (rf'\b(?:(?:no mes de|no mes|em|de|no|do) )?({_TOKEN})\b', 'mes'),
        (r'\b(?:(?:no ano de|no ano|em|de|do ano de) )?(20\d{2})\b(?!-)', 'ano'),
    ]
    for padrao, tipo in regras:
        m = re.search(padrao, text)
        if not m:
            continue
        resto = re.sub(r'\s+', ' ', text[:m.start()] + ' ' + text[m.end():]).strip(' .?!,')
        periodo = {'period': tipo}
        if tipo in ('ultimos_meses', 'proximos_meses'):
            n = int(m[1]) if m[1].isdigit() else _NUMEROS[m[1]]
            if not 1 <= n <= LIMITE_MESES:
                return None, None
            periodo['n'] = n
        elif tipo == 'intervalo':
            (im, ia), (fm, fa) = _ler_token(m[1]), _ler_token(m[2])
            periodo.update(inicio_mes=im, inicio_ano=ia, fim_mes=fm, fim_ano=fa)
        elif tipo == 'mes':
            mes, ano = _ler_token(m[1])
            periodo.update(mes=mes, ano=ano)
        elif tipo == 'ano':
            periodo['ano'] = int(m[1])
        return resto, periodo
    return text, {'period': 'current_month'}


def _sobrou_periodo(text):
    """Segunda referência de tempo no texto: ambígua, fica para a IA/fallback."""
    return bool(re.search(rf'\b(?:{_MES}|20\d{{2}}|\d{{4}}-\d{{2}}|ultim\w*|entre|mes passado|ano passado)\b'
                          r'|\b(?:este|esse|neste|nesse) (?:mes|ano)\b|\b(?:mes|ano) atual\b', text))


_PAGAR = re.compile(r'(?:quanto (?:eu )?(?:vou |tenho (?:que |de )?|preciso )?pagar|o que (?:eu )?(?:vou|tenho (?:que|de)) pagar'
                    r'|(?:contas )?a pagar) (?:de|do|da|dos|das|com|em|no|na|nos|nas) (?:o |a |os |as )?(.{2,60})')


def interpretar_pagar(texto):
    """'quanto vou pagar de moradia em dezembro' -> previsão a pagar por categoria (ou faturas).

    Vem antes da recusa de 'cartao/credito' de ``interpretar_consulta``: aqui
    "cartão", "crédito" e "faturas" significam a soma das faturas dos cartões.
    Mês sem ano é a PRÓXIMA ocorrência (é sobre o que ainda vai ser pago).
    """
    if not isinstance(texto, str) or len(texto) > 300:
        return None
    text = _normalizar(texto)
    if not re.match(r'(?:quanto|o que|contas a pagar|a pagar)\b', text) or not re.search(r'\bpagar\b', text):
        return None
    if re.search(r'\b(hoje|ontem|semana|semanas|dia|dias)\b', text):
        return None
    text, periodo = _extrair_periodo(text)
    if periodo is None or _sobrou_periodo(text):
        return None
    text = re.sub(r'\s+(?:no|nos|na|nas|em|de|do|da|durante)$', '', text).strip()
    m = _PAGAR.fullmatch(text)
    if not m:
        return None
    categoria = m[1].strip()
    if re.search(r'\b(?:e|ou)\b|\d', categoria):
        return None
    return dict(periodo, futuro=True, intent='pay', query_type='payables_category', category=categoria)


def interpretar_consulta(texto):
    if not isinstance(texto, str) or len(texto) > 500:
        return None
    pagar = interpretar_pagar(texto)
    if pagar is not None:
        return pagar
    text = _normalizar(texto)
    # Não simplificar filtros que esta camada ainda não sabe representar.
    if re.search(r'\b(hoje|ontem|semana|semanas|dia|dias|cartao|credito|debito|pix)\b', text):
        return None
    for mes in re.findall(r'\b\d{4}-\d{2}\b', text):
        if not re.fullmatch(r'20\d{2}-(?:0[1-9]|1[0-2])', mes):
            return None
    text, periodo = _extrair_periodo(text)
    if periodo is None or _sobrou_periodo(text):
        return None
    # Conectivos que sobram no fim depois de tirar o período ("viagem nos", "mercado no periodo").
    while True:
        novo = re.sub(r'\s+(?:no|nos|na|nas|em|de|do|da|durante|periodo|no periodo)$', '', text)
        if novo == text:
            break
        text = novo
    base = dict(periodo, intent='analytics', category='')
    if re.fullmatch(r'(?:quanto (?:eu )?(?:gastei|gasto)|total de (?:gastos|despesas)|minhas despesas)', text):
        return dict(base, query_type='expense_total')
    if re.fullmatch(r'(?:quanto (?:eu )?recebi|total de (?:receitas|entradas)|minhas receitas)', text):
        return dict(base, query_type='income_total')
    category = re.fullmatch(r'(?:quanto (?:eu )?(?:gastei|gasto)|gastos|despesas) (?:com|em|de) (.{1,80})', text)
    if category and not re.search(r'\b(?:e|ou|conta|banco|por)\b|\d', category[1]):
        return dict(base, query_type='category_expense', category=category[1])
    if re.fullmatch(r'(?:quero (?:enxergar|entender|saber) )?(?:para )?onde (?:meu |o )?(?:dinheiro|grana) (?:(?:esta|estao) )?(?:indo|vai)', text) or re.fullmatch(r'(?:onde (?:eu )?gastei mais|maiores gastos|o que (?:esta )?pesando(?: mais)?|o que esta pesando no mes)', text):
        return dict(base, query_type='largest_expenses')
    return None


def _somar_meses(ano, mes, n):
    total = ano * 12 + (mes - 1) + n
    return total // 12, total % 12 + 1


def _lista(inicio, fim):
    (ia, im), (fa, fm) = inicio, fim
    if (ia, im) > (fa, fm):
        return None
    meses = []
    while (ia, im) <= (fa, fm):
        meses.append(f'{ia:04d}-{im:02d}')
        ia, im = _somar_meses(ia, im, 1)
    return meses if len(meses) <= LIMITE_MESES else None


PERIODO_INVALIDO = ('<b>Período inválido</b>\n\nO mês inicial precisa vir antes do final, num intervalo de até 60 meses. '
                    'Exemplos: <i>quanto gastei com mercado de julho a novembro</i>, '
                    '<i>quanto gastei de viagem nos últimos 3 meses</i>.')


def rotulo_periodo(meses, hoje, rotulo_mes):
    """'Julho 2026' ou 'Julho 2026 a Novembro 2026 (até 13/11/2026)' quando o intervalo inclui o mês atual."""
    if len(meses) == 1:
        return rotulo_mes(meses[0])
    texto = f'{rotulo_mes(meses[0])} a {rotulo_mes(meses[-1])}'
    atual = hoje.strftime('%Y-%m')
    return texto + (f' (até {hoje:%d/%m/%Y})' if meses[0] <= atual <= meses[-1] else '')


def linhas_por_mes(meses, itens, hoje, rotulo_mes, dinheiro):
    """Intervalo: total de cada mês já começado (itens marcados com '_mes'); um mês só: nada."""
    if len(meses) < 2:
        return []
    soma = {}
    for item in itens:
        soma[item['_mes']] = soma.get(item['_mes'], 0.0) + float(item.get('valor') or 0)
    atual = hoje.strftime('%Y-%m')
    return ['', '<b>Por mês</b>'] + [f'{rotulo_mes(m)} · {dinheiro(soma.get(m, 0))}' for m in meses if m <= atual]


def resolver_meses(parsed, hoje):
    """Meses AAAA-MM de um período próprio desta camada; ``None`` se o período for inválido."""
    tipo = parsed.get('period')
    atual = (hoje.year, hoje.month)
    if tipo == 'ultimos_meses':
        return _lista(_somar_meses(hoje.year, hoje.month, -(int(parsed['n']) - 1)), atual)
    if tipo == 'proximos_meses':
        return _lista(atual, _somar_meses(hoje.year, hoje.month, int(parsed['n']) - 1))
    if tipo == 'mes':
        ano = parsed.get('ano') or hoje.year
        if parsed.get('futuro') and not parsed.get('ano') and int(parsed['mes']) < hoje.month:
            ano += 1  # "quanto vou pagar em janeiro", em novembro: janeiro do ano que vem
        return [f'{ano:04d}-{int(parsed["mes"]):02d}']
    if tipo in {'ano', 'ano_passado'}:
        ano = hoje.year - 1 if tipo == 'ano_passado' else int(parsed['ano'])
        return _lista((ano, 1), atual if ano == hoje.year else (ano, 12))
    if tipo == 'intervalo':
        im, ia, fm, fa = int(parsed['inicio_mes']), parsed.get('inicio_ano'), int(parsed['fim_mes']), parsed.get('fim_ano')
        if ia is None and fa is None:
            fa = hoje.year
        if fa is None:
            fa = ia if fm >= im else ia + 1
        if ia is None:
            ia = fa if im <= fm else fa - 1
        return _lista((ia, im), (fa, fm))
    return None
