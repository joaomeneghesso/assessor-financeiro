import unittest
from unittest.mock import patch

import compromissos
import services


class ChecklistCompatibilidadeLegadaTests(unittest.TestCase):
    @staticmethod
    def transacao(identificador, conta, forma):
        return {
            "origem": "transacao",
            "id": identificador,
            "tipo": "despesa",
            "nome": f"Compra {identificador}",
            "categoria": "Teste",
            "conta_pagamento": conta,
            "forma_pagamento": forma,
            "valor": 100.0,
            "data": "2026-07-10",
            "parcela_atual": None,
            "parcelas_total": None,
        }

    def test_forma_vazia_em_bancos_reais_permanece_na_fatura(self):
        for conta in ("Itaú", "Mercado Pago", "Nubank"):
            with self.subTest(conta=conta):
                self.assertTrue(compromissos.item_eh_fatura_cartao(self.transacao(1, conta, "")))

    def test_forma_legada_desconhecida_em_banco_real_permanece_na_fatura(self):
        self.assertTrue(compromissos.item_eh_fatura_cartao(
            self.transacao(2, "Mercado Pago", "não informada")
        ))

    def test_conta_pix_com_forma_vazia_nao_vira_fatura(self):
        self.assertFalse(compromissos.item_eh_fatura_cartao(self.transacao(3, "Pix", "")))

    def test_pix_explicito_em_banco_real_nao_vira_fatura(self):
        self.assertFalse(compromissos.item_eh_fatura_cartao(self.transacao(4, "Itaú", "pix")))

    def test_checklist_agrega_legados_sem_ocultar_valores(self):
        itens = [
            self.transacao(10, "Itaú", ""),
            self.transacao(11, "Mercado Pago", "não informada"),
            self.transacao(12, "Nubank", "outros"),
        ]
        def resumo(_mes, conta):
            return {
                "valor_bruto": 100.0,
                "creditos": 0.0,
                "pagamentos": 0.0,
                "saldo_restante": 100.0,
                "status": "pendente",
            }
        with patch.object(services, "projetar_pagamentos_mes", return_value=itens), \
             patch.object(services, "calcular_resumo_fatura", side_effect=resumo), \
             patch.object(services, "aplicar_datas_pagamento_checklist", side_effect=lambda _mes, dados: dados):
            checklist = services.montar_itens_checklist_mes("2026-07")
        contas = {item["conta"] for item in checklist if item["grupo"] == "bancos"}
        self.assertEqual({"Itaú", "Mercado Pago", "Nubank"}, contas)


if __name__ == "__main__":
    unittest.main()
