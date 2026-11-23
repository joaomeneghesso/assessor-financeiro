import unittest
from unittest.mock import patch

import services


class SaldoItauCentralizadoRC1513Tests(unittest.TestCase):
    def setUp(self):
        self.mes = "2026-07"
        self.saldos = {"Itaú": 1000.0, "Nubank": 200.0}
        self.transacoes = []
        self.pagamentos = [
            {"origem": "compromisso", "valor": 100.0, "conta_pagamento": "Itaú", "forma_pagamento": "pix"},
            {"origem": "compromisso", "valor": 300.0, "conta_pagamento": "Nubank", "forma_pagamento": "crédito"},
        ]

    def _patches(self):
        return (
            patch.object(services, "obter_saldos_iniciais_por_conta", return_value=self.saldos),
            patch.object(services, "buscar_transacoes_por_competencia" if hasattr(services, "buscar_transacoes_por_competencia") else "buscar_transacoes_por_mes", return_value=self.transacoes),
            patch.object(services, "listar_fatura_movimentos", return_value=[]),
            patch.object(services, "projetar_entradas_mes", return_value=[]),
            patch.object(services, "projetar_pagamentos_mes", return_value=self.pagamentos),
            # A ponte de caixa agora confere a reserva com a mesma fatura.
            # A projeção sintética de R$ 300 deve ter uma fatura sintética igual.
            patch("compromissos.calcular_fatura_unificada", return_value={"saldo_restante":300.0}),
            patch.object(services, "listar_pendencias_abertas_anteriores", return_value=[]),
        )

    def test_saldo_itau_usa_mesma_ponte_consolidada_de_meu_mes(self):
        patches = self._patches()
        for p in patches: p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(patches)])

        geral = services.calcular_saldo_mensal(self.mes)
        itau = services.calcular_saldo_mensal(self.mes, "Itaú")

        self.assertTrue(itau["saldo_centralizado"])
        self.assertIsNone(itau["conta_filtro_efetivo"])
        self.assertEqual(geral["saldo_inicial"], itau["saldo_inicial"])
        self.assertEqual(geral["despesas_esperadas_total"], itau["despesas_esperadas_total"])
        self.assertEqual(geral["saldo_projetado"], itau["saldo_projetado"])
        self.assertAlmostEqual(800.0, itau["saldo_projetado"], places=2)

    def test_outra_conta_permanece_individual(self):
        patches = self._patches()
        for p in patches: p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(patches)])

        nubank = services.calcular_saldo_mensal(self.mes, "Nubank")

        self.assertFalse(nubank["saldo_centralizado"])
        self.assertEqual("Nubank", nubank["conta_filtro_efetivo"])
        self.assertAlmostEqual(200.0, nubank["saldo_inicial"], places=2)
        self.assertAlmostEqual(300.0, nubank["despesas_esperadas_total"], places=2)
        self.assertAlmostEqual(-100.0, nubank["saldo_projetado"], places=2)

    def test_tela_explica_visao_centralizada(self):
        dados = {
            "saldo_centralizado": True,
            "saldo_herdado_auto": False,
            "saldo_configurado": True,
            "pendencias_herdadas_total": 0.0,
            "saldos_por_conta": {},
            "esperado_por_conta": {},
            "realizado_por_conta": {},
        }
        with patch.object(services, "obter_metricas_resultado_mes", return_value=dados), \
             patch.object(services, "bloco_resultado_mes", return_value="RESULTADO"), \
             patch.object(services, "bloco_caixa_acumulado", return_value="PONTE"):
            texto = services.gerar_saldo_mes_ux(self.mes, "Itaú")

        self.assertIn("Visão centralizada", texto)
        self.assertIn("faturas de outros cartões", texto)


if __name__ == "__main__":
    unittest.main()
