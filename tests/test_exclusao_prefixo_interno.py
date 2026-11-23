"""O prefixo interno de exclusão não pode ser acionado por texto digitado."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database as db
import services as svc


class ExclusaoPrefixoInternoTests(unittest.TestCase):
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
        self.id = db.inserir_transacao(dict(data="2026-10-05", tipo="despesa", valor=10, categoria="Lazer",
                                            descricao="teste", conta="Nubank", forma_pagamento="pix"))

    def total(self):
        with db.get_connection() as c:
            return c.execute("SELECT count(*) FROM transacoes").fetchone()[0]

    def test_prefixo_digitado_nao_apaga(self):
        for texto in (f"__executar_exclusao__ apagar {self.id}", f"__EXECUTAR_EXCLUSAO__ apagar {self.id}",
                      "__executar_exclusao__ apagar ultimo", "  __executar_exclusao__ apagar 1-50"):
            with self.subTest(texto=texto):
                resposta = svc.processar_mensagem(texto, sessao="t")
                self.assertIn("Comando interno não permitido", resposta)
                self.assertEqual(1, self.total())

    def test_caminho_confirmado_continua_apagando(self):
        svc.executar_exclusao_confirmada(f"apagar {self.id}", sessao="t")
        self.assertEqual(0, self.total())

    def test_sem_confirmacao_o_apagar_direto_continua_bloqueado(self):
        svc.processar_mensagem(f"apagar {self.id}", sessao="t")
        self.assertEqual(1, self.total())


if __name__ == "__main__":
    unittest.main()


class ExportacaoGrandeExigePinTests(unittest.TestCase):
    def test_periodos_grandes_ou_totais_exigem_pin(self):
        for texto in ("exportar csv 2000-01-01 2099-12-31", "exportar csv 2026-06-01 2030-12-30",
                      "exportar csv tudo", "exportar csv 2026-01-01 2027-01-03"):
            with self.subTest(texto=texto):
                self.assertTrue(svc.exportacao_exige_pin(texto, "s-export"))

    def test_periodos_ate_um_ano_continuam_sem_pin(self):
        for texto in ("exportar csv 2026-07", "exportar csv 2026-01-01 2026-12-31",
                      "exportar csv 2026-01-01 2027-01-01", "saldo geral", "exportar csv"):
            with self.subTest(texto=texto):
                self.assertFalse(svc.exportacao_exige_pin(texto, "s-export"))

    def test_resposta_ao_fluxo_guiado_tambem_exige_pin(self):
        svc.pedir_periodo_exportacao("s-export")
        try:
            self.assertTrue(svc.exportacao_exige_pin("tudo", "s-export"))
            self.assertTrue(svc.exportacao_exige_pin("2000-01-01 2099-12-31", "s-export"))
            self.assertFalse(svc.exportacao_exige_pin("2026-07-01 2026-07-31", "s-export"))
        finally:
            svc.PENDENCIAS_EXPORTACAO.clear()
