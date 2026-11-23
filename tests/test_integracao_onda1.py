"""Pontos de encontro entre as frentes da Onda 1 (corretude, gravação com prévia e jornadas)."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import database as db
import services as svc
import telegram_experiencia as ux

HOJE = date(2026, 11, 9)


class IntegracaoOnda1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod, attr, valor in ((db, "DB_PATH", Path(self.tmp.name) / "fixture.db"),
                                 (svc, "DB_PATH", Path(self.tmp.name) / "fixture.db"),
                                 (svc, "BACKUPS_DIR", Path(self.tmp.name) / "backups")):
            p = patch.object(mod, attr, valor)
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        self.addCleanup(svc.PENDENCIAS_ALTERACAO.clear)
        self.engine = ux.Experience(date_provider=lambda: HOJE)
        self.key = "teste-integracao"

    def contagens(self):
        with db.get_connection() as c:
            return tuple(c.execute("SELECT count(*) FROM " + t).fetchone()[0]
                         for t in ("transacoes", "compromissos", "fatura_movimentos", "transferencias_caixa"))

    def test_quanto_gastei_ignora_lancamento_com_data_futura(self):
        # Hoje é 09/11. Gasto de 100,00 em 05/11 (já aconteceu) e parcela de 50,00 em 14/11 (futura).
        # "Quanto gastei" = 100,00, o mesmo critério do Fechamento; antes somava 150,00.
        for dia, valor in (("2026-11-05", 100.0), ("2026-11-14", 50.0)):
            db.inserir_transacao(dict(data=dia, tipo="despesa", valor=valor, categoria="Mercado",
                                      descricao="compra", conta="Itaú", forma_pagamento="pix"))
        tela = self.engine._ai_query_result_core(self.key, {"query_type": "expense_total", "period": ""},
                                                 "quanto gastei")
        self.assertIn("R$ 100,00", tela.text)
        self.assertNotIn("R$ 150,00", tela.text)

    def test_nova_entrada_prevista_nao_grava_por_nenhum_caminho(self):
        antes = self.contagens()
        resposta = svc.processar_mensagem("nova entrada prevista freela 800 dia 20", sessao="t")
        self.assertEqual(antes, self.contagens())
        self.assertNotIn("Despesa registrada", str(resposta))
        self.engine.handle_text(self.key, "nova entrada prevista freela 800 dia 20")
        self.assertEqual(antes, self.contagens())

    def test_correcao_por_texto_pede_previa_e_so_grava_ao_confirmar(self):
        tid = db.inserir_transacao(dict(data="2026-11-05", tipo="despesa", valor=100.0, categoria="Mercado",
                                        descricao="compra", conta="Itaú", forma_pagamento="pix"))
        svc.processar_mensagem(f"corrigir valor {tid} para 80", sessao="t")
        with db.get_connection() as c:
            self.assertEqual(100.0, c.execute("SELECT valor FROM transacoes WHERE id=?", (tid,)).fetchone()[0])
        svc.processar_mensagem("confirmar alteracao", sessao="t")
        with db.get_connection() as c:
            self.assertEqual(80.0, c.execute("SELECT valor FROM transacoes WHERE id=?", (tid,)).fetchone()[0])

    def test_previa_de_alteracao_e_limpa_com_as_demais_pendencias(self):
        tid = db.inserir_transacao(dict(data="2026-11-05", tipo="despesa", valor=100.0, categoria="Mercado",
                                        descricao="compra", conta="Itaú", forma_pagamento="pix"))
        svc.processar_mensagem(f"corrigir valor {tid} para 80", sessao=self.key)
        self.assertTrue(svc._obter_pendencia(svc.PENDENCIAS_ALTERACAO, self.key))
        ux.clear_service_pending(self.key)
        self.assertFalse(svc._obter_pendencia(svc.PENDENCIAS_ALTERACAO, self.key))


if __name__ == "__main__":
    unittest.main()
