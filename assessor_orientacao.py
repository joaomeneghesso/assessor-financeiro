"""Orientação local explicável. Não consulta APIs, não decide pagamentos e não grava finanças."""
import calendar
import json
import os
import config
import re
import sqlite3
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
import database as db
from telegram_design import plural

DEFAULTS={'visual':True,'alertas':True,'hora_manha':'10:00','hora_noite':'22:00','hora_semana':'20:00',
          'silencio_inicio':'23:00','silencio_fim':'08:00','pausa_ate':'','ia_local':False,'alerta_valores':False,
          'ocultar_valores':False}

def normalizar(value):
    return ''.join(c for c in unicodedata.normalize('NFD',str(value).lower()) if unicodedata.category(c)!='Mn').strip()

def preferencias(key,conn=None):
    if conn is None:
        with db.get_connection() as c:return preferencias(key,c)
    row=conn.execute("SELECT dados_depois FROM auditoria_eventos WHERE entidade='experiencia_preferencia' AND entidade_id=? ORDER BY id DESC LIMIT 1",(str(key),)).fetchone()
    defaults=dict(DEFAULTS)
    for field,var in [('hora_manha','ASSESSOR_LEMBRETE_PAGAMENTOS_HORA'),('hora_noite','ASSESSOR_ALERTA_DIARIO_HORA'),('hora_semana','ASSESSOR_RESUMO_DOMINGO_HORA')]:
        value=config.ler(var,'').strip()
        if re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',value):defaults[field]=value
    return dict(defaults,**(json.loads(row[0]) if row else {}))

def salvar_preferencia(key,field,value):
    return salvar_preferencias(key,{field:value})

