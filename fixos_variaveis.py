"""Fixos de valor variável (ex.: conta de luz): regras puras, sem banco.

Pedido do titular em 18/11/2026. Um fixo marcado como variável:
- na previsão (A pagar, Início, herança) vale a **estimativa**: média dos valores
  pagos nos 3 últimos meses com pagamento, antes do mês consultado; sem histórico,
  vale o valor cadastrado;
- na baixa, o bot pergunta o valor real; qualquer valor fecha o mês (menor não deixa
  resto "a pagar"; maior não é recusado). Uma segunda baixa no mesmo mês é recusada;
- só vale para fixos de despesa fora do cartão (no crédito, a conta compõe a fatura).

Valor pago de um mês = soma dos lançamentos vinculados (baixas) naquele mês; meses
sem baixa usam os lançamentos antigos que o titular escolheu como histórico
(ex.: as contas de luz lançadas como gasto comum antes do fixo existir). Nada nos
lançamentos antigos é alterado: eles só entram na média.

Camadas (sem ciclo de import): este módulo não importa banco nem conciliação;
``conciliacao`` lê o estado (``auditoria_eventos``, entidade ``fixo_variavel``) e os
lançamentos e chama estas funções; ``fixos_variaveis_acoes`` grava e sugere histórico.
"""
import json
import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP

ENTIDADE = 'fixo_variavel'
MESES_MEDIA = 3
_IGNORAR = {'conta', 'de', 'da', 'do', 'das', 'dos', 'fixo', 'mensal', 'a', 'o', 'e', 'pagamento', 'boleto'}


class FixoVariavelErro(ValueError):
    pass


def centavos(valor):
    return int((Decimal(str(valor or 0)).quantize(Decimal('0.01'), ROUND_HALF_UP) * 100))


def _norm(texto):
    t = unicodedata.normalize('NFKD', str(texto or '').lower())
    return re.sub(r'\s+', ' ', ''.join(c for c in t if not unicodedata.combining(c))).strip()


def estados_de_eventos(eventos):
    """Eventos de auditoria (mais recente primeiro) -> {id (str): estado} só dos variáveis."""
    estados = {}
    for ev in eventos:
        chave = str(ev['entidade_id'])
        if chave in estados:
            continue
        try:
            estados[chave] = json.loads(ev['dados_depois'] or 'null') or {}
        except (TypeError, ValueError):
            estados[chave] = {}
    return {k: v for k, v in estados.items() if v.get('variavel')}


def elegivel(compromisso):
    """Motivo de recusa (texto) ou None se o fixo pode ser variável."""
    c = dict(compromisso)
    if c.get('tipo') != 'fixo':
        return 'Só fixos de despesa podem ter valor variável.'
    forma = _norm(c.get('forma_pagamento'))
    if 'credito' in forma or 'cartao' in forma:
        return ('Este fixo é pago no crédito: o valor real já entra na fatura do cartão. '
                'Valor variável vale para contas pagas por Pix, boleto, débito ou dinheiro.')
    return None


def historico_por_mes(transacoes):
    """Lançamentos de histórico -> {mes: centavos} (só despesas)."""
    meses = {}
    for t in transacoes:
        t = dict(t)
        if t.get('tipo') != 'despesa':
            continue
        mes = str(t['data'])[:7]
        meses[mes] = meses.get(mes, 0) + centavos(t['valor'])
    return meses


def estimativa(historico, baixas_por_mes, mes, valor_cadastro):
    """Média (2 casas, HALF_UP) dos 3 últimos meses com pagamento ANTES de ``mes``.

    Mês com baixa usa o valor baixado; sem baixa, o histórico escolhido. Sem nenhum
    mês anterior, vale o valor cadastrado. Devolve (valor, meses_usados).
    """
    valores = dict(historico or {})
    valores.update({m: int(c) for m, c in (baixas_por_mes or {}).items() if int(c) > 0})
    anteriores = sorted(((m, c) for m, c in valores.items() if m < mes), reverse=True)[:MESES_MEDIA]
    if not anteriores:
        return float(valor_cadastro or 0), []
    media = (Decimal(sum(c for _, c in anteriores)) / len(anteriores) / 100).quantize(Decimal('0.01'), ROUND_HALF_UP)
    return float(media), sorted(m for m, _ in anteriores)


def termos_busca(nome):
    """'Conta de luz' -> ['luz']; palavras de 3+ letras que não são genéricas."""
    return [p for p in re.findall(r'[a-z0-9]+', _norm(nome)) if len(p) >= 3 and p not in _IGNORAR]


def candidatos_de(transacoes, compromisso, ate_mes, meses=12):
    """Despesas avulsas dos ``meses`` meses antes de ``ate_mes`` cuja descrição contém um
    termo do nome do fixo. Só sugestão: o titular confirma antes de valer."""
    termos = termos_busca(dict(compromisso).get('nome'))
    if not termos:
        return []
    total = int(ate_mes[:4]) * 12 + int(ate_mes[5:7]) - 1 - meses
    inicio = f'{total // 12:04d}-{total % 12 + 1:02d}'
    achados = []
    for t in map(dict, transacoes):
        data = str(t.get('data') or '')
        if t.get('tipo') != 'despesa' or not (inicio <= data[:7] < ate_mes) or (t.get('parcelas_total') or 1) > 1:
            continue
        desc = _norm(t.get('descricao'))
        if any(re.search(rf'(?<![a-z0-9]){re.escape(termo)}(?![a-z0-9])', desc) for termo in termos):
            achados.append(t)
    return sorted(achados, key=lambda t: (str(t['data']), int(t['id'])))
