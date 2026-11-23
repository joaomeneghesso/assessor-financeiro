import unittest
from unittest.mock import patch

import services


class ChecklistCompactoRC157Tests(unittest.TestCase):
    @staticmethod
    def item(codigo, nome, valor, status="pendente", grupo="individuais", origem=None):
        return {
            "chave": codigo.lower(),
            "codigo": codigo,
            "nome": nome,
            "valor": valor,
            "status": status,
            "grupo": grupo,
            "status_origem": origem,
            "status_fatura": "pendente",
        }

    def gerar(self, itens, filtro=None):
        with patch.object(services, "montar_itens_checklist_mes", return_value=itens), \
             patch.object(services, "aplicar_status_checklist", side_effect=lambda _mes, dados: dados):
            return services.gerar_checklist_pagamentos("2026-07", filtro)

    def test_checklist_padrao_mostra_somente_pendentes(self):
        itens = [
            self.item("C7", "IPTV", 8.0),
            self.item("T41", "Acessórios drone", 17.0, status="pago", origem="automatico_transacao"),
            self.item("B1", "Itaú", 100.0, grupo="bancos"),
        ]
        texto = self.gerar(itens)
        self.assertIn("☐ Total pendente: R$ 108,00", texto)
        self.assertIn("📌 2 item(ns) pendente(s)", texto)
        self.assertIn("C7 IPTV", texto)
        self.assertIn("B1 Itaú", texto)
        self.assertNotIn("T41 Acessórios drone", texto)
        self.assertNotIn("Ações:", texto)
        self.assertNotIn("✅ Pagos:", texto)

    def test_checklist_completo_mantem_pagos_e_pendentes(self):
        itens = [
            self.item("C7", "IPTV", 8.0),
            self.item("T41", "Acessórios drone", 17.0, status="pago", origem="automatico_transacao"),
        ]
        texto = self.gerar(itens, "completo")
        self.assertIn("Checklist · completo", texto)
        self.assertIn("☐ Pendentes: R$ 8,00", texto)
        self.assertIn("✅ Pagos: R$ 17,00", texto)
        self.assertIn("T41 Acessórios drone", texto)
        self.assertIn("· auto", texto)
        self.assertNotIn("Ações:", texto)

    def test_checklist_pagos_mostra_somente_pagos(self):
        itens = [
            self.item("C7", "IPTV", 8.0),
            self.item("T41", "Acessórios drone", 17.0, status="pago"),
        ]
        texto = self.gerar(itens, "pagos")
        self.assertIn("✅ Total pago: R$ 17,00", texto)
        self.assertIn("T41 Acessórios drone", texto)
        self.assertNotIn("C7 IPTV", texto)

    def test_parser_aceita_completo_e_faturas(self):
        self.assertEqual(services.parsear_comando_checklist("checklist completo 2026-07"), ("2026-07", "completo"))
        self.assertEqual(services.parsear_comando_checklist("checklist faturas 2026-07"), ("2026-07", "faturas"))


if __name__ == "__main__":
    unittest.main()
