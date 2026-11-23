import contextlib
import sqlite3
from pathlib import Path

import database


LEGACY_COMPROMISSOS_SQL = """
CREATE TABLE compromissos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    nome TEXT NOT NULL,
    categoria TEXT NOT NULL,
    conta_pagamento TEXT,
    forma_pagamento TEXT,
    valor REAL NOT NULL,
    dia_vencimento INTEGER,
    data_inicio TEXT NOT NULL,
    data_fim TEXT,
    parcelas_total INTEGER,
    ativo INTEGER NOT NULL DEFAULT 1,
    origem TEXT,
    observacao TEXT,
    criado_em TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
)
"""


def criar_banco_legado(path: Path) -> Path:
    """Cria fixture RC1.5.4 sem depender do banco de produção."""
    path = Path(path)
    old_path = database.DB_PATH
    try:
        database.DB_PATH = path
        database.init_db()
    finally:
        database.DB_PATH = old_path

    with contextlib.closing(sqlite3.connect(path)) as connection:
        connection.execute("DROP TABLE compromissos")
        connection.execute(LEGACY_COMPROMISSOS_SQL)
        connection.commit()
    return path


def colunas_tabela(path: Path, tabela: str) -> list[tuple]:
    with contextlib.closing(sqlite3.connect(path)) as connection:
        return [
            tuple(row[1:6])
            for row in connection.execute(f'PRAGMA table_info("{tabela}")')
        ]
