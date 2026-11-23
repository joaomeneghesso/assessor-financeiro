"""Agenda discreta com preferências persistentes e deduplicação por janela de envio."""
from telegram_design import message_html
import asyncio
import json
import secrets
import time
from datetime import date,datetime,timedelta
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
import database as db
from assessor_orientacao import preferencias,em_silencio
from telegram_execucao import executar_core

ALERT_ACTIONS={}

def controles(key,identity,snapshot,kind=None):
    """Callbacks de alerta independentes dos tokens do formulário em andamento."""
    from telegram import InlineKeyboardMarkup,InlineKeyboardButton
    now=time.monotonic()
    for token,item in list(ALERT_ACTIONS.items()):
        if item['expires']<now:ALERT_ACTIONS.pop(token,None)
    if len(ALERT_ACTIONS)>500:ALERT_ACTIONS.clear()
    items=(snapshot.get('overdue',[])+snapshot.get('soon',[]))[:3]
    rows=[]
    def button(label,action):
        token='af:'+secrets.token_urlsafe(12)
        ALERT_ACTIONS[token]={'owner':key,'identity':identity,'action':action,'expires':now+86400}
        return InlineKeyboardButton(label,callback_data=token)
    for index,item in enumerate(items,1):
        code=item.get('codigo') or item.get('chave');month=item.get('origem_mes') or snapshot['month']
        if code:rows.append([button('🔎 Ver pendência '+str(index),('detail_obligation',code,month))])
    if kind=='semana':rows.append([button('📋 Fechamento',('view','closing')),button('🔔 Atenção',('view','attention'))])
    rows += [[button('📆 Agenda',('view','agenda')),button('🏠 Início',('view','home'))],
             [button('⏰ Lembrar em 1 hora',('snooze',)),button('🔎 Já registrei: conferir',('view','history'))]]
    return InlineKeyboardMarkup(rows)

def adiar(key,identity,now):
    ident=identity+'|soneca'
    with db.get_connection() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute("SELECT 1 FROM auditoria_eventos WHERE entidade='experiencia_soneca' AND entidade_id=? LIMIT 1",(ident,)).fetchone()
        if row:return False
        db.registrar_auditoria('experiencia_soneca',ident,'adiada',dados_depois={'owner':key,'due':(now+timedelta(hours=1)).isoformat()},origem='telegram',usuario_sessao=key,conn=c);c.commit()
    return True

def sonecas(key,now,prefs):
    if not prefs['alertas'] or prefs['pausa_ate']>now.date().isoformat() or em_silencio(now.strftime('%H:%M'),prefs):return []
    with db.get_connection() as c:
        rows=c.execute("SELECT entidade_id,dados_depois FROM auditoria_eventos WHERE entidade='experiencia_soneca' AND usuario_sessao=? AND operacao='adiada' ORDER BY id DESC LIMIT 30",(key,)).fetchall()
    ready=[]
    for ident,raw in rows:
        due=datetime.fromisoformat(json.loads(raw)['due'])
        if 0<=(now-due).total_seconds()<86400:ready.append('soneca:'+ident)
    return ready

async def callback(update,context,host):
    query=update.callback_query
    if not str(query.data or '').startswith('af:'):return False
    await query.answer()
    if await host.bloquear_se_assessor_travado(update,'agenda'):return True
    import telegram_experiencia as ux
    from telegram_recursos import _resume
    key=ux.session_key(update);record=ALERT_ACTIONS.get(query.data)
    s=ux.EXPERIENCE.session(key)
    ux.EXPERIENCE.pause_for_guidance(s)
    if not record or record['owner']!=key or record['expires']<time.monotonic():
        screen=ux.Screen('Esse lembrete expirou. Abra a agenda atual para conferir suas pendências.',[[('Agenda',('view','agenda'))]])
    elif record['action'][0]=='snooze':
        ok=await executar_core(adiar,key,record['identity'],datetime.now(host.obter_timezone_alertas()))
        screen=ux.Screen('⏰ Lembrete adiado por uma hora. Horários de silêncio e pausa continuam valendo; o assessor precisa estar ligado.' if ok else 'Este lembrete já foi adiado. Nenhum segundo aviso foi agendado.',[[('📆 Agenda',('view','agenda')),('🏠 Início',('view','home'))]])
    else:
        action=record['action']
        screen=(await ux.run_experience('render',key,action[1]) if action[0]=='view'
                else await ux.run_experience('act',key,action))
    if not any(action[0] in {'resume_suspended','learning_resume'} for row in screen.rows for _,action in row):
        _resume(ux.EXPERIENCE,s,screen)
    await ux.send_screen(update,screen,host,edit=False);return True

