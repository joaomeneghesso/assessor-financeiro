"""Bloco B (B1 + B5): movimentos de fatura nas telas de gasto.

B1 - Pagamentos de fatura (pagamento_parcial/pagamento_total) são liquidação,
não despesa: não podem aparecer como categoria negativa nem reduzir despesas
em Categorias, Fechamento e contexto do assessor/metas. Estornos,
créditos e ajustes de débito continuam valendo como em "meu mês" (reduzem ou
aumentam as despesas esperadas). Em Compromissos, os movimentos não podem ser
descontados duas vezes.

B5 - O bloco "Movimento do mês" precisa fechar com o Resultado operacional
exibido, sem alterar o valor do resultado.
"""
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import compromissos as comp
import database as db
import services as svc

MES = "2026-09"


def _valor(texto):
    return float(texto.replace("R$", "").replace(".", "").replace(",", ".").strip())


def _linhas_bloco(texto, titulo="Movimento do mês, sem herança"):
    linhas = texto.splitlines()
    inicio = linhas.index(f"┌ {titulo}")
    fim = linhas.index("└", inicio)
    return linhas[inicio + 1:fim]


def _valor_sinal(linha):
    m = re.search(r"([+-])\s*R\$\s*([\d\.]+,\d{2})\s*$", linha)
    assert m, linha
    v = _valor(m.group(2))
    return v if m.group(1) == "+" else -v


def _valor_status(linha):
    m = re.search(r"([+-]?)R\$ ([\d\.]+,\d{2})\s*$", linha)
    assert m, linha
    v = _valor(m.group(2))
    return -v if m.group(1) == "-" else v


class BaseFaturaTelas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        caminho = Path(self.tmp.name) / "financeiro.db"
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", caminho)
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        db.definir_saldo_inicial_conta_mes(MES, "Mercado Pago", 10000)

    def receita(self, valor, conta="Mercado Pago"):
        return db.inserir_transacao(dict(
            data=MES + "-05", tipo="receita", valor=valor, categoria="Salário",
            descricao="Salário", conta=conta, forma_pagamento="pix", parcelas_total=1))

    def despesa(self, valor, categoria, conta, forma, nome="Compra"):
        return db.inserir_transacao(dict(
            data=MES + "-06", tipo="despesa", valor=valor, categoria=categoria,
            descricao=nome, conta=conta, forma_pagamento=forma, parcelas_total=1))

    def fixo(self, valor, categoria, conta, nome="Aluguel"):
        return db.inserir_compromisso(dict(
            tipo="fixo", nome=nome, categoria=categoria, conta_pagamento=conta,
            forma_pagamento="crédito", valor=valor, data_inicio="2026-08-01",
            dia_vencimento=10, ativo=1))

    def movimento(self, tipo, valor, cartao, origem=None, mes=MES):
        return db.inserir_fatura_movimento(dict(
            ano_mes=mes, conta_cartao=cartao, tipo_movimento=tipo, valor=valor,
            data_movimento=mes + "-20", conta_origem=origem))

    def cenario_completo(self):
        """Receita 5000; Pix 100 + crédito Itaú 300 (Alimentação); fixo Nubank
        1200 (Moradia); estorno Itaú 50; pagamento total da fatura Nubank 1200."""
        self.receita(5000)
        self.despesa(100, "Alimentação", "Mercado Pago", "pix", "Feira")
        self.despesa(300, "Alimentação", "Itaú", "crédito", "Mercado")
        self.fixo(1200, "Moradia", "Nubank")
        self.movimento("estorno", 50, "Itaú")
        self.movimento("pagamento_total", 1200, "Nubank", origem="Mercado Pago")


