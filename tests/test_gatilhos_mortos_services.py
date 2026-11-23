"""Gatilhos de services._processar_mensagem_core que eram inalcançáveis.

Caracteriza QUAL função responde a cada texto (as respostas reais são trocadas por
marcadores, num banco temporário). Prova que as regras removidas eram mortas
(uma regra anterior já capturava o texto) e que as irmãs vivas continuam iguais.
Também cobre "quanto vou pagar este mês" (referência ao mês vigente).
"""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import database as db
import services as svc
from tests.relogio_fixo import data_fixa

GERADORES = (
    "gerar_saldo_mes_ux", "gerar_saldo_mes", "gerar_caixa_por_conta_mes", "gerar_meu_mes_curto_ux",
    "gerar_resumo_mes", "gerar_compromissos_ux", "listar_compromissos_formatado", "gerar_revisao_inteligente",
    "analisar_csv_importacao", "listar_ultimas", "listar_ultimas_paginado",
    "montar_lista_transacoes_paginada", "resumo_pagamento_mes_consolidado", "resumo_pagamento_por_conta",
)


def _marcador(nome):
    return lambda *a, **k: f"<{nome}{a}>"


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", Path(self.tmp.name) / "fixture.db")
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        for nome in GERADORES:
            p = patch.object(svc, nome, _marcador(nome))
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(svc, "buscar_ultimas_transacoes", lambda n: [])
        p.start()
        self.addCleanup(p.stop)
        # Os geradores recebem o mês de hoje: fixa o dia.
        self.enterContext(data_fixa(date(2026, 11, 9)))
        self.mes = "2026-11"

    def rota(self, texto):
        return svc.processar_mensagem(texto, sessao="t")


class GatilhosMortosTests(_Base):

    def test_caixa_vai_para_caixa_por_conta(self):
        self.assertEqual(f"<gerar_caixa_por_conta_mes('{self.mes}',)>", self.rota("caixa"))
        # "caixa mensal" não é capturado pelo caixa por conta: segue para o saldo.
        self.assertEqual(f"<gerar_saldo_mes_ux('{self.mes}',)>", self.rota("caixa mensal"))

    def test_compromissos_e_listar_compromissos(self):
        esperado = f"<gerar_compromissos_ux('{self.mes}',)>"
        for texto in ("compromissos", "listar compromissos", "meus compromissos"):
            with self.subTest(texto=texto):
                self.assertEqual(esperado, self.rota(texto))
        self.assertNotIn("listar_compromissos_formatado", self.rota("compromissos"))

    def test_revisar_vai_para_revisao_inteligente(self):
        for texto in ("revisar", "revisao", "revisão", "revisar base"):
            with self.subTest(texto=texto):
                self.assertEqual("<gerar_revisao_inteligente()>", self.rota(texto))
        for texto in ("analisar csv", "importar csv", "prever importacao csv"):
            with self.subTest(texto=texto):
                self.assertEqual("<analisar_csv_importacao('t',)>", self.rota(texto))

    def test_resumo_do_mes_vai_para_meu_mes_curto(self):
        esperado = f"<gerar_meu_mes_curto_ux('{self.mes}',)>"
        for texto in ("resumo do mês", "resumo do mes", "meu mês"):
            with self.subTest(texto=texto):
                self.assertEqual(esperado, self.rota(texto))
        # Só "resumo mensal" chega ao resumo antigo.
        self.assertEqual("<gerar_resumo_mes()>", self.rota("resumo mensal"))

    def test_resumo_aaaa_mm_vai_para_meu_mes_curto(self):
        self.assertEqual("<gerar_meu_mes_curto_ux('2026-07',)>", self.rota("resumo 2026-07"))

    def test_saldo_do_mes_e_saldo_aaaa_mm_vao_para_saldo_ux(self):
        for texto in ("saldo do mês", "saldo do mes"):
            with self.subTest(texto=texto):
                self.assertEqual(f"<gerar_saldo_mes_ux('{self.mes}',)>", self.rota(texto))
        self.assertEqual("<gerar_saldo_mes_ux('2026-07',)>", self.rota("saldo 2026-07"))
        self.assertEqual("<gerar_caixa_por_conta_mes('2026-07',)>", self.rota("caixa 2026-07"))

    def test_ultimas_transacoes_e_ultimas_n(self):
        # "últimas ..." cai na regra de filtro (a regra de lista exata era inalcançável).
        self.assertEqual("<listar_ultimas_paginado(1, 'transações')>", self.rota("últimas transações"))
        self.assertEqual("<listar_ultimas_paginado(1, 'transacoes')>", self.rota("ultimas transacoes"))
        self.assertEqual("<listar_ultimas_paginado(1, 'mercado')>", self.rota("últimas mercado"))
        for texto in ("últimas 5", "ultimas 5"):
            with self.subTest(texto=texto):
                self.assertEqual("<montar_lista_transacoes_paginada([], '📌 Últimas 5 transações', 1)>", self.rota(texto))
        # Sem limite de 100 para "últimas N" (comportamento atual, mantido).
        self.assertIn("Últimas 500 transações", self.rota("últimas 500"))

    def test_ultimos_continuam_vivos(self):
        self.assertEqual("<listar_ultimas()>", self.rota("últimos lançamentos"))
        self.assertEqual("<listar_ultimas()>", self.rota("ultimos lancamentos"))
        self.assertEqual("<listar_ultimas(5,)>", self.rota("ultimos 5"))
        self.assertEqual("<listar_ultimas(100,)>", self.rota("últimos 100"))
        self.assertIn("maior que zero", self.rota("ultimos 0"))
        self.assertIn("no máximo: últimas 100", self.rota("ultimos 101"))


class QuantoVouPagarMesVigenteTests(_Base):
    def test_referencias_ao_mes_vigente(self):
        esperado = f"<resumo_pagamento_mes_consolidado('{self.mes}',)>"
        for texto in (
            "quanto vou pagar", "quanto vou pagar no mês", "quanto vou pagar em este mes",
            "quanto vou pagar em esse mês", "quanto vou pagar em mês atual", "quanto vou pagar em mes atual",
            "quanto vou pagar em neste mês", "quanto vou pagar este mes", "quanto vou pagar esse mês",
            "quanto vou pagar neste mês", "quanto vou pagar nesse mes", "quanto vou pagar mês atual",
            "quanto vou pagar no mês atual",
        ):
            with self.subTest(texto=texto):
                self.assertEqual(esperado, self.rota(texto))

    def test_outros_meses_e_conta_inalterados(self):
        self.assertEqual("<resumo_pagamento_mes_consolidado('2026-11',)>", self.rota("quanto vou pagar em novembro 2026"))
        self.assertEqual("<resumo_pagamento_mes_consolidado('2026-07',)>", self.rota("quanto vou pagar em 2026-07"))
        self.assertEqual(f"<resumo_pagamento_por_conta('{self.mes}', 'nubank')>", self.rota("quanto vou pagar no nubank"))
        self.assertIn("Mês inválido", self.rota("quanto vou pagar em xyz"))


if __name__ == "__main__":
    unittest.main()
