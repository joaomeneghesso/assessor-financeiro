"""Bloco B: saldo inicial por texto (B3), agenda na virada do mês (B7) e
data da compra na listagem da fatura (R6). Sempre em banco temporário."""
import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import assessor_orientacao as orient
import database as db
import services as svc
import telegram_experiencia as ux
from tests.relogio_fixo import data_fixa


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'financeiro.db'
        for module in (db, svc):
            p = patch.object(module, 'DB_PATH', self.path); p.start(); self.addCleanup(p.stop)
        db.init_db()

    def rows(self, sql, *args):
        with db.get_connection() as c:
            return [tuple(r) for r in c.execute(sql, args).fetchall()]

    def bases(self, month):
        return dict(self.rows('SELECT conta,saldo_inicial FROM saldos_mensais_contas WHERE ano_mes=?', month))

    def geral(self, month):
        r = self.rows('SELECT saldo_inicial FROM saldos_mensais WHERE ano_mes=?', month)
        return r[0][0] if r else None

    def audits(self, entidade):
        return self.rows("SELECT entidade_id,operacao FROM auditoria_eventos WHERE entidade=? ORDER BY id", entidade)


class SaldoInicialComandoTexto(Base):
    def test_conta_em_mes_com_heranca_muda_so_a_conta_sem_criar_base(self):
        # Antes recusado (B3); agora só a conta muda e o mês continua herdado
        # (detalhes em test_saldo_ajuste_para_frente).
        db.definir_saldo_inicial_conta_mes('2026-10', 'Itaú', 1000)
        db.definir_saldo_inicial_conta_mes('2026-10', 'Nubank', 500)
        antes = svc.calcular_saldo_mensal('2026-11')
        self.assertTrue(antes['saldo_herdado_auto'])
        for texto, conta in (('saldo inicial 2026-11 Nubank 100', 'Nubank'),
                             ('ajustar saldo 2026-11 Nubank para 200', 'Nubank'),
                             ('corrigir saldo 2026-11 Itaú para 300', 'Itaú')):
            cmd = svc.parsear_comando_saldo_inicial(texto)
            self.assertEqual('2026-11', cmd[0])
            resposta = svc.definir_saldo_inicial_formatado(*cmd)
            self.assertIn('Saldo inicial definido', resposta)
            self.assertIn(conta, resposta)
        self.assertEqual({}, self.bases('2026-11'))
        self.assertIsNone(self.geral('2026-11'))
        depois = svc.calcular_saldo_mensal('2026-11')
        self.assertTrue(depois['saldo_herdado_auto'])
        self.assertAlmostEqual(500.0, depois['saldo_inicial'])
        caixa = svc.calcular_caixa_por_conta_mes('2026-11')['contas']
        self.assertEqual({'Itaú': 300.0, 'Nubank': 200.0}, {k: v['inicial'] for k, v in caixa.items()})

    def test_conta_em_mes_so_com_base_geral_e_recusada(self):
        db.definir_saldo_inicial_mes('2026-10', 900)
        resposta = svc.definir_saldo_inicial_formatado('2026-10', 100, 'Nubank')
        self.assertIn('Ajustar saldos atuais', resposta)
        self.assertEqual({}, self.bases('2026-10'))
        self.assertEqual(900, self.geral('2026-10'))

    def test_conta_em_mes_com_bases_preserva_outras_sincroniza_geral_e_audita(self):
        db.definir_saldo_inicial_conta_mes('2026-10', 'Itaú', 1000)
        db.definir_saldo_inicial_conta_mes('2026-10', 'Nubank', 500)
        resposta = svc.definir_saldo_inicial_formatado('2026-10', 700, 'nubank')
        self.assertIn('Saldo inicial definido', resposta)
        self.assertIn('Nubank', resposta)
        self.assertEqual({'Itaú': 1000, 'Nubank': 700}, self.bases('2026-10'))
        self.assertEqual(1700, self.geral('2026-10'))
        self.assertEqual([('2026-10:Nubank', 'saldo_inicial_comando_texto')], self.audits('saldo_conta'))
        self.assertAlmostEqual(1700, svc.calcular_saldo_mensal('2026-10')['saldo_inicial'])

    def test_primeira_configuracao_sem_heranca_continua_gravando(self):
        resposta = svc.definir_saldo_inicial_formatado('2026-10', 300, 'Itaú')
        self.assertIn('Saldo inicial definido', resposta)
        self.assertEqual({'Itaú': 300}, self.bases('2026-10'))
        self.assertEqual(300, self.geral('2026-10'))
        self.assertEqual(1, len(self.audits('saldo_conta')))

    def test_saldo_geral_mantem_regras_e_passa_a_auditar(self):
        resposta = svc.definir_saldo_inicial_formatado('2026-10', 900)
        self.assertIn('Saldo inicial geral', resposta)
        self.assertEqual(900, self.geral('2026-10'))
        self.assertEqual([('2026-10', 'saldo_inicial_comando_texto')], self.audits('saldo_mensal'))
        db.definir_saldo_inicial_conta_mes('2026-11', 'Itaú', 10)
        self.assertIn('saldos por conta', svc.definir_saldo_inicial_formatado('2026-11', 50))
        self.assertIsNone(self.geral('2026-11'))

    def test_parser_variantes_inalteradas(self):
        # "saldo inicial 1000" sem mês usa o mês de hoje: fixa o dia.
        self.enterContext(data_fixa(date(2026, 11, 9)))
        hoje = '2026-11'
        self.assertEqual(('2026-06', 1000.0, 'btg'), svc.parsear_comando_saldo_inicial('saldo inicial 2026-06 btg 1000'))
        self.assertEqual(('2026-07', 2000.0, None), svc.parsear_comando_saldo_inicial('saldo inicial 2026-07 2000'))
        self.assertEqual((hoje, 1000.0, None), svc.parsear_comando_saldo_inicial('saldo inicial 1000'))


