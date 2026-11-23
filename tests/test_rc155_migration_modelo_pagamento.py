import contextlib
import hashlib
import importlib.util
import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

import database
import services
from tests.helpers_rc155 import colunas_tabela, criar_banco_legado


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "migrations"
RUNNER_SPEC = importlib.util.spec_from_file_location(
    "migration_runner_rc155", ROOT / "migrations.py"
)
runner = importlib.util.module_from_spec(RUNNER_SPEC)
sys.modules[RUNNER_SPEC.name] = runner
RUNNER_SPEC.loader.exec_module(runner)

LEGACY_FIELDS = (
    "id", "tipo", "nome", "categoria", "conta_pagamento",
    "forma_pagamento", "valor", "dia_vencimento", "data_inicio",
    "data_fim", "parcelas_total", "ativo", "origem", "observacao",
    "criado_em", "atualizado_em",
)


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


class MigrationModeloPagamentoRC155Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # V39: esta classe testa o contrato historico 0001-0003.
        # A cadeia completa, incluindo 0004, e coberta em testes_v39.
        global MIGRATIONS_DIR
        self.original_migrations = MIGRATIONS_DIR
        historicas = self.root / "migrations_historicas"
        historicas.mkdir()
        for arquivo in self.original_migrations.glob("[0-9][0-9][0-9][0-9]_*.py"):
            if int(arquivo.name[:4]) <= 3:
                shutil.copy2(arquivo, historicas / arquivo.name)
        MIGRATIONS_DIR = historicas
        self.db = criar_banco_legado(self.root / "financeiro.db")
        self.backups = self.root / "backups" / "schema"
        self.audit = self.backups / "migrations_audit.jsonl"
        self.old_database_path = database.DB_PATH
        self.old_service_path = services.DB_PATH
        database.DB_PATH = self.db
        services.DB_PATH = self.db
        self._inserir_fixture_legada()

    def tearDown(self):
        global MIGRATIONS_DIR
        MIGRATIONS_DIR = self.original_migrations
        database.DB_PATH = self.old_database_path
        services.DB_PATH = self.old_service_path
        self.tmp.cleanup()

    def _inserir_fixture_legada(self):
        for nome, conta, forma, valor in (
            ("Condomínio", "Pix", "pix", 231.45),
            ("Lia", "Lia", "crédito", 33.45),
            ("Banco", "Itaú", "crédito", 100.0),
        ):
            database.inserir_compromisso({
                "tipo": "fixo",
                "nome": nome,
                "categoria": "Teste",
                "conta_pagamento": conta,
                "forma_pagamento": forma,
                "valor": valor,
                "dia_vencimento": 10,
                "data_inicio": "2026-07-01",
                "ativo": True,
                "origem": "fixture_rc155",
            })
        database.inserir_transacao({
            "data": "2026-07-05",
            "tipo": "receita",
            "valor": 1000,
            "categoria": "Receita",
            "descricao": "Entrada",
            "conta": "Itaú",
            "forma_pagamento": "entrada",
            "mensagem_original": "fixture rc155",
        })
        database.inserir_transacao({
            "data": "2026-07-06",
            "tipo": "despesa",
            "valor": 50,
            "categoria": "Teste",
            "descricao": "Pix realizado",
            "conta": "Itaú",
            "forma_pagamento": "pix",
            "mensagem_original": "fixture rc155",
        })
        database.marcar_checklist_pagamento(
            "2026-07", "C1", "pago", "manual rc155"
        )
        database.definir_checklist_data_pagamento(
            "2026-07", "C1", "2026-07-22", "manual rc155"
        )

    def _apply(self, migrations_dir=None):
        migrations_dir = migrations_dir or MIGRATIONS_DIR
        return runner.apply_migrations(
            self.db,
            migrations_dir,
            self.backups,
            self.audit,
            executed_by="teste_rc155",
        )

    def _rows(self, table, fields="*"):
        with contextlib.closing(sqlite3.connect(self.db)) as connection:
            connection.row_factory = sqlite3.Row
            return [
                dict(row)
                for row in connection.execute(
                    f"SELECT {fields} FROM {table} ORDER BY rowid"
                )
            ]

    def _functional_snapshot(self):
        with contextlib.closing(sqlite3.connect(self.db)) as connection:
            connection.row_factory = sqlite3.Row
            tables = [
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                    "AND name != 'schema_migrations' ORDER BY name"
                )
            ]
            snapshot = {}
            for table in tables:
                columns = [
                    row[1] for row in connection.execute(
                        f'PRAGMA table_info("{table}")'
                    )
                ]
                if table == "compromissos":
                    columns = [c for c in columns if c in LEGACY_FIELDS]
                select = ", ".join(f'"{c}"' for c in columns)
                snapshot[table] = [
                    tuple(row)
                    for row in connection.execute(
                        f'SELECT {select} FROM "{table}" ORDER BY rowid'
                    )
                ]
            return snapshot

    def _financial_snapshot(self):
        saldo = services.obter_metricas_resultado_mes("2026-07")
        quanto = services.resumo_pagamento_mes_consolidado("2026-07")
        checklist = services.aplicar_status_checklist(
            "2026-07",
            services.montar_itens_checklist_mes("2026-07", modo="geral"),
        )
        return {
            "entradas": saldo["total_entradas_mes"],
            "saidas_imediatas": saldo["saidas_imediatas_realizadas"],
            "credito_lancado": saldo["saidas_nao_imediatas_realizadas"],
            "despesas_esperadas_total": saldo["despesas_esperadas_total"],
            "resultado_operacional": saldo["resultado_projetado_mes"],
            "saldo_livre_provavel": saldo["saldo_livre_projetado"],
            "quanto": quanto,
            "checklist": [
                (
                    item["chave"], item["status"], item.get("data"),
                    item["valor"], item.get("grupo"),
                )
                for item in checklist
            ],
        }

    def test_descoberta_ordem_e_sem_lacuna(self):
        migrations = runner.discover_migrations(MIGRATIONS_DIR)
        self.assertEqual([1, 2, 3], [item.version for item in migrations])
        self.assertEqual(
            ["baseline", "campos_pagamento_canonicos", "normalizacao_pagamentos_historicos"],
            [item.name for item in migrations],
        )
        self.assertFalse(migrations[1].supports_rollback)

    def test_status_validate_e_dry_run_nao_criam_objetos(self):
        before = file_sha256(self.db)
        status = runner.get_status(self.db, MIGRATIONS_DIR)
        validation = runner.validate_compatibility(
            self.db, MIGRATIONS_DIR, self.backups
        )
        plan = runner.dry_run(self.db, MIGRATIONS_DIR, self.backups)
        self.assertEqual([1, 2, 3], [
            item["version"] for item in status["pending"]
        ])
        self.assertTrue(validation.valid, validation.errors)
        self.assertEqual(3, len(plan["plans"]))
        self.assertEqual(before, file_sha256(self.db))
        with contextlib.closing(sqlite3.connect(self.db)) as connection:
            self.assertIsNone(connection.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type='table' AND name='schema_migrations'"
            ).fetchone())
        self.assertFalse(self.backups.exists())

    def test_upgrade_zero_para_dois_registra_versoes_e_checksums(self):
        result = self._apply()
        self.assertEqual((0, 3), (
            result["previous_version"], result["current_version"]
        ))
        with contextlib.closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(
                3, connection.execute("PRAGMA user_version").fetchone()[0]
            )
            rows = connection.execute(
                "SELECT version, name, checksum, success, rollback_supported "
                "FROM schema_migrations ORDER BY version"
            ).fetchall()
        self.assertEqual([1, 2, 3], [row[0] for row in rows])
        self.assertTrue(all(row[2] for row in rows))
        self.assertEqual([1, 1, 1], [row[3] for row in rows])
        self.assertEqual([1, 0, 0], [row[4] for row in rows])

    def test_upgrade_um_para_dois(self):
        baseline = self.root / "baseline"
        baseline.mkdir()
        shutil.copy2(
            MIGRATIONS_DIR / "0001_baseline.py",
            baseline / "0001_baseline.py",
        )
        runner.apply_migrations(
            self.db, baseline, self.backups, self.audit,
            executed_by="teste_rc155",
        )
        result = self._apply()
        self.assertEqual((1, 3), (
            result["previous_version"], result["current_version"]
        ))

    def test_colunas_finais_opcionais_e_conta_legada_existente(self):
        self._apply()
        columns = {
            item[0]: item for item in colunas_tabela(self.db, "compromissos")
        }
        for name in (
            "conta_pagamento", "forma_pagamento",
            "conta_origem", "destino_pagamento",
        ):
            self.assertIn(name, columns)
            self.assertEqual(0, columns[name][2], name)

    def test_dados_pix_lia_e_forma_existente_ficam_identicos(self):
        before = self._rows(
            "compromissos", ", ".join(LEGACY_FIELDS)
        )
        self._apply()
        after = self._rows(
            "compromissos", ", ".join(LEGACY_FIELDS)
        )
        self.assertEqual(before, after)
        with contextlib.closing(sqlite3.connect(self.db)) as connection:
            rows = connection.execute(
                "SELECT conta_pagamento, forma_pagamento, conta_origem, "
                "destino_pagamento FROM compromissos "
                "WHERE conta_pagamento IN ('Pix', 'Lia') ORDER BY id"
            ).fetchall()
        self.assertEqual(["Pix", "Lia"], [row[0] for row in rows])
        self.assertEqual(["pix", "crédito"], [row[1] for row in rows])
        self.assertTrue(all(row[2] is None and row[3] is None for row in rows))

    def test_nenhuma_linha_funcional_adicionada_ou_removida(self):
        before = self._functional_snapshot()
        self._apply()
        after = self._functional_snapshot()
        self.assertEqual(before, after)

    def test_contagens_de_compromissos_e_transacoes_preservadas(self):
        before = (
            len(self._rows("compromissos")),
            len(self._rows("transacoes")),
        )
        self._apply()
        self.assertEqual(before, (
            len(self._rows("compromissos")),
            len(self._rows("transacoes")),
        ))

    def test_backup_antecede_cada_migration(self):
        self._apply()
        metadata = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(self.backups.glob("*.json"))
            if path.name != "migrations_audit.jsonl"
        ]
        self.assertEqual([0, 1, 2], sorted(item["version"] for item in metadata))
        for item in metadata:
            backup = Path(item["path"])
            self.assertTrue(backup.exists())
            self.assertEqual(item["sha256"], file_sha256(backup))

    def test_falha_simulada_reverte_alteracao_parcial(self):
        baseline = self.root / "baseline"
        baseline.mkdir()
        shutil.copy2(
            MIGRATIONS_DIR / "0001_baseline.py",
            baseline / "0001_baseline.py",
        )
        runner.apply_migrations(
            self.db, baseline, self.backups, self.audit,
            executed_by="teste_rc155",
        )
        failing = self.root / "failing"
        shutil.copytree(MIGRATIONS_DIR, failing)
        file = failing / "0002_campos_pagamento_canonicos.py"
        file.write_text(
            "\n".join([
                "VERSION = 2",
                "NAME = 'campos_pagamento_canonicos'",
                "SUPPORTS_ROLLBACK = False",
                "EXPECTED_SCHEMA_HASH = "
                "'C9865CBFABAB309EB2C080A974F96AF3D6B3211F1D8282377E36E3979E9F23D4'",
                "SQL = ('ALTER TABLE compromissos ADD COLUMN conta_origem TEXT NULL',)",
                "AFFECTED_OBJECTS = ('compromissos',)",
                "def upgrade(connection):",
                "    connection.execute(SQL[0])",
                "    raise RuntimeError('falha controlada rc155')",
                "",
            ]),
            encoding="utf-8",
        )
        with self.assertRaises(runner.MigrationError):
            runner.apply_migrations(
                self.db, failing, self.backups, self.audit,
                executed_by="teste_rc155",
            )
        self.assertNotIn(
            "conta_origem",
            {item[0] for item in colunas_tabela(self.db, "compromissos")},
        )
        with contextlib.closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(
                1, connection.execute("PRAGMA user_version").fetchone()[0]
            )

    def test_segunda_aplicacao_e_noop_e_status_sem_pendencias(self):
        self._apply()
        second = self._apply()
        self.assertEqual([], second["executed"])
        status = runner.get_status(self.db, MIGRATIONS_DIR)
        self.assertEqual(3, status["current_version"])
        self.assertEqual([], status["pending"])

    def test_validate_aceita_hash_resultante(self):
        self._apply()
        validation = runner.validate_compatibility(
            self.db, MIGRATIONS_DIR, self.backups
        )
        self.assertTrue(validation.valid, validation.errors)
        self.assertEqual(
            "6A80F75A7CD79B5B30A890B1E8F2F31C6ED2FAB0614C85CF7F7DA9FA32DE3A9A",
            validation.schema_hash,
        )

    def test_banco_novo_e_migrado_possuem_schema_equivalente(self):
        self._apply()
        migrated = colunas_tabela(self.db, "compromissos")
        new_db = self.root / "novo.db"
        old = database.DB_PATH
        try:
            database.DB_PATH = new_db
            database.init_db()
        finally:
            database.DB_PATH = old
        self.assertEqual(migrated, colunas_tabela(new_db, "compromissos"))
        with contextlib.closing(sqlite3.connect(new_db)) as connection:
            self.assertEqual(
                "6A80F75A7CD79B5B30A890B1E8F2F31C6ED2FAB0614C85CF7F7DA9FA32DE3A9A",
                runner.functional_schema_hash(connection),
            )

    def test_banco_novo_registra_migrations_sem_duplicar_colunas(self):
        new_db = self.root / "novo_versionado.db"
        old = database.DB_PATH
        try:
            database.DB_PATH = new_db
            database.init_db()
        finally:
            database.DB_PATH = old

        before = colunas_tabela(new_db, "compromissos")
        new_backups = self.root / "new_backups"
        validation = runner.validate_compatibility(
            new_db, MIGRATIONS_DIR, new_backups
        )
        self.assertTrue(validation.valid, validation.errors)

        result = runner.apply_migrations(
            new_db,
            MIGRATIONS_DIR,
            new_backups,
            executed_by="teste_rc155_banco_novo",
        )

        self.assertEqual(3, result["current_version"])
        self.assertEqual(before, colunas_tabela(new_db, "compromissos"))
        with contextlib.closing(sqlite3.connect(new_db)) as connection:
            self.assertEqual(
                [1, 2, 3],
                [
                    row[0] for row in connection.execute(
                        "SELECT version FROM schema_migrations ORDER BY version"
                    )
                ],
            )

    def test_rollback_por_backup_remove_colunas_da_0002(self):
        self._apply()
        version_one_backup = next(
            path.with_suffix(".db")
            for path in self.backups.glob("*.json")
            if json.loads(path.read_text(encoding="utf-8"))["version"] == 1
        )
        event = runner.rollback(
            self.db,
            MIGRATIONS_DIR,
            self.backups,
            self.audit,
            strategy="backup",
            backup_path=version_one_backup,
            executed_by="teste_rc155",
        )
        self.assertEqual(1, event["version_after"])
        columns = {item[0] for item in colunas_tabela(self.db, "compromissos")}
        self.assertNotIn("conta_origem", columns)
        self.assertNotIn("destino_pagamento", columns)
        self.assertIn("forma_pagamento", columns)

    def test_rollback_sql_da_0002_e_recusado_sem_alterar_estado(self):
        self._apply()
        before = file_sha256(self.db)
        with self.assertRaises(runner.MigrationError):
            runner.rollback(
                self.db,
                MIGRATIONS_DIR,
                self.backups,
                self.audit,
                strategy="migration",
                executed_by="teste_rc155",
            )
        self.assertEqual(before, file_sha256(self.db))
        with contextlib.closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(
                3, connection.execute("PRAGMA user_version").fetchone()[0]
            )

    def test_hash_logico_dos_dados_funcionais_preservado(self):
        before = self._functional_snapshot()
        before_hash = hashlib.sha256(
            repr(before).encode("utf-8")
        ).hexdigest()
        self._apply()
        after = self._functional_snapshot()
        after_hash = hashlib.sha256(
            repr(after).encode("utf-8")
        ).hexdigest()
        self.assertEqual(before_hash, after_hash)

    def test_calculos_checklist_chaves_status_e_datas_nao_mudam(self):
        before = self._financial_snapshot()
        self._apply()
        after = self._financial_snapshot()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
