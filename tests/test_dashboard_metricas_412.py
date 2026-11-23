"""Dashboard enriquecido: períodos comparáveis, privacidade e consulta sem gravação."""
import copy,importlib.util,json,tempfile,unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import database as db,services as svc,telegram_experiencia as ux
from telegram_visuais import painel
from saldo_resumo import resumir_saldo

class DashboardMetricas(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        for module in (db,svc):
            p=patch.object(module,'DB_PATH',Path(self.tmp.name)/'fixture.db');p.start();self.addCleanup(p.stop)
        db.init_db();db.definir_saldo_inicial_conta_mes('2026-09','Itaú',1000)
        self.engine=ux.Experience(date_provider=lambda:date(2026,9,15));self.key='dashboard-teste'
    def tx(self,day,value,kind='despesa',category='Casa'):
        return db.inserir_transacao(dict(data=day,tipo=kind,valor=value,categoria=category,descricao='Fictício',conta='Itaú',forma_pagamento='pix'))
    def financial(self):
        with db.get_connection() as c:return {t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in ('transacoes','compromissos','fatura_movimentos','saldos_mensais_contas')}
    def test_overview_has_activity_obligations_and_priorities_with_canonical_balance(self):
        self.tx('2026-09-10',120);self.tx('2026-09-11',500,'receita');before=self.financial()
        spec=self.engine.act(self.key,('chart','home')).image;summary=resumir_saldo(svc.obter_metricas_resultado_mes('2026-09'))
        self.assertEqual(ux.money(summary['saldo_final']),spec['hero']['value']);self.assertEqual(ux.money(summary['saldo_atual']),spec['cards'][0]['value'])
        metrics=spec['dashboard_sections'][0]['items'];self.assertEqual('R$ 500,00',metrics[0]['value']);self.assertEqual('R$ 120,00',metrics[1]['value'])
        self.assertEqual(before,self.financial())
    def test_credit_uses_invoice_month_and_fixed_does_not_become_registered_expense(self):
        spec=importlib.util.spec_from_file_location('credit_dashboard',Path(__file__).resolve().parents[1]/'migrations/0004_competencia_faturas.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with db.get_connection() as c:module.upgrade(c)
        db.inserir_transacao(dict(data='2026-08-27',data_compra='2026-08-27',competencia_fatura='2026-09',tipo='despesa',valor=100,categoria='Teste',descricao='Compra fictícia',conta='Nubank',forma_pagamento='crédito'))
        db.inserir_compromisso(dict(tipo='fixo',nome='Fixo fictício',categoria='Teste',valor=50,data_inicio='2026-09-01',dia_vencimento=10,conta_pagamento='Nubank',forma_pagamento='crédito',ativo=1))
        before=self.financial();image=self.engine.act(self.key,('chart','home')).image
        self.assertEqual('R$ 100,00',image['dashboard_sections'][0]['items'][1]['value'])
        self.assertEqual(100,image['dashboard_data']['series'][-1]['spending']);self.assertEqual(0,image['dashboard_data']['series'][-2]['spending'])
        self.assertEqual(ux.money(resumir_saldo(svc.obter_metricas_resultado_mes('2026-09'))['saldo_final']),image['hero']['value']);self.assertEqual(before,self.financial())
    def test_month_comparison_uses_same_day_and_excludes_later_previous_expense(self):
        self.tx('2026-08-10',100);self.tx('2026-08-28',900);self.tx('2026-09-10',150)
        comparison=self.engine.act(self.key,('chart','home')).image['dashboard_data']['comparison']
        self.assertEqual(100,comparison['previous_spending']);self.assertEqual(150,comparison['current_spending']);self.assertEqual(50,comparison['percent'])
        self.assertIn('15 dias',comparison['mode'])
    def test_short_previous_month_clips_both_comparison_windows(self):
        self.engine.date_provider=lambda:date(2026,3,31);self.engine.session(self.key).month='2026-03'
        self.tx('2026-02-28',100);self.tx('2026-03-28',100);self.tx('2026-03-30',900)
        comparison=self.engine.act(self.key,('chart','home')).image['dashboard_data']['comparison']
        self.assertEqual(0,comparison['percent']);self.assertEqual(100,comparison['current_spending']);self.assertIn('28 dias',comparison['mode'])
    def test_no_previous_history_does_not_fabricate_percentage(self):
        self.tx('2026-09-10',100);spec=self.engine.act(self.key,('chart','evolution')).image
        self.assertIsNone(spec['dashboard_data']['comparison']);self.assertIn('Sem base',json.dumps(spec))
    def test_future_does_not_compare_projected_and_realized_or_extend_history(self):
        self.tx('2026-09-10',100);self.engine.session(self.key).month='2026-10'
        spec=self.engine.act(self.key,('chart','evolution')).image
        self.assertIsNone(spec['dashboard_data']['comparison']);self.assertEqual('2026-09',spec['dashboard_data']['series'][-1]['month'])
        self.assertIn('2026-09',spec['subtitle'])
        spec=self.engine.act(self.key,('chart','diagnosis')).image;self.assertIn('Período futuro',json.dumps(spec,ensure_ascii=False))
    def test_empty_and_negative_reserve_do_not_divide_by_zero_or_negative_denominator(self):
        spec=self.engine.act(self.key,('chart','diagnosis')).image;self.assertIsNone(spec['dashboard_data']['coverage'])
        import dashboard_metricas as module
        with patch.object(module,'resumir_saldo',return_value=dict(saldo_atual=1000,saldo_final=1050,reservas_liquidas=-50,a_receber=0,base_configurada=True,herdado_auto=False,revisar=False)):
            self.assertIsNone(self.engine.act(self.key,('chart','diagnosis')).image['dashboard_data']['coverage'])
    def test_privacy_removes_money_ratios_history_and_warning_colors_from_every_panel(self):
        self.tx('2026-09-10',123.45);self.engine.session(self.key).privacy=True
        for view in ('home','evolution','diagnosis'):
            spec=self.engine.act(self.key,('chart',view)).image;serialized=json.dumps(spec,ensure_ascii=False)
            self.assertNotIn('R$',serialized);self.assertNotIn('123.45',serialized);self.assertEqual({},spec['dashboard_data']);self.assertEqual('neutral',spec['hero_tone'])
    def test_all_new_navigation_preserves_money_and_suspended_form(self):
        before=self.financial();self.engine.begin(self.key,'receita');draft=copy.deepcopy(self.engine.session(self.key).draft)
        self.engine.act(self.key,('chart','home'))
        for command in ('dashboard','dashboard evolucao','dashboard diagnostico','dashboard evolucao 2026-08','dashboard diagnostico 2026-10'):
            self.assertIsNotNone(self.engine.handle_text(self.key,command).image)
        for view in ('home','evolution','diagnosis'):
            screen=self.engine.act(self.key,('chart',view))
            for row in screen.rows:
                for _,action in row:
                    if action[0]=='chart':self.assertIsNotNone(self.engine.act(self.key,action).image)
        self.engine.act(self.key,('resume_suspended',));self.assertEqual(draft,self.engine.session(self.key).draft);self.assertEqual(before,self.financial())
    def test_all_visuals_render_bounded_png_with_long_labels_and_large_values(self):
        self.tx('2026-09-10',9999999,category='Categoria muito longa '*12)
        for view in ('home','evolution','diagnosis'):
            with Image.open(painel(self.engine.act(self.key,('chart',view)).image)) as image:
                self.assertEqual('PNG',image.format);self.assertEqual(720,image.width);self.assertLess(image.height,2300)
