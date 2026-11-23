import unittest
from datetime import date
from unittest.mock import patch

from tests.relogio_fixo import data_fixa

import compromissos
import services


class QuantoVouPagarMesTests(unittest.TestCase):
    def test_consolida_todas_as_contas(self):
        itens = [
            {"origem": "compromisso", "tipo": "fixo", "conta_pagamento": "Itaú", "forma_pagamento": "pix", "valor": 100},
            {"origem": "compromisso", "tipo": "parcelamento", "conta_pagamento": "Nubank", "forma_pagamento": "crédito", "valor": 200},
        ]
        with patch.object(compromissos, "obter_itens_base_pagamentos_mes", return_value=itens), \
             patch.object(compromissos, "listar_fatura_movimentos", return_value=[]), \
             patch.object(compromissos, "calcular_resumo_pagamento_conta") as calc:
            calc.side_effect = lambda mes, conta: {
                "fatura": 0 if conta == "Itaú" else 200,
                "fixos": 100 if conta == "Itaú" else 0,
                "compromissos": 0,
                "total": 100 if conta == "Itaú" else 200,
                "saldo_fatura": 0,
                "possui_dados": True,
            }
            texto = compromissos.resumo_pagamento_mes_consolidado("2026-07")

        self.assertIn("🏦 Nubank: R$ 200,00", texto)
        self.assertIn("🏦 Itaú: R$ 100,00", texto)
        self.assertIn("TOTAL A PAGAR: R$ 300,00", texto)
        self.assertNotIn("ainda", texto.lower())

    def test_exclui_pix_ja_realizado_da_descoberta_de_contas(self):
        itens = [
            {"origem": "transacao", "tipo": "despesa", "conta_pagamento": "Itaú", "forma_pagamento": "pix", "valor": 50},
            {"origem": "compromisso", "tipo": "fixo", "conta_pagamento": "Nubank", "forma_pagamento": "pix", "valor": 80},
        ]
        with patch.object(compromissos, "obter_itens_base_pagamentos_mes", return_value=itens), \
             patch.object(compromissos, "listar_fatura_movimentos", return_value=[]), \
             patch.object(compromissos, "calcular_resumo_pagamento_conta", return_value={
                 "fatura": 0, "fixos": 80, "compromissos": 0, "total": 80,
                 "saldo_fatura": 0, "possui_dados": True,
             }) as calc:
            compromissos.resumo_pagamento_mes_consolidado("2026-07")
        calc.assert_called_once_with("2026-07", "Nubank")

    def test_parser_aceita_comando_no_mes(self):
        with patch.object(services, "resumo_pagamento_mes_consolidado", return_value="OK") as resumo:
            retorno = services.processar_mensagem("quanto vou pagar no mês")
        self.assertEqual("OK", retorno)
        resumo.assert_called_once()

    def test_parser_aceita_mes_nome_sem_ainda(self):
        with patch.object(services, "resumo_pagamento_mes_consolidado", return_value="OK") as resumo:
            retorno = services.processar_mensagem("quanto vou pagar em julho/2026")
        self.assertEqual("OK", retorno)
        resumo.assert_called_once_with("2026-07")

    def test_parser_aceita_no_mes_de_julho(self):
        # Mês sem ano depende de hoje: fixa um dia anterior a julho.
        with data_fixa(date(2026, 3, 10)), \
             patch.object(services, "resumo_pagamento_mes_consolidado", return_value="OK") as resumo:
            retorno = services.processar_mensagem("quanto vou pagar no mes de julho")
        self.assertEqual("OK", retorno)
        resumo.assert_called_once_with("2026-07")

    def test_consolidado_ignora_registro_malformado(self):
        itens = [
            None,
            {"origem": "compromisso", "tipo": "fixo", "conta_pagamento": 123, "forma_pagamento": "pix", "valor": 80},
        ]
        with patch.object(compromissos, "obter_itens_base_pagamentos_mes", return_value=itens), \
             patch.object(compromissos, "listar_fatura_movimentos", return_value=[]), \
             patch.object(compromissos, "calcular_resumo_pagamento_conta", return_value={
                 "fatura": 0, "fixos": 80, "compromissos": 0, "total": 80,
                 "saldo_fatura": 0, "possui_dados": True,
             }):
            texto = compromissos.resumo_pagamento_mes_consolidado("2026-07")
        self.assertIn("TOTAL A PAGAR: R$ 80,00", texto)


if __name__ == "__main__":
    unittest.main()
