"""Bloco B, complementos (F1-F5) da revisão adversarial.

F1 - "relatório", "resumo" e "saldo do mês" aplicam a mesma regra de B1:
     pagamento de fatura não é despesa; estornos continuam abatendo.
F2 - "contas de pagamento do mês" (resumo_contas_mes_quebrado) idem.
F3 - (removido com o painel web em 13/11/2026) categorias, gastos por conta e desembolso diário somam o
     mesmo total de saídas; sem "-0,0".
F4 - "auditar mês" apresenta as linhas como "Meu mês" sem mudar o resultado.
F5 - Materializar a herança no comando legado mudaria o saldo projetado
     (pendências herdadas passam a ser descontadas), então foi abortado; os
     textos de ajuda deixam de sugerir comandos que hoje são recusados.
"""
import math
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


def _linhas_bloco(texto, titulo):
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


def _moeda_apos(texto, rotulo):
    m = re.search(re.escape(rotulo) + r"\s*(-?R\$ -?[\d\.]+,\d{2})", texto)
    assert m, (rotulo, texto)
    bruto = m.group(1)
    v = _valor(bruto.replace("-", ""))
    return -v if "-" in bruto else v


class Base(unittest.TestCase):
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

    def movimento(self, tipo, valor, cartao, origem=None):
        return db.inserir_fatura_movimento(dict(
            ano_mes=MES, conta_cartao=cartao, tipo_movimento=tipo, valor=valor,
            data_movimento=MES + "-20", conta_origem=origem))

    def cenario_completo(self):
        """Receita 5000; Pix 100 + crédito Itaú 300; fixo Nubank 1200;
        estorno Itaú 50; pagamento total da fatura Nubank 1200 (via Mercado Pago)."""
        self.receita(5000)
        self.despesa(100, "Alimentação", "Mercado Pago", "pix", "Feira")
        self.despesa(300, "Alimentação", "Itaú", "crédito", "Mercado")
        self.fixo(1200, "Moradia", "Nubank")
        self.movimento("estorno", 50, "Itaú")
        self.movimento("pagamento_total", 1200, "Nubank", origem="Mercado Pago")


class HelperUnico(unittest.TestCase):
    def test_services_reexporta_o_mesmo_criterio(self):
        self.assertIs(svc.item_eh_liquidacao_fatura, comp.item_eh_liquidacao_fatura)
        self.assertIs(svc.remover_liquidacoes_fatura, comp.remover_liquidacoes_fatura)
        itens = [
            {"origem": "fatura_movimento", "tipo_movimento": "pagamento_total", "valor": -1},
            {"origem": "fatura_movimento", "tipo_movimento": "pagamento_parcial", "valor": -1},
            {"origem": "fatura_movimento", "tipo_movimento": "estorno", "valor": -1},
            {"origem": "transacao", "tipo_movimento": "pagamento_total", "valor": 1},
        ]
        self.assertEqual(itens[2:], comp.remover_liquidacoes_fatura(itens))


