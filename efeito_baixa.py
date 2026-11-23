"""Efeito de um registro no dinheiro: saldo da conta e sobra prevista, antes → depois.

Pedido do titular em 19/11/2026: ao dar baixa no iCloud (Pix, Mercado Pago) ele não
percebeu que o saldo da conta caiu, porque a sobra prevista não muda (o valor já
estava reservado em A pagar). Agora a prévia e a confirmação mostram:

    🏦 Mercado Pago: R$ 10.000,00 → R$ 9.966,55
    📊 Sobra prevista: sem mudança — este valor já estava reservado em A pagar.

Crédito não sai do saldo na hora (vai para a fatura): só um aviso. Só leitura; uma
falha aqui nunca impede o registro (devolve texto vazio e registra no log).
"""
import logging

import database as db
import services as svc
from consulta_cache import contexto_consulta
from faturas_competencia import eh_credito
from saldo_resumo import resumir_saldo


def _norm(texto):
    return svc.normalizar_busca_texto(str(texto or '')).strip()


def instantaneo(t):
    """Saldo da conta do registro e sobra prevista no mês do registro (ou None)."""
    if not t or t.get('simulate') or eh_credito(t) or not str(t.get('conta') or '').strip():
        return None
    mes = str(t['data'])[:7]
    try:
        with db.read_only_mode(), contexto_consulta():
            contas = svc.calcular_caixa_por_conta_mes(mes)['contas']
            saldo = next((float(v['disponivel']) for k, v in contas.items() if _norm(k) == _norm(t['conta'])), None)
            sobra = float(resumir_saldo(svc.obter_metricas_resultado_mes(mes))['saldo_final'])
        return {'conta': t['conta'], 'saldo': saldo, 'sobra': sobra}
    except Exception:
        logging.warning('Efeito do registro indisponível (só exibição).', exc_info=True)
        return None


def previa(t, dinheiro):
    """Linha para a prévia: o que vai acontecer com o saldo da conta ao salvar."""
    if t and eh_credito(t):
        return '💳 No crédito: não sai do saldo agora; entra na fatura do cartão.'
    agora = instantaneo(t)
    if not agora or agora['saldo'] is None:
        return ''
    sinal = 1 if t.get('tipo') == 'receita' else -1
    return f'🏦 Ao salvar: {agora["conta"]} {dinheiro(agora["saldo"])} → {dinheiro(agora["saldo"] + sinal * float(t["valor"]))}'


def confirmacao(antes, t, dinheiro):
    """Bloco para a tela "Registro salvo": saldo da conta e sobra prevista, antes → depois."""
    if t and eh_credito(t):
        return '\n\n💳 No crédito: não saiu do saldo agora; entra na fatura do cartão.'
    depois = instantaneo(t)
    if not antes or not depois or antes['saldo'] is None or depois['saldo'] is None:
        return ''
    linhas = ['', '', '<b>Efeito no seu dinheiro</b>',
              f'🏦 {depois["conta"]}: {dinheiro(antes["saldo"])} → <b>{dinheiro(depois["saldo"])}</b>']
    if abs(depois['sobra'] - antes['sobra']) < 0.005:
        linhas.append('📊 Sobra prevista: sem mudança — este valor já estava '
                      + ('previsto em A receber.' if t.get('tipo') == 'receita' else 'reservado em A pagar.')
                      if t.get('conciliacao') else '📊 Sobra prevista: sem mudança.')
    else:
        linhas.append(f'📊 Sobra prevista: {dinheiro(antes["sobra"])} → {dinheiro(depois["sobra"])}')
    return '\n'.join(linhas)
