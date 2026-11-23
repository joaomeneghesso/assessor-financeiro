import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
import services


class ContratosBaselineRC153Tests(unittest.TestCase):
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

    @staticmethod
    def item(origem="compromisso", forma="pix", valor=100.0, **campos):
        item = {
            "origem": origem,
            "id": 1,
            "tipo": "fixo",
            "nome": "Conta futura",
            "categoria": "Teste",
            "conta_pagamento": "Pix",
            "forma_pagamento": forma,
            "valor": valor,
            "data": "2026-07-10",
            "parcela_atual": None,
            "parcelas_total": None,
        }
        item.update(campos)
        return item

    def test_filtro_puro_cobre_obrigacoes_e_operacoes_realizadas(self):
        casos_pendentes = [
            self.item(nome="Recorrência Pix"),
            self.item(nome="Fixo futuro"),
            self.item(nome="Boleto futuro", forma="boleto"),
            self.item(nome="Débito futuro", forma="débito"),
            self.item(nome="Empréstimo futuro", categoria="Empréstimos"),
            self.item(nome="Conta Pix legada", conta_pagamento="Pix", forma=""),
            self.item(
                origem="banco_agregado",
                nome="Nubank",
                conta_pagamento="Nubank",
                forma="fatura",
            ),
        ]
        casos_excluidos = [
            self.item(origem="transacao", nome="Pix realizado", forma="pix"),
            self.item(origem="transacao", nome="Transferência", forma="transferência"),
            self.item(origem="transacao", nome="Débito realizado", forma="débito"),
            self.item(origem="fatura_movimento", tipo="estorno", forma="fatura"),
            self.item(origem="fatura_movimento", tipo="credito", forma="fatura"),
            self.item(origem="fatura_movimento", tipo="pagamento", forma="fatura"),
            self.item(origem="fatura_movimento", tipo="pagamento_total", forma="fatura"),
            self.item(valor=0),
            self.item(valor=-10),
            self.item(status="pago"),
        ]

        self.assertTrue(all(
            services.item_deve_entrar_no_checklist(item)
            for item in casos_pendentes
        ))
        self.assertTrue(all(
            not services.item_deve_entrar_no_checklist(item)
            for item in casos_excluidos
        ))

    def test_concluido_fica_fora_de_pendentes_e_acessivel_em_outros_modos(self):
        concluido = self.item(status="pago")
        realizado = self.item(origem="transacao", forma="pix")

        self.assertFalse(services.item_deve_entrar_no_checklist(concluido))
        self.assertTrue(services.item_deve_entrar_no_checklist(concluido, "concluidos"))
        self.assertTrue(services.item_deve_entrar_no_checklist(concluido, "geral"))
        self.assertTrue(services.item_deve_entrar_no_checklist(realizado, "concluidos"))

    def test_visao_geral_preserva_transacao_realizada_com_status_concluido(self):
        realizado = self.item(origem="transacao", id=91, forma="pix")
        with patch.object(services, "projetar_pagamentos_mes", return_value=[realizado]):
            pendentes = services.montar_itens_checklist_mes("2026-07")
            geral = services.aplicar_status_checklist(
                "2026-07",
                services.montar_itens_checklist_mes("2026-07", modo="geral"),
            )

        self.assertEqual([], pendentes)
        self.assertEqual("T91", geral[0]["chave"])
        self.assertEqual("pago", geral[0]["status"])
        self.assertEqual("automatico", geral[0]["status_origem"])

    def test_chave_status_manual_e_data_manual_sao_preservados(self):
        compromisso_id = database.inserir_compromisso({
            "tipo": "fixo",
            "nome": "Condomínio",
            "categoria": "Moradia",
            "conta_pagamento": "Pix",
            "forma_pagamento": "pix",
            "valor": 350.0,
            "dia_vencimento": 10,
            "data_inicio": "2026-07-01",
            "ativo": True,
            "origem": "teste_rc153",
        })
        chave = f"C{compromisso_id}"
        database.marcar_checklist_pagamento(
            "2026-07", chave, "pago", "confirmado no teste"
        )
        database.definir_checklist_data_pagamento(
            "2026-07", chave, "2026-07-22", "data manual do teste"
        )

        itens = services.aplicar_status_checklist(
            "2026-07",
            services.montar_itens_checklist_mes("2026-07", modo="geral"),
        )
        item = next(item for item in itens if item["chave"] == chave)

        self.assertEqual(chave, item["chave"])
        # A marcacao persiste; a exibicao exige conciliacao com o movimento.
        self.assertEqual("revisar", item["status"])
        self.assertEqual("marcacao_sem_vinculo", item["status_origem"])
        self.assertEqual("pago", database.buscar_checklist_status_mes("2026-07")[chave]["status"])
        self.assertEqual("2026-07-22", item["data"])
        self.assertTrue(item["data_pagamento_manual"])

    def test_checklist_nao_altera_totais_centrais(self):
        for tipo, valor, descricao, forma in (
            ("receita", 1000.0, "Salário", "entrada"),
            ("despesa", 100.0, "Mercado", "pix"),
            ("despesa", 200.0, "Compra cartão", "crédito"),
        ):
            database.inserir_transacao({
                "data": "2026-07-05",
                "tipo": tipo,
                "valor": valor,
                "categoria": "Teste",
                "descricao": descricao,
                "conta": "Itaú",
                "forma_pagamento": forma,
                "mensagem_original": "teste RC1.5.3",
            })
        database.inserir_compromisso({
            "tipo": "fixo",
            "nome": "Internet",
            "categoria": "Casa",
            "conta_pagamento": "Pix",
            "forma_pagamento": "pix",
            "valor": 80.0,
            "dia_vencimento": 20,
            "data_inicio": "2026-07-01",
            "ativo": True,
            "origem": "teste_rc153",
        })

        metricas_antes = services.obter_metricas_resultado_mes("2026-07")
        quanto_antes = services.resumo_pagamento_mes_consolidado("2026-07")
        services.gerar_checklist_pagamentos("2026-07", "pendentes")
        metricas_depois = services.obter_metricas_resultado_mes("2026-07")
        quanto_depois = services.resumo_pagamento_mes_consolidado("2026-07")

        chaves = (
            "total_entradas_mes",
            "saidas_imediatas_realizadas",
            "saidas_nao_imediatas_realizadas",
            "despesas_esperadas_total",
            "resultado_projetado_mes",
            "saldo_livre_projetado",
        )
        self.assertEqual(
            {chave: metricas_antes[chave] for chave in chaves},
            {chave: metricas_depois[chave] for chave in chaves},
        )
        self.assertEqual(quanto_antes, quanto_depois)


if __name__ == "__main__":
    unittest.main()
