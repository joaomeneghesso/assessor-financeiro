"""D08 das jornadas: "quanto vou pagar em janeiro" (hoje = 09/11/2026)
respondia janeiro de 2026, no passado, com R$ 0,00.

Regra nova: em consulta de pagamento/recebimento futuro, mês sem ano é a
próxima ocorrência (janeiro → 2027-01; dezembro → 2026-12); "mês que vem" é
o mês seguinte; consultas sobre o passado ("quanto gastei em janeiro")
continuam no ano corrente. O cabeçalho mostra o mês e o ano interpretados.
Banco temporário.
"""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import database as db
import services as svc
import telegram_experiencia as ux

HOJE = date(2026, 11, 9)


class MesSemAnoFuturo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", Path(self.tmp.name) / "f.db"); p.start(); self.addCleanup(p.stop)
        db.init_db()
        self.engine = ux.Experience(date_provider=lambda: HOJE)

    def test_interpretacao_do_mes(self):
        mes = self.engine._month_from_text
        self.assertEqual(mes("quanto vou pagar em janeiro"), "2027-01")   # antes: 2026-01
        self.assertEqual(mes("quanto pagar em março"), "2027-03")
        self.assertEqual(mes("quanto vou pagar em dezembro"), "2026-12")
        self.assertEqual(mes("quanto vou pagar em novembro"), "2026-11")
        self.assertEqual(mes("quanto vou pagar mês que vem"), "2026-12")   # antes: None
        self.assertEqual(mes("quanto vou pagar em janeiro de 2026"), "2026-01")
        self.assertEqual(mes("quanto gastei em janeiro"), "2026-01")

    def test_cabecalho_mostra_mes_e_ano(self):
        # Mesmo caminho do texto livre no bot (dispatch_text → fast_deterministic_query).
        tela = self.engine.fast_deterministic_query("t-mes", "quanto vou pagar em janeiro")
        self.assertIn("JANEIRO 2027", tela.text.upper())   # antes: JANEIRO 2026


if __name__ == "__main__":
    unittest.main()
