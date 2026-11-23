import sqlite3
import tempfile
import contextvars
from concurrent.futures import ThreadPoolExecutor
import unittest
from pathlib import Path
from unittest.mock import patch

import database


class ConexaoLeituraFase2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = database.DB_PATH
        database.DB_PATH = Path(self.tmp.name) / "financeiro.db"
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.old_db
        self.tmp.cleanup()

    def test_uma_conexao_por_contexto_e_fechamento_ao_final(self):
        original = database.sqlite3.connect
        aberturas = []

        def contar(*args, **kwargs):
            connection = original(*args, **kwargs)
            aberturas.append(connection)
            return connection

        with patch.object(database.sqlite3, "connect", side_effect=contar):
            with database.read_only_mode():
                primeira = database.get_connection()
                with primeira as connection:
                    self.assertEqual(1, connection.execute("SELECT 1").fetchone()[0])
                segunda = database.get_connection()
                self.assertIs(primeira, segunda)
                with database.read_only_mode():
                    self.assertIs(primeira, database.get_connection())

        self.assertEqual(1, len(aberturas))
        with self.assertRaises(sqlite3.ProgrammingError):
            primeira.execute("SELECT 1")

    def test_row_factory_nao_vaza_entre_leituras(self):
        with database.read_only_mode():
            with database.get_connection() as connection:
                self.assertIsNone(connection.row_factory)
                connection.row_factory = sqlite3.Row
                self.assertIsInstance(connection.execute("SELECT 1 AS valor").fetchone(), sqlite3.Row)
            with database.get_connection() as connection:
                self.assertIsNone(connection.row_factory)
                self.assertIsInstance(connection.execute("SELECT 1").fetchone(), tuple)

    def test_conexao_compartilhada_permanece_somente_leitura(self):
        with database.read_only_mode():
            with database.get_connection() as connection:
                self.assertEqual(1, connection.execute("PRAGMA query_only").fetchone()[0])
                with self.assertRaises(sqlite3.OperationalError):
                    connection.execute("DELETE FROM transacoes")

    def test_conexoes_de_escrita_continuam_independentes(self):
        primeira = database.get_connection()
        segunda = database.get_connection()
        try:
            self.assertIsNot(primeira, segunda)
            self.assertEqual(0, primeira.execute("PRAGMA query_only").fetchone()[0])
            self.assertEqual(0, segunda.execute("PRAGMA query_only").fetchone()[0])
        finally:
            primeira.close()
            segunda.close()

    def test_contexto_copiado_para_outra_thread_nao_reutiliza_conexao(self):
        with database.read_only_mode():
            principal = database.get_connection()
            contexto = contextvars.copy_context()

            def consultar_em_thread():
                with database.get_connection() as connection:
                    return connection is principal, connection.execute("SELECT 1").fetchone()[0]

            with ThreadPoolExecutor(max_workers=1) as executor:
                mesma, valor = executor.submit(contexto.run, consultar_em_thread).result()

            self.assertFalse(mesma)
            self.assertEqual(1, valor)
            self.assertEqual(1, principal.execute("SELECT 1").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
