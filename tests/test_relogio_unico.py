"""Relógio único (Onda 3, etapa 1D): ``relogio.py`` e compatibilidade com os relógios de teste."""
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import conciliacao
import relogio
import telegram_experiencia as ux
from tests.relogio_fixo import data_fixa


class RelogioUnicoTest(unittest.TestCase):
    def test_data_fixa_muda_relogio_e_quem_usa(self):
        with data_fixa(date(2027, 1, 1), "10:00"):
            self.assertEqual(relogio.hoje(), date(2027, 1, 1))
            self.assertEqual(relogio.mes_atual(), "2027-01")
            self.assertEqual(relogio.agora().date(), date(2027, 1, 1))
            self.assertEqual(conciliacao._hoje(), date(2027, 1, 1))
            self.assertEqual(ux.today(), date(2027, 1, 1))
        with data_fixa(date(2028, 2, 29), "09:30"):
            self.assertEqual(relogio.hoje(), date(2028, 2, 29))
            self.assertEqual(relogio.mes_atual(), "2028-02")

    def test_fuso_unico_utc_menos_3(self):
        self.assertEqual(relogio.FUSO.utcoffset(None), timedelta(hours=-3))
        self.assertIsNone(relogio.agora().tzinfo)
        self.assertEqual(relogio.agora_com_fuso().utcoffset(), timedelta(hours=-3))

    def test_virada_do_dia_segue_utc_menos_3(self):
        instante = datetime(2026, 11, 1, 2, 30, tzinfo=timezone.utc)  # 31/10 23:30 em Brasília

        class Relogio(datetime):
            @classmethod
            def now(cls, tz=None):
                return instante.astimezone(tz)

        with patch.object(relogio, "datetime", Relogio):
            self.assertEqual(relogio.hoje(), date(2026, 10, 31))
            self.assertEqual(relogio.agora(), datetime(2026, 10, 31, 23, 30))
            self.assertEqual(relogio.mes_atual(), "2026-10")

    def test_respeita_substituto_do_modulo_chamador(self):
        class Hoje(date):
            @classmethod
            def today(cls):
                return cls(2024, 2, 29)

        self.assertEqual(relogio.hoje(Hoje), date(2024, 2, 29))
        self.assertEqual(relogio.hoje(date), relogio.hoje())
        self.assertEqual(relogio.hoje(fonte_datahora=datetime), relogio.hoje())

    def test_experience_date_provider_continua_mandando(self):
        engine = ux.Experience(date_provider=lambda: date(2026, 9, 30))
        self.assertEqual(engine.date_provider(), date(2026, 9, 30))


if __name__ == "__main__":
    unittest.main()
