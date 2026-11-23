import unittest
from unittest.mock import patch

import compromissos
import services


class DetalharQuantoVouPagarTests(unittest.TestCase):
    def test_parser_detalha_mes_e_conta(self):
        with patch.object(services, "detalhar_pagamento_por_conta", return_value="OK") as detalhe:
            retorno = services.processar_mensagem(
                "detalhar quanto vou pagar no Itaú em 2026-07"
            )
        self.assertEqual("OK", retorno)
        detalhe.assert_called_once_with("2026-07", "itaú")

    def test_detalhamento_reconcilia_resumo(self):
        fatura = {
            "itens": [
                {"origem": "transacao", "id": 1, "tipo": "despesa", "nome": "Mercado", "valor": 200},
                {"origem": "compromisso", "id": 2, "tipo": "fixo", "nome": "Internet", "valor": 90},
                {"origem": "compromisso", "id": 3, "tipo": "avulso", "nome": "IPTU", "valor": 100},
            ],
            "credito_herdado": 0,
            "creditos": 20,
            "pagamentos": 30,
            "ajustes_debito": 10,
        }
        resumo = {
            "fatura": 160,
            "fixos": 90,
            "compromissos": 100,
            "total": 350,
            "saldo_fatura": 160,
            "possui_dados": True,
            "possui_fatura": True,
        }
        with patch.object(compromissos, "calcular_fatura_unificada", return_value=fatura), \
             patch.object(compromissos, "calcular_resumo_pagamento_conta", return_value=resumo):
            texto = compromissos.detalhar_pagamento_por_conta("2026-07", "Itaú")

        self.assertIn("Mercado: R$ 200,00", texto)
        self.assertIn("Internet: R$ 90,00", texto)
        self.assertIn("IPTU: R$ 100,00", texto)
        self.assertIn("Créditos/estornos: -R$ 20,00", texto)
        self.assertIn("Pagamentos registrados: -R$ 30,00", texto)
        self.assertIn("Ajustes de débito: +R$ 10,00", texto)
        self.assertIn("TOTAL A PAGAR: R$ 350,00", texto)


if __name__ == "__main__":
    unittest.main()
