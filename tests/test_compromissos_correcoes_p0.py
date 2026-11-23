import contextlib
import logging
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import compromissos
import database
from conciliacao import ConciliacaoError


class _BancoTemp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old = database.DB_PATH
        database.DB_PATH = Path(self._tmp.name) / "t.db"
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self._old
        try:
            self._tmp.cleanup()
        except OSError:
            pass


class ResumoAvisaContaComErro(unittest.TestCase):
    def test_conta_com_erro_gera_aviso_e_mantem_total_das_demais(self):
        itens = [
            {"origem": "compromisso", "tipo": "fixo", "conta_pagamento": "Itaú", "forma_pagamento": "pix", "valor": 100},
            {"origem": "compromisso", "tipo": "fixo", "conta_pagamento": "Nubank", "forma_pagamento": "pix", "valor": 50},
        ]

        def calc(mes, conta):
            if conta == "Nubank":
                raise ConciliacaoError("vínculo inconsistente")
            return {"fatura": 0, "fixos": 100, "compromissos": 0, "total": 100, "possui_dados": True}

        with patch.object(compromissos, "obter_itens_base_pagamentos_mes", return_value=itens), \
             patch.object(compromissos, "listar_fatura_movimentos", return_value=[]), \
             patch.object(compromissos, "calcular_resumo_pagamento_conta", side_effect=calc), \
             self.assertLogs(compromissos._LOG, level=logging.ERROR):
            texto = compromissos.resumo_pagamento_mes_consolidado("2026-07")
        self.assertIn("TOTAL A PAGAR: R$ 100,00", texto)
        self.assertIn("⚠️ Não foi possível calcular a conta Nubank: vínculo inconsistente", texto)
        self.assertIn("o total pode estar incompleto", texto)

    def test_todas_as_contas_com_erro_nao_diz_que_nao_ha_pendencias(self):
        itens = [{"origem": "compromisso", "tipo": "fixo", "conta_pagamento": "Itaú", "forma_pagamento": "pix", "valor": 100}]
        with patch.object(compromissos, "obter_itens_base_pagamentos_mes", return_value=itens), \
             patch.object(compromissos, "listar_fatura_movimentos", return_value=[]), \
             patch.object(compromissos, "calcular_resumo_pagamento_conta", side_effect=RuntimeError("boom")), \
             self.assertLogs(compromissos._LOG, level=logging.ERROR):
            texto = compromissos.resumo_pagamento_mes_consolidado("2026-07")
        self.assertIn("Não foi possível calcular a conta Itaú", texto)
        self.assertNotIn("Não encontrei pagamentos pendentes", texto)


class AlterarContaComContaOrigem(_BancoTemp):
    def _criar(self, conta_origem, conta_pagamento="Itaú", forma="pix"):
        cid = database.inserir_compromisso({
            "tipo": "fixo", "nome": "Condomínio", "categoria": "Moradia",
            "conta_pagamento": conta_pagamento, "forma_pagamento": forma,
            "valor": 100.0, "dia_vencimento": 10, "data_inicio": "2026-01-01",
            "data_fim": None, "parcelas_total": None, "ativo": 1,
            "origem": "teste", "observacao": None,
        })
        with contextlib.closing(sqlite3.connect(database.DB_PATH)) as c:
            c.execute("UPDATE compromissos SET conta_origem=? WHERE id=?", (conta_origem, cid))
            c.commit()
        return cid

    def test_altera_conta_origem_preenchida(self):
        cid = self._criar("Itaú")
        texto = compromissos.alterar_compromisso_conta(cid, "btg")
        self.assertIn("Nova conta: BTG", texto)
        self.assertIn("Conta anterior: Itaú", texto)
        c = compromissos.buscar_compromisso_por_id(cid)
        self.assertEqual("BTG", c["conta_origem"])
        self.assertEqual("BTG", c["conta_pagamento"])

    def test_nao_preenche_conta_origem_vazia(self):
        cid = self._criar(None)
        compromissos.alterar_compromisso_conta(cid, "btg")
        c = compromissos.buscar_compromisso_por_id(cid)
        self.assertIsNone(c["conta_origem"])
        self.assertEqual("BTG", c["conta_pagamento"])

    def test_forma_nao_vira_conta_origem(self):
        cid = self._criar("Itaú")
        texto = compromissos.alterar_compromisso_conta(cid, "Pix")
        self.assertIn("forma de pagamento", texto)
        c = compromissos.buscar_compromisso_por_id(cid)
        self.assertEqual("Itaú", c["conta_origem"])


class ValoresNaoFinitos(_BancoTemp):
    def test_movimento_fatura_rejeita_nan_e_inf(self):
        for v in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(v=v):
                with self.assertRaises(ValueError):
                    database._validar_fatura_movimento({
                        "ano_mes": "2026-07", "conta_cartao": "Nubank",
                        "tipo_movimento": "estorno", "valor": v,
                        "data_movimento": "2026-07-01",
                    })

    def test_atualizar_valor_rejeita_invalidos(self):
        for v in (float("nan"), float("inf"), 0, -5, "abc", None):
            with self.subTest(v=v):
                with self.assertRaises(ValueError):
                    database.atualizar_valor_por_id(1, v)


class DataCartoesNovos(unittest.TestCase):
    def test_padrao_preservado(self):
        self.assertEqual("2026-09-01", compromissos.DATA_INICIO_CARTOES_NOVOS)

    def test_env_invalida_usa_padrao(self):
        with patch.dict(os.environ, {"ASSESSOR_CARTAO_NOVO_INICIO": "lixo"}):
            self.assertEqual("2026-09-01", compromissos._data_inicio_cartoes_novos())
        with patch.dict(os.environ, {"ASSESSOR_CARTAO_NOVO_INICIO": "2027-01-01"}):
            self.assertEqual("2027-01-01", compromissos._data_inicio_cartoes_novos())


if __name__ == "__main__":
    unittest.main()
