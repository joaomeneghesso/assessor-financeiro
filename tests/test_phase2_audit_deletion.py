import tempfile
import unittest
from pathlib import Path

import database
import services


class AuditDeletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = database.DB_PATH
        self.old_service_db = services.DB_PATH
        database.DB_PATH = Path(self.tmp.name) / "financeiro.db"
        services.DB_PATH = database.DB_PATH
        # A confirmação de exclusão agora gera backup obrigatório: fica no temporário.
        self.old_backups = services.BACKUPS_DIR
        services.BACKUPS_DIR = Path(self.tmp.name) / "backups"
        database.init_db()
        services.PENDENCIAS_EXCLUSAO.clear()
        self.sessao = "user1:chat1"
        self.mov_id = database.inserir_fatura_movimento({
            "ano_mes": "2026-07",
            "conta_cartao": "Nubank",
            "tipo_movimento": "estorno",
            "valor": 50,
            "data_movimento": "2026-07-10",
            "conta_origem": None,
            "descricao": "teste",
            "mensagem_original": "teste",
        })

    def tearDown(self):
        database.DB_PATH = self.old_db
        services.DB_PATH = self.old_service_db
        services.BACKUPS_DIR = self.old_backups
        self.tmp.cleanup()

    def test_exclusao_fatura_exige_confirmacao(self):
        resposta = services.processar_mensagem(f"apagar F{self.mov_id}", self.sessao)
        self.assertIn("Nada foi apagado ainda", resposta)
        self.assertIsNotNone(database.buscar_fatura_movimento_por_id(self.mov_id))
        resposta = services.processar_mensagem("confirmar exclusao", self.sessao)
        self.assertIn("apagado", resposta.lower())
        self.assertIsNone(database.buscar_fatura_movimento_por_id(self.mov_id))

    def test_confirmacao_e_isolada_por_sessao_e_consumida_uma_vez(self):
        services.processar_mensagem(f"apagar F{self.mov_id}", self.sessao)
        self.assertIn("Não há exclusão", services.processar_mensagem("confirmar exclusao", "user2:chat2"))
        services.processar_mensagem("confirmar exclusao", self.sessao)
        self.assertIn("Não há exclusão", services.processar_mensagem("confirmar exclusao", self.sessao))

    def test_cancelamento_preserva_movimento(self):
        services.processar_mensagem(f"apagar F{self.mov_id}", self.sessao)
        resposta = services.processar_mensagem("cancelar exclusao", self.sessao)
        self.assertIn("Nada foi apagado", resposta)
        self.assertIsNotNone(database.buscar_fatura_movimento_por_id(self.mov_id))

    def test_exclusao_gera_auditoria(self):
        services.processar_mensagem(f"apagar F{self.mov_id}", self.sessao)
        services.processar_mensagem("confirmar exclusao", self.sessao)
        eventos = database.listar_auditoria("fatura_movimento", self.mov_id)
        self.assertEqual(1, len(eventos))
        self.assertEqual("exclusao", eventos[0]["operacao"])
        self.assertIn('"valor": 50.0', eventos[0]["dados_antes"])

    def test_edicao_fatura_valida_e_auditada(self):
        # Onda 2: editar #F mostra prévia antes → depois; só grava ao confirmar.
        previa = services.processar_mensagem(f"corrigir F{self.mov_id} valor para 25,50", self.sessao)
        self.assertIn("R$ 50,00 → R$ 25,50", previa)
        self.assertAlmostEqual(50.0, database.buscar_fatura_movimento_por_id(self.mov_id)["valor"])
        resposta = services.processar_mensagem("confirmar alteracao", self.sessao)
        self.assertIn("atualizado", resposta.lower())
        mov = database.buscar_fatura_movimento_por_id(self.mov_id)
        self.assertAlmostEqual(25.5, mov["valor"])
        eventos = database.listar_auditoria("fatura_movimento", self.mov_id)
        self.assertEqual("atualizacao", eventos[0]["operacao"])

    def test_edicao_competencia_invalida_nao_altera(self):
        resposta = services.processar_mensagem(f"corrigir F{self.mov_id} competencia para 2026-99", self.sessao)
        self.assertIn("inválida", resposta)
        self.assertEqual("2026-07", database.buscar_fatura_movimento_por_id(self.mov_id)["ano_mes"])


if __name__ == "__main__":
    unittest.main()
