"""Parcelamentos pelo caminho legado: gravação e exclusão tudo-ou-nada.

Olha os dois lados:
- o que já funcionava continua idêntico (divisão n-1 iguais + resíduo na
  última, vínculo parcelamento_id = 1ª parcela, mensagens, listagem, saldo);
- o que estava errado deixa de acontecer (parcelas de R$ 0,00/negativas,
  parcelas soltas após falha, parcelamento apagado pela metade).
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import conciliacao
import database as db
import services as svc


def compra(valor, parcelas, forma="pix", data="2026-01-31"):
    return dict(data=data, tipo="despesa", valor=valor, categoria="Compras",
                descricao="Notebook", conta=None, forma_pagamento=forma,
                parcelas_total=parcelas, mensagem_original="teste")


class ParcelamentoAtomicoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", Path(self.tmp.name) / "fixture.db")
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(svc, "BACKUPS_DIR", Path(self.tmp.name) / "backups")
        p.start()
        self.addCleanup(p.stop)
        db.init_db()

    def linhas(self):
        with db.get_connection() as c:
            c.row_factory = None
            return c.execute(
                "SELECT id,data,valor,parcelamento_id,parcela_atual,parcelas_total,"
                "valor_total_parcelamento,descricao FROM transacoes ORDER BY id").fetchall()

    # ---------- gravação ----------
    def test_divisao_e_vinculo_preservados(self):
        resposta = svc.registrar_compra_parcelada(compra(100, 3))
        self.assertIn("Compra parcelada registrada", resposta)
        self.assertIn("apagar parcelamento P1", resposta)
        rows = self.linhas()
        self.assertEqual([33.33, 33.33, 33.34], [r[2] for r in rows])
        self.assertEqual(["2026-01-31", "2026-02-28", "2026-03-31"], [r[1] for r in rows])
        self.assertEqual({1}, {r[3] for r in rows})
        self.assertEqual([1, 2, 3], [r[4] for r in rows])
        self.assertEqual({3}, {r[5] for r in rows})
        self.assertEqual({100}, {r[6] for r in rows})
        self.assertEqual("Notebook (3/3)", rows[-1][7])

    def test_soma_das_parcelas_fecha_o_total_em_centavos(self):
        for valor, n in [(200, 3), (99.99, 7), (1234.56, 10), (0.12, 12), (5000, 24)]:
            with self.subTest(valor=valor, n=n):
                antes = len(self.linhas())
                svc.registrar_compra_parcelada(compra(valor, n))
                novas = self.linhas()[antes:]
                self.assertEqual(n, len(novas))
                self.assertEqual(round(valor * 100), sum(round(r[2] * 100) for r in novas))
                self.assertTrue(all(r[2] >= 0.01 for r in novas))

    def test_valor_pequeno_demais_nao_grava_parcela_zero_nem_negativa(self):
        for valor in (0.05, 0.10, 0.11):
            with self.subTest(valor=valor):
                resposta = svc.registrar_compra_parcelada(compra(valor, 12))
                self.assertIn("Nenhum lançamento foi gravado", resposta)
                self.assertEqual([], self.linhas())

    def test_falha_no_meio_nao_deixa_parcelas_soltas(self):
        original = db._inserir_transacao_conn
        chamadas = {"n": 0}

        def falha_na_terceira(conn, t):
            chamadas["n"] += 1
            if chamadas["n"] == 3:
                raise RuntimeError("falha simulada")
            return original(conn, t)

        with patch.object(db, "_inserir_transacao_conn", falha_na_terceira):
            with self.assertRaises(RuntimeError):
                svc.registrar_compra_parcelada(compra(300, 6))
        self.assertEqual([], self.linhas())

    def test_credito_que_exige_fatura_continua_recusado(self):
        resposta = svc.registrar_compra_parcelada(dict(compra(300, 3, "crédito"), competencia_fatura="2026-02"))
        self.assertIn("Nenhum", resposta)
        self.assertEqual([], self.linhas())

    def test_lancamento_unico_continua_igual(self):
        ident = db.inserir_transacao(dict(compra(50, 1), parcelas_total=1))
        self.assertEqual([(ident, "2026-01-31", 50.0)], [r[:3] for r in self.linhas()])

    # ---------- exclusão ----------
    def test_apagar_parcelamento_remove_tudo_e_mensagem_igual(self):
        svc.registrar_compra_parcelada(compra(90, 3))
        svc.registrar_compra_parcelada(dict(compra(40, 2), descricao="Outro"))
        previa = svc.processar_mensagem("apagar parcelamento P1", sessao="t")
        self.assertIn("Nada foi apagado ainda", previa)
        self.assertEqual(5, len(self.linhas()))
        resposta = svc.processar_mensagem("confirmar exclusao", sessao="t")
        self.assertIn("Parcelamento apagado", resposta)
        self.assertIn("Parcelas apagadas: 3/3", resposta)
        self.assertIn("IDs apagados: 1, 2, 3", resposta)
        self.assertIn("R$ 90,00", resposta)
        # O outro parcelamento não é tocado.
        self.assertEqual([4, 5], [r[0] for r in self.linhas()])

    def test_parcela_conciliada_bloqueia_sem_apagar_nada(self):
        svc.registrar_compra_parcelada(compra(90, 3))
        antes = self.linhas()
        with patch.object(conciliacao, "listar_vinculos",
                          lambda *a, **k: [{"transacao_id": 3, "compromisso_id": 9}]):
            with self.assertRaises(conciliacao.ConciliacaoError):
                svc.apagar_parcelamento(1)
        self.assertEqual(antes, self.linhas())

    def test_apagar_inexistente_mantem_resposta(self):
        resposta = svc.apagar_parcelamento(42)
        self.assertIn("Não encontrei parcelamento", resposta)

    def test_ciclo_completo_volta_ao_saldo_original(self):
        db.inserir_transacao(dict(compra(1000, 1), tipo="receita", categoria="Receita", descricao="Salário"))
        resumo_antes = svc.processar_mensagem("resumo 2026-02", sessao="t")
        svc.registrar_compra_parcelada(compra(300, 3))
        self.assertNotEqual(resumo_antes, svc.processar_mensagem("resumo 2026-02", sessao="t"))
        svc.apagar_parcelamento(2)
        self.assertEqual(resumo_antes, svc.processar_mensagem("resumo 2026-02", sessao="t"))


if __name__ == "__main__":
    unittest.main()
