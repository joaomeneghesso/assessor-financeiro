"""Framework versionado e isolado de migrations SQLite.

Este módulo não é importado pelo bot. Ele só atua quando executado
explicitamente pela linha de comando ou pelos testes dedicados.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import importlib.util
import json
import logging
import os
import re
import sqlite3
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = ROOT_DIR / "data" / "financeiro.db"
DEFAULT_MIGRATIONS_DIR = ROOT_DIR / "migrations"
DEFAULT_BACKUP_DIR = ROOT_DIR / "backups" / "schema"

MIGRATION_PATTERN = re.compile(r"^(?P<version>\d{4})_(?P<name>[a-z0-9_]+)\.py$")
TECHNICAL_TABLE = "schema_migrations"

CREATE_SCHEMA_MIGRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    execution_time_ms INTEGER NOT NULL,
    success INTEGER NOT NULL CHECK (success IN (0, 1)),
    rollback_supported INTEGER NOT NULL CHECK (rollback_supported IN (0, 1))
)
""".strip()

LOGGER = logging.getLogger("assessor.migrations")


class ClosingConnection(sqlite3.Connection):
    """Conexão cujo context manager também libera o handle no Windows."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class MigrationError(RuntimeError):
    """Erro seguro e esperado do framework de migrations."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path
    checksum: str
    sql: tuple[str, ...]
    affected_objects: tuple[str, ...]
    estimated_time_ms: int
    supports_rollback: bool
    expected_schema_hash: str | None
    resulting_schema_hash: str | None
    allows_preapplied_schema: bool
    module: ModuleType


@dataclass(frozen=True)
class BackupInfo:
    path: Path
    checksum: str
    size: int
    version: int
    created_at: str
    metadata_path: Path


@dataclass
class ValidationResult:
    valid: bool
    integrity: str
    current_version: int
    schema_hash: str
    expected_schema_hash: str | None
    backup_ready: bool
    rollback_ready: bool
    errors: list[str]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _sqlite_uri(path: Path, *, immutable: bool = False) -> str:
    suffix = "?mode=ro"
    if immutable:
        suffix += "&immutable=1"
    return path.resolve().as_uri() + suffix


def connect_read_only(path: Path, *, immutable: bool = False) -> sqlite3.Connection:
    if not path.is_file():
        raise MigrationError(f"Banco não encontrado: {path}")
    connection = sqlite3.connect(
        _sqlite_uri(path, immutable=immutable),
        uri=True,
        timeout=15.0,
        factory=ClosingConnection,
    )
    connection.execute("PRAGMA query_only=ON")
    connection.execute("PRAGMA busy_timeout=15000")
    return connection


