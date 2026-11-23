"""Conferência explícita com o banco; diferença de composição não é estorno.

Usa auditoria existente. Não cria compra, transferência ou pagamento adicional.
O ajuste pertence somente à competência conferida e não congela compras futuras.
"""
import json
import sqlite3
from datetime import date,datetime
import relogio
from decimal import Decimal
import database as db
from consulta_cache import obter_ou_calcular as _consulta_cache
from money import parse_money

def chave(mes,conta):
    from compromissos import normalizar_conta_fatura
    date.fromisoformat(mes+'-01')
    return mes+':'+normalizar_conta_fatura(conta)

def obter(mes,conta,conn=None):
    if conn is None:
        return _consulta_cache(
            ('fatura_conferencia.obter', mes, chave(mes,conta)),
            lambda: _obter_sem_conexao(mes,conta),
        )
    row=conn.execute("SELECT operacao,dados_depois FROM auditoria_eventos WHERE entidade='fatura_conferencia' AND entidade_id=? ORDER BY id DESC LIMIT 1",(chave(mes,conta),)).fetchone()
    return json.loads(row[1]) if row and row[0]=='confirmada' else None


def _obter_sem_conexao(mes,conta):
    with db.get_connection() as c:
        return obter(mes,conta,c)


def _ajustes_mes(mes):
    with db.get_connection() as c:
        keys=[r[0] for r in c.execute("SELECT DISTINCT entidade_id FROM auditoria_eventos WHERE entidade='fatura_conferencia' AND entidade_id LIKE ?",(mes+':%',))]
        result=[]
        for key in keys:
            row=c.execute("SELECT operacao,dados_depois FROM auditoria_eventos WHERE entidade='fatura_conferencia' AND entidade_id=? ORDER BY id DESC LIMIT 1",(key,)).fetchone()
            if row and row[0]=='confirmada':result.append(json.loads(row[1]))
        return result


def ajustes_mes(mes):
    return _consulta_cache(
        ('fatura_conferencia.ajustes_mes', mes),
        lambda: _ajustes_mes(mes),
    )

def item_projecao(evento):
    return dict(origem='conferencia_fatura',tipo='conferencia_fatura',id=None,
        nome='Conferência do total da fatura '+evento['conta_cartao'],
        categoria='Conferência de fatura',conta_pagamento=evento['conta_cartao'],
        forma_pagamento='fatura',valor=evento['ajuste_composicao'],
        data=evento['data_conferencia'],ativo=True,parcelas_total=None,parcela_atual=None)

