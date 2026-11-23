"""Composição explicável do saldo, sem banco e sem novas regras financeiras."""
from decimal import Decimal, ROUND_HALF_UP


def resumir_saldo(metricas):
    def valor(campo):
        number = Decimal(str(metricas.get(campo) or 0))
        if not number.is_finite():
            raise ValueError('O saldo contém um valor inválido. Confira os registros.')
        return number

    atual = valor('saldo_disponivel')
    # Receita prevista de mês anterior ainda não recebida (regra de herança de
    # 09/11/2026): faz parte do "a receber", mas é exibida separada.
    receber_herdado = valor('receitas_previstas_herdadas_total')
    receber = valor('entradas_previstas') + receber_herdado
    reservas = (valor('saidas_nao_imediatas_realizadas')
                + valor('despesas_esperadas_total')
                + valor('pendencias_herdadas_total')
                - valor('compensacao_pagamentos_fatura'))
    reservas -= valor('ajuste_reserva_faturas')
    final = valor('saldo_projetado')
    centavo = Decimal('0.01')
    if abs(atual + receber - reservas - final) > centavo:
        raise ValueError('A composição do saldo divergiu da projeção. Confira a memória do saldo.')
    arredondar = lambda number: number.quantize(centavo, rounding=ROUND_HALF_UP)
    atual, receber, final = map(arredondar, (atual, receber, final))
    # A soma dos valores EXIBIDOS também precisa fechar, inclusive no centavo.
    reservas = atual + receber - final
    meses_herdados = sorted({str(item.get('ano_mes_origem')) for item in
                             (metricas.get('receitas_previstas_herdadas_itens') or [])
                             if item.get('ano_mes_origem')})
    return {'saldo_atual': float(atual), 'a_receber': float(receber),
            'a_receber_herdado': float(arredondar(receber_herdado)),
            'a_receber_herdado_meses': meses_herdados,
            'reservas_liquidas': float(reservas), 'saldo_final': float(final),
            'resultado_mes': float(arredondar(valor('resultado_projetado_mes'))),
            'base_configurada': bool(metricas.get('saldo_configurado')),
            'herdado_auto': bool(metricas.get('saldo_herdado_auto')),
            'revisar': bool(metricas.get('revisoes_conciliacao'))}
