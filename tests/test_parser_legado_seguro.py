"""Texto livre pelo caminho legado (grava sem prévia) e valores com "mil".

Cada correção é testada junto com o que precisa continuar igual:
- fatura em texto livre não vira despesa, mas os comandos oficiais de fatura
  (pagar, pagar restante, estorno, consultar) seguem funcionando;
- "caiu" com verbo de gasto deixa de virar receita, mas "caiu 500 na conta",
  "salário 4000" e "recebi ..." continuam receita;
- conta por palavra inteira, sem perder "no itaú", "mercado pago", "mp";
- "1,5 mil" / "2 mil reais" e "X reais e Y centavos" no legado e no registro
  com prévia, sem mudar valores comuns, parcelas ou datas completas;
- data "dd/mm" sem ano é recusada (como no registro do Telegram), sem bloquear
  datas completas nem a notação de parcela "(3/10)".
"""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import compromissos
import database as db
import parser_financeiro as pf
import services as svc
import telegram_experiencia as ux
from registro_conversa import extrair_campos
from tests.relogio_fixo import data_fixa

HOJE = date(2026, 10, 13)


def parse(texto):
    return pf.parse_mensagem(texto, data_referencia=HOJE)


class ParserLegadoTests(unittest.TestCase):
    def campos(self, texto, *nomes):
        r = parse(texto)
        return tuple(r.get(n) for n in nomes)

    def test_valores_comuns_inalterados(self):
        casos = {
            "gastei 45,90 no mercado": 45.9,
            "gastei 1.234,56 no mercado": 1234.56,
            "uber 23": 23.0,
            "gastei R$ 80 de luz": 80.0,
            "gastei 197 reais no mercado": 197.0,
            "gastei vinte reais no lanche": 20.0,
            "gastei cem reais": 100.0,
            "comprei tv em 10x de 300": 3000.0,
            "comprei notebook 1200 em 12x": 1200.0,
            "gastei 100 em 13/10/2026": 100.0,
            "gastei 100 em 2026-10-01": 100.0,
        }
        for texto, valor in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(valor, parse(texto)["valor"])

    def test_multiplicador_mil(self):
        casos = {
            "gastei 1,5 mil no mercado": (1500.0, "Mercado"),
            "gastei 2 mil reais no aluguel": (2000.0, "Aluguel"),
            "mercado 1,5 mil": (1500.0, "Mercado"),
            "R$ 2 mil de aluguel": (2000.0, "Aluguel"),
            "ganhei 1 milhão": (1000000.0, None),
        }
        for texto, (valor, descricao) in casos.items():
            with self.subTest(texto=texto):
                r = parse(texto)
                self.assertEqual(valor, r["valor"])
                if descricao:
                    self.assertEqual(descricao, r["descricao"])
                self.assertNotIn("mil ", r["descricao"].lower() + " ")

    def test_mil_de_outra_parte_da_frase_nao_vira_valor(self):
        casos = {
            "manutenção 10 mil km R$ 450": (450.0, "Manutenção 10 mil km"),
            "R$ 450 revisão 10 mil km": (450.0, "Revisão 10 mil km"),
            "gastei R$ 50 na loja 2 mil": (50.0, None),
            "gastei 40 com 1 mil adesivos": (40.0, None),
        }
        for texto, (valor, descricao) in casos.items():
            with self.subTest(texto=texto):
                r = parse(texto)
                self.assertEqual(valor, r["valor"])
                if descricao:
                    self.assertEqual(descricao, r["descricao"])

    def test_reais_e_centavos(self):
        self.assertEqual((23.5, "Uber"), self.campos("uber 23 reais e 50 centavos", "valor", "descricao"))
        self.assertEqual(10.05, parse("recebi 10 reais e 5 centavos")["valor"])
        self.assertEqual(197.99, parse("Gastei 197 reais e 99 centavos no mercado")["valor"])

    def test_tipo(self):
        self.assertEqual("receita", parse("caiu 500 na conta")["tipo"])
        self.assertEqual("receita", parse("caiu o salario 3000")["tipo"])
        self.assertEqual("receita", parse("salario 4000")["tipo"])
        self.assertEqual("receita", parse("pix recebido 200")["tipo"])
        self.assertEqual("receita", parse("recebi 500 de salario")["tipo"])
        self.assertEqual("despesa", parse("paguei 50 de adiantamento do salario")["tipo"])
        self.assertEqual("despesa", parse("almoco 35")["tipo"])
        r = parse("o celular caiu e gastei 300 no conserto")
        self.assertEqual(("mensagem_bloqueada", "tipo_ambiguo"), (r.get("erro"), r.get("motivo")))

    def test_conta_por_palavra_inteira(self):
        self.assertIsNone(parse("gastei 15 na drogaria internacional")["conta"])
        self.assertIsNone(parse("gastei 50 no expresso")["conta"])
        self.assertIsNone(parse("Internet: R$ 90,00")["conta"])
        self.assertEqual("Inter", parse("gastei 15 no inter")["conta"])
        self.assertEqual("Itaú", parse("almoco 35 no itaú")["conta"])
        self.assertEqual("Itaú", parse("almoco 35 no itau")["conta"])
        self.assertEqual("Mercado Pago", parse("almoco 35 no mercado pago")["conta"])
        self.assertEqual("Mercado Pago", parse("almoco 35 no mp hoje")["conta"])
        self.assertEqual("Nubank", parse("gastei 45,90 no mercado com nubank")["conta"])
        self.assertEqual("Banco do Brasil", parse("gastei 30 no bb")["conta"])
        self.assertEqual("Pix", parse("paguei 80 de luz pelo pix")["conta"])
        self.assertEqual("C6", parse("gastei 50 c6bank")["conta"])
        self.assertEqual("C6", parse("gastei 50 no c6")["conta"])
        self.assertEqual("Mercado Pago", parse("gastei 30 no mercadopago")["conta"])

    def test_datas(self):
        self.assertEqual("2026-10-12", parse("gastei 50 ontem")["data"])
        self.assertEqual("2026-10-13", parse("gastei 50 no mercado")["data"])
        self.assertEqual("2026-10-01", parse("gastei 100 em 01/10/2026")["data"])
        self.assertEqual("2026-10-13", parse("Notebook (3/10) 200")["data"])
        # Fase 2 (P2): data curta assume o ano corrente (nunca futura).
        self.assertEqual("2026-10-05", parse("gastei 50 no mercado dia 05/10")["data"])
        self.assertIsNone(parse("25/09"))
        r = parse("gastei 50 no mercado dia 05/12")
        self.assertEqual(("mensagem_bloqueada", "data_futura"), (r.get("erro"), r.get("motivo")))


