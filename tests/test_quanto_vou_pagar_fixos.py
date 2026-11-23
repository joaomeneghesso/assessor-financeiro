import unittest

from compromissos import item_entra_no_quanto_vou_pagar


class QuantoVouPagarFixosTests(unittest.TestCase):
    def test_fixo_projetado_no_pix_entra_como_obrigacao_futura(self):
        item = {
            "origem": "compromisso",
            "tipo": "fixo",
            "forma_pagamento": "pix",
            "conta_pagamento": "Itaú",
        }
        self.assertTrue(item_entra_no_quanto_vou_pagar(item))

    def test_transacao_pix_ja_realizada_nao_entra(self):
        item = {
            "origem": "transacao",
            "tipo": "transacao",
            "forma_pagamento": "pix",
            "conta_pagamento": "Itaú",
        }
        self.assertFalse(item_entra_no_quanto_vou_pagar(item))

    def test_compra_no_credito_entra(self):
        item = {
            "origem": "transacao",
            "tipo": "transacao",
            "forma_pagamento": "crédito",
            "conta_pagamento": "Itaú",
        }
        self.assertTrue(item_entra_no_quanto_vou_pagar(item))


if __name__ == "__main__":
    unittest.main()
