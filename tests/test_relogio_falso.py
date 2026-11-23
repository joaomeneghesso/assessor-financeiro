"""Relógio falso dos testes e do modo ``--data`` do gate."""
import datetime as dm
import importlib.util
import time
import unittest
from datetime import date, datetime
from pathlib import Path

import services as svc
import telegram_experiencia as ux
from tests.relogio_fixo import HOJE_PADRAO, data_fixa, relogio

GATE = Path(__file__).resolve().parents[1] / "validacao" / "validar_versao_oficial.py"


class RelogioFalsoTests(unittest.TestCase):
    def test_fixa_hoje_em_modulos_do_projeto_e_restaura(self):
        externo = svc.date.today()
        with data_fixa(date(2028, 2, 29)):
            self.assertEqual(date(2028, 2, 29), svc.date.today())
            self.assertEqual(date(2028, 2, 29), svc.datetime.now().date())
            self.assertEqual(date(2028, 2, 29), dm.date.today())
            self.assertEqual(2028, time.localtime().tm_year)
            self.assertEqual(date(2028, 2, 29), ux.datetime.now(ux.timezone.utc).astimezone().date())
        self.assertEqual(externo, svc.date.today())

    def test_ativacoes_empilham(self):
        externo = date.today()
        with data_fixa(date(2026, 12, 31), "23:30"):
            with data_fixa(date(2027, 1, 1)):
                self.assertEqual(date(2027, 1, 1), svc.date.today())
            self.assertEqual(date(2026, 12, 31), svc.date.today())
            self.assertEqual(23, svc.datetime.now().hour)
        self.assertEqual(externo, date.today())

    def test_isinstance_continua_valendo_para_datas_reais_e_falsas(self):
        with data_fixa(HOJE_PADRAO):
            real = dm.date.today()
            self.assertIsInstance(real, svc.date)
            self.assertIsInstance(svc.date(2026, 1, 1), date)
            self.assertIsInstance(svc.datetime.now(), svc.date)
            self.assertNotIsInstance(svc.date(2026, 1, 1), svc.datetime)
            self.assertEqual("2026-01-02", (svc.date(2026, 1, 1) + dm.timedelta(days=1)).isoformat())

    def test_relogio_anda(self):
        with data_fixa(HOJE_PADRAO):
            a = datetime.now()
            time.sleep(0.01)
            self.assertGreater(svc.datetime.now(), a)

    def test_gate_aceita_data_e_hora(self):
        spec = importlib.util.spec_from_file_location("gate_relogio_sob_teste", GATE)
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        args = gate.criar_parser().parse_args(["--saida", "x", "--data", "2028-02-29", "--hora", "23:30"])
        self.assertEqual(("2028-02-29", "23:30"), (args.data, args.hora))
        self.assertIsNone(gate.criar_parser().parse_args(["--saida", "x"]).data)
        self.assertIn("relogio_falso.ativar_pelo_ambiente()", gate.HARNESS)
        self.assertTrue(relogio.ativo() in (True, False))


if __name__ == "__main__":
    unittest.main()
