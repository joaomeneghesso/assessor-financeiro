"""Confirmação atômica do saldo atual de uma conta e da base geral do mês."""
import sqlite3
from datetime import date, datetime
import relogio
from decimal import Decimal
import database as db
import services as svc
from money import parse_money


def capturar(month):
    """Foto para validação otimista. Não guarda dados em cache entre ações."""
    date.fromisoformat(month+'-01')
    general=db.buscar_saldo_mensal(month)
    return {'caixa':svc.calcular_caixa_por_conta_mes(month),
            'geral':dict(general) if general else None,
            'bases':[dict(row) for row in db.buscar_saldos_contas_mes(month)]}


def confirmar(month, account, desired, expected, session):
    account=svc.normalizar_conta_caixa(str(account or '').strip())
    if account==svc.CONTA_SEM_BANCO_DEFINIDO:
        raise ValueError('Informe uma conta real. Pix e crédito são formas de pagamento.')
    desired=parse_money(desired,allow_negative=True)
    if abs(desired)>100000000:raise ValueError('Use um saldo de até R$ 100 milhões.')
    if not expected:raise ValueError('A prévia do saldo expirou. Abra Ajustar saldo novamente.')
    stamp=relogio.agora().isoformat(timespec='seconds')
    with db.fatura_write_transaction() as conn:
        conn.row_factory=sqlite3.Row
        # Nenhum outro escritor pode entrar entre a releitura e as duas gravações.
        current=capturar(month)
        if current!=expected:
            raise ValueError('Os saldos ou movimentos mudaram desde a prévia. Abra Ajustar saldo novamente e confira o valor atual.')
        caixa=current['caixa']
        item=(caixa.get('contas') or {}).get(account) or {}
        amount=lambda key:Decimal(str(item.get(key) or 0))
        base=float(parse_money(desired-amount('entradas')+amount('saidas'),allow_negative=True))
        existentes=[row for row in conn.execute('SELECT * FROM saldos_mensais_contas WHERE ano_mes=?',(month,))
                    if svc.mesma_conta_saldo(row['conta'],account)]
        if len(existentes)>1:
            raise ValueError('Há mais de uma base para esta conta. Confira as duplicidades antes de ajustar o saldo.')
        old_account=existentes[0] if existentes else None
        old_general=conn.execute('SELECT * FROM saldos_mensais WHERE ano_mes=?',(month,)).fetchone()
        # A primeira base manual interrompe a herança automática de TODAS as
        # contas. Materialize as demais bases, incluindo ajustes já absorvidos,
        # para que corrigir um banco não zere o saldo inicial dos outros.
        preserved=[]
        if caixa.get('herdado_auto'):
            for name,other in (caixa.get('contas') or {}).items():
                if svc.mesma_conta_saldo(name,account):continue
                inherited=float(parse_money(Decimal(str(other.get('inicial') or 0))+Decimal(str(other.get('ajuste_conciliacao_heranca') or 0)),allow_negative=True))
                conn.execute('INSERT INTO saldos_mensais_contas (ano_mes,conta,saldo_inicial,observacao,criado_em,atualizado_em) VALUES (?,?,?,?,?,?)',(month,name,inherited,'Herança preservada ao ajustar outra conta.',stamp,stamp))
                preserved.append({'conta':name,'base':inherited})
        note='Saldo atual confirmado pelo Telegram; base derivada automaticamente.'
        if old_account:
            conn.execute('UPDATE saldos_mensais_contas SET conta=?,saldo_inicial=?,observacao=?,atualizado_em=? WHERE id=?',(account,base,note,stamp,old_account['id']))
        else:
            conn.execute('INSERT INTO saldos_mensais_contas (ano_mes,conta,saldo_inicial,observacao,criado_em,atualizado_em) VALUES (?,?,?,?,?,?)',(month,account,base,note,stamp,stamp))
        bases=conn.execute('SELECT saldo_inicial FROM saldos_mensais_contas WHERE ano_mes=?',(month,)).fetchall()
        total=float(sum((Decimal(str(r[0] or 0)) for r in bases),Decimal('0')))
        note_general='Sincronizado com a base de saldos por conta confirmada no Telegram.'
        if old_general:
            conn.execute('UPDATE saldos_mensais SET saldo_inicial=?,observacao=?,atualizado_em=? WHERE ano_mes=?',(total,note_general,stamp,month))
        else:
            conn.execute('INSERT INTO saldos_mensais (ano_mes,saldo_inicial,observacao,criado_em,atualizado_em) VALUES (?,?,?,?,?)',(month,total,note_general,stamp,stamp))
        db.registrar_auditoria('saldo_conta',month+':'+account,'ajuste_atual_confirmado',
            {'conta':dict(old_account) if old_account else None,'geral':dict(old_general) if old_general else None},
            {'conta':account,'saldo_atual':float(desired),'base_conta':base,'base_geral':total,'bases_herdadas_preservadas':preserved},'telegram',session,conn=conn)
    return base
