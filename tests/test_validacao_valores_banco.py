"""A camada de banco recusa valores monetários inválidos (auditoria D4/D7/D10).

Antes, `inserir_transacao` gravava -50, inf, nan, "abc" e 1e300; "abc" derrubava
os cálculos depois e inf aparecia como "R$ inf". A transferência aceitava a data
inexistente 2026-02-30.

Conta à mão do cenário da auditoria: base do Itaú 1000; despesas de 100 e de -50.
Sem validação: saídas = 100 + (-50) = 50 e disponível = 1000 - 50 = 950 (errado,
o -50 "devolve" dinheiro). Correto: o -50 é recusado, saídas = 100 e
disponível = 1000 - 100 = 900.

Sempre em banco temporário.
"""
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import database as db
import services as svc

INVALIDOS = (-50, float("inf"), float("-inf"), float("nan"), "abc", 1e300, True, None, 1_000_000_000)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = Path(self.tmp.name) / "fixture.db"
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", path)
            p.start()
            self.addCleanup(p.stop)
        db.init_db()

    def qtd(self, tabela):
        with db.get_connection() as c:
            return c.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]

    def valores(self, tabela, coluna="valor"):
        with db.get_connection() as c:
            return [Decimal(str(r[0])) for r in c.execute(f"SELECT {coluna} FROM {tabela} ORDER BY rowid").fetchall()]

    def transacao(self, valor):
        return dict(data="2026-10-05", tipo="despesa", valor=valor, categoria="Outros", descricao="x",
                    conta="Itaú", forma_pagamento="pix", mensagem_original="x")

    def compromisso(self, valor):
        return dict(tipo="fixo", nome="Aluguel", categoria="Moradia", conta_pagamento="Itaú",
                    forma_pagamento="pix", valor=valor, dia_vencimento=10, data_inicio="2026-10-01",
                    data_fim=None, ativo=True)


class TransacaoTests(Base):
    def test_recusa_valores_invalidos_sem_gravar(self):
        for valor in INVALIDOS + (0, 0.0):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    db.inserir_transacao(self.transacao(valor))
        self.assertEqual(0, self.qtd("transacoes"))

    def test_parcelamento_atomico_recusa_e_nao_grava_nada(self):
        with self.assertRaises(ValueError):
            db.inserir_parcelamento_atomico([self.transacao(10), self.transacao(-5)])
        self.assertEqual(0, self.qtd("transacoes"))

    def test_aceita_validos(self):
        db.inserir_transacao(self.transacao(0.01))
        db.inserir_transacao(self.transacao("1.234,56"))
        db.inserir_transacao(self.transacao(999_999_999.99))
        db.inserir_transacao(self.transacao(Decimal("10.005")))
        self.assertEqual([Decimal("0.01"), Decimal("1234.56"), Decimal("999999999.99"), Decimal("10.01")],
                         self.valores("transacoes"))

    def test_float_derivado_arredonda_a_duas_casas(self):
        db.inserir_transacao(self.transacao(0.1 + 0.2))
        db.inserir_transacao(self.transacao(100 / 3))
        self.assertEqual([Decimal("0.30"), Decimal("33.33")], self.valores("transacoes"))


class CompromissoTests(Base):
    def test_recusa_invalidos_e_negativo(self):
        for valor in INVALIDOS:
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    db.inserir_compromisso(self.compromisso(valor))
        self.assertEqual(0, self.qtd("compromissos"))

    def test_aceita_valor_e_zero(self):
        db.inserir_compromisso(self.compromisso(231.45))
        db.inserir_compromisso(self.compromisso(0))
        self.assertEqual([Decimal("231.45"), Decimal("0.00")], self.valores("compromissos"))

    def test_atualizar_valor_compromisso_recusa_invalidos(self):
        cid = db.inserir_compromisso(self.compromisso(100))
        for valor in INVALIDOS:
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    db.atualizar_valor_compromisso(cid, valor)
        self.assertEqual([Decimal("100.00")], self.valores("compromissos"))
        db.atualizar_valor_compromisso(cid, 150.5)
        self.assertEqual([Decimal("150.50")], self.valores("compromissos"))


