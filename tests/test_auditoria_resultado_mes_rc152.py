import tempfile
import unittest
from pathlib import Path

import database
import services


class AuditoriaResultadoMesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = database.DB_PATH
        database.DB_PATH = Path(self.tmp.name) / "financeiro.db"
        services.DB_PATH = database.DB_PATH
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.old_db
        services.DB_PATH = self.old_db
        self.tmp.cleanup()

    def inserir(self, data, tipo, valor, descricao, conta, forma):
        database.inserir_transacao({
            "data": data,
            "tipo": tipo,
            "valor": valor,
            "categoria": "Teste",
            "descricao": descricao,
            "conta": conta,
            "forma_pagamento": forma,
            "mensagem_original": "teste",
        })

    def test_auditoria_reconcilia_grupos_do_meu_mes(self):
        self.inserir("2026-07-05", "receita", 1000, "Salário", "Itaú", "entrada")
        self.inserir("2026-07-06", "despesa", 100, "Mercado", "Itaú", "pix")
        self.inserir("2026-07-07", "despesa", 200, "Compra cartão", "Itaú", "crédito")

        resposta = services.gerar_auditoria_resultado_mes_ux("2026-07")

        self.assertIn("Auditoria do resultado", resposta)
        self.assertIn("Salário", resposta)
        self.assertIn("Mercado", resposta)
        self.assertIn("Compra cartão", resposta)
        self.assertIn("Resultado operacional", resposta)
        self.assertIn("subtotais reconciliam", resposta)

    def test_comando_auditar_mes_dispara_auditoria(self):
        resposta = services.processar_mensagem("auditar mês 2026-07")
        self.assertIn("Auditoria do resultado", resposta)

    def test_auditoria_nao_altera_dados(self):
        self.inserir("2026-07-05", "despesa", 10, "Café", "Itaú", "pix")
        antes = len(list(database.buscar_transacoes_por_mes("2026-07")))
        services.gerar_auditoria_resultado_mes_ux("2026-07")
        depois = len(list(database.buscar_transacoes_por_mes("2026-07")))
        self.assertEqual(antes, depois)


if __name__ == "__main__":
    unittest.main()
