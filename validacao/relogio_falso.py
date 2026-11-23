"""Relógio falso por deslocamento, só para testes (nunca importado pela produção).

O relógio não para: ele anda a partir do instante-alvo. Substitui
``datetime.date``/``datetime.datetime`` (``today``/``now``/``utcnow``) e as
funções de ``time`` que leem a hora de parede (``time``, ``time_ns``,
``localtime``, ``gmtime``, ``ctime``, ``strftime`` sem tupla). ``monotonic`` e
``perf_counter`` ficam reais (medem duração, não data).

Usos:

- gate: ``validar_versao_oficial.py --data AAAA-MM-DD`` chama ``ativar`` antes
  de importar qualquer módulo do projeto, para a suíte inteira;
- testes: ``tests/relogio_fixo.py`` (``data_fixa``) ativa por teste e restaura.

As ativações empilham: um teste com data fixa dentro de uma suíte com data
falsa volta à data da suíte quando termina.

Limitações conhecidas: ``st_mtime`` de arquivos continua real, assim como
``date.fromtimestamp``/``datetime.fromtimestamp`` (não deslocados, para não
deslocar duas vezes um ``time.time()`` já falso).
"""
import datetime as _dm
import os
import sqlite3
import sys
import time as _tm
from pathlib import Path

_NOME = "relogio_falso"
if __name__ != _NOME:  # carregado por caminho: reaproveita a instância única
    sys.modules.setdefault(_NOME, sys.modules[__name__])

DataReal = getattr(_dm.date, "_classe_real", _dm.date)
DataHoraReal = getattr(_dm.datetime, "_classe_real", _dm.datetime)
_REAIS_TIME = {nome: getattr(_tm, nome) for nome in ("time", "time_ns", "localtime", "gmtime", "ctime", "strftime")}
_RAIZ = Path(__file__).resolve().parents[1]

_pilha = []          # deslocamentos (segundos) ativos; o último vale
_trocados = []       # (modulo, atributo, valor_original) para restaurar


def _delta():
    return _pilha[-1] if _pilha else 0.0


def _agora():
    return _REAIS_TIME["time"]() + _delta()


class _MetaData(type):
    def __instancecheck__(cls, obj):
        return isinstance(obj, DataReal)

    def __subclasscheck__(cls, sub):
        return issubclass(sub, DataReal)


class _MetaDataHora(type):
    def __instancecheck__(cls, obj):
        return isinstance(obj, DataHoraReal)

    def __subclasscheck__(cls, sub):
        return issubclass(sub, DataHoraReal)


class DataFalsa(DataReal, metaclass=_MetaData):
    _classe_real = DataReal

    @classmethod
    def today(cls):
        return DataReal.fromtimestamp(_agora())


class DataHoraFalsa(DataHoraReal, metaclass=_MetaDataHora):
    _classe_real = DataHoraReal

    @classmethod
    def now(cls, tz=None):
        return DataHoraReal.fromtimestamp(_agora(), tz) if tz is not None else DataHoraReal.fromtimestamp(_agora())

    @classmethod
    def utcnow(cls):
        return DataHoraReal.fromtimestamp(_agora(), _dm.timezone.utc).replace(tzinfo=None)

    @classmethod
    def today(cls):
        return cls.now()


class _ChamavelComTempo:
    """Objeto chamável (não função): não vira método ao ser atribuído a atributo
    de classe (ex.: ``logging.Formatter.converter = time.localtime``)."""

    def __init__(self, funcao):
        self.funcao = funcao

    def __call__(self, segundos=None):
        return self.funcao(_agora() if segundos is None else segundos)


def _strftime(formato, tupla=None):
    return _REAIS_TIME["strftime"](formato, _REAIS_TIME["localtime"](_agora()) if tupla is None else tupla)


