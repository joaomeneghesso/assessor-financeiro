"""Novos recursos com banco descartável, transporte simulado e autenticação real."""
import ast,asyncio,copy,hashlib,hmac,importlib.util,io,json,os,subprocess,tempfile,time,unittest
from pathlib import Path
from datetime import date,datetime,timedelta,timezone
from types import SimpleNamespace
from urllib.parse import urlencode
from unittest.mock import patch,AsyncMock
import database as db,services as svc,telegram_experiencia as ux
import telegram_recursos as extras,telegram_midia as media,telegram_alertas as alerts
import telegram_streaming as streaming
from security import hash_secret

def signed(user=1,stamp=None,token='test-only-token'):
    data={'auth_date':str(int(time.time() if stamp is None else stamp)),'user':json.dumps({'id':user,'first_name':'Fixture'})}
    check='\n'.join(k+'='+v for k,v in sorted(data.items()))
    key=hmac.new(b'WebAppData',token.encode(),hashlib.sha256).digest()
    data['hash']=hmac.new(key,check.encode(),hashlib.sha256).hexdigest()
    return urlencode(data)

class Innovations(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        for module in (db,svc):
            p=patch.object(module,'DB_PATH',Path(self.tmp.name)/'fixture.db');p.start();self.addCleanup(p.stop)
        db.init_db();db.definir_saldo_inicial_conta_mes('2026-09','Itaú',1000)
        self.engine=ux.Experience(date_provider=lambda:date(2026,9,30));self.key='1:1'
        extras.CURRENT_THREAD.set(None)
    def financial(self):
        with db.get_connection() as c:return {t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in ('transacoes','compromissos','fatura_movimentos','saldos_mensais_contas')}
    def test_origins_match_canonical_values_and_do_not_mutate(self):
        before=self.financial()
        for kind in ('saldo','reserva','previsao'):
            screen=self.engine.act(self.key,('origin',kind))
            self.assertIn('R$ 1.000,00',screen.text);self.assertIn('<details>',screen.rich_html)
            self.assertLess(len(screen.text.encode('utf-16-le'))//2,3900)
        self.assertEqual(before,self.financial())
    def test_core_financial_screens_gain_rich_presentation_without_changing_values(self):
        before=self.financial()
        for view in ('home','balance','balance_details','closing_details'):
            screen=self.engine.render(self.key,view)
            self.assertTrue(screen.rich_html)
            self.assertIn('<table',screen.rich_html)
            self.assertIn('R$ 1.000,00',screen.text)
            self.assertIn('R$ 1.000,00',screen.rich_html)
        self.assertEqual(before,self.financial())
    def test_how_much_to_pay_rich_table_reuses_canonical_total(self):
        db.inserir_compromisso({
            'tipo':'fixo','nome':'Conta de teste','valor':123.45,'dia_vencimento':20,
            'data_inicio':'2026-09-01','categoria':'Teste','conta_pagamento':'Itaú',
            'forma_pagamento':'Pix','recorrente':0,'ativo':1,
        })
        before=self.financial()
        screen=self.engine.act(self.key,('pay_month','2026-09'))
        self.assertIn('<table',screen.rich_html)
        self.assertIn('Itaú',screen.rich_html)
        self.assertIn('R$ 123,45',screen.text)
        self.assertIn('R$ 123,45',screen.rich_html)
        self.assertEqual(before,self.financial())
    def test_resources_offer_only_local_features_without_activation_links(self):
        with patch.dict(os.environ,{'ASSESSOR_MINIAPP_URL':'https://unused.test/miniapp'}):screen=self.engine.act(self.key,('innovations',))
        actions=[a for row in screen.rows for _,a in row]
        self.assertFalse(any(a[0] in {'miniapp','topics_create','topics_setup'} for a in actions))
        self.assertNotIn('HTTPS',screen.text);self.assertIn(('chart','home'),actions)
    def test_old_topics_entry_cannot_create_topics_or_touch_finances(self):
        import app
        before=self.financial();bot=SimpleNamespace(create_forum_topic=AsyncMock(),get_me=AsyncMock())
        update=SimpleNamespace(effective_user=SimpleNamespace(id=1),effective_chat=SimpleNamespace(id=1,type='private'),effective_message=None)
        with patch.object(app,'bloquear_se_nao_autorizado',new_callable=AsyncMock,return_value=False),patch.object(ux,'send_screen',new_callable=AsyncMock):asyncio.run(app.topics_command(update,SimpleNamespace(bot=bot)))
        bot.create_forum_topic.assert_not_awaited();bot.get_me.assert_not_awaited();self.assertEqual(before,self.financial())
    def test_external_panel_endpoints_and_configuration_removed(self):
        example=Path(__file__).resolve().parents[1]/'.env.example'
        if example.exists():self.assertNotIn('ASSESSOR_MINIAPP_URL',example.read_text(encoding='utf-8'))
    def test_origins_and_memory_respect_privacy(self):
        self.engine.session(self.key).privacy=True
        for action in [('origin','saldo'),('origin','reserva'),('origin','previsao'),('view','balance_details')]:
            screen=self.engine.act(self.key,action)
            self.assertNotIn('R$',screen.text+(screen.rich_html or ''))
    def test_all_quizzes_both_answers_preserve_draft_and_finances(self):
        before=self.financial();self.engine.begin(self.key,'receita');draft=copy.deepcopy(self.engine.session(self.key).draft)
        for lesson in extras.QUIZZES:
            screen=self.engine.act(self.key,('quiz',lesson));self.assertIn('entendimento',screen.text)
            for answer in (0,1):
                screen=self.engine.act(self.key,('quiz_answer',lesson,answer));self.assertIn('Nenhum dado financeiro',screen.text)
        self.engine.act(self.key,('resume_suspended',));self.assertEqual(draft,self.engine.session(self.key).draft)
        self.assertEqual(before,self.financial())
    def test_topics_have_separate_drafts_and_callback_ownership(self):
        def update(topic):return SimpleNamespace(effective_user=SimpleNamespace(id=1),effective_chat=SimpleNamespace(id=1),effective_message=SimpleNamespace(message_thread_id=topic))
        first,second=map(ux.session_key,(update(3),update(4)))
        self.engine.begin(first,'receita');self.engine.handle_text(first,'40')
        self.engine.begin(second,'despesa')
        token=self.engine.tokens_for(first,self.engine.render(first,'help'))[0][0][1]
        self.assertIsNone(self.engine.resolve(second,token));self.assertEqual(40,self.engine.session(first).draft['valor'])
        self.assertNotEqual(self.engine.session(first).stage,self.engine.session(second).stage)
        self.assertEqual('1:1',ux.session_key(update(None)))
    def test_legacy_pending_isolated_by_thread_context(self):
        store=extras.TopicPending();store[1]={'main':True}
        extras.CURRENT_THREAD.set(3);store[1]={'topic':3}
        extras.CURRENT_THREAD.set(4);self.assertIsNone(store.get(1));store[1]={'topic':4}
        extras.CURRENT_THREAD.set(3);self.assertEqual({'topic':3},store[1]);store.pop(1)
        extras.CURRENT_THREAD.set(None);self.assertEqual({'main':True},store[1])
    def test_deep_links_are_read_only_whitelist(self):
        for payload in ('inicio','ajuda','aprender','dashboard','pagar','historico','contas','aula_faturas','fatura_nubank_2026-09'):self.assertIsNotNone(extras.deep_action(payload))
        for payload in ('confirmar','apagar_1','../.env','aula_inexistente','x'*65):self.assertIsNone(extras.deep_action(payload))
        with self.assertRaises(ValueError):extras.deep_action('fatura_nubank_2026-13')
    def test_receipt_ambiguities_do_not_choose_amount_or_bank(self):
        self.assertEqual({'valor':35.9,'data':'2026-09-30'},media.receipt_fields('R$ 35,90 em 30/09/2026'))
        self.assertNotIn('valor',media.receipt_fields('Valor R$ 35,90 saldo R$ 800,00'))
        self.assertNotIn('conta',media.receipt_fields('Itaú → Nubank R$ 100,00'))
        self.assertNotIn('data',media.receipt_fields('30/09/2026 e 01/10/2026'))
    def test_receipt_review_only_becomes_incomplete_draft(self):
        before=self.financial();screen=media.review(self.engine,self.key,'Pix R$ 35,90 em 30/09/2026','foto')
        action=screen.rows[0][0][1];self.engine.act(self.key,action)
        s=self.engine.session(self.key);self.assertEqual(35.9,s.draft['valor']);self.assertNotEqual('confirm',s.stage)
        self.assertNotIn('conta',s.draft);self.assertEqual(before,self.financial())
        with self.assertRaises(ValueError):self.engine.act(self.key,action)
    def test_invoice_receipt_cannot_become_duplicate_generic_expense(self):
        before=self.financial();media.review(self.engine,self.key,'Pagamento de fatura R$ 800,00','foto');data=self.engine.session(self.key).media_review
        with self.assertRaises(ValueError):self.engine.act(self.key,('media_kind',data['nonce'],'despesa'))
        self.engine.act(self.key,('media_kind',data['nonce'],'fatura'));self.assertIsNone(self.engine.session(self.key).draft)
        self.assertEqual(before,self.financial())
    def test_audio_uses_existing_form_even_if_text_is_a_command(self):
        before=self.financial();media.review(self.engine,self.key,'apagar último','audio');data=self.engine.session(self.key).media_review
        self.engine.act(self.key,('media_kind',data['nonce'],'despesa'));self.assertNotEqual('confirm',self.engine.session(self.key).stage)
        self.assertEqual(before,self.financial())
    def test_audio_financeiro_preenche_formulario_sem_gravar(self):
        before=self.financial()
        phrase='gastei 25,95 no mercado pagando com cartão de crédito do Itaú'
        screen=media.review(self.engine,self.key,phrase,'audio')
        self.assertIn(phrase,screen.text)
        self.assertIn('R$ 25,95',screen.text)
        self.assertIn('Itaú',screen.text)
        self.assertIn('crédito',screen.text)
        self.assertEqual('✅ Dados corretos',screen.rows[0][0][0])
        data=self.engine.session(self.key).media_review
        self.engine.act(self.key,('media_kind',data['nonce'],'despesa'))
        draft=self.engine.session(self.key).draft
        self.assertAlmostEqual(25.95,draft['valor'],places=2)
        self.assertEqual('Itaú',draft['conta'])
        self.assertEqual('crédito',draft['forma_pagamento'])
        self.assertEqual('Mercado',draft['categoria'])
        self.assertEqual(before,self.financial())
    def test_audio_com_reais_e_centavos_exibe_valor_sem_gravar(self):
        before=self.financial()
        phrase='Gastei 197 reais e 99 centavos no mercado no cartão de crédito do Itaú.'
        screen=media.review(self.engine,self.key,phrase,'audio')
        self.assertIn('R$ 197,99',screen.text)
        self.assertIn('Itaú',screen.text)
        self.assertIn('crédito',screen.text)
        self.assertEqual('✅ Dados corretos',screen.rows[0][0][0])
        self.assertEqual(before,self.financial())
    def test_audio_petshop_define_intencao_categoria_e_edicao_sem_gravar(self):
        before=self.financial()
        phrase='Gastei 60 reais no Pet Shop, pagando com cartão de crédito do Itaú.'
        screen=media.review(self.engine,self.key,phrase,'audio')
        self.assertIn('Despesa reconhecida',screen.text)
        self.assertIn('Categoria: <b>Pet</b>',screen.text)
        self.assertIn('entra na fatura de <b>Itaú</b>',screen.text)
        labels=[label for row in screen.rows for label,_ in row]
        self.assertNotIn('💵 Entrada',labels);self.assertNotIn('💳 Pagamento de fatura',labels)
        data=self.engine.session(self.key).media_review
        edit=self.engine.act(self.key,('media_edit',data['nonce'],'despesa'))
        self.assertIn('Editar dados do registro',edit.text)
        self.assertEqual('Pet',self.engine.session(self.key).draft['categoria'])
        self.assertEqual('Pet Shop',self.engine.session(self.key).draft['descricao'])
        self.assertEqual(before,self.financial())
    def test_audio_salario_define_entrada_transferencia_e_data_sem_gravar(self):
        before=self.financial()
        phrase='Recebi meu salário de 5000 reais na conta Itaú.'
        screen=media.review(self.engine,self.key,phrase,'audio')
        self.assertIn('Entrada reconhecida',screen.text);self.assertIn('R$ 5.000,00',screen.text)
        self.assertIn('Forma: <b>transferência</b>',screen.text)
        self.assertIn('aumenta o saldo de <b>Itaú</b>',screen.text)
        data=self.engine.session(self.key).media_review
        self.engine.act(self.key,('media_kind',data['nonce'],'receita'))
        draft=self.engine.session(self.key).draft
        self.assertEqual('receita',draft['tipo']);self.assertEqual('Itaú',draft['conta'])
        self.assertEqual('transferência',draft['forma_pagamento']);self.assertEqual('2026-09-30',draft['data'])
        self.assertEqual('meu salário',draft['descricao'])
        self.assertEqual(before,self.financial())
    def test_categoria_deterministica_corrige_sugestao_ruim_da_ia(self):
        parsed={'query_type':'register_expense','amount':60,'installments':1,
                'description':'Pet Shop','category':'alimentação',
                'account':'Itaú','payment_method':'crédito'}
        self.engine._ai_registration_preview(self.key,parsed,'gastei 60 no petshop')
        self.assertEqual('Pet',self.engine.session(self.key).draft['categoria'])
    def test_audio_transferencia_permite_correcao_pontual_sem_gravar(self):
        db.definir_saldo_inicial_conta_mes('2026-09','Mercado Pago',200)
        media.review(self.engine,self.key,'Transferi 100 reais da conta do Itaú para a conta do Mercado Pago.','audio')
        data=self.engine.session(self.key).media_review;nonce=data['nonce']
        edit=self.engine.act(self.key,('media_transfer_edit',nonce));self.assertIn('Ajustar transferência',edit.text)
        prompt=self.engine.act(self.key,('media_transfer_field',nonce,'valor'));self.assertIn('novo valor',prompt.text)
        preview=self.engine.handle_text(self.key,'125,50');self.assertIn('R$ 125,50',preview.text)
        with db.get_connection() as conn:self.assertEqual(0,conn.execute('SELECT COUNT(*) FROM transferencias_caixa').fetchone()[0])
    def test_audio_transferencia_confirma_uma_vez_e_move_saldos(self):
        db.definir_saldo_inicial_conta_mes('2026-09','Mercado Pago',200)
        phrase='Transferi 100 reais da conta do Itaú para a conta do Mercado Pago.'
        screen=media.review(self.engine,self.key,phrase,'audio')
        self.assertIn('Transferência reconhecida',screen.text)
        self.assertIn('Sai de: <b>Itaú</b>',screen.text);self.assertIn('Entra em: <b>Mercado Pago</b>',screen.text)
        with db.get_connection() as conn:self.assertEqual(0,conn.execute('SELECT COUNT(*) FROM transferencias_caixa').fetchone()[0])
        data=self.engine.session(self.key).media_review
        result=self.engine.act(self.key,('media_transfer_commit',data['nonce']))
        self.assertIn('Transferência registrada',result.text)
        with db.get_connection() as conn:self.assertEqual(1,conn.execute('SELECT COUNT(*) FROM transferencias_caixa').fetchone()[0])
        caixa=svc.calcular_caixa_por_conta_mes('2026-09')
        self.assertEqual(900,caixa['contas']['Itaú']['disponivel'])
        self.assertEqual(300,caixa['contas']['Mercado Pago']['disponivel'])
        with self.assertRaises(ValueError):self.engine.act(self.key,('media_transfer_commit',data['nonce']))
        with db.get_connection() as conn:self.assertEqual(1,conn.execute('SELECT COUNT(*) FROM transferencias_caixa').fetchone()[0])
    def test_receiving_media_does_not_discard_existing_form(self):
        self.engine.begin(self.key,'receita');draft=copy.deepcopy(self.engine.session(self.key).draft)
        self.assertIn('andamento',media.review(self.engine,self.key,'R$ 50,00','foto').text)
        self.assertEqual(draft,self.engine.session(self.key).draft)
    def test_cancel_invalidates_pending_media(self):
        self.engine.session(self.key).media_review={'processing':True,'nonce':'test-only'}
        self.engine.act(self.key,('cancel',));self.assertIsNone(self.engine.session(self.key).media_review)
    def test_open_invoice_preserves_fixed_form(self):
        s=self.engine.session(self.key);s.fixed_edit={'id':123,'nome':'Rascunho'};s.stage='fixed_value'
        with patch.object(self.engine,'screen_obligation',return_value=ux.Screen('Fatura',[])):
            screen=self.engine.act(self.key,('detail_obligation','B_nubank','2026-09'))
        self.assertEqual('Rascunho',s.fixed_edit['nome']);self.assertEqual('fixed_value',s.learning_stage)
        self.assertTrue(any(action[0]=='learning_resume' for row in screen.rows for _,action in row))
    def test_invoice_origin_paginates_all_entries_without_writes(self):
        spec=importlib.util.spec_from_file_location('invoice_fixture_410',Path(__file__).resolve().parents[1]/'migrations/0004_competencia_faturas.py')
        migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
        with db.get_connection() as conn:migration.upgrade(conn)
        for n in range(7):db.inserir_transacao(dict(data='2026-09-10',tipo='despesa',valor=10+n,categoria='Teste',descricao='Compra '+str(n),conta='Nubank',forma_pagamento='crédito',competencia_fatura='2026-09',data_compra='2026-09-10'))
        before=self.financial();texts=''
        for page in (0,1):
            screen=self.engine.act(self.key,('invoice_origin','B_nubank','2026-09',page));texts+=screen.text
            self.assertIn('R$ 91,00',screen.text);self.assertIn('<table',screen.rich_html)
        for n in range(7):self.assertIn('Compra '+str(n),texts)
        self.engine.session(self.key).privacy=True
        screen=self.engine.act(self.key,('invoice_origin','B_nubank','2026-09',1));self.assertNotIn('R$',screen.text+screen.rich_html)
        self.assertEqual(before,self.financial())
    def test_snooze_callback_preserves_existing_draft(self):
        self.engine.begin(self.key,'receita');draft=copy.deepcopy(self.engine.session(self.key).draft)
        markup=alerts.controles(self.key,'snooze-test',{'month':'2026-09','overdue':[],'soon':[]})
        callback=markup.inline_keyboard[-1][0].callback_data
        update=SimpleNamespace(callback_query=SimpleNamespace(data=callback,answer=AsyncMock()),effective_user=SimpleNamespace(id=1),effective_chat=SimpleNamespace(id=1),effective_message=None)
        host=SimpleNamespace(bloquear_se_assessor_travado=AsyncMock(return_value=False),obter_timezone_alertas=lambda:timezone(timedelta(hours=-3)))
        with patch.object(ux,'EXPERIENCE',self.engine),patch.object(ux,'send_screen',new_callable=AsyncMock) as send:
            self.assertTrue(asyncio.run(alerts.callback(update,None,host)))
            screen=send.await_args.args[1];self.assertTrue(any(action[0]=='resume_suspended' for row in screen.rows for _,action in row))
        self.engine.act(self.key,('resume_suspended',));self.assertEqual(draft,self.engine.session(self.key).draft)
    def test_media_receiver_downloads_to_temporary_file_without_financial_writes(self):
        before=self.financial();paths=[]
        async def download(custom_path):paths.append(Path(custom_path));Path(custom_path).write_bytes(b'fixture-only')
        attachment=SimpleNamespace(file_size=12,duration=0,get_file=AsyncMock(return_value=SimpleNamespace(download_to_drive=download)))
        message=SimpleNamespace(voice=None,audio=None,photo=[attachment],message_thread_id=None,reply_text=AsyncMock())
        update=SimpleNamespace(effective_user=SimpleNamespace(id=1),effective_chat=SimpleNamespace(id=1),effective_message=message)
        host=SimpleNamespace(bloquear_se_nao_autorizado=AsyncMock(return_value=False),bloquear_se_assessor_travado=AsyncMock(return_value=False))
        with patch.object(ux,'EXPERIENCE',self.engine),patch.object(media,'reconhecer_foto',return_value='R$ 35,90 em 30/09/2026'),patch.object(ux,'send_screen',new_callable=AsyncMock):asyncio.run(media.receive(update,None,host))
        self.assertTrue(paths);self.assertFalse(paths[0].exists());self.assertEqual('foto',self.engine.session(self.key).media_review['source']);self.assertEqual(before,self.financial())
    def test_snooze_is_idempotent_and_honors_silence_and_pause(self):
        now=datetime(2026,9,30,10,tzinfo=timezone(timedelta(hours=-3)))
        before=self.financial();self.assertTrue(alerts.adiar(self.key,'fixture',now));self.assertFalse(alerts.adiar(self.key,'fixture',now))
        prefs={'alertas':True,'pausa_ate':'','silencio_inicio':'23:00','silencio_fim':'08:00'}
        self.assertFalse(alerts.sonecas(self.key,now,prefs));self.assertTrue(alerts.sonecas(self.key,now+timedelta(hours=1),prefs))
        self.assertFalse(alerts.sonecas(self.key,now+timedelta(hours=13),prefs))
        self.assertEqual(before,self.financial())
    def test_alert_controls_do_not_invalidate_draft_tokens_or_show_amounts(self):
        self.engine.begin(self.key,'receita');screen=self.engine.prompt(self.engine.session(self.key));token=self.engine.tokens_for(self.key,screen)[0][0][1]
        markup=alerts.controles(self.key,'fixture',{'month':'2026-09','overdue':[{'chave':'B_nubank','valor':900}], 'soon':[]})
        self.assertIsNotNone(self.engine.resolve(self.key,token));self.assertNotIn('900',json.dumps(markup.to_dict()));self.assertNotIn('R$',json.dumps(markup.to_dict()))


class RichTransport(unittest.IsolatedAsyncioTestCase):
    async def test_sensitive_screen_is_sent_protected_and_old_controls_are_retired(self):
        from telegram import InlineKeyboardMarkup
        bot=SimpleNamespace(do_api_request=AsyncMock(return_value={'message_id':10}))
        query=SimpleNamespace(
            message=SimpleNamespace(photo=None,message_id=9),
            edit_message_reply_markup=AsyncMock(),
        )
        chat=SimpleNamespace(id=1)
        update=SimpleNamespace(
            get_bot=lambda:bot,effective_user=SimpleNamespace(id=1),effective_chat=chat,
            effective_message=query.message,callback_query=query,
        )
        host=SimpleNamespace(registrar_mensagem_enviada=lambda msg:None)
        screen=ux.Screen('<b>Saldo</b>\n\nR$ 1.000,00',rich_html='<h2>Saldo</h2><p>R$ 1.000,00</p>',sensitive=True)
        with patch.dict(os.environ,{'ASSESSOR_RICH_MESSAGES':'1','ASSESSOR_PROTECT_FINANCIAL_CONTENT':'1'}):
            await ux.send_screen(update,screen,host,edit=True)
        self.assertEqual('sendRichMessage',bot.do_api_request.await_args.args[0])
        data=bot.do_api_request.await_args.kwargs['api_kwargs']
        self.assertIs(data['protect_content'],True)
        query.edit_message_reply_markup.assert_awaited_once()
        retired=query.edit_message_reply_markup.await_args.kwargs['reply_markup']
        self.assertEqual({},retired.inline_keyboard[0][0].api_kwargs['disabled'])
    async def test_already_protected_financial_screen_keeps_atomic_edit(self):
        bot=SimpleNamespace(do_api_request=AsyncMock(return_value=True))
        query=SimpleNamespace(
            message=SimpleNamespace(photo=None,message_id=9,has_protected_content=True),
            edit_message_reply_markup=AsyncMock(),
        )
        update=SimpleNamespace(
            get_bot=lambda:bot,effective_user=SimpleNamespace(id=1),effective_chat=SimpleNamespace(id=1),
            effective_message=query.message,callback_query=query,
        )
        screen=ux.Screen('R$ 20,00',rich_html='<p>R$ 20,00</p>')
        with patch.dict(os.environ,{'ASSESSOR_RICH_MESSAGES':'1','ASSESSOR_PROTECT_FINANCIAL_CONTENT':'1'}):
            await ux.send_screen(update,screen,SimpleNamespace(),edit=True)
        self.assertEqual('editMessageText',bot.do_api_request.await_args.args[0])
        query.edit_message_reply_markup.assert_not_awaited()
    async def test_financial_protection_can_be_disabled_without_changing_screen(self):
        screen=ux.Screen('R$ 10,00')
        self.assertTrue(screen.sensitive)
        with patch.dict(os.environ,{'ASSESSOR_PROTECT_FINANCIAL_CONTENT':'0'}):
            self.assertFalse(extras.protect_financial_content(screen))
    async def test_rich_edit_uses_only_supported_parameters(self):
        from telegram import InlineKeyboardMarkup
        bot=SimpleNamespace(do_api_request=AsyncMock(return_value=True))
        update=SimpleNamespace(get_bot=lambda:bot,effective_chat=SimpleNamespace(id=1),callback_query=SimpleNamespace(message=SimpleNamespace(photo=None,message_id=9)))
        screen=ux.Screen('Teste',rich_html='<p>Teste</p>')
        self.assertTrue(await extras.send_rich(update,screen,InlineKeyboardMarkup([]),SimpleNamespace(),edit=True))
        self.assertEqual('editMessageText',bot.do_api_request.await_args.args[0]);self.assertNotIn('allow_paid_broadcast',bot.do_api_request.await_args.kwargs['api_kwargs'])
    async def test_rich_message_uses_documented_request_without_upgrading_library(self):
        bot=SimpleNamespace(do_api_request=AsyncMock(return_value={'message_id':9}))
        update=SimpleNamespace(get_bot=lambda:bot,effective_chat=SimpleNamespace(id=1),callback_query=None,message=SimpleNamespace(message_thread_id=7))
        from telegram import InlineKeyboardMarkup
        host=SimpleNamespace(registrar_mensagem_enviada=lambda msg:None)
        screen=ux.Screen('Resumo',rich_html='<h2>Resumo</h2><details><summary>Detalhes</summary><p>Teste</p></details>')
        with patch.dict(os.environ,{'ASSESSOR_RICH_MESSAGES':'1'}):self.assertTrue(await extras.send_rich(update,screen,InlineKeyboardMarkup([]),host))
        data=bot.do_api_request.await_args.kwargs['api_kwargs'];self.assertEqual({'html':screen.rich_html},data['rich_message']);self.assertEqual(7,data['message_thread_id']);self.assertIs(data['allow_paid_broadcast'],False)
    async def test_explicit_rejection_falls_back_timeout_does_not_duplicate(self):
        from telegram.error import BadRequest,TimedOut
        from telegram import InlineKeyboardMarkup
        bot=SimpleNamespace(do_api_request=AsyncMock(side_effect=BadRequest('unknown method')))
        update=SimpleNamespace(get_bot=lambda:bot,effective_chat=SimpleNamespace(id=1),callback_query=None)
        screen=ux.Screen('Teste',rich_html='<p>Teste</p>')
        self.assertFalse(await extras.send_rich(update,screen,InlineKeyboardMarkup([]),SimpleNamespace()))
        bot.do_api_request.side_effect=TimedOut()
        with self.assertRaises(TimedOut):await extras.send_rich(update,screen,InlineKeyboardMarkup([]),SimpleNamespace())


class StreamingProgress(unittest.IsolatedAsyncioTestCase):
    async def test_streaming_reuses_draft_and_never_includes_financial_content(self):
        bot=SimpleNamespace(do_api_request=AsyncMock(return_value=True))
        update=SimpleNamespace(
            get_bot=lambda:bot,effective_chat=SimpleNamespace(id=1,type='private'),
            effective_message=SimpleNamespace(message_thread_id=7),
        )
        progress=streaming.DraftProgress(update,delay=0,min_interval=0)
        with patch.dict(os.environ,{'ASSESSOR_STREAMING_PROGRESS':'1'}):
            self.assertTrue(await progress.show('🧠 Analisando localmente…'))
            self.assertTrue(await progress.show('📝 Preparando a revisão…'))
        calls=bot.do_api_request.await_args_list
        self.assertEqual(2,len(calls))
        payloads=[call.kwargs['api_kwargs'] for call in calls]
        self.assertEqual({progress.draft_id},{p['draft_id'] for p in payloads})
        self.assertEqual({7},{p['message_thread_id'] for p in payloads})
        self.assertTrue(all('R$' not in p['text'] for p in payloads))
        self.assertTrue(all(call.args[0]=='sendMessageDraft' for call in calls))
    async def test_streaming_disabled_or_unavailable_is_silent_fallback(self):
        bot=SimpleNamespace(do_api_request=AsyncMock(side_effect=RuntimeError('indisponível')))
        update=SimpleNamespace(get_bot=lambda:bot,effective_chat=SimpleNamespace(id=1,type='private'),effective_message=None)
        progress=streaming.DraftProgress(update,delay=0,min_interval=0)
        with patch.dict(os.environ,{'ASSESSOR_STREAMING_PROGRESS':'0'}):
            self.assertFalse(await progress.show('Processando…'))
        bot.do_api_request.assert_not_awaited()
        with patch.dict(os.environ,{'ASSESSOR_STREAMING_PROGRESS':'1'}):
            self.assertFalse(await progress.show('Processando…'))
        bot.do_api_request.assert_awaited_once()

