"""Recursos de leitura e aprendizado; nenhum pagamento é confirmado aqui."""
import copy
import os
import config
import re
from contextvars import ContextVar
from datetime import date
from html import escape
from urllib.parse import urlparse
import database as db
import services as svc
from saldo_resumo import resumir_saldo
from telegram_design import rich_table

CURRENT_THREAD=ContextVar('assessor_thread',default=None)

class TopicPending(dict):
    """Mantém as chaves legadas no chat principal e isola pendências nos tópicos."""
    def _key(self,key):
        topic=CURRENT_THREAD.get()
        return (key,topic) if topic is not None and not isinstance(key,tuple) else key
    def __setitem__(self,key,value):return super().__setitem__(self._key(key),value)
    def __getitem__(self,key):return super().__getitem__(self._key(key))
    def __contains__(self,key):return super().__contains__(self._key(key))
    def get(self,key,default=None):return super().get(self._key(key),default)
    def pop(self,key,default=None):return super().pop(self._key(key),default)

def scope_update(update):CURRENT_THREAD.set(thread_id(update))

QUIZZES = {
 'primeiros':('Ao ajustar saldo, qual valor informar?',('Dinheiro disponível agora','Saldo do primeiro dia do mês'),0,'Ajustar saldo atual usa o dinheiro disponível agora e deriva a base sem criar receita.'),
 'lancamentos':('Um gasto já está no Histórico. O que fazer?',('Registrar novamente','Conferir o registro existente'),1,'Um novo registro criaria outra movimentação. Confira o existente antes de corrigir.'),
 'faturas':('Comprar no crédito reduz o saldo bancário imediatamente?',('Sim','Não'),1,'A compra compõe a fatura. A saída bancária acontece no pagamento da fatura.'),
 'caixa':('Saldo 1.000 + a receber 200 − reserva 300. Qual a previsão?',('900','1.200'),0,'A previsão é 900; o dinheiro disponível continua sendo 1.000 até as movimentações acontecerem.'),
 'transferencias':('Transferir entre suas contas aumenta seu dinheiro total?',('Sim','Não'),1,'A origem diminui e o destino aumenta. O total é preservado.'),
 'previsoes':('Alterar um fixo a partir de outubro deve preservar setembro?',('Sim','Não'),0,'A versão anterior mantém sua vigência. A nova condição vale a partir do mês escolhido.'),
 'meu mes':('Sobra prevista é dinheiro já recebido?',('Sim','Não'),1,'É uma projeção que considera dinheiro disponível, entradas previstas e reservas.'),
 'compromissos':('Uma fatura quitada deve receber outra baixa?',('Sim','Não; conferir os registros'),1,'Confira o pagamento e seu vínculo. Uma nova baixa pode duplicar a saída.'),
 'checklist':('Um alerta de vencimento comprova pagamento?',('Sim','Não'),1,'Alertas orientam a conferência. Eles não movimentam dinheiro.'),
 'conciliacao':('O pagamento já foi registrado. Como ligar à previsão?',('Criar outra despesa','Vincular o lançamento existente'),1,'O vínculo relaciona previsão e realização sem criar outra despesa.'),
 'planejamento':('Uma simulação salva uma compra realizada?',('Sim','Não'),1,'Simular estima o impacto. Registrar uma compra é uma ação diferente, com confirmação.'),
 'auditoria':('Um saldo surpreendeu. Qual o primeiro passo?',('Ajustar sem investigar','Ver a composição e o Histórico'),1,'Descubra conta, data, competência e origem antes de corrigir.'),
 'dados':('Exportar CSV substitui a cópia de recuperação?',('Sim','Não'),1,'CSV é uma consulta. O backup guarda o banco para recuperação.'),
 'caju':('Gastos pagos com Caju devem sair de qual conta?',('Caju','Qualquer banco'),0,'A conta representa de onde o dinheiro saiu; a forma é informada separadamente.'),
 'rotina':('Na virada do mês, qual conferência ajuda?',('Saldo e faturas da nova competência','Repetir os pagamentos anteriores'),0,'Confira a competência e o saldo disponível; pagamentos anteriores não devem ser repetidos.'),
}

