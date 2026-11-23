"""Baseline da RC1.5.4.

Esta migration não altera tabelas funcionais. A tabela técnica
``schema_migrations`` e o ``PRAGMA user_version`` são geridos pelo runner.
"""

VERSION = 1
NAME = "baseline"
SUPPORTS_ROLLBACK = True
EXPECTED_SCHEMA_HASH = (
    "C9865CBFABAB309EB2C080A974F96AF3D6B3211F1D8282377E36E3979E9F23D4"
)
ESTIMATED_TIME_MS = 25
SQL = ("-- baseline no-op: nenhuma tabela funcional será alterada",)
AFFECTED_OBJECTS = ()


def upgrade(connection):
    """Registra o baseline sem executar DDL funcional."""


def downgrade(connection):
    """Desfaz o baseline sem executar DDL funcional."""
