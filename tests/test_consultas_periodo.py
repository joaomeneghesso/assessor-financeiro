"""Consultas de gasto por categoria e período ("últimos 3 meses", "de julho a novembro", "em 2025").

Pedido do titular em 13/11/2026. Antes, "quanto gastei com alimentação de julho a
novembro" virava a categoria "alimentacao de julho a novembro" e só olhava julho
(resposta "não encontrei"); "últimos N meses", "de <categoria>" e ano solto não
eram entendidos. Tudo aqui é determinístico: a IA local nunca é chamada.
"""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import assessor_ia_local
import database as db
import services as svc
import telegram_experiencia as ux
from consultas_rapidas import PERIODOS_PROPRIOS, interpretar_consulta, resolver_meses
from tests.test_jornadas_ponta_a_ponta import JornadaBase, setUpModule, tearDownModule  # noqa: F401

HOJE = date(2026, 11, 13)


def meses(texto, hoje=HOJE):
    p = interpretar_consulta(texto)
    assert p is not None and p['period'] in PERIODOS_PROPRIOS, (texto, p)
    return resolver_meses(p, hoje)


class InterpretadorTests(unittest.TestCase):
    def test_frases_do_titular(self):
        p = interpretar_consulta('quanto gastei de viagem nos últimos 3 meses')
        self.assertEqual(('category_expense', 'viagem'), (p['query_type'], p['category']))
        self.assertEqual(['2026-09', '2026-10', '2026-11'], resolver_meses(p, HOJE))
        p = interpretar_consulta('quanto gastei com alimentação de julho a novembro')
        self.assertEqual('alimentacao', p['category'])
        self.assertEqual(['2026-07', '2026-08', '2026-09', '2026-10', '2026-11'], resolver_meses(p, HOJE))

    def test_mes_com_ou_sem_ano_nao_contamina_a_categoria(self):
        for texto, esperado in [('quanto gastei com alimentação em julho', ['2026-07']),
                                ('quanto gastei com alimentação em julho de 2025', ['2025-07']),
                                ('quanto gastei com mercado em 2026-07', ['2026-07']),
                                ('quanto gastei com mercado no mês de março', ['2026-03'])]:
            with self.subTest(texto=texto):
                self.assertEqual(esperado, meses(texto))
                self.assertNotRegex(interpretar_consulta(texto)['category'], r'julho|marco|2026|2025|mes')

    def test_intervalos(self):
        casos = [
            ('quanto gastei com mercado entre julho e setembro', ['2026-07', '2026-08', '2026-09']),
            ('quanto gastei com mercado julho até setembro', ['2026-07', '2026-08', '2026-09']),
            ('quanto gastei com mercado de novembro a fevereiro', ['2025-11', '2025-12', '2026-01', '2026-02']),
            ('quanto gastei de alimentação de julho de 2025 a março de 2026',
             ['2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12', '2026-01', '2026-02', '2026-03']),
            ('quanto gastei com mercado julho até setembro de 2025', ['2025-07', '2025-08', '2025-09']),
            ('quanto gastei com mercado de 2026-01 a 2026-02', ['2026-01', '2026-02']),
        ]
        for texto, esperado in casos:
            with self.subTest(texto=texto):
                self.assertEqual(esperado, meses(texto))

    def test_ano(self):
        self.assertEqual([f'2025-{m:02d}' for m in range(1, 13)], meses('quanto gastei com viagem em 2025'))
        self.assertEqual([f'2025-{m:02d}' for m in range(1, 13)], meses('gastos com lazer no ano passado'))
        # Ano corrente vai só até o mês atual.
        self.assertEqual([f'2026-{m:02d}' for m in range(1, 12)], meses('quanto recebi em 2026'))

    def test_ultimos_meses_cruza_a_virada_do_ano(self):
        self.assertEqual(['2025-11', '2025-12', '2026-01'], meses('quanto gastei nos últimos três meses', date(2026, 1, 15)))
        self.assertEqual(['2026-11'], meses('quanto gastei nos últimos 1 meses'))

    def test_tipos_de_pergunta_com_periodo(self):
        self.assertEqual('expense_total', interpretar_consulta('quanto gastei de julho a novembro')['query_type'])
        self.assertEqual('income_total', interpretar_consulta('quanto recebi nos últimos 6 meses')['query_type'])
        self.assertEqual('largest_expenses', interpretar_consulta('onde gastei mais nos últimos seis meses')['query_type'])

    def test_periodos_antigos_continuam(self):
        self.assertEqual('current_month', interpretar_consulta('quanto gastei com mercado')['period'])
        self.assertEqual('previous_month', interpretar_consulta('quanto gastei com mercado mês passado')['period'])
        self.assertEqual('current_year', interpretar_consulta('quanto gastei com viagem esse ano')['period'])

    def test_o_que_nao_sabe_representar_fica_para_o_fallback(self):
        for texto in ['quanto gastei nos últimos 10 dias', 'quanto gastei com mercado em julho e agosto',
                      'quanto gastei com mercado no cartão', 'quanto gastei semana passada',
                      'quanto gastei com mercado em julho de 2025 em 2024']:
            with self.subTest(texto=texto):
                self.assertIsNone(interpretar_consulta(texto))

    def test_intervalo_invertido_com_anos_e_invalido(self):
        self.assertIsNone(meses('quanto gastei com mercado de março de 2026 a janeiro de 2026'))


class ConsultaNoMotorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, 'DB_PATH', Path(self.tmp.name) / 'fixture.db')
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        for data, tipo, valor, cat, desc in [
            ('2025-12-01', 'despesa', 40, 'Alimentação', 'Padaria'),
            ('2026-06-15', 'despesa', 1000, 'Viagem', 'Pacote junho'),
            ('2026-07-10', 'despesa', 100, 'Alimentação', 'Mercado julho'),
            ('2026-08-05', 'despesa', 50.5, 'Alimentação', 'Mercado agosto'),
            ('2026-09-20', 'despesa', 300, 'Viagem', 'Hotel'),
            ('2026-10-02', 'despesa', 200, 'Viagem', 'Passagem'),
            ('2026-11-10', 'despesa', 80, 'Viagem', 'Uber aeroporto'),
            ('2026-11-20', 'despesa', 999, 'Viagem', 'Reserva futura'),
            ('2026-11-01', 'receita', 5000, 'Salário', 'Salário'),
        ]:
            db.inserir_transacao(dict(data=data, tipo=tipo, valor=valor, categoria=cat, descricao=desc,
                                      conta='Itaú', forma_pagamento='pix', parcelas_total=1))
        self.engine = ux.Experience(date_provider=lambda: HOJE)
        self.key = 'teste-consulta-periodo'
        ia = patch.object(assessor_ia_local, 'interpretar_contexto', side_effect=AssertionError('IA não deveria ser chamada'))
        ia.start()
        self.addCleanup(ia.stop)

    def perguntar(self, texto):
        tela = self.engine.fast_deterministic_query(self.key, texto)
        self.assertIsNotNone(tela, texto)
        return tela.text

    def test_viagem_nos_ultimos_3_meses(self):
        texto = self.perguntar('quanto gastei de viagem nos últimos 3 meses')
        self.assertIn('R$ 580,00', texto)  # 300 + 200 + 80; junho e o lançamento futuro ficam fora
        self.assertIn('Setembro 2026 a Novembro 2026 (até 13/11/2026)', texto)
        for linha in ('Setembro 2026 · R$ 300,00', 'Outubro 2026 · R$ 200,00', 'Novembro 2026 · R$ 80,00'):
            self.assertIn(linha, texto)
        self.assertNotIn('999', texto)
        self.assertEqual('2026-11', self.engine.session(self.key).month)

    def test_alimentacao_de_julho_a_novembro(self):
        texto = self.perguntar('quanto gastei com alimentação de julho a novembro')
        self.assertIn('R$ 150,50', texto)
        self.assertIn('Julho 2026 · R$ 100,00', texto)
        self.assertIn('Setembro 2026 · R$ 0,00', texto)
        self.assertNotIn('Não encontrei', texto)

    def test_alimentacao_em_julho_regressao(self):
        texto = self.perguntar('quanto gastei com alimentação em julho')
        self.assertIn('R$ 100,00', texto)
        self.assertNotIn('Por mês', texto)

    def test_ano_informado(self):
        self.assertIn('R$ 40,00', self.perguntar('quanto gastei com alimentação em 2025'))

    def test_total_de_despesas_no_intervalo(self):
        texto = self.perguntar('quanto gastei de julho a novembro')
        self.assertIn('R$ 730,50', texto)  # 100 + 50,50 + 300 + 200 + 80
        self.assertIn('Por mês', texto)

    def test_periodo_invalido_explica(self):
        texto = self.perguntar('quanto gastei com mercado de março de 2026 a janeiro de 2026')
        self.assertIn('Período inválido', texto)


class ConsultaPeloTelegramTests(JornadaBase):
    """Caminho real: dispatch_text, sem IA local."""

    def test_pergunta_com_intervalo_responde_pelo_motor_novo(self):
        with patch.object(assessor_ia_local, 'interpretar_contexto', side_effect=AssertionError('IA chamada')):
            db.inserir_transacao(dict(data='2026-08-03', tipo='despesa', valor=120, categoria='Alimentação',
                                      descricao='Feira', conta='Itaú', forma_pagamento='pix', parcelas_total=1))
            tela = self.dizer('quanto gastei com alimentação de julho a novembro?')
        self.assertIsNotNone(tela)
        self.assertIn('R$ 120,00', tela.text)
        self.assertIn('Agosto 2026 · R$ 120,00', tela.text)


if __name__ == '__main__':
    unittest.main()