def confirmar(mes,conta,movimento_id,total_banco,expected_movimento,expected_fatura,usuario,motivo):
    """Corrige UM pagamento já realizado e confere a composição da mesma fatura.

Exige prévia integral, motivo e total efetivamente informado pelo usuário.
Saldos atuais conferidos após o pagamento original são preservados.
"""
    from compromissos import calcular_fatura_unificada,normalizar_conta_fatura
    from services import mesma_conta_saldo
    total=parse_money(total_banco)
    if total<=0 or total>100000000:raise ValueError('Informe o total positivo quitado no banco.')
    if not usuario or not str(motivo or '').strip():raise ValueError('Informe quem confirmou e o motivo da conferência.')
    stamp=relogio.agora().isoformat(timespec='seconds')
    with db.fatura_write_transaction() as c:
        c.row_factory=sqlite3.Row
        existing=obter(mes,conta,c)
        if existing and existing['movimento_id']==movimento_id and Decimal(str(existing['total_banco']))==total:
            current=c.execute('SELECT * FROM fatura_movimentos WHERE id=?',(movimento_id,)).fetchone()
            if current and dict(current)==existing['movimento_corrigido']:return dict(existing,repetido=True)
        mov=c.execute('SELECT * FROM fatura_movimentos WHERE id=?',(movimento_id,)).fetchone()
        if not mov or dict(mov)!=expected_movimento:raise ValueError('O pagamento mudou desde a prévia. Confira novamente.')
        if mov['ano_mes']!=mes or normalizar_conta_fatura(mov['conta_cartao'])!=normalizar_conta_fatura(conta) or mov['tipo_movimento']!='pagamento_total':
            raise ValueError('A conferência exige o pagamento total dessa fatura.')
        fatura=calcular_fatura_unificada(mes,conta,somente_cartao=True)
        if fatura!=expected_fatura:raise ValueError('A composição mudou desde a prévia. Confira novamente.')
        if existing:raise ValueError('Já há uma conferência diferente. Revise a conferência anterior antes de substituí-la.')
        outros=Decimal(str(fatura['pagamentos']))-Decimal(str(mov['valor']))
        novo_pagamento=total-outros
        if novo_pagamento<=0:raise ValueError('O total informado conflita com os outros pagamentos da fatura.')
        liquid_original=(Decimal(str(fatura['valor_bruto']))-Decimal(str(fatura['credito_herdado']))
            -Decimal(str(fatura['creditos']))+Decimal(str(fatura['ajustes_debito'])))
        ajuste=total-liquid_original
        delta=novo_pagamento-Decimal(str(mov['valor']))
        preserved=[]
        # Uma correção de pagamento histórico não deve descontar novamente
        # dinheiro que o usuário já conferiu no banco depois desse pagamento.
        for base in c.execute('SELECT * FROM saldos_mensais_contas WHERE ano_mes=?',(mes,)).fetchall():
            if not mesma_conta_saldo(base['conta'],mov['conta_origem']):continue
            events=c.execute("SELECT entidade_id,criado_em FROM auditoria_eventos WHERE entidade='saldo_conta' AND operacao='ajuste_atual_confirmado' ORDER BY id DESC").fetchall()
            anchored=any(key.startswith(mes+':') and mesma_conta_saldo(key.split(':',1)[1],base['conta']) and when>=mov['criado_em'] for key,when in events)
            if anchored and delta:
                value=float(Decimal(str(base['saldo_inicial']))+delta)
                c.execute('UPDATE saldos_mensais_contas SET saldo_inicial=?,atualizado_em=? WHERE id=?',(value,stamp,base['id']))
                preserved.append(dict(conta=base['conta'],base_antes=base['saldo_inicial'],base_depois=value))
        if preserved:
            total_base=float(sum((Decimal(str(r[0])) for r in c.execute('SELECT saldo_inicial FROM saldos_mensais_contas WHERE ano_mes=?',(mes,))),Decimal('0')))
            c.execute('UPDATE saldos_mensais SET saldo_inicial=?,atualizado_em=? WHERE ano_mes=?',(total_base,stamp,mes))
        c.execute('UPDATE fatura_movimentos SET valor=?,atualizado_em=? WHERE id=?',(float(novo_pagamento),stamp,movimento_id))
        corrected=dict(c.execute('SELECT * FROM fatura_movimentos WHERE id=?',(movimento_id,)).fetchone())
        db.registrar_auditoria('fatura_movimento',movimento_id,'correcao_valor_conferido',dict(mov),corrected,'conferencia',usuario,conn=c)
        event=dict(ano_mes=mes,conta_cartao=conta,movimento_id=movimento_id,
            total_banco=float(total),total_composicao_registrada=float(liquid_original),
            ajuste_composicao=float(ajuste.quantize(Decimal('0.01'))),
            data_conferencia=date.fromisoformat(mes+'-01').replace(day=__import__('calendar').monthrange(int(mes[:4]),int(mes[5:]))[1]).isoformat(),
            motivo=str(motivo),movimento_corrigido=corrected,bases_preservadas=preserved)
        db.registrar_auditoria('fatura_conferencia',chave(mes,conta),'confirmada',
            dict(fatura=fatura,movimento=dict(mov)),event,'conferencia',usuario,conn=c)
        return dict(event,repetido=False)
