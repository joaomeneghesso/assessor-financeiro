import copy
import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pagamentos_canonicos import (
    comparar_dados_pagamento_em_sombra,
    obter_dados_pagamento_canonicos,
)


class PagamentosCanonicosRC155Tests(unittest.TestCase):
    def test_registro_completo_prioriza_campos_canonicos(self):
        result = obter_dados_pagamento_canonicos({
            "conta_pagamento": "Legado",
            "conta_origem": "Itaú",
            "forma_pagamento": "Pix",
            "destino_pagamento": "Condomínio",
        })
        self.assertEqual("Itaú", result["conta_origem"])
        self.assertEqual("Pix", result["forma_pagamento"])
        self.assertEqual("Condomínio", result["destino_pagamento"])
        self.assertEqual("Legado", result["conta_pagamento_legado"])
        self.assertFalse(result["necessita_revisao"])

    def test_todos_nulos_sinalizam_revisao(self):
        result = obter_dados_pagamento_canonicos({
            "conta_pagamento": None,
            "conta_origem": None,
            "forma_pagamento": None,
            "destino_pagamento": None,
        })
        self.assertTrue(result["necessita_revisao"])
        self.assertEqual("sem_dados", result["origem_dos_dados"])

    def test_pix_legado_nao_e_inferido(self):
        result = obter_dados_pagamento_canonicos({
            "conta_pagamento": "Pix",
            "conta_origem": None,
            "forma_pagamento": None,
            "destino_pagamento": None,
        })
        self.assertIsNone(result["conta_origem"])
        self.assertIsNone(result["forma_pagamento"])
        self.assertIsNone(result["destino_pagamento"])
        self.assertEqual("Pix", result["conta_pagamento_legado"])
        self.assertIn("ambiguidade_legada", result["motivo_revisao"])

    def test_lia_legado_nao_e_inferida(self):
        result = obter_dados_pagamento_canonicos({
            "conta_pagamento": "Lia",
        })
        self.assertIsNone(result["conta_origem"])
        self.assertIsNone(result["forma_pagamento"])
        self.assertIsNone(result["destino_pagamento"])
        self.assertEqual("Lia", result["conta_pagamento_legado"])

    def test_banco_legado_nao_e_inferido(self):
        result = obter_dados_pagamento_canonicos({
            "conta_pagamento": "Itaú",
        })
        self.assertIsNone(result["conta_origem"])
        self.assertEqual("Itaú", result["conta_pagamento_legado"])

    def test_registro_sem_conta_pagamento(self):
        result = obter_dados_pagamento_canonicos({})
        self.assertIsNone(result["conta_pagamento_legado"])
        self.assertEqual("sem_dados", result["origem_dos_dados"])

    def test_registros_mistos_preservam_exatamente_o_preenchido(self):
        cases = (
            ("conta_origem", "Nubank"),
            ("forma_pagamento", "boleto"),
            ("destino_pagamento", "Prefeitura"),
        )
        for field, value in cases:
            with self.subTest(field=field):
                record = {
                    "conta_pagamento": "Legado",
                    "conta_origem": None,
                    "forma_pagamento": None,
                    "destino_pagamento": None,
                }
                record[field] = value
                result = obter_dados_pagamento_canonicos(record)
                self.assertEqual(value, result[field])
                self.assertEqual("Legado", result["conta_pagamento_legado"])
                self.assertTrue(result["necessita_revisao"])

    def test_funcao_nao_altera_objeto_e_e_deterministica(self):
        record = {
            "conta_pagamento": "Pix",
            "conta_origem": None,
            "forma_pagamento": None,
            "destino_pagamento": None,
        }
        before = copy.deepcopy(record)
        first = obter_dados_pagamento_canonicos(record)
        second = obter_dados_pagamento_canonicos(record)
        self.assertEqual(before, record)
        self.assertEqual(first, second)

    def test_funcao_nao_abre_banco(self):
        with patch.object(sqlite3, "connect", side_effect=AssertionError):
            result = obter_dados_pagamento_canonicos({
                "conta_pagamento": "Pix",
            })
        self.assertEqual("Pix", result["conta_pagamento_legado"])

    def test_compatibilidade_com_objeto_e_mapeamento(self):
        obj = SimpleNamespace(
            conta_pagamento="Legado",
            conta_origem="Caixa",
            forma_pagamento=None,
            destino_pagamento=None,
        )
        result = obter_dados_pagamento_canonicos(obj)
        self.assertEqual("Caixa", result["conta_origem"])
        self.assertEqual("Legado", result["conta_pagamento_legado"])

    def test_compatibilidade_com_sqlite_row_antiga(self):
        connection = sqlite3.connect(":memory:")
        try:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT 'Pix' AS conta_pagamento, NULL AS forma_pagamento"
            ).fetchone()
            result = obter_dados_pagamento_canonicos(row)
        finally:
            connection.close()
        self.assertEqual("Pix", result["conta_pagamento_legado"])
        self.assertIsNone(result["conta_origem"])
        self.assertTrue(result["necessita_revisao"])

    def test_shadow_read_compara_sem_substituir_legado(self):
        record = {
            "conta_pagamento": "Lia",
            "conta_origem": None,
            "forma_pagamento": None,
            "destino_pagamento": None,
        }
        result = comparar_dados_pagamento_em_sombra(record)
        self.assertEqual("Lia", result["legado"]["conta_pagamento"])
        self.assertTrue(result["legado_preservado"])
        self.assertFalse(result["substituir_comportamento_legado"])


if __name__ == "__main__":
    unittest.main()
