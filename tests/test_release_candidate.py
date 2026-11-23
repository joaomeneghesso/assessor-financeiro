import gc
import sqlite3
import tempfile
import unittest
import warnings
from pathlib import Path

import database


class ReleaseCandidateTests(unittest.TestCase):
    def setUp(self):
        self.original_db = database.DB_PATH
        self.tmp = tempfile.TemporaryDirectory()
        database.DB_PATH = Path(self.tmp.name) / "financeiro.db"
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.original_db
        self.tmp.cleanup()

    def test_connection_context_closes_file_handle(self):
        with database.get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_database_regression_emits_no_resource_warning(self):
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", ResourceWarning)
            for _ in range(20):
                with database.get_connection() as conn:
                    conn.execute("SELECT COUNT(*) FROM transacoes").fetchone()
            gc.collect()
        resource_warnings = [w for w in captured if issubclass(w.category, ResourceWarning)]
        self.assertEqual([], resource_warnings)


if __name__ == "__main__":
    unittest.main()
