import unittest
from datetime import date
from unittest.mock import patch

from telegram_design import rich_table, superscript_number
import telegram_experiencia as ux


class TabelasFinanceirasRichTests(unittest.TestCase):
    def test_total_fica_dentro_da_tabela_com_destaque_semantico(self):
        rendered = rich_table(
            ('Indicador', 'Valor'),
            [('Saldo atual', 'R$ 1.000,00')],
            ('Saldo previsto', 'R$ 900,00'),
        )

        self.assertTrue(rendered.startswith('<table striped compact>'))
        self.assertTrue(rendered.endswith('</table>'))
        self.assertIn('<th align="left">Indicador</th><th align="right">Valor</th>', rendered)
        self.assertIn('<td align="left">Saldo atual</td><td align="right">R$ 1.000,00</td>', rendered)
        self.assertIn('<tr><th align="left">Saldo previsto</th><th align="right">R$ 900,00</th></tr>', rendered)

    def test_conteudo_das_celulas_e_escapado(self):
        rendered = rich_table(('Conta', 'Valor'), [('A&B <teste>', 'R$ 1,00')])

        self.assertIn('A&amp;B &lt;teste&gt;', rendered)
        self.assertNotIn('A&B <teste>', rendered)

    def test_contagem_sobrescrita_e_discreta(self):
        self.assertEqual('⁰', superscript_number(0))
        self.assertEqual('¹¹', superscript_number(11))
        self.assertEqual('¹²³', superscript_number(123))

    @patch('telegram_experiencia.svc.calcular_caixa_por_conta_mes')
    def test_saldos_por_conta_e_detalhe_usam_tabela_com_total(self, calcular):
        calcular.return_value = {
            'contas': {
                'Itaú': {'inicial': 1000, 'entradas': 200, 'saidas': 300, 'disponivel': 900},
                'Nubank': {'inicial': 500, 'entradas': 0, 'saidas': 50, 'disponivel': 450},
            },
            'total_disponivel': 1350,
        }
        engine = ux.Experience(date_provider=lambda: date(2026, 10, 8))

        accounts = engine._cash_accounts_screen('1:1', '2026-10')
        detail = engine._cash_account_detail_screen('1:1', 'Itaú', '2026-10')

        self.assertIn('<tr><th align="left">Total disponível</th><th align="right">R$ 1.350,00</th></tr>', accounts.rich_html)
        self.assertIn('<tr><th align="left">Saldo atual</th><th align="right">R$ 900,00</th></tr>', detail.rich_html)
        self.assertIn('<td align="left">Saídas realizadas</td><td align="right">R$ 300,00</td>', detail.rich_html)

    @patch('telegram_experiencia.orient.coletar')
    def test_meu_mes_resume_movimento_projecao_e_pendencias_sem_dupla_contagem(self, coletar):
        coletar.return_value = {
            'metrics': {
                'saldo_disponivel': 1000,
                'entradas_realizadas': 500,
                'saidas_imediatas_realizadas': 250,
                'saidas_nao_imediatas_realizadas': 100,
                'entradas_previstas': 200,
                'despesas_esperadas_total': 200,
                'pendencias_herdadas_total': 0,
                'compensacao_pagamentos_fatura': 0,
                'ajuste_reserva_faturas': 0,
                'saldo_projetado': 900,
                'resultado_projetado_mes': -100,
                'saldo_configurado': True,
                'saldo_herdado_auto': False,
                'revisoes_conciliacao': [],
            },
            'items': [{'valor': 150}, {'valor': 200}],
        }
        engine = ux.Experience(date_provider=lambda: date(2026, 10, 8))

        screen = engine.screen_home(engine.session('1:1'))

        for expected in (
            '<td align="left">🟢 Entradas recebidas</td><td align="right">R$ 500,00</td>',
            '<td align="left">🔴 Saídas já realizadas</td><td align="right">R$ 250,00</td>',
            '<td align="left">🟠 Compras lançadas no crédito</td><td align="right">R$ 100,00</td>',
            '<td align="left">🟢 Ainda a receber</td><td align="right">R$ 200,00</td>',
            '<td align="left">🧾 Obrigações abertas ²</td><td align="right">R$ 350,00</td>',
            '<tr><th align="left">🎯 Deve sobrar no fim do mês</th><th align="right">R$ 900,00</th></tr>',
            '<details><summary>Entenda o mês</summary>',
        ):
            self.assertIn(expected, screen.rich_html)

        coletar.return_value['items'] = [{'valor': 150}]
        after_one_payment = engine.screen_home(engine.session('1:1'))
        self.assertIn('🧾 Obrigações abertas ¹</td><td align="right">R$ 150,00', after_one_payment.rich_html)
        self.assertNotIn('Obrigações abertas ²', after_one_payment.rich_html)

        coletar.return_value['items'] = []
        after_all_payments = engine.screen_home(engine.session('1:1'))
        self.assertIn('🧾 Obrigações abertas ⁰</td><td align="right">R$ 0,00', after_all_payments.rich_html)


if __name__ == '__main__':
    unittest.main()
