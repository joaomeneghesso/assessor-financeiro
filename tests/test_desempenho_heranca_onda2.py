"""Desempenho da herança de saldo (Onda 2): cache correto e sem dado velho.

- O cache de consulta respeita o corte de conciliação (``conciliacao.referencia``):
  antes, a projeção de um mês calculada sem corte era reaproveitada nas
  pendências herdadas calculadas com o corte do mês seguinte, e o resultado de
  uma tela dependia da ordem das chamadas.
- Os pontos de entrada de leitura (``obter_metricas_resultado_mes``,
  ``calcular_saldo_mensal``, ``calcular_caixa_por_conta_mes``) usam uma conexão
  somente-leitura e um cache só durante a chamada: poucas conexões, e uma
  gravação feita depois é vista na leitura seguinte (mesma sessão e outra).
Sempre em banco temporário.
"""
import sqlite3
import tempfile
import threading
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import conciliacao as cc
import consulta_cache
import database as db
import services as svc


def D(x):
    return Decimal(str(x)).quantize(Decimal("0.01"))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "financeiro.db"
        for nome in ("database", "services", "compromissos", "conciliacao", "reservas_faturas",
                     "saldos_edicao", "pagamentos_canonicos", "fatura_conferencia"):
            mod = __import__(nome)
            if hasattr(mod, "DB_PATH"):
                p = patch.object(mod, "DB_PATH", self.path); p.start(); self.addCleanup(p.stop)
        db.init_db()
        db.definir_saldo_inicial_conta_mes("2026-10", "Itaú", 1000)
        self.aluguel = db.inserir_compromisso(dict(
            tipo="fixo", nome="Aluguel", categoria="Moradia", conta_pagamento="Itaú", conta_origem="Itaú",
            forma_pagamento="pix", valor=300.0, dia_vencimento=10, data_inicio="2026-10-01",
            data_fim=None, parcelas_total=None, ativo=1, origem="teste", observacao=""))

    def tx(self, data, valor, tipo="despesa", descricao="Aluguel"):
        return db.inserir_transacao(dict(
            data=data, tipo=tipo, valor=float(valor), categoria="Moradia", descricao=descricao,
            conta="Itaú", forma_pagamento="pix", mensagem_original="teste"))

    def pagar_outubro_em_novembro(self):
        tid = self.tx("2026-11-02", 300)
        row = dict(db.buscar_compromisso_por_id(self.aluguel))
        cc.vincular_existente(tid, dict(id=self.aluguel, mes="2026-10", assinatura=cc.assinatura_alvo(row)),
                              "teste-vinc-aluguel", "teste")


class CacheRespeitaCorteDeConciliacao(Base):
    def test_ordem_das_chamadas_nao_muda_o_resultado(self):
        self.pagar_outubro_em_novembro()
        isolado = svc.obter_metricas_resultado_mes("2026-11")
        with db.read_only_mode(), svc.contexto_consulta():
            # outubro primeiro: a projeção de outubro (corte em 31/10) entra no cache
            svc.obter_metricas_resultado_mes("2026-10")
            svc.montar_itens_checklist_mes("2026-10")
            depois = svc.obter_metricas_resultado_mes("2026-11")
        with db.read_only_mode(), svc.contexto_consulta():
            so_novembro = svc.obter_metricas_resultado_mes("2026-11")
        for chave in ("saldo_disponivel", "saldo_projetado", "saldo_inicial", "pendencias_herdadas_total"):
            if chave in isolado:
                self.assertEqual(D(isolado[chave]), D(depois[chave]), chave)
                self.assertEqual(D(isolado[chave]), D(so_novembro[chave]), chave)
        self.assertEqual(isolado.get("pendencias_herdadas_itens"), depois.get("pendencias_herdadas_itens"))

    def test_escopo_separa_entradas_do_cache(self):
        chamadas = []
        with consulta_cache.contexto_consulta():
            consulta_cache.obter_ou_calcular(("x",), lambda: chamadas.append(1) or 1)
            with consulta_cache.escopo(("corte", "2026-11-30")):
                consulta_cache.obter_ou_calcular(("x",), lambda: chamadas.append(2) or 2)
                self.assertIsNot(consulta_cache.namespace("n"), None)
            consulta_cache.obter_ou_calcular(("x",), lambda: chamadas.append(3) or 3)
        self.assertEqual([1, 2], chamadas)


class LeituraSemDadoVelho(Base):
    def test_gravar_e_ler_de_novo_na_mesma_sessao(self):
        antes = svc.obter_metricas_resultado_mes("2026-11")
        caixa_antes = svc.calcular_caixa_por_conta_mes("2026-11")["total_disponivel"]
        self.tx("2026-11-05", 50, tipo="receita", descricao="Venda")
        depois = svc.obter_metricas_resultado_mes("2026-11")
        caixa_depois = svc.calcular_caixa_por_conta_mes("2026-11")["total_disponivel"]
        self.assertEqual(D(antes["saldo_disponivel"]) + D(50), D(depois["saldo_disponivel"]))
        self.assertEqual(D(caixa_antes) + D(50), D(caixa_depois))
        # a gravação no mês anterior chega pela herança
        self.tx("2026-10-20", 20, tipo="receita", descricao="Venda")
        self.assertEqual(D(depois["saldo_disponivel"]) + D(20),
                         D(svc.calcular_saldo_mensal("2026-11")["saldo_disponivel"]))

    def test_gravar_e_ler_em_outra_sessao(self):
        antes = svc.obter_metricas_resultado_mes("2026-11")["saldo_disponivel"]
        resultado = {}

        def outra_sessao():
            resultado["m"] = svc.obter_metricas_resultado_mes("2026-11")

        self.tx("2026-11-06", 70, tipo="receita", descricao="Venda")
        t = threading.Thread(target=outra_sessao); t.start(); t.join()
        self.assertEqual(D(svc.obter_metricas_resultado_mes("2026-11")["saldo_disponivel"]),
                         D(resultado["m"]["saldo_disponivel"]))
        self.assertEqual(D(antes) + D(70), D(resultado["m"]["saldo_disponivel"]))

    def test_escrita_continua_possivel_depois_da_leitura(self):
        svc.calcular_saldo_mensal("2026-12")
        self.assertFalse(db._READ_ONLY.get())
        self.assertIsNone(db._READ_CONNECTION.get())
        self.assertIsNone(consulta_cache.cache_atual())
        self.assertTrue(self.tx("2026-12-01", 10))

    def test_poucas_conexoes_por_calculo(self):
        for mes in ("2027-01", "2027-02", "2027-03"):
            self.tx(mes + "-03", 300)
        abertas = []
        original = sqlite3.connect

        def contar(*args, **kwargs):
            abertas.append(args[0] if args else kwargs.get("database"))
            return original(*args, **kwargs)

        with patch.object(sqlite3, "connect", contar):
            svc.obter_metricas_resultado_mes("2027-03")
        # antes: milhares de conexões por cálculo de herança
        self.assertLessEqual(len(abertas), 3, abertas)


class PastaDoBanco(unittest.TestCase):
    def test_pasta_recriada_se_sumir(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / "financeiro.db"
            with patch.object(db, "DB_PATH", path):
                with db.get_connection() as c:
                    c.execute("CREATE TABLE t (x)")
                path.unlink(missing_ok=True)
                for extra in path.parent.glob("*"):
                    extra.unlink()
                path.parent.rmdir()
                with db.get_connection() as c:
                    c.execute("CREATE TABLE t (x)")
                self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
