"""P1 de app.py: reexecução após PIN, limitador no reset textual, validade de
pendências, botões vinculados à pendência e apagar `desbloquear <PIN>`."""
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest import mock
from unittest.mock import AsyncMock

import app
import security

PIN = "123456"


def _hash():
    return security.hash_secret(PIN, iterations=1000, salt=b"0123456789abcdef")


def _msg_update(texto, user_id=1, chat_id=1):
    msg = SimpleNamespace(text=texto, message_id=7, reply_text=AsyncMock())
    return SimpleNamespace(
        message=msg, callback_query=None,
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=chat_id),
    )


def _cb_update(chave, user_id=1, chat_id=1):
    query = SimpleNamespace(
        data=chave, answer=AsyncMock(),
        message=SimpleNamespace(reply_text=AsyncMock(), edit_text=AsyncMock(), chat_id=chat_id),
    )
    return SimpleNamespace(
        message=None, callback_query=query,
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=chat_id),
    ), query


class _Base(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patches = [
            mock.patch.object(app, "ASSESSOR_PIN_HASH", _hash()),
            mock.patch.object(app, "ASSESSOR_PIN", ""),
            mock.patch.object(app, "ASSESSOR_PIN_LENGTH", "6"),
            mock.patch.object(app, "AUTH_LIMITER", security.AuthAttemptLimiter(3, 15)),
            mock.patch.object(app, "registrar_auditoria", mock.Mock()),
            mock.patch.dict(app.PIN_TECLADO, {}, clear=True),
            mock.patch.dict(app.ACAO_PENDENTE_PIN, {}, clear=True),
            mock.patch.dict(app.PENDENCIAS_RESET_PIN, {}, clear=True),
            mock.patch.dict(app.PENDENCIAS_EXCLUSAO, {}, clear=True),
            mock.patch.dict(app.PENDENCIAS_APRENDIZADO_CATEGORIA, {}, clear=True),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(app.RESET_PIN_EXPIRADOS.clear)
        self.addCleanup(app.EXCLUSAO_EXPIRADAS.clear)
        app.bloquear_assessor(1)


class AcaoPendenteAposPinTests(_Base):
    async def _digitar(self, pin):
        for d in pin:
            pares = app.PIN_TECLADO[1]["pares"]
            indice = next(i for i, par in enumerate(pares) if d in par)
            update, _ = _cb_update(f"pin_pair:{indice}")
            await app.processar_callback_pin(update, None)

    async def test_acao_bloqueada_e_reexecutada_apos_pin_correto(self):
        original = _msg_update("backup")
        with mock.patch.object(app, "enviar_teclado_pin", AsyncMock()) as teclado:
            self.assertTrue(await app.bloquear_se_assessor_travado(original, "backup"))
        teclado.assert_awaited()
        app.iniciar_teclado_pin(1)
        with mock.patch.object(app, "receber_mensagem", AsyncMock()) as rm, \
                mock.patch.object(app, "menu_command", AsyncMock()) as menu:
            await self._digitar(PIN)
        rm.assert_awaited_once()
        self.assertIs(rm.await_args.args[0], original)
        menu.assert_not_awaited()
        self.assertNotIn(1, app.ACAO_PENDENTE_PIN)

    async def test_nao_reexecuta_apos_pin_errado(self):
        original = _msg_update("backup")
        with mock.patch.object(app, "enviar_teclado_pin", AsyncMock()):
            await app.bloquear_se_assessor_travado(original, "backup")
        # Pares fixos: com o sorteio aleatório, "654321" (o PIN ao contrário) seria aceito se os pares
        # 1-6, 2-5 e 3-4 saíssem juntos (1 chance em 315) e o teste ficaria intermitente.
        pares_fixos = [("1", "2"), ("3", "4"), ("5", "6"), ("7", "8"), ("9", "0")]
        with mock.patch.object(app, "gerar_pares_teclado_pin", return_value=pares_fixos):
            app.iniciar_teclado_pin(1)
        with mock.patch.object(app, "receber_mensagem", AsyncMock()) as rm, \
                mock.patch.object(app, "menu_command", AsyncMock()):
            await self._digitar("654321")
        rm.assert_not_awaited()
        self.assertIn(1, app.ACAO_PENDENTE_PIN)

    async def test_acao_pendente_expira(self):
        original = _msg_update("backup")
        with mock.patch.object(app, "enviar_teclado_pin", AsyncMock()):
            await app.bloquear_se_assessor_travado(original, "backup")
        app.ACAO_PENDENTE_PIN[1]["expira_mono"] = app._monotonic() - 1
        self.assertIsNone(app.retirar_acao_pendente_pin(1))

    async def test_pin_nao_e_guardado(self):
        original = _msg_update("backup")
        with mock.patch.object(app, "enviar_teclado_pin", AsyncMock()):
            await app.bloquear_se_assessor_travado(original, "backup")
        self.assertNotIn(PIN, repr(app.ACAO_PENDENTE_PIN))


class DesbloquearTextoTests(_Base):
    async def test_apaga_mensagem_do_pin_e_reexecuta(self):
        original = _msg_update("backup")
        with mock.patch.object(app, "enviar_teclado_pin", AsyncMock()):
            await app.bloquear_se_assessor_travado(original, "backup")
        update = _msg_update(f"desbloquear {PIN}")
        context = SimpleNamespace(bot=SimpleNamespace(delete_message=AsyncMock()))
        with mock.patch.object(app, "bloquear_se_nao_autorizado", AsyncMock(return_value=False)), \
                mock.patch.object(app, "enviar_resposta", AsyncMock()), \
                mock.patch.object(app, "desbloquear_assessor", mock.Mock()), \
                mock.patch.object(app, "registrar_mensagem_update", mock.Mock()), \
                mock.patch.object(app, "reexecutar_acao_pendente_pin", AsyncMock()) as rex:
            await app.receber_mensagem(update, context)
        context.bot.delete_message.assert_awaited_once()
        rex.assert_awaited_once()

    async def test_pin_errado_tambem_apaga_e_nao_reexecuta(self):
        update = _msg_update("desbloquear 000000")
        context = SimpleNamespace(bot=SimpleNamespace(delete_message=AsyncMock()))
        with mock.patch.object(app, "bloquear_se_nao_autorizado", AsyncMock(return_value=False)), \
                mock.patch.object(app, "enviar_resposta", AsyncMock()), \
                mock.patch.object(app, "registrar_mensagem_update", mock.Mock()), \
                mock.patch.object(app, "reexecutar_acao_pendente_pin", AsyncMock()) as rex:
            await app.receber_mensagem(update, context)
        context.bot.delete_message.assert_awaited_once()
        rex.assert_not_awaited()

    async def test_falha_ao_apagar_nao_quebra(self):
        update = _msg_update("desbloquear 000000")
        context = SimpleNamespace(bot=SimpleNamespace(delete_message=AsyncMock(side_effect=RuntimeError("sem permissao"))))
        with mock.patch.object(app, "bloquear_se_nao_autorizado", AsyncMock(return_value=False)), \
                mock.patch.object(app, "enviar_resposta", AsyncMock()), \
                mock.patch.object(app, "registrar_mensagem_update", mock.Mock()), \
                mock.patch.object(app, "reexecutar_acao_pendente_pin", AsyncMock()) as rex:
            await app.receber_mensagem(update, context)
        # A tentativa de apagar ocorreu, a falha foi absorvida e nada foi reexecutado.
        context.bot.delete_message.assert_awaited_once()
        rex.assert_not_awaited()


class ResetPinTextualTests(_Base):
    async def test_chave_errada_usa_limitador_e_audita(self):
        with mock.patch.object(app, "_recovery_armazenada", return_value=True), \
                mock.patch.object(app, "validar_chave_recuperacao", return_value=False), \
                mock.patch.object(app, "enviar_resposta", AsyncMock()) as env:
            ctx = SimpleNamespace(bot=SimpleNamespace(delete_message=AsyncMock()))
            for _ in range(3):
                await app.processar_reset_pin(_msg_update("reset errada 123456"), ctx, "reset errada 123456")
            locked, _ = app.AUTH_LIMITER.status(1, 1, "recovery")
            self.assertTrue(locked)
            with mock.patch.object(app, "validar_chave_recuperacao", return_value=True) as val:
                await app.processar_reset_pin(_msg_update("reset certa 123456"), ctx, "reset certa 123456")
                val.assert_not_called()
        self.assertIn("bloqueada", env.await_args.args[1])
        acoes = [c.args[2] for c in app.registrar_auditoria.call_args_list]
        self.assertEqual(3, acoes.count("recovery_falha"))

    async def test_sucesso_audita_e_mantem_mensagem(self):
        with mock.patch.object(app, "_recovery_armazenada", return_value=True), \
                mock.patch.object(app, "validar_chave_recuperacao", return_value=True), \
                mock.patch.object(app, "salvar_pin_protegido", mock.Mock()), \
                mock.patch.object(app, "enviar_teclado_pin", AsyncMock()), \
                mock.patch.object(app, "enviar_resposta", AsyncMock()) as env:
            ctx = SimpleNamespace(bot=SimpleNamespace(delete_message=AsyncMock()))
            await app.processar_reset_pin(_msg_update("reset k 123456"), ctx, "reset k 123456")
        self.assertIn("✅ PIN redefinido com sucesso", env.await_args_list[0].args[1])
        acoes = [c.args[2] for c in app.registrar_auditoria.call_args_list]
        self.assertIn("recovery_sucesso", acoes)


class ExpiracaoTests(_Base):
    def test_reset_pin_expira_em_5_minutos(self):
        app.definir_pendencia_reset_pin(1, "chave")
        self.assertIsNotNone(app.obter_pendencia_reset_pin(1))
        app.PENDENCIAS_RESET_PIN[1]["criado_em"] = datetime.now() - timedelta(minutes=6)
        self.assertIsNone(app.obter_pendencia_reset_pin(1))
        self.assertNotIn(1, app.PENDENCIAS_RESET_PIN)
        self.assertIn(1, app.RESET_PIN_EXPIRADOS)

    def test_exclusao_expira_em_10_minutos(self):
        app.definir_pendencia_exclusao(1, "apagar 1", "previa")
        self.assertIsNotNone(app.obter_pendencia_exclusao(1))
        app.PENDENCIAS_EXCLUSAO[1]["criado_em"] = datetime.now() - timedelta(minutes=11)
        self.assertIsNone(app.obter_pendencia_exclusao(1))
        self.assertIn(1, app.EXCLUSAO_EXPIRADAS)

    async def test_sim_tardio_nao_confirma_exclusao(self):
        app.definir_pendencia_exclusao(1, "apagar 1", "previa")
        app.PENDENCIAS_EXCLUSAO[1]["criado_em"] = datetime.now() - timedelta(minutes=11)
        update = _msg_update("sim")
        with mock.patch.object(app, "bloquear_se_nao_autorizado", AsyncMock(return_value=False)), \
                mock.patch.object(app, "registrar_mensagem_update", mock.Mock()), \
                mock.patch.object(app, "executar_confirmacao_exclusao", AsyncMock()) as exe, \
                mock.patch.object(app, "enviar_resposta", AsyncMock()) as env:
            await app.receber_mensagem(update, SimpleNamespace())
        exe.assert_not_awaited()
        self.assertIn("expirada", env.await_args.args[1])

    async def test_mensagem_apos_reset_expirado_nao_vira_chave(self):
        app.definir_pendencia_reset_pin(1, "chave")
        app.PENDENCIAS_RESET_PIN[1]["criado_em"] = datetime.now() - timedelta(minutes=6)
        update = _msg_update("minha-chave")
        ctx = SimpleNamespace(bot=SimpleNamespace(delete_message=AsyncMock()))
        with mock.patch.object(app, "bloquear_se_nao_autorizado", AsyncMock(return_value=False)), \
                mock.patch.object(app, "registrar_mensagem_update", mock.Mock()), \
                mock.patch.object(app, "processar_reset_pin_guiado", AsyncMock()) as guiado, \
                mock.patch.object(app, "enviar_resposta", AsyncMock()) as env:
            await app.receber_mensagem(update, ctx)
        guiado.assert_not_awaited()
        self.assertIn("expirada", env.await_args.args[1])


class BotaoVinculadoTests(_Base):
    def _chave(self, markup, indice=0):
        return markup.inline_keyboard[0][indice].callback_data

    async def _clicar(self, chave):
        update, query = _cb_update(chave)
        with mock.patch.object(app, "bloquear_se_nao_autorizado", AsyncMock(return_value=False)), \
                mock.patch.object(app.ux, "dispatch_callback", AsyncMock(return_value=False)), \
                mock.patch.object(app, "bloquear_se_assessor_travado", AsyncMock(return_value=False)), \
                mock.patch.object(app, "executar_confirmacao_exclusao", AsyncMock()) as exe:
            await app.callback_submenu(update, SimpleNamespace())
        return exe, query

    async def test_botao_antigo_de_exclusao_nao_confirma_pendencia_nova(self):
        app.definir_pendencia_exclusao(1, "apagar 1", "p1")
        antigo = self._chave(app.montar_botoes_confirmacao_exclusao(app.obter_pendencia_exclusao(1)["id"]))
        app.definir_pendencia_exclusao(1, "apagar 2", "p2")
        novo = self._chave(app.montar_botoes_confirmacao_exclusao(app.obter_pendencia_exclusao(1)["id"]))
        exe, query = await self._clicar(antigo)
        exe.assert_not_awaited()
        self.assertIn("antiga", query.message.reply_text.await_args.args[0])
        exe, _ = await self._clicar(novo)
        exe.assert_awaited_once()

    async def test_botao_antigo_de_aprendizado_nao_cria_regra(self):
        antes = {"id": 1, "descricao": "padaria x", "categoria": "Outros"}
        depois = {"id": 1, "descricao": "padaria x", "categoria": "Alimentação"}
        chaves = []
        for _ in range(2):
            upd = _msg_update("x")
            await app.oferecer_aprendizado_categoria(upd, antes, depois)
            markup = upd.message.reply_text.await_args.kwargs["reply_markup"]
            chaves.append(self._chave(markup))
        update, query = _cb_update(chaves[0])
        with mock.patch.object(app, "bloquear_se_nao_autorizado", AsyncMock(return_value=False)), \
                mock.patch.object(app.ux, "dispatch_callback", AsyncMock(return_value=False)), \
                mock.patch.object(app, "bloquear_se_assessor_travado", AsyncMock(return_value=False)), \
                mock.patch("categorias_pessoais.salvar_regra") as salvar:
            await app.callback_submenu(update, SimpleNamespace())
        salvar.assert_not_called()
        self.assertIn("antiga", query.message.reply_text.await_args.args[0])
        self.assertIn(1, app.PENDENCIAS_APRENDIZADO_CATEGORIA)


if __name__ == "__main__":
    unittest.main()
