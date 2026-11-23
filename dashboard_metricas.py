"""Indicadores descritivos do dashboard; leitura, sem alterar o motor financeiro."""
import calendar
from datetime import date
import database as db
import services as svc
from assessor_orientacao import mes_anterior
from saldo_resumo import resumir_saldo

def registros(exp,month,cutoff):
    rows=[t for t in exp.transactions(month) if str(t['data'])<=cutoff.isoformat()]
    income=sum(float(t['valor']) for t in rows if t['tipo']=='receita')
    spending=sum(float(t['valor']) for t in rows if t['tipo']=='despesa')
    return dict(month=month,income=round(income,2),spending=round(spending,2),count=len(rows),cutoff=cutoff.isoformat())

def variacao_categorias(exp,month,today,top=3):
    """B4: variação de despesas POR CATEGORIA na mesma janela do mês anterior (mesmos dias, como enriquecer).

    None em período futuro. Sem despesa no mês anterior => base=False (não fabrica percentual).
    Categoria sem gasto na janela anterior entra com percent=None ("sem base"), nunca com %.
    """
    from decimal import Decimal
    from money import parse_money
    from assessor_orientacao import normalizar
    today_month=today.strftime('%Y-%m')
    if month>today_month:return None
    previous=mes_anterior(month)
    if not previous:return None
    y,m=map(int,month.split('-'));yy,mm=map(int,previous.split('-'))
    prev_last=calendar.monthrange(yy,mm)[1];current=month==today_month
    day=min(today.day,prev_last) if current else prev_last
    limit_cur=date(y,m,min(day,calendar.monthrange(y,m)[1])) if current else date(y,m,calendar.monthrange(y,m)[1])
    limit_prev=date(yy,mm,day)
    def agrupar(mes,limite):
        grupos={}
        for t in exp.transactions(mes):
            if t['tipo']!='despesa' or str(t['data'])>limite.isoformat():continue
            nome=normalizar(t['categoria']);g=grupos.setdefault(nome,dict(categoria=t['categoria'],total=Decimal('0'),n=0,maior=Decimal('0'),maior_desc=''))
            v=parse_money(t['valor'],allow_negative=True);g['total']+=v;g['n']+=1
            if v>g['maior']:g['maior']=v;g['maior_desc']=str(t.get('descricao') or '')
        return grupos
    with db.read_only_mode(),svc.contexto_consulta():
        atual=agrupar(month,limit_cur);anterior=agrupar(previous,limit_prev)
    base=sum((g['total'] for g in anterior.values()),Decimal('0'))>0
    linhas=[]
    for nome,g in atual.items():
        antes=anterior.get(nome,{}).get('total',Decimal('0'));delta=g['total']-antes
        pct=float(delta/antes*100) if antes>0 else None
        unico=g['n']==1 or (delta>0 and g['maior']>0 and g['maior']>=delta*Decimal('0.6') and g['maior']>antes)
        linhas.append(dict(categoria=g['categoria'],atual=g['total'],anterior=antes,delta=delta,percent=pct,
                           lancamentos=g['n'],maior=g['maior'],maior_desc=g['maior_desc'],um_lancamento=bool(unico and g['n']>=1 and delta>0)))
    for nome,g in anterior.items():
        if nome not in atual:
            linhas.append(dict(categoria=g['categoria'],atual=Decimal('0'),anterior=g['total'],delta=-g['total'],
                               percent=-100.0,lancamentos=0,maior=Decimal('0'),maior_desc='',um_lancamento=False))
    subiram=sorted([l for l in linhas if l['delta']>0],key=lambda l:l['delta'],reverse=True)[:top]
    caiu=sorted([l for l in linhas if l['delta']<0],key=lambda l:l['delta'])[:1]
    return dict(base=base,previous=previous,day=day,mode=('até o dia '+str(day)) if current else 'mês completo',
                subiram=subiram,caiu=caiu,total=len(linhas))

