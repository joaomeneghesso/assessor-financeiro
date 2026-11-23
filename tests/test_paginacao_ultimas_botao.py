"""Botão "Próxima ▶️" das listas paginadas do legado ("ultimas", "buscar ...").

Bug relatado em 13/11/2026: "ultimas" listava os 5 primeiros; ao tocar em
"Próxima", o botão reenviava "ultimas pagina 2" e o motor novo
(``Experience.handle_text``) lia isso como um lançamento de R$ 2,00 com a
descrição "ultimas pagina", abrindo o formulário "Como foi pago?".

O botão de paginação repete um comando do legado: vai direto ao assessor
(prefixo ``__legado__:``), como os botões de confirmar/cancelar.
"""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import app
import database as db
import services as svc
import telegram_experiencia as ux
from tests.relogio_fixo import data_fixa

HOJE = date(2026, 11, 13)


class PaginacaoPorBotaoTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        banco = Path(self.tmp.name) / "fixture.db"
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", banco)
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        self.enterContext(data_fixa(HOJE))
        for i in range(1, 13):
            db.inserir_transacao(dict(data=f"2026-11-{i:02d}", tipo="despesa", valor=10 + i, categoria="Mercado",
                                      descricao=f"Compra {i}", conta="Itaú", forma_pagamento="pix", parcelas_total=1))
        self.engine = ux.Experience(date_provider=lambda: HOJE)
        self.respostas, self.telas = [], []

        async def core(funcao, *args, **kwargs):
            return funcao(*args, **kwargs)

        async def responder(update, resposta, **kwargs):
            self.respostas.append((resposta, kwargs.get("comando_executado")))

        async def tela(update, screen, host, edit=False):
            self.telas.append(screen)

        for alvo, valor in (("executar_core", core), ("enviar_resposta", responder),
                            ("enviar_acao_digitando", AsyncMock()), ("bloquear_se_nao_autorizado", AsyncMock(return_value=False)),
                            ("bloquear_se_assessor_travado", AsyncMock(return_value=False)),
                            ("iniciar_feedback_visual", AsyncMock()), ("atualizar_feedback_visual", AsyncMock()),
                            ("finalizar_feedback_visual", AsyncMock()), ("marcar_acesso_seguro", Mock()),
                            ("chave_sessao_update", lambda u: "1:1"), ("obter_chat_id_update", lambda u: 1)):
            p = patch.object(app, alvo, valor)
            p.start()
            self.addCleanup(p.stop)
        # Motor novo REAL (o bug estava nele); só o envio ao Telegram é simulado.
        for alvo, valor in (("EXPERIENCE", self.engine), ("send_screen", tela),
                            ("dispatch_callback", AsyncMock(return_value=False))):
            p = patch.object(app.ux, alvo, valor)
            p.start()
            self.addCleanup(p.stop)

    def token(self, comando, resposta, rotulo):
        teclado = app.montar_teclado_inline_para_resposta(comando, resposta, "1:1")
        self.assertIsNotNone(teclado, "a lista paginada deveria ter botões")
        for linha in teclado.inline_keyboard:
            for b in linha:
                if rotulo in b.text:
                    return b.callback_data
        self.fail(f"botão {rotulo!r} não encontrado")

    async def tocar(self, token):
        query = SimpleNamespace(data=token, answer=AsyncMock(), message=SimpleNamespace(reply_text=AsyncMock()))
        update = SimpleNamespace(callback_query=query, message=None, effective_user=SimpleNamespace(id=1),
                                 effective_chat=SimpleNamespace(id=1))
        await app.callback_submenu(update, SimpleNamespace())

    async def test_proxima_de_ultimas_mostra_a_pagina_2_e_nao_abre_lancamento(self):
        resposta = svc.processar_mensagem("ultimas", sessao="1:1")
        self.assertIn("Página 1 de", resposta)
        await self.tocar(self.token("ultimas", resposta, "Próxima"))
        self.assertEqual([], self.telas, "o motor novo não pode abrir tela (formulário de lançamento)")
        self.assertIsNone(self.engine.session("1:1").draft)
        texto, comando = self.respostas[-1]
        self.assertIn("Página 2 de", texto)
        self.assertEqual("ultimas pagina 2", comando)  # base dos próximos botões, sem prefixo interno
        # E a página 2 também oferece voltar, de novo direto ao assessor.
        anterior = self.token(comando, texto, "Anterior")
        self.respostas.clear()
        await self.tocar(anterior)
        self.assertIn("Página 1 de", self.respostas[-1][0])
        self.assertEqual([], self.telas)

    async def test_proxima_de_busca_tambem_vai_direto_ao_assessor(self):
        resposta = svc.processar_mensagem("buscar compra", sessao="1:1")
        self.assertIn("Página 1 de", resposta)
        await self.tocar(self.token("buscar compra", resposta, "Próxima"))
        self.assertEqual([], self.telas)
        self.assertIn("Página 2 de", self.respostas[-1][0])


if __name__ == "__main__":
    unittest.main()
