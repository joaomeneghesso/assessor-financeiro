import unittest
from types import SimpleNamespace
from unittest import mock
from unittest.mock import AsyncMock

import app
import security
import telegram_experiencia as ux


def _hash():
    return security.hash_secret('123456', iterations=1000, salt=b'0123456789abcdef')


def _msg_update(texto, user_id=1, chat_id=1):
    msg = SimpleNamespace(text=texto, message_id=7, reply_text=AsyncMock())
    return SimpleNamespace(
        message=msg, callback_query=None,
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=chat_id),
    )


class QuickAccessPolicyTests(unittest.IsolatedAsyncioTestCase):
    acao_exige_pin = staticmethod(app.acao_exige_pin)

    def setUp(self):
        patches = [
            mock.patch.object(app, 'ASSESSOR_PIN_HASH', _hash()),
            mock.patch.object(app, 'ASSESSOR_PIN', ''),
            mock.patch.object(app, 'ASSESSOR_PIN_LENGTH', '6'),
            mock.patch.object(app, 'registrar_auditoria', mock.Mock()),
            mock.patch.dict(app.ACAO_PENDENTE_PIN, {}, clear=True),
            mock.patch.dict(app.PENDENCIAS_EXCLUSAO, {}, clear=True),
            mock.patch.dict(app.SESSOES_SEGURANCA, {}, clear=True),
            mock.patch.object(app, 'bloquear_se_nao_autorizado', AsyncMock(return_value=False)),
            mock.patch.object(app, 'registrar_mensagem_update', mock.Mock()),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(app.EXCLUSAO_EXPIRADAS.clear)
        app.bloquear_assessor(1)

    def test_daily_actions_do_not_require_pin(self):
        daily = [
            'saldo geral', 'gastei 35 almoço credito itau', 'recebi 100 pix itau',
            'historico', 'quanto vou pagar no itau em 2026-09',
            'paguei B1 2026-09', 'corrigir valor 7 para 42,90', 'apagar 7',
            'exportar csv 2026-09',
        ]
        for command in daily:
            with self.subTest(command=command):
                self.assertFalse(self.acao_exige_pin(command))

    def test_sensitive_actions_require_pin(self):
        sensitive = [
            'backup', 'gerar backup', 'exportar csv tudo', 'exportar tudo',
            'confirmar importacao', 'confirmar importação',
            'apagar 10-18', 'excluir 10-18',
            'status', '/status', 'saude do assessor', 'saúde do assessor',
        ]
        for command in sensitive:
            with self.subTest(command=command):
                self.assertTrue(self.acao_exige_pin(command))

    async def test_blocker_classifies_before_keypad(self):
        with mock.patch.object(app, 'enviar_teclado_pin', AsyncMock()) as teclado:
            self.assertFalse(await app.bloquear_se_assessor_travado(_msg_update('saldo geral'), 'saldo geral'))
            teclado.assert_not_awaited()
            self.assertTrue(await app.bloquear_se_assessor_travado(_msg_update('backup'), 'backup'))
            teclado.assert_awaited_once()

    async def test_blanket_pin_gate_removed_from_message_flow(self):
        """Com o PIN configurado e o assessor travado, texto diario nao pede o teclado de PIN."""
        update = _msg_update('saldo geral')
        with mock.patch.object(app, 'enviar_teclado_pin', AsyncMock()) as teclado, \
                mock.patch.object(app.ux, 'dispatch_text', AsyncMock(return_value=True)) as dispatch:
            await app.receber_mensagem(update, SimpleNamespace())
        dispatch.assert_awaited_once()
        teclado.assert_not_awaited()

    async def test_sensitive_text_is_gated_in_message_flow(self):
        update = _msg_update('backup')
        with mock.patch.object(app, 'enviar_teclado_pin', AsyncMock()) as teclado, \
                mock.patch.object(app.ux, 'dispatch_text', AsyncMock(return_value=False)), \
                mock.patch.object(app, 'executar_core', AsyncMock()) as core:
            await app.receber_mensagem(update, SimpleNamespace())
        teclado.assert_awaited_once()
        core.assert_not_awaited()

    async def test_bulk_delete_is_gated_before_confirmation(self):
        update = _msg_update('apagar 10-18')
        with mock.patch.object(app, 'enviar_teclado_pin', AsyncMock()) as teclado, \
                mock.patch.object(app.ux, 'dispatch_text', AsyncMock(return_value=False)), \
                mock.patch.object(app, 'solicitar_confirmacao_exclusao', AsyncMock(return_value=True)) as confirmar:
            await app.receber_mensagem(update, SimpleNamespace())
            teclado.assert_awaited_once()
            confirmar.assert_not_awaited()
            # Destravado, a mesma exclusao segue para a confirmacao (nao e bloqueada para sempre).
            app.desbloquear_assessor(1)
            await app.receber_mensagem(update, SimpleNamespace())
            confirmar.assert_awaited_once()

    async def test_ux_callbacks_classify_legacy_command_for_sensitive_pin(self):
        exp = ux.Experience()
        update = SimpleNamespace(
            message=None, effective_user=SimpleNamespace(id=1), effective_chat=SimpleNamespace(id=1),
            callback_query=SimpleNamespace(data='ux:tok', answer=AsyncMock(),
                                           message=SimpleNamespace(reply_text=AsyncMock(), chat_id=1)),
        )
        key = ux.session_key(update)
        exp.session(key).tokens['ux:tok'] = ('legacy', 'backup')
        host = SimpleNamespace(bloquear_se_assessor_travado=AsyncMock(return_value=True))
        with mock.patch.object(ux, 'EXPERIENCE', exp):
            self.assertTrue(await ux.dispatch_callback(update, SimpleNamespace(), host))
        host.bloquear_se_assessor_travado.assert_awaited_once_with(update, 'backup')
        # Acao de navegacao comum nao carrega comando sensivel.
        exp.session(key).tokens['ux:tok'] = ('view', 'pay')
        host.bloquear_se_assessor_travado.reset_mock()
        with mock.patch.object(ux, 'EXPERIENCE', exp):
            await ux.dispatch_callback(update, SimpleNamespace(), host)
        host.bloquear_se_assessor_travado.assert_awaited_once_with(update, '')

    def test_version_is_402(self):
        from version import VERSION
        self.assertEqual('4.2.0', VERSION)
        self.assertEqual(VERSION, ux.VERSION)


if __name__ == '__main__':
    unittest.main()
