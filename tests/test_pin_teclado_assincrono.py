"""Teclado de PIN: verificação fora do loop, sem mudar o resultado nem a contagem.

Cobre os dois lados da mudança:
- comportamento preservado (PIN certo desbloqueia; PIN errado conta 1 falha;
  bloqueio após o limite; nada de veredito parcial);
- o loop do bot continua livre enquanto o PBKDF2 roda, e toques extras durante
  a verificação não contam a mesma tentativa duas vezes.
"""
import asyncio
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

import app
import security

PIN = "123456"


def _hash():
    return security.hash_secret(PIN, iterations=1000, salt=b"0123456789abcdef")


class _Query:
    def __init__(self, data):
        self.data = data
        self.edits = []
        self.message = SimpleNamespace(edit_text=self._edit)

    async def answer(self, *a, **k):
        return None

    async def _edit(self, text, **kwargs):
        self.edits.append(text)


def _update(data, user_id=1, chat_id=1):
    query = _Query(data)
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=chat_id),
    )
    return update, query


class PinTecladoAssincronoTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = 1
        patches = [
            mock.patch.object(app, "ASSESSOR_PIN_HASH", _hash()),
            mock.patch.object(app, "ASSESSOR_PIN", ""),
            mock.patch.object(app, "ASSESSOR_PIN_LENGTH", "6"),
            mock.patch.object(app, "AUTH_LIMITER", security.AuthAttemptLimiter(5, 15)),
            mock.patch.object(app, "registrar_auditoria", lambda *a, **k: None),
            mock.patch.object(app, "desbloquear_assessor", mock.Mock()),
            mock.patch.object(app, "menu_command", mock.AsyncMock()),
            mock.patch.dict(app.PIN_TECLADO, {}, clear=True),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        app.iniciar_teclado_pin(self.user)

    def _indice_do_digito(self, digito):
        pares = app.PIN_TECLADO[self.user]["pares"]
        return next(i for i, par in enumerate(pares) if digito in par)

    async def _tocar(self, digito):
        update, query = _update(f"pin_pair:{self._indice_do_digito(digito)}", self.user)
        await app.processar_callback_pin(update, None)
        return query

    async def _digitar(self, pin):
        query = None
        for d in pin:
            query = await self._tocar(d)
        return query

    async def test_pin_correto_desbloqueia_uma_vez(self):
        query = await self._digitar(PIN)
        app.desbloquear_assessor.assert_called_once_with(self.user)
        self.assertIn("desbloqueado", query.edits[-1])
        self.assertNotIn(self.user, app.PIN_TECLADO)
        self.assertEqual((False, 0), app.AUTH_LIMITER.status(self.user, self.user, "pin"))

    async def test_pin_errado_conta_exatamente_uma_falha_e_reinicia_escolhas(self):
        indice_6 = self._indice_do_digito("6")
        ultimo = next(d for d in "0123456789" if self._indice_do_digito(d) != indice_6)
        query = await self._digitar(PIN[:5] + ultimo)
        app.desbloquear_assessor.assert_not_called()
        self.assertIn("PIN incorreto", query.edits[-1])
        estado = app.PIN_TECLADO[self.user]
        self.assertEqual([], estado["escolhas"])
        self.assertFalse(estado.get("verificando"))
        failures = app.AUTH_LIMITER._states["pin:1:1"].failures
        self.assertEqual(1, failures)

    async def test_sem_veredito_parcial(self):
        query = await self._digitar(PIN[:5])
        app.desbloquear_assessor.assert_not_called()
        self.assertTrue(all("incorreto" not in e for e in query.edits))

    async def test_bloqueio_apos_limite_continua_funcionando(self):
        app.AUTH_LIMITER = security.AuthAttemptLimiter(2, 15)
        indice_6 = self._indice_do_digito("6")
        errado = next(d for d in "0123456789" if self._indice_do_digito(d) != indice_6)
        await self._digitar(PIN[:5] + errado)
        query = await self._digitar(PIN[:5] + errado)
        self.assertIn("bloqueado", query.edits[-1])
        # Mesmo com o PIN certo, segue bloqueado.
        update, query = _update("pin_pair:0", self.user)
        await app.processar_callback_pin(update, None)
        app.desbloquear_assessor.assert_not_called()

    async def test_verificacao_roda_fora_do_loop_e_nao_congela(self):
        loop_thread = threading.get_ident()
        liberar = threading.Event()
        chamadas = []
        original = app.verify_pin_pairs

        def lento(*args):
            chamadas.append(threading.get_ident())
            liberar.wait(5)
            return original(*args)

        with mock.patch.object(app, "verify_pin_pairs", lento):
            await self._digitar(PIN[:5])
            ultimo = asyncio.create_task(self._tocar(PIN[5]))
            # Enquanto a verificação está presa, o loop segue respondendo
            # e toques extras são ignorados (não geram segunda verificação).
            for _ in range(50):
                await asyncio.sleep(0.01)
                if chamadas:
                    break
            self.assertEqual(1, len(chamadas))
            self.assertTrue(app.PIN_TECLADO[self.user]["verificando"])
            extra = await self._tocar(PIN[0])
            self.assertEqual([], extra.edits)
            liberar.set()
            query = await ultimo
        self.assertEqual(1, len(chamadas))
        self.assertNotEqual(loop_thread, chamadas[0])
        self.assertIn("desbloqueado", query.edits[-1])
        app.desbloquear_assessor.assert_called_once()

    async def test_falha_na_verificacao_nao_deixa_teclado_travado(self):
        with mock.patch.object(app, "verify_pin_pairs", side_effect=RuntimeError("x")):
            await self._digitar(PIN[:5])
            with self.assertRaises(RuntimeError):
                await self._tocar(PIN[5])
        self.assertFalse(app.PIN_TECLADO[self.user].get("verificando"))


if __name__ == "__main__":
    unittest.main()
