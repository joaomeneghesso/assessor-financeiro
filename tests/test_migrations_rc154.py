import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import database
from tests.helpers_rc155 import criar_banco_legado


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "migrations.py"
MIGRATIONS_DIR = ROOT / "migrations"

SPEC = importlib.util.spec_from_file_location("migration_runner_rc154", RUNNER_PATH)
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


class MigrationFrameworkRC154Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "financeiro.db"
        self.backups = self.root / "backups" / "schema"
        self.audit = self.backups / "migrations_audit.jsonl"
        self.baseline_migrations = self.root / "migrations_baseline"
        self.baseline_migrations.mkdir()
        shutil.copy2(
            MIGRATIONS_DIR / "0001_baseline.py",
            self.baseline_migrations / "0001_baseline.py",
        )
        shutil.copy2(
            MIGRATIONS_DIR / "__init__.py",
            self.baseline_migrations / "__init__.py",
        )
        self.old_database_path = database.DB_PATH
        database.DB_PATH = self.db
        criar_banco_legado(self.db)

    def tearDown(self):
        database.DB_PATH = self.old_database_path
        self.tmp.cleanup()

    def apply(self, migrations_dir=None):
        return runner.apply_migrations(
            self.db,
            migrations_dir or self.baseline_migrations,
            self.backups,
            self.audit,
            executed_by="teste_rc154",
        )

    def schema_objects(self):
        with closing(sqlite3.connect(self.db)) as connection:
            return {
                row[0]
                for row in connection.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE name NOT LIKE 'sqlite_%'
                    ORDER BY name
                    """
                )
            }

    def test_discovery_encontra_baseline_e_valida_ordem(self):
        migrations = runner.discover_migrations(self.baseline_migrations)

        self.assertEqual([1], [migration.version for migration in migrations])
        self.assertEqual("baseline", migrations[0].name)
        self.assertTrue(migrations[0].supports_rollback)
        self.assertEqual(
            file_sha256(self.baseline_migrations / "0001_baseline.py"),
            migrations[0].checksum,
        )

    def test_discovery_bloqueia_lacuna_de_versao(self):
        copied_migrations = self.root / "migrations_gap"
        shutil.copytree(self.baseline_migrations, copied_migrations)
        (copied_migrations / "0003_gap.py").write_text(
            "\n".join([
                "VERSION = 3",
                "NAME = 'gap'",
                "SUPPORTS_ROLLBACK = False",
                "SQL = ()",
                "AFFECTED_OBJECTS = ()",
                "def upgrade(connection):",
                "    pass",
                "",
            ]),
            encoding="utf-8",
        )

        with self.assertRaises(runner.MigrationError):
            runner.discover_migrations(copied_migrations)

    def test_status_e_somente_leitura(self):
        hash_antes = file_sha256(self.db)
        status = runner.get_status(self.db, self.baseline_migrations)
        hash_depois = file_sha256(self.db)

        self.assertEqual(hash_antes, hash_depois)
        self.assertEqual(0, status["current_version"])
        self.assertEqual([1], [item["version"] for item in status["available"]])
        self.assertEqual([], status["executed"])
        self.assertEqual([1], [item["version"] for item in status["pending"]])
        self.assertNotIn("schema_migrations", self.schema_objects())

    def test_dry_run_nao_altera_banco_nem_filesystem(self):
        hash_antes = file_sha256(self.db)
        plan = runner.dry_run(
            self.db, self.baseline_migrations, self.backups
        )

        self.assertTrue(plan["dry_run"])
        self.assertFalse(plan["changes_applied"])
        self.assertEqual(1, len(plan["plans"]))
        self.assertIn(
            "schema_migrations", plan["plans"][0]["affected_objects"]
        )
        self.assertTrue(any(
            "CREATE TABLE IF NOT EXISTS schema_migrations" in sql
            for sql in plan["plans"][0]["sql"]
        ))
        self.assertEqual(hash_antes, file_sha256(self.db))
        self.assertFalse(self.backups.exists())
        self.assertNotIn("schema_migrations", self.schema_objects())

    def test_apply_cria_apenas_tabela_tecnica_e_versiona(self):
        objetos_antes = self.schema_objects()
        with closing(sqlite3.connect(self.db)) as connection:
            schema_antes = runner.functional_schema_hash(connection)

        result = self.apply()

        objetos_depois = self.schema_objects()
        self.assertEqual(
            {"schema_migrations"}, objetos_depois - objetos_antes
        )
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(
                schema_antes, runner.functional_schema_hash(connection)
            )
            self.assertEqual(
                1, connection.execute("PRAGMA user_version").fetchone()[0]
            )
            row = connection.execute(
                "SELECT version, name, success, rollback_supported "
                "FROM schema_migrations"
            ).fetchone()
            columns = {
                item[1]
                for item in connection.execute(
                    "PRAGMA table_info(schema_migrations)"
                )
            }
        self.assertEqual((1, "baseline", 1, 1), row)
        self.assertEqual(
            {
                "id", "version", "name", "checksum", "executed_at",
                "execution_time_ms", "success", "rollback_supported",
            },
            columns,
        )
        self.assertEqual(0, result["previous_version"])
        self.assertEqual(1, result["current_version"])

    def test_backup_registra_hash_tamanho_e_versao(self):
        self.apply()
        backups = list(self.backups.glob("financeiro_schema_backup_*.db"))

        self.assertEqual(1, len(backups))
        metadata_path = backups[0].with_suffix(".json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(file_sha256(backups[0]), metadata["sha256"])
        self.assertEqual(backups[0].stat().st_size, metadata["size"])
        self.assertEqual(0, metadata["version"])
        with closing(sqlite3.connect(backups[0])) as connection:
            self.assertEqual(
                "ok", connection.execute("PRAGMA integrity_check").fetchone()[0]
            )
        self.assertEqual(("ok", 0), runner._validate_backup(backups[0]))
        metadata["version"] = 99
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False),
            encoding="utf-8",
        )
        with self.assertRaises(runner.MigrationError):
            runner._validate_backup(backups[0])

    def test_validate_confere_integridade_schema_checksum_e_versao(self):
        self.apply()
        validation = runner.validate_compatibility(
            self.db, self.baseline_migrations, self.backups
        )

        self.assertTrue(validation.valid, validation.errors)
        self.assertEqual("ok", validation.integrity)
        self.assertEqual(1, validation.current_version)
        self.assertEqual(
            "C9865CBFABAB309EB2C080A974F96AF3D6B3211F1D8282377E36E3979E9F23D4",
            validation.schema_hash,
        )
        self.assertTrue(validation.backup_ready)
        self.assertTrue(validation.rollback_ready)

    def test_rollback_da_migration_retorna_ao_schema_original(self):
        objetos_antes = self.schema_objects()
        self.apply()

        event = runner.rollback(
            self.db,
            self.baseline_migrations,
            self.backups,
            self.audit,
            strategy="migration",
            executed_by="teste_rc154",
        )

        self.assertEqual("success", event["result"])
        self.assertEqual(0, event["version_after"])
        self.assertEqual(objetos_antes, self.schema_objects())
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(
                0, connection.execute("PRAGMA user_version").fetchone()[0]
            )

    def test_rollback_por_backup_restaura_estado_logico(self):
        hash_logico_antes = runner.logical_database_hash(self.db)
        self.apply()

        event = runner.rollback(
            self.db,
            self.baseline_migrations,
            self.backups,
            self.audit,
            strategy="backup",
            executed_by="teste_rc154",
        )

        self.assertEqual("success", event["result"])
        self.assertEqual(0, event["version_after"])
        self.assertEqual(hash_logico_antes, runner.logical_database_hash(self.db))
        self.assertNotIn("schema_migrations", self.schema_objects())

    def test_schema_divergente_interrompe_compatibilidade(self):
        with closing(sqlite3.connect(self.db)) as connection:
            connection.execute("CREATE TABLE tabela_estranha (id INTEGER)")
            connection.commit()

        validation = runner.validate_compatibility(
            self.db, self.baseline_migrations, self.backups
        )

        self.assertFalse(validation.valid)
        self.assertTrue(any(
            "Schema funcional divergente" in error
            for error in validation.errors
        ))
        self.assertNotIn("schema_migrations", self.schema_objects())

    def test_checksum_e_versao_divergentes_sao_bloqueados(self):
        copied_migrations = self.root / "migrations"
        shutil.copytree(self.baseline_migrations, copied_migrations)
        self.apply(copied_migrations)
        migration_file = copied_migrations / "0001_baseline.py"
        migration_file.write_text(
            migration_file.read_text(encoding="utf-8") + "\n# alterada\n",
            encoding="utf-8",
        )

        checksum_validation = runner.validate_compatibility(
            self.db, copied_migrations, self.backups
        )
        self.assertFalse(checksum_validation.valid)
        self.assertTrue(any(
            "Checksum divergente" in error
            for error in checksum_validation.errors
        ))

        with closing(sqlite3.connect(self.db)) as connection:
            connection.execute("PRAGMA user_version=7")
        version_validation = runner.validate_compatibility(
            self.db, copied_migrations, self.backups
        )
        self.assertFalse(version_validation.valid)
        self.assertTrue(any(
            "Versão divergente" in error
            for error in version_validation.errors
        ))

    def test_falha_de_migration_faz_rollback_e_registra_auditoria(self):
        copied_migrations = self.root / "migrations_failure"
        shutil.copytree(self.baseline_migrations, copied_migrations)
        (copied_migrations / "0002_failure.py").write_text(
            "\n".join([
                "VERSION = 2",
                "NAME = 'failure'",
                "SUPPORTS_ROLLBACK = True",
                "EXPECTED_SCHEMA_HASH = "
                "'C9865CBFABAB309EB2C080A974F96AF3D6B3211F1D8282377E36E3979E9F23D4'",
                "SQL = ('CREATE TABLE nunca_persistir (id INTEGER)',)",
                "AFFECTED_OBJECTS = ('nunca_persistir',)",
                "def upgrade(connection):",
                "    connection.execute(SQL[0])",
                "    raise RuntimeError('falha controlada')",
                "def downgrade(connection):",
                "    connection.execute('DROP TABLE IF EXISTS nunca_persistir')",
                "",
            ]),
            encoding="utf-8",
        )

        with self.assertRaises(runner.MigrationError):
            self.apply(copied_migrations)

        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(
                1, connection.execute("PRAGMA user_version").fetchone()[0]
            )
            self.assertIsNone(connection.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type='table' AND name='nunca_persistir'"
            ).fetchone())
            versions = [
                row[0] for row in connection.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                )
            ]
        self.assertEqual([1], versions)
        events = [
            json.loads(line)
            for line in self.audit.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(
            [(1, "success"), (2, "failed")],
            [(event["version"], event["result"]) for event in events],
        )

    def test_cli_status_validate_dry_run_e_auditoria(self):
        for command in ("status", "validate", "dry-run"):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = runner.main([
                    command,
                    "--db", str(self.db),
                    "--migrations-dir", str(self.baseline_migrations),
                    "--backup-dir", str(self.backups),
                ])
            self.assertEqual(0, exit_code, output.getvalue())
            self.assertTrue(output.getvalue().strip())

        self.apply()
        events = [
            json.loads(line)
            for line in self.audit.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(1, len(events))
        event = events[0]
        self.assertEqual("migration", event["event"])
        self.assertEqual("success", event["result"])
        self.assertEqual("teste_rc154", event["executed_by"])
        self.assertTrue(event["hash_before"])
        self.assertTrue(event["hash_after"])
        self.assertIn("execution_time_ms", event)


if __name__ == "__main__":
    unittest.main()
