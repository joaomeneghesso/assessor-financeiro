import tempfile
import threading
import unittest
from pathlib import Path

import database
import services


class FaturaRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = database.DB_PATH
        self.old_service_db = services.DB_PATH
        self.db = Path(self.tmp.name) / "financeiro.db"
        database.DB_PATH = self.db
        services.DB_PATH = self.db
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.old_db
        services.DB_PATH = self.old_service_db
        self.tmp.cleanup()

    def compra(self, ano_mes, valor, conta="Nubank"):
        database.inserir_transacao({
            "data": f"{ano_mes}-05", "tipo": "despesa", "valor": valor,
            "categoria": "Teste", "descricao": "Compra cartão",
            "conta": conta, "forma_pagamento": "crédito",
            "mensagem_original": "teste",
        })

    def movimento(self, ano_mes, tipo, valor, origem=None):
        return database.inserir_fatura_movimento({
            "ano_mes": ano_mes, "conta_cartao": "Nubank",
            "tipo_movimento": tipo, "valor": valor,
            "data_movimento": f"{ano_mes}-10", "conta_origem": origem,
        })

    def test_credito_atravessa_mes_vazio_e_abate_compra_futura(self):
        self.compra("2026-01", 100)
        self.movimento("2026-01", "estorno", 150)
        fevereiro = services.calcular_resumo_fatura("2026-02", "Nubank")
        self.assertEqual(fevereiro["saldo_restante"], -50)
        self.assertEqual(fevereiro["status"], "saldo credor transportado")
        self.compra("2026-03", 30)
        marco = services.calcular_resumo_fatura("2026-03", "Nubank")
        self.assertEqual(marco["credito_herdado"], 50)
        self.assertEqual(marco["saldo_restante"], -20)

    def test_mes_sem_atividade_tem_status_proprio(self):
        resumo = services.calcular_resumo_fatura("2026-07", "Nubank")
        self.assertEqual(resumo["status"], "sem movimentação")

    def test_pagamento_em_fatura_credora_e_bloqueado(self):
        self.compra("2026-04", 100)
        self.movimento("2026-04", "credito", 120)
        resposta = services.registrar_movimento_fatura_formatado(
            "pagamento_parcial", 10, "Nubank", "2026-04", "Itaú"
        )
        self.assertIn("não possui saldo pendente", resposta)
        self.assertEqual(len(database.listar_fatura_movimentos("2026-04")), 1)

    def test_pagamento_parcial_acima_do_saldo_e_limitado(self):
        self.compra("2026-05", 100)
        services.registrar_movimento_fatura_formatado(
            "pagamento_parcial", 150, "Nubank", "2026-05", "Itaú"
        )
        resumo = services.calcular_resumo_fatura("2026-05", "Nubank")
        self.assertEqual(resumo["pagamentos"], 100)
        self.assertEqual(resumo["saldo_restante"], 0)

    def test_competencia_invalida_nao_cai_no_mes_atual(self):
        parsed = services.parsear_comando_movimento_fatura(
            "paguei 10 da fatura Nubank usando Itaú 2090-99"
        )
        self.assertEqual(parsed[0], "erro")

    def test_pagamento_total_concorrente_registra_uma_vez(self):
        self.compra("2026-06", 100)
        respostas = []
        def pagar():
            respostas.append(services.registrar_movimento_fatura_formatado(
                "pagamento_total", 1, "Nubank", "2026-06", "Itaú"
            ))
        threads = [threading.Thread(target=pagar) for _ in range(2)]
        for t in threads: t.start()
        for t in threads: t.join()
        resumo = services.calcular_resumo_fatura("2026-06", "Nubank")
        self.assertEqual(resumo["pagamentos"], 100)
        self.assertEqual(len(database.listar_fatura_movimentos("2026-06")), 1)
        self.assertTrue(any("não possui saldo pendente" in r for r in respostas))


if __name__ == "__main__":
    unittest.main()
