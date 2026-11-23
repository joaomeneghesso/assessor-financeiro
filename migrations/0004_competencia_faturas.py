"""V39: campos opcionais de competencia de fatura, sem redistribuir historico."""
VERSION = 4
NAME = 'competencia_faturas'
DESCRIPTION = 'Adiciona data_compra e competencia_fatura, sem backfill nem alteracao de valores.'
SUPPORTS_ROLLBACK = False
EXPECTED_SCHEMA_HASH = '6A80F75A7CD79B5B30A890B1E8F2F31C6ED2FAB0614C85CF7F7DA9FA32DE3A9A'
RESULTING_SCHEMA_HASH = '006361B321E88161E465DB3917833E6479720788E6BC0BAA6A89DDC530948673'
ALLOWS_PREAPPLIED_SCHEMA = False
ESTIMATED_TIME_MS = 50
AFFECTED_OBJECTS = ('transacoes',)
SQL = (
    'ALTER TABLE transacoes ADD COLUMN data_compra TEXT NULL',
    'ALTER TABLE transacoes ADD COLUMN competencia_fatura TEXT NULL',
)


def upgrade(connection):
    columns = {row[1] for row in connection.execute('PRAGMA table_info(transacoes)')}
    if not {'id', 'data', 'tipo', 'valor', 'conta', 'forma_pagamento'} <= columns:
        raise RuntimeError('Tabela transacoes incompativel com a v39.')
    if {'data_compra', 'competencia_fatura'} & columns:
        raise RuntimeError('Campos da v39 ja existem sem a migration registrada. Revise o schema.')
    for statement in SQL:
        connection.execute(statement)


def downgrade(connection):
    raise RuntimeError('Nao remova competencias com compras registradas. Use o backup compativel; restaurar banco antigo descarta registros posteriores.')
