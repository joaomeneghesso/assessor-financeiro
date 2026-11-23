"""Isolamento obrigatório de qualquer execução da suíte ``tests``.

Este arquivo roda no import do pacote ``tests``, ou seja, antes de qualquer
módulo de teste, em todos os caminhos aceitos:

- gate oficial (``validacao/validar_versao_oficial.py``);
- ``python -m unittest discover -s tests -t .``;
- ``python -m unittest tests.test_<modulo>``.

Garantias (as mesmas do HARNESS do gate, agora também fora dele):

1. ``.env`` real não é carregado e variáveis TELEGRAM*/ASSESSOR*/OPENAI*/OLLAMA*
   do ambiente do desenvolvedor são descartadas.
2. ``database.DB_PATH`` aponta para um banco temporário já com ``init_db``;
   backups, exports e dashboards de serviços vão para a pasta temporária.
3. Qualquer ``sqlite3.connect`` que aponte para o banco oficial
   (``<projeto>/data/financeiro.db`` ou ``ASSESSOR_TEST_FORBIDDEN_DB``) levanta
   ``RuntimeError``: o teste falha em vez de ler ou gravar dados reais.
4. ``.runtime`` (sessões e callbacks do Telegram) é redirecionado para a pasta
   temporária: o import de ``app``/``telegram_experiencia`` não lê nem
   sobrescreve o estado real do bot.

Observação: ``discover -s tests`` SEM ``-t .`` importa os módulos como
top-level e não passa por aqui; use sempre ``-t .`` (ou o gate).
"""
import atexit
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

PROJETO = Path(__file__).resolve().parents[1]
_PREFIXOS_DESCARTADOS = ("TELEGRAM", "ASSESSOR", "OPENAI", "OLLAMA")
_PRESERVAR = {"ASSESSOR_TEST_FORBIDDEN_DB"}


def _limpar_ambiente():
    for nome in list(os.environ):
        if nome.upper().startswith(_PREFIXOS_DESCARTADOS) and nome.upper() not in _PRESERVAR:
            del os.environ[nome]
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    os.environ.setdefault("MPLBACKEND", "Agg")
    try:
        import dotenv
        import dotenv.main
    except ImportError:  # pragma: no cover - dependência do projeto
        return
    sem_env = lambda *args, **kwargs: False  # noqa: E731
    dotenv.load_dotenv = sem_env
    dotenv.main.load_dotenv = sem_env


def _chave(caminho):
    """Forma canônica barata (sem syscall) para comparar caminhos."""
    return os.path.normcase(os.path.abspath(os.fspath(caminho)))


_PROIBIDOS_CACHE = {}


def bancos_proibidos():
    """Chaves canônicas do banco oficial (e de ASSESSOR_TEST_FORBIDDEN_DB)."""
    extra = os.environ.get("ASSESSOR_TEST_FORBIDDEN_DB") or ""
    if extra not in _PROIBIDOS_CACHE:
        alvos = [PROJETO / "data" / "financeiro.db"] + ([Path(extra)] if extra else [])
        chaves = set()
        for alvo in alvos:
            chaves.add(_chave(alvo))
            chaves.add(_chave(alvo.resolve()))
        _PROIBIDOS_CACHE[extra] = frozenset(chaves)
    return _PROIBIDOS_CACHE[extra]


def _caminho_do_alvo(alvo):
    if isinstance(alvo, bytes):
        alvo = alvo.decode("utf-8", "replace")
    if isinstance(alvo, os.PathLike):
        alvo = os.fspath(alvo)
    if not isinstance(alvo, str) or alvo in ("", ":memory:"):
        return None
    if alvo.startswith("file:"):
        parsed = urlparse(alvo)
        caminho = unquote(parsed.path or "")
        if os.name == "nt" and caminho.startswith("/") and len(caminho) > 2 and caminho[2] == ":":
            caminho = caminho[1:]
        if not caminho or caminho == ":memory:":
            return None
        alvo = caminho
    try:
        return _chave(alvo)
    except (OSError, ValueError):
        return None


class BancoOficialEmTeste(RuntimeError):
    """Um teste tentou abrir o banco oficial."""


def _instalar_guarda_sqlite():
    original = sqlite3.connect
    if getattr(original, "_guarda_testes_assessor", False):
        return

    def connect_protegido(database, *args, **kwargs):
        caminho = _caminho_do_alvo(database)
        if caminho is not None and caminho in bancos_proibidos():
            raise BancoOficialEmTeste("Teste tentou acessar o banco oficial: " + str(caminho))
        return original(database, *args, **kwargs)

    connect_protegido._guarda_testes_assessor = True
    connect_protegido._original = original
    sqlite3.connect = connect_protegido


def _redirecionar_runtime(temp):
    import estado_runtime

    oficial = (PROJETO / ".runtime").resolve()
    destino = temp / ".runtime"

    def remapear(path):
        path = Path(path)
        try:
            relativo = path.resolve().relative_to(oficial)
        except ValueError:
            return path
        return destino / relativo

    base = estado_runtime.ProtectedJsonStore
    if not getattr(base, "_runtime_de_teste", False):
        class ProtectedJsonStoreDeTeste(base):
            _runtime_de_teste = True

            def __init__(self, path, *args, **kwargs):
                super().__init__(remapear(path), *args, **kwargs)

        ProtectedJsonStoreDeTeste.__name__ = base.__name__
        ProtectedJsonStoreDeTeste.__qualname__ = base.__qualname__
        estado_runtime.ProtectedJsonStore = ProtectedJsonStoreDeTeste

    # Se algum módulo já foi importado antes do pacote (ex.: pelo harness do
    # gate), corrige as instâncias já criadas.
    ux = sys.modules.get("telegram_experiencia")
    store = getattr(getattr(ux, "EXPERIENCE", None), "state_store", None)
    if store is not None:
        store.path = remapear(store.path)
    app = sys.modules.get("app")
    store = getattr(app, "_CALLBACK_STORE", None)
    if store is not None:
        store.path = remapear(store.path)


def _isolar_banco(temp):
    import database as db
    import services as svc

    if _chave(db.DB_PATH) in bancos_proibidos():
        db.DB_PATH = temp / "fixture.db"
        db.init_db()
    svc.DB_PATH = db.DB_PATH
    svc.BACKUPS_DIR = temp / "backups"
    svc.EXPORTS_DIR = temp / "exports"
    svc.DASHBOARDS_DIR = temp / "dashboards"


def _instalar():
    if getattr(sys, "_assessor_tests_isolados", None):
        return sys._assessor_tests_isolados
    temp = Path(tempfile.mkdtemp(prefix="assessor_tests_"))
    atexit.register(shutil.rmtree, temp, True)
    _limpar_ambiente()
    _instalar_guarda_sqlite()
    _redirecionar_runtime(temp)
    _isolar_banco(temp)
    sys._assessor_tests_isolados = temp
    return temp


PASTA_TEMPORARIA = _instalar()
