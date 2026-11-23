import unittest
from unittest.mock import patch

import compromissos
from consulta_cache import contexto_consulta, obter_ou_calcular


class CacheConsultaFase1Tests(unittest.TestCase):
    def test_cache_existe_apenas_dentro_da_interacao(self):
        chamadas = []

        def calcular():
            chamadas.append(1)
            return {"itens": [{"valor": 10}]}

        with contexto_consulta():
            primeiro = obter_ou_calcular(("teste",), calcular)
            primeiro["itens"][0]["valor"] = 999
            segundo = obter_ou_calcular(("teste",), calcular)
            self.assertEqual(10, segundo["itens"][0]["valor"])
            self.assertEqual(1, len(chamadas))

        obter_ou_calcular(("teste",), calcular)
        self.assertEqual(2, len(chamadas))

    def test_projecao_de_compromissos_e_reutilizada_sem_compartilhar_mutacao(self):
        item = {
            "data": "2026-10-01",
            "conta_pagamento": "Teste",
            "nome": "Item",
        }
        with patch.object(compromissos, "_projetar_compromissos_mes", return_value=[item]) as calcular:
            with contexto_consulta():
                primeira = compromissos.projetar_compromissos_mes("2026-10")
                primeira[0]["nome"] = "Alterado"
                segunda = compromissos.projetar_compromissos_mes("2026-10")

        self.assertEqual("Item", segunda[0]["nome"])
        calcular.assert_called_once_with("2026-10", True)

    def test_memo_de_fatura_e_compartilhado_somente_no_contexto(self):
        base = [{
            "origem": "transacao",
            "conta_pagamento": "Nubank",
            "forma_pagamento": "crédito",
            "nome": "Compra",
            "valor": 25.0,
        }]
        with (
            patch.object(compromissos, "obter_itens_base_pagamentos_mes", return_value=base) as obter,
            patch.object(compromissos, "listar_fatura_movimentos", return_value=[]),
            patch.object(compromissos, "obter_primeira_competencia_financeira", return_value=None),
            patch("fatura_conferencia.obter", return_value=None),
            contexto_consulta(),
        ):
            primeira = compromissos.calcular_fatura_unificada("2026-10", "Nubank", somente_cartao=True)
            primeira["saldo_restante"] = 999
            segunda = compromissos.calcular_fatura_unificada("2026-10", "Nubank", somente_cartao=True)

        self.assertEqual(25.0, segunda["saldo_restante"])
        obter.assert_called_once()


if __name__ == "__main__":
    unittest.main()
