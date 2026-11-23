"""O Menu/Início sempre abre o mês vigente, mesmo depois de uma consulta de outro mês.

Bug relatado: "quanto vou pagar em novembro" gravava o mês na sessão e o /menu
(ou o botão Início) passava a mostrar novembro em vez do mês atual.
"""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import database as db
import services as svc
import telegram_experiencia as ux

HOJE = date(2026, 9, 30)


class MenuMesNaoGrudaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", Path(self.tmp.name) / "fixture.db")
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        self.engine = ux.Experience(date_provider=lambda: HOJE)
        self.key = "teste-menu-mes"

    def mes(self):
        return self.engine.sessions[self.key].month

    def consulta_novembro(self):
        self.engine.act(self.key, ("view", "home"))
        self.assertEqual("2026-09", self.mes())
        self.engine.fast_deterministic_query(self.key, "quanto vou pagar em novembro")
        self.assertEqual("2026-11", self.mes())  # a consulta em si mostra novembro

    def test_botao_inicio_volta_ao_mes_atual(self):
        self.consulta_novembro()
        self.engine.act(self.key, ("view", "home"))
        self.assertEqual("2026-09", self.mes())

    def test_texto_menu_volta_ao_mes_atual(self):
        self.consulta_novembro()
        self.engine.handle_text(self.key, "menu")
        self.assertEqual("2026-09", self.mes())

    def test_navegar_entre_meses_por_botao_continua_preservando_o_mes(self):
        self.engine.act(self.key, ("view", "pay"))
        self.engine.act(self.key, ("month", 1, "pay"))
        self.assertEqual("2026-10", self.mes())
        self.engine.act(self.key, ("month", 1, "pay"))
        self.assertEqual("2026-11", self.mes())


if __name__ == "__main__":
    unittest.main()


class InicioNavegaMesesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", Path(self.tmp.name) / "fixture.db")
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        self.engine = ux.Experience(date_provider=lambda: HOJE)
        self.key = "teste-inicio-meses"

    def acoes(self, tela):
        return [a for linha in tela.rows for _, a in linha]

    def test_inicio_oferece_proximo_mes_e_mes_anterior(self):
        tela = self.engine.act(self.key, ("view", "home"))
        acoes = self.acoes(tela)
        self.assertIn(("month", 1, "home"), acoes)
        self.assertIn(("month", -1, "home"), acoes)
        self.assertNotIn(("current_month", "home"), acoes)  # já está no mês atual

    def test_proximo_mes_mostra_projecao_e_oferece_voltar(self):
        self.engine.act(self.key, ("view", "home"))
        tela = self.engine.act(self.key, ("month", 1, "home"))
        self.assertEqual("2026-10", self.engine.sessions[self.key].month)
        self.assertIn("Outubro 2026", tela.text)
        self.assertIn("Previsão para o mês selecionado", tela.text)
        self.assertIn(("current_month", "home"), self.acoes(tela))
        tela = self.engine.act(self.key, ("current_month", "home"))
        self.assertEqual("2026-09", self.engine.sessions[self.key].month)

    def test_navegar_varios_meses_para_frente_e_voltar_ao_menu(self):
        self.engine.act(self.key, ("view", "home"))
        for _ in range(3):
            self.engine.act(self.key, ("month", 1, "home"))
        self.assertEqual("2026-12", self.engine.sessions[self.key].month)
        self.engine.act(self.key, ("view", "home"))
        self.assertEqual("2026-09", self.engine.sessions[self.key].month)

    def test_atualizar_nos_detalhes_nao_perde_o_mes_projetado(self):
        self.engine.act(self.key, ("view", "home"))
        self.engine.act(self.key, ("month", 1, "home"))
        self.engine.act(self.key, ("view", "month_actions"))
        # view abre outra tela sem mexer no mês (só Início volta ao mês vigente)
        self.assertEqual("2026-10", self.engine.sessions[self.key].month)
        self.engine.act(self.key, ("month", 0, "month_actions"))
        self.assertEqual("2026-10", self.engine.sessions[self.key].month)
