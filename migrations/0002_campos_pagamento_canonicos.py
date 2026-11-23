"""Expansão aditiva do modelo de pagamento de compromissos.

O campo ``forma_pagamento`` já existe no baseline e é preservado byte a byte.
Esta migration adiciona somente as colunas ausentes e não executa backfill.
O rollback operacional suportado é a restauração do backup pré-migration.
"""

VERSION = 2
NAME = "campos_pagamento_canonicos"
DESCRIPTION = (
    "Adiciona conta_origem e destino_pagamento opcionais; preserva "
    "conta_pagamento e forma_pagamento existentes."
)
SUPPORTS_ROLLBACK = False
EXPECTED_SCHEMA_HASH = (
    "C9865CBFABAB309EB2C080A974F96AF3D6B3211F1D8282377E36E3979E9F23D4"
)
RESULTING_SCHEMA_HASH = (
    "6A80F75A7CD79B5B30A890B1E8F2F31C6ED2FAB0614C85CF7F7DA9FA32DE3A9A"
)
ALLOWS_PREAPPLIED_SCHEMA = True
ESTIMATED_TIME_MS = 50

SQL = (
    "ALTER TABLE compromissos ADD COLUMN conta_origem TEXT NULL",
    "ALTER TABLE compromissos ADD COLUMN destino_pagamento TEXT NULL",
)
AFFECTED_OBJECTS = ("compromissos",)

_COLUMNS = (
    ("conta_origem", SQL[0]),
    ("destino_pagamento", SQL[1]),
)


def _column_names(connection) -> set[str]:
    table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='compromissos'"
    ).fetchone()
    if table is None:
        raise RuntimeError("Tabela obrigatória ausente: compromissos")
    return {
        str(row[1])
        for row in connection.execute("PRAGMA table_info(compromissos)")
    }


def upgrade(connection):
    """Adiciona somente colunas ausentes, sem alterar qualquer linha."""
    columns = _column_names(connection)
    required = {"conta_pagamento", "forma_pagamento"}
    missing_required = sorted(required - columns)
    if missing_required:
        raise RuntimeError(
            "Schema legado incompatível; colunas ausentes: "
            + ", ".join(missing_required)
        )
    for name, statement in _COLUMNS:
        if name not in columns:
            connection.execute(statement)
            columns.add(name)


def downgrade(connection):
    """Rollback SQL não suportado; restaure o backup criado pelo runner."""
    raise RuntimeError(
        "A migration 0002 requer rollback por restauração de backup"
    )