class SaldoTests(Base):
    def test_saldo_conta_recusa_invalidos(self):
        for valor in (float("inf"), float("nan"), "abc", 1e300, True, None, 1_000_000_000, -1_000_000_000):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    db.definir_saldo_inicial_conta_mes("2026-10", "Itaú", valor)
        self.assertEqual(0, self.qtd("saldos_mensais_contas"))

    def test_saldo_conta_aceita_negativo_zero_e_teto(self):
        db.definir_saldo_inicial_conta_mes("2026-10", "Itaú", -200.00)
        db.definir_saldo_inicial_conta_mes("2026-10", "Inter", 0)
        db.definir_saldo_inicial_conta_mes("2026-10", "C6", 999_999_999.99)
        self.assertEqual([Decimal("-200.00"), Decimal("0.00"), Decimal("999999999.99")],
                         self.valores("saldos_mensais_contas", "saldo_inicial"))

    def test_saldo_mensal_geral(self):
        for valor in (float("inf"), float("nan"), "abc", 1e300, True, None):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    db.definir_saldo_inicial_mes("2026-10", valor)
        self.assertEqual(0, self.qtd("saldos_mensais"))
        db.definir_saldo_inicial_mes("2026-10", -200.00)
        self.assertEqual([Decimal("-200.00")], self.valores("saldos_mensais", "saldo_inicial"))


class TransferenciaTests(Base):
    def transferencia(self, valor=100, data="2026-10-05"):
        return dict(data=data, valor=valor, conta_origem="Itaú", conta_destino="Inter",
                    descricao="t", mensagem_original="t")

    def test_recusa_valor_invalido(self):
        for valor in INVALIDOS + (0,):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    db.inserir_transferencia_caixa(self.transferencia(valor))
        self.assertEqual(0, self.qtd("transferencias_caixa"))

    def test_recusa_data_inexistente(self):
        for data in ("2026-02-30", "2026-13-01", "abc", "", None):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    db.inserir_transferencia_caixa(self.transferencia(data=data))
        self.assertEqual(0, self.qtd("transferencias_caixa"))

    def test_aceita_valida(self):
        db.inserir_transferencia_caixa(self.transferencia(0.01))
        db.inserir_transferencia_caixa(self.transferencia("1.234,56", "2026-02-28"))
        self.assertEqual([Decimal("0.01"), Decimal("1234.56")], self.valores("transferencias_caixa"))


class MetaTests(Base):
    def test_meta_recusa_invalidos(self):
        for valor in INVALIDOS:
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    db.definir_meta("Alimentação", valor)
        self.assertEqual(0, self.qtd("metas"))


class CenarioAuditoriaTests(Base):
    def test_despesa_negativa_recusada_nao_altera_saidas_nem_disponivel(self):
        db.definir_saldo_inicial_conta_mes("2026-10", "Itaú", 1000)
        db.inserir_transacao(self.transacao(100))
        with self.assertRaises(ValueError):
            db.inserir_transacao(self.transacao(-50))
        m = svc.obter_metricas_resultado_mes("2026-10")
        self.assertEqual(Decimal("100"), Decimal(str(m["saidas_imediatas_realizadas"])))
        self.assertEqual(Decimal("900"), Decimal(str(m["saldo_disponivel"])))

    def test_transferencia_texto_com_data_inexistente_responde_sem_gravar(self):
        """D7: "transferi 100 do Itaú para Nubank em 2026-02-30" gravava a data."""
        texto = svc.registrar_transferencia_caixa_formatado("transferi 100 do Itaú para Nubank em 2026-02-30")
        self.assertIn("Não registrei a transferência", texto)
        self.assertEqual(0, self.qtd("transferencias_caixa"))


if __name__ == "__main__":
    unittest.main()
