"""Ponte de caixa: crédito em um cartão não é dinheiro em outro banco."""
from collections import defaultdict
from decimal import Decimal


def ajustar_reservas(mes, transacoes, esperados, liquidacoes, conta_filtro=None):
    import compromissos as comp
    import services as svc
    custos=defaultdict(Decimal); pagos=defaultdict(Decimal); nomes={}
    def conta(item):
        nome=item.get('conta_pagamento') or item.get('conta') or ''
        key=comp.normalizar_conta_fatura(nome);nomes[key]=nome
        return key
    for row in transacoes:
        item=dict(row,origem='transacao',nome=row.get('descricao'))
        if row.get('tipo')=='despesa' and not svc.transacao_afeta_saldo_disponivel(row) and comp.item_eh_fatura_cartao(item):
            if conta_filtro and not svc.mesma_conta_saldo(row.get('conta'),conta_filtro):continue
            custos[conta(item)]+=Decimal(str(row.get('valor') or 0))
    for item in esperados:
        if comp.item_eh_fatura_cartao(item) or item.get('origem')=='fatura_movimento':
            custos[conta(item)]+=Decimal(str(item.get('valor') or 0))
    for item in liquidacoes:
        pagos[conta(item)]-=Decimal(str(item.get('valor') or 0))
    detalhes=[];memo={};total=Decimal('0')
    for key in sorted(custos.keys()|pagos.keys()):
        fatura=comp.calcular_fatura_unificada(mes,nomes[key],memo,somente_cartao=True)
        # Pagamento desta fatura feito em mês posterior (D3): no fim deste mês
        # a fatura ainda estava em aberto; o caixa do pagamento é o do outro mês.
        pago_depois=sum((Decimal(str(m['valor'] or 0)) for m in svc.pagamentos_fatura_posteriores(mes)
                         if comp.normalizar_conta_fatura(m['conta_cartao'] or '')==key), Decimal('0'))
        reserva=max(Decimal('0'),Decimal(str(fatura['saldo_restante']))+pago_depois).quantize(Decimal('0.01'))
        bruto=custos[key]-pagos[key]
        ajuste=(bruto-reserva).quantize(Decimal('0.01'))
        total+=ajuste
        detalhes.append(dict(conta=nomes[key],reserva_antes=float(bruto),reserva_fatura=float(reserva),
            ajuste=float(ajuste),credito_no_cartao=max(0,-float(fatura['saldo_restante']))))
    return float(total),detalhes
