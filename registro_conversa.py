"""Extrai apenas os dados informados em um registro, sem banco, rede ou IA.

Ausência de descrição, conta ou forma é ausência: não se inventa um valor para
completar o formulário. A interface decide o que perguntar e quando confirmar.
O parser legado continua disponível para os demais comandos do assessor.
"""
from datetime import date, timedelta
from decimal import DecimalException
import re
import unicodedata

from money import parse_money
from parser_financeiro import (
    PADRAO_EXPRESSAO_DATA, PERIODO_DO_DIA, EXPRESSAO_DATA_VAGA,
    detectar_categoria, interpretar_expressao_data, mensagem_varios_lancamentos,
    numero_e_de_produto, parece_codigo_ou_texto_longo, texto_com_varios_lancamentos,
    texto_numero_para_float,
)
from categorias import canonicalizar_categoria


def normalizar(text):
    return ''.join(c for c in unicodedata.normalize('NFD', str(text).lower())
                   if unicodedata.category(c) != 'Mn')


CONTAS = {
    'mercado pago': 'Mercado Pago', 'mp': 'Mercado Pago',
    'nubank': 'Nubank', 'nu bank': 'Nubank', 'itau': 'Itaú',
    'btg': 'BTG', 'inter': 'Inter', 'bradesco': 'Bradesco',
    'santander': 'Santander', 'caixa': 'Caixa', 'banco do brasil': 'Banco do Brasil',
    'bb': 'Banco do Brasil', 'picpay': 'PicPay', 'c6': 'C6', 'c6 bank': 'C6',
    'neon': 'Neon', 'will': 'Will', 'xp': 'XP', 'caju': 'Caju',
    'vr caju': 'Caju', 'nu': 'Nubank', 'it': 'Itaú', 'will bank': 'Will',
    'willbank': 'Will', 'c6bank': 'C6', 'mercadopago': 'Mercado Pago', 'infinitepay': 'InfinitePay', 'infinite pay': 'InfinitePay',
}
FORMAS = {
    'pix': 'pix', 'debito': 'débito', 'credito': 'crédito',
    'cartao': 'crédito', 'cartao de credito': 'crédito',
    'cartao de debito': 'débito', 'dinheiro': 'dinheiro',
    'transferencia': 'transferência', 'boleto': 'boleto',
}
MULTIPLICADORES = {'mil': 1000, 'milhao': 1000000, 'milhoes': 1000000}
VALOR = r'[+-]?\d[\d.,]*(?!\w)'
DATA = r'\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b'
RELATIVAS = r'\b(?:depois de amanha|anteontem|ontem|hoje|amanha)' + PERIODO_DO_DIA + r'\b'
DATAS_NO_TEXTO = '|'.join((PADRAO_EXPRESSAO_DATA, DATA, RELATIVAS))
VERBOS = r'\b(?:gastei|paguei|comprei|recebi|ganhei)\b'
UNIDADE_DEPOIS = r'\s*(?:dias?|mes(?:es)?|semanas?|horas?|anos?|pessoas?|km|kg|itens?|unidades?|min|h)\b'
CONECTORES =r'(?:no|na|nos|nas|de|do|da|dos|das|em|com|pelo|pela|por|via|para|pra|um|uma|o|a|conta|pagando)'


def data_informada(text, hoje):
    """Data completa, relativa ou curta ("15/10", "dia 15", "segunda").

    Data curta assume o ano de ``hoje`` e nunca é futura; data completa
    (DD/MM/AAAA, AAAA-MM-DD) é devolvida como informada.
    """
    value = normalizar(text.strip())
    relative = {'hoje': 0, 'ontem': -1, 'anteontem': -2,
                'amanha': 1, 'depois de amanha': 2}
    value = re.sub(r'\s+', ' ', re.sub(PERIODO_DO_DIA + r'$', '', value)).strip()
    if value in relative:
        return (hoje + timedelta(days=relative[value])).isoformat()
    if re.search(EXPRESSAO_DATA_VAGA, value):
        raise ValueError('Não consegui saber o dia exato. Informe DD/MM, "ontem" ou "dia 15".')
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            raise ValueError('Essa data não existe ou está incompleta. Use DD/MM/AAAA.')
    natural = interpretar_expressao_data(value, hoje)
    if natural is not None:
        return natural.isoformat()
    raise ValueError('Essa data não existe ou está incompleta. Use DD/MM/AAAA.')


def descricao_valida(value):
    text = str(value or '').strip()
    return bool(text and len(text) <= 160 and
                (any(char.isalpha() for char in text) or text == '99'))


def valor_informado(value):
    try:
        amount=parse_money(value)
        if not amount.is_finite():raise ValueError('Use um valor numérico finito.')
        return float(amount)
    except DecimalException as exc:
        raise ValueError('Valor inválido ou grande demais. Confira o valor informado.') from exc


