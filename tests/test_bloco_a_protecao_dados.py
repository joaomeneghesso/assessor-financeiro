"""Bloco A: proteção contra perda de dados.

Cada correção é testada junto com o comportamento que precisa continuar igual.
"""
import os
import sqlite3
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import app
import database as db
import services as svc
import telegram_experiencia as ux
from estado_runtime import ProtectedJsonStore



class _ConexaoQueFecha(sqlite3.Connection):
    """Como `with conn`, mas também fecha: no Windows uma conexão aberta
    impede apagar o banco temporário no fim do teste."""
    def __exit__(self, *exc):
        try:
            return super().__exit__(*exc)
        finally:
            self.close()

def compra(valor, descricao="Mercado"):
    return dict(data="2026-10-10", tipo="despesa", valor=valor, categoria="Mercado",
                descricao=descricao, conta="Itaú", forma_pagamento="pix")


class BancoTemporario(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name)
        for mod in (db, svc):
            p = mock.patch.object(mod, "DB_PATH", self.pasta / "fixture.db")
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(svc, "BACKUPS_DIR", self.pasta / "backups")
        p.start()
        self.addCleanup(p.stop)
        db.init_db()

    def ids(self):
        with db.get_connection() as c:
            return [r[0] for r in c.execute("SELECT id FROM transacoes ORDER BY id")]


