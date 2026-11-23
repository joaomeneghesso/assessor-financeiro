import unittest
from unittest.mock import patch

import compromissos
import services


class TestRC1511FaturaFonteUnica(unittest.TestCase):
    def setUp(self):
        self.transacao_real = {
            "origem": "transacao", "tipo": "transacao", "id": 100,
            "nome": "Compras Itaú", "categoria": "Cartão",
            "conta_pagamento": "Itaú", "forma_pagamento": "crédito",
            "valor": 872.06, "data": "2026-07-10",
        }
        self.recorrentes_credito = [
            {
                "origem": "compromisso", "tipo": "fixo", "id": 1,
                "nome": "Wellhub", "categoria": "Assinaturas",
                "conta_pagamento": "Itaú", "forma_pagamento": "crédito",
                "valor": 91.70, "data": "2026-07-05",
            },
            {
                "origem": "compromisso", "tipo": "fixo", "id": 2,
                "nome": "Plano de celular", "categoria": "Telefonia",
                "conta_pagamento": "Itaú", "forma_pagamento": "crédito",
                "valor": 50.00, "data": "2026-07-10",
            },
            {
                "origem": "compromisso", "tipo": "fixo", "id": 3,
                "nome": "YouTube Premium", "categoria": "Assinaturas",
                "conta_pagamento": "Itaú", "forma_pagamento": "crédito",
                "valor": 13.13, "data": "2026-07-12",
            },
        ]
        self.credito = [{
            "id": 1, "conta_cartao": "Itaú", "tipo_movimento": "credito",
            "valor": 235.43, "descricao": "Reembolso", "data_movimento": "2026-07-15",
            "conta_origem": None,
        }]

    def _patch_base(self, itens):
        return (
            patch.object(compromissos, "obter_itens_base_pagamentos_mes", return_value=itens),
            patch.object(compromissos, "listar_fatura_movimentos", return_value=self.credito),
            patch.object(compromissos, "obter_primeira_competencia_financeira", return_value="2026-07"),
        )

    def test_fatura_real_preserva_previsoes_de_outros_itens(self):
        p1, p2, p3 = self._patch_base([self.transacao_real, *self.recorrentes_credito])
        with p1, p2, p3:
            resumo = compromissos.calcular_fatura_unificada("2026-07", "Itaú", somente_cartao=True)

        # Contrato ja presente na v38 e em test_rc307_deduplicacao.py:
        # somente o MESMO item previsto/realizado e deduplicado.
        self.assertEqual("mista", resumo["fonte_fatura"])
        self.assertAlmostEqual(1026.89, resumo["valor_bruto"], places=2)
        self.assertAlmostEqual(791.46, resumo["saldo_restante"], places=2)
        self.assertEqual(
            {"Compras Itaú", "Wellhub", "Plano de celular", "YouTube Premium"},
            {item["nome"] for item in resumo["itens"]},
        )
        self.assertEqual(0, len(resumo["itens_previstos_ignorados"]))

    def test_sem_lancamento_real_recorrentes_formam_fatura_prevista(self):
        with patch.object(compromissos, "obter_itens_base_pagamentos_mes", return_value=self.recorrentes_credito), \
             patch.object(compromissos, "listar_fatura_movimentos", return_value=[]), \
             patch.object(compromissos, "obter_primeira_competencia_financeira", return_value="2026-07"):
            resumo = compromissos.calcular_fatura_unificada("2026-07", "Itaú", somente_cartao=True)

        self.assertEqual("prevista", resumo["fonte_fatura"])
        self.assertAlmostEqual(154.83, resumo["valor_bruto"], places=2)
        self.assertAlmostEqual(154.83, resumo["saldo_restante"], places=2)

    def test_resumo_por_conta_preserva_recorrentes_nao_realizados(self):
        pix = {
            "origem": "compromisso", "tipo": "fixo", "id": 10,
            "nome": "iCloud", "categoria": "Assinaturas",
            "conta_pagamento": "Itaú", "forma_pagamento": "pix",
            "valor": 33.45, "data": "2026-07-20",
        }
        itens = [self.transacao_real, *self.recorrentes_credito, pix]
        p1, p2, p3 = self._patch_base(itens)
        with p1, p2, p3:
            resumo = compromissos.calcular_resumo_pagamento_conta("2026-07", "Itaú")

        self.assertAlmostEqual(636.63, resumo["fatura"], places=2)
        self.assertAlmostEqual(188.28, resumo["fixos"], places=2)
        self.assertAlmostEqual(824.91, resumo["total"], places=2)
        self.assertAlmostEqual(resumo["fatura"] + resumo["fixos"], resumo["total"], places=2)

    def test_checklist_usa_mesma_fatura_real_do_resumo(self):
        banco = {
            "chave": "B_ITAU", "codigo": "B1", "alias": ["B1", "B_ITAU"],
            "grupo": "bancos", "origem": "banco_agregado", "id": None,
            "data": "2026-07-30", "nome": "Itaú", "categoria": "Fatura/cartão",
            "conta": "Itaú", "forma": "fatura", "valor": 636.63,
            "status": "pendente", "status_origem": "pendente",
            "fonte_fatura": "real", "status_fatura": "parcialmente abatida",
        }
        with patch.object(services, "montar_itens_checklist_mes", return_value=[banco]), \
             patch.object(services, "aplicar_status_checklist", side_effect=lambda _mes, xs: xs):
            texto = services.gerar_checklist_pagamentos("2026-07")

        self.assertIn("Total pendente: R$ 636,63", texto)
        self.assertIn("B1 Itaú — R$ 636,63", texto)
        self.assertIn("realizada", texto)
        self.assertNotIn("R$ 791,46", texto)


if __name__ == "__main__":
    unittest.main()
