import unittest
from unittest.mock import patch

from compromissos import resumo_pagamento_por_conta


class QuantoVouPagarResumoTests(unittest.TestCase):
    def _fatura(self, itens, **overrides):
        base = {
            "itens": itens,
            "movimentos": [],
            "credito_herdado": 0.0,
            "creditos": 0.0,
            "pagamentos": 0.0,
            "ajustes_debito": 0.0,
        }
        base.update(overrides)
        return base

    @patch("compromissos.calcular_fatura_unificada")
    def test_resumo_separa_fatura_fixos_e_total(self, calcular):
        calcular.return_value = self._fatura(
            [
                {"tipo": "transacao", "origem": "transacao", "valor": 797.08},
                {"tipo": "fixo", "origem": "compromisso", "valor": 154.83},
            ],
            creditos=235.43,
        )

        texto = resumo_pagamento_por_conta("2026-07", "Itaú")

        self.assertIn("Fatura/cartão: R$ 561,65", texto)
        self.assertIn("Fixos: R$ 154,83", texto)
        self.assertIn("TOTAL A PAGAR: R$ 716,48", texto)
        self.assertNotIn("Por categoria", texto)
        self.assertNotIn("Ignorados por", texto)
        self.assertNotIn("Itens da fatura", texto)

    @patch("compromissos.calcular_fatura_unificada")
    def test_credito_da_fatura_nao_abate_fixos(self, calcular):
        calcular.return_value = self._fatura(
            [
                {"tipo": "transacao", "origem": "transacao", "valor": 100.00},
                {"tipo": "fixo", "origem": "compromisso", "valor": 80.00},
            ],
            creditos=150.00,
        )

        texto = resumo_pagamento_por_conta("2026-07", "Itaú")

        self.assertIn("Fatura/cartão: R$ 0,00", texto)
        self.assertIn("Fixos: R$ 80,00", texto)
        self.assertIn("TOTAL A PAGAR: R$ 80,00", texto)
        self.assertIn("Crédito disponível na fatura: R$ 50,00", texto)

    @patch("compromissos.calcular_fatura_unificada")
    def test_parcelamento_fica_na_fatura_e_avulso_em_compromissos(self, calcular):
        calcular.return_value = self._fatura(
            [
                {"tipo": "parcelamento", "origem": "compromisso", "valor": 120.00},
                {"tipo": "avulso", "origem": "compromisso", "valor": 30.00},
            ]
        )

        texto = resumo_pagamento_por_conta("2026-07", "Itaú")

        self.assertIn("Fatura/cartão: R$ 120,00", texto)
        self.assertIn("Compromissos: R$ 30,00", texto)
        self.assertIn("TOTAL A PAGAR: R$ 150,00", texto)


if __name__ == "__main__":
    unittest.main()