def categoria_da_descricao(description, tipo):
    return canonicalizar_categoria(detectar_categoria(normalizar(description), tipo), 'Outros')


def extrair_campos(text, *, hoje, contas=(), tipo=None, extrair_valor=True):
    """Reconhece campos explícitos; rejeita valores/contas/formas conflitantes.

    Números de produtos (iPhone 15, C6, 99) não viram valor automaticamente.
    Valor: início da frase, R$, reais, por/custou/valor de ou N parcelas de X.
    A ordem de descrição, forma, conta e data é livre após o valor.
    """
    bruto = str(text or '').strip()
    linhas = texto_com_varios_lancamentos(bruto)
    if linhas and not parece_codigo_ou_texto_longo(' '.join(bruto.splitlines())):
        # Nunca funde linhas nem grava a primeira: pede um lançamento por vez.
        raise ValueError(mensagem_varios_lancamentos(linhas))
    if len(bruto.splitlines()) > 1 and not parece_codigo_ou_texto_longo(bruto):
        bruto = ' '.join(l.strip() for l in bruto.splitlines() if l.strip())
    original = unicodedata.normalize('NFC', bruto)
    if not original or parece_codigo_ou_texto_longo(original):
        raise ValueError('Use uma frase curta para um único registro.')
    # Portuguese accents do not change offsets after NFC + NFD accent removal.
    clean = normalizar(original)
    if len(clean) != len(original):
        raise ValueError('Não consegui interpretar esses caracteres. Use o registro por etapas.')
    chars = list(original)
    fields = {}

    def restante():
        return normalizar(''.join(chars))

    def apagar(start, end):
        chars[start:end] = ' ' * (end - start)

    match = re.match(r'^(gastei|paguei|comprei|recebi|ganhei|entrada)\b', clean)
    if match:
        detected = 'receita' if match[1] in {'recebi', 'ganhei', 'entrada'} else 'despesa'
        if tipo and tipo != detected:
            raise ValueError('Esse texto muda o tipo do registro. Cancele e comece uma nova movimentação.')
        tipo = detected
        apagar(*match.span())
    tipo = tipo or 'despesa'

    category = re.search(r'\bcategoria\s+(.+)$', restante())
    if category:
        value = original[category.start(1):category.end(1)].strip()
        if len(value) > 80:
            raise ValueError('Use uma categoria de até 80 caracteres.')
        fields['categoria'] = canonicalizar_categoria(value.title(), 'Outros')
        fields['_categoria_explicita'] = True
        apagar(*category.span())

    if re.search(EXPRESSAO_DATA_VAGA, restante()):
        raise ValueError('Não consegui saber o dia exato. Informe DD/MM, "ontem" ou "dia 15".')
    dates = [m for m in re.finditer(DATAS_NO_TEXTO, restante())
             if not (original[max(0, m.start() - 1):m.start()] == '(' and original[m.end():m.end() + 1] == ')')]
    values = {data_informada(original[m.start():m.end()], hoje) for m in dates}
    if len(values) > 1:
        raise ValueError('Há mais de uma data. Informe uma data por registro.')
    if values:
        fields['data'] = values.pop()
        for m in dates:
            apagar(*m.span())

    installment_pattern = rf'\b(?:em\s+)?(\d{{1,3}})\s*(?:x\b|parcelas\b|vezes\b)(?:\s+de\s+(?:r\$\s*)?({VALOR})\s*(?:reais|real)?)?'
    installments = list(re.finditer(installment_pattern, restante()))
    if len(installments) > 1:
        raise ValueError('Informe um único parcelamento por registro.')
    total_parcelado = None
    if installments:
        m = installments[0]
        count = int(m[1])
        if not 1 <= count <= 60:
            raise ValueError('Use de 1 a 60 parcelas.')
        if tipo == 'receita' and count > 1:
            raise ValueError('Registre cada recebimento separadamente.')
        fields['parcelas_total'] = count
        if m[2] is not None:
            total_parcelado = round(valor_informado(m[2]) * count, 2)
        apagar(*m.span())
    elif re.search(r'\bparcelad[oa]\b', restante()):
        if tipo == 'receita':
            raise ValueError('Registre cada recebimento separadamente.')
        fields['_installments_pending'] = True
    for m in list(re.finditer(r'\b(?:parcelad[oa]|dividid[oa])\b', restante())):
        apagar(*m.span())

    def aliases(mapping):
        if not mapping:
            return []
        pattern = r'(?<!\w)(?:' + '|'.join(re.escape(k) for k in sorted(mapping, key=len, reverse=True)) + r')(?!\w)'
        return [(m, mapping[m[0]]) for m in re.finditer(pattern, restante())]

    methods = aliases(FORMAS)
    unique = {value for _, value in methods}
    if len(unique) > 1:
        raise ValueError('Há mais de uma forma de pagamento. Escolha uma por registro.')
    if unique:
        fields['forma_pagamento'] = unique.pop()
    for m, _ in methods:
        apagar(*m.span())
    if fields.get('parcelas_total', 1) > 1 or fields.get('_installments_pending'):
        if fields.get('forma_pagamento') not in (None, 'crédito'):
            raise ValueError('Esta compra está parcelada. Informe crédito ou registre a compra à vista.')
        fields['forma_pagamento'] = 'crédito'
    if tipo == 'receita' and fields.get('forma_pagamento') in {'crédito', 'débito', 'boleto'}:
        raise ValueError('Para recebimentos, escolha Pix, dinheiro ou transferência.')

    accounts = dict(CONTAS)
    for account in contas:
        if normalizar(account) not in FORMAS:
            accounts[normalizar(account)] = account
    found = aliases(accounts)
    # Caju também é alimento; não confundir "suco de caju" com a conta Caju.
    found = [(m, value) for m, value in found if not (
        normalizar(value) == 'caju' and re.search(r'\b(?:suco|castanha|doce)(?:\s+de)?\s*$', clean[:m.start()]))]
    unique = {normalizar(value): value for _, value in found}
    if len(unique) > 1:
        raise ValueError('Há mais de uma conta. Informe uma conta por registro.')
    if unique:
        fields['conta'] = next(iter(unique.values()))
    for m, _ in found:
        apagar(*m.span())

    if extrair_valor:
        monetary = []

        def centavos_apos(end):
            """Lê a continuação opcional ``e N centavos`` de um valor em reais."""
            tail = restante()[end:]
            numeric = re.match(rf'\s+e\s+({VALOR})\s+centavos?\b', tail)
            if numeric:
                cents = valor_informado(numeric[1])
                if not cents.is_integer() or not 0 <= cents <= 99:
                    raise ValueError('Use de 0 a 99 centavos após o valor em reais.')
                return cents, end + numeric.end()
            written = re.match(r'\s+e\s+([a-z\s]+?)\s+centavos?\b', tail)
            if written:
                cents = texto_numero_para_float(written[1])
                if cents is None or not float(cents).is_integer() or not 0 <= cents <= 99:
                    raise ValueError('Não consegui interpretar os centavos informados.')
                return float(cents), end + written.end()
            return 0.0, end

        # "1,5k", "2k" e "1 mil e 500": Decimal via parse_money, sem float novo.
        for m in re.finditer(r'(?<![\w.,])(\d+(?:[.,]\d{1,2})?)k(?!\w)', restante()):
            monetary.append((m.start(), m.end(), float(parse_money(m[1]) * 1000)))
        for m in re.finditer(r'(?<![\w.,])(\d{1,3})\s+mil\s+e\s+(\d{1,3})(?![\w.,])(?:\s+(?:reais|real)\b)?', restante()):
            if not any(m.start() < end and m.end() > start for start, end, _ in monetary):
                monetary.append((m.start(), m.end(), float(parse_money(m[1]) * 1000 + parse_money(m[2]))))
        patterns = [rf'^\s*(?:r\$\s*)?({VALOR})(?:\s*(?:reais|real)\b)?(?!\s*centavos?\b)',
                    rf'r\$\s*({VALOR})(?:\s*(?:reais|real)\b)?',
                    rf'(?<!\w)({VALOR})\s+(?:reais|real)\b',
                    rf'\b(?:valor(?:\s+de)?|custou|por)\s+(?:r\$\s*)?({VALOR})(?!\s*centavos?\b)']
        for pattern in patterns:
            for m in re.finditer(pattern, restante()):
                if not any(m.start() < end and m.end() > start for start, end, _ in monetary):
                    token=m[1]
                    # Pontuação de final de frase não é uma casa decimal.
                    if token.endswith(('.', ',')) and not token.endswith(('..', ',,', '.,', ',.')):
                        token=token[:-1]
                    value = valor_informado(token)
                    end = m.end()
                    consumido = m[0]
                    # "1,5 mil", "R$ 2 mil", "3 mil reais": o multiplicador faz
                    # parte do valor (antes virava R$ 1,50 e "mil" na descrição).
                    escala = re.match(r'\s+(mil|milhao|milhoes)\b(?:\s+(?:reais|real)\b)?', restante()[end:])
                    if escala and not re.search(r'\b(?:reais|real)\b', m[0]):
                        value = round(value * MULTIPLICADORES[escala[1]], 2)
                        end += escala.end()
                        consumido += escala[0]
                    # Voz costuma transcrever R$ 197,99 como "197 reais e 99 centavos".
                    if re.search(r'\b(?:reais|real)\b', consumido):
                        cents, end = centavos_apos(end)
                        value = round(value + cents / 100, 2)
                    monetary.append((m.start(), end, value))
        # Por extenso precisa de "reais"; nomes de produtos permanecem intactos.
        if not monetary:
            for m in re.finditer(r'\b([a-z\s]+?)\s+(?:reais|real)\b', restante()):
                word_matches = list(re.finditer(r'\S+', m[1]))
                for word in word_matches:
                    value = texto_numero_para_float(m[1][word.start():])
                    if value is not None:
                        cents, end = centavos_apos(m.end())
                        monetary.append((m.start(1) + word.start(), end,
                                         round(valor_informado(value) + cents / 100, 2)))
                        break
        # Também aceita valores abaixo de um real ditados somente em centavos.
        if not monetary:
            cents_match = re.search(rf'(?<!\w)({VALOR})\s+centavos?\b', restante())
            if cents_match:
                cents = valor_informado(cents_match[1])
                if not cents.is_integer() or not 0 <= cents <= 99:
                    raise ValueError('Use de 0 a 99 centavos.')
                monetary.append((cents_match.start(), cents_match.end(), cents / 100))
        if not monetary:
            for m in re.finditer(r'\b([a-z\s]+?)\s+centavos?\b', restante()):
                for word in re.finditer(r'\S+', m[1]):
                    cents = texto_numero_para_float(m[1][word.start():])
                    if cents is not None:
                        if not float(cents).is_integer() or not 0 <= cents <= 99:
                            raise ValueError('Use de 0 a 99 centavos.')
                        monetary.append((m.start(1) + word.start(), m.end(), cents / 100))
                        break
        # Valor em qualquer posição ("mercado 45", "recebi salário 5000"), só quando
        # há exatamente um número livre: dois ou mais números nunca são adivinhados.
        if not monetary and total_parcelado is None:
            livres = []
            texto_rest = restante()
            for m in re.finditer(r'(?<![\w.,/-])[+-]?\d[\d.,]*(?![\w/])', texto_rest):
                token = m[0].rstrip('.,')
                if not token or token.lstrip('+-') == '99':
                    continue
                if re.match(UNIDADE_DEPOIS, texto_rest[m.end():]) or numero_e_de_produto(texto_rest, m.start()):
                    continue
                livres.append((m.start(), m.start() + len(token), token))
            if len(livres) > 1:
                nomes = [t for _, _, t in livres]
                lista = (f'dois valores: {nomes[0]} e {nomes[1]}' if len(nomes) == 2 else
                         f'{len(nomes)} valores: {", ".join(nomes[:-1])} e {nomes[-1]}')
                raise ValueError(f'Encontrei {lista}. Qual é o valor?')
            if livres:
                inicio, fim, token = livres[0]
                valor = valor_informado(token)
                escala = re.match(r'\s+(mil|milhao|milhoes)\b', texto_rest[fim:])
                if escala:
                    valor = float(parse_money(token) * MULTIPLICADORES[escala[1]])
                    fim += escala.end()
                monetary.append((inicio, fim, valor))
        if len(monetary) > 1:
            raise ValueError('Há mais de um valor. Informe uma movimentação por vez.')
        if monetary:
            fields['valor'] = monetary[0][2]
            apagar(monetary[0][0], monetary[0][1])
        if total_parcelado is not None:
            if 'valor' in fields and abs(fields['valor'] - total_parcelado) > .005:
                raise ValueError('O total não corresponde às parcelas informadas.')
            fields['valor'] = total_parcelado

        if re.search(VERBOS, restante()):
            raise ValueError('Parece haver mais de um lançamento. Envie um por vez para eu conferir cada um.')
        if re.search(r'(?:\b(?:e|mais)\b|[+;,])\s*(?:r\$\s*)?[+-]?\d', restante()):
            raise ValueError('Parece haver mais de uma movimentação. Envie um registro por vez.')

    description = re.sub(r'\s+', ' ', ''.join(chars)).strip(' .,;:-/!?')
    for _ in range(6):
        description = re.sub(rf'^{CONECTORES}(?:\s+|$)', '', description, flags=re.I).strip(' .,;:-/!?')
        description = re.sub(rf'(?:^|\s+){CONECTORES}$', '', description, flags=re.I).strip(' .,;:-/!?')
    if len(description) > 160:
        raise ValueError('Use uma descrição de até 160 caracteres.')
    if descricao_valida(description):
        fields['descricao'] = description
        if 'categoria' not in fields:
            fields['categoria'] = categoria_da_descricao(description, tipo)
    fields['tipo'] = tipo
    return fields
