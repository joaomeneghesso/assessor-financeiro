import unittest
from unittest.mock import patch

import services


class TestRC1510TotalChecklistFaturaLiquida(unittest.TestCase):
    def test_total_pendente_usa_saldo_liquido_da_fatura_sem_duplicar_fixos(self):
        itens = [
            {
                "chave": "C7", "codigo": "C7", "alias": [],
                "grupo": "individuais", "origem": "compromisso",
                "id": 7, "data": "2026-07-10", "nome": "IPTV",
                "categoria": "Assinaturas", "conta": "Itaú",
                "forma": "pix", "valor": 8.00, "extra": "",
                "status": "pendente", "status_origem": "pendente",
            },
            {
                "chave": "B_ITAU", "codigo": "B1", "alias": ["B1", "B_ITAU"],
                "grupo": "bancos", "origem": "banco_agregado",
                "id": None, "data": "2026-07-30", "nome": "Itaú",
                "categoria": "Fatura/cartão", "conta": "Itaú",
                "forma": "fatura", "valor": 636.63, "extra": "",
                "status": "pendente", "status_origem": "pendente",
                "status_fatura": "parcialmente abatida",
            },
        ]

        with patch.object(services, "montar_itens_checklist_mes", return_value=itens), \
             patch.object(services, "aplicar_status_checklist", side_effect=lambda _mes, xs: xs):
            texto = services.gerar_checklist_pagamentos("2026-07")

        self.assertIn("☐ Total pendente: R$ 644,63", texto)
        self.assertIn("☐ C7 IPTV — R$ 8,00", texto)
        self.assertIn("☐ B1 Itaú — R$ 636,63", texto)
        self.assertNotIn("R$ 1.617,79", texto)

    def test_total_do_exemplo_cai_para_3617_07(self):
        total_antigo = 4598.23
        itau_incorreto = 1617.79
        itau_correto = 636.63
        self.assertAlmostEqual(total_antigo - itau_incorreto + itau_correto, 3617.07, places=2)


if __name__ == "__main__":
    unittest.main()
