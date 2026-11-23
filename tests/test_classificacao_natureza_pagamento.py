import unittest
from unittest.mock import patch

import compromissos


class ClassificacaoNaturezaPagamentoTests(unittest.TestCase):
    def _fatura(self, itens):
        return {
            "itens": itens,
            "itens_todos": itens,
            "movimentos": [],
            "credito_herdado": 0.0,
            "creditos": 0.0,
            "pagamentos": 0.0,
            "ajustes_debito": 0.0,
            "saldo_restante": 0.0,
        }

    def test_emprestimo_parcelado_tem_grupo_proprio(self):
        item = {
            "origem": "compromisso",
            "tipo": "parcelamento",
            "nome": "Empréstimo",
            "categoria": "Empréstimos",
            "forma_pagamento": "pix",
            "parcelas_total": 12,
            "parcela_atual": 3,
            "valor": 400.0,
        }
        self.assertEqual("emprestimos", compromissos.classificar_natureza_pagamento(item))

    def test_compra_parcelada_continua_como_parcelamento(self):
        item = {
            "origem": "compromisso",
            "tipo": "parcelamento",
            "nome": "Notebook",
            "categoria": "Compras",
            "parcelas_total": 10,
            "valor": 250.0,
        }
        self.assertEqual("parcelas", compromissos.classificar_natureza_pagamento(item))

    @patch("compromissos.calcular_fatura_unificada")
    def test_resumo_exibe_emprestimo_e_nao_parcela(self, calcular):
        calcular.return_value = self._fatura([
            {
                "origem": "compromisso",
                "tipo": "parcelamento",
                "nome": "Empréstimo",
                "categoria": "Empréstimos",
                "forma_pagamento": "pix",
                "parcelas_total": 12,
                "parcela_atual": 3,
                "valor": 400.0,
            }
        ])

        texto = compromissos.resumo_pagamento_por_conta("2026-07", "Itaú")

        self.assertIn("Empréstimos: R$ 400,00", texto)
        self.assertNotIn("Parcelamentos:", texto)
        self.assertIn("TOTAL A PAGAR: R$ 400,00", texto)


if __name__ == "__main__":
    unittest.main()