class F1RelatorioResumoSaldo(Base):
    def test_relatorio_bate_com_fechamento(self):
        self.cenario_completo()
        texto = svc.gerar_relatorio_mes(MES)
        ctx = svc.montar_contexto_financeiro(MES)
        self.assertAlmostEqual(1150.0, _moeda_apos(texto, "Compromissos previstos:"))
        self.assertAlmostEqual(ctx["compromissos_previstos"], _moeda_apos(texto, "Compromissos previstos:"))
        self.assertAlmostEqual(ctx["despesas"], _moeda_apos(texto, "Saídas totais previstas/registradas:"))
        saldo = _moeda_apos(texto, "Saldo projetado:")
        self.assertAlmostEqual(3450.0, saldo)
        self.assertAlmostEqual(svc.obter_metricas_resultado_mes(MES)["resultado_projetado_mes"], saldo)
        fech = svc.gerar_fechamento_mensal_formatado(MES)
        self.assertIn("Saldo projetado: R$ 3.450,00", fech)
        self.assertNotIn("-R$", texto)
        self.assertNotIn("R$ -", texto.split("Maiores categorias")[0])

    def test_saldo_do_mes_bate_com_fechamento(self):
        self.cenario_completo()
        texto = svc.gerar_saldo_mes(MES)
        bloco = "\n".join(_linhas_bloco(texto, "Saídas"))
        self.assertIn("R$ 1.150,00", bloco)  # Compromissos
        self.assertIn("R$ 1.550,00", bloco)  # Total
        self.assertIn("R$ 3.450,00", texto.split("Saldo projetado:")[1])

    def test_resumo_compromissos_esperados(self):
        self.cenario_completo()
        texto = svc.gerar_resumo_mes(MES)
        bloco = "\n".join(_linhas_bloco(texto, "Referência dos lançamentos"))
        self.assertIn("R$ 1.150,00", next(l for l in bloco.splitlines() if "Compromissos esperados" in l))

    def test_sem_pagamento_valores_inalterados(self):
        # Só estorno: o estorno continua abatendo, como antes.
        self.receita(1000)
        self.despesa(300, "Alimentação", "Itaú", "crédito")
        self.fixo(200, "Moradia", "Itaú")
        self.movimento("estorno", 40, "Itaú")
        bruto_comp = sum(i["valor"] for i in svc.projetar_pagamentos_mes(MES, incluir_transacoes=False))
        bruto_total = sum(i["valor"] for i in svc.projetar_pagamentos_mes(MES, incluir_transacoes=True))
        self.assertAlmostEqual(160.0, bruto_comp)
        texto = svc.gerar_relatorio_mes(MES)
        self.assertAlmostEqual(bruto_comp, _moeda_apos(texto, "Compromissos previstos:"))
        self.assertAlmostEqual(bruto_total, _moeda_apos(texto, "Saídas totais previstas/registradas:"))
        self.assertAlmostEqual(1000 - bruto_total, _moeda_apos(texto, "Saldo projetado:"))


class F2ContasDePagamento(Base):
    def test_esperado_sem_pagamento_de_fatura(self):
        self.cenario_completo()
        texto = comp.resumo_contas_mes_quebrado(MES)
        self.assertIn("Esperado: R$ 1.150,00", texto)
        self.assertIn("Realizado: R$ 400,00", texto)
        self.assertIn("Total do mês: R$ 1.550,00", texto)
        nubank = next(l for l in texto.splitlines() if l.startswith("- Nubank"))
        self.assertIn("esperado R$ 1.200,00", nubank)
        itau = next(l for l in texto.splitlines() if l.startswith("- Itaú"))
        self.assertIn("esperado R$ -50,00", itau)  # estorno continua abatendo
        self.assertEqual(texto, svc.resumo_contas_mes(MES))

    def test_mes_so_com_pagamento(self):
        self.movimento("pagamento_total", 300, "Nubank", origem="Mercado Pago")
        self.assertIn("Não encontrei pagamentos", comp.resumo_contas_mes_quebrado(MES))


