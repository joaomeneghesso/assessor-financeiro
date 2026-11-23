import unittest
from unittest.mock import patch

import services


class VencimentoFaturasRC158Tests(unittest.TestCase):
    def fatura(self, nome="Itaú", chave="B_ITAU", codigo="B1", data=""):
        return {
            "chave": chave,
            "codigo": codigo,
            "alias": [codigo, chave],
            "grupo": "bancos",
            "nome": nome,
            "conta": nome,
            "valor": 100.0,
            "status": "pendente",
            "status_fatura": "pendente",
            "data": data,
            "qtd_itens": 2,
        }

    def test_configura_vencimento_recorrente_por_nome_com_chave_estavel(self):
        item = self.fatura()
        with patch.object(services, "montar_itens_checklist_mes", return_value=[item]), \
             patch.object(services, "aplicar_status_checklist", side_effect=lambda _mes, dados: dados), \
             patch.object(services, "definir_checklist_data_pagamento_padrao") as salvar:
            texto = services.definir_vencimento_fatura_por_nome_formatado(
                "vencimento fatura Itaú dia 10"
            )
        salvar.assert_called_once_with(
            "B_ITAU", 10,
            "Dia de vencimento recorrente da fatura definido pelo usuário.",
        )
        self.assertIn("Vencimento recorrente", texto)
        self.assertIn("Cartão: Itaú", texto)

    def test_configura_vencimento_de_uma_competencia(self):
        item = self.fatura(nome="Nubank", chave="B_NUBANK", codigo="B3")
        with patch.object(services, "montar_itens_checklist_mes", return_value=[item]), \
             patch.object(services, "aplicar_status_checklist", side_effect=lambda _mes, dados: dados), \
             patch.object(services, "definir_checklist_data_pagamento") as salvar:
            texto = services.definir_vencimento_fatura_por_nome_formatado(
                "vencimento fatura Nubank 2026-08 dia 31"
            )
        salvar.assert_called_once()
        args = salvar.call_args.args
        self.assertEqual(args[0], "2026-08")
        self.assertEqual(args[1], "B_NUBANK")
        self.assertEqual(args[2], "2026-08-31")
        self.assertIn("somente para esta fatura", texto)

    def test_dia_31_cai_no_ultimo_dia_de_fevereiro(self):
        self.assertEqual(services.data_por_dia_no_mes("2027-02", 31), "2027-02-28")
        self.assertEqual(services.data_por_dia_no_mes("2028-02", 31), "2028-02-29")

    def test_checklist_exibe_vencimento_da_fatura(self):
        item = self.fatura(data="2026-07-10")
        with patch.object(services, "montar_itens_checklist_mes", return_value=[item]), \
             patch.object(services, "aplicar_status_checklist", side_effect=lambda _mes, dados: dados):
            texto = services.gerar_checklist_pagamentos("2026-07", "faturas")
        self.assertIn("vence 10/julho/2026", texto)

    def test_alerta_separa_faturas_e_compromissos(self):
        itens = [
            self.fatura(data="2026-07-10"),
            {
                "chave": "C7", "codigo": "C7", "grupo": "individuais",
                "nome": "IPTV", "valor": 8.0, "status": "pendente",
                "data": "2026-07-10",
            },
        ]
        with patch.object(services, "montar_itens_checklist_mes", return_value=itens), \
             patch.object(services, "aplicar_status_checklist", side_effect=lambda _mes, dados: dados):
            texto = services.gerar_lembrete_pagamentos_data("2026-07-10")
        self.assertIn("🧾 Compromissos", texto)
        self.assertIn("💳 Faturas", texto)
        self.assertIn("B1 Itaú", texto)

    def test_alerta_ignora_fatura_paga(self):
        item = self.fatura(data="2026-07-10")
        item["status"] = "pago"
        with patch.object(services, "montar_itens_checklist_mes", return_value=[item]), \
             patch.object(services, "aplicar_status_checklist", side_effect=lambda _mes, dados: dados):
            texto = services.gerar_lembrete_pagamentos_data("2026-07-10")
        self.assertIn("Nenhum compromisso ou fatura pendente", texto)
        self.assertNotIn("Itaú —", texto)


if __name__ == "__main__":
    unittest.main()
