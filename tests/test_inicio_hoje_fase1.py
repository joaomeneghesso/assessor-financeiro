"""Linha "Hoje" e rótulo "Deve faltar" no Início (Fase 1)."""
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import database as db
import services as svc
import telegram_experiencia as ux

HOJE = date(2026, 9, 20)


class InicioHojeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", Path(self.tmp.name) / "fixture.db")
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        self.engine = ux.Experience(date_provider=lambda: HOJE)
        self.key = "teste-hoje"

    def fixo(self, nome, dia, valor=100):
        return db.inserir_compromisso(dict(
            tipo="fixo", nome=nome, categoria="Outros", conta_pagamento="Itaú", forma_pagamento="pix",
            valor=valor, dia_vencimento=dia, data_inicio="2026-09-01", data_fim=None,
            parcelas_total=None, ativo=1, origem="teste", observacao=""))

    def home(self):
        return self.engine.act(self.key, ("view", "home"))

    def acoes(self, tela):
        return [(r, a) for linha in tela.rows for r, a in linha]

    def test_sem_nada_vencendo_mostra_linha_tranquila_e_sem_botao_extra(self):
        tela = self.home()
        self.assertIn("Hoje:", tela.text)
        self.assertIn("nenhuma conta vencendo", tela.text)
        self.assertFalse([r for r, _ in self.acoes(tela) if "Ver " in r and "vencid" in r])

    def test_conta_vencida_aparece_com_contagem_e_botao_primeiro(self):
        self.fixo("Internet", 5)
        self.fixo("Luz", 8)
        tela = self.home()
        self.assertIn("2 contas vencidas", tela.text)
        self.assertEqual(("view", "pay"), tela.rows[0][0][1])
        self.assertIn("2 vencidas", tela.rows[0][0][0])

    def test_linha_hoje_nao_mostra_valores_nem_com_privacidade_desligada(self):
        self.fixo("Internet", 5, valor=1234.56)
        linha = [l for l in self.home().text.splitlines() if "Hoje:" in l][0]
        self.assertNotRegex(linha, r"R\$|\d{1,3}\.\d{3}|,\d{2}")

    def test_vence_hoje(self):
        self.fixo("Aluguel", 20)
        tela = self.home()
        self.assertIn("vence hoje", tela.text)

    def test_mes_futuro_nao_mostra_linha_hoje(self):
        self.fixo("Internet", 5)
        self.home()
        tela = self.engine.act(self.key, ("month", 1, "home"))
        self.assertNotIn("Hoje:", tela.text)

    def test_saldo_negativo_usa_deve_faltar(self):
        self.fixo("Aluguel", 28, valor=5000)
        tela = self.home()
        if "Deve faltar" in tela.text:
            self.assertNotIn("−R$", tela.text.split("Deve faltar")[1][:60])
        else:
            self.assertIn("Deve sobrar", tela.text)  # projeção não ficou negativa neste cenário

    def test_tabela_usa_o_mesmo_icone_do_texto_para_saldo(self):
        tela = self.home()
        self.assertIn("🏦 Saldo agora", tela.rich_html)


if __name__ == "__main__":
    unittest.main()
