"""Botões no lugar de frases digitadas (confirmar/cancelar, exportar, voltar a
herdar) e coerência de cores e ícones dos botões.

Olha os dois lados: o botão faz exatamente o que a frase digitada faz (e nada
além disso), e digitar continua funcionando como antes. Sempre em banco
temporário.
"""
import asyncio
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
from telegram_design import button_label, button_style, screen_styles
from tests.relogio_fixo import data_fixa

# Mês fixo; as classes com banco fixam "hoje" em HOJE (dia comum, antes do corte).
HOJE = date(2026, 11, 9)
MES = HOJE.strftime("%Y-%m")


def botoes(teclado):
    """[(texto, comando registrado, estilo)] de um InlineKeyboardMarkup legado."""
    saida = []
    for linha in teclado.inline_keyboard:
        for b in linha:
            saida.append((b.text, app.CALLBACK_COMANDOS.get(b.callback_data, b.callback_data),
                          getattr(b, "style", None), b.callback_data))
    return saida


class DesignDosBotoes(unittest.TestCase):
    def test_sem_icone_generico_e_icones_com_sentido(self):
        self.assertEqual("📅 Hoje", button_label("Hoje", ("answer", "2026-10-14")))
        self.assertEqual("📅 Ontem", button_label("Ontem", ("answer", "2026-10-13")))
        self.assertEqual("Sim", button_label("Sim", ("answer", "sim")))
        self.assertEqual("Não", button_label("Não", ("answer", "não")))
        self.assertEqual("Próximas ›", button_label("Próximas ›", ("page", 1)))
        self.assertEqual("✏️ Nome", button_label("Nome", ("new_fixed_edit", "name")))
        self.assertEqual("⏭️ Pular esta conta", button_label("Pular esta conta", ("cash_setup_skip",)))
        self.assertEqual("🗑 Apagar", button_label("Apagar", ("guided", "apagar_lancamento:3")))
        for label in ("Hoje", "Sim", "Próximas ›", "Pausar até amanhã", "Meu mês", "Detalhar mês"):
            self.assertFalse(button_label(label, ("x",)).startswith("📋"), label)
        # Preservação: ícones explícitos, números e referências ficam intactos.
        self.assertEqual("🏠 Início", button_label("🏠 Início", ("view", "home")))
        self.assertEqual("1/4", button_label("1/4", ("page", 0)))
        self.assertEqual("✖️ Cancelar", button_label("Cancelar", ("cancel",)))
        self.assertEqual("✅ Salvar", button_label("Salvar", ("fixed_save",)))
        self.assertIn("Copiar", button_label("Copiar", ("copy_text", "x")))

    def test_estilos_por_tipo_de_acao(self):
        self.assertEqual("success", button_style("", ("legacy", "__legado__:confirmar pagamento")))
        self.assertEqual("success", button_style("", ("legacy", "__legado__[fatura:0123456789ab]:confirmar pagamento")))
        self.assertEqual("danger", button_style("", ("legacy", "__legado__[exclusao:0123456789ab]:confirmar exclusao")))
        self.assertEqual("danger", button_style("", ("legacy", "__legado__:confirmar exclusao")))
        self.assertEqual("danger", button_style("", ("legacy", "__confirmar_exclusao__")))
        self.assertIsNone(button_style("", ("legacy", "__legado__:cancelar pagamento")))
        self.assertEqual("danger", button_style("", ("legacy", "__legado__:saldo inicial 2026-11 itaú herdado")))
        self.assertEqual("danger", button_style("", ("guided", "apagar_lancamento:7")))
        self.assertEqual("success", button_style("", ("media_transfer_commit", "n")))
        self.assertEqual("danger", button_style("", ("category_rule_remove_commit",)))
        self.assertEqual("danger", button_style("", ("discard_suspended",)))
        # Preservação: menus continuam como antes.
        self.assertIsNone(button_style("", ("legacy", "exportar csv")))
        self.assertEqual("primary", button_style("", ("legacy", "saldo 2026-10")))
        self.assertEqual("success", button_style("", ("commit", "k")))
        self.assertEqual("danger", button_style("", ("legacy", "apagar 3")))

    def test_cancelar_vermelho_so_quando_ha_confirmacao_verde(self):
        previa = [[("Salvar despesa", ("commit", "k")), ("Editar dados", ("edit_menu",))], [("Cancelar", ("cancel",))]]
        self.assertEqual([["success", "primary"], ["danger"]], screen_styles(previa))
        desfazer = [[("Sim, desfazer", ("undo", "e")), ("Cancelar", ("cancel",))]]
        self.assertEqual([["danger", None]], screen_styles(desfazer))
        etapa = [[("Hoje", ("answer", "x")), ("Ontem", ("answer", "y"))], [("Cancelar", ("cancel",))]]
        self.assertEqual([[None, None], [None]], screen_styles(etapa))
        # "Entrada" (verde) no início não é uma confirmação: Cancelar fica neutro.
        inicio = [[("Entrada", ("start", "receita")), ("Cancelar", ("cancel",))]]
        self.assertEqual([["success", None]], screen_styles(inicio))
        midia = [[("✅ Salvar transferência", ("media_transfer_commit", "n"))], [("Descartar", ("media_kind", "n", "discard"))]]
        self.assertEqual([["success"], ["danger"]], screen_styles(midia))


