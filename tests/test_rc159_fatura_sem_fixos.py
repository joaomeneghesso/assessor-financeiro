import unittest
from unittest.mock import patch

import compromissos


class TestRC159FaturaSemFixos(unittest.TestCase):
    def test_fatura_contem_somente_itens_de_cartao(self):
        itens = [
            {
                "origem": "transacao", "tipo": "transacao", "id": 1,
                "nome": "Compra cartão", "categoria": "Compras",
                "conta_pagamento": "Itaú", "forma_pagamento": "crédito",
                "valor": 872.06, "data": "2026-07-10",
            },
            {
                "origem": "compromisso", "tipo": "fixo", "id": 2,
                "nome": "Internet", "categoria": "Moradia",
                "conta_pagamento": "Itaú", "forma_pagamento": "pix",
                "valor": 581.16, "data": "2026-07-15",
            },
            {
                "origem": "compromisso", "tipo": "fixo", "id": 3,
                "nome": "Empréstimos", "categoria": "Empréstimos",
                "conta_pagamento": "Itaú", "forma_pagamento": "pix",
                "valor": 400.00, "data": "2026-07-20",
            },
        ]
        movimentos = [
            {
                "conta_cartao": "Itaú", "tipo_movimento": "credito",
                "valor": 235.43,
            }
        ]

        with patch.object(compromissos, "obter_itens_base_pagamentos_mes", return_value=itens), \
             patch.object(compromissos, "listar_fatura_movimentos", return_value=movimentos), \
             patch.object(compromissos, "obter_primeira_competencia_financeira", return_value="2026-07"):
            resumo = compromissos.calcular_fatura_unificada("2026-07", "Itaú", somente_cartao=True)

        self.assertAlmostEqual(resumo["valor_bruto"], 872.06, places=2)
        self.assertAlmostEqual(resumo["creditos"], 235.43, places=2)
        self.assertAlmostEqual(resumo["saldo_restante"], 636.63, places=2)
        self.assertEqual([item["nome"] for item in resumo["itens"]], ["Compra cartão"])

    def test_parcela_no_cartao_continua_na_fatura(self):
        item = {
            "origem": "compromisso", "tipo": "parcelamento", "id": 4,
            "nome": "Notebook", "categoria": "Compras",
            "conta_pagamento": "Nubank", "forma_pagamento": "crédito",
            "valor": 250.00, "data": "2026-07-12",
            "parcela_atual": 2, "parcelas_total": 10,
        }
        with patch.object(compromissos, "obter_itens_base_pagamentos_mes", return_value=[item]), \
             patch.object(compromissos, "listar_fatura_movimentos", return_value=[]), \
             patch.object(compromissos, "obter_primeira_competencia_financeira", return_value="2026-07"):
            resumo = compromissos.calcular_fatura_unificada("2026-07", "Nubank", somente_cartao=True)

        self.assertAlmostEqual(resumo["valor_bruto"], 250.00, places=2)
        self.assertEqual(len(resumo["itens"]), 1)


if __name__ == "__main__":
    unittest.main()
