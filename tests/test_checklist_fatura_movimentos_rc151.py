import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
import services


class ChecklistFaturaMovimentosRC151Tests(unittest.TestCase):
    def test_movimento_de_fatura_nao_vira_item_individual(self):
        itens_projetados = [
            {
                "origem": "fatura_movimento",
                "id": 1,
                "tipo": "fatura_movimento",
                "nome": "Estorno",
                "categoria": "Ajuste de fatura",
                "conta_pagamento": "Itaú",
                "forma_pagamento": "fatura",
                "valor": -143.73,
                "data": "2026-07-10",
            },
            {
                "origem": "compromisso",
                "id": 7,
                "tipo": "fixo",
                "nome": "IPTV",
                "categoria": "Assinaturas",
                "conta_pagamento": "Pix",
                "forma_pagamento": "pix",
                "valor": 8.0,
                "data": "2026-07-15",
            },
        ]

        with patch.object(services, "projetar_pagamentos_mes", return_value=itens_projetados), \
             patch.object(services, "calcular_resumo_fatura") as resumo, \
             patch.object(services, "aplicar_datas_pagamento_checklist", side_effect=lambda _mes, itens: itens):
            itens = services.montar_itens_checklist_mes("2026-07")

        resumo.assert_not_called()
        self.assertEqual(1, len(itens))
        self.assertEqual("IPTV", itens[0]["nome"])
        self.assertFalse(any(i.get("origem") == "fatura_movimento" for i in itens))

    def test_banco_real_recuperado_preserva_faturas_e_remove_estornos(self):
        with tempfile.TemporaryDirectory() as tmp:
            banco_teste = Path(tmp) / "financeiro.db"
            db_path_original = database.DB_PATH
            service_db_original = services.DB_PATH
            try:
                database.DB_PATH = banco_teste
                services.DB_PATH = banco_teste
                database.init_db()
                for conta, valor in (
                    ("Itaú", 860.21),
                    ("Mercado Pago", 842.46),
                    ("Nubank", 1301.10),
                ):
                    database.inserir_transacao({
                        "data": "2026-07-05",
                        "tipo": "despesa",
                        "valor": valor,
                        "categoria": "Compras",
                        "descricao": f"Compra {conta}",
                        "conta": conta,
                        "forma_pagamento": "crédito",
                        "mensagem_original": "fixture portátil RC1.5.3",
                    })
                for nome, valor in (
                    ("Empréstimos", 400.0),
                    ("Condominio", 300.0),
                    ("Internet", 100.0),
                ):
                    database.inserir_compromisso({
                        "tipo": "fixo",
                        "nome": nome,
                        "categoria": "Contas",
                        "conta_pagamento": "Pix",
                        "forma_pagamento": "pix",
                        "valor": valor,
                        "dia_vencimento": 10,
                        "data_inicio": "2026-07-01",
                        "ativo": True,
                        "origem": "fixture_rc153",
                    })
                database.inserir_fatura_movimento({
                    "ano_mes": "2026-07",
                    "conta_cartao": "Itaú",
                    "tipo_movimento": "estorno",
                    "valor": 143.73,
                    "data_movimento": "2026-07-10",
                    "conta_origem": None,
                    "descricao": "Estorno portátil",
                    "mensagem_original": "fixture portátil RC1.5.3",
                })
                itens = services.montar_itens_checklist_mes("2026-07")
            finally:
                database.DB_PATH = db_path_original
                services.DB_PATH = service_db_original

        self.assertFalse(any(i.get("origem") == "fatura_movimento" for i in itens))
        self.assertFalse(any((i.get("nome") or "").lower() == "estorno" for i in itens))

        faturas = {i["conta"]: round(float(i["valor"]), 2) for i in itens if i.get("origem") == "banco_agregado"}
        self.assertEqual(716.48, faturas.get("Itaú"))
        self.assertEqual(842.46, faturas.get("Mercado Pago"))
        self.assertEqual(1301.10, faturas.get("Nubank"))

        nomes = {i.get("nome") for i in itens}
        self.assertIn("Empréstimos", nomes)
        self.assertIn("Condominio", nomes)
        self.assertIn("Internet", nomes)


if __name__ == "__main__":
    unittest.main()
