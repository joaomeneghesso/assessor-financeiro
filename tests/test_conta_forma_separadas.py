import unittest
from unittest.mock import patch

import compromissos
import services


class ContaFormaSeparadasTests(unittest.TestCase):
    @patch("compromissos.listar_fatura_movimentos", return_value=[])
    @patch("compromissos.obter_primeira_competencia_financeira", return_value=None)
    @patch("compromissos.obter_itens_base_pagamentos_mes")
    def test_compromisso_pix_no_itau_nao_vira_fatura(self, obter_itens, _primeira, _movimentos):
        obter_itens.return_value = [
            {
                "origem": "compromisso",
                "id": 30,
                "tipo": "avulso",
                "nome": "Empréstimo",
                "conta_pagamento": "Itaú",
                "forma_pagamento": "pix",
                "valor": 400.0,
            }
        ]

        resumo = compromissos.calcular_resumo_pagamento_conta("2026-07", "Itaú")

        self.assertEqual(0.0, resumo["fatura"])
        self.assertEqual(400.0, resumo["emprestimos"])
        self.assertEqual(0.0, resumo["compromissos"])
        self.assertEqual(400.0, resumo["total"])

    @patch("compromissos.listar_fatura_movimentos", return_value=[])
    @patch("compromissos.obter_primeira_competencia_financeira", return_value=None)
    @patch("compromissos.obter_itens_base_pagamentos_mes")
    def test_conta_pix_legada_continua_consultavel(self, obter_itens, _primeira, _movimentos):
        obter_itens.return_value = [
            {
                "origem": "compromisso",
                "id": 31,
                "tipo": "fixo",
                "nome": "Condomínio",
                "conta_pagamento": "Pix",
                "forma_pagamento": "pix",
                "valor": 231.45,
            }
        ]

        texto = compromissos.resumo_pagamento_por_conta("2026-07", "Pix")

        self.assertIn("Fixos: R$ 231,45", texto)
        self.assertNotIn("Fatura/cartão", texto)
        self.assertIn("TOTAL A PAGAR: R$ 231,45", texto)

    def test_checklist_distingue_conta_pix_de_transacao_pix_realizada(self):
        compromisso = {
            "origem": "compromisso",
            "id": 10,
            "tipo": "avulso",
            "conta_pagamento": "Pix",
            "forma_pagamento": "pix",
            "valor": 100.0,
        }
        realizado = {
            "origem": "transacao",
            "id": 11,
            "tipo": "despesa",
            "conta_pagamento": "Pix",
            "forma_pagamento": "pix",
            "valor": 100.0,
        }

        self.assertTrue(services.item_deve_entrar_no_checklist(compromisso))
        self.assertFalse(services.item_deve_entrar_no_checklist(realizado))

    def test_estorno_nunca_vira_item_do_checklist(self):
        estorno = {
            "origem": "fatura_movimento",
            "id": 1,
            "tipo": "fatura_movimento",
            "tipo_movimento": "estorno",
            "conta_pagamento": "Itaú",
            "forma_pagamento": "fatura",
            "valor": -91.70,
        }
        self.assertFalse(services.item_deve_entrar_no_checklist(estorno))


if __name__ == "__main__":
    unittest.main()
