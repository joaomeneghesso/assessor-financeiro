import unittest
from datetime import date
from unittest.mock import patch

import telegram_experiencia as ux


class QuantoVouPagarTabelaContaTests(unittest.TestCase):
    def setUp(self):
        self.engine = ux.Experience(date_provider=lambda: date(2026, 10, 8))

    def _resumo(self, **overrides):
        resumo = {
            'fatura': 674.19,
            'fatura_bruta': 674.19,
            'credito_herdado': 0.0,
            'ajuste_conferencia': 0.0,
            'fixos': 581.54,
            'emprestimos': 400.0,
            'compromissos': 0.0,
            'credito_disponivel': 0.0,
            'total': 1655.73,
            'possui_dados': True,
            'possui_fatura': True,
        }
        resumo.update(overrides)
        return resumo

    @patch('telegram_experiencia.comp.calcular_resumo_pagamento_conta')
    def test_detalhamento_por_conta_usa_tabela_com_total_canonico(self, calcular):
        calcular.return_value = self._resumo()

        screen = self.engine._pay_account_screen('1:1', 'Itaú', '2026-10')

        self.assertIn('<h2>Quanto vou pagar no Itaú</h2>', screen.rich_html)
        self.assertIn('<table striped compact>', screen.rich_html)
        self.assertIn('<th align="left">Componente</th><th align="right">Valor</th>', screen.rich_html)
        self.assertIn('<td align="left">Fatura/cartão</td><td align="right">R$ 674,19</td>', screen.rich_html)
        self.assertIn('<td align="left">Compras/cobranças do mês</td><td align="right">R$ 674,19</td>', screen.rich_html)
        self.assertIn('<td align="left">Fixos</td><td align="right">R$ 581,54</td>', screen.rich_html)
        self.assertIn('<td align="left">Empréstimos</td><td align="right">R$ 400,00</td>', screen.rich_html)
        self.assertIn('<tr><th align="left">Total a pagar</th><th align="right">R$ 1.655,73</th></tr>', screen.rich_html)
        self.assertIn('<details><summary>Entenda este total</summary>', screen.rich_html)
        self.assertIn('elas não são somadas novamente ao total', screen.rich_html)
        self.assertIn('TOTAL A PAGAR: R$ 1.655,73', screen.text)

    @patch('telegram_experiencia.comp.calcular_resumo_pagamento_conta')
    def test_tabela_escapa_nome_da_conta_e_mostra_credito_disponivel(self, calcular):
        calcular.return_value = self._resumo(
            fatura=0.0,
            fatura_bruta=100.0,
            fixos=0.0,
            emprestimos=0.0,
            credito_disponivel=25.0,
            total=0.0,
        )

        screen = self.engine._pay_account_screen('1:1', 'A&B <cartão>', '2026-10')

        self.assertIn('A&amp;B &lt;cartão&gt;', screen.rich_html)
        self.assertNotIn('A&B <cartão>', screen.rich_html)
        self.assertIn('<td align="left">Crédito disponível</td><td align="right">R$ 25,00</td>', screen.rich_html)
        self.assertIn('<td align="left">Fatura/cartão</td><td align="right">R$ 0,00</td>', screen.rich_html)

    @patch('telegram_experiencia.comp.calcular_resumo_pagamento_conta')
    def test_conta_sem_pendencias_mantem_o_padrao_tabular(self, calcular):
        calcular.return_value = self._resumo(possui_dados=False, possui_fatura=False, total=0.0)

        screen = self.engine._pay_account_screen('1:1', 'InfinitePay', '2026-10')

        self.assertIn('<table striped compact>', screen.rich_html)
        self.assertIn('Nenhuma obrigação em aberto', screen.rich_html)
        self.assertIn('<tr><th align="left">Total a pagar</th><th align="right">R$ 0,00</th></tr>', screen.rich_html)

    @patch('telegram_experiencia.comp.calcular_resumo_pagamento_conta')
    @patch('telegram_experiencia.comp.obter_itens_base_pagamentos_mes', return_value=[])
    def test_botao_da_conta_expande_o_detalhamento_na_rich_message(self, _itens, calcular):
        calcular.return_value = self._resumo()
        opened = [{'conta': 'Itaú', 'valor': 1655.73, 'status': 'pendente'}]

        with patch.object(self.engine, '_pay_month_open_items', return_value=opened):
            collapsed = self.engine._pay_month_screen('1:1', '2026-10')
            expanded = self.engine.act('1:1', ('pay_month_expand', 'Itaú', '2026-10', 0))

        self.assertNotIn('Detalhamento · Itaú', collapsed.rich_html)
        self.assertIn('Detalhamento · Itaú', expanded.rich_html)
        self.assertIn('<td align="left">Fixos</td><td align="right">R$ 581,54</td>', expanded.rich_html)
        self.assertIn('<tr><th align="left">Total a pagar</th><th align="right">R$ 1.655,73</th></tr>', expanded.rich_html)
        actions = [action for row in expanded.rows for _, action in row]
        labels = [label for row in expanded.rows for label, _ in row]
        self.assertTrue(any(action[0] == 'pay_month' for action in actions))
        self.assertTrue(any(label.startswith('▲ Itaú') for label in labels))
        self.assertTrue(any('Ver lançamentos' in label for label in labels))


if __name__ == '__main__':
    unittest.main()
