# Decisão arquitetural — versionamento híbrido de migrations

Data: 24/07/2026  
Status: aceita e oficial a partir da RC1.5.4A  
Escopo: framework SQLite de migrations do Assessor Financeiro

## 1. Decisão

O framework usa duas fontes persistentes, complementares e obrigatoriamente
sincronizadas:

1. `PRAGMA user_version`, para representar a versão corrente do banco;
2. a tabela SQLite `schema_migrations`, para registrar o histórico verificável
   das migrations aplicadas.

Essa arquitetura híbrida substitui oficialmente a interpretação anterior de
que seria necessário escolher apenas uma dessas fontes.

## 2. Por que usar `PRAGMA user_version`

`PRAGMA user_version` é um inteiro mantido no cabeçalho do banco SQLite. Ele
oferece:

- leitura nativa e rápida da versão corrente;
- interoperabilidade com ferramentas externas ao projeto;
- verificação simples antes de uma operação;
- ausência de consulta a uma tabela para descobrir a versão atual.

Sua responsabilidade é deliberadamente estreita: informar a versão corrente.
Ele não registra nome, checksum, data, duração, resultado ou capacidade de
rollback.

## 3. Por que usar `schema_migrations`

`schema_migrations` é uma tabela técnica SQLite com os campos:

- `id`;
- `version`;
- `name`;
- `checksum`;
- `executed_at`;
- `execution_time_ms`;
- `success`;
- `rollback_supported`.

Ela oferece:

- histórico ordenado das migrations;
- detecção de arquivo de migration alterado após aplicação, por checksum;
- data e duração de cada aplicação;
- registro do resultado;
- declaração verificável da capacidade de rollback;
- base de auditoria para validar a evolução do schema.

Sua responsabilidade é explicar como o banco chegou à versão corrente. Ela
não substitui o valor nativo de versão exposto pelo SQLite.

## 4. Regra de consistência

As duas fontes formam um único contrato:

- o maior registro bem-sucedido em `schema_migrations` deve ser igual a
  `PRAGMA user_version`;
- se `schema_migrations` não existe, `user_version` deve ser `0`;
- qualquer divergência interrompe validação, migration e rollback;
- migrations aplicadas também precisam manter o checksum original.

O banco real permanece no estado inicial enquanto nenhuma migration é
aplicada:

```text
PRAGMA user_version = 0
schema_migrations = inexistente
```

## 5. Criação da tabela técnica

`schema_migrations` somente pode ser criada durante uma aplicação real:

```text
migrate
  └─ apply_migrations()
       ├─ valida compatibilidade
       ├─ cria e valida backup
       ├─ abre transação de escrita
       ├─ cria schema_migrations, se necessário
       ├─ executa upgrade()
       ├─ registra a migration
       ├─ atualiza PRAGMA user_version
       └─ commit
```

Os comandos abaixo não criam a tabela:

- `status`;
- `validate`;
- `dry-run`;
- `migrate --dry-run`.

Eles usam `connect_read_only()`, com URI `mode=ro` e
`PRAGMA query_only=ON`. No `dry-run`, o DDL é apenas exibido como parte do
plano; ele não é executado.

## 6. Fluxo operacional completo

```text
status
  ↓
validate
  ↓
dry-run
  ↓
backup automático validado
  ↓
migrate em transação
  ↓
validação e auditoria
  ↓
rollback por backup ou migration, quando necessário
```

### `status`

Consulta versão atual, migrations disponíveis, executadas e pendentes.

### `validate`

Verifica integridade, hash do schema, versão, checksums, contrato de rollback
e disponibilidade do destino de backup.

### `dry-run`

Exibe migration, SQL previsto, tempo estimado, objetos afetados e destino do
backup. Não executa DDL/DML e não altera o conteúdo do banco principal.

### Backup

Antes de cada migration real, o runner cria backup online, valida integridade,
calcula SHA-256 e registra tamanho, versão e data.

### `migrate`

Abre transação de escrita, cria a tabela técnica quando necessário, executa a
migration, registra o histórico, atualiza `user_version` e confirma
atomicamente.

### Rollback

Quando necessário, restaura um backup validado ou executa `downgrade()` da
migration, atualizando de forma consistente as duas fontes de versão.

## 7. Vantagens

- consulta rápida da versão corrente;
- histórico detalhado e auditável;
- detecção de inconsistência entre estado resumido e histórico;
- detecção de migrations modificadas;
- integração simples com ferramentas SQLite;
- suporte explícito a rollback;
- nenhuma dependência do código financeiro.

## 8. Limitações

- as duas fontes precisam ser atualizadas na mesma transação;
- intervenções manuais podem produzir divergência e bloquear o runner;
- a auditoria JSONL e os backups precisam de proteção operacional;
- o framework não possui lock externo entre dois processos; a escrita é
  serializada pelo `BEGIN IMMEDIATE` do SQLite;
- o runner aceita qualquer caminho informado por `--db`, portanto operações
  de escrita exigem disciplina operacional;
- conexões somente leitura em bancos configurados com WAL podem criar ou
  atualizar arquivos auxiliares `-wal` e `-shm`.

Os sidecars WAL/SHM não são tabelas, não são migrations e não representam
alteração do conteúdo lógico do banco principal. Por essa razão, `status`,
`validate` e `dry-run` garantem ausência de alteração do conteúdo e do schema,
mas não prometem ausência absoluta de atividade no filesystem.

## 9. Consequências

- a arquitetura híbrida passa a ser normativa;
- futuras migrations devem preservar a consistência entre as duas fontes;
- `schema_migrations` continua sendo a única tabela técnica permitida;
- nenhuma tabela funcional é alterada por esta decisão;
- a RC1.5.4A não aplica migration nem muda o banco real;
- não há mudança em parser, Pix, Lia, checklist, cálculos ou regras
  financeiras.