def deep_action(payload):
    if not payload or len(payload)>64:return None
    if payload in {'inicio','ajuda','aprender','dashboard','pagar','historico','contas'}:
        return {'inicio':('view','home'),'ajuda':('view','help'),'aprender':('view','learn'),
                'dashboard':('chart','home'),'pagar':('view','pay'),'historico':('view','history'),
                'contas':('cash_accounts',date.today().strftime('%Y-%m'))}[payload]
    if payload.startswith('aula_') and payload[5:] in QUIZZES:return ('lesson',payload[5:])
    match=re.fullmatch(r'fatura_([a-z0-9_]{1,32})_(\d{4}-\d{2})',payload)
    if match:
        date.fromisoformat(match[2]+'-01')
        return ('detail_obligation','B_'+match[1],match[2])
    return None

def rich_summary(title,summary,details):
    return '<h2>'+escape(title)+'</h2><p>'+summary.replace('\n','<br>')+'</p><details><summary>Ver composição e orientação</summary><p>'+details.replace('\n','<br>')+'</p></details>'

def dispatch(engine,key,action):
    from telegram_experiencia import Screen,heading,money,month_label,safe
    s=engine.session(key);kind=action[0]
    if kind=='invoice_origin':
        engine.pause_for_guidance(s);code,month=action[1:3];page=int(action[3]) if len(action)>3 else 0
        date.fromisoformat(month+'-01')
        with db.read_only_mode(),svc.contexto_consulta():
            _,item=svc.resolver_item_checklist(month,code)
            if not item or item.get('grupo')!='bancos':raise ValueError('Escolha a fatura em A pagar.')
            account=item.get('conta') or item.get('conta_pagamento') or item['nome']
            r=svc.calcular_resumo_fatura(month,account)
        show=lambda v:'••••' if s.privacy else money(v)
        title='Composição da fatura · '+str(r['conta_cartao'])
        lines=[heading(title,month_label(month)),'',
          'Valor bruto · '+show(r['valor_bruto']),
          '− Crédito herdado · '+show(r.get('credito_herdado',0)),
          '− Créditos e estornos · '+show(r['creditos']),
          '− Pagamentos · '+show(r['pagamentos']),
          '+ Ajustes de débito · '+show(r['ajustes_debito']),
          '+ Conferência no banco · '+show(r.get('ajuste_conferencia',0)),
          '<b>Saldo restante · '+show(r['saldo_restante'])+'</b>','',
          'A composição usa a competência da fatura. Fixos no crédito já estão incluídos. Pagamentos registrados não devem ser repetidos.']
        # R6: exibe a data real da compra; a data da competência fica só no cálculo.
        entries=[(str(i.get('data_compra') or i.get('data') or ''),str(i.get('nome') or 'Compra'),float(i.get('valor') or 0)) for i in r['itens']]
        entries += [(str(i.get('data_movimento') or ''),'#F'+str(i['id'])+' · '+str(i['tipo_movimento']).replace('_',' '),float(i['valor'])) for i in r['movimentos']]
        pages=max(1,(len(entries)+4)//5);page=max(0,min(page,pages-1));visible=entries[page*5:page*5+5]
        lines+=['','<b>Compras e movimentos · página '+str(page+1)+'/'+str(pages)+'</b>']
        for day,name,amount in visible:lines+=[safe(day,10)+' · '+safe(name,60)+' · '+show(amount)]
        if not visible:lines+=['Sem compras ou movimentos nesta competência.']
        rows=[]
        if pages>1:
            rows.append([('‹ Anteriores',('invoice_origin',code,month,max(0,page-1))),('Próximos ›',('invoice_origin',code,month,min(pages-1,page+1)))])
        rows+=[[('🧾 Voltar à fatura',('detail_obligation',code,month)),('🔎 Histórico',('view','history'))]]
        screen=Screen('\n'.join(lines),rows)
        table=rich_table(
            ('Data', 'Origem', 'Valor'),
            [(day, name, show(amount)) for day, name, amount in visible],
            aligns=('left', 'left', 'right'),
        )
        screen.rich_html='<h2>'+safe(title)+'</h2><p>'+month_label(month)+'<br>'+'<br>'.join(lines[2:9])+'</p><details><summary>Compras e movimentos · página '+str(page+1)+'/'+str(pages)+'</summary>'+table+'</details><p>'+safe(lines[10])+'</p>'
        _resume(engine,s,screen);return screen
    if kind=='origin':
        engine.pause_for_guidance(s)
        field=action[1]
        if field not in {'saldo','reserva','previsao','fatura'}:raise ValueError('Indicador desconhecido.')
        with db.read_only_mode(),svc.contexto_consulta():
            m=svc.obter_metricas_resultado_mes(s.month);summary=resumir_saldo(m)
            show=lambda value:'••••' if s.privacy else money(value)
            titles={'saldo':'De onde vem meu saldo','reserva':'De onde vem a reserva','previsao':'Como chega à sobra prevista','fatura':'De onde vem a fatura'}
            text=[heading(titles[field],month_label(s.month)),'',
                  '🏦 Saldo disponível · <b>'+show(summary['saldo_atual'])+'</b>',
                  '↗ Ainda a receber · <b>'+show(summary['a_receber'])+'</b>',
                  '🧾 Reservas líquidas · <b>'+show(summary['reservas_liquidas'])+'</b>',
                  '🎯 Previsão · <b>'+('Revisar conciliação' if summary['revisar'] else show(summary['saldo_final']))+'</b>',
                  '', 'Saldo disponível + a receber − reservas líquidas.']
            if field=='saldo':
                text+=['','<b>Movimentos que formam o caixa</b>',
                       'Base do mês · '+show(m['saldo_inicial']),
                       'Entradas recebidas · '+show(m['entradas_realizadas']),
                       'Saídas imediatas · '+show(m['saidas_imediatas_realizadas']),
                       '', 'O ajuste de saldo atual informa o dinheiro que está no banco agora. Pagamentos já incluídos nesse valor não são descontados novamente.']
            elif field=='reserva':
                text+=['','<b>Componentes do motor</b>',
                       'Crédito lançado · '+show(m.get('saidas_nao_imediatas_realizadas',0)),
                       'Despesas ainda esperadas · '+show(m.get('despesas_esperadas_total',0)),
                       'Pendências herdadas · '+show(m.get('pendencias_herdadas_total',0)),
                       '− Compensação de faturas pagas · '+show(m.get('compensacao_pagamentos_fatura',0)),
                       '− Ajuste da reserva por cartão · '+show(m.get('ajuste_reserva_faturas',0))]
                text+=['','<b>Por que reserva e A pagar podem ser diferentes?</b>',
                       'A reserva pertence à previsão e incorpora compensações do motor. A pagar lista obrigações abertas. Não some os dois indicadores.',
                       'Fixos no crédito compõem a fatura. Pix, débito e transferência têm baixa própria. Cada cartão é conferido separadamente.']
            else:text+=['','A previsão inclui entradas ainda esperadas e pendências da competência. Meses futuros são projeções, não dinheiro recebido.']
            if summary['revisar']:text+=['','⚠️ Há conciliações que precisam de revisão.']
            if not summary['base_configurada'] or summary['herdado_auto']:text+=['','⚠️ Confira a base em Ajustar saldo atual.']
        detail='\n'.join(text[7:]);screen=Screen('\n'.join(text),[
          [('🏦 Ver por conta',('cash_accounts',s.month)),('🧾 Obrigações',('view','pay'))],
          [('🔎 Histórico',('view','history')),('↗ A receber',('view','receivables'))],
          [('🧮 Memória do cálculo',('view','balance_details')),('🏠 Início',('view','home'))]])
        screen.rich_html=rich_summary(titles[field],'\n'.join(text[2:7]),detail)
        _resume(engine,s,screen);return screen
    if kind in {'quiz','quiz_answer'}:
        engine.pause_for_guidance(s);lesson=action[1]
        if lesson not in QUIZZES:raise ValueError('Escolha uma aula válida.')
        question,options,correct,explanation=QUIZZES[lesson]
        rows=[];lines=['<b>🎯 Teste seu entendimento</b>','',safe(question)]
        if kind=='quiz_answer':
            choice=int(action[2])
            if not 0<=choice<len(options):raise ValueError('Resposta inválida.')
            lines+=['','✅ Isso mesmo!' if choice==correct else '💡 Vamos conferir juntos.',safe(explanation),
                    '', '<i>Exercício ilustrativo. Nenhum dado financeiro foi alterado.</i>']
        else:rows=[[(safe(option),('quiz_answer',lesson,i))] for i,option in enumerate(options)]
        rows += [[('📚 Voltar à aula',('lesson',lesson)),('Escolher aula',('view','learn_topics'))]]
        screen=Screen('\n'.join(lines),rows);_resume(engine,s,screen);return screen
    if kind=='innovations':
        engine.pause_for_guidance(s)
        screen=Screen('<b>✨ Mais facilidade no assessor</b>\n\n'
          '🔎 Confira a origem dos valores.\n🎓 Pratique com exercícios das aulas.\n'
          '🎙 Envie áudio ou foto para montar um rascunho conferível.\n'
          '📊 Digite painel (ou /dashboard) para conferir o mês.'+
          '\n\nToda movimentação continua passando pela prévia e confirmação.',[
          [('🔎 Origem dos valores',('origin','previsao')),('🎓 Exercícios',('quiz','primeiros'))],
          [('🎙 Áudio e comprovantes',('media_help',)),('📊 Painel',('chart','home'))],
          [('💡 Ajuda',('view','help')),('🏠 Início',('view','home'))]])
        _resume(engine,s,screen);return screen
    if kind=='media_help':
        return Screen('<b>🎙 Áudio e comprovantes</b>\n\nEnvie uma mensagem de voz ou uma foto legível. '
          'O assessor mostra o texto reconhecido e pede o tipo da movimentação. '
          'Valor, data, conta e forma precisam ser conferidos.\n\n'
          'Comprovante de fatura deve seguir Pagar fatura. Transferência entre suas contas segue Transferências. '
          'Ambiguidades exigem preenchimento; nenhum arquivo confirma uma saída sozinho.',[
          [('➕ Registrar por etapas',('view','register')),('✨ Recursos',('innovations',))]])
    if kind=='topics_setup':
        return Screen('Essa opção foi retirada da versão sem cobranças. Use o menu habitual para acessar as ferramentas.',[[('✨ Recursos',('innovations',))]])
    return None

def _resume(engine,s,screen):
    row=engine._draft_pause_row(s)
    if row:screen.rows.append(row)
    if s.learning_stage and (s.fixed_edit or s.new_fixed):screen.rows.append([('↩ Retomar cadastro',('learning_resume',))])

def thread_id(update):
    message=getattr(update,'effective_message',None) or getattr(update,'message',None)
    if message is None:message=getattr(getattr(update,'callback_query',None),'message',None)
    value=getattr(message,'message_thread_id',None)
    return value if isinstance(value,int) and value>0 else None

def thread_options(update):
    value=thread_id(update)
    return {'message_thread_id':value} if value is not None else {}

def protect_financial_content(screen):
    """Política de transporte; não interfere no conteúdo ou nos cálculos."""
    enabled=config.ler('ASSESSOR_PROTECT_FINANCIAL_CONTENT','1').strip().lower()
    return bool(getattr(screen,'sensitive',False)) and enabled in {'1','true','sim','s','yes','on'}

async def send_rich(update,screen,markup,host,edit=False,protect=False):
    """Retorna False só em rejeição explícita; timeout não duplica a mensagem."""
    if not screen.rich_html or config.ler('ASSESSOR_RICH_MESSAGES','1')!='1':return False
    getter=getattr(update,'get_bot',None)
    if not callable(getter):return False
    bot=getter()
    if not callable(getattr(bot,'do_api_request',None)):return False
    from telegram.error import BadRequest
    from types import SimpleNamespace
    data={'chat_id':update.effective_chat.id,'rich_message':{'html':screen.rich_html},'reply_markup':markup.to_dict()}
    query=getattr(update,'callback_query',None)
    endpoint='sendRichMessage'
    if edit and query and not getattr(query.message,'photo',None):
        endpoint='editMessageText';data['message_id']=query.message.message_id
    elif thread_id(update):data['message_thread_id']=thread_id(update)
    if endpoint=='sendRichMessage':
        data['allow_paid_broadcast']=False
        if protect:data['protect_content']=True
    try:result=await bot.do_api_request(endpoint,api_kwargs=data)
    except BadRequest as exc:
        if 'not modified' in str(exc).lower():return True
        return False
    if isinstance(result,dict):host.registrar_mensagem_enviada(SimpleNamespace(message_id=result.get('message_id'),chat_id=update.effective_chat.id))
    return True