class CategoriasSemPagamentoDeFatura(BaseFaturaTelas):
    def test_categorias_excluem_pagamento_e_mantem_estorno(self):
        self.cenario_completo()
        texto = svc.listar_categorias_mes(MES)
        m = svc.obter_metricas_resultado_mes(MES)
        total = _valor(re.search(r"Total previsto\s+(R\$ [\d\.,]+)", texto).group(1))
        # Total de categorias = total de saídas de "meu mês" (estorno abate).
        self.assertAlmostEqual(1550.0, m["total_saidas_mes"], places=2)
        self.assertAlmostEqual(m["total_saidas_mes"], total, places=2)
        self.assertNotIn("-R$ 1.200,00", texto)
        self.assertNotIn("1.250,00", texto)
        bloco_ajuste = texto.split("Ajuste de fatura")[1].splitlines()[1]
        self.assertIn("R$ -50,00", bloco_ajuste)

    def test_detalhe_da_categoria_ajuste_mostra_so_estorno(self):
        self.cenario_completo()
        texto = svc.detalhar_categoria_mes("Ajuste de fatura", MES)
        self.assertIn("R$ -50,00", texto)
        self.assertNotIn("1.200,00", texto)
        self.assertIn(f"│ {'Itens':<24} {1:>14}", texto)

    def test_mes_so_com_estornos_mantem_resultado_antigo(self):
        self.despesa(300, "Alimentação", "Itaú", "crédito")
        self.movimento("estorno", 40, "Itaú")
        texto = svc.listar_categorias_mes(MES)
        self.assertIn("R$ 260,00", texto)
        self.assertIn("R$ -40,00", texto)


class CompromissosSemDuplaContagem(BaseFaturaTelas):
    def _linha(self, texto, rotulo):
        return next(l for l in texto.splitlines() if l.startswith(f"│ {rotulo}"))

    def _num(self, texto, rotulo):
        linha = self._linha(texto, rotulo)
        m = re.search(r"([+-]?)\s*R\$\s*(-?)([\d\.]+,\d{2})\s*$", linha)
        self.assertIsNotNone(m, linha)
        v = _valor(m.group(3))
        return -v if "-" in (m.group(1) + m.group(2)) else v

    def test_estorno_descontado_uma_unica_vez(self):
        self.despesa(300, "Alimentação", "Itaú", "crédito")
        self.fixo(200, "Moradia", "Itaú")
        self.movimento("estorno", 50, "Itaú")
        texto = svc.gerar_compromissos_ux(MES)
        self.assertAlmostEqual(200.0, self._num(texto, "Compromissos esperados"))
        self.assertAlmostEqual(500.0, self._num(texto, "Total bruto"))
        self.assertAlmostEqual(-50.0, self._num(texto, "Créditos/estornos"))
        self.assertAlmostEqual(450.0, self._num(texto, "Saldo a pagar"))
        restante = comp.calcular_fatura_unificada(MES, "Itaú")["saldo_restante"]
        self.assertAlmostEqual(450.0, restante, places=2)
        self.assertNotIn("Ajuste de fatura", texto)

    def test_pagamento_e_credito_uma_unica_vez(self):
        self.cenario_completo()
        self.movimento("credito", 7, "Itaú")
        texto = svc.gerar_compromissos_ux(MES)
        self.assertAlmostEqual(1200.0, self._num(texto, "Compromissos esperados"))
        self.assertAlmostEqual(1500.0, self._num(texto, "Total bruto"))
        self.assertAlmostEqual(-57.0, self._num(texto, "Créditos/estornos"))
        self.assertAlmostEqual(-1200.0, self._num(texto, "Pagamentos de fatura"))
        # 1500 - 57 - 1200: só sobra a fatura Itaú (300 - 57); Nubank está paga.
        self.assertAlmostEqual(243.0, self._num(texto, "Saldo a pagar"))
        restantes = sum(
            max(0.0, comp.calcular_fatura_unificada(MES, c)["saldo_restante"])
            for c in ("Itaú", "Nubank"))
        self.assertAlmostEqual(243.0, restantes, places=2)

    def test_sem_movimentos_tela_inalterada(self):
        self.despesa(300, "Alimentação", "Itaú", "crédito")
        self.fixo(200, "Moradia", "Itaú")
        texto = svc.gerar_compromissos_ux(MES)
        self.assertAlmostEqual(500.0, self._num(texto, "Saldo a pagar"))
        self.assertIn("- Moradia: R$ 200,00", texto)


