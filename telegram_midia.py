"""Recepção local de mídia: reconhecimento -> revisão -> formulário existente."""
import asyncio
import json
import logging
import os
import config
import re
import secrets
import subprocess
import tempfile
from pathlib import Path
from datetime import date
import database as db
from telegram_execucao import executar_core

class MediaError(ValueError):pass
EH_WINDOWS=os.name=='nt'  # Linux (servidor): OCR pelo Tesseract

def reconhecer_foto(path):
    from PIL import Image
    with Image.open(path) as img:
        if img.width*img.height>20_000_000:raise MediaError('A foto é muito grande. Envie uma imagem menor e legível.')
        img.verify()
    if not EH_WINDOWS:return _reconhecer_foto_tesseract(path)
    script=Path(__file__).with_name('reconhecer_comprovante.ps1')
    try:
        command='& { '+script.read_text(encoding='utf-8')+" } -ImagePath '"+str(Path(path).resolve()).replace("'","''")+"'"
        try:timeout=max(5,min(60,int(config.ler('ASSESSOR_OCR_TIMEOUT','30'))))
        except (TypeError,ValueError):timeout=30
        run=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,encoding='utf-8-sig',errors='replace',timeout=timeout)
    except (OSError,subprocess.TimeoutExpired) as exc:raise MediaError('O reconhecimento local não respondeu. Use Registrar por etapas.') from exc
    if run.returncode:raise MediaError('O reconhecimento de foto não está disponível neste Windows. Confira o idioma do sistema ou use Registrar por etapas.')
    try:result=json.loads(run.stdout)
    except (ValueError,TypeError) as exc:raise MediaError('Não consegui ler essa foto. Tente uma imagem mais nítida.') from exc
    text=str(result.get('text') or '').strip()
    if not text:raise MediaError('Não identifiquei texto. Envie o comprovante sem cortes e com boa iluminação.')
    return text

