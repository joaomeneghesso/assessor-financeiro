"""Operação do bot: trava de instância única, tratador global de erro e tarefas monitoradas."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

MENSAGEM_ERRO_GENERICA = (
    "⚠️ Não consegui concluir esta ação agora. Nada foi alterado por esta mensagem de erro. "
    "Confira o Histórico antes de repetir e use /menu para continuar."
)

_OFFSET_TRAVA = 1_000_000

_log_erros =logging.getLogger("assessor.erros")
_log_rotinas = logging.getLogger("assessor.rotinas")


class InstanciaJaEmExecucao(RuntimeError):
    """Outra instância do assessor já segura a trava."""


def _travar(handle) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(_OFFSET_TRAVA)  # byte distante: não bloqueia a leitura do PID
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _destravar(handle) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(_OFFSET_TRAVA)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _ler_pid(caminho: Path) -> str:
    try:
        texto = caminho.read_text(encoding="utf-8", errors="ignore")
        return texto.split()[0] if texto.split() else "desconhecido"
    except Exception:
        return "desconhecido"


class TravaInstancia:
    def __init__(self, caminho: Path, handle):
        self.caminho = Path(caminho)
        self._handle = handle

    def liberar(self) -> None:
        handle, self._handle = self._handle, None
        if handle is None:
            return
        try:
            _destravar(handle)
        except Exception:
            pass
        try:
            handle.close()
        except Exception:
            pass

    def __enter__(self) -> "TravaInstancia":
        return self

    def __exit__(self, *exc) -> None:
        self.liberar()


def adquirir_trava_instancia(caminho: Path) -> TravaInstancia:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    handle = open(caminho, "a+b")
    try:
        _travar(handle)
    except OSError:
        handle.close()
        pid = _ler_pid(caminho)
        raise InstanciaJaEmExecucao(
            f"O assessor já está rodando (PID {pid}). "
            "Feche a outra janela antes de iniciar de novo."
        ) from None
    try:
        handle.seek(0)
        handle.truncate()
        handle.write(f"{os.getpid()} {datetime.now().isoformat(timespec='seconds')}\n".encode("utf-8"))
        handle.flush()
    except Exception:
        _log_rotinas.warning("Não foi possível gravar o PID na trava.", exc_info=True)
    return TravaInstancia(caminho, handle)


async def aviso_padrao(update, texto: str) -> None:
    await update.effective_chat.send_message(texto)


def criar_tratador_erro(enviar_aviso=aviso_padrao):
    from telegram.error import NetworkError, TimedOut

    async def tratador(update, context) -> None:
        erro = getattr(context, "error", None)
        update_id = getattr(update, "update_id", None)
        if isinstance(erro, (NetworkError, TimedOut)):
            _log_erros.warning("Falha transitória de rede (update_id=%s): %s", update_id, type(erro).__name__)
            return
        _log_erros.error("Erro não tratado (update_id=%s).", update_id, exc_info=erro)
        if update is not None and getattr(update, "effective_chat", None) is not None:
            try:
                await enviar_aviso(update, MENSAGEM_ERRO_GENERICA)
            except Exception:
                _log_erros.warning("Não foi possível avisar o titular sobre o erro.", exc_info=True)

    return tratador


def criar_tarefa_monitorada(coro, nome: str, registro: set) -> asyncio.Task:
    tarefa = asyncio.create_task(coro, name=nome)
    registro.add(tarefa)

    def _concluida(t: asyncio.Task) -> None:
        registro.discard(t)
        if t.cancelled():
            return
        exc = t.exception()
        if exc is not None:
            _log_rotinas.error("Rotina de fundo '%s' falhou.", nome, exc_info=exc)

    tarefa.add_done_callback(_concluida)
    return tarefa
