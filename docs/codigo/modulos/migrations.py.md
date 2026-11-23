---
tipo: modulo
grupo: Dados, backup e segurança
linhas: 1005
tags: [modulo, dados-backup-e-seguranca]
---
# migrations.py

> Framework versionado e isolado de migrations SQLite.

**Grupo:** [[Dados, backup e segurança]] · **Linhas:** 1005 · **Funções:** 31 · **Classes:** 5

## Usa

- (nenhum módulo do projeto)

## Usado por

- (ninguém no código de produção; ponto de entrada ou script)

## Tudo que define

- classe `ClosingConnection` (L52, 8 linhas) — Conexão cujo context manager também libera o handle no Windows.
- classe `MigrationError` (L62, 2 linhas) — Erro seguro e esperado do framework de migrations.
- classe `Migration` (L67, 13 linhas)
- classe `BackupInfo` (L83, 7 linhas)
- classe `ValidationResult` (L93, 9 linhas)
- `sha256_file` (L104, 6 linhas)
- `_sqlite_uri` (L112, 5 linhas)
- `connect_read_only` (L119, 12 linhas)
- `connect_write` (L133, 11 linhas)
- `_normalize_sql` (L146, 2 linhas)
- `functional_schema_hash` (L150, 16 linhas)
- `logical_database_hash` (L168, 4 linhas)
- `database_snapshot_hash` (L174, 8 linhas)
- `migration_checksum` (L184, 2 linhas)
- `_load_migration` (L188, 14 linhas)
- `discover_migrations` (L204, 73 linhas)
- `_table_exists` (L279, 6 linhas)
- `applied_migrations` (L287, 13 linhas)
- `current_version` (L302, 17 linhas)
- `_backup_destination_ready` (L321, 5 linhas)
- `validate_compatibility` (L328, 97 linhas)
- `get_status` (L427, 29 linhas)
- `dry_run` (L458, 51 linhas)
- `_unique_backup_path` (L511, 12 linhas)
- `create_schema_backup` (L525, 46 linhas)
- `_append_audit` (L573, 5 linhas)
- `apply_migrations` (L580, 129 linhas)
- `_latest_backup` (L711, 9 linhas)
- `_validate_backup` (L722, 31 linhas)
- `rollback` (L755, 109 linhas)
- `_print_status` (L866, 23 linhas)
- `_print_validation` (L891, 10 linhas)
- `_print_dry_run` (L903, 17 linhas)
- `_add_paths` (L922, 7 linhas)
- `build_parser` (L931, 26 linhas)
- `main` (L959, 43 linhas)

## Documentos que citam

- [[OPERACAO]]
- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
