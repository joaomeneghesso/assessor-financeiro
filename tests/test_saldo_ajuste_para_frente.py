"""Saldo inicial de uma conta em mês que herda o saldo: "levado para frente".

Regra do dono: o novo saldo vale do mês informado em diante, nunca para trás.
Em mês herdado, 'saldo inicial AAAA-MM <conta> <valor>' muda só o saldo
inicial dessa conta; o total do mês muda exatamente pela diferença; as
pendências herdadas (já abatidas no saldo livre herdado) não são descontadas
de novo; os meses seguintes herdam; os anteriores não mudam. A mudança é
auditada na mesma gravação e se desfaz com 'saldo inicial AAAA-MM <conta>
herdado' (ou informando o próprio valor herdado): a conta volta a herdar e as
correções feitas depois nos meses anteriores voltam a chegar a ela. Sempre em
banco temporário.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database as db
import services as svc
from tests.relogio_fixo import data_fixa

MESES = ("2026-09", "2026-10", "2026-11", "2026-12", "2027-01")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "financeiro.db"
        for module in (db, svc):
            p = patch.object(module, "DB_PATH", self.path); p.start(); self.addCleanup(p.stop)
        db.init_db()
        # Outubro tem bases por conta; novembro em diante herda.
        db.definir_saldo_inicial_conta_mes("2026-10", "Itaú", 1000)
        db.definir_saldo_inicial_conta_mes("2026-10", "Mercado Pago", 2000)
        # Obrigação de outubro não paga: vira pendência herdada em novembro,
        # já abatida no saldo livre herdado.
        db.inserir_compromisso(dict(tipo="fixo", nome="Aluguel", categoria="Moradia", conta_pagamento="Itaú",
                                    forma_pagamento="pix", valor=300, dia_vencimento=10,
                                    data_inicio="2026-10-01", data_fim="2026-10-31", ativo=True))
        # Obrigação nova em dezembro (a projeção de dezembro também a desconta).
        db.inserir_compromisso(dict(tipo="fixo", nome="Escola", categoria="Educação", conta_pagamento="Mercado Pago",
                                    forma_pagamento="pix", valor=120, dia_vencimento=5,
                                    data_inicio="2026-12-01", data_fim="2026-12-31", ativo=True))

    def rows(self, sql, *args):
        with db.get_connection() as c:
            return [tuple(r) for r in c.execute(sql, args).fetchall()]

    def eventos(self):
        return self.rows("SELECT entidade_id, operacao, dados_antes, dados_depois FROM auditoria_eventos "
                         "WHERE entidade = ? ORDER BY id", svc.ENTIDADE_SALDO_INICIAL_HERANCA)

    def foto(self):
        out = {}
        for m in MESES:
            s = svc.calcular_saldo_mensal(m)
            c = svc.calcular_caixa_por_conta_mes(m)
            out[m] = {
                "saldo": s, "caixa": c,
                "contas": {k: (v["inicial"], v["disponivel"]) for k, v in c["contas"].items()},
                "por_conta": {k: (svc.calcular_saldo_mensal(m, k)["saldo_inicial"],
                                  svc.calcular_saldo_mensal(m, k)["saldo_projetado"]) for k in c["contas"]},
            }
        return out

    def comando(self, texto):
        cmd = svc.parsear_comando_saldo_inicial(texto)
        self.assertIsNotNone(cmd, texto)
        return svc.definir_saldo_inicial_formatado(*cmd)


class LevadoParaFrente(Base):
    def test_cenario_tem_pendencia_herdada_ja_abatida(self):
        nov = svc.calcular_saldo_mensal("2026-11")
        self.assertTrue(nov["saldo_herdado_auto"])
        self.assertAlmostEqual(300.0, nov["pendencias_herdadas_total_bruto"])
        self.assertAlmostEqual(0.0, nov["pendencias_herdadas_total"])
        self.assertAlmostEqual(2700.0, nov["saldo_inicial"])

    def _verificar_delta(self, antes, depois, conta, delta):
        # (1) meses anteriores idênticos, inclusive todos os campos.
        for m in ("2026-09", "2026-10"):
            self.assertEqual(antes[m]["saldo"], depois[m]["saldo"], m)
            self.assertEqual(antes[m]["caixa"], depois[m]["caixa"], m)
            self.assertEqual(antes[m]["por_conta"], depois[m]["por_conta"], m)
        # (2) no mês: só a conta muda; total muda exatamente pelo delta; o mês
        # continua herdado e as pendências herdadas não são descontadas de novo.
        a, d = antes["2026-11"], depois["2026-11"]
        self.assertTrue(d["saldo"]["saldo_herdado_auto"])
        self.assertTrue(d["caixa"]["herdado_auto"])
        self.assertAlmostEqual(0.0, d["saldo"]["pendencias_herdadas_total"])
        self.assertAlmostEqual(a["saldo"]["pendencias_herdadas_total_bruto"], d["saldo"]["pendencias_herdadas_total_bruto"])
        for chave in ("saldo_inicial", "saldo_disponivel", "saldo_projetado"):
            self.assertAlmostEqual(a["saldo"][chave] + delta, d["saldo"][chave], places=6, msg=chave)
        self.assertAlmostEqual(a["caixa"]["total_inicial"] + delta, d["caixa"]["total_inicial"], places=6)
        for nome, valores in a["contas"].items():
            if not svc.mesma_conta_saldo(nome, conta):
                self.assertEqual(valores, d["contas"][nome], nome)
                # "saldo Itaú" é a visão centralizada (= total do mês); as
                # demais contas são individuais e não mudam.
                if not svc.conta_centraliza_fluxo_mensal(nome):
                    self.assertEqual(a["por_conta"][nome], d["por_conta"][nome], nome)
        # (3) meses seguintes herdam a diferença.
        for m in ("2026-12", "2027-01"):
            for chave in ("saldo_inicial", "saldo_projetado"):
                self.assertAlmostEqual(antes[m]["saldo"][chave] + delta, depois[m]["saldo"][chave], places=6, msg=(m, chave))
            self.assertAlmostEqual(antes[m]["caixa"]["total_inicial"] + delta, depois[m]["caixa"]["total_inicial"], places=6)
            self.assertTrue(depois[m]["saldo"]["saldo_herdado_auto"])

    def test_conta_existente_muda_so_ela_e_propaga_para_frente(self):
        antes = self.foto()
        herdado = antes["2026-11"]["contas"]["Mercado Pago"][0]
        resposta = self.comando("saldo inicial 2026-11 Mercado Pago 500")
        self.assertIn("Saldo inicial definido", resposta)
        self.assertIn("Para voltar a herdar", resposta)
        self.assertIn("saldo inicial 2026-11 Mercado Pago herdado", resposta)
        depois = self.foto()
        self._verificar_delta(antes, depois, "Mercado Pago", 500 - herdado)
        self.assertAlmostEqual(500.0, depois["2026-11"]["contas"]["Mercado Pago"][0])
        self.assertAlmostEqual(500.0, depois["2026-11"]["por_conta"]["Mercado Pago"][0])
        # Nenhuma base foi criada (a herança continua ligada).
        self.assertEqual([], self.rows("SELECT * FROM saldos_mensais_contas WHERE ano_mes >= '2026-11'"))
        self.assertEqual([], self.rows("SELECT * FROM saldos_mensais WHERE ano_mes >= '2026-11'"))

    def test_conta_nova_entra_com_o_valor_e_as_outras_ficam(self):
        antes = self.foto()
        self.assertNotIn("Nubank", antes["2026-11"]["contas"])
        self.comando("ajustar saldo 2026-11 Nubank para 100")
        depois = self.foto()
        self._verificar_delta(antes, depois, "Nubank", 100.0)
        self.assertEqual((100.0, 100.0), depois["2026-11"]["contas"]["Nubank"])
        self.assertAlmostEqual(100.0, depois["2026-12"]["contas"]["Nubank"][0])

    def test_auditado_e_desfeito_repetindo_o_comando(self):
        antes = self.foto()
        herdado = antes["2026-11"]["contas"]["Itaú"][0]
        self.comando("saldo inicial 2026-11 Itaú 50")
        resposta = self.comando("saldo inicial 2026-11 Nubank 0")
        self.assertIn("Saldo inicial definido", resposta)
        eventos = self.eventos()
        self.assertEqual(["2026-11:Itaú", "2026-11:Nubank"], [e[0] for e in eventos])
        self.assertEqual({"saldo_inicial_definido"}, {e[1] for e in eventos})
        antes_ev, depois_ev = json.loads(eventos[0][2]), json.loads(eventos[0][3])
        self.assertAlmostEqual(herdado, antes_ev["saldo_inicial"])
        self.assertAlmostEqual(herdado, antes_ev["saldo_herdado"])
        self.assertIsNone(antes_ev["definido_anterior"])
        self.assertEqual("Itaú", depois_ev["conta"])
        self.assertAlmostEqual(50.0, depois_ev["saldo_inicial"])
        self.assertAlmostEqual(antes["2026-11"]["saldo"]["saldo_inicial"] - herdado + 50, depois_ev["saldo_inicial_mes"])
        # Desfazer: o comando sugerido faz a conta voltar a herdar.
        resposta = self.comando("saldo inicial 2026-11 Itaú 25")
        sugestao = next(l for l in resposta.splitlines() if l.startswith("saldo inicial 2026-11 Itaú "))
        self.assertEqual("saldo inicial 2026-11 Itaú herdado", sugestao)
        resposta = self.comando(sugestao)
        self.assertIn("voltou a ser herdado", resposta)
        self.assertEqual("saldo_inicial_herdado", self.eventos()[-1][1])
        self.comando("saldo inicial 2026-11 Nubank herdado")
        depois = self.foto()
        for m in MESES:
            for chave in ("saldo_inicial", "saldo_disponivel", "saldo_projetado"):
                self.assertAlmostEqual(antes[m]["saldo"][chave], depois[m]["saldo"][chave], places=6, msg=(m, chave))
            self.assertEqual(antes[m]["contas"].keys(), depois[m]["contas"].keys(), m)
            for nome in antes[m]["contas"]:
                for x, y in zip(antes[m]["contas"][nome], depois[m]["contas"][nome]):
                    self.assertAlmostEqual(x, y, places=6, msg=(m, nome))

    def test_valor_negativo_e_zero_por_conta(self):
        self.assertEqual(("2026-11", 0.0, "Nubank"), svc.parsear_comando_saldo_inicial("saldo inicial 2026-11 Nubank 0"))
        self.assertEqual(("2026-11", -50.25, "Itaú"), svc.parsear_comando_saldo_inicial("ajustar saldo 2026-11 Itaú para -50,25"))
        self.assertEqual(("2026-11", -50.25, "Itaú"), svc.parsear_comando_saldo_inicial("saldo inicial 2026-11 Itaú -50,25"))
        # Saldo geral continua exigindo valor positivo.
        self.assertIsNone(svc.parsear_comando_saldo_inicial("saldo inicial 2026-11 0"))
        self.assertIsNone(svc.parsear_comando_saldo_inicial("saldo inicial 2026-11 -5"))
        antes = self.foto()
        herdado = antes["2026-11"]["contas"]["Itaú"][0]
        self.comando("ajustar saldo 2026-11 Itaú para -50,25")
        self._verificar_delta(antes, self.foto(), "Itaú", -50.25 - herdado)

    def test_textos_mostram_o_valor_definido(self):
        self.comando("saldo inicial 2026-11 Nubank 100")
        caixa = svc.gerar_caixa_por_conta_mes("2026-11")
        self.assertIn("✏️ Nubank: R$ 100,00 (herdado: R$ 0,00)", caixa)
        self.assertNotIn("o total bate com o Saldo livre herdado", caixa)
        saldo = svc.processar_mensagem("saldo 2026-11")
        self.assertIn("Saldo livre herdado: R$ 2.700,00", saldo)
        self.assertIn("Saldo inicial do mês: R$ 2.800,00", saldo)
        meu = svc.bloco_heranca_mes_anterior(svc.calcular_saldo_mensal("2026-11"))
        self.assertIn("Saldo inicial do mês: R$ 2.800,00", meu)
        # Dezembro só herda (sem marca de valor definido).
        self.assertNotIn("✏️", svc.gerar_caixa_por_conta_mes("2026-12"))


class Preservacao(Base):
    def test_sem_valor_definido_resultados_nao_ganham_campos(self):
        for m in MESES:
            self.assertNotIn("saldos_iniciais_definidos_heranca", svc.calcular_saldo_mensal(m))
            self.assertNotIn("saldos_iniciais_definidos_heranca", svc.calcular_caixa_por_conta_mes(m))
        self.assertIn("o total bate com o Saldo livre herdado", svc.gerar_caixa_por_conta_mes("2026-11"))

    def test_mes_com_bases_mantem_gravacao_de_base(self):
        resposta = self.comando("saldo inicial 2026-10 Itaú 700")
        self.assertIn("Saldo inicial definido", resposta)
        self.assertEqual([("Itaú", 700.0), ("Mercado Pago", 2000.0)],
                         self.rows("SELECT conta, saldo_inicial FROM saldos_mensais_contas WHERE ano_mes='2026-10' ORDER BY conta"))
        self.assertEqual([], self.eventos())

    def test_mes_com_base_geral_continua_recusado(self):
        db.definir_saldo_inicial_mes("2026-12", 900)
        resposta = self.comando("saldo inicial 2026-12 Nubank 100")
        self.assertNotIn("Saldo inicial definido", resposta)
        self.assertIn("saldo inicial geral", resposta)
        self.assertEqual([], self.rows("SELECT * FROM saldos_mensais_contas WHERE ano_mes='2026-12'"))
        self.assertEqual([], self.eventos())

    def test_forma_de_pagamento_nao_e_conta(self):
        resposta = self.comando("saldo inicial 2026-11 pix 100")
        self.assertIn("formas de pagamento", resposta)
        self.assertEqual([], self.eventos())

    def test_base_surgida_antes_da_gravacao_recusa_sem_gravar(self):
        db.definir_saldo_inicial_conta_mes("2026-11", "Itaú", 10)
        with self.assertRaises(ValueError):
            svc._definir_saldo_inicial_conta_herdada("2026-11", "Nubank", 100)
        self.assertEqual([], self.eventos())

    def test_falha_na_auditoria_nao_grava_nada(self):
        antes = self.foto()
        with patch.object(svc, "registrar_auditoria", side_effect=RuntimeError("falha induzida")):
            with self.assertRaises(RuntimeError):
                svc._definir_saldo_inicial_conta_herdada("2026-11", "Nubank", 100)
        self.assertEqual([], self.eventos())
        depois = self.foto()
        for m in MESES:
            self.assertEqual(antes[m]["saldo"], depois[m]["saldo"], m)

    def test_base_posterior_no_mes_prevalece_sobre_valor_definido(self):
        self.comando("saldo inicial 2026-11 Nubank 100")
        db.definir_saldo_inicial_conta_mes("2026-11", "Itaú", 10)
        s = svc.calcular_saldo_mensal("2026-11")
        self.assertFalse(s["saldo_herdado_auto"])
        self.assertAlmostEqual(10.0, s["saldo_inicial"])
        self.assertNotIn("saldos_iniciais_definidos_heranca", s)



class VoltarAHerdar(Base):
    """Desfazer de verdade: a conta volta a herdar e o mês volta a acompanhar
    as correções feitas depois nos meses anteriores."""

    def gasto_outubro(self, valor, conta="Mercado Pago"):
        db.inserir_transacao(dict(data="2026-10-15", tipo="despesa", valor=valor, categoria="Compras",
                                  descricao="Correção", conta=conta, forma_pagamento="pix"))

    def test_correcao_posterior_em_mes_anterior_volta_a_chegar(self):
        # Cenário do revisor: definir, voltar ao herdado e lançar em outubro.
        antes = self.foto()
        herdado = antes["2026-11"]["contas"]["Mercado Pago"][0]
        self.comando("saldo inicial 2026-11 Mercado Pago 5000")
        self.comando(f"saldo inicial 2026-11 Mercado Pago {svc._valor_para_comando(herdado)}")
        self.assertEqual("saldo_inicial_herdado", self.eventos()[-1][1])
        self.gasto_outubro(100)
        out = svc.calcular_saldo_mensal("2026-10")["saldo_projetado"]
        nov = svc.calcular_saldo_mensal("2026-11")
        self.assertNotIn("saldos_iniciais_definidos_heranca", nov)
        self.assertAlmostEqual(out, nov["saldo_inicial"], places=6)
        self.assertAlmostEqual(antes["2026-11"]["saldo"]["saldo_inicial"] - 100, nov["saldo_inicial"], places=6)

    def test_comando_herdado_igual_a_nunca_ter_definido(self):
        self.comando("saldo inicial 2026-11 Itaú 50")
        self.comando("saldo inicial 2026-11 Itaú herdado")
        self.gasto_outubro(70, "Itaú")
        com_historico = self.foto()
        # Referência: banco idêntico sem nunca ter definido nada.
        with db.get_connection() as c:
            c.execute("DELETE FROM auditoria_eventos WHERE entidade = ?", (svc.ENTIDADE_SALDO_INICIAL_HERANCA,))
            c.commit()
        referencia = self.foto()
        for m in MESES:
            self.assertEqual(referencia[m]["saldo"], com_historico[m]["saldo"], m)
            self.assertEqual(referencia[m]["caixa"], com_historico[m]["caixa"], m)
            self.assertEqual(referencia[m]["por_conta"], com_historico[m]["por_conta"], m)

    def test_herdado_sem_valor_definido_nao_grava(self):
        resposta = self.comando("saldo inicial 2026-11 Itaú herdado")
        self.assertIn("já usa o saldo herdado", resposta)
        self.assertIn("Nada foi alterado", resposta)
        self.assertEqual([], self.eventos())
        # Valor igual ao herdado sem definição prévia: grava como definido
        # (comportamento anterior), sem efeito no saldo.
        antes = self.foto()
        herdado = antes["2026-11"]["contas"]["Itaú"][0]
        self.comando(f"saldo inicial 2026-11 Itaú {svc._valor_para_comando(herdado)}")
        self.assertEqual(["saldo_inicial_definido"], [e[1] for e in self.eventos()])

    def test_herdado_em_mes_sem_heranca_recusa(self):
        resposta = self.comando("saldo inicial 2026-10 Itaú herdado")
        self.assertIn("não herda", resposta)
        self.assertIn("Nada foi alterado", resposta)
        self.assertEqual([("Itaú", 1000.0), ("Mercado Pago", 2000.0)],
                         self.rows("SELECT conta, saldo_inicial FROM saldos_mensais_contas WHERE ano_mes='2026-10' ORDER BY conta"))
        self.assertEqual([], self.eventos())
        db.definir_saldo_inicial_mes("2026-12", 900)
        self.assertIn("não herda", self.comando("saldo inicial 2026-12 Itaú herdado"))
        self.assertEqual([], self.eventos())

    def test_parser_do_herdado(self):
        p = svc.parsear_comando_saldo_inicial
        self.assertEqual(("2026-11", None, "mercado pago"), p("saldo inicial 2026-11 mercado pago herdado"))
        self.assertEqual(("2026-11", None, "itaú"), p("saldo inicial 2026-11 itaú herdada"))
        with data_fixa(svc.date(2026, 11, 9)):
            self.assertEqual(("2026-11", None, "caju"), p("saldo inicial caju herdado"))
        resultado = p("saldo inicial 2026-11 herdado")
        self.assertTrue(resultado is None or resultado[1] is not None)
        # Formatos antigos inalterados.
        self.assertEqual(("2026-11", 100.0, "Itaú"), p("saldo inicial 2026-11 Itaú 100"))
        self.assertEqual(("2026-11", 2000.0, None), p("saldo inicial 2026-11 2000"))

    def test_so_a_conta_pedida_volta_a_herdar(self):
        self.comando("saldo inicial 2026-11 Itaú 50")
        self.comando("saldo inicial 2026-11 Nubank 100")
        self.comando("saldo inicial 2026-11 Itaú herdado")
        definidos = svc.saldos_iniciais_definidos_heranca("2026-11")
        self.assertEqual({"Nubank": 100.0}, definidos)
        # Definir de novo depois de voltar a herdar continua funcionando.
        self.comando("saldo inicial 2026-11 Itaú 70")
        self.assertEqual({"Nubank": 100.0, "Itaú": 70.0}, svc.saldos_iniciais_definidos_heranca("2026-11"))


if __name__ == "__main__":
    unittest.main()