def _reconhecer_foto_tesseract(path):
    """Linux (servidor): Tesseract local em português; mesmo contrato do OCR do Windows."""
    try:timeout=max(5,min(60,int(config.ler('ASSESSOR_OCR_TIMEOUT','30'))))
    except (TypeError,ValueError):timeout=30
    try:run=subprocess.run(['tesseract',str(Path(path).resolve()),'stdout','-l','por'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    except (OSError,subprocess.TimeoutExpired) as exc:raise MediaError('O reconhecimento local não respondeu. Use Registrar por etapas.') from exc
    if run.returncode:raise MediaError('O reconhecimento de foto não está disponível neste servidor (instale tesseract-ocr-por). Use Registrar por etapas.')
    text=run.stdout.strip()
    if not text:raise MediaError('Não identifiquei texto. Envie o comprovante sem cortes e com boa iluminação.')
    return text

def receipt_fields(text):
    """Só reconhece valores inequívocos; não escolhe banco de origem/destino."""
    from money import parse_money
    amounts=set()
    for raw in re.findall(r'R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})',text,re.I):
        try:amounts.add(str(parse_money(raw)))
        except ValueError:pass
    fields={}
    if len(amounts)==1:fields['valor']=float(amounts.pop())
    days=set()
    for day,month,year in re.findall(r'\b(\d{2})/(\d{2})/(\d{4})\b',text):
        try:days.add(date(int(year),int(month),int(day)).isoformat())
        except ValueError:pass
    if len(days)==1:fields['data']=days.pop()
    return fields

def audio_kind_hint(text):
    """Infere uma intenção explícita sem executar qualquer movimentação."""
    normalized=str(text or '').lower()
    if (re.search(r'^\s*(?:transferi|transferir|transfere|mover|movimentar|passei)\b',normalized)
            and re.search(r'\b(?:da|do|de)\b.+\b(?:para|pra)\b',normalized)):
        return 'transferencia'
    if re.search(r'\bfatura\b',normalized) and re.search(r'\b(?:paguei|pagamento|quitei|quitei)\b',normalized):
        return 'fatura'
    expense=bool(re.search(r'\b(gastei|comprei|paguei|despesa|d[eé]bito|custou)\b',normalized))
    income=bool(re.search(r'\b(recebi|ganhei|sal[aá]rio|renda|entrou)\b',normalized))
    if expense==income:return None
    return 'despesa' if expense else 'receita'

def _transfer_screen(data, *, editing=False):
    from telegram_experiencia import Screen,safe,money
    fields=data.get('fields') or {};nonce=data['nonce']
    if fields.get('erro') or not all(fields.get(k) for k in ('valor','conta_origem','conta_destino','data')):
        return Screen(
            '<b>🔁 Transferência reconhecida, mas incompleta</b>\n\n'
            'Não consegui separar valor, origem e destino com segurança. Nenhuma movimentação foi salva.',
            [[('✏️ Corrigir dados',('media_transfer_edit',nonce)),('Descartar',('media_kind',nonce,'discard'))]],
        )
    text=(('<b>✏️ Ajustar transferência</b>' if editing else '<b>🔎 Transferência reconhecida</b>')+
          '\n\nValor: <b>'+money(fields['valor'])+'</b>\n'
          'Sai de: <b>'+safe(fields['conta_origem'])+'</b>\n'
          'Entra em: <b>'+safe(fields['conta_destino'])+'</b>\n'
          'Data: <b>'+date.fromisoformat(fields['data']).strftime('%d/%m/%Y')+'</b>\n\n'
          'O total entre suas contas não muda. Nenhuma transferência foi salva ainda.')
    if editing:
        rows=[
            [('Valor',('media_transfer_field',nonce,'valor')),('Origem',('media_transfer_field',nonce,'origem'))],
            [('Destino',('media_transfer_field',nonce,'destino')),('Data',('media_transfer_field',nonce,'data'))],
            [('↩ Voltar à confirmação',('media_transfer_back',nonce)),('Descartar',('media_kind',nonce,'discard'))],
        ]
    else:
        rows=[
            [('✅ Salvar transferência',('media_transfer_commit',nonce))],
            [('✏️ Ajustar dados',('media_transfer_edit',nonce)),('Descartar',('media_kind',nonce,'discard'))],
        ]
    return Screen(text,rows)

def review(engine,key,text,source):
    from telegram_experiencia import Screen,safe,money
    text=str(text).strip()[:5000]
    if not text:raise MediaError('Não consegui reconhecer uma mensagem.')
    s=engine.session(key)
    if s.stage or s.suspended_draft or s.learning_stage or s.media_review:
        return Screen('Há um cadastro ou rascunho em andamento. Retome ou cancele antes de enviar outro arquivo.',[[('↩ Retomar cadastro',('learning_resume',))]] if s.learning_stage else [[('↩ Retomar registro',('resume_suspended',))]] if s.suspended_draft else [[('Cancelar',('cancel',))]])
    hint=audio_kind_hint(text) if source=='audio' else None
    fields=receipt_fields(text) if source=='foto' else {}
    if source=='audio' and hint=='transferencia':
        import services as svc
        fields=svc.parsear_comando_transferencia_caixa(text) or {}
        if fields and not fields.get('erro'):
            fields['data']=engine.date_provider().isoformat()
    elif source=='audio' and hint in {'despesa','receita'}:
        from registro_conversa import extrair_campos
        try:fields=extrair_campos(text,hoje=engine.date_provider(),contas=engine.accounts(),tipo=hint)
        except (ValueError,TypeError):fields={}
        if hint=='receita' and fields.get('conta') and not fields.get('forma_pagamento'):
            fields['forma_pagamento']='transferência'
        if all(fields.get(k) for k in ('valor','descricao','forma_pagamento','conta')):
            fields.setdefault('data',engine.date_provider().isoformat())
    s.media_review={'text':text,'source':source,'fields':fields,'suggested_kind':hint,'nonce':secrets.token_urlsafe(12)}
    fields=s.media_review['fields'];nonce=s.media_review['nonce']
    if hint=='transferencia':return _transfer_screen(s.media_review)
    warning='Valor: '+(money(fields['valor']) if fields.get('valor') else 'precisa ser informado/conferido')
    recognized=[]
    if fields.get('conta'):recognized.append('Conta: <b>'+safe(fields['conta'])+'</b>')
    if fields.get('forma_pagamento'):recognized.append('Forma: <b>'+safe(fields['forma_pagamento'])+'</b>')
    if fields.get('categoria'):recognized.append('Categoria: <b>'+safe(fields['categoria'])+'</b>')
    detail=('\n'+' · '.join(recognized)) if recognized else ''
    impact=''
    if hint=='receita' and fields.get('conta'):
        impact='\nImpacto: aumenta o saldo de <b>'+safe(fields['conta'])+'</b>.'
    elif hint=='despesa' and fields.get('conta'):
        if fields.get('forma_pagamento')=='crédito':
            impact='\nImpacto: entra na fatura de <b>'+safe(fields['conta'])+'</b>; não reduz o saldo bancário agora.'
        elif fields.get('forma_pagamento'):
            impact='\nImpacto: reduz o saldo de <b>'+safe(fields['conta'])+'</b>.'
    special=bool(re.search(r'\bfatura\b',text,re.I))
    expense_label='✅ Continuar como despesa' if hint=='despesa' else '💸 Despesa'
    income_label='✅ Continuar como entrada' if hint=='receita' else '💵 Entrada'
    if hint in {'despesa','receita'}:
        intention='Despesa' if hint=='despesa' else 'Entrada'
        screen=Screen('<b>🔎 '+intention+' reconhecida</b>\n\n'+safe(text,1800)+'\n\n'+warning+detail+impact+
          '\n\nConfira os dados. Ao continuar, o assessor mostra a confirmação final antes de salvar. Nenhuma movimentação foi salva.',[
          [('✅ Dados corretos',('media_kind',nonce,hint))],
          [('✏️ Ajustar dados',('media_edit',nonce,hint)),('Descartar',('media_kind',nonce,'discard'))]])
    elif hint=='fatura':
        screen=Screen('<b>🔎 Pagamento de fatura reconhecido</b>\n\n'+safe(text,1800)+'\n\n'+warning+detail+
          '\n\nO fluxo de pagamento fará a conferência antes de salvar.',[
          [('💳 Conferir pagamento da fatura',('media_kind',nonce,'fatura'))],
          [('Descartar',('media_kind',nonce,'discard'))]])
    else:
        screen=Screen('<b>🔎 Confira o que reconheci</b>\n\n'+safe(text,1800)+'\n\n'+warning+detail+
          '\n\n<b>Não identifiquei uma intenção inequívoca.</b> Escolha o tipo; nenhuma movimentação foi salva.',[
          *([] if special else [[(expense_label,('media_kind',nonce,'despesa')),(income_label,('media_kind',nonce,'receita'))]]),
          [('💳 Pagamento de fatura',('media_kind',nonce,'fatura')),('🔁 Transferência própria',('media_kind',nonce,'transferencia'))],
          [('Descartar',('media_kind',nonce,'discard'))]])
    return screen

def _draft_from_media(engine,data,kind):
    text=data['text'];fields=dict(data['fields'])
    if data['source']=='audio':
        from registro_conversa import extrair_campos
        try:fields=extrair_campos(text,hoje=engine.date_provider(),contas=engine.accounts(),tipo=kind)
        except (ValueError,TypeError):fields={}
    if kind=='receita' and fields.get('conta') and not fields.get('forma_pagamento'):
        fields['forma_pagamento']='transferência'
    if all(fields.get(k) for k in ('valor','descricao','forma_pagamento','conta')):
        fields.setdefault('data',engine.date_provider().isoformat())
    draft={k:v for k,v in fields.items() if k in {'valor','descricao','categoria','forma_pagamento','conta','data','parcelas_total','_installments_pending'} }
    draft.update(tipo=kind,parcelas_total=draft.get('parcelas_total',1),key=secrets.token_urlsafe(18),parsed=True,
                 mensagem_original='Reconhecido de '+data['source']+': '+text[:2000])
    draft.setdefault('categoria','Receita' if kind=='receita' else 'Outros')
    return draft

def dispatch(engine,key,action):
    from telegram_experiencia import Screen,safe,money
    s=engine.session(key);data=s.media_review
    if not data or action[1]!=data['nonce']:raise ValueError('Este rascunho expirou. Envie o arquivo novamente.')
    event=action[0]
    if event=='media_transfer_edit':
        s.stage=None
        return _transfer_screen(data,editing=True)
    if event=='media_transfer_back':
        s.stage=None
        return _transfer_screen(data)
    if event=='media_transfer_field':
        field=action[2]
        if field not in {'valor','origem','destino','data'}:raise ValueError('Campo de transferência inválido.')
        s.stage='media_transfer_'+field
        prompts={'valor':'Digite o novo valor da transferência.',
                 'origem':'Digite a conta de onde o dinheiro saiu.',
                 'destino':'Digite a conta em que o dinheiro entrou.',
                 'data':'Digite a data em DD/MM/AAAA.'}
        return Screen('<b>Corrigir '+field+'</b>\n\n'+prompts[field],[[('Cancelar edição',('media_transfer_edit',data['nonce']))]])
    if event=='media_transfer_commit':
        fields=dict(data.get('fields') or {})
        if fields.get('erro') or not all(fields.get(k) for k in ('valor','conta_origem','conta_destino','data')):
            raise ValueError('Corrija valor, origem e destino antes de confirmar.')
        import services as svc
        if svc.mesma_conta_saldo(fields['conta_origem'],fields['conta_destino']):
            raise ValueError('Origem e destino precisam ser contas diferentes.')
        transfer_id=db.inserir_transferencia_caixa(fields)
        s.media_review=None;s.stage=None
        return Screen('<b>✅ Transferência registrada no assessor</b>\n\n'
                      f'Referência: <code>#{transfer_id}</code>\nValor: <b>{money(fields["valor"])}</b>\n'
                      f'Saiu de: <b>{safe(fields["conta_origem"])}</b>\nEntrou em: <b>{safe(fields["conta_destino"])}</b>\n\n'
                      'Ela altera os dois saldos por conta, mas não cria receita nem despesa.',
                      [[('🏦 Ver saldos',('view','balance')),('🏠 Início',('view','home'))]])
    kind=action[2]
    if kind=='discard':s.media_review=None;return engine.render(key,'register')
    if kind=='fatura':s.media_review=None;return engine.render(key,'pay')
    if kind=='transferencia':s.media_review=None;s.topic='transferencias';return engine.render(key,'help_topic')
    if kind not in {'despesa','receita'}:raise ValueError('Escolha entrada ou despesa.')
    if re.search(r'\bfatura\b',data['text'],re.I):raise ValueError('Este arquivo menciona fatura. Use o caminho de pagamento da fatura.')
    draft=_draft_from_media(engine,data,kind)
    # Fotos não inferem conta/forma/descrição e exigem revisão de campos faltantes.
    s.media_review=None;s.draft=draft
    if kind=='despesa' and 'forma_pagamento' not in draft and not draft.get('_installments_pending'):draft['_ask_installment_choice']=True
    if event=='media_edit':
        s.stage='confirm'
        return engine._edit_menu_screen(s)
    return engine._advance_registration(key)

def answer(engine,key,text):
    """Edita um único campo da transferência reconhecida, sem gravá-la."""
    from money import parse_money
    from registro_conversa import data_informada,normalizar
    s=engine.session(key);data=s.media_review
    if not data or not str(s.stage or '').startswith('media_transfer_'):
        raise ValueError('Essa edição de transferência expirou.')
    fields=data.setdefault('fields',{});field=s.stage.removeprefix('media_transfer_')
    raw=str(text or '').strip()
    import services as svc
    if field=='valor':
        value=float(parse_money(raw))
        if value<=0:raise ValueError('Informe um valor maior que zero.')
        fields['valor']=value
    elif field in {'origem','destino'}:
        matches={normalizar(name):name for name in engine.accounts()}
        account=matches.get(normalizar(raw))
        if not account:raise ValueError('Escolha uma conta já cadastrada no assessor.')
        fields['conta_origem' if field=='origem' else 'conta_destino']=account
    elif field=='data':
        fields['data']=data_informada(raw,engine.date_provider())
    else:raise ValueError('Campo de transferência inválido.')
    if (fields.get('conta_origem') and fields.get('conta_destino')
            and svc.mesma_conta_saldo(fields['conta_origem'],fields['conta_destino'])):
        raise ValueError('Origem e destino precisam ser contas diferentes.')
    fields.pop('erro',None);s.stage=None
    return _transfer_screen(data)

async def receive(update,context,host):
    if await host.bloquear_se_nao_autorizado(update):return
    if await host.bloquear_se_assessor_travado(update,'registrar'):return
    import telegram_experiencia as ux
    key=ux.session_key(update);s=ux.EXPERIENCE.session(key)
    if s.stage or s.suspended_draft or s.learning_stage or s.media_review:
        await ux.send_screen(update,ux.Screen('Retome ou cancele o cadastro em andamento antes de enviar outro arquivo.',[[('Cancelar cadastro',('cancel',)),('Ajuda',('view','help'))]]),host);return
    message=update.effective_message
    attachment=message.voice or message.audio or (message.photo[-1] if message.photo else None)
    if attachment is None:return
    source='foto' if message.photo else 'audio'
    if (getattr(attachment,'file_size',0) or 0)>10_000_000 or (getattr(attachment,'duration',0) or 0)>180:
        await ux.send_screen(update,ux.Screen('Envie até 10 MB ou um áudio de até 3 minutos. Nenhuma movimentação foi criada.',[[('Registrar por etapas',('view','register'))]]),host);return
    # Identifica a sessão antes de aguardar reconhecimento; descarte evita resposta atrasada.
    owner=s;marker=secrets.token_urlsafe(12);s.media_review={'nonce':marker,'processing':True}
    from telegram_streaming import DraftProgress
    progress=DraftProgress(update)
    if not await progress.show('🔎 Preparando o reconhecimento local…'):
        await message.reply_text('🔎 Vou reconhecer o arquivo neste computador. Depois você confere os dados. Nenhum lançamento será salvo automaticamente.')
    try:
        with tempfile.TemporaryDirectory(prefix='assessor_midia_') as tmp:
            path=Path(tmp)/('arquivo.jpg' if source=='foto' else 'arquivo.audio')
            file=await attachment.get_file();await file.download_to_drive(custom_path=str(path))
            if path.stat().st_size>10_000_000:raise MediaError('O arquivo excedeu 10 MB.')
            if source=='foto':
                await progress.show('🔎 Lendo o comprovante neste computador…')
                text=await asyncio.to_thread(reconhecer_foto,path)
            else:
                from transcricao_audio import transcrever_audio
                await progress.show('🎙 Transcrevendo o áudio neste computador…')
                text=await asyncio.to_thread(transcrever_audio,path)
        if ux.EXPERIENCE.sessions.get(key) is not owner or not s.media_review or s.media_review.get('nonce')!=marker:return
        if s.stage or s.draft or s.fixed_edit or s.new_fixed:s.media_review=None;return
        await progress.show('📝 Preparando a revisão dos dados…')
        s.media_review=None;screen=await executar_core(review,ux.EXPERIENCE,key,text,source)
        await ux.send_screen(update,screen,host)
    except Exception as exc:
        if ux.EXPERIENCE.sessions.get(key) is not owner or not s.media_review or s.media_review.get('nonce')!=marker:return
        s.media_review=None
        logging.exception('Falha recuperável no reconhecimento de mídia (%s)',source)
        if source=='audio':
            from transcricao_audio import AudioDependencyMissing,AudioTranscriptionError
            if isinstance(exc,AudioDependencyMissing):detail='O motor local de voz ainda não está pronto. Rode instalar_audio.ps1 e reinicie o assessor.'
            elif isinstance(exc,AudioTranscriptionError):detail=str(exc)
            else:detail='O motor local de voz encontrou uma falha inesperada.'
            message='Não consegui transcrever este áudio. '+detail+' Nenhum lançamento foi criado.'
        else:
            message='Não consegui reconhecer essa imagem com segurança. Confira o idioma OCR ou use o formulário. Nenhum lançamento foi criado.'
        await ux.send_screen(update,ux.Screen(message,[[('Registrar por etapas',('view','register')),('Como funciona',('media_help',))]]),host)
    finally:
        await progress.close()
