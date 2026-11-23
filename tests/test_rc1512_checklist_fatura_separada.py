import unittest
from unittest.mock import patch

import services


class ChecklistFaturaSeparadaRC1512Tests(unittest.TestCase):
    @staticmethod
    def item(origem, identificador, nome, valor, tipo, categoria="Teste"):
        return {
            "origem": origem,
            "id": identificador,
            "tipo": tipo,
            "nome": nome,
            "categoria": categoria,
            "conta_pagamento": "Itaú",
            "forma_pagamento": "crédito",
            "valor": valor,
            "data": "2026-07-10",
            "parcela_atual": None,
            "parcelas_total": None,
        }

    def dados(self):
        itens = [
            self.item("transacao", 1, "Compras e parcelas", 636.63, "despesa"),
            self.item("compromisso", 2, "Wellhub", 91.70, "fixo"),
            self.item("compromisso", 3, "Plano de celular", 50.00, "fixo"),
            self.item("compromisso", 4, "YouTube Premium", 13.13, "fixo"),
        ]
        resumo = {
            "valor_bruto": 791.46,
            "creditos": 0.0,
            "pagamentos": 0.0,
            "saldo_restante": 791.46,
            "status": "pendente",
        }
        return itens, resumo

    def test_banco_preserva_total_e_expoe_componentes(self):
        itens, resumo = self.dados()
        with patch.object(services, "projetar_pagamentos_mes", return_value=itens), \
             patch.object(services, "calcular_resumo_fatura", return_value=resumo), \
             patch.object(services, "buscar_checklist_datas_pagamento_mes", return_value={}), \
             patch.object(services, "buscar_checklist_datas_pagamento_padrao", return_value={}):
            resultado = services.montar_itens_checklist_mes("2026-07")

        self.assertEqual(len(resultado), 1)
        banco = resultado[0]
        self.assertAlmostEqual(banco["valor"], 791.46, places=2)
        self.assertAlmostEqual(banco["cartao_parcelas"], 636.63, places=2)
        self.assertAlmostEqual(banco["fixos_credito"], 154.83, places=2)

    def test_checklist_mostra_separacao_sem_alterar_total(self):
        banco = {
            "chave": "B_itau", "codigo": "B1", "alias": ["B1"],
            "grupo": "bancos", "origem": "banco_agregado", "id": None,
            "data": "", "nome": "Itaú", "categoria": "Fatura/cartão",
            "conta": "Itaú", "forma": "fatura", "valor": 791.46,
            "cartao_parcelas": 636.63, "fixos_credito": 154.83,
            "emprestimos": 0.0, "outros_compromissos": 0.0,
            "status_fatura": "pendente", "qtd_itens": 4,
        }
        with patch.object(services, "montar_itens_checklist_mes", return_value=[banco]), \
             patch.object(services, "aplicar_status_checklist", return_value=[dict(banco, status="pendente")]):
            texto = services.gerar_checklist_pagamentos("2026-07")

        self.assertIn("B1 Itaú — R$ 791,46", texto)
        self.assertIn("Cartão e parcelas: R$ 636,63", texto)
        self.assertIn("Fixos no crédito: R$ 154,83", texto)
        self.assertIn("Total pendente: R$ 791,46", texto)


if __name__ == "__main__":
    unittest.main()
