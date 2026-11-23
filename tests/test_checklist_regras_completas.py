import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
import services


class ChecklistRegrasCompletasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = database.DB_PATH
        self.old_service_db = services.DB_PATH
        self.db = Path(self.tmp.name) / "financeiro.db"
        database.DB_PATH = self.db
        services.DB_PATH = self.db
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.old_db
        services.DB_PATH = self.old_service_db
        self.tmp.cleanup()

    @staticmethod
    def item(origem, identificador, nome, valor, forma="pix", conta="Itaú", tipo="fixo"):
        return {
            "origem": origem,
            "id": identificador,
            "tipo": tipo,
            "nome": nome,
            "categoria": "Teste",
            "conta_pagamento": conta,
            "forma_pagamento": forma,
            "valor": valor,
            "data": "2026-07-10",
            "parcela_atual": None,
            "parcelas_total": None,
        }

    def montar(self, itens):
        with patch.object(services, "projetar_pagamentos_mes", return_value=itens):
            return services.montar_itens_checklist_mes("2026-07")

    def test_pix_realizado_nao_entra(self):
        itens = self.montar([self.item("transacao", 1, "Pix realizado", 100)])
        self.assertEqual(itens, [])

    def test_transferencia_realizada_nao_entra(self):
        itens = self.montar([
            self.item("transacao", 2, "Transferência realizada", 200, forma="transferência")
        ])
        self.assertEqual(itens, [])

    def test_compromisso_pix_pendente_entra(self):
        itens = self.montar([self.item("compromisso", 3, "Condomínio", 300, forma="pix")])
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["nome"], "Condomínio")
        self.assertEqual(itens[0]["forma"], "pix")

    def test_fixo_transferencia_pendente_entra(self):
        itens = self.montar([
            self.item("compromisso", 4, "Empréstimo", 400, forma="transferência", tipo="fixo")
        ])
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["nome"], "Empréstimo")

    def test_movimentos_de_fatura_nao_entram_individualmente(self):
        movimentos = [
            self.item("fatura_movimento", 5, "Estorno", -143.73, forma="fatura", tipo="fatura_movimento"),
            self.item("fatura_movimento", 6, "Crédito", -91.70, forma="fatura", tipo="fatura_movimento"),
            self.item("fatura_movimento", 7, "Ajuste débito", 50.0, forma="fatura", tipo="fatura_movimento"),
        ]
        self.assertEqual(self.montar(movimentos), [])

    def test_credito_ou_valor_zero_nao_entra(self):
        itens = self.montar([
            self.item("compromisso", 8, "Crédito", -10),
            self.item("compromisso", 9, "Zerado", 0),
        ])
        self.assertEqual(itens, [])

    def test_compra_no_credito_realizada_compoe_somente_fatura_agregada(self):
        compra = self.item("transacao", 10, "Mercado", 120, forma="crédito", tipo="despesa")
        resumo = {
            "valor_bruto": 120.0, "creditos": 0.0, "pagamentos": 0.0,
            "saldo_restante": 120.0, "status": "pendente",
        }
        with patch.object(services, "projetar_pagamentos_mes", return_value=[compra]), \
             patch.object(services, "calcular_resumo_fatura", return_value=resumo):
            itens = services.montar_itens_checklist_mes("2026-07")
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["grupo"], "bancos")
        self.assertEqual(itens[0]["conta"], "Itaú")
        self.assertEqual(itens[0]["valor"], 120.0)


if __name__ == "__main__":
    unittest.main()
