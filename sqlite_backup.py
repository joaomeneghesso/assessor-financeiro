"""Backup consistente de SQLite, incluindo transações confirmadas no WAL."""
from contextlib import closing
from pathlib import Path
import sqlite3
import uuid


def backup_sqlite_consistente(origem, destino):
    origem, destino = Path(origem).resolve(), Path(destino).resolve()
    if origem == destino:
        raise ValueError('Origem e destino do backup precisam ser diferentes.')
    if destino.exists():
        raise FileExistsError(f'O destino do backup já existe: {destino}')
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name+'.tmp_'+uuid.uuid4().hex)
    try:
        with closing(sqlite3.connect(origem.as_uri()+'?mode=ro', uri=True, timeout=15)) as source:
            source.execute('PRAGMA query_only=ON')
            with closing(sqlite3.connect(temporario, timeout=15)) as target:
                source.backup(target)
                target.commit()
                if target.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                    raise sqlite3.DatabaseError('O backup não passou na verificação de integridade.')
        temporario.replace(destino)
        return destino
    except Exception:
        temporario.unlink(missing_ok=True)
        raise
