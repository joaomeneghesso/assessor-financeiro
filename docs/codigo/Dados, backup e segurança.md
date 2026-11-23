---
tipo: grupo
tags: [grupo, dados-backup-e-seguranca]
---
# Dados, backup e segurança

Banco SQLite, migrations, backups (local e externo cifrado), PIN, estado protegido e limitador.

[[00 Início|← Início]]

| Módulo | Linhas | Usado por | Papel |
|---|---|---|---|
| [[database.py]] | 1960 | 23 |  |
| [[migrations.py]] | 1005 | 0 | Framework versionado e isolado de migrations SQLite. |
| [[backup_externo.py]] | 304 | 2 | Cópia diária criptografada do assessor FORA do computador (OneDrive por padrão). |
| [[estado_runtime.py]] | 189 | 3 | Estado efêmero protegido para retomada do Telegram. |
| [[security.py]] | 182 | 3 |  |
| [[preparar_seguranca_v40.py]] | 139 | 0 |  |
| [[backup_externo_cli.py]] | 86 | 0 | Linha de comando do backup externo criptografado (rodar no terminal do titular). |
| [[limitador_persistente.py]] | 75 | 1 | Limitador de tentativas de PIN que sobrevive a reinícios do bot. |
| [[sqlite_backup.py]] | 28 | 1 | Backup consistente de SQLite, incluindo transações confirmadas no WAL. |

---
*Gerado por `tools/gerar_vault_codigo.py`.*
