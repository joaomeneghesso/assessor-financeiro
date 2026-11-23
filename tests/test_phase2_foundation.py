import tempfile
import unittest
from pathlib import Path

import database
import services
from money import parse_money_float


class MoneyTests(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(parse_money_float("10.50"), 10.50)
        self.assertEqual(parse_money_float("10,50"), 10.50)
        self.assertEqual(parse_money_float("1.234,56"), 1234.56)
        self.assertEqual(parse_money_float("1.234"), 1234.00)

    def test_ambiguous_us_mixed_rejected(self):
        with self.assertRaises(ValueError):
            parse_money_float("1,234.56")


class DatabaseSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = database.DB_PATH
        database.DB_PATH = Path(self.tmp.name) / "financeiro.db"
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.old_db
        self.tmp.cleanup()

    def test_connection_pragmas(self):
        with database.get_connection() as conn:
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")

    def test_fatura_validation(self):
        base = {
            "ano_mes": "2026-07", "conta_cartao": "Nubank",
            "tipo_movimento": "estorno", "valor": 10,
            "data_movimento": "2026-07-10", "conta_origem": None,
        }
        movimento_id = database.inserir_fatura_movimento(base)
        self.assertGreater(movimento_id, 0)
        with self.assertRaises(ValueError):
            database.atualizar_fatura_movimento(movimento_id, valor=-1)
        with self.assertRaises(ValueError):
            database.atualizar_fatura_movimento(movimento_id, ano_mes="2026-99")
        with self.assertRaises(ValueError):
            database.atualizar_fatura_movimento(movimento_id, tipo_movimento="banana")

    def test_atomic_replace_rolls_back(self):
        good = [{
            "tipo": "fixo", "nome": "A", "categoria": "Teste",
            "valor": 10, "data_inicio": "2026-01-01", "origem": "csv:x"
        }]
        database.substituir_compromissos_por_origem("csv:x", good)
        bad = [good[0], {"tipo": "fixo"}]
        with self.assertRaises(Exception):
            database.substituir_compromissos_por_origem("csv:x", bad)
        rows = database.listar_compromissos()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["nome"], "A")


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = database.DB_PATH
        self.old_service_db = services.DB_PATH
        self.old_backups = services.BACKUPS_DIR
        db = Path(self.tmp.name) / "financeiro.db"
        database.DB_PATH = db
        services.DB_PATH = db
        services.BACKUPS_DIR = Path(self.tmp.name) / "backups"
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.old_db
        services.DB_PATH = self.old_service_db
        services.BACKUPS_DIR = self.old_backups
        self.tmp.cleanup()

    def test_unique_valid_backups(self):
        a, _ = services.criar_backup_db()
        b, _ = services.criar_backup_db()
        self.assertNotEqual(a.name, b.name)
        self.assertTrue(a.exists() and b.exists())
        services._validar_backup_sqlite(a)
        services._validar_backup_sqlite(b)


if __name__ == "__main__":
    unittest.main()
