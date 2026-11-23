"""Proteção para execução direta com pytest.

O caminho oficial continua sendo ``validacao/validar_versao_oficial.py``
(unittest, ignora este arquivo). Aqui só reproduzimos a mesma garantia do gate
para quem rodar ``pytest tests``: banco temporário e bloqueio do banco oficial.
"""
import tempfile
from pathlib import Path

import database as db
import services as svc

_OFICIAL = (Path(db.BASE_DIR) / "data" / "financeiro.db").resolve()
_TEMP = tempfile.TemporaryDirectory(prefix="assessor_pytest_")

_original_open_connection = db._open_connection


def _guarded_open_connection(read_only):
    if Path(db.DB_PATH).resolve() == _OFICIAL:
        raise RuntimeError("Teste tentou acessar o banco oficial: " + str(_OFICIAL))
    return _original_open_connection(read_only)


db._open_connection = _guarded_open_connection
db.DB_PATH = Path(_TEMP.name) / "fixture.db"
svc.DB_PATH = db.DB_PATH
# Backups criados por testes (ex.: antes de exclusões) não vão para a pasta real.
svc.BACKUPS_DIR = Path(_TEMP.name) / "backups"
db.init_db()
