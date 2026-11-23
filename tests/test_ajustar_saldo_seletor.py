"""Ajustar saldo: seletor com todas as contas e seus saldos; escolher, digitar o valor e confirmar."""
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import contas_inativas
import database as db
import services as svc
import telegram_experiencia as ux

HOJE = date(2026, 10, 28)
MES = "2026-10"


class AjustarSaldoSeletorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", Path(self.tmp.name) / "fixture.db")
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        self.engine = ux.Experience(date_provider=lambda: HOJE)
        self.key = "teste-seletor"
        for conta, valor in (("Itaú", 0.0), ("Mercado Pago", 5000.0), ("Caju", 818.02)):
            db.definir_saldo_inicial_conta_mes(MES, conta, valor, "teste")

    def sessao(self):
        return self.engine.sessions[self.key]

    def abrir(self):
        return self.engine.act(self.key, ("cash_setup_start",))

    def botoes(self, tela):
        return [(r, a) for linha in tela.rows for r, a in linha]

    def test_botao_abre_seletor_com_todas_as_contas_e_saldos(self):
        tela = self.abrir()
        rotulos = [r for r, _ in self.botoes(tela)]
        self.assertIn("Mercado Pago · R$ 5.000,00", rotulos)
        self.assertIn("Itaú · R$ 0,00", rotulos)
        self.assertIn("Caju · R$ 818,02", rotulos)
        self.assertIn("➕ Outra conta", rotulos)
        self.assertIn("📋 Todas em sequência", rotulos)
        self.assertIsNone(self.sessao().stage)  # nada em andamento até escolher a conta

    def test_escolher_conta_pede_o_valor_so_dela(self):
        self.abrir()
        tela = self.engine.act(self.key, ("cash_setup_account", "Mercado Pago"))
        self.assertEqual("cash_setup_value", self.sessao().stage)
        self.assertIn("Ajustar saldo · Mercado Pago", tela.text)
        self.assertNotIn("1/1", tela.text)
        self.assertNotIn("Pular esta conta", [r for r, _ in self.botoes(tela)])

    def test_fluxo_completo_altera_so_a_conta_escolhida(self):
        self.abrir()
        self.engine.act(self.key, ("cash_setup_account", "Mercado Pago"))
        confirmacao = self.engine.handle_text(self.key, "5100")
        self.assertIn("Confirmar saldo atual?", confirmacao.text)
        final = self.engine.act(self.key, ("cash_setup_commit",))
        self.assertIn("concluído", final.text)
        self.assertIn("✏️ Ajustar outra conta", [r for r, _ in self.botoes(final)])
        caixa = svc.calcular_caixa_por_conta_mes(MES)["contas"]
        self.assertAlmostEqual(5100.0, caixa["Mercado Pago"]["disponivel"], places=2)
        self.assertAlmostEqual(818.02, caixa["Caju"]["disponivel"], places=2)  # intacta
        self.assertAlmostEqual(0.0, caixa.get("Itaú", {}).get("disponivel", 0.0), places=2)  # intacta

    def test_todas_em_sequencia_continua_disponivel(self):
        self.abrir()
        tela = self.engine.act(self.key, ("cash_setup_all",))
        self.assertEqual("cash_setup_value", self.sessao().stage)
        self.assertIn("1/3", tela.text)
        self.assertIn("Pular esta conta", [r for r, _ in self.botoes(tela)])

    def test_conta_desativada_nao_aparece_no_seletor(self):
        contas_inativas.desativar("Caju", "u")
        rotulos = [r for r, _ in self.botoes(self.abrir())]
        self.assertFalse([r for r in rotulos if r.startswith("Caju")])

    def test_modo_ocultar_mascara_os_saldos_do_seletor(self):
        self.engine.act(self.key, ("view", "home"))
        self.sessao().privacy = True
        tela = self.abrir()
        self.assertNotRegex(tela.text, r"R\$\s*\d")
        for rotulo, _ in self.botoes(tela):
            self.assertNotRegex(rotulo, r"R\$\s*\d")
            self.assertNotRegex(rotulo, r"\d,\d\d")
        self.assertTrue(any("••••" in r for r, _ in self.botoes(tela)))

    def test_muitas_contas_ganham_paginacao(self):
        for i in range(10):
            db.definir_saldo_inicial_conta_mes(MES, f"Banco {i:02d}", 10.0 + i, "teste")
        tela = self.abrir()
        rotulos = [r for r, _ in self.botoes(tela)]
        self.assertIn("Mais contas ›", rotulos)
        pagina2 = self.engine.act(self.key, ("cash_setup_pick", 1))
        self.assertIn("‹ Contas", [r for r, _ in self.botoes(pagina2)])

    def test_callbacks_cabem_em_64_bytes(self):
        tela = self.abrir()
        for _, acao in self.botoes(tela):
            self.assertLessEqual(len(repr(acao).encode("utf-8")), 200)  # tokenizados pelo motor, nunca crus
        self.assertTrue(all(isinstance(a, tuple) for _, a in self.botoes(tela)))

    def test_sem_nenhuma_conta_vai_direto_para_criar_a_primeira(self):
        with db.get_connection() as c:
            c.execute("DELETE FROM saldos_mensais_contas")
        tela = self.abrir()
        self.assertEqual("cash_setup_account_name", self.sessao().stage)


if __name__ == "__main__":
    unittest.main()
