"""V39: regressao sintetica, sem Telegram, tokens ou servicos externos."""
import calendar
import contextlib
import copy
import importlib.util
import json
import os
import shutil
import socket
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import database as db
import services as svc
import compromissos as comp
import conciliacao as conc
import telegram_experiencia as ux
import telegram_registros as reg
import faturas_competencia as fc

spec = importlib.util.spec_from_file_location('migration_runner_v39_tests', ROOT/'migrations.py')
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)

class Today(date):
    @classmethod
    def today(cls):
        return cls(2026, 9, 30)

class Now(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 30, 12, 0, tzinfo=tz)


def dados(**kw):
    result = dict(data='2026-09-25', tipo='despesa', valor=150.0,
                  categoria='Alimenta\u00e7\u00e3o', descricao='Mercado teste',
                  conta='Ita\u00fa', forma_pagamento='cr\u00e9dito', parcelas_total=1,
                  competencia_fatura='2026-10')
    result.update(kw)
    return result


class Ambiente(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root/'financeiro.db'
        self.patches = [patch.object(db,'DB_PATH',self.path), patch.object(svc,'DB_PATH',self.path),
            patch.object(svc,'date',Today), patch.object(comp,'date',Today),
            patch.object(conc,'datetime',Now),
            patch.dict(os.environ,{'ASSESSOR_FATURA_DIA_CORTE':'25','ASSESSOR_FATURA_CORTES':'{}'}),
            patch.object(socket.socket,'connect',side_effect=AssertionError('Rede proibida nos testes'))]
        for p in self.patches:
            p.start();self.addCleanup(p.stop)
        db.init_db()
        runner.apply_migrations(self.path, ROOT/'migrations', self.root/'backups', executed_by='testes_v39')
        self.exp = ux.Experience(date_provider=lambda:date(2026,9,30))
        self.key = 'usuario-teste'
        self.counter = 0

    def record(self, **kwargs):
        self.counter += 1
        return reg.confirmar_registro(dados(**kwargs), 'compra-'+str(self.counter), self.key)

    def invoice(self, month, account='Ita\u00fa'):
        return comp.calcular_fatura_unificada(month,account,somente_cartao=True)

    def parse(self, text='gastei 150 no mercado no credito itau em 25/09/2026'):
        screen = self.exp.parse_draft(self.key, text)
        # Os testes de fatura existentes partem de uma compra a vista. Na v39.1,
        # frases de despesa sem parcelamento explicito recuperam a pergunta que
        # ja existia no fluxo por botoes; responda Nao para chegar ao mesmo ponto.
        if self.exp.session(self.key).stage == 'installment_choice':
            screen = self.exp.answer(self.key, 'não')
        return screen

    def choose(self, month='2026-10'):
        return self.exp.answer(self.key,month)

    def count(self):
        with db.get_connection() as conn:
            return conn.execute('SELECT count(*) FROM transacoes').fetchone()[0]


class ParcelamentoTexto(Ambiente):
    def test_gastei_apenas_valor_pergunta_parcelamento(self):
        # Fase 2 (P7): a pergunta de parcelas só aparece no crédito, depois da forma.
        screen = self.exp.parse_draft(self.key, 'gastei 700')
        self.assertEqual('description', self.exp.session(self.key).stage)
        self.assertNotIn('Essa despesa foi parcelada?', screen.text)

    def test_gastei_apenas_valor_nao_segue_para_descricao(self):
        screen = self.exp.parse_draft(self.key, 'gastei 700')
        self.assertEqual('description', self.exp.session(self.key).stage)
        self.assertIn('Com o que foi?', screen.text)

    def test_credito_completo_pergunta_e_preserva_credito_ao_responder_nao(self):
        screen = self.exp.parse_draft(self.key, 'gastei 700 almoco credito itau em 25/09/2026')
        self.assertEqual('installment_choice', self.exp.session(self.key).stage)
        self.assertIn('Essa despesa foi parcelada?', screen.text)
        self.exp.answer(self.key, 'não')
        session = self.exp.session(self.key)
        self.assertEqual('billing_month', session.stage)
        self.assertEqual('crédito', session.draft['forma_pagamento'])

    def test_pix_explicito_nao_pergunta_parcelamento(self):
        self.exp.parse_draft(self.key, 'gastei 700 almoco pix itau em 25/09/2026')
        self.assertEqual('confirm', self.exp.session(self.key).stage)

    def test_parcelas_explicitas_nao_reperguntam(self):
        self.exp.parse_draft(self.key, 'comprei celular em 3x de 100 credito itau em 25/09/2026')
        session = self.exp.session(self.key)
        self.assertEqual('billing_month', session.stage)
        self.assertEqual(3, session.draft['parcelas_total'])

    def test_palavra_parcelado_pede_quantidade_sem_sim_nao(self):
        self.exp.parse_draft(self.key, 'gastei 700 parcelado credito itau em 25/09/2026')
        session = self.exp.session(self.key)
        self.assertEqual('description', session.stage)
        self.assertTrue(session.draft['_installments_pending'])
        self.exp.answer(self.key, 'Compra teste')
        self.assertEqual('installments', session.stage)


class Calendario(Ambiente):
    def test_dias_24_25_fim_todos_meses(self):
        for month in range(1,13):
            for day in (24,25,calendar.monthrange(2026,month)[1]):
                with self.subTest(month=month,day=day):
                    t=dados(data=f'2026-{month:02d}-{day:02d}')
                    self.assertEqual(day>=25,fc.precisa_escolher(t))
                    self.assertEqual(2 if day>=25 else 1,len(fc.opcoes_fatura(t)))

    def test_fevereiro_bissexto(self):
        self.assertEqual(('2028-02','2028-03'),fc.opcoes_fatura(dados(data='2028-02-29')))

    def test_dezembro_janeiro(self):
        self.assertEqual(('2026-12','2027-01'),fc.opcoes_fatura(dados(data='2026-12-25')))

    def test_configuracao_por_cartao_sem_alterar_padrao(self):
        with patch.dict(os.environ,{'ASSESSOR_FATURA_CORTES':'{"Itau":20,"Nubank":31}'}):
            self.assertTrue(fc.precisa_escolher(dados(data='2026-09-20')))
            self.assertFalse(fc.precisa_escolher(dados(data='2026-09-20',conta='Outro')))
            self.assertEqual(28,fc.dia_corte('Nubank','2026-02-28'))

    def test_configuracao_invalida_nao_inventa_corte(self):
        for value in ('0','32','25.5','True'):
            with self.subTest(value=value),patch.dict(os.environ,{'ASSESSOR_FATURA_DIA_CORTE':value}):
                with self.assertRaises(ValueError):fc.precisa_escolher(dados())
        for value in ('[]','null','{"Itau":true}','INVALID'):
            with self.subTest(value=value),patch.dict(os.environ,{'ASSESSOR_FATURA_CORTES':value}):
                with self.assertRaises(ValueError):fc.precisa_escolher(dados())

    def test_meios_nao_credito_sem_fatura(self):
        for method in ('pix','d\u00e9bito','dinheiro','boleto','transfer\u00eancia'):
            with self.subTest(method=method):
                self.assertFalse(fc.precisa_escolher(dados(forma_pagamento=method)))
        self.assertFalse(fc.precisa_escolher(dados(tipo='receita')))

    def test_mes_invalido_rejeitado(self):
        for value in ('2026-13','2026-00','26-09','2026-9','2026-09-01','',None):
            with self.subTest(value=value):
                with self.assertRaises((ValueError,TypeError)):fc.validar_mes(value)


class Fluxo(Ambiente):
    def test_frase_completa_pergunta_antes_de_gravar(self):
        screen=self.parse()
        self.assertEqual('billing_month',self.exp.session(self.key).stage)
        self.assertIn('Setembro/2026',str(screen.rows));self.assertIn('Outubro/2026',str(screen.rows))
        self.assertEqual(0,self.count())

    def test_compra_24_registrada_30_sem_pergunta(self):
        screen=self.parse('gastei 150 no mercado credito itau em 24/09/2026')
        self.assertEqual('confirm',self.exp.session(self.key).stage)
        self.assertEqual('2026-09',self.exp.session(self.key).draft['competencia_fatura'])
        self.assertIn('24/09/2026',screen.text)

    def test_hoje_25_inclusivo(self):
        self.exp=ux.Experience(date_provider=lambda:date(2026,9,25))
        self.parse('gastei 150 no mercado credito itau')
        self.assertEqual('billing_month',self.exp.session(self.key).stage)

    def test_guiado_completo_inclui_fatura_depois_das_parcelas(self):
        self.exp.begin(self.key,'despesa')
        # Fase 2: valor, descrição, forma; parcelas só no crédito; data padrão = hoje (25/09).
        for answer in ('100,01','Eletronico teste','crédito','sim','Itau','3'):
            self.exp.answer(self.key,answer)
        s=self.exp.session(self.key)
        self.assertEqual('billing_month',s.stage)
        screen=self.choose()
        self.assertEqual('confirm',s.stage)
        self.assertIn('Outubro',screen.text);self.assertIn('Dezembro',screen.text)
        self.assertEqual(0,self.count())

    def test_nao_credito_texto_nao_pergunta(self):
        for method in ('pix','debito','dinheiro','boleto','transferencia'):
            with self.subTest(method=method):
                self.exp.invalidate(self.key)
                self.parse(f'gastei 150 no mercado {method} itau em 25/09/2026')
                s=self.exp.session(self.key)
                self.assertEqual('confirm',s.stage)
                self.assertNotIn('competencia_fatura',s.draft)

    def test_receita_nao_pergunta(self):
        self.parse('recebi 150 salario pix itau em 25/09/2026')
        self.assertEqual('confirm',self.exp.session(self.key).stage)
        self.assertNotIn('competencia_fatura',self.exp.session(self.key).draft)

    def test_escolhas_com_nomes_e_alias(self):
        for value,expected in [('mes vigente','2026-09'),('proximo mes','2026-10'),('Outubro/2026','2026-10'),('Setembro 2026','2026-09')]:
            with self.subTest(value=value):
                self.exp.invalidate(self.key);self.parse();screen=self.choose(value)
                self.assertEqual('confirm',self.exp.session(self.key).stage)
                self.assertEqual(expected,self.exp.session(self.key).draft['competencia_fatura'])
                self.assertEqual(0,self.count())

    def test_mes_fora_opcoes_mantem_rascunho(self):
        self.parse();before=copy.deepcopy(self.exp.session(self.key).draft)
        self.choose('2026-11')
        self.assertEqual(before,self.exp.session(self.key).draft)
        self.assertEqual('billing_month',self.exp.session(self.key).stage)

    def test_editar_conta_invalida_fatura(self):
        self.parse();self.choose();self.exp.act(self.key,('edit','account'));self.exp.answer(self.key,'Nubank')
        self.assertEqual('billing_month',self.exp.session(self.key).stage)
        self.assertNotIn('competencia_fatura',self.exp.session(self.key).draft)

    def test_editar_data_anterior_corte_remove_fatura_futura(self):
        self.parse();self.choose();self.exp.act(self.key,('edit','date'));self.exp.answer(self.key,'24/09/2026')
        s=self.exp.session(self.key)
        self.assertEqual('confirm',s.stage);self.assertEqual('2026-09',s.draft['competencia_fatura'])
        self.assertEqual('2026-09-24',s.draft['data_compra'])

    def test_editar_data_apos_corte_repergunta(self):
        self.parse();self.choose();self.exp.act(self.key,('edit','date'));self.exp.answer(self.key,'26/09/2026')
        self.assertEqual('billing_month',self.exp.session(self.key).stage)

    def test_editar_forma_pix_limpa_campos_credito(self):
        self.parse();self.choose();self.exp.act(self.key,('edit','method'));self.exp.answer(self.key,'pix')
        s=self.exp.session(self.key)
        self.assertEqual('confirm',s.stage);self.assertNotIn('competencia_fatura',s.draft);self.assertNotIn('data_compra',s.draft)
        self.exp.act(self.key,('commit',s.draft['key']))
        row=dict(db.buscar_todas_transacoes()[0]);self.assertIsNone(row['competencia_fatura'])

    def test_editar_parcelas_repergunta_e_recalcula_centavos(self):
        self.parse();self.choose();self.exp.act(self.key,('edit','installments'));self.exp.answer(self.key,'3')
        self.assertEqual('billing_month',self.exp.session(self.key).stage)
        self.choose();s=self.exp.session(self.key)
        self.assertEqual(['2026-10','2026-11','2026-12'],[x['data'].strftime('%Y-%m') for x in ux.installment_plan(s.draft)])

    def test_editar_valor_nao_esquece_fatura(self):
        self.parse();self.choose();self.exp.act(self.key,('edit','amount'));self.exp.answer(self.key,'199,99')
        s=self.exp.session(self.key)
        self.assertEqual('confirm',s.stage);self.assertEqual('2026-10',s.draft['competencia_fatura'])

    def test_cancelar_na_pergunta_sem_escrita(self):
        self.parse();self.exp.act(self.key,('cancel',))
        self.assertEqual(0,self.count());self.assertIsNone(self.exp.session(self.key).draft)

    def test_cancelar_na_confirmacao_sem_escrita(self):
        self.parse();self.choose();self.exp.act(self.key,('cancel',))
        self.assertEqual(0,self.count())

    def test_ajuda_nao_perde_rascunho(self):
        self.parse();before=copy.deepcopy(self.exp.session(self.key).draft)
        self.exp.handle_text(self.key,'ajuda');self.exp.act(self.key,('flow_resume',))
        self.assertEqual(before,self.exp.session(self.key).draft)
        self.assertEqual('billing_month',self.exp.session(self.key).stage)

    def test_pausar_e_retomar_mantem_fatura(self):
        self.parse();self.choose();s=self.exp.session(self.key);before=copy.deepcopy(s.draft)
        self.exp.act(self.key,('view','history'));self.exp.act(self.key,('resume_suspended',))
        self.assertEqual(before,s.draft);self.assertEqual('confirm',s.stage)

    def test_callback_anterior_expira_apos_edicao(self):
        self.parse();self.choose();s=self.exp.session(self.key);old=s.draft['key']
        self.exp.act(self.key,('edit','account'));self.exp.answer(self.key,'Nubank');self.choose()
        self.exp.act(self.key,('commit',old));self.assertEqual(0,self.count())
        self.exp.act(self.key,('commit',s.draft['key']));self.assertEqual(1,self.count())

    def test_duplo_clique_interface_nao_duplica(self):
        self.parse();self.choose();key=self.exp.session(self.key).draft['key']
        self.exp.act(self.key,('commit',key));self.exp.act(self.key,('commit',key))
        self.assertEqual(1,self.count())

    def test_confirmacao_revalida_rascunho_alterado(self):
        self.parse();self.choose();s=self.exp.session(self.key);s.draft['conta']='Nubank'
        self.exp.act(self.key,('commit',s.draft['key']))
        self.assertEqual('billing_month',s.stage);self.assertEqual(0,self.count())

    def test_simulacao_pergunta_e_nao_salva(self):
        self.exp.parse_draft(self.key,'gastei 100 celular credito itau em 25/09/2026',simulation=True)
        self.assertEqual('installment_choice',self.exp.session(self.key).stage)
        self.exp.answer(self.key,'não')
        self.assertEqual('billing_month',self.exp.session(self.key).stage)
        screen=self.choose();self.assertIn('Outubro',screen.text)
        self.exp.act(self.key,('commit',self.exp.session(self.key).draft['key']))
        self.assertEqual(0,self.count())

    def test_entrada_ia_usa_mesmo_fluxo(self):
        screen=self.exp._ai_registration_preview(self.key, dict(query_type='register_expense',
            amount=150,installments=1,description='Mercado teste',category='Alimentacao',
            account='Itau',payment_method='credito'), 'despesa teste')
        self.assertEqual('billing_month',self.exp.session(self.key).stage)
        self.assertIn('Outubro/2026',str(screen.rows))
        self.assertEqual(0,self.count())


class Persistencia(Ambiente):
    def test_compra_setembro_fatura_outubro_sem_mudar_data(self):
        result=self.record();row=result['linhas'][0]
        self.assertEqual('2026-09-25',row['data']);self.assertEqual('2026-09-25',row['data_compra'])
        self.assertEqual('2026-10',row['competencia_fatura'])
        self.assertEqual(0,self.invoice('2026-09')['valor_bruto']);self.assertEqual(150,self.invoice('2026-10')['valor_bruto'])

    def test_escolher_mes_vigente(self):
        self.record(competencia_fatura='2026-09')
        self.assertEqual(150,self.invoice('2026-09')['valor_bruto']);self.assertEqual(0,self.invoice('2026-10')['valor_bruto'])

    def test_centavos_cronograma_e_grupo(self):
        r=self.record(valor=100.01,parcelas_total=3)
        rows=r['linhas']
        self.assertEqual([33.34,33.34,33.33],[x['valor'] for x in rows])
        self.assertEqual(['2026-10','2026-11','2026-12'],[x['competencia_fatura'] for x in rows])
        self.assertEqual(['2026-09-25']*3,[x['data_compra'] for x in rows])
        self.assertEqual([r['ids'][0]]*3,[x['parcelamento_id'] for x in rows])
        self.assertAlmostEqual(100.01,sum(x['valor'] for x in rows),2)
        for i,mes in enumerate(('2026-10','2026-11','2026-12')):
            self.assertEqual(rows[i]['valor'],self.invoice(mes)['valor_bruto'])

    def test_centavos_de_1_a_60_parcelas(self):
        for n in range(1,61):
            with self.subTest(parcelas=n):
                self.counter+=1
                r=reg.confirmar_registro(dados(valor=123.47,parcelas_total=n),str(self.counter),self.key)
                cents=[round(x['valor']*100) for x in r['linhas']]
                self.assertEqual(12347,sum(cents));self.assertLessEqual(max(cents)-min(cents),1)
                self.assertEqual(n,len(r['ids']))

    def test_virada_de_ano_parcelada(self):
        r=self.record(data='2026-12-31',competencia_fatura='2027-01',parcelas_total=3)
        self.assertEqual(['2027-01','2027-02','2027-03'],[x['competencia_fatura'] for x in r['linhas']])
        self.assertEqual('2026-12-31',r['linhas'][0]['data_compra'])
        self.assertEqual('2027-02-28',comp.incluir_transacoes_mes_na_projecao('2027-02')[0]['data'])

    def test_obrigatorio_escolher_no_backend(self):
        t=dados();t.pop('competencia_fatura')
        with self.assertRaises(ValueError):reg.confirmar_registro(t,'novo',self.key)
        self.assertEqual(0,self.count())

    def test_competencia_invalida_nao_grava(self):
        for month in ('2026-08','2026-11','2026-99','bad'):
            with self.subTest(month=month),self.assertRaises(ValueError):self.record(competencia_fatura=month)
        self.assertEqual(0,self.count())

    def test_data_compra_falsa_rejeitada(self):
        with self.assertRaises(ValueError):self.record(data_compra='2026-10-01')
        self.assertEqual(0,self.count())

    def test_menos_de_um_centavo_por_parcela_rejeita(self):
        with self.assertRaises(ValueError):self.record(valor=.02,parcelas_total=3)
        self.assertEqual(0,self.count())

    def test_idempotencia_mesma_chave(self):
        a=reg.confirmar_registro(dados(),'unica',self.key);b=reg.confirmar_registro(dados(),'unica',self.key)
        self.assertEqual(a['ids'],b['ids']);self.assertTrue(b['repetido']);self.assertEqual(1,self.count())

    def test_mesma_chave_outra_fatura_nao_reutiliza(self):
        reg.confirmar_registro(dados(),'unica',self.key)
        with self.assertRaises(ValueError):reg.confirmar_registro(dados(competencia_fatura='2026-09'),'unica',self.key)
        self.assertEqual(1,self.count())

    def test_mesma_chave_outro_usuario_bloqueada(self):
        reg.confirmar_registro(dados(),'unica',self.key)
        with self.assertRaises(ValueError):reg.confirmar_registro(dados(),'unica','outro')
        self.assertEqual(1,self.count())

    def test_rollback_atomico_falha_parcela_2(self):
        with db.get_connection() as conn:
            conn.execute("CREATE TRIGGER falhar_parcela BEFORE INSERT ON transacoes WHEN NEW.parcela_atual=2 BEGIN SELECT RAISE(ABORT,'falha induzida'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.record(parcelas_total=3)
        self.assertEqual(0,self.count())
        with db.get_connection() as conn:
            self.assertEqual(0,conn.execute("SELECT count(*) FROM auditoria_eventos WHERE entidade='telegram_registro'").fetchone()[0])

    def test_rollback_atomico_falha_auditoria(self):
        with db.get_connection() as conn:
            conn.execute("CREATE TRIGGER falhar_auditoria BEFORE INSERT ON auditoria_eventos WHEN NEW.entidade='telegram_registro' BEGIN SELECT RAISE(ABORT,'falha induzida'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.record(parcelas_total=3)
        self.assertEqual(0,self.count())

    def test_desfazer_remove_todas_parcelas_uma_vez(self):
        self.record(parcelas_total=3)
        self.assertTrue(reg.desfazer_registro('compra-1',self.key));self.assertFalse(reg.desfazer_registro('compra-1',self.key))
        self.assertEqual(0,self.count());self.assertEqual(0,self.invoice('2026-10')['valor_bruto'])

    def test_desfazer_bloqueia_competencia_alterada(self):
        r=self.record()
        with db.get_connection() as conn:conn.execute('UPDATE transacoes SET competencia_fatura=? WHERE id=?',('2026-11',r['ids'][0]))
        with self.assertRaises(ValueError):reg.desfazer_registro('compra-1',self.key)
        self.assertEqual(1,self.count())

    def test_alteracao_conta_de_compra_postergada_exige_revisao(self):
        r=self.record()
        with self.assertRaises(ValueError):db.atualizar_conta_por_id(r['ids'][0],'Nubank')
        self.assertEqual('Ita\u00fa',db.buscar_transacao_por_id(r['ids'][0])['conta'])

    def test_alteracao_forma_de_compra_postergada_exige_revisao(self):
        r=self.record()
        with self.assertRaises(ValueError):db.atualizar_forma_por_id(r['ids'][0],'pix')
        self.assertEqual('cr\u00e9dito',db.buscar_transacao_por_id(r['ids'][0])['forma_pagamento'])

    def test_categoria_editavel_preserva_competencia(self):
        r=self.record();db.atualizar_categoria_por_id(r['ids'][0],'Outros')
        self.assertEqual('2026-10',db.buscar_transacao_por_id(r['ids'][0])['competencia_fatura'])

    def test_migracao_obrigatoria_para_gravar_credito(self):
        db.DB_PATH=svc.DB_PATH=self.root/'legado.db';db.init_db()
        with self.assertRaises(ValueError):self.record()
        self.assertEqual(0,self.count())

    def test_legado_mesmo_dia_sem_redistribuicao(self):
        t=dados();t.pop('competencia_fatura');ident=db.inserir_transacao(t)
        self.assertEqual(150,self.invoice('2026-09')['valor_bruto'])
        self.assertEqual(0,self.invoice('2026-10')['valor_bruto'])
        self.assertIsNone(db.buscar_transacao_por_id(ident)['competencia_fatura'])

    def test_caminho_legado_direto_nao_pula_pergunta(self):
        t=dados();t.pop('competencia_fatura')
        self.assertIn('Nenhum',svc.registrar_transacao_unica(t))
        self.assertIn('Nenhum',svc.registrar_compra_parcelada(dict(t,parcelas_total=3)))
        self.assertEqual(0,self.count())


class Financeiro(Ambiente):
    def test_saldo_setembro_e_outubro(self):
        db.definir_saldo_inicial_mes('2026-09',1000)
        self.record()
        sep=svc.obter_metricas_resultado_mes('2026-09');october=svc.obter_metricas_resultado_mes('2026-10')
        self.assertEqual(1000,sep['saldo_projetado']);self.assertEqual(0,sep['saidas_nao_imediatas_realizadas'])
        self.assertEqual(1000,october['saldo_disponivel']);self.assertEqual(850,october['saldo_projetado'])
        self.assertEqual(150,october['saidas_nao_imediatas_realizadas'])

    def test_pagamento_nao_desconta_duas_vezes(self):
        db.definir_saldo_inicial_mes('2026-09',1000);self.record()
        before=svc.obter_metricas_resultado_mes('2026-10')
        result=reg.confirmar_pagamento_fatura(dict(ano_mes='2026-10',conta_cartao='Ita\u00fa',conta_origem='Ita\u00fa',modo='total',valor=150,saldo_esperado=150,data_movimento='2026-10-10'),'fatura',self.key)
        after=svc.obter_metricas_resultado_mes('2026-10')
        self.assertEqual(0,result['saldo_restante']);self.assertEqual(before['saldo_projetado'],after['saldo_projetado'])
        self.assertEqual(850,after['saldo_disponivel']);self.assertEqual(1,self.count())
        self.assertEqual(0,self.invoice('2026-10')['saldo_restante'])
        self.assertEqual(850,svc.obter_metricas_resultado_mes('2026-11')['saldo_projetado'])

    def test_pagamento_parcial_deixa_somente_restante(self):
        db.definir_saldo_inicial_mes('2026-09',1000);self.record()
        result=reg.confirmar_pagamento_fatura(dict(ano_mes='2026-10',conta_cartao='Ita\u00fa',conta_origem='Ita\u00fa',modo='parcial',valor=40,saldo_esperado=150,data_movimento='2026-10-10'),'parcial',self.key)
        self.assertEqual(110,result['saldo_restante'])
        self.assertEqual(850,svc.obter_metricas_resultado_mes('2026-10')['saldo_projetado'])

    def test_pagamento_primeira_fatura_nao_apaga_futuras(self):
        self.record(valor=300,parcelas_total=3)
        reg.confirmar_pagamento_fatura(dict(ano_mes='2026-10',conta_cartao='Ita\u00fa',conta_origem='Ita\u00fa',modo='total',valor=100,saldo_esperado=100,data_movimento='2026-10-10'),'fatura',self.key)
        self.assertEqual(0,self.invoice('2026-10')['saldo_restante']);self.assertEqual(100,self.invoice('2026-11')['saldo_restante']);self.assertEqual(100,self.invoice('2026-12')['saldo_restante'])

    def test_totais_categoria_e_resumo_mes_respeitam_fatura(self):
        self.record()
        self.assertEqual(0,db.total_por_tipo_mes('2026-09','despesa'));self.assertEqual(150,db.total_por_tipo_mes('2026-10','despesa'))
        self.assertEqual(150,db.total_por_categoria_mes('2026-10','Alimenta\u00e7\u00e3o'))
        self.assertEqual(150,list(db.resumo_mes('2026-10')[0])[0]['total'])

    def test_caixa_pix_debito_e_credito_independentes(self):
        db.definir_saldo_inicial_mes('2026-09',1000)
        self.record()
        for method in ('pix','d\u00e9bito','dinheiro','transfer\u00eancia'):
            t=dados(forma_pagamento=method,valor=10);t.pop('competencia_fatura');db.inserir_transacao(t)
        self.assertEqual(960,svc.obter_metricas_resultado_mes('2026-09')['saldo_disponivel'])
        self.assertEqual(150,self.invoice('2026-10')['saldo_restante'])

    def test_historico_data_real_e_filtro_fatura(self):
        r=self.record();s=self.exp.session(self.key);s.month='2026-09'
        text=self.exp.screen_history(s).text
        self.assertIn('25/09',text);self.assertIn('Outubro',text);self.assertEqual(1,len(self.exp.history_items(s)))
        self.exp.act(self.key,('history_basis','fatura'));self.assertEqual(0,len(self.exp.history_items(s)))
        s.month='2026-10';self.assertEqual(1,len(self.exp.history_items(s)))
        s.selected_id=r['ids'][0];text=self.exp.screen_transaction(s).text
        self.assertIn('25/09/2026',text);self.assertIn('Outubro 2026',text)

    def test_painel_analises_competencia_quando_mes_chega(self):
        self.record();self.exp=ux.Experience(date_provider=lambda:date(2026,10,31))
        s=self.exp.session(self.key);s.month='2026-10'
        self.assertIn('150,00',self.exp.screen_analytics(s).text)
        self.assertIn('fatura escolhida',self.exp.screen_analytics(s).text)
        s.month='2026-09';self.assertNotIn('150,00',self.exp.screen_analytics(s).text)

    def test_a_pagar_consistente(self):
        self.record();s=self.exp.session(self.key);s.month='2026-09'
        self.assertNotIn('150,00',self.exp.screen_pay(s).text)
        s.month='2026-10';self.assertIn('150,00',self.exp.screen_pay(s).text)

    def test_fatura_mesma_conta_e_separacao_outros_cartoes(self):
        self.record();self.record(conta='Nubank',valor=70,competencia_fatura='2026-09')
        self.assertEqual(150,self.invoice('2026-10','Ita\u00fa')['valor_bruto']);self.assertEqual(0,self.invoice('2026-10','Nubank')['valor_bruto'])
        self.assertEqual(70,self.invoice('2026-09','Nubank')['valor_bruto'])

    def test_previsao_nao_relacionada_continua_preservada(self):
        db.inserir_compromisso(dict(tipo='fixo',nome='Assinatura teste',categoria='Assinaturas',conta_pagamento='Ita\u00fa',forma_pagamento='cr\u00e9dito',valor=25,dia_vencimento=10,data_inicio='2026-09-01'))
        self.record()
        self.assertEqual(25,self.invoice('2026-09')['valor_bruto']);self.assertEqual(175,self.invoice('2026-10')['valor_bruto'])

    def test_periodo_grupo_parcelado_e_meses_futuros(self):
        self.record(parcelas_total=3,valor=300)
        g=svc.construir_grupos_parcelamentos()[0]
        self.assertEqual('2026-10',g['periodo_inicio']);self.assertEqual('2026-12',g['periodo_fim'])
        self.assertEqual({'2026-10':100,'2026-11':100,'2026-12':100},svc.calcular_parcelas_futuras_por_mes('2026-09'))

    def test_lista_parcelas_sem_duplicar_total(self):
        self.record(parcelas_total=3,valor=300)
        text=svc.listar_parcelas_mes('2026-10')
        self.assertIn('Total previsto no m\u00eas: R$ 100,00',text)
        self.assertNotIn('Total previsto no m\u00eas: R$ 200,00',text)


class Migracao(Ambiente):
    def test_migracao_registrada_com_checksum_e_versao4(self):
        with db.get_connection() as conn:
            self.assertEqual(4,conn.execute('PRAGMA user_version').fetchone()[0])
            self.assertEqual('competencia_faturas',conn.execute('SELECT name FROM schema_migrations WHERE version=4').fetchone()[0])
        self.assertTrue(runner.validate_compatibility(self.path,ROOT/'migrations',self.root/'backups').valid)

    def test_migracao_repetida_idempotente(self):
        result=runner.apply_migrations(self.path,ROOT/'migrations',self.root/'backups')
        self.assertEqual([],result['executed']);self.assertEqual(4,result['current_version'])

    def test_banco_antigo_preserva_linhas_e_schema_nulo(self):
        oldpath=self.path
        self.path=self.root/'old.db';db.DB_PATH=svc.DB_PATH=self.path;db.init_db()
        t=dados();t.pop('competencia_fatura');ident=db.inserir_transacao(t)
        before=dict(db.buscar_transacao_por_id(ident))
        runner.apply_migrations(self.path,ROOT/'migrations',self.root/'old-backups')
        after=dict(db.buscar_transacao_por_id(ident))
        self.assertEqual(before,{k:after[k] for k in before})
        self.assertIsNone(after['data_compra']);self.assertIsNone(after['competencia_fatura'])
        self.assertEqual(150,self.invoice('2026-09')['valor_bruto'])

    def test_consultas_legadas_sem_migracao_funcionam(self):
        self.path=self.root/'old.db';db.DB_PATH=svc.DB_PATH=self.path;db.init_db()
        t=dados();t.pop('competencia_fatura');db.inserir_transacao(t)
        self.assertEqual(150,self.invoice('2026-09')['valor_bruto'])
        self.assertEqual(150,db.total_por_tipo_mes('2026-09','despesa'))
        self.assertEqual(1,len(db.buscar_transacoes_por_mes('2026-09')))

    def test_desfazer_evento_v38_apos_migracao(self):
        self.path=self.root/'old.db';db.DB_PATH=svc.DB_PATH=self.path;db.init_db()
        t=dados();t.pop('competencia_fatura');ident=db.inserir_transacao(t)
        with db.get_connection() as conn:
            conn.row_factory=sqlite3.Row
            row=dict(conn.execute('SELECT * FROM transacoes WHERE id=?',(ident,)).fetchone())
            reg._auditar(conn,'antigo','confirmado',self.key,depois={'ids':[ident],'transacao':t,'linhas':[row]})
        runner.apply_migrations(self.path,ROOT/'migrations',self.root/'old-backups')
        self.assertTrue(reg.desfazer_registro('antigo',self.key));self.assertEqual(0,self.count())

    def test_repetir_evento_v38_apos_migracao_nao_exige_nova_fatura(self):
        self.path=self.root/'old.db';db.DB_PATH=svc.DB_PATH=self.path;db.init_db()
        t=dados();t.pop('competencia_fatura');ident=db.inserir_transacao(t)
        with db.get_connection() as conn:
            conn.row_factory=sqlite3.Row
            row=dict(conn.execute('SELECT * FROM transacoes WHERE id=?',(ident,)).fetchone())
            reg._auditar(conn,'antigo','confirmado',self.key,depois={'ids':[ident],'transacao':reg.validar_transacao(t),'linhas':[row]})
        runner.apply_migrations(self.path,ROOT/'migrations',self.root/'old-backups')
        result=reg.confirmar_registro(t,'antigo',self.key)
        self.assertTrue(result['repetido']);self.assertEqual(1,self.count())

    def test_schema_incompativel_impede_migracao(self):
        with db.get_connection() as conn:conn.execute('CREATE TABLE tabela_inesperada(x)')
        validation=runner.validate_compatibility(self.path,ROOT/'migrations',self.root/'backups')
        self.assertFalse(validation.valid)


if __name__=='__main__':
    unittest.main(verbosity=2)
