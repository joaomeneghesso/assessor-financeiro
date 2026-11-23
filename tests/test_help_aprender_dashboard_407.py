"""Ensino, navegação e retrato financeiro; banco de teste exclusivamente."""
import copy,json,tempfile,unittest
from pathlib import Path
from datetime import date
from unittest.mock import patch,AsyncMock,Mock
from types import SimpleNamespace
from PIL import Image
import database as db,services as svc,telegram_experiencia as ux
from saldo_resumo import resumir_saldo
from telegram_visuais import painel


class HelpLearningDashboard(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        for module in (db,svc):
            p=patch.object(module,'DB_PATH',Path(self.tmp.name)/'fixture.db');p.start();self.addCleanup(p.stop)
        db.init_db();db.definir_saldo_inicial_conta_mes('2026-09','Itaú',1000)
        self.engine=ux.Experience(date_provider=lambda:date(2026,9,30));self.key='educacao'

    def financial(self):
        with db.get_connection() as c:
            return {table:[tuple(r) for r in c.execute('SELECT * FROM '+table)] for table in
                    ('transacoes','compromissos','fatura_movimentos','saldos_mensais_contas')}

    def test_all_lessons_catalog_help_and_tools_preserve_financial_rows(self):
        before=self.financial()
        actions=[('view','learn'),('view','help')]+[('lesson_page',i) for i in range(3)]
        actions += [('topic',key) for key in ux.HELP_TOPICS]
        for action in actions:
            screen=self.engine.act(self.key,action)
            self.assertLessEqual(len(screen.text.encode('utf-16-le'))//2,3900)
            for row in self.engine.tokens_for(self.key,screen):
                for _,token in row:self.assertIsNotNone(self.engine.resolve(self.key,token))
        for key in ux.learning.ORDER:
            engine=copy.deepcopy(self.engine)
            screen=engine.act(self.key,('lesson',key))
            for heading in ('Como funciona','Exemplo ilustrativo','Como conferir'):
                self.assertIn(heading,screen.text)
            tool=screen.rows[0][0][1]
            self.assertIsInstance(engine.act(self.key,tool),ux.Screen)
            self.assertEqual(before,self.financial())
        self.assertEqual(before,self.financial())

    def test_numbered_aliases_and_unknown_theme(self):
        for number in range(1,17):
            self.assertIn('Aula',self.engine.handle_text(self.key,'/aprender '+str(number)).text)
        for alias in ('aprender quanto vou pagar','aula transferência','aprender primeiros passos','/aprender caixa'):
            self.assertIn('Como conferir',self.engine.handle_text(self.key,alias).text)
        self.assertIn('Não encontrei',self.engine.handle_text(self.key,'aprender tema inexistente').text)

    def test_learning_preserves_transaction_draft_and_resumes_same_stage(self):
        self.engine.begin(self.key,'receita');self.engine.handle_text(self.key,'35')
        s=self.engine.session(self.key);draft=copy.deepcopy(s.draft);stage=s.stage
        self.engine.open_learning(self.key,'caixa')
        self.assertEqual(draft,s.suspended_draft)
        self.engine.act(self.key,('resume_suspended',))
        self.assertEqual(stage,s.stage);self.assertEqual(draft,s.draft)

    def test_dashboard_preserves_transaction_and_restores_original_stage(self):
        before=self.financial()
        self.engine.begin(self.key,'receita');self.engine.handle_text(self.key,'35')
        s=self.engine.session(self.key);draft=copy.deepcopy(s.draft);stage=s.stage
        screen=self.engine.act(self.key,('chart','home'))
        self.assertEqual(draft,s.suspended_draft)
        self.assertIn(('resume_suspended',),[a for row in screen.rows for _,a in row])
        self.engine.act(self.key,('resume_suspended',))
        self.assertEqual(stage,s.stage);self.assertEqual(draft,s.draft)
        self.assertEqual(before,self.financial())

    def test_dashboard_preserves_new_fixed_draft_and_resumes(self):
        before=self.financial()
        self.engine.begin_new_fixed(self.key)
        s=self.engine.session(self.key);stage=s.stage;draft=copy.deepcopy(s.new_fixed)
        screen=self.engine.act(self.key,('chart','home'))
        self.assertEqual(draft,s.new_fixed);self.assertIsNone(s.stage)
        self.assertIn(('learning_resume',),[a for row in screen.rows for _,a in row])
        self.engine.act(self.key,('learning_resume',))
        self.assertEqual(stage,s.stage);self.assertEqual(draft,s.new_fixed)
        self.assertEqual(before,self.financial())

    def test_learning_preserves_new_fixed_draft(self):
        self.engine.begin_new_fixed(self.key)
        s=self.engine.session(self.key);stage=s.stage;draft=copy.deepcopy(s.new_fixed)
        self.engine.open_learning(self.key,'previsoes')
        self.assertEqual(draft,s.new_fixed);self.assertIsNone(s.stage)
        self.engine.act(self.key,('learning_resume',))
        self.assertEqual(stage,s.stage);self.assertEqual(draft,s.new_fixed)

    def test_dashboard_refresh_reloads_balance_and_navigation_keeps_month(self):
        first=self.engine.handle_text(self.key,'dashboard').image
        db.definir_saldo_inicial_conta_mes('2026-09','Itaú',1300)
        second=self.engine.act(self.key,('chart','home')).image
        self.assertNotEqual(first['cards'][0]['value'],second['cards'][0]['value'])
        next_screen=self.engine.act(self.key,('dashboard_month',1,'home'))
        self.assertIn('Outubro',next_screen.image['subtitle']);self.assertIn('projeção',next_screen.image['subtitle'])
        prev=self.engine.act(self.key,('dashboard_month',-1,'home'))
        self.assertIn('Setembro',prev.image['subtitle'])

    def test_dashboard_equals_canonical_summary_and_adds_context_blocks(self):
        before=self.financial();summary=resumir_saldo(svc.obter_metricas_resultado_mes('2026-09'))
        spec=self.engine.handle_text(self.key,'dashboard').image
        self.assertEqual(ux.money(summary['saldo_atual']),spec['cards'][0]['value'])
        self.assertEqual(ux.money(abs(summary['reservas_liquidas'])),spec['cards'][1]['value'])
        self.assertEqual(ux.money(summary['saldo_final']),spec['hero']['value'])
        self.assertEqual([],spec['bars']);self.assertEqual([],spec['details']);self.assertEqual(2,len(spec['cards']))
        with Image.open(painel(spec)) as img:
            self.assertEqual(720,img.width);self.assertLess(img.height,1900)
        self.assertEqual('dashboard',spec['layout']);self.assertGreaterEqual(len(spec['dashboard_sections']),3)
        self.assertEqual(before,self.financial())

    def test_privacy_removes_receivables_and_neutralizes_color(self):
        self.engine.session(self.key).privacy=True
        spec=self.engine.handle_text(self.key,'dashboard').image
        self.assertEqual('neutral',spec['hero_tone'])
        self.assertNotIn('R$',json.dumps(spec,ensure_ascii=False))

    def test_negative_forecast_and_unconfigured_base_are_not_positive_signals(self):
        db.definir_saldo_inicial_conta_mes('2026-09','Itaú',-100)
        self.assertEqual('danger',self.engine.handle_text(self.key,'dashboard').image['hero_tone'])
        self.engine.session(self.key).month='2026-08'
        spec=self.engine.handle_text(self.key,'dashboard').image
        self.assertEqual('warning',spec['hero_tone']);self.assertIn('saldos',spec['footer'])

    def test_help_dashboard_and_beginner_alias_are_native(self):
        for command in ('/help dashboard','help painel','/help primeiros passos'):
            self.assertIsInstance(self.engine.handle_text(self.key,command),ux.Screen)
        self.assertIn('configurável',ux.HELP_TOPICS['faturas']['body'])

    def test_lesson_phrase_as_description_is_preserved(self):
        self.engine.begin(self.key,'receita');self.engine.handle_text(self.key,'20')
        self.engine.handle_text(self.key,'aprender primeiros passos')
        self.assertEqual('aprender primeiros passos',self.engine.session(self.key).draft['descricao'])

    def test_help_does_not_discard_fixed_edit_and_can_resume(self):
        db.inserir_compromisso(dict(tipo='fixo',nome='Internet',categoria='Casa',valor=80,data_inicio='2026-09-01',dia_vencimento=10,conta_pagamento='Itaú',forma_pagamento='pix',ativo=1))
        with db.get_connection() as c:ident=c.execute('SELECT id FROM compromissos').fetchone()[0]
        self.engine.act(self.key,('fixed_field',ident,'valor'))
        s=self.engine.session(self.key);stage=s.stage;draft=copy.deepcopy(s.fixed_edit)
        screen=self.engine.act(self.key,('topic','compromissos'))
        self.assertEqual(draft,s.fixed_edit);self.assertIsNone(s.stage)
        self.assertIn(('learning_resume',),[a for row in screen.rows for _,a in row])
        self.engine.act(self.key,('learning_resume',))
        self.assertEqual(stage,s.stage);self.assertEqual(draft,s.fixed_edit)


class DashboardSlashHandler(unittest.IsolatedAsyncioTestCase):
    async def test_command_handler_uses_native_dashboard_and_keeps_registration_draft(self):
        import app
        engine=ux.Experience(date_provider=lambda:date(2026,9,30));key='1:1'
        engine.begin(key,'receita');s=engine.session(key);draft=copy.deepcopy(s.draft)
        update=SimpleNamespace(effective_user=SimpleNamespace(id=1),effective_chat=SimpleNamespace(id=1))
        with patch.object(app,'bloquear_se_nao_autorizado',AsyncMock(return_value=False)),patch.object(app,'bloquear_se_assessor_travado',AsyncMock(return_value=False)),patch.object(app,'registrar_mensagem_update'),patch.object(ux,'EXPERIENCE',engine),patch.object(ux,'send_screen',AsyncMock()) as send,patch.object(ux.Experience,'act',return_value=ux.Screen('Painel')) as act:
            await app.dashboard_command(update,SimpleNamespace(args=['2026-10']))
            act.assert_called_once_with(key,('chart','home'));self.assertEqual('2026-10',s.month)
            send.assert_awaited_once();self.assertEqual(draft,s.draft)

    async def test_invalid_period_does_not_replace_selected_month(self):
        import app
        engine=ux.Experience(date_provider=lambda:date(2026,9,30));key='1:1'
        update=SimpleNamespace(effective_user=SimpleNamespace(id=1),effective_chat=SimpleNamespace(id=1))
        with patch.object(app,'bloquear_se_nao_autorizado',AsyncMock(return_value=False)),patch.object(app,'bloquear_se_assessor_travado',AsyncMock(return_value=False)),patch.object(app,'registrar_mensagem_update'),patch.object(ux,'EXPERIENCE',engine),patch.object(ux,'send_screen',AsyncMock()) as send:
            await app.dashboard_command(update,SimpleNamespace(args=['2026-13']))
            self.assertEqual('2026-09',engine.session(key).month)
            self.assertIsNone(send.await_args.args[1].image)
