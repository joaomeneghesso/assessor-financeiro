"""D5/D6 (reavaliação 02): formatador de dinheiro único, Decimal HALF_UP.

Antes, f"{float:,.2f}" arredondava pelo binário: 2,675 → "R$ 2,67" e
1,005 → "R$ 1,00"; compromissos.formatar_moeda(−0,004) → "R$ -0,00".
Conta à mão (HALF_UP em 2 casas): 2,675 → 2,68; 1,005 → 1,01; 0,125 → 0,13;
10,075 → 10,08; −0,004 → 0,00; −50 → −50,00; 1.234.567,891 → 1.234.567,89.
Cada camada mantém seu sinal: services/compromissos "R$ -50,00"; UX "−R$ 50,00".
"""
import unittest
from decimal import Decimal

import compromissos
import services
import telegram_experiencia as ux

CASOS = [
    (2.675, "R$ 2,68"), (1.005, "R$ 1,01"), (0.125, "R$ 0,13"), (10.075, "R$ 10,08"),
    (-0.004, "R$ 0,00"), (0.004, "R$ 0,00"), (-0.0, "R$ 0,00"), (0.009, "R$ 0,01"),
    (-50, "R$ -50,00"), (1234567.891, "R$ 1.234.567,89"), (Decimal("2.675"), "R$ 2,68"),
    (None, "R$ 0,00"), (0, "R$ 0,00"),
]


class FormatadorMoedaUnico(unittest.TestCase):
    def test_services_e_compromissos_seguem_half_up(self):
        for valor, esperado in CASOS:
            with self.subTest(valor=valor):
                self.assertEqual(services.formatar_moeda(valor), esperado)
                self.assertEqual(compromissos.formatar_moeda(valor), esperado)
                from money import formatar_brl  # novo: falha de import no código antigo
                self.assertEqual(formatar_brl(valor), esperado)

    def test_ux_mesma_regra_com_sinal_proprio(self):
        self.assertEqual(ux.money(2.675), "R$ 2,68")
        self.assertEqual(ux.money(-0.004), "R$ 0,00")
        self.assertEqual(ux.money(-50), "−R$ 50,00")
        self.assertEqual(ux.money(-0.01), "−R$ 0,01")

    def test_valor_nao_finito_nao_vira_inf(self):
        self.assertEqual(services.formatar_moeda(float("inf")), "R$ —")
        self.assertEqual(services.formatar_moeda(float("nan")), "R$ —")


if __name__ == "__main__":
    unittest.main()
