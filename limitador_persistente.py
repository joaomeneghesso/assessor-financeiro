"""Limitador de tentativas de PIN que sobrevive a reinícios do bot."""
from __future__ import annotations

import logging
from datetime import datetime

import security

_log = logging.getLogger("assessor.limitador")


class LimitadorPersistente(security.AuthAttemptLimiter):
    def __init__(self, max_attempts: int, lock_minutes: int, store):
        super().__init__(max_attempts, lock_minutes)
        self._store = store
        self._restaurar()

    def _restaurar(self) -> None:
        try:
            dados = self._store.load({})
            estados = dados.get("states") if isinstance(dados, dict) else None
            if not isinstance(estados, dict):
                return
            agora = datetime.now()
            for chave, item in estados.items():
                try:
                    if not isinstance(chave, str) or not isinstance(item, dict):
                        continue
                    falhas = item.get("failures")
                    if isinstance(falhas, bool) or not isinstance(falhas, int) or falhas < 0:
                        continue
                    bruto = item.get("locked_until")
                    ate = None
                    if bruto is not None:
                        ate = datetime.fromisoformat(bruto)
                        if ate.tzinfo is not None:
                            continue
                        if ate <= agora:
                            continue
                    elif falhas == 0:
                        continue
                    self._states[chave] = security.AttemptState(
                        failures=falhas, locked_until=ate, locked_until_mono=None
                    )
                except Exception:
                    continue
        except Exception:
            _log.warning("Não foi possível restaurar o limitador de PIN.", exc_info=True)

    def _salvar(self) -> None:
        try:
            with self._lock:
                estados = {
                    chave: {
                        "failures": s.failures,
                        "locked_until": s.locked_until.isoformat() if s.locked_until else None,
                    }
                    for chave, s in self._states.items()
                }
            self._store.save({"version": 1, "states": estados})
        except Exception:
            _log.warning("Não foi possível salvar o limitador de PIN.", exc_info=True)

    def register_failure(self, user_id, chat_id=None, purpose: str = "pin", now=None):
        resultado = super().register_failure(user_id, chat_id, purpose, now)
        self._salvar()
        return resultado

    def register_success(self, user_id, chat_id=None, purpose: str = "pin"):
        super().register_success(user_id, chat_id, purpose)
        self._salvar()

    def clear(self):
        super().clear()
        self._salvar()
