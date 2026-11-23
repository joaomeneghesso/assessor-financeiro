"""Data fixa para testes que dependem de "hoje".

Uso típico::

    from tests.relogio_fixo import data_fixa, HOJE_PADRAO

    def setUp(self):
        self.enterContext(data_fixa(HOJE_PADRAO))

Por baixo usa ``validacao/relogio_falso.py`` (o mesmo relógio do modo
``--data`` do gate): ``date.today()``/``datetime.now()``/``time.time()`` de todos
os módulos do projeto passam a partir da data pedida, e tudo volta ao normal
na saída do contexto (inclusive dentro de uma suíte já com data falsa).
"""
import importlib.util
import sys
from datetime import date
from pathlib import Path

_ARQUIVO = Path(__file__).resolve().parents[1] / "validacao" / "relogio_falso.py"


def _carregar():
    modulo = sys.modules.get("relogio_falso")
    if modulo is not None:
        return modulo
    spec = importlib.util.spec_from_file_location("relogio_falso", _ARQUIVO)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["relogio_falso"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


relogio = _carregar()

# Dia comum, longe do corte da fatura (25), de virada de mês e de ano.
HOJE_PADRAO = date(2026, 11, 9)


def data_fixa(data=HOJE_PADRAO, hora="10:00"):
    """Context manager que fixa "hoje" (o relógio anda a partir de ``data hora``)."""
    return relogio.fixar(data, hora)