def elegiveis(now,prefs,manhã=True,gerais=True):
    if not prefs['alertas'] or prefs['pausa_ate']>now.date().isoformat() or em_silencio(now.strftime('%H:%M'),prefs):return []
    result=[]
    for kind,hour,enabled in [('manha',prefs['hora_manha'],manhã),('semana' if now.weekday()==6 else 'noite',prefs['hora_semana'] if now.weekday()==6 else prefs['hora_noite'],gerais)]:
        target=now.replace(hour=int(hour[:2]),minute=int(hour[3:]),second=0,microsecond=0)
        # Não dispara avisos antigos ao ligar o computador horas depois.
        if enabled and 0<=(now-target).total_seconds()<180:result.append(kind)
    return result

def reservar(key,day,kind):
    identity=f'{key}|{day}|{kind}'
    with db.get_connection() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute("SELECT 1 FROM auditoria_eventos WHERE entidade='experiencia_alerta' AND entidade_id=? LIMIT 1",(identity,)).fetchone()
        if row:return None
        db.registrar_auditoria('experiencia_alerta',identity,'reservado',dados_depois={'tipo':kind},origem='telegram',usuario_sessao=key,conn=c);c.commit()
    return identity

def _valor(item):
    try:return Decimal(str(item.get('valor') or 0)).quantize(Decimal('0.01'),ROUND_HALF_UP)
    except (InvalidOperation,ValueError):return Decimal('0.00')

def _brl(total):
    return 'R$ '+f'{total:,.2f}'.replace(',','X').replace('.',',').replace('X','.')

def contagens(snapshot):
    """Conta (sem nomes) as obrigações em aberto: vencidas, de hoje, de amanhã e dos demais dias da janela.
    Vencida = data anterior ao corte; hoje = data igual ao corte (já fora de 'vencidas')."""
    try:hoje=date.fromisoformat(str(snapshot.get('cutoff') or '')[:10])
    except ValueError:hoje=None
    r={'vencidas':0,'hoje':0,'amanha':0,'proximas':0,'v_vencidas':Decimal('0'),'v_hoje':Decimal('0'),'v_amanha':Decimal('0')}
    r['vencidas']=len(snapshot.get('overdue',[]));r['v_vencidas']=sum((_valor(i) for i in snapshot.get('overdue',[])),Decimal('0'))
    for item in snapshot.get('soon',[]):
        try:d=date.fromisoformat(str(item.get('data',''))[:10])
        except ValueError:r['proximas']+=1;continue
        if hoje and d==hoje:r['hoje']+=1;r['v_hoje']+=_valor(item)
        elif hoje and d==hoje+timedelta(days=1):r['amanha']+=1;r['v_amanha']+=_valor(item)
        else:r['proximas']+=1
    return r

def _n(n,um,varios):return f'{n} {um if n==1 else varios}'

def _habito_sem_registro_hoje(snapshot):
    """Critério determinístico: o titular tem o hábito se registrou em >=3 dias distintos dos 7 dias
    anteriores a hoje (dentro do mês do retrato) e ainda não registrou nada hoje."""
    try:hoje=date.fromisoformat(str(snapshot.get('cutoff') or '')[:10])
    except ValueError:return False
    if snapshot.get('future'):return False
    dias={str(t.get('data'))[:10] for t in snapshot.get('transactions',[])}
    if hoje.isoformat() in dias:return False
    janela={(hoje-timedelta(days=n)).isoformat() for n in range(1,8)}
    return len(dias&janela)>=3

