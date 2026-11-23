"""Cache efêmero compartilhado por uma única consulta/renderização.

O conteúdo vive em um ``ContextVar`` e é descartado ao fim do contexto. Assim,
nenhuma leitura é reaproveitada entre ações do usuário ou depois de uma escrita.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from datetime import date, datetime, time
from decimal import Decimal
import sqlite3


CONTEXTO_CONSULTA = ContextVar("assessor_contexto_consulta", default=None)


@contextmanager
def contexto_consulta():
    atual = CONTEXTO_CONSULTA.get()
    if atual is not None:
        yield atual
        return
    cache = {}
    token = CONTEXTO_CONSULTA.set(cache)
    try:
        yield cache
    finally:
        CONTEXTO_CONSULTA.reset(token)


def cache_atual():
    return CONTEXTO_CONSULTA.get()


# Tipos exatos que dispensam cópia e chamada recursiva (atalho de desempenho;
# subclasses seguem pelo caminho geral, com o mesmo resultado).
_ESCALARES_SIMPLES = frozenset({str, int, float, bool, bytes, type(None)})


def copia_defensiva(valor):
    """Copia estruturas de leitura, normalizando ``sqlite3.Row`` para dict."""
    if type(valor) in _ESCALARES_SIMPLES:
        return valor
    if valor is None or isinstance(valor, (str, int, float, bool, bytes)):
        return valor
    if isinstance(valor, sqlite3.Row):
        return {chave: copia_defensiva(valor[chave]) for chave in valor.keys()}
    if isinstance(valor, dict):
        simples = _ESCALARES_SIMPLES
        return {(chave if type(chave) in simples else copia_defensiva(chave)):
                (item if type(item) in simples else copia_defensiva(item))
                for chave, item in valor.items()}
    if isinstance(valor, list):
        simples = _ESCALARES_SIMPLES
        return [item if type(item) in simples else copia_defensiva(item) for item in valor]
    if isinstance(valor, tuple):
        return tuple(copia_defensiva(item) for item in valor)
    if isinstance(valor, set):
        return {copia_defensiva(item) for item in valor}
    return deepcopy(valor)


_IMUTAVEIS = (str, int, float, bool, bytes, type(None), Decimal, date, datetime, time)
_IMUTAVEIS_EXATOS = frozenset(_IMUTAVEIS)


def copia_rapida(valor, _memo=None):
    """Equivale a ``deepcopy`` para estruturas de leitura (dict/list/tuple/set).

    Escalares imutáveis são reaproveitados; contêineres são recriados e a
    identidade compartilhada dentro de um mesmo valor é preservada (como no
    deepcopy). Qualquer outro tipo cai no ``deepcopy`` original.
    """
    if type(valor) in _IMUTAVEIS_EXATOS or isinstance(valor, _IMUTAVEIS):
        return valor
    if _memo is None:
        _memo = {}
    chave = id(valor)
    if chave in _memo:
        return _memo[chave]
    tipo = type(valor)
    imutaveis = _IMUTAVEIS_EXATOS
    if tipo is dict:
        novo = {}
        _memo[chave] = novo
        for k, v in valor.items():
            if type(k) not in imutaveis:
                k = copia_rapida(k, _memo)
            novo[k] = v if type(v) in imutaveis else copia_rapida(v, _memo)
        return novo
    if tipo is list:
        novo = []
        _memo[chave] = novo
        novo.extend(v if type(v) in imutaveis else copia_rapida(v, _memo) for v in valor)
        return novo
    if tipo is tuple:
        novo = tuple(copia_rapida(v, _memo) for v in valor)
        _memo[chave] = novo
        return novo
    if tipo is set:
        novo = {copia_rapida(v, _memo) for v in valor}
        _memo[chave] = novo
        return novo
    return deepcopy(valor)


# Escopo de leitura: um cálculo feito sob outro "ponto de vista" (hoje, o corte
# de conciliação de ``conciliacao.referencia``) não pode reaproveitar nem
# alimentar as entradas calculadas fora dele. Antes, a chave do cache ignorava
# esse corte e o resultado de uma tela dependia da ordem das chamadas.
_ESCOPO = ContextVar("assessor_consulta_escopo", default=None)


@contextmanager
def escopo(valor):
    token = _ESCOPO.set(valor)
    try:
        yield
    finally:
        _ESCOPO.reset(token)


def chave_no_escopo(chave):
    atual = _ESCOPO.get()
    return chave if atual is None else ("escopo", atual, chave)


def obter_ou_calcular(chave, calcular):
    """Obtém uma leitura do cache e sempre devolve uma cópia defensiva."""
    cache = cache_atual()
    if cache is None:
        return calcular()
    chave = chave_no_escopo(chave)
    if chave not in cache:
        cache[chave] = copia_defensiva(calcular())
    return copia_rapida(cache[chave])


def namespace(nome):
    """Retorna um espaço mutável privado para memos internos de um algoritmo."""
    cache = cache_atual()
    if cache is None:
        return None
    return cache.setdefault(chave_no_escopo(("namespace", nome)), {})
