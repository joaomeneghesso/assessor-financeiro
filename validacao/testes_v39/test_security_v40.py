import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import security


class SecretProtectionV40Tests(unittest.TestCase):
    def test_hash_roundtrip_and_wrong_secret(self):
        protected = security.hash_secret('123456', iterations=1000, salt=b'0123456789abcdef')
        self.assertTrue(security.is_hashed_secret(protected))
        self.assertTrue(security.verify_secret('123456', protected))
        self.assertFalse(security.verify_secret('123457', protected))
        self.assertNotIn('123456', protected)

    def test_legacy_plaintext_verification_is_compatible(self):
        self.assertTrue(security.verify_secret('123456', '123456'))
        self.assertFalse(security.verify_secret('123457', '123456'))

    def test_pair_keyboard_validates_hash_without_plain_pin(self):
        protected = security.hash_secret('123456', iterations=1000, salt=b'fedcba9876543210')
        choices = [('7','1'), ('8','2'), ('9','3'), ('0','4'), ('7','5'), ('8','6')]
        self.assertTrue(security.verify_pin_pairs(choices, protected, 6))
        choices[-1] = ('7','8')
        self.assertFalse(security.verify_pin_pairs(choices, protected, 6))

    def test_private_chat_is_fail_closed(self):
        update = SimpleNamespace(effective_chat=SimpleNamespace(type='private', id=123))
        self.assertFalse(security.chat_is_allowed(update))
        self.assertTrue(security.chat_is_allowed(update, allowed_chat_id=123))
        self.assertFalse(security.chat_is_allowed(update, allowed_chat_id=456))

    def test_group_requires_opt_in_and_exact_chat(self):
        update = SimpleNamespace(effective_chat=SimpleNamespace(type='supergroup', id=-1001))
        self.assertFalse(security.chat_is_allowed(update, allowed_chat_id=-1001))
        self.assertTrue(security.chat_is_allowed(update, allow_groups=True, allowed_chat_id=-1001))
        self.assertFalse(security.chat_is_allowed(update, allow_groups=True, allowed_chat_id=-1002))


class AppPolicyV40Tests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _update(user_id, chat_id=None):
        chat_id = user_id if chat_id is None else chat_id
        return SimpleNamespace(
            message=SimpleNamespace(text='/meuid', message_id=1, reply_text=mock.AsyncMock()),
            callback_query=None,
            effective_user=SimpleNamespace(id=user_id, username='u', full_name='U') if user_id is not None else None,
            effective_chat=SimpleNamespace(type='private', id=chat_id),
        )

    def setUp(self):
        import app
        self.app = app
        for p in (mock.patch.object(app, 'ASSESSOR_ALLOWED_CHAT_ID', ''),
                  mock.patch.object(app, 'ASSESSOR_ALLOW_GROUPS', False)):
            p.start()
            self.addCleanup(p.stop)

    def test_authorization_is_fail_closed_without_user_id(self):
        update = self._update(7)
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(self.app.usuario_autorizado(update))
        with mock.patch.dict(os.environ, {'TELEGRAM_ALLOWED_USER_ID': '7'}, clear=True):
            self.assertTrue(self.app.usuario_autorizado(update))
            self.assertFalse(self.app.usuario_autorizado(self._update(8)))
            self.assertFalse(self.app.usuario_autorizado(self._update(None, 7)))

    async def test_unauthorized_handler_is_fail_silent(self):
        update = self._update(8)
        with mock.patch.dict(os.environ, {'TELEGRAM_ALLOWED_USER_ID': '7'}, clear=True), \
                mock.patch.object(self.app, 'enviar_resposta', mock.AsyncMock()) as enviar:
            self.assertTrue(await self.app.bloquear_se_nao_autorizado(update))
        update.message.reply_text.assert_not_awaited()
        enviar.assert_not_awaited()

    def test_startup_validator_requires_allowlist(self):
        with mock.patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'x'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'TELEGRAM_ALLOWED_USER_ID é obrigatório'):
                self.app.validar_configuracao_seguranca()

    async def test_meuid_passes_authorization_and_pin(self):
        app = self.app
        update = self._update(7)
        with mock.patch.object(app, 'enviar_resposta', mock.AsyncMock()) as enviar, \
                mock.patch.object(app, 'registrar_mensagem_update', mock.Mock()):
            with mock.patch.object(app, 'bloquear_se_nao_autorizado', mock.AsyncMock(return_value=True)):
                await app.meuid_command(update, None)
            enviar.assert_not_awaited()
            with mock.patch.object(app, 'bloquear_se_nao_autorizado', mock.AsyncMock(return_value=False)), \
                    mock.patch.object(app, 'bloquear_se_assessor_travado', mock.AsyncMock(return_value=True)) as travado:
                await app.meuid_command(update, None)
            travado.assert_awaited_once_with(update, '/meuid')
            enviar.assert_not_awaited()
            with mock.patch.object(app, 'bloquear_se_nao_autorizado', mock.AsyncMock(return_value=False)), \
                    mock.patch.object(app, 'bloquear_se_assessor_travado', mock.AsyncMock(return_value=False)):
                await app.meuid_command(update, None)
            enviar.assert_awaited_once()

    def test_meuid_is_not_public_anymore(self):
        for texto in ('/meuid', 'meuid', '/MEUID'):
            with self.subTest(texto=texto):
                self.assertFalse(self.app.comando_publico(texto))
        self.assertTrue(self.app.comando_publico('/start'))


class SetupScriptV40Tests(unittest.TestCase):
    def test_env_writer_removes_plain_secrets(self):
        import preparar_seguranca_v40 as setup
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'.env'
            path.write_text('TELEGRAM_ALLOWED_USER_ID=7\nASSESSOR_PIN=123456\nASSESSOR_PIN_RESET_KEY=segredo-antigo-123\n', encoding='utf-8')
            lines, _ = setup.ler_env(path)
            setup.escrever_env(path, lines, {
                'ASSESSOR_PIN_HASH':'pbkdf2_sha256$1$YQ$Yg',
                'ASSESSOR_PIN_LENGTH':'6',
                'ASSESSOR_PIN_RESET_KEY_HASH':'pbkdf2_sha256$1$YQ$Yg',
            }, {'ASSESSOR_PIN','ASSESSOR_PIN_RESET_KEY'})
            out = path.read_text(encoding='utf-8')
            self.assertNotIn('ASSESSOR_PIN=123456', out)
            self.assertNotIn('ASSESSOR_PIN_RESET_KEY=segredo', out)
            self.assertIn('ASSESSOR_PIN_HASH=', out)
            self.assertIn('ASSESSOR_PIN_RESET_KEY_HASH=', out)


if __name__ == '__main__':
    unittest.main()
