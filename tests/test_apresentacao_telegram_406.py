"""Contratos de transporte e isolamento da nova apresentação."""
import html
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from html.parser import HTMLParser
from telegram_design import button_label, legacy_pages, message_html, present_text


class TelegramHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.content = []

    def handle_starttag(self, tag, attrs):
        if tag not in {'b', 'i', 'u', 's', 'code', 'pre', 'a', 'blockquote', 'tg-spoiler'}:
            raise AssertionError('Tag não suportada: '+tag)
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            raise AssertionError('HTML desbalanceado')

    def handle_data(self, text):
        self.content.append(text)


class PresentationContracts(unittest.TestCase):
    def test_long_untrusted_reports_preserve_every_character_and_balanced_pages(self):
        payload = '<script>& "Conta" 😀' * 400
        pages = legacy_pages('Relatório\n'+payload, limit=280)
        collected = []
        for page in pages:
            self.assertLessEqual(len(page.encode('utf-16-le'))//2, 280)
            parser = TelegramHTML()
            parser.feed(page)
            self.assertEqual([], parser.stack)
            collected.append(''.join(parser.content))
        # A quebra de páginas insere somente separadores, sem perder dados.
        self.assertEqual(payload, ''.join(collected).replace('\n', '').removeprefix('Relatório'))

    def test_formatting_is_idempotent_and_keeps_money_references_and_privacy(self):
        for payload in ('<b>Início</b>\n<i>Setembro 2026</i>\nR$ 1.240,80\n••••',
                        '<b>Lançamento #54</b>\nConta &lt;teste&gt;\nR$ -340,19',
                        'Cancelado. Nenhuma alteração foi salva.'):
            once = present_text(payload)
            self.assertEqual(once, present_text(once))
            before = html.unescape(payload)
            for marker in ('1.240,80', '••••', '#54', '-340,19', '<teste>'):
                if marker in before:
                    self.assertIn(marker, html.unescape(once))

    def test_direct_message_escapes_injected_html(self):
        value = 'Erro\nConta <b>falsa</b> & <script>ação</script>'
        result = message_html(value)
        parser = TelegramHTML()
        parser.feed(result)
        self.assertEqual([], parser.stack)
        self.assertIn('Conta <b>falsa</b> & <script>ação</script>', ''.join(parser.content))

    def test_decoration_preserves_callbacks_and_copy_payload(self):
        action = ('copy_text', '#C54 | R$ 49,99')
        original = action
        self.assertIn('Copiar', button_label('Copiar', action))
        self.assertEqual(original, action)
        self.assertEqual('🏠 Início', button_label('🏠 Início', ('view', 'home')))
        self.assertEqual('1/4', button_label('1/4', ('page', 0)))

    def test_maximum_native_screen_is_not_expanded_past_limit(self):
        original = '<b>Saldo</b>\n' + 'x' * (3900 - len('<b>Saldo</b>\n'))
        self.assertEqual(original, present_text(original))


class LegacyPhotoPresentation(unittest.IsolatedAsyncioTestCase):
    async def test_long_caption_continues_without_losing_content(self):
        import app
        caption='Dashboard\n'+'Conta <teste> & valor R$ 1.240,80 😀 '*120
        message=SimpleNamespace(reply_photo=AsyncMock(),reply_text=AsyncMock())
        update=SimpleNamespace(message=message,callback_query=None)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'imagem.png';path.write_bytes(b'fixture')
            with patch.object(app,'montar_teclado_inline_para_resposta',return_value=None), patch.object(app,'registrar_mensagem_enviada'):
                await app.enviar_resposta(update,dict(texto=caption,imagem=str(path)),mostrar_menu=False)
        rendered=[message.reply_photo.await_args.kwargs['caption']]
        rendered += [call.args[0] for call in message.reply_text.await_args_list]
        self.assertGreater(len(rendered),1)
        joined=[]
        for page in rendered:
            self.assertLessEqual(len(page.encode('utf-16-le'))//2,950)
            parser=TelegramHTML();parser.feed(page)
            self.assertEqual([],parser.stack);joined.append(''.join(parser.content))
        self.assertIn('Conta <teste>', ''.join(joined))
        self.assertEqual(120, ''.join(joined).count('R$ 1.240,80'))