class BotoesAposReinicioTests(unittest.TestCase):
    def setUp(self):
        for nome in ("CALLBACK_COMANDOS", "CALLBACK_SEQUENCIA", "_CALLBACK_STORE", "_CALLBACK_DIRTY", "_CALLBACK_LAST_SAVE"):
            p = mock.patch.object(app, nome, getattr(app, nome))
            p.start()
            self.addCleanup(p.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        app._CALLBACK_STORE = ProtectedJsonStore(Path(self.tmp.name) / "cb.bin", protect=False)
        app.CALLBACK_COMANDOS = {}
        app.CALLBACK_SEQUENCIA = 0

    def test_token_aleatorio_unico_e_curto(self):
        tokens = {app.registrar_callback_comando("meu mês") for _ in range(300)}
        self.assertEqual(300, len(tokens))
        self.assertTrue(all(t.startswith("cmd:") and len(t.encode()) <= 64 for t in tokens))
        self.assertTrue(all(app.CALLBACK_COMANDOS[t] == "meu mês" for t in tokens))

    def test_botao_antigo_nao_executa_comando_novo_apos_reinicio(self):
        antigo = app.registrar_callback_comando("registrar")
        # Reinício depois de 24h: a restauração descarta tudo e a sequência zera.
        app.CALLBACK_COMANDOS, app.CALLBACK_SEQUENCIA = app._restaurar_callbacks(
            {"saved_at": time.time() - 90000, "sequence": 9, "commands": {antigo: "registrar"}})
        self.assertEqual(({}, 0), (app.CALLBACK_COMANDOS, app.CALLBACK_SEQUENCIA))
        novos = [app.registrar_callback_comando("__confirmar_exclusao__") for _ in range(50)]
        self.assertNotIn(antigo, novos)
        self.assertIsNone(app.CALLBACK_COMANDOS.get(antigo))

    def test_restauracao_dentro_de_24h_continua_valendo(self):
        token = app.registrar_callback_comando("quanto vou pagar")
        app.persistir_callback_comandos(force=True)
        comandos, seq = app._restaurar_callbacks(app._CALLBACK_STORE.load({}))
        self.assertEqual("quanto vou pagar", comandos[token])
        self.assertEqual(1, seq)
        # Botões numéricos antigos (antes desta versão) ainda são restaurados.
        comandos, _ = app._restaurar_callbacks({"saved_at": time.time(), "sequence": 3, "commands": {"cmd:3": "meu mês"}})
        self.assertEqual("meu mês", comandos["cmd:3"])

    def test_arquivo_com_formato_estranho_nao_impede_inicio(self):
        for doc in ({"saved_at": time.time(), "sequence": "12a"},
                    {"saved_at": time.time(), "commands": ["x"]},
                    {"saved_at": "ontem"}, {"saved_at": time.time(), "commands": 5}):
            with self.subTest(doc=doc):
                self.assertEqual(({}, 0), app._restaurar_callbacks(doc))


class SessoesRestauradasTests(unittest.TestCase):
    def experiencia(self, documento):
        store = mock.Mock()
        store.load.return_value = documento
        return ux.Experience(clock=lambda: 10.0, wall_clock=lambda: 1000.0, state_store=store)

    def test_formatos_estranhos_sao_descartados_sem_erro(self):
        for doc in (["lista"], {"saved_at": 999, "sessions": [1, 2]},
                    {"saved_at": 999, "sessions": {"1:1": {"month": "2026-10", "tokens": 5}}},
                    {"saved_at": 999, "sessions": {"1:1": {"month": "2026-10", "selected_obligation": 7}}}):
            with self.subTest(doc=doc):
                self.assertEqual({}, self.experiencia(doc).sessions)

    def test_sessao_valida_continua_restaurada(self):
        exp = self.experiencia({"saved_at": 999, "sessions": {"1:1": {"month": "2026-10", "stage": "confirm", "tokens": {"a": ["view", "home"]}}}})
        self.assertEqual("confirm", exp.sessions["1:1"].stage)
        self.assertEqual(("view", "home"), exp.sessions["1:1"].tokens["a"])


class ExclusaoConfereAPreviaTests(BancoTemporario):
    def test_apagar_ultimo_nao_apaga_registro_novo(self):
        a = db.inserir_transacao(compra(10, "Antigo"))
        self.assertIn("Nada foi apagado ainda", svc.processar_mensagem("apagar ultimo", sessao="s"))
        b = db.inserir_transacao(compra(20, "Novo"))
        resposta = svc.processar_mensagem("confirmar exclusao", sessao="s")
        self.assertIn("mudaram desde a prévia", resposta)
        self.assertEqual([a, b], self.ids())

    def test_faixa_com_registro_novo_nao_apaga(self):
        a = db.inserir_transacao(compra(10))
        svc.processar_mensagem(f"apagar {a}-{a + 5}", sessao="s")
        b = db.inserir_transacao(compra(20))
        self.assertIn("mudaram desde a prévia", svc.processar_mensagem("confirmar exclusao", sessao="s"))
        self.assertEqual([a, b], self.ids())

    def test_fluxo_normal_continua_apagando_e_faz_backup_separado(self):
        a = db.inserir_transacao(compra(10))
        b = db.inserir_transacao(compra(20))
        svc.processar_mensagem("apagar ultimo", sessao="s")
        resposta = svc.processar_mensagem("confirmar exclusao", sessao="s")
        self.assertNotIn("mudaram", resposta)
        self.assertEqual([a], self.ids())
        self.assertEqual(1, len(svc.listar_arquivos_backup(svc.PREFIXO_BACKUP_PRE_EXCLUSAO)))
        self.assertEqual([], svc.listar_arquivos_backup())

    def test_backup_falhou_nada_e_apagado(self):
        a = db.inserir_transacao(compra(10))
        svc.processar_mensagem(f"apagar {a}", sessao="s")
        with mock.patch.object(svc, "criar_backup_db", side_effect=OSError("disco cheio")):
            resposta = svc.processar_mensagem("confirmar exclusao", sessao="s")
        self.assertIn("Nada foi apagado", resposta)
        self.assertIn("disco cheio", resposta)
        self.assertEqual([a], self.ids())

    def test_cancelar_continua_igual(self):
        a = db.inserir_transacao(compra(10))
        svc.processar_mensagem(f"apagar {a}", sessao="s")
        self.assertIn("Nada foi apagado", svc.processar_mensagem("cancelar exclusao", sessao="s"))
        self.assertIn("Não há exclusão pendente", svc.processar_mensagem("confirmar exclusao", sessao="s"))
        self.assertEqual([a], self.ids())


class ExclusaoPeloTelegramTests(BancoTemporario):
    """Caminho dos botões ✅ Sim, apagar / ❌ Cancelar (app.py)."""

    def setUp(self):
        super().setUp()
        self.respostas = []

        async def core(funcao, *args, **kwargs):
            return funcao(*args, **kwargs)

        async def responder(update, resposta, **kwargs):
            self.respostas.append(resposta if isinstance(resposta, str) else str(resposta))

        for alvo, valor in (("executar_core", core), ("enviar_resposta", responder),
                            ("enviar_acao_digitando", mock.AsyncMock())):
            p = mock.patch.object(app, alvo, valor)
            p.start()
            self.addCleanup(p.stop)
        self.update = SimpleNamespace(effective_chat=SimpleNamespace(id=1), effective_user=SimpleNamespace(id=1),
                                      callback_query=None, message=None, effective_message=None)
        p = mock.patch.object(app, "obter_chat_id_update", lambda u: 1)
        p.start()
        self.addCleanup(p.stop)
        p = mock.patch.object(app, "chave_sessao_update", lambda u: "1:1")
        p.start()
        self.addCleanup(p.stop)

    def confirmar(self, comando):
        app.definir_pendencia_exclusao(1, comando, svc.preparar_previa_exclusao(comando))
        import asyncio
        asyncio.run(app.executar_confirmacao_exclusao(self.update, None))

    def test_previa_mudou_nada_apagado(self):
        a = db.inserir_transacao(compra(10))
        app.definir_pendencia_exclusao(1, "apagar ultimo", svc.preparar_previa_exclusao("apagar ultimo"))
        b = db.inserir_transacao(compra(20))
        import asyncio
        asyncio.run(app.executar_confirmacao_exclusao(self.update, None))
        self.assertIn("mudaram desde a prévia", self.respostas[-1])
        self.assertEqual([a, b], self.ids())

    def test_backup_falhou_nada_apagado(self):
        a = db.inserir_transacao(compra(10))
        with mock.patch.object(svc, "criar_backup_db", side_effect=OSError("sem permissão")):
            self.confirmar(f"apagar {a}")
        self.assertIn("Nada foi apagado", self.respostas[-1])
        self.assertEqual([a], self.ids())

    def test_confirmacao_normal_apaga(self):
        a = db.inserir_transacao(compra(10))
        b = db.inserir_transacao(compra(20))
        self.confirmar(f"apagar {a}")
        self.assertEqual([b], self.ids())
        self.assertEqual(1, len(svc.listar_arquivos_backup(svc.PREFIXO_BACKUP_PRE_EXCLUSAO)))


class RodizioDeBackupsTests(BancoTemporario):
    def test_backups_de_exclusao_nao_apagam_historico_diario(self):
        pasta = svc.BACKUPS_DIR
        pasta.mkdir()
        for i in range(15):
            f = pasta / f"financeiro_backup_202610{i:02d}.db"
            f.write_bytes(b"x")
            os.utime(f, (1_000_000 + i, 1_000_000 + i))
        for _ in range(20):
            svc.criar_backup_pre_exclusao()
        self.assertEqual(15, len(svc.listar_arquivos_backup()))
        self.assertEqual(svc.BACKUPS_MANTER, len(svc.listar_arquivos_backup(svc.PREFIXO_BACKUP_PRE_EXCLUSAO)))

    def test_backup_diario_continua_com_o_mesmo_nome_e_rodizio(self):
        caminho, _ = svc.criar_backup_db()
        self.assertTrue(caminho.name.startswith("financeiro_backup_"))
        self.assertIn("Backup automático gerado", svc.processar_mensagem("backup automatico"))
        self.assertEqual(2, len(svc.listar_arquivos_backup()))

    def test_backup_de_hoje(self):
        from datetime import date, timedelta
        self.assertFalse(svc.existe_backup_diario_hoje())
        caminho, _ = svc.criar_backup_db()
        # st_mtime vem do sistema de arquivos; alinha ao relógio corrente para o
        # teste valer também com relógio falso (gate --data).
        agora = time.time()
        os.utime(caminho, (agora, agora))
        self.assertTrue(svc.existe_backup_diario_hoje())
        self.assertFalse(svc.existe_backup_diario_hoje(date.today() + timedelta(days=1)))
        svc.criar_backup_pre_exclusao()
        self.assertFalse(svc.existe_backup_diario_hoje(date.today() + timedelta(days=1)))

    def test_alvo_inexistente_nao_gera_backup(self):
        svc.processar_mensagem("apagar 999", sessao="s")
        resposta = svc.processar_mensagem("confirmar exclusao", sessao="s")
        self.assertIn("Não encontrei", resposta)
        self.assertEqual([], svc.listar_arquivos_backup(svc.PREFIXO_BACKUP_PRE_EXCLUSAO))

    def test_idade_do_ultimo_backup_diario(self):
        self.assertIsNone(svc.horas_desde_ultimo_backup_diario())
        caminho, _ = svc.criar_backup_db()
        os.utime(caminho, (1_000_000, 1_000_000))
        self.assertAlmostEqual(10.0, svc.horas_desde_ultimo_backup_diario(agora=1_000_000 + 36000))
        svc.criar_backup_pre_exclusao()  # não conta como diário
        self.assertAlmostEqual(10.0, svc.horas_desde_ultimo_backup_diario(agora=1_000_000 + 36000))

    def test_recuperacao_ao_iniciar(self):
        import asyncio
        chamadas = []

        async def core(funcao, *args, **kwargs):
            chamadas.append(args[0] if args else funcao.__name__)
            return funcao(*args, **kwargs)

        class Parar(Exception):
            pass

        async def dormir(segundos):
            if segundos != 60:
                raise Parar()

        for tem_hoje, esperado in ((False, True), (True, False)):
            chamadas.clear()
            with mock.patch.object(app, "executar_core", core), \
                 mock.patch.object(app, "ASSESSOR_BACKUP_AUTOMATICO", True), \
                 mock.patch.object(svc, "existe_backup_diario_hoje", lambda: tem_hoje), \
                 mock.patch.object(app.asyncio, "sleep", dormir):
                with self.assertRaises(Parar):
                    asyncio.run(app.rotina_backup_diario())
            self.assertEqual(esperado, "backup automatico" in chamadas, tem_hoje)


class InicioComBancoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name)
        (self.p / "migrations").mkdir()
        for n in ("0001_a.py", "0002_b.py", "0003_c.py", "0004_d.py"):
            (self.p / "migrations" / n).write_text("")
        (self.p / "backups").mkdir()

    def verificar(self):
        return db.verificar_banco_para_iniciar(self.p / "f.db", self.p / "backups", self.p / "migrations")

    def banco(self, versao):
        with sqlite3.connect(self.p / "f.db", factory=_ConexaoQueFecha) as c:
            c.execute(f"PRAGMA user_version = {versao}")

    def test_instalacao_nova_inicia(self):
        self.assertIsNone(self.verificar())

    def test_banco_sumiu_mas_ha_backups_recusa(self):
        (self.p / "backups" / "financeiro_backup_1.db").write_bytes(b"x")
        self.assertIn("Restaure o backup", self.verificar())
        self.assertFalse((self.p / "f.db").exists())

    def test_banco_sumiu_so_com_backup_pre_exclusao_tambem_recusa(self):
        (self.p / "backups" / "financeiro_preexclusao_1.db").write_bytes(b"x")
        self.assertIn("Restaure o backup", self.verificar())

    def test_banco_ilegivel_mantem_comportamento_anterior(self):
        (self.p / "f.db").write_bytes(b"isto nao e sqlite" * 100)
        self.assertIsNone(self.verificar())

    def test_versoes(self):
        for versao, esperado in ((4, None), (0, None), (3, "migrations.py migrate"), (5, "mais nova")):
            with self.subTest(versao=versao):
                self.banco(versao)
                r = self.verificar()
                self.assertTrue(r is None if esperado is None else esperado in r)

    def test_banco_real_do_projeto_usa_as_migrations_reais(self):
        numeros = sorted(int(p.name[:4]) for p in (Path(db.BASE_DIR) / "migrations").glob("[0-9][0-9][0-9][0-9]_*.py"))
        self.assertEqual(4, numeros[-1])


if __name__ == "__main__":
    unittest.main()