_FALSOS_TIME = {
    "time": lambda: _agora(),
    "time_ns": lambda: _REAIS_TIME["time_ns"]() + int(_delta() * 1e9),
    "localtime": _ChamavelComTempo(_REAIS_TIME["localtime"]),
    "gmtime": _ChamavelComTempo(_REAIS_TIME["gmtime"]),
    "ctime": _ChamavelComTempo(_REAIS_TIME["ctime"]),
    "strftime": _strftime,
}
_SUBSTITUTOS = {id(DataReal): DataFalsa, id(DataHoraReal): DataHoraFalsa}


def _modulo_do_projeto(mod):
    arquivo = getattr(mod, "__file__", None)
    if not arquivo:
        return False
    try:
        caminho = Path(arquivo).resolve()
        caminho.relative_to(_RAIZ)
    except (ValueError, OSError):
        return False
    partes = {p.lower() for p in caminho.parts}
    return not ({".venv", "site-packages", "venv"} & partes)


def _trocar(alvo, nome, novo):
    _trocados.append((alvo, nome, getattr(alvo, nome)))
    setattr(alvo, nome, novo)


def _instalar():
    _trocar(_dm, "date", DataFalsa)
    _trocar(_dm, "datetime", DataHoraFalsa)
    for nome, falso in _FALSOS_TIME.items():
        _trocar(_tm, nome, falso)
    for mod in list(sys.modules.values()):
        if mod is None or not _modulo_do_projeto(mod) or mod is sys.modules.get(_NOME):
            continue
        for nome, valor in list(vars(mod).items()):
            novo = _SUBSTITUTOS.get(id(valor))
            if novo is not None:
                _trocar(mod, nome, novo)
            elif nome in _REAIS_TIME and valor is _REAIS_TIME[nome] and mod is not _tm:  # from time import time
                _trocar(mod, nome, _FALSOS_TIME[nome])
    sqlite3.register_adapter(DataFalsa, lambda d: d.isoformat())
    sqlite3.register_adapter(DataHoraFalsa, lambda d: d.isoformat(" "))


def _desinstalar():
    while _trocados:
        alvo, nome, original = _trocados.pop()
        setattr(alvo, nome, original)
    # módulos importados com o relógio ativo ficaram com as classes falsas
    for mod in list(sys.modules.values()):
        if mod is None or not _modulo_do_projeto(mod):
            continue
        for nome, valor in list(vars(mod).items()):
            if valor is DataFalsa:
                setattr(mod, nome, DataReal)
            elif valor is DataHoraFalsa:
                setattr(mod, nome, DataHoraReal)


def interpretar(data, hora="10:00"):
    """'AAAA-MM-DD' (+ 'HH:MM') -> datetime ingênuo local."""
    ano, mes, dia = map(int, str(data).split("-"))
    hh, mm = map(int, str(hora or "10:00").split(":"))
    return DataHoraReal(ano, mes, dia, hh, mm)


def ativar(data, hora="10:00"):
    """Empilha um relógio que começa em ``data hora`` (hora local do processo)."""
    alvo = data if isinstance(data, DataHoraReal) else (
        DataHoraReal(data.year, data.month, data.day, *map(int, (hora or "10:00").split(":")))
        if isinstance(data, DataReal) else interpretar(data, hora))
    if not _pilha:
        _instalar()
    _pilha.append(alvo.timestamp() - _REAIS_TIME["time"]())


def desativar():
    if not _pilha:
        return
    _pilha.pop()
    if not _pilha:
        _desinstalar()


def ativo():
    return bool(_pilha)


class fixar:
    """Context manager: ``with fixar('2026-11-09'): ...`` (ou ``date``/``datetime``)."""

    def __init__(self, data, hora="10:00"):
        self.data, self.hora = data, hora

    def __enter__(self):
        ativar(self.data, self.hora)
        return self

    def __exit__(self, *exc):
        desativar()
        return False


def ativar_pelo_ambiente():
    """Usado pelo HARNESS do gate: GATE_DATA_FALSA=AAAA-MM-DD, GATE_HORA_FALSA=HH:MM."""
    data = os.environ.get("GATE_DATA_FALSA")
    if data:
        ativar(data, os.environ.get("GATE_HORA_FALSA") or "10:00")
    return data