def enriquecer(exp,s,data,spec,view):
    """Valores de caixa seguem resumir_saldo; estatísticas usam registros por competência."""
    from telegram_experiencia import money,month_label
    summary=resumir_saldo(data['metrics']);today=exp.date_provider();month=s.month
    future=bool(data['future']);current=month==today.strftime('%Y-%m')
    y,m=map(int,month.split('-'));end=date(y,m,calendar.monthrange(y,m)[1]);cutoff=min(today,end)
    with db.read_only_mode(),svc.contexto_consulta():
        series=[]
        # Não apresenta meses futuros sem registro como realizados iguais a zero.
        anchor=today.strftime('%Y-%m') if future else month
        for offset in (2,1,0):
            period=mes_anterior(anchor,offset)
            if period is None:continue
            yy,mm=map(int,period.split('-'));last=date(yy,mm,calendar.monthrange(yy,mm)[1])
            row=registros(exp,period,min(today,last));row['label']=month_label(period).split()[0][:3]+' '+period[:4]
            row['partial']=period==today.strftime('%Y-%m');series.append(row)
        previous=mes_anterior(month)
        reference=None
        comparison_current=None
        if not future and previous:
            yy,mm=map(int,previous.split('-'))
            day=min(cutoff.day,calendar.monthrange(yy,mm)[1]) if current else calendar.monthrange(yy,mm)[1]
            reference=registros(exp,previous,date(yy,mm,day))
            comparison_current=registros(exp,month,date(y,m,day)) if current else None
    spending=float(data['spending']);income=float(data['income']);pending=round(sum(float(i['valor']) for i in data['items']),2)
    overdue=round(sum(float(i['valor']) for i in data['overdue']),2);soon=round(sum(float(i['valor']) for i in data['soon']),2)
    insights=[]
    def note(title,body,tone='neutral'):insights.append(dict(title=title,body=body,tone=tone))
    def percent(value,signed=False):return (f'{value:+.1f}' if signed else f'{value:.1f}').replace('.',',')+'%'
    if summary['revisar']:note('Conciliação precisa de revisão','A sobra fica sem confirmação até os vínculos serem conferidos. Não repita pagamentos.','warning')
    elif not summary['base_configurada'] or summary['herdado_auto']:note('Confira a base do saldo','O saldo deste período está ausente ou estimado. Confira as contas antes de usar a previsão.','warning')
    elif summary['saldo_final']<0:note('Previsão de falta de saldo','A previsão fica negativa com as entradas esperadas e reservas cadastradas.','danger')
    if future:note('Período futuro','Os valores principais são projeções. A evolução abaixo usa apenas registros até hoje.','warning')
    if data['overdue'] and not future:note('Pendências no corte',str(len(data['overdue']))+' compromisso(s), '+money(overdue)+'. Confira o histórico antes de registrar outra saída.','warning')
    elif data['soon'] and not future:note('Agenda dos próximos 7 dias',str(len(data['soon']))+' compromisso(s), '+money(soon)+'. Abra A pagar para ver contas e datas.')
    comparison=None
    if reference and reference['count'] and reference['spending']>0:
        measured=comparison_current['spending'] if comparison_current else spending
        delta=round(measured-reference['spending'],2);pct=round(delta/reference['spending']*100,1)
        comparison=dict(delta=delta,percent=pct,current_spending=measured,previous_spending=reference['spending'],cutoff=reference['cutoff'],mode=('primeiros '+str(day)+' dias de cada mês') if current else 'meses encerrados')
        note('Gastos versus mês anterior',('Subiram ' if delta>0 else 'Caíram ' if delta<0 else 'Sem variação: ')+percent(abs(pct))+' · '+money(abs(delta))+'. Comparação por competência, '+comparison['mode']+'.','warning' if delta>0 else 'neutral')
    elif not future:note('Comparação ainda indisponível','Faltam gastos registrados no período anterior; não estimei uma variação percentual.')
    categories=list(data['categories']);total=sum(float(v) for _,v in categories)
    if categories and total>0:
        category,amount=categories[0];share=round(float(amount)/total*100,1)
        note('Maior concentração de gastos',str(category)+': '+percent(share)+' dos gastos registrados · '+money(amount)+'.')
    budgets=data['budgets'];exceeded=[b for b in budgets if b['ratio']>=1];near=[b for b in budgets if .8<=b['ratio']<1]
    if exceeded:note('Limites atingidos',str(len(exceeded))+' categoria(s) atingiram o limite informado. Abra Limites para conferir.','warning')
    elif near:note('Limites próximos',str(len(near))+' categoria(s) já consumiram pelo menos 80% do limite.','warning')
    coverage=round(summary['saldo_atual']/summary['reservas_liquidas']*100,1) if summary['reservas_liquidas']>0 else None
    if not insights:note('Visão atualizada','Confira lançamentos e contas. Ausência de alertas não comprova que todos os movimentos foram registrados.')
    sections=[]
    if view=='home':
        spec['layout']='dashboard';spec['bars']=[];spec['details']=[]
        sections.append(dict(type='metrics',title='MOVIMENTO REGISTRADO E OBRIGAÇÕES',items=[
            dict(label='ENTRADAS REGISTRADAS',value=money(income),hint='Por competência, até o corte'),
            dict(label='GASTOS REGISTRADOS',value=money(spending),hint=str(sum(t['tipo']=='despesa' for t in data['transactions']))+' despesas por competência'),
            dict(label='A PAGAR · '+str(len(data['items']))+' ITENS',value=money(pending),hint='Obrigações abertas; não somar à reserva'),
            dict(label='AINDA A RECEBER',value=money(summary['a_receber']),hint='Entrada esperada, ainda não recebida')]))
        sections.append(dict(type='bars',title='ONDE ESTÃO OS GASTOS · TOP 3',items=categories[:3],empty='Sem gastos registrados nesta competência.'))
        sections.append(dict(type='notes',title='LEITURA DO MÊS',items=insights[:2]))
    elif view=='evolution':
        spec.update(layout='dashboard',title='Evolução dos registros',hero=None,cards=[],bars=[],details=[])
        spec['subtitle']='Janela até '+anchor+' · registros até '+date.fromisoformat(series[-1]['cutoff']).strftime('%d/%m/%Y')
        sections.append(dict(type='trend',title='ENTRADAS E GASTOS · ÚLTIMOS 3 MESES',items=series))
        average=round(sum(r['spending'] for r in series if not r['partial'] and r['count'])/max(1,sum(not r['partial'] and bool(r['count']) for r in series)),2)
        sections.append(dict(type='metrics',title='COMPARAÇÃO EXPLICÁVEL',items=[
            dict(label='MÉDIA DOS MESES ENCERRADOS',value=money(average) if any(not r['partial'] and r['count'] for r in series) else 'Sem base',hint='Meses com registros nesta janela'),
            dict(label='GASTOS VS. PERÍODO ANTERIOR',value=(percent(comparison['percent'],True) if comparison else 'Sem base'),hint=comparison['mode'] if comparison else 'Sem base comparável')]))
        sections.append(dict(type='notes',title='COMO LER A EVOLUÇÃO',items=[dict(title='Registro não é saldo bancário',body='Crédito segue a competência da fatura. Mês parcial tem menos dias; não compare sua barra inteira com um mês encerrado.',tone='neutral')]))
    else:
        spec.update(layout='dashboard',title='Diagnóstico do mês',hero=None,cards=[],bars=[],details=[])
        spec['subtitle']=month_label(month)+(' · projeção futura' if future else ' · posição no corte '+cutoff.strftime('%d/%m'))
        sections.append(dict(type='metrics',title='PENDÊNCIAS E COBERTURA',items=[
            dict(label='VENCIDAS NO CORTE',value=money(overdue) if not future else 'Período futuro',hint=str(len(data['overdue']))+' itens' if not future else 'Sem classificação de atraso futuro'),
            dict(label='PRÓXIMOS 7 DIAS DO CORTE',value=money(soon) if not future else 'Período futuro',hint=str(len(data['soon']))+' itens' if not future else 'Veja a agenda da competência'),
            dict(label='COBERTURA PROJETADA' if future else 'SALDO / RESERVA LÍQUIDA',value=percent(coverage) if coverage is not None else 'Não se aplica',hint='100% = reserva coberta, sem a receber'),
            dict(label='LIMITES ATINGIDOS / PRÓXIMOS',value=str(len(exceeded))+' / '+str(len(near)),hint='Próximo = de 80% a menos de 100%')]))
        sections.append(dict(type='notes',title='PRIORIDADES PARA CONFERÊNCIA',items=insights[:5]))
    spec['dashboard_sections']=sections
    spec['footer']='Registros por competência ≠ saldo bancário. A pagar e reserva não se somam. Consulte a composição antes de corrigir.'
    if view=='home':
        if summary['revisar']:spec['footer']='Há conciliações pendentes. Confira os vínculos antes de usar a previsão. A pagar e reserva não se somam.'
        elif not summary['base_configurada'] or summary['herdado_auto']:spec['footer']='Base ausente ou estimada. Confira os saldos das contas. A pagar e reserva não se somam.'
    spec['dashboard_data']=dict(comparison=comparison,coverage=coverage,pending=pending,series=series)
    if s.privacy:
        # Remove montantes, porcentagens, gráficos e diagnósticos também da especificação.
        spec['dashboard_data']={};spec['dashboard_sections']=[dict(type='notes',title='PRIVACIDADE ATIVADA',items=[dict(title='Indicadores ocultos',body='Use Mostrar no início para revelar valores e análises.',tone='neutral')])]
    return spec
