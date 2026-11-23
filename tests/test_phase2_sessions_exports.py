import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import services


class SessionIsolationTests(unittest.TestCase):
    def tearDown(self):
        services.PENDENCIAS_IMPORTACAO.clear()
        services.PENDENCIAS_EXPORTACAO.clear()
        services.PENDENCIAS_CONFIRMACAO.clear()

    def test_export_pending_is_scoped(self):
        services._definir_pendencia(services.PENDENCIAS_EXPORTACAO, "user-a:chat-a", True)
        self.assertTrue(services._obter_pendencia(services.PENDENCIAS_EXPORTACAO, "user-a:chat-a"))
        self.assertIsNone(services._obter_pendencia(services.PENDENCIAS_EXPORTACAO, "user-b:chat-b"))

    def test_import_preview_is_scoped(self):
        preview_a = {"arquivo": "a.csv"}
        preview_b = {"arquivo": "b.csv"}
        services._definir_pendencia(services.PENDENCIAS_IMPORTACAO, "a", preview_a)
        services._definir_pendencia(services.PENDENCIAS_IMPORTACAO, "b", preview_b)
        self.assertEqual(services._obter_pendencia(services.PENDENCIAS_IMPORTACAO, "a"), preview_a)
        self.assertEqual(services._obter_pendencia(services.PENDENCIAS_IMPORTACAO, "b"), preview_b)


class CsvSafetyTests(unittest.TestCase):
    def test_formula_cells_are_neutralized(self):
        for value in ("=1+1", "+SUM(A1:A2)", "-2+3", "@cmd"):
            self.assertTrue(services.sanitizar_celula_csv(value).startswith("'"))
        self.assertEqual(services.sanitizar_celula_csv("texto normal"), "texto normal")

    def test_same_period_exports_have_unique_names(self):
        item = {
            "origem": "transacao", "id": 1, "data": "2026-07-01",
            "tipo": "despesa", "valor": 10.0, "categoria": "Teste",
            "descricao": "=1+1", "conta": "Itaú", "forma_pagamento": "pix",
            "parcela_atual": None, "parcelas_total": None, "ativo": 1,
        }
        with tempfile.TemporaryDirectory() as tmp:
            old_dir = services.EXPORTS_DIR
            services.EXPORTS_DIR = Path(tmp)
            try:
                with patch.object(services, "buscar_itens_financeiros_periodo", return_value=[item]):
                    first = services.exportar_csv_periodo("2026-07-01", "2026-07-01")
                    second = services.exportar_csv_periodo("2026-07-01", "2026-07-01")
                self.assertNotEqual(first["arquivo"], second["arquivo"])
                self.assertTrue(Path(first["arquivo"]).exists())
                self.assertTrue(Path(second["arquivo"]).exists())
                content = Path(first["arquivo"]).read_text(encoding="utf-8-sig")
                self.assertIn("'=1+1", content)
            finally:
                services.EXPORTS_DIR = old_dir


if __name__ == "__main__":
    unittest.main()