def validar_preferencia(field,value):
    if field not in DEFAULTS:raise ValueError('Preferência desconhecida.')
    if field in {'visual','alertas','ia_local','alerta_valores','ocultar_valores'} and not isinstance(value,bool):raise ValueError('Use ativado ou desativado.')
    if field.startswith('hora_') or field.startswith('silencio_'):
        if not isinstance(value,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',value):raise ValueError('Informe HH:MM, entre 00:00 e 23:59.')
    if field=='pausa_ate' and value:date.fromisoformat(value)

def salvar_preferencias(key,changes):
    for field,value in changes.items():validar_preferencia(field,value)
    with db.get_connection() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute("SELECT dados_depois FROM auditoria_eventos WHERE entidade='experiencia_preferencia' AND entidade_id=? ORDER BY id DESC LIMIT 1",(str(key),)).fetchone()
        old=json.loads(row[0]) if row else {};new=dict(old,**changes)
        db.registrar_auditoria('experiencia_preferencia',key,'alteracao',old,new,'telegram',key,conn=c)
        c.commit()
    return preferencias(key)

def configurar_saldo(key,month,amount,expected):
    """Mesmo saldo inicial do motor, com prévia otimista e auditoria na mesma transação."""
    import math
    date.fromisoformat(month+'-01')
    if not math.isfinite(amount) or abs(amount)>100000000:raise ValueError('Saldo fora do intervalo permitido.')
    stamp=datetime.now().isoformat(timespec='seconds')
    with db.get_connection() as c:
        c.row_factory=sqlite3.Row;c.execute('BEGIN IMMEDIATE')
        raw=c.execute('SELECT * FROM saldos_mensais WHERE ano_mes=?',(month,)).fetchone()
        current=dict(raw) if raw else None
        if current!=expected:raise ValueError('O saldo foi alterado desde a prévia. Confira novamente.')
        bases=c.execute('SELECT saldo_inicial FROM saldos_mensais_contas WHERE ano_mes=?',(month,)).fetchall()
        if bases and abs(sum(float(row[0]) for row in bases)-amount)>0.005:
            raise ValueError('Este mês usa saldos por conta. Use Ajustar saldo atual para atualizar o dinheiro de cada banco e a previsão.')
        if current:c.execute('UPDATE saldos_mensais SET saldo_inicial=?,observacao=?,atualizado_em=? WHERE ano_mes=?',(amount,'Configurado pela prévia Telegram',stamp,month))
        else:c.execute('INSERT INTO saldos_mensais (ano_mes,saldo_inicial,observacao,criado_em,atualizado_em) VALUES (?,?,?,?,?)',(month,amount,'Configurado pela prévia Telegram',stamp,stamp))
        db.registrar_auditoria('saldo_mensal',month,'configurado_rc3',current,{'saldo_inicial':amount},'telegram',key,conn=c)
        c.commit()

def em_silencio(hora,prefs):
    ini,fim=prefs['silencio_inicio'],prefs['silencio_fim']
    if ini==fim:return False
    return ini<=hora<fim if ini<fim else hora>=ini or hora<fim

def mes_anterior(month,offset=1):
    y,m=map(int,month.split('-'));y,m=divmod(y*12+m-1-offset,12)
    if y<1:return None
    return f'{y:04d}-{m+1:02d}'

def coletar(exp,s):
    """Um retrato por renderização, obtido do motor RC2 sem fórmulas de saldo paralelas."""
    if getattr(exp,'_retrato',None) is not None:return exp._retrato
    import services as svc
    m=svc.obter_metricas_resultado_mes(s.month)
    y,mo=map(int,s.month.split('-'));fim=date(y,mo,calendar.monthrange(y,mo)[1])
    hoje=exp.date_provider();corte=min(hoje,fim);futuro=s.month>hoje.strftime('%Y-%m')
    tx=[t for t in exp.transactions(s.month) if t['data']<=corte.isoformat()] if not futuro else []
    items=exp.obligations(s.month)
    cats=defaultdict(float);days=defaultdict(float)
    for t in tx:
        if t['tipo']=='despesa':cats[t['categoria']]+=float(t['valor']);days[t['data']]+=float(t['valor'])
    budgets=[]
    for raw in db.listar_metas():
        meta=dict(raw);limit=float(meta['valor'])
        if limit<=0:continue
        spent=sum(v for k,v in cats.items() if normalizar(k)==normalizar(meta['categoria']))
        budgets.append(dict(category=meta['categoria'],limit=limit,spent=round(spent,2),ratio=spent/limit,remaining=round(limit-spent,2)))
    overdue=[];soon=[];unknown=[]
    for item in items:
        try:d=date.fromisoformat(str(item.get('data',''))[:10])
        except ValueError:unknown.append(item);continue
        if d<corte:overdue.append(item)
        elif 0<=(d-corte).days<=7:soon.append(item)
    # B7: no mês real, a janela de 7 dias pode atravessar a virada do mês
    # (ex.: 31/12 → 07/01). Entram só as obrigações PRÓPRIAS do mês seguinte
    # dentro da janela; pendências antigas já estão em items. Os totais do mês
    # (items) não mudam: esses itens ficam apenas em soon/soon_next_month.
    soon_next=[]
    if not futuro and s.month==hoje.strftime('%Y-%m') and corte+timedelta(days=7)>fim:
        limite=corte+timedelta(days=7);prox=f'{limite.year:04d}-{limite.month:02d}'
        vistos={(i.get('origem_mes'),i.get('chave') or i.get('codigo_origem') or i.get('codigo')) for i in items}
        for item in exp.obligations(prox):
            ident=(item.get('origem_mes'),item.get('chave') or item.get('codigo_origem') or item.get('codigo'))
            if item.get('origem_mes')!=prox or ident in vistos:continue
            try:d=date.fromisoformat(str(item.get('data',''))[:10])
            except ValueError:continue
            if fim<d<=limite:soon_next.append(item);vistos.add(ident)
        soon+=soon_next
    income=sum(float(t['valor']) for t in tx if t['tipo']=='receita');spending=sum(cats.values())
    recent=[]
    with db.get_connection() as conn:
        conn.row_factory=sqlite3.Row
        prev=mes_anterior(s.month,3)
        if prev:recent=[dict(r) for r in conn.execute('SELECT * FROM transacoes WHERE data>=? AND data<? ORDER BY data,id',(prev+'-01',s.month+'-01'))]
    recurring=[];groups=defaultdict(list)
    for t in recent+tx:
        if t['tipo']=='despesa' and int(t.get('parcelas_total') or 1)==1:
            groups[(normalizar(t['descricao']),normalizar(t['conta']))].append(t)
    for _,group in groups.items():
        months={t['data'][:7] for t in group}
        if len(months)<3 or not any(t['data'][:7]==s.month for t in group):continue
        if len(group)!=len(months):continue  # Várias compras por mês não provam assinatura.
        amounts=[float(t['valor']) for t in group];mean=sum(amounts)/len(amounts)
        if mean>0 and max(abs(v-mean)/mean for v in amounts)<=.08:
            recurring.append(dict(name=group[-1]['descricao'],average=round(mean,2),months=len(months),ids=[t['id'] for t in group]))
    insights=[]
    def add(code,title,detail,view,priority):insights.append(dict(code=code,title=title,detail=detail,view=view,priority=priority))
    if not m.get('saldo_configurado'):add('base','Falta informar o saldo inicial','Complete a base antes de usar a previsão para decidir uma compra.','setup',0)
    if m.get('revisoes_conciliacao'):add('review','Confira as conciliações',f'{plural(len(m["revisoes_conciliacao"]), "situação", "situações")} {"impede" if len(m["revisoes_conciliacao"]) == 1 else "impedem"} usar a sobra com confiança.','review',0)
    if not futuro and overdue:add('overdue','Comece pelas contas vencidas',f'{plural(len(overdue), "compromisso")} com data anterior ao corte. Confirme se já foram pagos antes de lançar outra saída.','pay',1)
    if m.get('saldo_configurado') and m['saldo_projetado']<0:add('deficit','A previsão termina negativa','Revise as obrigações e as entradas esperadas antes de assumir outra despesa.','balance',1)
    if not futuro and soon:add('soon','Prepare os próximos sete dias',f'{plural(len(soon), "compromisso")} no período. Abra a agenda para conferir datas e contas.','agenda',2)
    exceeded=[b for b in budgets if b['ratio']>=1]
    if exceeded:add('budget','Um limite de gastos foi alcançado',f'{plural(len(exceeded), "categoria")} {"chegou" if len(exceeded) == 1 else "chegaram"} ao limite. Confira os lançamentos que compõem o valor.','budgets',2)
    near=[b for b in budgets if .8<=b['ratio']<1]
    if near:add('near','Acompanhe limites próximos',f'{plural(len(near), "categoria")} {"consumiu" if len(near) == 1 else "consumiram"} pelo menos 80% do limite informado.','budgets',3)
    if recurring:add('recurring','Revise pagamentos que se repetem',f'{plural(len(recurring), "padrão", "padrões")} em pelo menos três meses. São sugestões de revisão, não assinaturas confirmadas.','recurring',4)
    if tx and not any(t['data']==hoje.isoformat() for t in tx) and not futuro and s.month==hoje.strftime('%Y-%m'):
        add('today','Seu dia está atualizado?','Não há movimento registrado hoje. Isso pode ser normal; confira se ficou algo de fora.','register',5)
    if not insights:add('check','Mantenha os registros completos','Não encontrei esses sinais de atenção. Isso não comprova que todo o seu dinheiro está registrado.','history',6)
    result=dict(month=s.month,metrics=m,transactions=tx,items=items,categories=sorted(cats.items(),key=lambda x:x[1],reverse=True),days=sorted(days.items()),
                budgets=budgets,overdue=overdue,soon=soon,unknown=unknown,income=income,spending=spending,recurring=recurring,
                insights=sorted(insights,key=lambda x:x['priority']),cutoff=corte.isoformat(),future=futuro,
                soon_next_month=soon_next)
    if getattr(exp,'_em_render',False):exp._retrato=result
    return result

TOPICS={
 'primeiros':('Começar em três passos','Confira sua base, registre movimentos reais e acompanhe previsões sem misturar os dois.','setup'),
 'registrar':('Registrar sem se perder','Informe valor, conta, forma e data. No crédito, parcelamento e competência da fatura são revisados antes de salvar.','register'),
 'compromissos':('Fixos, parcelas e previsões','Fixos se repetem, parcelamentos terminam e entradas previstas só viram realizado quando o dinheiro entra.','pay'),
 'pagar':('Pagar e dar baixa','A pagar → detalhe → pagamento. Se a saída já existe, vincule pelo Histórico para evitar duplicidade.','pay'),
 'receber':('Receber uma entrada prevista','A receber → Registrar recebimento. Se já entrou no Histórico, vincule aquele lançamento.','receivables'),
 'faturas':('Compra no cartão e fatura','Data da compra e competência da fatura são distintas. A partir do dia 25, compras no crédito podem ser direcionadas à fatura atual ou à próxima.','pay'),
 'transferencias':('Transferir entre contas próprias','Transferência move caixa entre contas sem virar receita ou despesa.','balance'),
 'saldo':('Entender caixa e projeção','Disponível é caixa realizado; A pagar são obrigações; Sobra é projeção. Crédito não reduz o caixa na compra.','balance'),
 'historico':('Histórico e rastreabilidade','Localize movimentos, confira detalhes e só então corrija, exclua ou vincule.','history'),
 'analisar':('Análises e auditoria','Use análises, atenção e fechamento para investigar números sem alterar registros.','analytics'),
 'corrigir':('Corrigir com rastreabilidade','Abra o Histórico. Movimentos vinculados podem exigir desvinculação antes de alterações financeiras.','history'),
 'conciliar':('Ligar previsão ao realizado','Conciliação evita contar a previsão e o movimento real duas vezes.','reconciliations'),
 'planejar':('Planejar sem gravar hipótese','Limites, plano, simulação e recorrências ajudam a decidir sem criar movimentos realizados.','plan'),
 'limites':('Planejar um limite','Defina quanto pretende gastar em uma categoria e acompanhe o realizado.','budgets'),
 'alertas':('Alertas e vencimentos','Configure horários e pausa. Alertas não registram pagamentos nem alteram valores.','alerts'),
 'controle':('Fechamento e atenção','Atenção mostra sinais objetivos; Fechamento resume o mês sem alterar registros.','closing'),
 'ia':('Interpretação inteligente e local','Ollama interpreta intenção; regras e cálculos determinísticos continuam sendo a fonte financeira.','assistant'),
 'dados':('Backup, importação, exportação e segurança','Backup recupera estado; exportação não o substitui. Importe só após revisar a prévia.','more'),
 'backup':('Guardar e recuperar','Faça backup completo de código e banco. CSV não substitui recuperação completa.','more'),
 'exportar':('Exportar seus registros','Exportação serve para consulta/transporte e não altera o banco.','more'),
 'privacidade':('Proteger seus dados','PIN controla acesso ao assessor; ocultar valores não apaga mensagens antigas do Telegram.','more'),
}


def reconhecer_pergunta(text):
    t=normalizar(text)
    if len(t)>600:return None
    rules=[('receivables',r'quanto.*receber|o que.*receber|entradas previstas|salario.*cai'),
           ('pay',r'quanto.*pagar|o que.*pagar|contas.*venc|contas a pagar|dividas|pendencias'),
           ('agenda',r'proximos.*dias|agenda|vence.*semana'),
           ('balance',r'quanto.*tenho|saldo|quanto.*sobr|dinheiro.*disponivel'),
           ('analytics',r'onde.*gast|quanto.*gast|gastos?.*(?:com|em)|.*pesando.*|meus gastos|gastei mais|analis|para onde.*(?:(?:dinheiro|grana).*(?:indo|vai)|(?:indo|vai).*(?:dinheiro|grana))|(?:dinheiro|grana).*(?:indo|vai)|(?:com|no).*que.*gast|maiores gastos|entender.*gastos|enxergar.*gastos|consumindo.*(?:dinheiro|grana)|(?:dinheiro|grana).*(?:acabando|sumindo)|organizar.*gastos'),
           ('recurring',r'assinaturas|recorrentes|se repet'),('budgets',r'limites|orcamento|economizar'),
           ('review',r'duplicad|concili|erro.*valor'),('alerts',r'alerta|notific|lembret'),
           ('attention',r'o que.*(?:merece|precisa).*atenc|preciso.*(?:me preocupar|conferir)|central.*atenc|atencao'),
           ('closing',r'fechamento.*mes|fechar.*mes|como.*fechou|resultado.*mes'),
           ('home',r'meu mes|como.*mes|resumo|dashboard'),('help',r'ajuda|como.*funciona')]
    hits=[view for view,regex in rules if re.search(regex,t)]
    return hits[0] if len(set(hits))==1 else None


# ---------------------------------------------------------------------------
# Fase 2 (B4/B5/B7): leitura pura, sem gravação, dinheiro sempre em Decimal.
# ---------------------------------------------------------------------------
from decimal import Decimal
from money import parse_money

CENTAVO=Decimal('0.01')
ZERO=Decimal('0')

def _dec(value):
    return parse_money(value,allow_negative=True)

def barra(ratio,largura=10):
    """Barra de progresso ▰▱. Passar de 100% enche a barra; >0% mostra ao menos 1 bloco."""
    r=max(0.0,float(ratio));cheios=min(largura,int(r*largura+0.5))
    if r>0 and cheios==0:cheios=1
    return '▰'*cheios+'▱'*(largura-cheios)

def situacao_limites(metas,transacoes,hoje,mes):
    """B5: gasto, ritmo e margem diária por limite. Não consulta nem grava nada.

    ritmo (projeção de fechamento) só existe no mês vigente, com >=5 dias e >=3
    lançamentos na categoria; sem base suficiente fica None (não inventa).
    """
    y,m=map(int,mes.split('-'));dias_mes=calendar.monthrange(y,m)[1]
    vigente=mes==hoje.strftime('%Y-%m')
    dia=hoje.day if vigente else 0
    itens=[]
    for raw in metas:
        meta=dict(raw);limite=_dec(meta['valor'])
        if limite<=0:continue
        alvo=normalizar(meta['categoria'])
        mine=[t for t in transacoes if t['tipo']=='despesa' and normalizar(t['categoria'])==alvo]
        gasto=sum((_dec(t['valor']) for t in mine),ZERO)
        ratio=gasto/limite
        esperado=ritmo=por_dia=None
        if vigente:
            esperado=(limite*dia/dias_mes).quantize(CENTAVO)
            if dia>=5 and len(mine)>=3:ritmo=(gasto/dia*dias_mes).quantize(CENTAVO)
            if gasto<limite:por_dia=((limite-gasto)/(dias_mes-dia+1)).quantize(CENTAVO)
        if gasto>=limite:estado='estourou'
        elif ritmo is not None and ritmo>limite:estado='ritmo'
        elif ratio>=Decimal('0.8'):estado='perto'
        else:estado='ok'
        evento=None
        if gasto>limite and mine:
            maior=max(mine,key=lambda t:_dec(t['valor']))
            if _dec(maior['valor'])>gasto-limite:evento=(_dec(maior['valor']),str(maior.get('descricao') or ''),len(mine))
        itens.append(dict(categoria=meta['categoria'],limite=limite,gasto=gasto,ratio=ratio,restante=limite-gasto,
                          lancamentos=len(mine),esperado=esperado,ritmo=ritmo,por_dia=por_dia,estado=estado,
                          evento=evento,dia=dia,dias_mes=dias_mes,vigente=vigente))
    return sorted(itens,key=lambda i:i['ratio'],reverse=True)

_COMPRA_INICIO=re.compile(r'^(?:posso|consigo|da pra|vale a pena)\s+comprar\b')

def eh_pergunta_compra(text):
    return bool(_COMPRA_INICIO.match(normalizar(text)))

def extrair_pergunta_compra(text):
    """'posso comprar um celular de 3000 em 10x' -> dict(total_centavos, parcelas, descricao, credito); None sem valor."""
    t=normalizar(text).replace('?',' ');t=_COMPRA_INICIO.sub('',t,count=1).strip()
    por_parcela=re.search(r'(\d{1,2})\s*x\s*de\s*(?:r\$\s*)?(\d[\d.]*(?:,\d{1,2})?)',t)
    parcelas=None;total=None
    if por_parcela:
        parcelas=int(por_parcela[1])
        try:total=_dec(por_parcela[2])*parcelas
        except ValueError:return None
        antes=t[:por_parcela.start()]
    else:
        achou=re.search(r'(?:em\s+)?(\d{1,2})\s*(?:x|vezes|parcelas?)\b',t)
        if achou:parcelas=int(achou[1]);t=t.replace(achou[0],' ')
        achou=re.search(r'(?:r\$\s*)?(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)\s*(k|mil)?\b',t)
        if not achou:return None
        try:total=_dec(achou[1])
        except ValueError:return None
        if achou[2]:total*=1000
        antes=t[:achou.start()]
    if total<=0:return None
    credito=bool(re.search(r'credito|cartao',t)) or (parcelas or 1)>1
    if parcelas is None:parcelas=1
    if not 1<=parcelas<=48:return None
    palavras=[w for w in re.sub(r'[^a-z0-9 ]',' ',antes).split() if w not in {'um','uma','o','a','de','do','da','por','que','no','na','em','r','reais','real'}]
    return dict(total_centavos=int((total*100).to_integral_value()),parcelas=parcelas,
                descricao=' '.join(palavras[:4]) or 'compra',credito=credito)

def _somar_mes(mes,n):
    y,m=map(int,mes.split('-'));y,m=divmod(y*12+m-1+n,12);return f'{y:04d}-{m+1:02d}'

def simular_compra(total_centavos,parcelas,primeiro_mes,max_meses=6):
    """B7: 'Deve sobrar' antes e depois da compra, com o motor canônico (resumir_saldo).

    Antes = saldo_final do mês (o mesmo número do Início). Depois = antes − parcela do mês,
    em memória: nada é gravado. Em meses com saldo herdado (estimado) as parcelas anteriores também descontam.
    """
    import services as svc
    from saldo_resumo import resumir_saldo
    n=max(1,int(parcelas));base,resto=divmod(int(total_centavos),n)
    meses=[];acumulado=ZERO
    with db.read_only_mode(),svc.contexto_consulta():
        for i in range(min(n,max_meses)):
            mes=_somar_mes(primeiro_mes,i);parcela=Decimal(base+(1 if i<resto else 0))/100
            antes=None;revisar=False;estimado=False;herdado=False
            try:
                resumo=resumir_saldo(svc.obter_metricas_resultado_mes(mes))
                if resumo['base_configurada'] or resumo['herdado_auto']:antes=_dec(resumo['saldo_final'])
                revisar=resumo['revisar'];herdado=resumo['herdado_auto'];estimado=herdado or not resumo['base_configurada']
            except Exception:
                pass  # mês sem base calculável: segue sem número, nunca inventa
            # Mês com saldo herdado carrega a previsão do anterior: as parcelas já pagas também o reduzem.
            acumulado=acumulado+parcela if herdado else parcela
            meses.append(dict(mes=mes,parcela=parcela,antes=antes,depois=None if antes is None else antes-acumulado,
                              revisar=revisar,estimado=estimado,acumulado=acumulado))
    validos=[x for x in meses if x['antes'] is not None and not x['revisar']]
    apertado=min(validos,key=lambda x:x['depois']) if validos else None
    return dict(meses=meses,apertado=apertado,total=Decimal(int(total_centavos))/100,parcelas=n,
                omitidas=max(0,n-len(meses)))

def veredito_compra(sim):
    """Leitura descritiva (nunca recomendação): dict(tom, emoji, mes, valor, pct)."""
    meses=sim['meses']
    if not meses or meses[0]['revisar']:return dict(tom='revisar',emoji='⚪')
    apertado=sim['apertado']
    if apertado is None:return dict(tom='sem_base',emoji='⚪')
    if apertado['depois']<0:return dict(tom='negativo',emoji='🔴',mes=apertado['mes'],valor=apertado['depois'],ja_negativo=apertado['antes']<0)
    primeiro=next((x for x in meses if x['antes'] is not None and not x['revisar']),None)
    if primeiro and primeiro['antes']>0:
        parte=primeiro['parcela']/primeiro['antes']
        if parte>=Decimal('0.5'):return dict(tom='aperta',emoji='🟡',mes=primeiro['mes'],pct=float(parte*100))
    return dict(tom='cabe',emoji='🟢',mes=apertado['mes'],valor=apertado['depois'])
