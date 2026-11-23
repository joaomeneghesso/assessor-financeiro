"""D1 (reavaliação 02): receita prevista e não recebida não vira saldo herdado.

Regra de 09/11/2026 (docs/reavaliacao/06_regra_heranca.md):
- o saldo herdado mostra só o realizado;
- a receita prevista do mês anterior e não recebida aparece separada
  ("a receber herdado") e entra na projeção uma única vez;
- recebida com vínculo, entra uma vez como entrada realizada;
- recebida sem vínculo (mesmo nome e conta), fica fora da projeção e vira
  revisão de conciliação, sem contar em dobro;
- despesa prevista não paga continua abatida na herança (pendência herdada).

Cenário (conta à mão, em reais):
  out/26: base Itaú 1.000; Freela 400 previsto em 25/10, não recebido.
    out: disponível 1.000; projetado 1.000 + 400 = 1.400.
  Antes da correção: nov herdava 1.400 como "saldo agora" e, lançado o
    recebimento sem vínculo em 02/11, ia a 1.800 (dobro).
  Depois: nov disponível 1.000; a receber herdado 400; projetado 1.400.
    Com o recebimento vinculado: disponível 1.000 + 400 = 1.400; projetado 1.400.
    Com o recebimento sem vínculo: disponível 1.400; projetado 1.400 (o
    previsto não soma de novo); revisão 'receita_sem_vinculo'; dez 1.400.
    Sem receber nada até dez: dez disponível 1.000; a receber herdado 400.
Sempre em banco temporário.
"""
import secrets
import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import conciliacao as cc
import database as db
import services as svc
from saldo_resumo import resumir_saldo


def D(x):
    return Decimal(str(x)).quantize(Decimal("0.01"))