class AgendaViradaDoMes(Base):
    def fixed(self, nome, dia):
        return db.inserir_compromisso(dict(tipo='fixo', nome=nome, categoria='Outros', conta_pagamento='Itaú',
                                           forma_pagamento='pix', valor=120, dia_vencimento=dia,
                                           data_inicio='2026-12-01', ativo=True))

    def snap(self, today, month):
        exp = ux.Experience(date_provider=lambda: today)
        s = exp.session('u:1'); s.month = month
        return exp, s, orient.coletar(exp, s)

    def test_31_12_inclui_fixo_de_03_01_sem_duplicar_nem_alterar_total(self):
        self.fixed('Academia', 3)
        self.fixed('Aluguel', 31)
        exp, s, data = self.snap(date(2026, 12, 31), '2026-12')
        soon = [(i['nome'], i['data'], i['origem_mes']) for i in data['soon']]
        self.assertIn(('Aluguel', '2026-12-31', '2026-12'), soon)
        self.assertIn(('Academia', '2027-01-03', '2027-01'), soon)
        self.assertEqual(len(soon), len(set(soon)))
        # A Academia de dezembro (03/12) continua vencida, não some nem duplica.
        self.assertEqual([('Academia', '2026-12-03')], [(i['nome'], i['data']) for i in data['overdue']])
        # Itens/totais do mês não recebem o mês seguinte.
        self.assertTrue(all(i['origem_mes'] == '2026-12' for i in data['items']))
        self.assertEqual(240, sum(float(i['valor']) for i in data['items']))
        agenda = ux.Experience(date_provider=lambda: date(2026, 12, 31))
        texto = agenda.render('u:1', 'agenda').text
        self.assertIn('Academia', texto)
        self.assertIn('03/01', texto)

    def test_janela_dentro_do_mes_nao_muda(self):
        self.fixed('Academia', 3)
        self.fixed('Aluguel', 25)
        _, _, data = self.snap(date(2026, 12, 20), '2026-12')
        self.assertEqual([('Aluguel', '2026-12-25')], [(i['nome'], i['data']) for i in data['soon']])
        self.assertEqual([], data['soon_next_month'])

    def test_mes_passado_e_futuro_nao_buscam_mes_seguinte(self):
        self.fixed('Academia', 3)
        _, _, passado = self.snap(date(2027, 1, 15), '2026-12')
        self.assertEqual([], passado['soon_next_month'])
        _, _, futuro = self.snap(date(2026, 12, 31), '2027-01')
        self.assertEqual([], futuro['soon_next_month'])


class FaturaDataCompra(Base):
    def test_listagem_mostra_data_da_compra_e_agregacao_mantem_competencia(self):
        spec = importlib.util.spec_from_file_location(
            'fixture_competencia_b', Path(__file__).resolve().parents[1] / 'migrations/0004_competencia_faturas.py')
        migration = importlib.util.module_from_spec(spec); spec.loader.exec_module(migration)
        with db.get_connection() as conn:
            migration.upgrade(conn)
        db.inserir_transacao(dict(data='2026-09-28', tipo='despesa', valor=80, categoria='Outros',
                                  descricao='Compra pos corte', conta='Itaú', forma_pagamento='crédito',
                                  mensagem_original='fixture', parcelas_total=1,
                                  data_compra='2026-09-28', competencia_fatura='2026-10'))
        resumo = svc.calcular_resumo_fatura('2026-10', 'Itaú')
        item = [i for i in resumo['itens'] if i.get('nome') == 'Compra pos corte'][0]
        self.assertEqual('2026-10-28', item['data'])
        self.assertEqual('2026-09-28', item['data_compra'])
        texto = svc.formatar_resumo_fatura('2026-10', 'Itaú')
        linha = [l for l in texto.splitlines() if 'Compra pos corte' in l][0]
        self.assertIn(svc.formatar_data_visual('2026-09-28'), linha)
        self.assertNotIn(svc.formatar_data_visual('2026-10-28'), linha)


if __name__ == '__main__':
    unittest.main()