def connect_write(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise MigrationError(f"Banco não encontrado: {path}")
    connection = sqlite3.connect(
        path,
        timeout=15.0,
        factory=ClosingConnection,
    )
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=15000")
    return connection


def _normalize_sql(sql: str | None) -> str:
    return re.sub(r"\s+", " ", str(sql or "")).strip()


def functional_schema_hash(connection: sqlite3.Connection) -> str:
    rows = connection.execute(
        """
        SELECT type, name, tbl_name, COALESCE(sql, '')
        FROM sqlite_master
        WHERE name NOT LIKE 'sqlite_%'
          AND name != ?
        ORDER BY type, name
        """,
        (TECHNICAL_TABLE,),
    ).fetchall()
    canonical = "\n".join(
        "|".join((str(kind), str(name), str(table), _normalize_sql(sql)))
        for kind, name, table, sql in rows
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest().upper()


def logical_database_hash(path: Path) -> str:
    with connect_read_only(path) as connection:
        script = "\n".join(connection.iterdump())
    return hashlib.sha256(script.encode("utf-8")).hexdigest().upper()


def database_snapshot_hash(path: Path) -> str:
    with tempfile.TemporaryDirectory(prefix="assessor_migration_hash_") as tmp:
        snapshot = Path(tmp) / "snapshot.db"
        with connect_read_only(path) as source, sqlite3.connect(
            snapshot, factory=ClosingConnection
        ) as target:
            source.backup(target)
        return sha256_file(snapshot)


def migration_checksum(path: Path) -> str:
    return sha256_file(path)


def _load_migration(path: Path, version: int) -> ModuleType:
    module_name = f"_assessor_migration_{version:04d}_{migration_checksum(path)[:12]}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise MigrationError(f"Não foi possível carregar migration: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise MigrationError(f"Falha ao carregar {path.name}: {exc}") from exc
    finally:
        sys.modules.pop(module_name, None)
    return module


def discover_migrations(directory: Path = DEFAULT_MIGRATIONS_DIR) -> list[Migration]:
    directory = Path(directory)
    if not directory.is_dir():
        raise MigrationError(f"Diretório de migrations não encontrado: {directory}")

    migrations: list[Migration] = []
    for path in sorted(directory.glob("[0-9][0-9][0-9][0-9]_*.py")):
        match = MIGRATION_PATTERN.match(path.name)
        if not match:
            continue
        filename_version = int(match.group("version"))
        module = _load_migration(path, filename_version)
        version = int(getattr(module, "VERSION", -1))
        if version != filename_version:
            raise MigrationError(
                f"Versão interna divergente em {path.name}: "
                f"arquivo={filename_version}, módulo={version}"
            )
        name = str(getattr(module, "NAME", match.group("name"))).strip()
        if not name:
            raise MigrationError(f"Migration sem nome: {path.name}")
        upgrade = getattr(module, "upgrade", None)
        if not callable(upgrade):
            raise MigrationError(f"Migration sem upgrade(conn): {path.name}")
        supports_rollback = getattr(module, "SUPPORTS_ROLLBACK", None)
        if not isinstance(supports_rollback, bool):
            raise MigrationError(
                f"SUPPORTS_ROLLBACK deve ser bool em {path.name}"
            )
        if supports_rollback and not callable(getattr(module, "downgrade", None)):
            raise MigrationError(
                f"Migration declara rollback, mas não possui downgrade(conn): {path.name}"
            )
        sql = tuple(str(item) for item in getattr(module, "SQL", ()))
        affected = tuple(
            str(item) for item in getattr(module, "AFFECTED_OBJECTS", ())
        )
        expected_hash = getattr(module, "EXPECTED_SCHEMA_HASH", None)
        if expected_hash is not None:
            expected_hash = str(expected_hash).upper()
        resulting_hash = getattr(module, "RESULTING_SCHEMA_HASH", None)
        if resulting_hash is not None:
            resulting_hash = str(resulting_hash).upper()
        allows_preapplied = bool(
            getattr(module, "ALLOWS_PREAPPLIED_SCHEMA", False)
        )
        migrations.append(
            Migration(
                version=version,
                name=name,
                path=path,
                checksum=migration_checksum(path),
                sql=sql,
                affected_objects=affected,
                estimated_time_ms=max(
                    0, int(getattr(module, "ESTIMATED_TIME_MS", 0))
                ),
                supports_rollback=supports_rollback,
                expected_schema_hash=expected_hash,
                resulting_schema_hash=resulting_hash,
                allows_preapplied_schema=allows_preapplied,
                module=module,
            )
        )

    versions = [migration.version for migration in migrations]
    if len(versions) != len(set(versions)):
        raise MigrationError("Existem versões de migration duplicadas")
    if versions and versions != list(range(1, max(versions) + 1)):
        raise MigrationError(
            f"Ordem de migrations inválida: {versions}; esperado 1..{max(versions)}"
        )
    return migrations


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def applied_migrations(connection: sqlite3.Connection) -> list[dict]:
    if not _table_exists(connection, TECHNICAL_TABLE):
        return []
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT id, version, name, checksum, executed_at,
               execution_time_ms, success, rollback_supported
        FROM schema_migrations
        ORDER BY version
        """
    ).fetchall()
    return [dict(row) for row in rows]


def current_version(connection: sqlite3.Connection) -> int:
    user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    applied = [
        row for row in applied_migrations(connection)
        if int(row.get("success") or 0) == 1
    ]
    recorded = max((int(row["version"]) for row in applied), default=0)
    if _table_exists(connection, TECHNICAL_TABLE) and user_version != recorded:
        raise MigrationError(
            "Versão divergente: "
            f"PRAGMA user_version={user_version}, schema_migrations={recorded}"
        )
    if not _table_exists(connection, TECHNICAL_TABLE) and user_version != 0:
        raise MigrationError(
            "PRAGMA user_version indica migration, mas schema_migrations não existe"
        )
    return user_version


def _backup_destination_ready(directory: Path) -> bool:
    probe = Path(directory)
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return probe.exists() and probe.is_dir() and os.access(probe, os.W_OK)


def validate_compatibility(
    db_path: Path = DEFAULT_DB_PATH,
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
) -> ValidationResult:
    db_path = Path(db_path)
    migrations = discover_migrations(Path(migrations_dir))
    errors: list[str] = []
    integrity = "não verificada"
    version = 0
    schema_hash = ""
    expected_hash: str | None = None
    rollback_ready = all(
        isinstance(migration.supports_rollback, bool) for migration in migrations
    )
    backup_ready = _backup_destination_ready(Path(backup_dir))

    try:
        with connect_read_only(db_path) as connection:
            integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            if integrity.lower() != "ok":
                errors.append(f"Integridade SQLite inválida: {integrity}")
            schema_hash = functional_schema_hash(connection)
            version = current_version(connection)
            applied = {
                int(row["version"]): row
                for row in applied_migrations(connection)
                if int(row.get("success") or 0) == 1
            }
    except (sqlite3.Error, MigrationError) as exc:
        return ValidationResult(
            valid=False,
            integrity=integrity,
            current_version=version,
            schema_hash=schema_hash,
            expected_schema_hash=expected_hash,
            backup_ready=backup_ready,
            rollback_ready=rollback_ready,
            errors=[str(exc)],
        )

    available = {migration.version: migration for migration in migrations}
    for applied_version, row in applied.items():
        migration = available.get(applied_version)
        if migration is None:
            errors.append(
                f"Migration executada {applied_version} não existe no código"
            )
            continue
        if str(row["checksum"]).upper() != migration.checksum:
            errors.append(
                f"Checksum divergente na migration {applied_version:04d}"
            )

    pending = [migration for migration in migrations if migration.version > version]
    reference = pending[0] if pending else (
        available.get(version) if version else (migrations[0] if migrations else None)
    )
    if reference is not None:
        if pending:
            expected_hash = reference.expected_schema_hash
            preapplied_hashes = {
                migration.resulting_schema_hash
                for migration in pending
                if (
                    migration.allows_preapplied_schema
                    and migration.resulting_schema_hash
                )
            }
            if schema_hash in preapplied_hashes:
                expected_hash = schema_hash
        else:
            expected_hash = (
                reference.resulting_schema_hash
                or reference.expected_schema_hash
            )
        if expected_hash and schema_hash != expected_hash:
            errors.append(
                "Schema funcional divergente: "
                f"atual={schema_hash}, esperado={expected_hash}"
            )

    if not backup_ready:
        errors.append(f"Diretório de backup não está gravável: {backup_dir}")
    if not rollback_ready:
        errors.append("Declaração de rollback inválida")

    return ValidationResult(
        valid=not errors,
        integrity=integrity,
        current_version=version,
        schema_hash=schema_hash,
        expected_schema_hash=expected_hash,
        backup_ready=backup_ready,
        rollback_ready=rollback_ready,
        errors=errors,
    )


def get_status(
    db_path: Path = DEFAULT_DB_PATH,
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
) -> dict:
    migrations = discover_migrations(Path(migrations_dir))
    with connect_read_only(Path(db_path)) as connection:
        version = current_version(connection)
        executed = applied_migrations(connection)
    return {
        "current_version": version,
        "available": [
            {
                "version": migration.version,
                "name": migration.name,
                "checksum": migration.checksum,
            }
            for migration in migrations
        ],
        "executed": executed,
        "pending": [
            {
                "version": migration.version,
                "name": migration.name,
                "checksum": migration.checksum,
            }
            for migration in migrations
            if migration.version > version
        ],
    }


def dry_run(
    db_path: Path = DEFAULT_DB_PATH,
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
) -> dict:
    validation = validate_compatibility(db_path, migrations_dir, backup_dir)
    if not validation.valid:
        raise MigrationError("; ".join(validation.errors))
    migrations = discover_migrations(Path(migrations_dir))
    pending = [
        migration
        for migration in migrations
        if migration.version > validation.current_version
    ]
    plans = []
    for migration in pending:
        sql = list(migration.sql)
        if validation.current_version == 0 and migration.version == 1:
            sql = [
                CREATE_SCHEMA_MIGRATIONS_SQL,
                *sql,
                "INSERT INTO schema_migrations (...) VALUES (...)",
                f"PRAGMA user_version = {migration.version}",
            ]
        else:
            sql.extend(
                [
                    "INSERT INTO schema_migrations (...) VALUES (...)",
                    f"PRAGMA user_version = {migration.version}",
                ]
            )
        plans.append(
            {
                "version": migration.version,
                "name": migration.name,
                "checksum": migration.checksum,
                "sql": sql,
                "estimated_time_ms": migration.estimated_time_ms,
                "affected_objects": sorted(
                    {TECHNICAL_TABLE, *migration.affected_objects}
                ),
                "backup_directory": str(Path(backup_dir)),
            }
        )
    return {
        "dry_run": True,
        "current_version": validation.current_version,
        "schema_hash": validation.schema_hash,
        "plans": plans,
        "changes_applied": False,
    }


def _unique_backup_path(directory: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = directory / f"financeiro_schema_backup_{timestamp}.db"
    if not base.exists():
        return base
    for sequence in range(1, 1000):
        candidate = directory / (
            f"financeiro_schema_backup_{timestamp}_{sequence:02d}.db"
        )
        if not candidate.exists():
            return candidate
    raise MigrationError("Não foi possível gerar nome único para o backup")


def create_schema_backup(
    db_path: Path,
    backup_dir: Path,
    version: int,
) -> BackupInfo:
    db_path = Path(db_path)
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    destination = _unique_backup_path(backup_dir)
    temporary = destination.with_suffix(".tmp")
    try:
        with connect_read_only(db_path) as source, sqlite3.connect(
            temporary, factory=ClosingConnection
        ) as target:
            source.backup(target)
        with connect_read_only(temporary, immutable=True) as check:
            integrity = str(check.execute("PRAGMA integrity_check").fetchone()[0])
            if integrity.lower() != "ok":
                raise MigrationError(f"Backup inválido: {integrity}")
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise

    created_at = datetime.now().isoformat(timespec="seconds")
    metadata_path = destination.with_suffix(".json")
    metadata = {
        "path": str(destination),
        "sha256": sha256_file(destination),
        "size": destination.stat().st_size,
        "version": int(version),
        "created_at": created_at,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return BackupInfo(
        path=destination,
        checksum=metadata["sha256"],
        size=metadata["size"],
        version=metadata["version"],
        created_at=created_at,
        metadata_path=metadata_path,
    )


def _append_audit(audit_log: Path, event: dict) -> None:
    audit_log = Path(audit_log)
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    with audit_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def apply_migrations(
    db_path: Path = DEFAULT_DB_PATH,
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
    audit_log: Path | None = None,
    *,
    dry_run_only: bool = False,
    executed_by: str | None = None,
) -> dict:
    db_path = Path(db_path)
    migrations_dir = Path(migrations_dir)
    backup_dir = Path(backup_dir)
    audit_log = Path(audit_log or (backup_dir / "migrations_audit.jsonl"))
    if dry_run_only:
        return dry_run(db_path, migrations_dir, backup_dir)

    validation = validate_compatibility(db_path, migrations_dir, backup_dir)
    if not validation.valid:
        raise MigrationError("; ".join(validation.errors))
    migrations = discover_migrations(migrations_dir)
    pending = [
        migration
        for migration in migrations
        if migration.version > validation.current_version
    ]
    results = []
    actor = executed_by or getpass.getuser() or "unknown"
    current = validation.current_version

    for migration in pending:
        step_validation = validate_compatibility(
            db_path, migrations_dir, backup_dir
        )
        if not step_validation.valid:
            raise MigrationError("; ".join(step_validation.errors))
        if step_validation.current_version != current:
            raise MigrationError(
                "Versão mudou durante a execução: "
                f"esperada={current}, atual={step_validation.current_version}"
            )
        backup = create_schema_backup(db_path, backup_dir, current)
        started = time.perf_counter()
        before_hash = backup.checksum
        event = {
            "event": "migration",
            "version": migration.version,
            "name": migration.name,
            "executed_at": datetime.now().isoformat(timespec="seconds"),
            "executed_by": actor,
            "result": "failed",
            "hash_before": before_hash,
            "hash_after": None,
            "backup_path": str(backup.path),
            "backup_sha256": backup.checksum,
            "backup_size": backup.size,
            "version_before": current,
            "version_after": current,
        }
        connection = connect_write(db_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(CREATE_SCHEMA_MIGRATIONS_SQL)
            migration.module.upgrade(connection)
            resulting_hash = functional_schema_hash(connection)
            if (
                migration.resulting_schema_hash
                and resulting_hash != migration.resulting_schema_hash
            ):
                raise MigrationError(
                    "Schema resultante divergente na migration "
                    f"{migration.version:04d}: atual={resulting_hash}, "
                    f"esperado={migration.resulting_schema_hash}"
                )
            elapsed_ms = max(0, round((time.perf_counter() - started) * 1000))
            connection.execute(
                """
                INSERT INTO schema_migrations (
                    version, name, checksum, executed_at,
                    execution_time_ms, success, rollback_supported
                ) VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    migration.version,
                    migration.name,
                    migration.checksum,
                    event["executed_at"],
                    elapsed_ms,
                    1 if migration.supports_rollback else 0,
                ),
            )
            connection.execute(f"PRAGMA user_version={migration.version}")
            connection.commit()
        except Exception as exc:
            connection.rollback()
            event["error"] = str(exc)
            event["execution_time_ms"] = max(
                0, round((time.perf_counter() - started) * 1000)
            )
            try:
                event["hash_after"] = database_snapshot_hash(db_path)
            except Exception as hash_error:
                event["hash_error"] = str(hash_error)
            _append_audit(audit_log, event)
            raise MigrationError(
                f"Migration {migration.version:04d} falhou: {exc}"
            ) from exc
        finally:
            connection.close()

        elapsed_ms = max(0, round((time.perf_counter() - started) * 1000))
        after_hash = database_snapshot_hash(db_path)
        event.update(
            {
                "result": "success",
                "hash_after": after_hash,
                "execution_time_ms": elapsed_ms,
                "version_after": migration.version,
                "rollback_supported": migration.supports_rollback,
            }
        )
        _append_audit(audit_log, event)
        results.append(event)
        current = migration.version

    return {
        "previous_version": validation.current_version,
        "current_version": current,
        "executed": results,
    }