class _Banco(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", Path(self.tmp.name) / "fixture.db")
            p.start()
            self.addCleanup(p.stop)
        for alvo, valor in (("BACKUPS_DIR", Path(self.tmp.name) / "backups"),
                            ("EXPORTS_DIR", Path(self.tmp.name) / "exports")):
            p = patch.object(svc, alvo, valor)
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        for store in (svc.PENDENCIAS_PAGAMENTO_FATURA, svc.PENDENCIAS_EXCLUSAO,
                      svc.PENDENCIAS_EXPORTACAO, svc.PENDENCIAS_IMPORTACAO, svc.PENDENCIAS_ALTERACAO):
            store.clear()
            self.addCleanup(store.clear)
        for nome in ("CALLBACK_COMANDOS",):
            p = patch.object(app, nome, {})
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(app, "persistir_callback_comandos", lambda *a, **k: None)
        p.start()
        self.addCleanup(p.stop)
        self.enterContext(data_fixa(HOJE))
        db.inserir_transacao(dict(data=f"{MES}-01", tipo="despesa", valor=200, categoria="Compras",
                                  descricao="Loja", conta="Itaú", forma_pagamento="crédito"))

    def teclado(self, comando, sessao="1:1"):
        resposta = svc.processar_mensagem(comando, sessao=sessao)
        return resposta, app.montar_teclado_inline_para_resposta(comando, resposta)

    def confirmado(self, comando, sessao="1:1"):
        """Onda 2: saldo inicial por texto mostra prévia; a resposta final vem do confirmar."""
        self.assertIn("Responda: confirmar alteracao", str(svc.processar_mensagem(comando, sessao=sessao)))
        resposta = svc.processar_mensagem("confirmar alteracao", sessao=sessao)
        return resposta, app.montar_teclado_inline_para_resposta(comando, resposta)

    def movimentos(self):
        return db.listar_fatura_movimentos(MES)


class TecladosDasPrevias(_Banco):
    def test_previa_de_fatura_tem_confirmar_verde_e_cancelar_vermelho(self):
        for comando, rotulo, nome in (("reembolso de 50 na fatura itaú", "estorno", "estorno"),
                                      ("paguei 50 da fatura itaú usando itaú", "pagamento", "pagamento"),
                                      ("credito de 10 na fatura itaú", "credito", "crédito")):
            with self.subTest(comando=comando):
                resposta, teclado = self.teclado(comando)
                self.assertIn(f"Responda: confirmar {rotulo}", resposta)  # texto inalterado
                (t1, c1, s1, _), (t2, c2, s2, _) = botoes(teclado)
                self.assertEqual((f"✅ Confirmar {nome}", f"__legado__:confirmar {rotulo}", "success"), (t1, c1, s1))
                self.assertEqual(("✖️ Cancelar", f"__legado__:cancelar {rotulo}", "danger"), (t2, c2, s2))
                # Com a sessão, o botão fica preso a esta prévia.
                vinculado = botoes(app.montar_teclado_inline_para_resposta(comando, resposta, "1:1"))
                self.assertRegex(vinculado[0][1], rf"^__legado__\[fatura:[0-9a-f]{{12}}\]:confirmar {rotulo}$")
                self.assertEqual("success", vinculado[0][2])
        self.assertEqual([], self.movimentos())

    def test_exclusao_de_movimento_de_fatura(self):
        svc.processar_mensagem("reembolso de 50 na fatura itaú", sessao="1:1")
        svc.processar_mensagem("confirmar estorno", sessao="1:1")
        mov_id = self.movimentos()[0]["id"]
        resposta, teclado = self.teclado(f"apagar #F{mov_id}")
        self.assertIn("Responda: confirmar exclusao", resposta)
        (t1, c1, s1, _), (t2, c2, s2, _) = botoes(teclado)
        self.assertEqual(("🗑 Sim, apagar", "__legado__:confirmar exclusao", "danger"), (t1, c1, s1))
        self.assertEqual(("✖️ Não apagar", "__legado__:cancelar exclusao", None), (t2, c2, s2))

    def test_importacao_csv(self):
        texto = "📥 Prévia\n\nPara gravar no banco, envie:\nconfirmar importacao\n\nPara descartar a prévia, envie:\ncancelar importacao"
        (t1, c1, s1, _), (t2, c2, s2, _) = botoes(app.montar_teclado_inline_para_resposta("analisar csv", texto))
        self.assertEqual(("✅ Importar", "__legado__:confirmar importacao", "success"), (t1, c1, s1))
        self.assertEqual(("✖️ Descartar", "__legado__:cancelar importacao", "danger"), (t2, c2, s2))

    def test_exportacao_oferece_periodos(self):
        resposta, teclado = self.teclado("exportar csv")
        comandos = {t: c for t, c, _, _ in botoes(teclado)}
        hoje = date.today()
        self.assertEqual("__legado__:exportar csv tudo", comandos["📦 Tudo"])
        self.assertEqual("__legado__:cancelar exportacao", comandos["✖️ Cancelar"])
        self.assertEqual("__exportar_periodo__:mes_atual", comandos["📅 Este mês"])
        self.assertEqual("__exportar_periodo__:mes_passado", comandos["📅 Mês passado"])
        self.assertEqual("__exportar_periodo__:ano_atual", comandos["📅 Este ano"])
        # Datas calculadas no toque, inclusive na virada do ano.
        f = app.comando_exportacao_periodo
        self.assertEqual("exportar csv 2026-12-01 2026-12-31", f("mes_atual", date(2026, 12, 15)))
        self.assertEqual("exportar csv 2025-12-01 2025-12-31", f("mes_passado", date(2026, 1, 3)))
        self.assertEqual("exportar csv 2024-02-01 2024-02-29", f("mes_atual", date(2024, 2, 10)))
        self.assertEqual("exportar csv 2026-01-01 2026-12-31", f("ano_atual", date(2026, 7, 1)))
        self.assertIsNone(f("outro"))
        # Cada botão funciona com a exportação pendente...
        r = svc.processar_mensagem("exportar csv tudo", sessao="1:1")
        self.assertIsInstance(r, dict)
        self.assertTrue(Path(r["arquivo"]).exists())
        # ...e também depois que ela expirou (sem pendência).
        r = svc.processar_mensagem(app.comando_exportacao_periodo("mes_atual"), sessao="1:1")
        self.assertIsInstance(r, dict)
        self.assertIn("Não há exportação pendente", svc.processar_mensagem("cancelar exportacao", sessao="1:1"))

    def test_exportacao_digitada_inalterada(self):
        svc.processar_mensagem("exportar csv", sessao="1:1")
        self.assertIn("Exportação cancelada", svc.processar_mensagem("cancelar", sessao="1:1"))
        svc.processar_mensagem("exportar csv", sessao="1:1")
        self.assertIsInstance(svc.processar_mensagem("tudo", sessao="1:1"), dict)

    def test_voltar_a_herdar(self):
        db.definir_saldo_inicial_conta_mes("2026-10", "Itaú", 1000)
        resposta, teclado = self.confirmado("saldo inicial 2026-11 Itaú 500")
        self.assertIn("Saldo inicial definido", resposta)
        (t1, c1, s1, _), (t2, c2, s2, _) = botoes(teclado)
        self.assertEqual(("↩️ Voltar a herdar", "__perguntar_herdar__:saldo inicial 2026-11 Itaú herdado", "danger"), (t1, c1, s1))
        self.assertEqual(("🏦 Ver caixa", "caixa 2026-11", "primary"), (t2, c2, s2))
        # O primeiro toque só pergunta; nada muda até o "Sim".
        self.assertEqual({"Itaú": 500.0}, svc.saldos_iniciais_definidos_heranca("2026-11"))
        # Saldo em mês com base própria não oferece o botão.
        resposta, teclado = self.confirmado("saldo inicial 2026-10 Itaú 700")
        self.assertIn("Saldo inicial definido", resposta)
        self.assertFalse(any("herdar" in t for t, *_ in botoes(teclado)) if teclado else False)

    def test_avisos_de_fatura_levam_ao_a_pagar(self):
        r = svc.processar_mensagem("paguei a fatura do nubank 100", sessao="1:1")
        self.assertEqual([("🧾 Abrir A pagar", "a pagar", "primary")],
                         [b[:3] for b in botoes(app.montar_teclado_inline_para_resposta("x", r))])

    def test_recuperacao_de_pin_tem_cancelar(self):
        t = app.montar_teclado_inline_para_resposta("/seguranca", "🔑 Recuperação\n\nPara sair, envie: cancelar")
        self.assertEqual([("✖️ Cancelar recuperação", "pin_reset_cancelar", None, "pin_reset_cancelar")], botoes(t))
        self.assertIsNone(app.montar_teclado_inline_para_resposta("saldo", "Para sair, envie: cancelar"))

    def test_respostas_comuns_sem_teclado_novo(self):
        for comando in ("meu mês", "fatura itaú", "saldo"):
            resposta = svc.processar_mensagem(comando, sessao="1:1")
            self.assertIsNone(app.montar_teclado_confirmacoes_texto(comando, resposta if isinstance(resposta, str) else ""))


class CliqueNoBotao(_Banco, unittest.IsolatedAsyncioTestCase):
    """O toque executa a mesma frase, direto no assessor, sem passar pelo menu."""

    def setUp(self):
        super().setUp()
        self.respostas = []

        async def core(funcao, *args, **kwargs):
            return funcao(*args, **kwargs)

        async def responder(update, resposta, **kwargs):
            self.respostas.append((resposta, kwargs.get("comando_executado")))

        self.native = AsyncMock(return_value=None)
        for alvo, valor in (("executar_core", core), ("enviar_resposta", responder),
                            ("enviar_acao_digitando", AsyncMock()), ("bloquear_se_nao_autorizado", AsyncMock(return_value=False)),
                            ("bloquear_se_assessor_travado", AsyncMock(return_value=False)),
                            ("iniciar_feedback_visual", AsyncMock()), ("atualizar_feedback_visual", AsyncMock()),
                            ("finalizar_feedback_visual", AsyncMock()), ("marcar_acesso_seguro", Mock()),
                            ("chave_sessao_update", lambda u: "1:1"), ("obter_chat_id_update", lambda u: 1)):
            p = patch.object(app, alvo, valor)
            p.start()
            self.addCleanup(p.stop)
        for alvo, valor in (("dispatch_callback", AsyncMock(return_value=False)), ("run_experience", self.native)):
            p = patch.object(app.ux, alvo, valor)
            p.start()
            self.addCleanup(p.stop)

    async def tocar(self, token):
        query = SimpleNamespace(data=token, answer=AsyncMock(), message=SimpleNamespace(reply_text=AsyncMock()))
        update = SimpleNamespace(callback_query=query, message=None, effective_user=SimpleNamespace(id=1),
                                 effective_chat=SimpleNamespace(id=1))
        await app.callback_submenu(update, SimpleNamespace())
        return self.respostas[-1][0] if self.respostas else None

    def token(self, teclado, texto_inicio):
        return next(tok for t, _, _, tok in botoes(teclado) if t.startswith(texto_inicio))

    async def test_confirmar_grava_uma_vez_e_nao_consulta_o_menu(self):
        _, teclado = self.teclado("reembolso de 50 na fatura itaú")
        confirmar = self.token(teclado, "✅")
        r = await self.tocar(confirmar)
        self.assertIn("Movimento de fatura registrado", r)
        self.assertEqual(1, len(self.movimentos()))
        self.native.assert_not_awaited()
        # Toque duplo: nada pendente, nada gravado de novo.
        self.assertIn("Não há estorno de fatura pendente", await self.tocar(confirmar))
        self.assertEqual(1, len(self.movimentos()))

    def teclado_vinculado(self, comando):
        resposta = svc.processar_mensagem(comando, sessao="1:1")
        return app.montar_teclado_inline_para_resposta(comando, resposta, "1:1")

    async def test_botao_de_previa_antiga_nao_confirma_a_nova(self):
        antigo = self.teclado_vinculado("paguei 50 da fatura itaú usando itaú")
        novo = self.teclado_vinculado("paguei 150 da fatura itaú usando nubank")
        r = await self.tocar(self.token(antigo, "✅"))
        self.assertIn("prévia antiga", r)
        self.assertEqual([], self.movimentos())
        # O cancelar antigo também não mexe na prévia nova.
        self.assertIn("prévia antiga", await self.tocar(self.token(antigo, "✖️")))
        self.assertIn("Movimento de fatura registrado", await self.tocar(self.token(novo, "✅")))
        self.assertEqual([150.0], [float(m["valor"]) for m in self.movimentos()])

    async def test_exclusao_antiga_nao_apaga_outra(self):
        svc.processar_mensagem("reembolso de 50 na fatura itaú", sessao="1:1")
        svc.processar_mensagem("confirmar estorno", sessao="1:1")
        svc.processar_mensagem("reembolso de 20 na fatura itaú", sessao="1:1")
        svc.processar_mensagem("confirmar estorno", sessao="1:1")
        a, b = [m["id"] for m in self.movimentos()]
        antigo = self.teclado_vinculado(f"apagar #F{a}")
        self.teclado_vinculado(f"apagar #F{b}")
        self.assertIn("prévia antiga", await self.tocar(self.token(antigo, "🗑")))
        self.assertEqual(2, len(self.movimentos()))

    async def test_voltar_a_herdar_pergunta_antes(self):
        # Onda 2: o toque em "Voltar a herdar" abre a prévia padrão (antes → depois)
        # com botões vinculados; só o "Confirmar alteração" muda o saldo.
        db.definir_saldo_inicial_conta_mes("2026-10", "Itaú", 1000)
        _, teclado = self.confirmado("saldo inicial 2026-11 Itaú 500")
        previa = await self.tocar(self.token(teclado, "↩️"))
        self.assertIn("volta a herdar", previa)
        self.assertIn("Responda: confirmar alteracao", previa)
        self.assertEqual({"Itaú": 500.0}, svc.saldos_iniciais_definidos_heranca("2026-11"))
        pergunta = app.montar_teclado_inline_para_resposta("x", previa, sessao="1:1")
        self.assertEqual(["success", "danger"], [b[2] for b in botoes(pergunta)])
        self.assertIn("Nada foi alterado", await self.tocar(self.token(pergunta, "✖️")))
        self.assertEqual({"Itaú": 500.0}, svc.saldos_iniciais_definidos_heranca("2026-11"))
        previa = await self.tocar(self.token(teclado, "↩️"))
        pergunta = app.montar_teclado_inline_para_resposta("x", previa, sessao="1:1")
        self.assertIn("voltou a ser herdado", await self.tocar(self.token(pergunta, "✅")))
        self.assertEqual({}, svc.saldos_iniciais_definidos_heranca("2026-11"))

    async def test_bloquear_igual_ao_digitado_sem_descartar_registro(self):
        with patch.object(app, "bloquear_assessor") as bloquear, \
                patch.object(app.ux.EXPERIENCE, "invalidate") as invalidar:
            r = await self.tocar(app.registrar_callback_comando("__bloquear__"))
        bloquear.assert_called_once_with(1)
        invalidar.assert_not_called()
        self.assertIn("Proteção reforçada bloqueada", r)

    async def test_cancelar_descarta(self):
        _, teclado = self.teclado("paguei 50 da fatura itaú usando itaú")
        self.assertIn("Nada foi registrado", await self.tocar(self.token(teclado, "✖️")))
        self.assertIn("Não há pagamento de fatura pendente", svc.processar_mensagem("confirmar pagamento", sessao="1:1"))
        self.assertEqual([], self.movimentos())

    async def test_previa_alterada_nao_grava(self):
        _, teclado = self.teclado("paguei o restante da fatura itaú usando itaú")
        db.inserir_transacao(dict(data=f"{MES}-02", tipo="despesa", valor=30, categoria="Compras",
                                  descricao="Outra", conta="Itaú", forma_pagamento="crédito"))
        r = await self.tocar(self.token(teclado, "✅"))
        self.assertNotIn("Movimento de fatura registrado", r)
        self.assertEqual([], self.movimentos())

    async def test_exclusao_por_botao_faz_backup_e_apaga(self):
        svc.processar_mensagem("reembolso de 50 na fatura itaú", sessao="1:1")
        svc.processar_mensagem("confirmar estorno", sessao="1:1")
        mov_id = self.movimentos()[0]["id"]
        _, teclado = self.teclado(f"apagar #F{mov_id}")
        await self.tocar(self.token(teclado, "🗑"))
        self.assertEqual([], self.movimentos())
        self.assertEqual(1, len(svc.listar_arquivos_backup(svc.PREFIXO_BACKUP_PRE_EXCLUSAO)))

    async def test_pin_e_verificado_com_o_comando_real(self):
        _, teclado = self.teclado("exportar csv")
        await self.tocar(self.token(teclado, "📦"))
        app.bloquear_se_assessor_travado.assert_awaited()
        self.assertEqual("exportar csv tudo", app.bloquear_se_assessor_travado.await_args.args[1])

    async def test_cancelar_fluxo_guiado_e_bloquear(self):
        app.definir_pendencia_guiada(1, "corrigir_valor", {"id": 3})
        self.addCleanup(app.limpar_pendencia_guiada, 1)
        teclado = app.montar_teclado_cancelar_guiado()
        self.assertIn("Fluxo cancelado", await self.tocar(self.token(teclado, "✖️")))
        self.assertIsNone(app.obter_pendencia_guiada(1))


    async def test_apagar_guiado_vai_direto_para_previa_com_botoes(self):
        ident = db.inserir_transacao(dict(data=f"{MES}-03", tipo="despesa", valor=12, categoria="Compras",
                                          descricao="Café", conta="Itaú", forma_pagamento="pix"))
        enviados = []
        message = SimpleNamespace(text=f"✅ Despesa registrada #{ident}",
                                  reply_text=AsyncMock(side_effect=lambda *a, **k: enviados.append(k) or None))
        update = SimpleNamespace(callback_query=SimpleNamespace(message=message), message=None,
                                 effective_user=SimpleNamespace(id=1), effective_chat=SimpleNamespace(id=1))
        self.addCleanup(app.limpar_pendencia_exclusao, 1)
        with patch.object(app, "registrar_mensagem_enviada", Mock()):
            await app.iniciar_fluxo_guiado(update, SimpleNamespace(), f"apagar_lancamento:{ident}")
        self.assertEqual(f"apagar {ident}", app.obter_pendencia_exclusao(1)["comando"])
        textos = [b[0] for b in botoes(enviados[-1]["reply_markup"])]
        self.assertEqual(["🗑 Sim, apagar", "✖️ Não apagar"], textos)
        self.assertIsNone(app.obter_pendencia_guiada(1))
        self.assertEqual(1, len([r for r in db.buscar_ultimas_transacoes(10) if r["id"] == ident]))


class FaturaComRegistroAberto(_Banco, unittest.IsolatedAsyncioTestCase):
    """O caso do Uber: comando de fatura digitado com um registro aberto."""

    def setUp(self):
        super().setUp()
        self.engine = ux.Experience(date_provider=date.today)
        for alvo, valor in (("EXPERIENCE", self.engine),):
            p = patch.object(ux, alvo, valor)
            p.start()
            self.addCleanup(p.stop)
        self.sent = []

        async def fake_send(update, screen, host, edit=False):
            self.sent.append(screen)
        p = patch.object(ux, "send_screen", fake_send)
        p.start()
        self.addCleanup(p.stop)
        self.host = SimpleNamespace(
            PENDENCIAS_GUIADAS={}, PENDENCIAS_EXCLUSAO={}, obter_chat_id_update=lambda u: 1,
            limpar_pendencia_guiada=Mock(), limpar_pendencia_exclusao=Mock(), marcar_acesso_seguro=Mock(),
            registrar_mensagem_enviada=Mock(), bloquear_se_assessor_travado=AsyncMock(return_value=False),
            enviar_acao_digitando=AsyncMock())
        self.key = "1:1"

    async def send(self, text):
        update = SimpleNamespace(message=SimpleNamespace(text=text), callback_query=None,
                                 effective_user=SimpleNamespace(id=1), effective_chat=SimpleNamespace(id=1))
        with patch.object(ux, "session_key", lambda u: self.key):
            return await ux.dispatch_text(update, SimpleNamespace(), self.host)

    async def abrir_registro_na_data(self):
        await self.send("gastei 13,32 uber pix Itaú")
        s = self.engine.session(self.key)
        if s.stage != "date":
            s.stage = "date"
        self.assertEqual("date", s.stage)

    async def test_registro_e_pausado_e_comando_segue_para_a_fatura(self):
        await self.abrir_registro_na_data()
        self.assertFalse(await self.send("Reembolso de 62,16 na fatura Itaú"))
        s = self.engine.session(self.key)
        self.assertIsNone(s.stage)
        self.assertEqual(13.32, s.suspended_draft["valor"])
        self.assertIn("pausado", self.sent[-1].text)
        self.assertIn("R$ 13,32", self.sent[-1].text)
        acoes = [a[0] for row in self.sent[-1].rows for _, a in row]
        self.assertEqual(["resume_suspended", "discard_suspended"], acoes)
        # Retomar devolve o registro intacto na mesma etapa.
        self.engine.act(self.key, ("resume_suspended",))
        self.assertEqual("date", self.engine.session(self.key).stage)

    async def test_preservacao_respostas_normais_da_etapa(self):
        await self.abrir_registro_na_data()
        self.assertTrue(await self.send("ontem"))
        self.assertIsNone(self.engine.session(self.key).suspended_draft)

    async def test_nao_sobrescreve_registro_ja_pausado(self):
        await self.abrir_registro_na_data()
        s = self.engine.session(self.key)
        s.suspended_draft = {"descricao": "Antigo", "valor": 1.0}
        s.suspended_stage = "confirm"
        # O comando segue para a fatura (False) e nada é perdido.
        self.assertFalse(await self.send("Reembolso de 62,16 na fatura Itaú"))
        s = self.engine.session(self.key)
        self.assertEqual("Antigo", s.suspended_draft["descricao"])
        self.assertEqual("date", s.stage)
        self.assertEqual(13.32, s.draft["valor"])

    async def test_confirmar_digitado_depois_da_pausa_mantem_registro_pausado(self):
        await self.abrir_registro_na_data()
        await self.send("Reembolso de 62,16 na fatura Itaú")
        tokens = self.engine.tokens_for(self.key, self.sent[-1])
        pares = zip([tok for row in tokens for _, tok in row], [acao for row in self.sent[-1].rows for _, acao in row])
        retomar = next(tok for tok, acao in pares if tuple(acao) == ("resume_suspended",))
        self.assertFalse(await self.send("confirmar estorno"))
        # O botão "Retomar" da tela de pausa continua funcionando.
        self.assertEqual(("resume_suspended",), tuple(self.engine.resolve(self.key, retomar)))
        s = self.engine.sessions.get(self.key)
        self.assertIsNotNone(s)
        self.assertEqual(13.32, s.suspended_draft["valor"])
        self.assertIsNone(s.stage)
        self.engine.act(self.key, ("resume_suspended",))
        self.assertEqual("date", self.engine.session(self.key).stage)

    async def test_valor_invalido_nao_pausa(self):
        await self.abrir_registro_na_data()
        await self.send("reembolso de , na fatura itau")
        s = self.engine.session(self.key)
        self.assertIsNone(s.suspended_draft)
        self.assertEqual(13.32, s.draft["valor"])

    async def test_comando_de_fatura_nunca_vai_para_a_ia(self):
        def ia(*a, **k):
            raise AssertionError("a IA local não deve interpretar comando de fatura")
        with patch("assessor_ia_local.interpretar_contexto", ia):
            for texto in ("Reembolso de 1 na fatura Itaú", "estorno de 5 na fatura nubank",
                          "paguei 100 da fatura itaú usando mercado pago", "paguei o restante da fatura itaú usando itaú",
                          "reembolso de 1 na fatura itaú 2026-13"):
                with self.subTest(texto=texto):
                    self.assertFalse(await self.send(texto))
                    self.assertIsNone(self.engine.session(self.key).draft)
        self.assertEqual([], self.sent)

    async def test_sem_registro_aberto_nao_mostra_aviso(self):
        self.assertFalse(await self.send("Reembolso de 62,16 na fatura Itaú"))
        self.assertEqual([], self.sent)


if __name__ == "__main__":
    unittest.main()
