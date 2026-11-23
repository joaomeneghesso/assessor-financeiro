"""Parser legado: valor errado silencioso, data ignorada, categoria explicita
sobrescrita e falsos positivos de comando/codigo (BUGS_CONHECIDOS P0.3 / P1)."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import database as db
import parser_financeiro as pf
import services as svc

HOJE = date(2026, 10, 13)


def parse(texto):
    return pf.parse_mensagem(texto, data_referencia=HOJE)


class ValorTests(unittest.TestCase):
    def test_preco_e_nao_numero_do_item(self):
        casos = {
            "comprei iphone 15 por 5000 em 10x": (5000.0, 10),
            "comprei iphone 15 por 5000": (5000.0, 1),
            "comprei galaxy s24 custou 4200": (4200.0, 1),
            "comprei ps5 2 controles por R$ 600": (600.0, 1),
        }
        for texto, (valor, parcelas) in casos.items():
            with self.subTest(texto=texto):
                r = parse(texto)
                self.assertEqual((valor, parcelas), (r["valor"], r["parcelas_total"]))

    def test_mil_e_centenas(self):
        casos = {
            "gastei 3 mil e 500 reais no aluguel": 3500.0,
            "gastei 1 mil e 500 no aluguel": 1500.0,
            "recebi 2 mil e 250": 2250.0,
        }
        for texto, valor in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(valor, parse(texto)["valor"])
        self.assertEqual("Aluguel", parse("gastei 3 mil e 500 reais no aluguel")["descricao"])

    def test_dois_valores_sao_recusados(self):
        for texto in ("gastei 10,00 e 20,00 no mercado", "gastei R$ 10 e R$ 20 no mercado"):
            with self.subTest(texto=texto):
                r = parse(texto)
                self.assertEqual(("mensagem_bloqueada", "mais_de_um_valor"), (r.get("erro"), r.get("motivo")))

    def test_valores_comuns_seguem(self):
        self.assertEqual(40.0, parse("gastei 40 com 1 mil adesivos")["valor"])
        self.assertEqual(23.5, parse("uber 23 reais e 50 centavos")["valor"])
        self.assertEqual(3000.0, parse("comprei tv em 10x de 300")["valor"])


class DataTests(unittest.TestCase):
    def test_formatos_de_data(self):
        casos = {
            "gastei 50 no mercado 05/10/26": "2026-10-05",
            "gastei 50 no mercado 05-10-2026": "2026-10-05",
            "gastei 50 no mercado 5/10/2026": "2026-10-05",
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                r = parse(texto)
                self.assertEqual(esperado, r["data"])
                self.assertEqual(50.0, r["valor"])
                self.assertEqual("Mercado", r["descricao"])

    def test_amanha_e_recusado(self):
        for texto in ("gastei 50 no mercado amanhã", "gastei 50 no mercado amanha"):
            with self.subTest(texto=texto):
                r = parse(texto)
                self.assertEqual(("mensagem_bloqueada", "data_futura"), (r.get("erro"), r.get("motivo")))

    def test_data_invalida_recusada(self):
        r = parse("gastei 50 no mercado 31/02/26")
        self.assertEqual("valor_ou_data_invalida", r.get("motivo"))


class FluxoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", Path(self.tmp.name) / "fixture.db")
            p.start()
            self.addCleanup(p.stop)

        class _DataFixa(date):
            @classmethod
            def today(cls):
                return HOJE

        p = patch.object(pf, "date", _DataFixa)
        p.start()
        self.addCleanup(p.stop)
        db.init_db()

    def linhas(self):
        with db.get_connection() as c:
            return [tuple(x) for x in c.execute(
                "SELECT valor, categoria, data FROM transacoes ORDER BY id").fetchall()]

    def registrar(self, texto):
        """Onda 2: texto livre no núcleo mostra prévia; só grava ao confirmar."""
        antes = self.linhas()
        previa = svc.processar_mensagem(texto, sessao="t")
        self.assertIn("Responda: confirmar alteracao", previa, texto)
        self.assertEqual(antes, self.linhas(), texto)
        return svc.processar_mensagem("confirmar alteracao", sessao="t")

    def test_categoria_explicita_e_respeitada(self):
        r = self.registrar("gastei 50 no uber categoria Lazer")
        self.assertIn("registrada", r)
        self.assertEqual([(50.0, "Lazer", "2026-10-13")], self.linhas())

    def test_sem_categoria_explicita_segue_inferindo(self):
        self.registrar("gastei 50 no uber")
        self.assertEqual("Transporte", self.linhas()[0][1])

    def test_recusas_nao_gravam(self):
        for texto in ("gastei 10,00 e 20,00 no mercado", "gastei 50 no mercado amanhã"):
            with self.subTest(texto=texto):
                r = svc.processar_mensagem(texto, sessao="t")
                self.assertIn("Nada foi registrado", r)
        self.assertEqual([], self.linhas())

    def test_data_com_ano_curto_grava_na_data(self):
        self.registrar("gastei 50 no mercado 05/10/26")
        self.assertEqual("2026-10-05", self.linhas()[0][2])

    def test_falsos_positivos_de_comando_registram(self):
        casos = ["guia IPTU 300", "caixa de som 200", "hoje gastei 40 na padaria",
                 "metade da conta do jantar 80", "agendei corte de cabelo 60",
                 "compra online 80", "masterclass 90"]
        for texto in casos:
            with self.subTest(texto=texto):
                antes = len(self.linhas())
                r = self.registrar(texto)
                self.assertIn("registrada", r, texto)
                self.assertEqual(antes + 1, len(self.linhas()))

    def test_comandos_continuam_protegidos(self):
        for texto in ("guia", "caixa", "meu caixa", "hoje", "saldo 500", "meta 500", "apagar fixo xyz 40",
                      "contas 2026-7", "entradas 2026-13"):
            with self.subTest(texto=texto):
                svc.processar_mensagem(texto, sessao="t")
                self.assertEqual([], self.linhas(), texto)

    def test_codigo_real_segue_bloqueado(self):
        for texto in ("def f(): return 1", "import os", "select * from x", "class A: pass"):
            with self.subTest(texto=texto):
                self.assertEqual(("mensagem_bloqueada", "codigo_ou_texto_longo"),
                                 (parse(texto).get("erro"), parse(texto).get("motivo")))


if __name__ == "__main__":
    unittest.main()
