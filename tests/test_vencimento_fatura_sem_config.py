"""Vencimento falso de cartão (D06 das jornadas / D11 da reavaliação 02).

Sem vencimento configurado, a data da compra mais recente virava o
"vencimento" da fatura: uma compra no crédito feita hoje fazia o Início dizer
"vence hoje" e uma compra de 05/11 virava "Vencido há 4 dias".
Regra nova: sem vencimento manual/padrão, a fatura fica sem data (as telas
mostram "sem vencimento"), e o checklist ensina a configurar. Configurado,
o dia escolhido vale. Hoje fixo = 09/11/2026. Banco temporário.
"""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import database as db
import services as svc
import telegram_experiencia as ux

HOJE = date(2026, 11, 9)


class VencimentoFaturaSemConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = Path(self.tmp.name) / "financeiro.db"
        modulos = [db, svc]
        for nome in ("compromissos", "conciliacao", "reservas_faturas", "fatura_conferencia"):
            try:
                modulos.append(__import__(nome))
            except Exception:
                pass
        for mod in modulos:
            if hasattr(mod, "DB_PATH"):
                p = patch.object(mod, "DB_PATH", path); p.start(); self.addCleanup(p.stop)
        # O comando sem mês usa "hoje": fixa a data para o teste não depender do relógio real
        # (em 29/02/2028 as compras de 11/2026 ficam fora da janela de busca do cartão).
        from tests.relogio_fixo import data_fixa
        self.enterContext(data_fixa(HOJE))
        db.init_db()
        db.definir_saldo_inicial_conta_mes("2026-11", "Itaú", 1000)
        for dia, valor in (("2026-11-05", 80.0), ("2026-11-09", 120.0)):
            db.inserir_transacao(dict(data=dia, tipo="despesa", valor=valor, categoria="Compras",
                                      descricao="compra", conta="Nubank", forma_pagamento="credito",
                                      mensagem_original="teste"))

    def fatura(self):
        itens = [i for i in svc.montar_itens_checklist_mes("2026-11") if i.get("grupo") == "bancos"]
        self.assertEqual(len(itens), 1)
        return itens[0]

    def test_sem_vencimento_nao_usa_data_da_compra(self):
        item = self.fatura()
        self.assertEqual(item["data"], "")            # antes: "2026-11-09" (data da compra)
        self.assertFalse(item["vencimento_definido"])
        self.assertEqual(item["data_ultima_compra"], "2026-11-09")

    def test_inicio_nao_diz_vence_hoje_nem_vencida(self):
        texto = ux.Experience(date_provider=lambda: HOJE).act("t-venc", ("view", "home")).text
        self.assertNotIn("vence hoje", texto)          # antes: "1 conta vence hoje"
        self.assertNotIn("vencid", texto.lower())

    def test_checklist_oferece_configurar(self):
        texto = svc.gerar_checklist_pagamentos("2026-11", "faturas")
        self.assertIn("sem vencimento definido", texto)
        self.assertIn("vencimento fatura", texto)

    def test_vencimento_configurado_vale(self):
        svc.definir_vencimento_fatura_por_nome_formatado("vencimento fatura Nubank dia 20")
        item = self.fatura()
        self.assertEqual(item["data"], "2026-11-20")
        self.assertTrue(item["vencimento_definido"])

    def test_vencimento_recorrente_vale_mesmo_sem_fatura_no_mes_de_hoje(self):
        # Compras só em novembro; em 01/12 o cartão não tem fatura no mês corrente.
        # Antes: "Não encontrei uma fatura..." e nada era configurado.
        from tests.relogio_fixo import data_fixa
        with data_fixa(date(2026, 12, 1)):
            resposta = svc.definir_vencimento_fatura_por_nome_formatado("vencimento fatura Nubank dia 20")
        self.assertNotIn("Não encontrei", resposta)
        item = self.fatura()
        self.assertEqual(item["data"], "2026-11-20")
        self.assertTrue(item["vencimento_definido"])

    def test_cartao_inexistente_continua_recusado(self):
        resposta = svc.definir_vencimento_fatura_por_nome_formatado("vencimento fatura Banco Fantasma dia 20")
        self.assertIn("Não encontrei", resposta)


if __name__ == "__main__":
    unittest.main()
