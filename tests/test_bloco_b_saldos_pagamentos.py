"""Bloco B: "quanto vou pagar" x fatura paga (B2), saldo por conta x caixa
reconciliado (B6) e caixa com lançamento sem banco (R5).

Cada cenário usa um banco temporário e verifica a correção e a preservação
do comportamento que não deveria mudar.
"""
import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import compromissos as comp
import database as db
import services as svc
import telegram_experiencia as ux


class _BancoTemporario(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        target = Path(self.tmp.name) / "fixture.db"
        for module in (db, svc):
            mocked = patch.object(module, "DB_PATH", target)
            mocked.start()
            self.addCleanup(mocked.stop)
        db.init_db()
        migration_path = Path(__file__).resolve().parents[1] / "migrations" / "0004_competencia_faturas.py"
        spec = importlib.util.spec_from_file_location("fixture_competencia_bloco_b", migration_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with db.get_connection() as conn:
            migration.upgrade(conn)

    def compra(self, mes, valor, conta="Itaú", forma="crédito", descricao="Compra", dia="07"):
        credito = forma == "crédito"
        return db.inserir_transacao({
            "data": f"{mes}-{dia}",
            "tipo": "despesa",
            "valor": valor,
            "categoria": "Outros",
            "descricao": descricao,
            "conta": conta,
            "forma_pagamento": forma,
            "parcelas_total": 1,
            "data_compra": f"{mes}-{dia}" if credito else None,
            "competencia_fatura": mes if credito else None,
        })

    def fixo(self, nome, valor, conta="Itaú", forma="crédito", inicio="2026-09-01", dia=10, tipo="fixo"):
        return db.inserir_compromisso({
            "tipo": tipo,
            "nome": nome,
            "categoria": "Assinaturas",
            "conta_pagamento": conta,
            "forma_pagamento": forma,
            "valor": valor,
            "dia_vencimento": dia,
            "data_inicio": inicio,
            "data_fim": None,
            "parcelas_total": None,
            "ativo": True,
            "origem": "teste",
        })

    def pagamento(self, mes, valor, conta="Itaú", origem="Itaú"):
        return db.inserir_fatura_movimento({
            "ano_mes": mes,
            "conta_cartao": conta,
            "tipo_movimento": "pagamento_total",
            "valor": valor,
            "data_movimento": f"{mes}-27",
            "conta_origem": origem,
            "descricao": "Pagamento da fatura",
        })


class QuantoVouPagarFaturaPagaTests(_BancoTemporario):
    """B2: fixos no crédito fazem parte da fatura antes de abater pagamentos."""

    def test_fatura_paga_inclui_fixos_do_cartao(self):
        self.compra("2026-09", 100.0)
        self.fixo("Streaming", 50.0)
        self.pagamento("2026-09", 150.0)

        unificada = comp.calcular_fatura_unificada("2026-09", "Itaú")
        self.assertAlmostEqual(0.0, unificada["saldo_restante"], places=2)

        resumo = comp.calcular_resumo_pagamento_conta("2026-09", "Itaú")
        self.assertEqual(0.0, resumo["total"])
        self.assertEqual(0.0, resumo["fixos"])
        self.assertEqual(0.0, resumo["fatura"])
        self.assertEqual(0.0, resumo["credito_disponivel"])
        self.assertAlmostEqual(50.0, resumo["fixos_cobertos_fatura"], places=2)

        texto = comp.resumo_pagamento_por_conta("2026-09", "Itaú")
        self.assertIn("TOTAL A PAGAR: R$ 0,00", texto)
        self.assertNotIn("Fixos:", texto)
        self.assertNotIn("Crédito disponível", texto)

        detalhe = comp.detalhar_pagamento_por_conta("2026-09", "Itaú")
        self.assertIn("Streaming: R$ 50,00", detalhe)
        self.assertIn("Coberto pelo pagamento/crédito da fatura: -R$ 50,00", detalhe)
        self.assertIn("TOTAL A PAGAR: R$ 0,00", detalhe)

        consolidado = comp.resumo_pagamento_mes_consolidado("2026-09")
        self.assertIn("Não encontrei pagamentos pendentes", consolidado)

    def test_compromisso_avulso_no_cartao_tambem_e_coberto(self):
        self.compra("2026-09", 100.0)
        self.fixo("Curso", 30.0, tipo="avulso")
        self.pagamento("2026-09", 130.0)

        resumo = comp.calcular_resumo_pagamento_conta("2026-09", "Itaú")
        self.assertEqual(0.0, resumo["total"])
        self.assertEqual(0.0, resumo["compromissos"])
        self.assertAlmostEqual(30.0, resumo["compromissos_cobertos_fatura"], places=2)

    def test_pagamento_parcial_cobre_so_parte_dos_fixos(self):
        self.compra("2026-09", 100.0)
        self.fixo("Streaming", 50.0)
        self.pagamento("2026-09", 120.0)

        resumo = comp.calcular_resumo_pagamento_conta("2026-09", "Itaú")
        unificada = comp.calcular_fatura_unificada("2026-09", "Itaú")
        self.assertAlmostEqual(30.0, resumo["total"], places=2)
        self.assertAlmostEqual(30.0, resumo["fixos"], places=2)
        self.assertEqual(0.0, resumo["fatura"])
        self.assertAlmostEqual(unificada["saldo_restante"], resumo["total"], places=2)

    def test_credito_do_cartao_nao_abate_fixo_pix(self):
        self.compra("2026-09", 100.0)
        self.fixo("Streaming", 50.0)
        self.fixo("Condomínio", 40.0, forma="pix")
        self.pagamento("2026-09", 200.0)

        resumo = comp.calcular_resumo_pagamento_conta("2026-09", "Itaú")
        self.assertAlmostEqual(40.0, resumo["fixos"], places=2)
        self.assertAlmostEqual(40.0, resumo["total"], places=2)
        self.assertAlmostEqual(50.0, resumo["fixos_cobertos_fatura"], places=2)
        self.assertAlmostEqual(50.0, resumo["credito_disponivel"], places=2)
        self.assertAlmostEqual(-50.0, resumo["saldo_fatura"], places=2)

    def test_sem_pagamento_preserva_separacao_fatura_e_fixos(self):
        self.compra("2026-09", 100.0)
        self.fixo("Streaming", 50.0)

        resumo = comp.calcular_resumo_pagamento_conta("2026-09", "Itaú")
        self.assertAlmostEqual(100.0, resumo["fatura"], places=2)
        self.assertAlmostEqual(50.0, resumo["fixos"], places=2)
        self.assertAlmostEqual(150.0, resumo["total"], places=2)
        self.assertAlmostEqual(100.0, resumo["saldo_fatura"], places=2)
        self.assertEqual(0.0, resumo["fixos_cobertos_fatura"])
        texto = comp.resumo_pagamento_por_conta("2026-09", "Itaú")
        self.assertIn("Fatura/cartão: R$ 100,00", texto)
        self.assertIn("Fixos: R$ 50,00", texto)


class SaldoPorContaCaixaReconciliadoTests(_BancoTemporario):
    """B6: saldo por conta herda do caixa reconciliado, sem desconto duplo."""

    def test_conta_sem_caixa_nao_herda_obrigacao_ja_reconciliada(self):
        db.definir_saldo_inicial_conta_mes("2026-09", "Mercado Pago", 1000.0)
        db.definir_saldo_inicial_conta_mes("2026-09", "Nubank", 0.0)
        self.compra("2026-09", 100.0, conta="Nubank")

        setembro = svc.calcular_saldo_mensal("2026-09", "Nubank")
        self.assertAlmostEqual(-100.0, setembro["saldo_projetado"], places=2)

        geral = svc.calcular_saldo_mensal("2026-10")
        caixa = svc.calcular_caixa_por_conta_mes("2026-10")
        mp = svc.calcular_saldo_mensal("2026-10", "Mercado Pago")
        nubank = svc.calcular_saldo_mensal("2026-10", "Nubank")

        self.assertAlmostEqual(900.0, geral["saldo_inicial"], places=2)
        self.assertAlmostEqual(geral["saldo_inicial"], caixa["total_inicial"], places=2)
        self.assertNotIn("Nubank", caixa["contas"])
        self.assertAlmostEqual(900.0, mp["saldo_inicial"], places=2)
        self.assertAlmostEqual(0.0, nubank["saldo_inicial"], places=2)
        self.assertTrue(nubank["saldo_herdado_auto"])
        self.assertAlmostEqual(
            geral["saldo_inicial"], mp["saldo_inicial"] + nubank["saldo_inicial"], places=2,
        )

    def test_conta_presente_no_caixa_continua_usando_caixa(self):
        db.definir_saldo_inicial_conta_mes("2026-09", "Mercado Pago", 1000.0)
        db.definir_saldo_inicial_conta_mes("2026-09", "Caju", 300.0)
        self.compra("2026-09", 50.0, conta="Caju", forma="pix")

        caixa = svc.calcular_caixa_por_conta_mes("2026-10")
        caju = svc.calcular_saldo_mensal("2026-10", "Caju")
        self.assertAlmostEqual(250.0, caixa["contas"]["Caju"]["inicial"], places=2)
        self.assertAlmostEqual(250.0, caju["saldo_inicial"], places=2)

    def test_ajuste_da_heranca_vai_para_maior_saldo_positivo(self):
        db.definir_saldo_inicial_conta_mes("2026-09", "Mercado Pago", 1000.0)
        db.definir_saldo_inicial_conta_mes("2026-09", "Caju", -2000.0)
        self.compra("2026-09", 100.0, conta="Nubank")

        geral_set = svc.calcular_saldo_mensal("2026-09")
        caixa = svc.calcular_caixa_por_conta_mes("2026-10")
        self.assertAlmostEqual(-2000.0, caixa["contas"]["Caju"]["inicial"], places=2)
        self.assertAlmostEqual(900.0, caixa["contas"]["Mercado Pago"]["inicial"], places=2)
        self.assertAlmostEqual(geral_set["saldo_projetado"], caixa["total_inicial"], places=2)

    def test_sem_saldo_positivo_mantem_maior_saldo_absoluto(self):
        db.definir_saldo_inicial_conta_mes("2026-09", "Mercado Pago", -10.0)
        db.definir_saldo_inicial_conta_mes("2026-09", "Caju", -500.0)
        self.compra("2026-09", 100.0, conta="Nubank")

        caixa = svc.calcular_caixa_por_conta_mes("2026-10")
        self.assertAlmostEqual(-10.0, caixa["contas"]["Mercado Pago"]["inicial"], places=2)
        self.assertAlmostEqual(-600.0, caixa["contas"]["Caju"]["inicial"], places=2)

    def test_consolidado_e_centralizadora_nao_mudam(self):
        db.definir_saldo_inicial_conta_mes("2026-09", "Mercado Pago", 1000.0)
        self.compra("2026-09", 100.0, conta="Nubank")
        geral = svc.calcular_saldo_mensal("2026-10")
        itau = svc.calcular_saldo_mensal("2026-10", "Itaú")
        self.assertAlmostEqual(900.0, geral["saldo_inicial"], places=2)
        self.assertEqual(geral["saldo_inicial"], itau["saldo_inicial"])
        self.assertEqual(geral["saldo_projetado"], itau["saldo_projetado"])


class CaixaSemBancoDefinidoTests(_BancoTemporario):
    """R5: lançamento com conta "Pix" fica fora do total por banco, mas o
    caixa mostra o disponível equivalente ao do Meu mês."""

    def test_caixa_explica_total_com_lancamento_sem_banco(self):
        db.definir_saldo_inicial_conta_mes("2026-09", "Itaú", 1000.0)
        self.compra("2026-09", 104.35, conta="Pix", forma="pix")

        caixa = svc.calcular_caixa_por_conta_mes("2026-09")
        geral = svc.calcular_saldo_mensal("2026-09")
        self.assertAlmostEqual(1000.0, caixa["total_disponivel"], places=2)
        self.assertAlmostEqual(895.65, geral["saldo_disponivel"], places=2)

        texto = svc.gerar_caixa_por_conta_mes("2026-09")
        self.assertIn("Disponível em caixa considerando estes lançamentos: R$ 895,65", texto)

        engine = ux.Experience(date_provider=lambda: date(2026, 9, 15))
        tela = engine._cash_accounts_screen("u:r5", "2026-09")
        self.assertIn("Considerando-os: <b>R$ 895,65</b>", tela.text)
        self.assertIn("Considerando-os", tela.rich_html)

    def test_caixa_sem_lancamento_sem_banco_nao_ganha_linha_nova(self):
        db.definir_saldo_inicial_conta_mes("2026-09", "Itaú", 1000.0)
        self.compra("2026-09", 10.0, conta="Itaú", forma="pix")
        texto = svc.gerar_caixa_por_conta_mes("2026-09")
        self.assertNotIn("considerando estes lançamentos", texto)
        tela = ux.Experience(date_provider=lambda: date(2026, 9, 15))._cash_accounts_screen("u:r5b", "2026-09")
        self.assertNotIn("Considerando-os", tela.text)


if __name__ == "__main__":
    unittest.main()