def montar_aviso(kind,snapshot,prefs=None):
    """Avisos sem nomes, contas ou descrições. Valores só com a preferência alerta_valores (padrão desligada).
    Manhã: só sai se há algo. Noite: só sai com contas vencidas/de hoje, conciliações a conferir ou
    dia sem registro para quem costuma registrar (ver _habito_sem_registro_hoje)."""
    valores=bool((prefs or {}).get('alerta_valores'))
    if kind=='semana':return '📅 Domingo: um bom momento para olhar a semana.\n\nAbra Fechamento para ver como o mês está e Atenção para os pontos que merecem conferência. Valores e detalhes ficam dentro do assessor.'
    if not snapshot:  # prévia genérica do botão de configuração
        return '🌙 Vamos fechar o dia?\n\nConfira se faltou registrar alguma entrada ou despesa. Depois, veja como ficou a previsão do mês.'
    c=contagens(snapshot);rev=len((snapshot.get('metrics') or {}).get('revisoes_conciliacao') or [])
    def v(total):return ' ('+_brl(total)+')' if valores else ''
    if kind=='manha':
        partes=[]
        if c['hoje']:partes.append(_n(c['hoje'],'conta vence hoje','contas vencem hoje')+v(c['v_hoje']))
        if c['vencidas']:partes.append(_n(c['vencidas'],'está vencida','estão vencidas')+v(c['v_vencidas']))
        if c['amanha']:partes.append(_n(c['amanha'],'vence amanhã','vencem amanhã')+v(c['v_amanha']))
        if c['proximas']:partes.append(_n(c['proximas'],'vence','vencem')+' nos próximos dias')
        if rev:partes.append(_n(rev,'conciliação para conferir','conciliações para conferir'))
        if not partes:return None
        texto='; '.join(partes)
        return '☀️ Agenda de hoje\n\n'+texto[0].upper()+texto[1:]+'.\n\nAbra o assessor para ver os detalhes.'
    habito=_habito_sem_registro_hoje(snapshot);partes=[]
    if c['hoje']+c['vencidas']:partes.append(_n(c['hoje']+c['vencidas'],'conta ainda em aberto','contas ainda em aberto')+v(c['v_hoje']+c['v_vencidas']))
    if c['amanha']:partes.append(_n(c['amanha'],'vence amanhã','vencem amanhã'))
    if rev:partes.append(_n(rev,'conciliação para conferir','conciliações para conferir'))
    if habito:partes.append('nenhum registro hoje')
    if not (c['hoje'] or c['vencidas'] or rev or habito):return None
    texto='; '.join(partes)
    return '🌙 Fechando o dia\n\n'+texto[0].upper()+texto[1:]+'.\n\nSe faltou registrar algo, ainda dá tempo. Os detalhes ficam dentro do assessor.'

async def executar_janela(application,host,now=None):
    now=now or datetime.now(host.obter_timezone_alertas())
    chat=host.obter_chat_id_alertas()
    user=host.obter_allowed_user_id()
    # O destino continua vinculado ao proprietário autorizado. Não envia para grupos.
    if chat is None or user is None or str(chat).startswith('-'):return 0
    if host.ASSESSOR_ALLOWED_CHAT_ID and str(chat)!=str(host.ASSESSOR_ALLOWED_CHAT_ID):return 0
    if not host.ASSESSOR_ALLOWED_CHAT_ID and str(chat)!=str(user):return 0
    key=f'{user}:{chat}';prefs=await executar_core(preferencias,key)
    kinds=elegiveis(now,prefs,host.ASSESSOR_LEMBRETE_PAGAMENTOS_ATIVO,host.ASSESSOR_ALERTAS_ATIVOS)
    kinds+=await executar_core(sonecas,key,now,prefs)
    if not kinds:return 0
    import telegram_experiencia as ux
    snapshot=await executar_core(_snapshot_alerta,ux,key,now)
    sent=0
    for kind in kinds:
        text=('⏰ Hora de conferir o lembrete que você adiou. Abra a pendência ou procure o registro existente; nenhum pagamento foi criado.' if kind.startswith('soneca:') else montar_aviso(kind,snapshot,prefs))
        if text is None:continue
        ident=await executar_core(reservar,key,'unico' if kind.startswith('soneca:') else now.date().isoformat(),kind)
        if ident is None:continue
        markup=controles(key,ident,snapshot,kind)
        try:
            await application.bot.send_message(chat_id=chat,text=message_html(text),reply_markup=markup, parse_mode="HTML")
            await executar_core(db.registrar_auditoria,'experiencia_alerta',ident,'enviado',origem='telegram',usuario_sessao=key);sent+=1
        except Exception:
            # Um timeout pode ter ocorrido depois da entrega. Não repetir automaticamente.
            await executar_core(db.registrar_auditoria,'experiencia_alerta',ident,'entrega_incerta',origem='telegram',usuario_sessao=key)
    return sent


def _snapshot_alerta(ux,key,now):
    from assessor_orientacao import coletar
    ui=ux.Experience(date_provider=lambda:now.date());s=ui.session(key)
    with db.read_only_mode():
        return coletar(ui,s)

async def rotina(application,host):
    while True:
        try:await executar_janela(application,host)
        except asyncio.CancelledError:raise
        except Exception:
            import logging
            logging.exception('Falha na rotina local de alertas')
        await asyncio.sleep(30)