class RegistroComPreviaTests(unittest.TestCase):
    def extrair(self, texto):
        return extrair_campos(texto, hoje=HOJE, contas=["Itaú", "Nubank"])

    def test_mil_no_registro_com_previa(self):
        casos = {
            "gastei 1,5 mil no mercado": (1500.0, "mercado"),
            "gastei 2 mil reais no aluguel": (2000.0, "aluguel"),
            "gastei R$ 2 mil de aluguel": (2000.0, "aluguel"),
            "comprei sofa por 3 mil": (3000.0, "sofa"),
        }
        for texto, (valor, descricao) in casos.items():
            with self.subTest(texto=texto):
                c = self.extrair(texto)
                self.assertEqual(valor, c["valor"])
                self.assertEqual(descricao, c["descricao"].lower())

    def test_valores_existentes_inalterados(self):
        self.assertEqual(197.99, self.extrair("gastei 197 reais e 99 centavos no mercado")["valor"])
        self.assertEqual(45.9, self.extrair("gastei 45,90 no mercado")["valor"])
        self.assertEqual(5000.0, self.extrair("comprei iphone 15 por 5000")["valor"])
        self.assertEqual(1234.56, self.extrair("gastei 1.234,56 no mercado")["valor"])
        c = self.extrair("comprei tv em 10x de 300 no credito")
        self.assertEqual((3000.0, 10), (c["valor"], c["parcelas_total"]))
        with self.assertRaises(ValueError):
            self.extrair("gastei 50 e 30 no mercado")


class FluxoTextoLivreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", Path(self.tmp.name) / "fixture.db")
            p.start()
            self.addCleanup(p.stop)
        # processar_mensagem não recebe data de referência: o parser cai em date.today().
        # Sem fixar o dia, estes testes passam a depender do corte do cartão (dia 25).
        class _DataFixa(date):
            @classmethod
            def today(cls):
                return HOJE

        p = patch.object(pf, "date", _DataFixa)
        p.start()
        self.addCleanup(p.stop)
        # O resto da produção (competência, conciliação) também lê "hoje".
        self.enterContext(data_fixa(HOJE))
        db.init_db()
        db.inserir_transacao(dict(data="2026-10-05", tipo="despesa", valor=100, categoria="Compras",
                                  descricao="Loja", conta="Nubank", forma_pagamento="crédito"))

    def total_transacoes(self):
        with db.get_connection() as c:
            return c.execute("SELECT count(*) FROM transacoes").fetchone()[0]

    def fatura(self):
        return compromissos.calcular_fatura_unificada("2026-10", "Nubank", somente_cartao=True)

    def test_fatura_em_texto_livre_nao_vira_despesa(self):
        antes = self.fatura()["valor_bruto"]
        for texto in ("paguei a fatura de 100 do nubank", "paguei fatura nubank 100", "nubank paguei fatura 100",
                      "paguei as faturas do nubank 500", "pagamento fatura nubank 100"):
            with self.subTest(texto=texto):
                resposta = svc.processar_mensagem(texto, sessao="t")
                self.assertIn("Nada foi registrado", resposta)
                self.assertEqual(1, self.total_transacoes())
                self.assertEqual(antes, self.fatura()["valor_bruto"])

    def registrar(self, texto):
        """Onda 2: texto livre no núcleo mostra prévia; só grava ao confirmar."""
        antes = self.total_transacoes()
        previa = svc.processar_mensagem(texto, sessao="t")
        self.assertIn("Responda: confirmar alteracao", previa, texto)
        self.assertEqual(antes, self.total_transacoes(), texto)
        return svc.processar_mensagem("confirmar alteracao", sessao="t")

    def test_despesas_que_so_citam_a_fatura_continuam_registrando(self):
        for texto in ("paguei 15 de juros da fatura do nubank", "anuidade da fatura 30",
                      "iof 12 na fatura itau", "tenis 300 no credito nubank vem na proxima fatura"):
            with self.subTest(texto=texto):
                antes = self.total_transacoes()
                resposta = self.registrar(texto)
                self.assertIn("Despesa registrada", resposta)
                self.assertEqual(antes + 1, self.total_transacoes())

    def test_telegram_entrega_fatura_ao_caminho_legado(self):
        # A tela nativa devolve None e o host chama processar_mensagem.
        engine = ux.Experience(date_provider=lambda: HOJE)
        self.assertIsNone(engine.handle_text("k", "paguei a fatura de 100 do nubank"))

    def test_comandos_oficiais_de_fatura_continuam(self):
        consulta = svc.processar_mensagem("fatura nubank 2026-10", sessao="t")
        self.assertIn("R$ 100,00", consulta)
        # Movimentos de fatura por texto mostram prévia e só gravam com a
        # confirmação própria ("confirmar estorno" / "confirmar pagamento").
        estorno = svc.processar_mensagem("estorno de 10 na fatura nubank 2026-10", sessao="t")
        self.assertIn("Nada foi registrado ainda", estorno)
        estorno = svc.processar_mensagem("confirmar estorno", sessao="t")
        self.assertIn("Movimento de fatura registrado", estorno)
        pago = svc.processar_mensagem("paguei 50 da fatura nubank usando itau 2026-10", sessao="t")
        self.assertIn("Nada foi registrado ainda", pago)
        pago = svc.processar_mensagem("confirmar pagamento", sessao="t")
        self.assertIn("Movimento de fatura registrado", pago)
        resto = svc.processar_mensagem("paguei o restante da fatura nubank usando itau 2026-10", sessao="t")
        self.assertIn("Nada foi registrado ainda", resto)
        resto = svc.processar_mensagem("confirmar pagamento", sessao="t")
        self.assertIn("Movimento de fatura registrado", resto)
        r = self.fatura()
        self.assertEqual(("paga", 0.0), (r["status"], r["saldo_restante"]))
        self.assertEqual(1, self.total_transacoes())

    def test_texto_livre_normal_continua_registrando(self):
        resposta = self.registrar("mercado 1,5 mil")
        self.assertIn("Despesa registrada", resposta)
        self.assertIn("R$ 1.500,00", resposta)
        resposta = self.registrar("caiu 500 na conta")
        self.assertIn("registrad", resposta.lower())
        with db.get_connection() as c:
            linhas = c.execute("SELECT tipo, valor FROM transacoes ORDER BY id").fetchall()
        self.assertEqual([("despesa", 100.0), ("despesa", 1500.0), ("receita", 500.0)], [tuple(x) for x in linhas])

    def test_ambiguos_e_data_sem_ano_nao_gravam(self):
        r = svc.processar_mensagem("o celular caiu e gastei 300 no conserto", sessao="t")
        self.assertIn("entrada ou uma saída", r)
        r = svc.processar_mensagem("mercado 50 dia 31/02", sessao="t")  # data inexistente
        self.assertIn("Nada foi registrado", r)
        self.assertEqual(1, self.total_transacoes())

    def test_simular_continua_funcionando(self):
        r = svc.processar_mensagem("simular comprei sofa 3 mil em 10x", sessao="t")
        self.assertIn("3.000,00", r)
        self.assertEqual(1, self.total_transacoes())


if __name__ == "__main__":
    unittest.main()
