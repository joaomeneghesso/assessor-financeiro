"""Contratos das melhorias de confiabilidade e aprendizado da versão 4.1.3."""
from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import categorias
import database
import services
import app
from categorias_pessoais import listar_regras, remover_regra, salvar_regra
from estado_runtime import ProtectedJsonStore
from telegram_experiencia import Experience, Screen, TTL


class CategoriasPessoaisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "categorias.json"
        self.env = patch.dict(os.environ, {"ASSESSOR_CATEGORY_RULES_PATH": str(self.path)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_so_aprende_em_acao_explicita_e_regra_pessoal_tem_prioridade(self):
        self.assertFalse(self.path.exists())
        regra = salvar_regra("Mercado Livre", "Eletrônicos", now=datetime(2026, 10, 8, 12, 0))
        self.assertEqual("Eletrônicos", regra["category"])
        self.assertEqual("Eletrônicos", categorias.sugerir_categoria("monitor no Mercado Livre"))
        self.assertEqual("Receita", categorias.sugerir_categoria("Mercado Livre", "receita"))
        self.assertEqual(1, len(listar_regras()))

    def test_atualiza_e_remove_sem_reclassificar_historico(self):
        salvar_regra("Loja do bairro", "Mercado")
        salvar_regra("Loja do bairro", "Pet")
        self.assertEqual("Pet", categorias.sugerir_categoria("compra na loja do bairro"))
        self.assertEqual(1, len(listar_regras()))
        self.assertTrue(remover_regra("Loja do bairro"))
        self.assertIsNone(categorias.sugerir_categoria("compra na loja do bairro"))

    def test_arquivo_invalido_nao_inventa_regra(self):
        self.path.write_text("{incompleto", encoding="utf-8")
        self.assertEqual([], listar_regras())
        self.assertEqual("Pet", categorias.sugerir_categoria("petshop"))


class EstadoRuntimeTests(unittest.TestCase):
    def test_store_atomico_roundtrip_sem_protecao_para_contrato_portatil(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state.bin"
            store = ProtectedJsonStore(path, protect=False)
            self.assertTrue(store.save({"value": [1, "dois"]}))
            self.assertEqual({"value": [1, "dois"]}, store.load())
            self.assertFalse(any(path.parent.glob("*.tmp_*")))

    def test_store_dpapi_nao_grava_json_legivel(self):
        # Windows: DPAPI. Linux (servidor): AES-GCM com chave local (estado_runtime._local_protect).
        import estado_runtime
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(estado_runtime, "CHAVE_LOCAL", Path(temp) / "chave_local.key"):
            path = Path(temp) / "state.bin"
            store = ProtectedJsonStore(path)
            store.save({"segredo": "rascunho financeiro"})
            self.assertNotIn(b"rascunho financeiro", path.read_bytes())
            self.assertEqual("rascunho financeiro", store.load()["segredo"])

    def test_sessao_e_callback_sobrevivem_reinicio_dentro_do_ttl(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "session.bin"
            store = ProtectedJsonStore(path, protect=False)
            first = Experience(clock=lambda: 10.0, wall_clock=lambda: 1000.0, state_store=store)
            session = first.session("1:1")
            session.stage = "amount"
            session.draft = {"tipo": "despesa", "descricao": "Pet Shop"}
            token = first.tokens_for("1:1", Screen("Teste", [[("Continuar", ("flow_resume",))]]))[0][0][1]
            first.persist()

            restored = Experience(clock=lambda: 1.0, wall_clock=lambda: 1000.0 + TTL - 1, state_store=store)
            self.assertEqual("amount", restored.session("1:1").stage)
            self.assertEqual("Pet Shop", restored.session("1:1").draft["descricao"])
            self.assertEqual(("flow_resume",), restored.resolve("1:1", token))
            self.assertEqual("restored_after_restart", restored.session("1:1").last_event)

    def test_sessao_expirada_nao_e_restaurada(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProtectedJsonStore(Path(temp) / "session.bin", protect=False)
            first = Experience(clock=lambda: 10.0, wall_clock=lambda: 1000.0, state_store=store)
            first.session("1:1").stage = "confirm"
            first.persist()
            restored = Experience(clock=lambda: 1.0, wall_clock=lambda: 1001.0 + TTL, state_store=store)
            self.assertNotIn("1:1", restored.sessions)

    def test_callbacks_legados_sao_persistidos_sem_expor_comando(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProtectedJsonStore(Path(temp) / "callbacks.bin")
            old_store = app._CALLBACK_STORE
            old_commands = app.CALLBACK_COMANDOS
            old_sequence = app.CALLBACK_SEQUENCIA
            old_dirty = app._CALLBACK_DIRTY
            old_last = app._CALLBACK_LAST_SAVE
            try:
                app._CALLBACK_STORE = store
                app.CALLBACK_COMANDOS = {}
                app.CALLBACK_SEQUENCIA = 0
                app._CALLBACK_DIRTY = 0
                app._CALLBACK_LAST_SAVE = 0
                token = app.registrar_callback_comando("quanto vou pagar")
                app.persistir_callback_comandos(force=True)
                self.assertEqual("quanto vou pagar", store.load()["commands"][token])
                self.assertNotIn(b"quanto vou pagar", store.path.read_bytes())
            finally:
                app._CALLBACK_STORE = old_store
                app.CALLBACK_COMANDOS = old_commands
                app.CALLBACK_SEQUENCIA = old_sequence
                app._CALLBACK_DIRTY = old_dirty
                app._CALLBACK_LAST_SAVE = old_last


class SaudeAssessorTests(unittest.TestCase):
    def test_status_verifica_copia_em_modo_leitura(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(
            os.environ, {"ASSESSOR_CATEGORY_RULES_PATH": str(Path(temp) / "categorias.json")}
        ):
            old_db, old_service_db, old_backups = database.DB_PATH, services.DB_PATH, services.BACKUPS_DIR
            try:
                database.DB_PATH = Path(temp) / "financeiro.db"
                services.DB_PATH = database.DB_PATH
                services.BACKUPS_DIR = Path(temp) / "backups"
                database.init_db()
                before = hashlib.sha256(database.DB_PATH.read_bytes()).hexdigest()
                text = services.gerar_status()
                after = hashlib.sha256(database.DB_PATH.read_bytes()).hexdigest()
            finally:
                database.DB_PATH, services.DB_PATH, services.BACKUPS_DIR = old_db, old_service_db, old_backups
            self.assertEqual(before, after)
            self.assertIn("Integridade: OK", text)
            self.assertIn("somente leitura", text)
            self.assertIn("Retomada após reinício", text)


if __name__ == "__main__":
    unittest.main()