class F4Auditoria(Base):
    def _bloco(self, texto):
        linhas = _linhas_bloco(texto, "Reconciliação")
        idx = next(i for i, l in enumerate(linhas) if "Resultado operacional" in l)
        return linhas, idx

    def test_apresentacao_igual_meu_mes_e_resultado_inalterado(self):
        self.cenario_completo()
        m = svc.obter_metricas_resultado_mes(MES)
        texto = svc.gerar_auditoria_resultado_mes_ux(MES)
        linhas, idx = self._bloco(texto)
        soma = sum(_valor_sinal(l) for l in linhas[:idx])
        self.assertAlmostEqual(m["resultado_projetado_mes"], _valor_status(linhas[idx]), places=2)
        self.assertAlmostEqual(m["resultado_projetado_mes"], soma, places=2)
        self.assertAlmostEqual(3450.0, soma, places=2)
        meu = _linhas_bloco(svc.bloco_resultado_mes(m, compacto=True), "Movimento do mês, sem herança")
        sai = lambda ls: _valor_sinal(next(l for l in ls if "Saídas imediatas" in l))
        esp = lambda ls: _valor_sinal(next(l for l in ls if "Ainda esperado" in l))
        self.assertAlmostEqual(sai(meu), sai(linhas), places=2)
        self.assertAlmostEqual(esp(meu), esp(linhas), places=2)
        self.assertAlmostEqual(-100.0, sai(linhas), places=2)
        self.assertAlmostEqual(-1150.0, esp(linhas), places=2)
        info = linhas[idx + 1:]
        self.assertEqual(1, len(info))
        self.assertIn("Fatura paga, não soma", info[0])
        self.assertIn("R$ 1.200,00", info[0])
        self.assertIn("✅ Os subtotais reconciliam", texto)
        self.assertIn("Pagamentos de fatura já realizados (não somam no resultado)", texto)

    def test_sem_pagamento_sem_linha_informativa(self):
        self.receita(1000)
        self.despesa(100, "Alimentação", "Mercado Pago", "pix")
        self.fixo(200, "Moradia", "Itaú")
        texto = svc.gerar_auditoria_resultado_mes_ux(MES)
        linhas, idx = self._bloco(texto)
        self.assertEqual(idx + 1, len(linhas))
        self.assertAlmostEqual(700.0, _valor_status(linhas[idx]), places=2)
        self.assertNotIn("Pagamentos de fatura já realizados", texto)
        self.assertIn("✅ Os subtotais reconciliam", texto)


class F5TextosDeAjuda(Base):
    def test_saldo_geral_nao_sugere_comando_recusado(self):
        resposta = svc.definir_saldo_inicial_formatado("2026-10", 900)
        self.assertIn("Saldo inicial geral", resposta)
        self.assertNotIn("saldo inicial 2026-10 BTG", resposta)
        self.assertIn("Ajustar saldos atuais", resposta)
        # O que a mensagem diz é verdade: o comando por conta é recusado.
        recusa = svc.definir_saldo_inicial_formatado("2026-10", 100, "BTG")
        self.assertNotIn("Saldo inicial definido", recusa)

    def test_mes_herdado_aceita_e_mes_com_base_geral_recusa(self):
        db.definir_saldo_inicial_conta_mes("2026-10", "Itaú", 1000)
        resposta = svc.definir_saldo_inicial_formatado("2026-11", 100, "Nubank")
        self.assertIn("Saldo inicial definido", resposta)
        self.assertIn("os meses anteriores não mudam", resposta)
        self.assertEqual([], list(db.buscar_saldos_contas_mes("2026-11")))
        db.definir_saldo_inicial_mes("2026-12", 900)
        recusa = svc.definir_saldo_inicial_formatado("2026-12", 100, "Nubank")
        self.assertIn("Ajustar saldos atuais", recusa)
        self.assertIn("saldo inicial geral", recusa)
        self.assertEqual([], list(db.buscar_saldos_contas_mes("2026-12")))

    def test_dica_do_caixa_vazio_aponta_fluxo_e_comando_funciona(self):
        # 2026-08 vem antes da primeira base (setUp): nada a herdar.
        texto = svc.gerar_caixa_por_conta_mes("2026-08")
        self.assertIn("Ajustar saldos atuais", texto)
        self.assertIn("ajustar saldo 2026-08 Itaú para 1000", texto)
        cmd = svc.parsear_comando_saldo_inicial("ajustar saldo 2026-08 Itaú para 1000")
        self.assertIn("Saldo inicial definido", svc.definir_saldo_inicial_formatado(*cmd))

    def test_ajuda_do_app_explica_limitacao(self):
        import app
        for montar in (app.montar_help_saldo, app.montar_help_caixa):
            texto = montar()
            self.assertIn("Ajustar saldos atuais", texto)
            self.assertNotIn("recusado", texto)
            self.assertIn("só essa conta muda", texto)
            self.assertIn("os anteriores não mudam", texto)
        self.assertIn("Ajustar saldos atuais", app.montar_help_caju())
        principal = app.montar_help_principal()
        self.assertIn("Ajustar saldos atuais", principal)
        self.assertNotIn("ajustar saldo 2026-07 Caju para 580,11", principal)


if __name__ == "__main__":
    unittest.main()
