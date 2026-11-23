# Migrations do Assessor Financeiro

Este diretório contém migrations numeradas. O runner é
`C:\Projetos\assessor-financeiro\migrations.py`.

## Comandos

```powershell
python migrations.py status
python migrations.py validate
python migrations.py dry-run
python migrations.py migrate --dry-run
python migrations.py migrate
python migrations.py rollback --strategy backup
python migrations.py rollback --strategy migration
```

`status`, `validate` e `dry-run` não alteram o conteúdo do banco principal,
não criam objetos de schema e não criam `schema_migrations`. Em bancos SQLite
configurados com WAL, o próprio SQLite pode criar ou atualizar os arquivos
auxiliares `-wal` e `-shm` durante conexões somente leitura. Esses sidecars são
mecanismos de coordenação do SQLite e não representam alteração do conteúdo
do banco principal.

`migrate` cria um backup online validado em `backups/schema/` antes de cada
migration. O comando não é executado automaticamente pelo bot.

## Fluxo operacional

```text
status
  ↓
validate
  ↓
dry-run
  ↓
backup
  ↓
migrate
  ↓
rollback (quando necessário)
```

`status`, `validate` e `dry-run` são etapas de inspeção e planejamento. O
backup e as alterações persistentes acontecem somente depois da chamada
explícita de `migrate`. O rollback também exige chamada explícita.

## Contrato de uma migration

Cada arquivo deve usar o nome `NNNN_nome.py` e declarar:

```python
VERSION = 2
NAME = "nome"
SUPPORTS_ROLLBACK = True
EXPECTED_SCHEMA_HASH = "SHA256_DO_SCHEMA_ANTERIOR"
RESULTING_SCHEMA_HASH = "SHA256_DO_SCHEMA_RESULTANTE"
ALLOWS_PREAPPLIED_SCHEMA = False
ESTIMATED_TIME_MS = 100
SQL = ("ALTER TABLE ...",)
AFFECTED_OBJECTS = ("tabela",)

def upgrade(connection):
    ...

def downgrade(connection):
    ...
```

Regras:

- versões são contínuas e começam em 1;
- migrations aplicadas não podem ser editadas: o checksum é validado;
- toda alteração usa a conexão/transaction fornecida pelo runner;
- `SUPPORTS_ROLLBACK` é obrigatório;
- o hash esperado deve representar o schema funcional anterior;
- migrations que alteram schema devem declarar `RESULTING_SCHEMA_HASH`, e o
  runner valida esse hash antes do commit;
- `ALLOWS_PREAPPLIED_SCHEMA=True` só deve ser usado quando bancos novos já
  nascem com o schema resultante e o `upgrade()` é idempotente;
- migrations não devem importar `services.py`, `compromissos.py` ou iniciar o
  bot;
- cada evolução futura deve incluir seus próprios testes.

## Versionamento oficial

O framework adota oficialmente uma arquitetura híbrida com duas fontes
persistentes, complementares e obrigatoriamente sincronizadas:

- `PRAGMA user_version`: representa exclusivamente a versão corrente do
  banco, com leitura nativa e rápida pelo SQLite;
- `schema_migrations`: mantém o histórico verificável, nome, checksum, data,
  duração, sucesso e suporte a rollback de cada migration aplicada.

Se as duas fontes divergirem, a execução é interrompida.

A tabela `schema_migrations` não é criada por `status`, `validate` ou
`dry-run`. Somente `migrate`, por meio de `apply_migrations()`, está autorizado
a criá-la quando houver uma migration real a aplicar.

## Baseline 0001

`0001_baseline.py` é intencionalmente no-op. Ela não altera Pix, Lia,
checklist, parser, saldos, compromissos, transações nem qualquer tabela
funcional. O runner cria somente a tabela técnica `schema_migrations`.

## Modelo de pagamento 0002

`0002_campos_pagamento_canonicos.py` expande somente `compromissos`:

- adiciona `conta_origem TEXT NULL`, se ausente;
- preserva `forma_pagamento TEXT NULL`, que já existe no baseline;
- adiciona `destino_pagamento TEXT NULL`, se ausente;
- preserva integralmente `conta_pagamento`;
- não executa `UPDATE`, backfill ou inferência.

A verificação condicional das colunas evita duplicar `forma_pagamento` e torna
o `upgrade()` idempotente em nível de schema. O runner continua impedindo a
aplicação repetida pela versão e pelo histórico.

Como bancos novos já nascem com as colunas, a 0002 declara
`ALLOWS_PREAPPLIED_SCHEMA=True`. O runner reconhece o hash final conhecido,
registra 0001/0002 e o `upgrade()` não duplica colunas.

`SUPPORTS_ROLLBACK=False` porque remover colunas por reconstrução da tabela
seria desnecessariamente destrutivo. O rollback operacional da 0002 deve usar
o backup automático da versão 1:

```powershell
python migrations.py rollback --strategy backup
```

## Auditoria e backup

Cada backup possui:

- arquivo `financeiro_schema_backup_YYYYMMDD_HHMMSS.db`;
- metadado JSON com SHA-256, tamanho, versão e data;
- validação `PRAGMA integrity_check`.

Cada execução/rollback é registrada em
`backups/schema/migrations_audit.jsonl`, incluindo usuário, resultado, tempo,
versões e hashes antes/depois.
