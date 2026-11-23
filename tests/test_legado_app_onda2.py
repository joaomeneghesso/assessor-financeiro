"""Onda 2 (app.py): fluxo guiado legado sem gravação direta, texto não reconhecido
com sugestões e botões, e resíduos de segurança (dedupe por update_id,
allowed_updates, edited_message, .env atômico, ajuda sem PIN em texto puro,
bloquear descarta a ação pendente de PIN).

Banco, backups e .env sempre temporários.
"""
import asyncio
import importlib.util
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from unittest.mock import AsyncMock

import database as db
import services as svc
import app

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("migration_runner_app_onda2", ROOT / "migrations.py")
runner = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = runner
_spec.loader.exec_module(runner)


def _update(texto, update_id=1):
    respostas = []

    async def reply_text(*a, **k):
        respostas.append((a, k))
        return SimpleNamespace(message_id=1, chat_id=1)

    message = SimpleNamespace(text=texto, reply_text=reply_text, message_id=10, chat_id=1)
    return SimpleNamespace(update_id=update_id, message=message, callback_query=None,
                           effective_user=SimpleNamespace(id=1), effective_chat=SimpleNamespace(id=1)), respostas


class _AppBanco(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        for mod, attr, valor in ((db, "DB_PATH", base / "fixture.db"), (svc, "DB_PATH", base / "fixture.db"),
                                 (svc, "BACKUPS_DIR", base / "backups")):
            p = mock.patch.object(mod, attr, valor)
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        runner.apply_migrations(base / "fixture.db", ROOT / "migrations", base / "mig", executed_by="app_onda2")
        for store in (svc.PENDENCIAS_ALTERACAO, svc.PENDENCIAS_EXCLUSAO):
            store.clear()
            self.addCleanup(store.clear)
        self.enviadas = []

        async def responder(update, resposta, **kwargs):
            self.enviadas.append(str(resposta))

        async def core(func, *a, **k):
            return func(*a, **k)

        for alvo, valor in (("bloquear_se_nao_autorizado", AsyncMock(return_value=False)),
                            ("registrar_mensagem_update", mock.Mock()),
                            ("enviar_resposta", responder), ("executar_core", core),
                            ("enviar_acao_digitando", AsyncMock()),
                            ("bloquear_se_assessor_travado", AsyncMock(return_value=False)),
                            ("chave_sessao_update", lambda u: "1:1"),
                            ("PENDENCIAS_GUIADAS", {})):
            p = mock.patch.object(app, alvo, valor)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(app.ux, "dispatch_text", AsyncMock(return_value=False))
        p.start()
        self.addCleanup(p.stop)

    def transacoes(self):
        with closing(sqlite3.connect(db.DB_PATH)) as c:
            return c.execute("SELECT count(*) FROM transacoes").fetchone()[0]


class FluxoGuiadoLegadoTests(_AppBanco):
    async def test_registrar_despesa_guiada_mostra_previa_e_nao_grava(self):
        for tipo, texto in (("registrar_despesa", "gastei 35 no mercado"),
                            ("registrar_entrada", "500 de salário"),
                            ("registrar_parcela", "celular 1200 em 10x no pix")):
            with self.subTest(tipo=tipo):
                svc.PENDENCIAS_ALTERACAO.clear()
                app.definir_pendencia_guiada(1, tipo)
                update, _ = _update(texto)
                await app.receber_mensagem(update, SimpleNamespace())
                self.assertEqual(0, self.transacoes(), self.enviadas[-1])
                self.assertIn("Responda: confirmar alteracao", self.enviadas[-1])
        # O "confirmar alteracao" digitado grava o último pendente, uma vez só.
        update, _ = _update("confirmar alteracao")
        await app.receber_mensagem(update, SimpleNamespace())
        self.assertGreaterEqual(self.transacoes(), 1)
        total = self.transacoes()
        await app.receber_mensagem(_update("confirmar alteracao", 2)[0], SimpleNamespace())
        self.assertEqual(total, self.transacoes())

    async def test_corrigir_categoria_guiada_oferece_aprender_depois_de_confirmar(self):
        ident = db.inserir_transacao(dict(data="2026-11-02", tipo="despesa", valor=10.0, categoria="Outros",
                                          descricao="padaria do zé", conta="Itaú", forma_pagamento="pix"))
        app.definir_pendencia_guiada(1, "corrigir_categoria", {"id": ident})
        with mock.patch.object(app, "oferecer_aprendizado_categoria", AsyncMock()) as oferecer:
            await app.receber_mensagem(_update("Alimentação")[0], SimpleNamespace())
            self.assertEqual("Outros", db.buscar_transacao_por_id(ident)["categoria"])
            await app.receber_mensagem(_update("confirmar alteracao", 2)[0], SimpleNamespace())
        self.assertEqual("Alimentação", db.buscar_transacao_por_id(ident)["categoria"])
        depois = [c.args[2] for c in oferecer.await_args_list if c.args[2]]
        self.assertIn("Alimentação", [d["categoria"] for d in depois])


class TextoNaoReconhecidoTests(unittest.TestCase):
    def test_resposta_tem_sugestoes_parecidas_e_nao_grava(self):
        r = svc.processar_mensagem("alterar data do 3 para ontem", sessao="x")
        self.assertTrue(r.startswith("🤔 Não entendi"), r)
        self.assertIn("Nada foi registrado", r)
        self.assertNotIn("apagar fixo 46", r)  # exemplos sem relação de antes
        r = svc.processar_mensagem("parcelas relatorio", sessao="x")
        self.assertTrue(r.startswith("🤔"), r)

    def test_sem_valor_sugere(self):
        r = svc.processar_mensagem("extrato", sessao="x")
        self.assertTrue(r.startswith("🤔 Não encontrei um valor"), r)
        self.assertIn("extrato", r.lower())

    def test_botoes_registrar_e_menu(self):
        with mock.patch.object(app, "persistir_callback_comandos", lambda *a, **k: None), \
                mock.patch.object(app, "CALLBACK_COMANDOS", {}):
            for resposta in ("🤔 Não entendi esse comando\nNada foi registrado.",
                             "🤔 Não encontrei um valor nessa mensagem.\nNada foi registrado."):
                teclado = app.montar_teclado_inline_para_resposta("x", resposta)
                comandos = [app.CALLBACK_COMANDOS[b.callback_data] for row in teclado.inline_keyboard for b in row]
                self.assertEqual(["registrar", "menu"], comandos)


class SegurancaAppTests(unittest.TestCase):
    def test_update_repetido_e_descartado(self):
        from telegram.ext import ApplicationHandlerStop
        with mock.patch.object(app, "UPDATES_VISTOS", {}):
            asyncio.run(app.descartar_update_repetido(SimpleNamespace(update_id=77), None))
            with self.assertRaises(ApplicationHandlerStop):
                asyncio.run(app.descartar_update_repetido(SimpleNamespace(update_id=77), None))
            asyncio.run(app.descartar_update_repetido(SimpleNamespace(update_id=78), None))

    def test_so_mensagem_nova_e_callback(self):
        self.assertEqual(["message", "callback_query"], app.UPDATES_PERMITIDOS)
        from telegram import Update, Message, Chat, User
        chat, user = Chat(1, "private"), User(1, "t", False)
        nova = Update(1, message=Message(1, datetime.now(), chat, from_user=user, text="/limpar"))
        editada = Update(2, edited_message=Message(1, datetime.now(), chat, from_user=user, text="/limpar"))
        self.assertTrue(app.SO_MENSAGEM_NOVA.check_update(nova))
        self.assertFalse(app.SO_MENSAGEM_NOVA.check_update(editada))

    def test_main_registra_filtros_dedupe_e_allowed_updates(self):
        fonte = Path(app.__file__).read_text(encoding="utf-8")
        principal = fonte[fonte.index("def main():"):]
        self.assertIn("run_polling(allowed_updates=UPDATES_PERMITIDOS)", principal)
        self.assertIn("TypeHandler(Update, descartar_update_repetido), group=-1", principal)
        self.assertEqual(principal.count("CommandHandler("), principal.count("filters=SO_MENSAGEM_NOVA)"))
        self.assertEqual(2, principal.count("MessageHandler(SO_MENSAGEM_NOVA &"))

    def test_env_gravado_de_forma_atomica(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text("A=1\nB=2\n", encoding="utf-8")
            with mock.patch.object(app, "obter_caminho_env", lambda: env), \
                    mock.patch.dict("os.environ", {}, clear=False), \
                    mock.patch.object(app.os, "replace", wraps=app.os.replace) as substituir:
                app.atualizar_valor_env("B", "3")
                app.remover_valor_env("A")
            self.assertEqual(2, substituir.call_count)
            self.assertEqual("B=3\n", env.read_text(encoding="utf-8"))
            self.assertEqual([".env"], [p.name for p in Path(tmp).iterdir()])

    def test_falha_na_escrita_preserva_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text("TOKEN=abc\n", encoding="utf-8")
            with mock.patch.object(app, "obter_caminho_env", lambda: env), \
                    mock.patch.object(app.os, "replace", side_effect=OSError("disco")):
                with self.assertRaises(OSError):
                    app.atualizar_valor_env("X", "1")
            self.assertEqual("TOKEN=abc\n", env.read_text(encoding="utf-8"))
            self.assertEqual([".env"], [p.name for p in Path(tmp).iterdir()])

    def test_ajuda_nao_manda_por_pin_em_texto_puro(self):
        with mock.patch.object(app, "_recovery_armazenada", lambda: False):
            texto = app.montar_instrucao_reset_pin()
        self.assertNotIn("ASSESSOR_PIN=", texto)
        self.assertIn("preparar_seguranca_v40.py", texto)

    def test_bloquear_descarta_acao_pendente_de_pin(self):
        with mock.patch.dict(app.ACAO_PENDENTE_PIN, {}, clear=True):
            app.ACAO_PENDENTE_PIN[5] = {"update": object(), "criado_em": datetime.now()}
            app.bloquear_assessor(5)
            self.assertNotIn(5, app.ACAO_PENDENTE_PIN)


if __name__ == "__main__":
    unittest.main()