class HerancaReceitaPrevista(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = Path(self.tmp.name) / "financeiro.db"
        modulos = [db, svc]
        for nome in ("compromissos", "conciliacao", "reservas_faturas", "saldos_edicao",
                     "pagamentos_canonicos", "fatura_conferencia"):
            try:
                modulos.append(__import__(nome))
            except Exception:
                pass
        for mod in modulos:
            if hasattr(mod, "DB_PATH"):
                p = patch.object(mod, "DB_PATH", path); p.start(); self.addCleanup(p.stop)
        db.init_db()
        db.definir_saldo_inicial_conta_mes("2026-10", "Itaú", 1000)
        self.cid = db.inserir_compromisso(dict(
            tipo="entrada_avulsa", nome="Freela", categoria="Receita", conta_pagamento="Itaú",
            conta_origem="Itaú", forma_pagamento="entrada", valor=400.0, dia_vencimento=25,
            data_inicio="2026-10-25", data_fim="2026-10-25", parcelas_total=None, ativo=1,
            origem="teste", observacao=""))

    def receber(self, data="2026-11-02"):
        return db.inserir_transacao(dict(
            data=data, tipo="receita", valor=400.0, categoria="Receita", descricao="Freela",
            conta="Itaú", forma_pagamento="pix", mensagem_original="teste"))

    def m(self, mes):
        return svc.obter_metricas_resultado_mes(mes)

    def test_outubro_nao_muda(self):
        m = self.m("2026-10")
        self.assertEqual(D(m["saldo_disponivel"]), D(1000))
        self.assertEqual(D(m["saldo_projetado"]), D(1400))

    def test_novembro_sem_receber_nao_herda_previsto_como_saldo(self):
        m = self.m("2026-11")
        self.assertEqual(D(m["saldo_disponivel"]), D(1000))  # antes: 1.400
        self.assertEqual(D(m["receitas_previstas_herdadas_total"]), D(400))
        self.assertEqual(D(m["saldo_projetado"]), D(1400))
        self.assertEqual(D(svc.calcular_caixa_por_conta_mes("2026-11")["total_disponivel"]), D(1000))
        s = resumir_saldo(m)
        self.assertEqual(D(s["saldo_atual"]), D(1000))
        self.assertEqual(D(s["a_receber"]), D(400))
        self.assertEqual(D(s["a_receber_herdado"]), D(400))
        self.assertEqual(s["a_receber_herdado_meses"], ["2026-10"])
        self.assertEqual(D(s["saldo_final"]), D(1400))
        # dezembro: continua só o realizado; o previsto de outubro segue separado
        dez = self.m("2026-12")
        self.assertEqual(D(dez["saldo_disponivel"]), D(1000))
        self.assertEqual(D(dez["receitas_previstas_herdadas_total"]), D(400))
        self.assertEqual(D(dez["saldo_projetado"]), D(1400))

    def test_recebimento_vinculado_conta_uma_vez(self):
        tid = self.receber()
        with db.get_connection() as cn:
            cn.row_factory = sqlite3.Row
            row = dict(cn.execute("select * from compromissos").fetchone())
        cc.vincular_existente(tid, dict(id=row["id"], mes="2026-10", assinatura=cc.assinatura_alvo(row)),
                              secrets.token_urlsafe(10), "u")
        nov = self.m("2026-11")
        self.assertEqual(D(nov["saldo_disponivel"]), D(1400))
        self.assertEqual(D(nov["receitas_previstas_herdadas_total"]), D(0))
        self.assertEqual(D(nov["saldo_projetado"]), D(1400))
        self.assertEqual(D(nov["ajuste_conciliacao_heranca"]), D(0))
        self.assertEqual(D(self.m("2026-12")["saldo_disponivel"]), D(1400))

    def test_recebimento_sem_vinculo_nao_conta_em_dobro(self):
        self.receber()
        nov = self.m("2026-11")
        self.assertEqual(D(nov["saldo_disponivel"]), D(1400))  # antes: 1.800
        self.assertEqual(D(nov["saldo_projetado"]), D(1400))   # antes: 1.800
        self.assertTrue(any(r["tipo"] == "receita_sem_vinculo" and r.get("compromisso_id") == self.cid
                            for r in nov["revisoes_conciliacao"]))
        dez = self.m("2026-12")
        self.assertEqual(D(dez["saldo_disponivel"]), D(1400))  # antes: 1.800
        self.assertEqual(D(dez["saldo_projetado"]), D(1400))

    def test_inicio_e_saldo_mostram_previsto_separado(self):
        """Hoje = 09/11/2026: Início e Saldo mostram 'Saldo agora' 1.000 e,
        separado, 'Previsto de outubro não recebido · R$ 400,00'."""
        from datetime import date
        import telegram_experiencia as ux
        engine = ux.Experience(date_provider=lambda: date(2026, 11, 9))
        for view in ("home", "balance"):
            texto = engine.act("teste-d1", ("view", view)).text
            self.assertIn("R$ 1.000,00", texto)
            self.assertRegex(texto, r"Previsto de .*[Oo]utubro.* não recebido · R\$ 400,00")

    def test_base_configurada_continua_mandando(self):
        db.definir_saldo_inicial_conta_mes("2026-11", "Itaú", 1250)
        nov = self.m("2026-11")
        self.assertEqual(D(nov["saldo_disponivel"]), D(1250))
        self.assertEqual(D(nov["receitas_previstas_herdadas_total"]), D(0))

    def test_despesa_prevista_nao_paga_segue_abatida(self):
        """Fixo de 300 não pago em out. Antes: nov herdava 1.000 + 400 − 300
        = 1.100 como saldo. Agora herda 1.000 − 300 = 700 (a despesa segue
        abatida, pendência herdada) e projeta 700 + 400 (a receber herdado)
        = 1.100."""
        db.inserir_compromisso(dict(tipo="fixo", nome="Aluguel", categoria="Moradia", conta_pagamento="Itaú",
                                    forma_pagamento="pix", valor=300, dia_vencimento=10,
                                    data_inicio="2026-10-01", data_fim="2026-10-31", ativo=True))
        nov = self.m("2026-11")
        self.assertEqual(D(nov["saldo_disponivel"]), D(700))
        self.assertEqual(D(nov["pendencias_herdadas_total_bruto"]), D(300))
        self.assertEqual(D(nov["saldo_projetado"]), D(1100))


if __name__ == "__main__":
    unittest.main()
