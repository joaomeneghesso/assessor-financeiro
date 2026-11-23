---
name: nova-migration
description: Cria uma nova migration de banco (migrations/000N_*.py) seguindo o framework do projeto, com backup prévio e testes. Use ao alterar o esquema SQLite.
disable-model-invocation: true
---
# Nova migration

Antes: leia `migrations/README.md`, `docs/DECISAO_ARQUITETURAL_MIGRATIONS.md` e a última migration (`0004_competencia_faturas.py`) como modelo.

1. Nunca altere esquema em `database.py` sem migration; nunca edite migrations já aplicadas.
2. Crie `migrations/000N_nome.py` seguindo a interface das existentes (versão, descrição, função de aplicação idempotente).
3. A migration deve ser reversível por backup: confirme que o backup prévio do framework roda (`sqlite_backup.py`).
4. Escreva teste em `tests/` usando banco temporário, com dados antes/depois e verificação de integridade.
5. Rode a skill `rodar-gate`. Registre no CHANGELOG (skill `fechar-versao`).
6. NUNCA aplique em `data/financeiro.db` sem o usuário pedir; antes, backup (`backup_db.ps1`).
