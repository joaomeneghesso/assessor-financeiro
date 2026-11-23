"""Onda 1: o caminho legado de texto não grava nem apaga sem prévia + confirmação,
"sim" solto não confirma exclusão e as respostas do legado respeitam a privacidade.

Banco, backups e .runtime sempre temporários.
"""
import sqlite3
from contextlib import closing
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from unittest.mock import AsyncMock

import database as db
import services as svc
import app
import security

SESSAO = "u1:c1"


class _BaseBanco(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = mock.patch.object(mod, "DB_PATH", Path(self.tmp.name) / "fixture.db")
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(svc, "BACKUPS_DIR", Path(self.tmp.name) / "backups")
        p.start()
        self.addCleanup(p.stop)
        db.init_db()
        for store in (svc.PENDENCIAS_ALTERACAO, svc.PENDENCIAS_EXCLUSAO):
            store.clear()
            self.addCleanup(store.clear)

    def msg(self, texto):
        return str(svc.processar_mensagem(texto, sessao=SESSAO))

    def tx(self, **extra):
        dados = dict(data="2026-07-10", tipo="despesa", valor=10.0, categoria="Mercado",
                     descricao="compra", conta="Nubank", forma_pagamento="pix")
        dados.update(extra)
        return db.inserir_transacao(dados)

    def linha(self, ident):
        return dict(db.buscar_transacao_por_id(ident))

    def snapshot(self):
        with closing(sqlite3.connect(db.DB_PATH)) as c:
            return (c.execute("SELECT * FROM transacoes ORDER BY id").fetchall(),
                    c.execute("SELECT * FROM metas ORDER BY id").fetchall(),
                    c.execute("SELECT * FROM compromissos ORDER BY id").fetchall(),
                    c.execute("SELECT * FROM transferencias_caixa ORDER BY id").fetchall())


class AlteracaoComPreviaTests(_BaseBanco):
    def test_comandos_de_edicao_nao_gravam_antes_de_confirmar(self):
        a, b = self.tx(), self.tx(valor=20.0)
        fixo = db.inserir_compromisso(dict(tipo="fixo", nome="Academia", categoria="Saúde",
                                           conta_pagamento="Nubank", forma_pagamento="pix", valor=100.0,
                                           data_inicio="2026-07-01", dia_vencimento=10, ativo=True))
        comandos = [f"mudar {a}-{b} para Lazer", f"mudar {a} para Lazer", "mudar último para Lazer",
                    f"corrigir valor {a} para 99", f"corrigir {a} para 99", f"corrigir conta {a} para Itaú",
                    f"corrigir forma {a} para débito", "meta lazer 300", f"pausar fixo {fixo}",
                    f"alterar conta fixo {fixo} para Itaú", f"alterar valor fixo {fixo} para 120",
                    "nova entrada fixa salario 4000 dia 5", "novo fixo agua 150 dia 25"]
        for comando in comandos:
            with self.subTest(comando=comando):
                antes = self.snapshot()
                resposta = self.msg(comando)
                self.assertIn("Responda: confirmar alteracao", resposta)
                self.assertIn("Nada foi alterado ainda", resposta)
                self.assertEqual(antes, self.snapshot())
                self.assertIn("Nada foi alterado", self.msg("cancelar alteracao"))
                self.assertEqual(antes, self.snapshot())

    def test_previa_mostra_antes_e_depois_e_confirmar_grava_uma_vez(self):
        a = self.tx()
        previa = self.msg(f"corrigir valor {a} para 99")
        self.assertIn("R$ 10,00 → R$ 99,00", previa)
        self.assertIsNotNone(svc.assinatura_pendencia("alteracao", SESSAO))
        self.assertIn("Valor atualizado", self.msg("confirmar alteracao"))
        self.assertEqual(99.0, self.linha(a)["valor"])
        self.assertIn("Não há alteração pendente", self.msg("confirmar alteracao"))
        self.assertIsNone(svc.assinatura_pendencia("alteracao", SESSAO))

    def test_faixa_lista_cada_lancamento_e_confirmar_altera_todos(self):
        a, b = self.tx(), self.tx(valor=20.0, categoria="Casa")
        previa = self.msg(f"mudar {a}-{b} para Lazer")
        self.assertIn("2 lançamento(s)", previa)
        self.assertIn("Mercado → Lazer", previa)
        self.assertIn("Casa → Lazer", previa)
        self.msg("confirmar alteracao")
        self.assertEqual({"Lazer"}, {self.linha(a)["categoria"], self.linha(b)["categoria"]})

    def test_dados_mudaram_desde_a_previa_nada_e_gravado(self):
        a = self.tx()
        self.msg(f"corrigir valor {a} para 99")
        db.atualizar_valor_por_id(a, 50.0)
        self.assertIn("mudaram desde a prévia", self.msg("confirmar alteracao"))
        self.assertEqual(50.0, self.linha(a)["valor"])

    def test_pendencia_expira(self):
        a = self.tx()
        self.msg(f"corrigir valor {a} para 99")
        svc.PENDENCIAS_ALTERACAO[SESSAO]["criado_em"] = datetime.now() - timedelta(minutes=11)
        self.assertIn("Não há alteração pendente", self.msg("confirmar alteracao"))
        self.assertEqual(10.0, self.linha(a)["valor"])

    def test_pendencia_e_por_sessao(self):
        a = self.tx()
        self.msg(f"corrigir valor {a} para 99")
        self.assertIn("Não há alteração pendente", str(svc.processar_mensagem("confirmar alteracao", sessao="outra")))
        self.assertEqual(10.0, self.linha(a)["valor"])

    def test_conta_e_forma_de_parcela_isolada_sao_bloqueadas(self):
        svc.registrar_compra_parcelada(dict(data="2026-09-10", tipo="despesa", valor=300, categoria="Compras",
                                            descricao="Notebook", conta="Itaú", forma_pagamento="crédito",
                                            parcelas_total=3, mensagem_original="teste"))
        with closing(sqlite3.connect(db.DB_PATH)) as c:
            parcela = c.execute("SELECT id FROM transacoes ORDER BY id LIMIT 1 OFFSET 1").fetchone()[0]
        antes = self.snapshot()
        for comando in (f"corrigir conta {parcela} para Nubank", f"corrigir forma {parcela} para pix"):
            with self.subTest(comando=comando):
                resposta = self.msg(comando)
                self.assertTrue(resposta.startswith(svc.PREFIXO_ALTERACAO_BLOQUEADA), resposta)
                self.assertNotIn("confirmar alteracao", resposta)
                self.assertIn("Não há alteração pendente", self.msg("confirmar alteracao"))
                # Mesmo pelo caminho confirmado (botão antigo), a parcela não muda sozinha.
                svc.executar_alteracao_confirmada(comando, sessao=SESSAO)
                self.assertEqual(antes, self.snapshot())


class ExclusoesDiretasTests(_BaseBanco):
    def transferencia(self):
        return db.inserir_transferencia_caixa(dict(data="2026-07-10", valor=100.0, conta_origem="Itaú",
                                                   conta_destino="Nubank"))

    def test_apagar_transferencia_caixa_pede_previa_backup_e_audita(self):
        ident = self.transferencia()
        self.assertTrue(app.comando_exige_confirmacao_exclusao(f"apagar transferencia caixa {ident}"))
        previa = self.msg(f"apagar transferencia caixa {ident}")
        self.assertIn("Responda: confirmar exclusao", previa)
        self.assertIn("Itaú → Nubank", previa)
        self.assertIsNotNone(db.buscar_transferencia_caixa_por_id(ident))
        self.assertIn("apagada", self.msg("confirmar exclusao"))
        self.assertIsNone(db.buscar_transferencia_caixa_por_id(ident))
        self.assertTrue(list(svc.BACKUPS_DIR.glob("*.db")), "sem backup antes da exclusão")
        eventos = db.listar_auditoria("transferencias_caixa", ident)
        self.assertEqual(["apagada"], [e["operacao"] for e in eventos])

    def test_resetar_checklist_e_data_pagamento_pedem_confirmacao(self):
        db.marcar_checklist_pagamento("2026-07", "c_1", "pago")
        for comando in ("resetar checklist 2026-07", "limpar checklist 2026-07", "apagar data pagamento C1 2026-07"):
            with self.subTest(comando=comando):
                self.assertTrue(app.comando_exige_confirmacao_exclusao(comando))
                self.assertIn("Responda: confirmar exclusao", self.msg(comando))
                self.assertEqual(1, len(db.buscar_checklist_status_mes("2026-07")))
                self.msg("cancelar exclusao")


def _msg_update(texto, user_id=1, chat_id=1):
    msg = SimpleNamespace(text=texto, message_id=7, reply_text=AsyncMock(), reply_document=AsyncMock(),
                          reply_photo=AsyncMock())
    return SimpleNamespace(message=msg, callback_query=None, effective_user=SimpleNamespace(id=user_id),
                           effective_chat=SimpleNamespace(id=chat_id))


class _BaseApp(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patches = [
            mock.patch.object(app, "ASSESSOR_PIN_HASH", security.hash_secret("123456", iterations=1000,
                                                                             salt=b"0123456789abcdef")),
            mock.patch.object(app, "ASSESSOR_PIN", ""),
            mock.patch.object(app, "ASSESSOR_PIN_LENGTH", "6"),
            mock.patch.object(app, "AUTH_LIMITER", security.AuthAttemptLimiter(3, 15)),
            mock.patch.object(app, "registrar_auditoria", mock.Mock()),
            mock.patch.dict(app.PENDENCIAS_EXCLUSAO, {}, clear=True),
            mock.patch.dict(app.ACAO_PENDENTE_PIN, {}, clear=True),
            mock.patch.dict(app.PIN_TECLADO, {}, clear=True),
            mock.patch.object(app, "bloquear_se_nao_autorizado", AsyncMock(return_value=False)),
            mock.patch.object(app, "registrar_mensagem_update", mock.Mock()),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(app.EXCLUSAO_EXPIRADAS.clear)
        app.bloquear_assessor(1)


class SimSoltoTests(_BaseApp):
    async def _texto(self, texto):
        with mock.patch.object(app.ux, "dispatch_text", AsyncMock(return_value=False)), \
                mock.patch.object(app, "executar_confirmacao_exclusao", AsyncMock()) as exe, \
                mock.patch.object(app, "enviar_resposta", AsyncMock()) as env:
            await app.receber_mensagem(_msg_update(texto), SimpleNamespace())
        return exe, env

    async def test_sim_ou_s_nao_confirmam_exclusao_pendente(self):
        for texto in ("sim", "s", "confirmar", "apagar", "excluir", "deletar"):
            with self.subTest(texto=texto):
                app.definir_pendencia_exclusao(1, "apagar 1", "previa")
                exe, env = await self._texto(texto)
                exe.assert_not_awaited()
                self.assertIn("confirmar exclusao", env.await_args.args[1])
                self.assertIsNotNone(app.obter_pendencia_exclusao(1))

    async def test_frase_explicita_confirma(self):
        app.definir_pendencia_exclusao(1, "apagar 1", "previa")
        exe, _ = await self._texto("confirmar exclusao")
        exe.assert_awaited_once()

    async def test_navegar_pela_interface_nova_descarta_exclusao_pendente(self):
        app.definir_pendencia_exclusao(1, "apagar 1", "previa")
        query = SimpleNamespace(data="ux:qualquer", answer=AsyncMock(),
                                message=SimpleNamespace(reply_text=AsyncMock(), chat_id=1))
        update = SimpleNamespace(message=None, callback_query=query, effective_user=SimpleNamespace(id=1),
                                 effective_chat=SimpleNamespace(id=1))
        with mock.patch.object(app.ux, "dispatch_callback", AsyncMock(return_value=True)):
            await app.callback_submenu(update, SimpleNamespace())
        self.assertIsNone(app.obter_pendencia_exclusao(1))
        exe, _ = await self._texto("sim")
        exe.assert_not_awaited()

    async def test_confirmar_alteracao_digitado_vai_ao_nucleo_antes_da_interface(self):
        with mock.patch.object(app.ux, "dispatch_text", AsyncMock(return_value=True)) as ux_text, \
                mock.patch.object(app, "processar_mensagem", mock.Mock(return_value="ok")) as pm, \
                mock.patch.object(app, "enviar_resposta", AsyncMock()):
            await app.receber_mensagem(_msg_update("confirmar alteracao"), SimpleNamespace())
        ux_text.assert_not_awaited()
        self.assertEqual("confirmar alteracao", pm.call_args.args[0])


class PinNoChatTests(_BaseApp):
    async def test_resetar_checklist_nao_e_reset_de_pin(self):
        with mock.patch.object(app, "processar_reset_pin", AsyncMock()) as reset, \
                mock.patch.object(app.ux, "dispatch_text", AsyncMock(return_value=True)):
            await app.receber_mensagem(_msg_update("resetar checklist 2026-11"), SimpleNamespace())
        reset.assert_not_awaited()
        self.assertFalse(app.acao_exige_pin("resetar checklist 2026-11"))
        self.assertTrue(app.acao_exige_pin("resetar chave 123456"))

    async def test_comando_desbloquear_com_pin_apaga_a_mensagem(self):
        ctx = SimpleNamespace(args=["123456"], bot=SimpleNamespace(delete_message=AsyncMock()))
        with mock.patch.object(app, "enviar_teclado_pin", AsyncMock()):
            await app.desbloquear_command(_msg_update("/desbloquear 123456"), ctx)
        ctx.bot.delete_message.assert_awaited_once()

    async def test_reset_incompleto_apaga_a_chave(self):
        ctx = SimpleNamespace(bot=SimpleNamespace(delete_message=AsyncMock()))
        with mock.patch.object(app, "_recovery_armazenada", return_value=True), \
                mock.patch.object(app, "enviar_resposta", AsyncMock()):
            await app.processar_reset_pin(_msg_update("reset MINHACHAVE"), ctx, "reset MINHACHAVE")
        ctx.bot.delete_message.assert_awaited_once()


class PrivacidadeLegadoTests(_BaseApp):
    def _sessao_ux(self, privacy):
        return mock.patch.dict(app.ux.EXPERIENCE.sessions, {"1:1": SimpleNamespace(privacy=privacy)})

    async def test_ocultar_mascara_valores_e_protege(self):
        update = _msg_update("saldo")
        with self._sessao_ux(True), mock.patch.object(app, "chave_sessao_update", return_value="1:1"):
            await app.enviar_resposta(update, "Saldo geral: R$ 1.234,56", comando_executado="saldo geral")
        texto = update.message.reply_text.await_args.args[0]
        self.assertNotIn("1.234,56", texto)
        self.assertNotIn("R$", texto)

    async def test_sem_ocultar_texto_com_valor_sai_protegido(self):
        update = _msg_update("saldo")
        with self._sessao_ux(False), mock.patch.object(app, "chave_sessao_update", return_value="1:1"):
            await app.enviar_resposta(update, "Saldo geral: R$ 1.234,56", comando_executado="saldo geral")
        self.assertIn("1.234,56", update.message.reply_text.await_args.args[0])
        self.assertTrue(update.message.reply_text.await_args.kwargs.get("protect_content"))

    async def test_ocultar_nao_envia_imagem(self):
        update = _msg_update("dashboard")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"x")
        self.addCleanup(Path(f.name).unlink)
        with self._sessao_ux(True), mock.patch.object(app, "chave_sessao_update", return_value="1:1"):
            await app.enviar_resposta(update, {"texto": "Total R$ 10,00", "imagem": f.name}, comando_executado="x")
        update.message.reply_photo.assert_not_awaited()

    async def test_arquivo_so_vai_ao_chat_com_pin_e_protegido(self):
        with tempfile.TemporaryDirectory() as tmp:
            arquivo = Path(tmp) / "export.csv"
            arquivo.write_text("a;b", encoding="utf-8")
            update = _msg_update("exportar csv 2026-07")
            with mock.patch.object(app, "enviar_teclado_pin", AsyncMock()) as teclado:
                await app.enviar_resposta(update, {"texto": "CSV gerado", "arquivo": str(arquivo)})
            update.message.reply_document.assert_not_awaited()
            teclado.assert_awaited_once()
            self.assertIn(1, app.ACAO_PENDENTE_PIN)  # entrega refeita após o PIN

            app.desbloquear_assessor(1)
            update = _msg_update("exportar csv 2026-07")
            await app.enviar_resposta(update, {"texto": "CSV gerado", "arquivo": str(arquivo)})
            update.message.reply_document.assert_awaited_once()
            self.assertTrue(update.message.reply_document.await_args.kwargs.get("protect_content"))

    def test_botoes_da_previa_de_alteracao_sao_vinculados(self):
        with mock.patch.object(app, "_assinatura", return_value="0123456789ab"):
            markup = app.montar_teclado_confirmacoes_texto(
                "mudar 1 para Lazer", "x\nResponda: confirmar alteracao\nPara desistir: cancelar alteracao", "1:1")
        comandos = [app.CALLBACK_COMANDOS[b.callback_data] for b in markup.inline_keyboard[0]]
        self.assertEqual(["__legado__[alteracao:0123456789ab]:confirmar alteracao",
                          "__legado__[alteracao:0123456789ab]:cancelar alteracao"], comandos)
        self.assertTrue(app._RE_BOTAO_TEXTO.match(comandos[0]))


class OperacaoTests(unittest.IsolatedAsyncioTestCase):
    def test_limitador_persistente_so_na_subida(self):
        original = app.AUTH_LIMITER
        self.addCleanup(setattr, app, "AUTH_LIMITER", original)
        self.assertNotEqual("LimitadorPersistente", type(original).__name__)
        with tempfile.TemporaryDirectory() as tmp:
            limitador = app.ativar_limitador_persistente(Path(tmp) / "lim.bin")
            self.assertEqual("LimitadorPersistente", type(limitador).__name__)
            self.assertIs(limitador, app.AUTH_LIMITER)

    async def test_aviso_de_erro_nunca_vai_para_chat_nao_autorizado(self):
        chat = SimpleNamespace(id=999, type="private", send_message=AsyncMock())
        update = SimpleNamespace(effective_user=SimpleNamespace(id=999), effective_chat=chat)
        with mock.patch.object(app, "usuario_autorizado", return_value=False):
            await app.avisar_erro_ao_titular(update, "erro")
        chat.send_message.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