class FechamentoEContextoAssessor(BaseFaturaTelas):
    def test_contexto_bate_com_meu_mes(self):
        self.cenario_completo()
        db.definir_meta("Alimentação", 380)
        db.definir_meta("Moradia", 5000)
        ctx = svc.montar_contexto_financeiro(MES)
        m = svc.obter_metricas_resultado_mes(MES)
        self.assertAlmostEqual(m["total_saidas_mes"], ctx["despesas"], places=2)
        self.assertAlmostEqual(1150.0, ctx["compromissos_previstos"], places=2)
        self.assertAlmostEqual(m["resultado_projetado_mes"], ctx["receitas"] - ctx["despesas"], places=2)
        cats = {c["categoria"]: c["total"] for c in ctx["categorias"]}
        self.assertAlmostEqual(-50.0, cats["Ajuste de fatura"], places=2)
        self.assertAlmostEqual(400.0, cats["Alimentação"], places=2)
        metas = {x["categoria"]: x for x in ctx["metas_status"]}
        self.assertEqual("acima", metas["Alimentação"]["status"])
        self.assertAlmostEqual(400.0, metas["Alimentação"]["gasto"], places=2)
        self.assertEqual("ok", metas["Moradia"]["status"])

    def test_texto_do_fechamento(self):
        self.cenario_completo()
        texto = svc.gerar_fechamento_mensal_formatado(MES)
        self.assertIn("Despesas/compromissos previstos: R$ 1.550,00", texto)
        self.assertIn("Saldo projetado: R$ 3.450,00", texto)
        self.assertIn("Fixos/parcelas previstos: R$ 1.150,00", texto)
        self.assertNotIn("-R$", texto)

    def test_meses_futuros_ignoram_pagamento_de_fatura(self):
        self.cenario_completo()
        futuros = svc.calcular_parcelas_futuras_por_mes("2026-08")
        self.assertAlmostEqual(1150.0, futuros[MES], places=2)


class MovimentoDoMesFecha(BaseFaturaTelas):
    def _conferir(self, compacto):
        m = svc.obter_metricas_resultado_mes(MES)
        linhas = _linhas_bloco(svc.bloco_resultado_mes(m, compacto=compacto))
        idx = next(i for i, l in enumerate(linhas) if "Resultado operacional" in l)
        soma = sum(_valor_sinal(l) for l in linhas[:idx])
        resultado = _valor_status(linhas[idx])
        self.assertAlmostEqual(resultado, soma, places=2)
        self.assertAlmostEqual(m["resultado_projetado_mes"], resultado, places=2)
        return m, linhas, idx

    def test_bloco_fecha_com_pagamento_de_fatura(self):
        self.cenario_completo()
        for compacto in (False, True):
            m, linhas, idx = self._conferir(compacto)
            self.assertAlmostEqual(3450.0, m["resultado_projetado_mes"], places=2)
            self.assertAlmostEqual(1300.0, m["saidas_imediatas_realizadas"], places=2)
            self.assertAlmostEqual(1200.0, m["saidas_pagamentos_fatura"], places=2)
            self.assertAlmostEqual(-100.0, _valor_sinal(next(l for l in linhas if "Saídas imediatas" in l)))
            info = linhas[idx + 1:]
            self.assertEqual(1, len(info))
            self.assertIn("Fatura paga, não soma", info[0])
            self.assertIn("R$ 1.200,00", info[0])

    def test_sem_pagamento_bloco_identico_ao_anterior(self):
        self.receita(5000)
        self.despesa(100, "Alimentação", "Mercado Pago", "pix")
        self.movimento("estorno", 10, "Itaú")
        m = svc.obter_metricas_resultado_mes(MES)
        self.assertEqual(0.0, m["saidas_pagamentos_fatura"])
        for compacto in (False, True):
            _, linhas, idx = self._conferir(compacto)
            self.assertEqual(idx + 1, len(linhas))
        legado = dict(m)
        legado.pop("saidas_pagamentos_fatura")
        self.assertEqual(svc.bloco_resultado_mes(m), svc.bloco_resultado_mes(legado))

    def test_valores_de_caixa_e_resultado_preservados(self):
        self.cenario_completo()
        m = svc.obter_metricas_resultado_mes(MES)
        self.assertAlmostEqual(10000 + 5000 - 100 - 1200, m["saldo_disponivel"], places=2)
        self.assertAlmostEqual(400.0, m["total_saidas_realizadas_mes"], places=2)
        self.assertAlmostEqual(1150.0, m["despesas_esperadas_total"], places=2)
        self.assertAlmostEqual(1200.0, m["compensacao_pagamentos_fatura"], places=2)
        texto = svc.processar_mensagem(f"meu mês {MES}")
        self.assertIn("Resultado operacional", texto)


if __name__ == "__main__":
    unittest.main()
