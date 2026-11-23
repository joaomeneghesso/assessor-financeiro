"""Baixa de fixo: a conta de pagamento é sempre escolhida pelo titular (padrão sugerido ✦),
e a confirmação avisa quando o caixa da conta ficaria negativo."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import conciliacao
import database as db
import services as svc
import telegram_experiencia as ux

HOJE = date(2026, 10, 28)
MES = "2026-10"


class BaixaFixoContaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", Path(self.tmp.name) / "fixture.db")
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        # A conciliação usa o próprio relógio: fixa a mesma data da Experience.
        p = patch.object(conciliacao, "_hoje", lambda: HOJE)
        p.start()
        self.addCleanup(p.stop)
        self.engine = ux.Experience(date_provider=lambda: HOJE)
        self.key = "teste-baixa"
        # duas contas conhecidas, com bases acompanhadas
        db.definir_saldo_inicial_conta_mes(MES, "Itaú", 0.0, "teste")
        db.definir_saldo_inicial_conta_mes(MES, "Mercado Pago", 5000.0, "teste")
        self.fixo_id = db.inserir_compromisso(dict(
            tipo="fixo", nome="Condominio", categoria="Moradia", conta_pagamento="Pix", conta_origem="Itaú",
            forma_pagamento="pix", valor=231.45, dia_vencimento=16, data_inicio="2026-10-01", data_fim=None,
            parcelas_total=None, ativo=1, origem="teste", observacao=""))
        # inserir_compromisso grava só o campo legado; no banco real a migration 0003 preencheu conta_origem
        with db.get_connection() as c:
            c.execute("UPDATE compromissos SET conta_origem='Itaú' WHERE id=?", (self.fixo_id,))

    def baixar(self):
        return self.engine.act(self.key, ("settle", self.fixo_id, MES))

    def sessao(self):
        return self.engine.sessions[self.key]

    def rotulos(self, tela):
        return [r for linha in tela.rows for r, _ in linha]

    def test_baixa_pergunta_a_conta_em_vez_de_assumir_a_do_fixo(self):
        tela = self.baixar()
        self.assertEqual("account", self.sessao().stage)
        self.assertEqual("", self.sessao().draft["conta"])
        self.assertEqual("✦ Itaú", self.rotulos(tela)[0])  # padrão do fixo, primeiro e marcado
        self.assertIn("Mercado Pago", self.rotulos(tela))
        self.assertIn("cadastrada neste item", tela.text)

    def test_escolher_outra_conta_grava_na_conta_escolhida(self):
        self.baixar()
        tela = self.engine.act(self.key, ("answer", "Mercado Pago"))
        self.assertIn("Conta: Mercado Pago", tela.text)
        self.assertNotIn("ficaria negativo", tela.text)
        self.engine.act(self.key, ("commit", self.sessao().draft["key"]))
        with db.get_connection() as c:
            linhas = c.execute("SELECT conta, valor FROM transacoes WHERE descricao='Condominio'").fetchall()
        self.assertEqual([("Mercado Pago", 231.45)], [tuple(r) for r in linhas])

    def test_conta_sem_saldo_avisa_que_ficaria_negativa_mas_nao_bloqueia(self):
        self.baixar()
        tela = self.engine.act(self.key, ("answer", "Itaú"))
        self.assertIn("O saldo de Itaú ficaria negativo", tela.text)
        self.assertIn("R$ 231,45", tela.text)
        acoes = [a for linha in tela.rows for _, a in linha]
        self.assertTrue(any(a[0] == "commit" for a in acoes))  # só avisa; Salvar continua disponível

    def test_sem_nenhum_saldo_acompanhado_nao_avisa(self):
        with db.get_connection() as c:
            c.execute("DELETE FROM saldos_mensais_contas")
        self.baixar()
        tela = self.engine.act(self.key, ("answer", "Itaú"))
        self.assertNotIn("ficaria negativo", tela.text)

    def test_credito_nao_gera_aviso_de_saldo(self):
        self.engine.act(self.key, ("start", "despesa"))
        for resposta in ("40", "teste", "crédito", "não", "Itaú"):
            try:
                self.engine.answer(self.key, resposta)
            except ValueError:
                pass
        tela = self.engine.preview(self.key)
        self.assertNotIn("ficaria negativo", tela.text)


if __name__ == "__main__":
    unittest.main()