def _latest_backup(backup_dir: Path) -> Path:
    backups = sorted(
        Path(backup_dir).glob("financeiro_schema_backup_*.db"),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    if not backups:
        raise MigrationError(f"Nenhum backup encontrado em {backup_dir}")
    return backups[0]


def _validate_backup(path: Path) -> tuple[str, int]:
    path = Path(path)
    if not path.is_file():
        raise MigrationError(f"Backup não encontrado: {path}")
    with connect_read_only(path, immutable=True) as connection:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if integrity.lower() != "ok":
        raise MigrationError(f"Backup inválido: {integrity}")
    metadata_path = path.with_suffix(".json")
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        expected = str(metadata.get("sha256") or "").upper()
        actual = sha256_file(path)
        if expected and expected != actual:
            raise MigrationError(
                f"Checksum do backup divergente: esperado={expected}, atual={actual}"
            )
        expected_size = metadata.get("size")
        if expected_size is not None and int(expected_size) != path.stat().st_size:
            raise MigrationError(
                "Tamanho do backup diverge do metadado: "
                f"esperado={expected_size}, atual={path.stat().st_size}"
            )
        expected_version = metadata.get("version")
        if expected_version is not None and int(expected_version) != version:
            raise MigrationError(
                "Versão do backup diverge do metadado: "
                f"esperada={expected_version}, atual={version}"
            )
    return integrity, version


def rollback(
    db_path: Path = DEFAULT_DB_PATH,
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
    audit_log: Path | None = None,
    *,
    strategy: str = "backup",
    backup_path: Path | None = None,
    executed_by: str | None = None,
) -> dict:
    db_path = Path(db_path)
    migrations_dir = Path(migrations_dir)
    backup_dir = Path(backup_dir)
    audit_log = Path(audit_log or (backup_dir / "migrations_audit.jsonl"))
    migrations = discover_migrations(migrations_dir)
    with connect_read_only(db_path) as connection:
        version_before = current_version(connection)
    if version_before <= 0:
        raise MigrationError("Não existe migration aplicada para rollback")

    actor = executed_by or getpass.getuser() or "unknown"
    before_hash = database_snapshot_hash(db_path)
    event = {
        "event": "rollback",
        "strategy": strategy,
        "executed_at": datetime.now().isoformat(timespec="seconds"),
        "executed_by": actor,
        "result": "failed",
        "hash_before": before_hash,
        "hash_after": None,
        "version_before": version_before,
        "version_after": version_before,
    }

    if strategy == "backup":
        selected = Path(backup_path) if backup_path else _latest_backup(backup_dir)
        _validate_backup(selected)
        expected_logical_hash = logical_database_hash(selected)
        safety = create_schema_backup(db_path, backup_dir, version_before)
        event.update(
            {
                "restored_backup": str(selected),
                "safety_backup": str(safety.path),
            }
        )
        try:
            with connect_read_only(selected, immutable=True) as source:
                destination = connect_write(db_path)
                try:
                    source.backup(destination)
                    destination.commit()
                finally:
                    destination.close()
            if logical_database_hash(db_path) != expected_logical_hash:
                raise MigrationError("Banco restaurado diverge logicamente do backup")
            with connect_read_only(db_path) as connection:
                version_after = int(
                    connection.execute("PRAGMA user_version").fetchone()[0]
                )
        except Exception as exc:
            event["error"] = str(exc)
            _append_audit(audit_log, event)
            raise
    elif strategy == "migration":
        migration_by_version = {
            migration.version: migration for migration in migrations
        }
        migration = migration_by_version.get(version_before)
        if migration is None:
            raise MigrationError(
                f"Migration {version_before:04d} não está disponível"
            )
        if not migration.supports_rollback:
            raise MigrationError(
                f"Migration {version_before:04d} não suporta rollback"
            )
        safety = create_schema_backup(db_path, backup_dir, version_before)
        event["safety_backup"] = str(safety.path)
        destination = connect_write(db_path)
        try:
            destination.execute("BEGIN IMMEDIATE")
            migration.module.downgrade(destination)
            destination.execute(
                "DELETE FROM schema_migrations WHERE version=?",
                (version_before,),
            )
            version_after = version_before - 1
            destination.execute(f"PRAGMA user_version={version_after}")
            if version_after == 0:
                destination.execute("DROP TABLE schema_migrations")
            destination.commit()
        except Exception:
            destination.rollback()
            raise
        finally:
            destination.close()
    else:
        raise MigrationError(f"Estratégia de rollback inválida: {strategy}")

    after_hash = database_snapshot_hash(db_path)
    event.update(
        {
            "result": "success",
            "hash_after": after_hash,
            "version_after": version_after,
        }
    )
    _append_audit(audit_log, event)
    return event


def _print_status(status: dict) -> None:
    print(f"Versão atual: {status['current_version']}")
    print("Migrações disponíveis:")
    if status["available"]:
        for item in status["available"]:
            print(f"  {item['version']:04d} {item['name']}")
    else:
        print("  nenhuma")
    print("Migrações executadas:")
    if status["executed"]:
        for item in status["executed"]:
            print(
                f"  {int(item['version']):04d} {item['name']} "
                f"success={int(item['success'])}"
            )
    else:
        print("  nenhuma")
    print("Pendentes:")
    if status["pending"]:
        for item in status["pending"]:
            print(f"  {item['version']:04d} {item['name']}")
    else:
        print("  nenhuma")


def _print_validation(result: ValidationResult) -> None:
    print(f"Válido: {'sim' if result.valid else 'não'}")
    print(f"Integridade: {result.integrity}")
    print(f"Versão atual: {result.current_version}")
    print(f"Hash do schema: {result.schema_hash}")
    print(f"Hash esperado: {result.expected_schema_hash or 'não definido'}")
    print(f"Backup: {'pronto' if result.backup_ready else 'indisponível'}")
    print(f"Rollback: {'pronto' if result.rollback_ready else 'inválido'}")
    for error in result.errors:
        print(f"ERRO: {error}")


def _print_dry_run(plan: dict) -> None:
    print("DRY RUN — nenhuma alteração será aplicada")
    print(f"Versão atual: {plan['current_version']}")
    if not plan["plans"]:
        print("Nenhuma migration pendente.")
        return
    for item in plan["plans"]:
        print(f"Migration encontrada: {item['version']:04d} {item['name']}")
        print(f"Tempo estimado: {item['estimated_time_ms']} ms")
        print(
            "Objetos afetados: "
            + (", ".join(item["affected_objects"]) or "nenhum")
        )
        print("SQL previsto:")
        for sql in item["sql"]:
            print(f"  {sql}")
    print("Alterações aplicadas: não")


def _add_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument(
        "--migrations-dir", type=Path, default=DEFAULT_MIGRATIONS_DIR
    )
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--audit-log", type=Path, default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Framework seguro de migrations do Assessor Financeiro"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("status", "validate", "dry-run", "migrate"):
        subparser = subparsers.add_parser(command)
        _add_paths(subparser)
    migrate_parser = subparsers.choices["migrate"]
    migrate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Planeja sem alterar o conteúdo do banco; o SQLite pode gerenciar "
            "sidecars WAL/SHM"
        ),
    )
    rollback_parser = subparsers.add_parser("rollback")
    _add_paths(rollback_parser)
    rollback_parser.add_argument(
        "--strategy",
        choices=("backup", "migration"),
        default="backup",
    )
    rollback_parser.add_argument("--backup", type=Path, default=None)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "status":
            _print_status(get_status(args.db, args.migrations_dir))
        elif args.command == "validate":
            result = validate_compatibility(
                args.db, args.migrations_dir, args.backup_dir
            )
            _print_validation(result)
            return 0 if result.valid else 1
        elif args.command == "dry-run":
            _print_dry_run(
                dry_run(args.db, args.migrations_dir, args.backup_dir)
            )
        elif args.command == "migrate":
            if args.dry_run:
                _print_dry_run(
                    dry_run(args.db, args.migrations_dir, args.backup_dir)
                )
            else:
                result = apply_migrations(
                    args.db,
                    args.migrations_dir,
                    args.backup_dir,
                    args.audit_log,
                )
                print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "rollback":
            result = rollback(
                args.db,
                args.migrations_dir,
                args.backup_dir,
                args.audit_log,
                strategy=args.strategy,
                backup_path=args.backup,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (MigrationError, sqlite3.Error, OSError, ValueError) as exc:
        LOGGER.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
