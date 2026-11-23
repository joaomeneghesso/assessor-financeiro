"""D3 (reavaliação 02): pagar em novembro a fatura de outubro não muda o
"Saldo agora" de outubro; o pagamento sai do caixa de novembro.

Conta à mão (reais): base Itaú out/26 = 2.000; compra no crédito Nubank 400
em 05/10 (fatura de outubro); pagamento total 400 com data 10/11.
- out: disponível 2.000 (antes da correção: 1.600); projetado 2.000 − 400
  (fatura ainda reservada no fim de outubro) = 1.600.
- nov (herdado): herda 1.600 (fatura reservada); o pagamento sai do caixa
  (−400) e a reserva herdada é liberada (+400): disponível 1.600; projetado 1.600.
- dez: 1.600 / 1.600. Soma entre meses fecha: 2.000 − 400 = 1.600.
- Com base confirmada em nov (2.000 no banco em 01/11): disponível 2.000 − 400 = 1.600.
Banco temporário.
"""
import secrets
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import database as db
import services as svc
import telegram_registros as reg


def D(x):
    return Decimal(str(x)).quantize(Decimal("0.01"))


class FaturaPagaMesPosterior(unittest.TestCase):
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
        db.definir_saldo_inicial_conta_mes("2026-10", "Itaú", 2000)
        db.inserir_transacao(dict(data="2026-10-05", tipo="despesa", valor=400.0, categoria="Compras",
                                  descricao="tenis", conta="Nubank", forma_pagamento="credito",
                                  mensagem_original="teste"))

    def pagar(self, data):
        reg.confirmar_pagamento_fatura(dict(ano_mes="2026-10", conta_cartao="Nubank", conta_origem="Itaú",
                                            modo="total", valor=400, saldo_esperado=400, data_movimento=data),
                                       secrets.token_urlsafe(12), "u")

    def ver(self, mes):
        m = svc.obter_metricas_resultado_mes(mes)
        cx = svc.calcular_caixa_por_conta_mes(mes)
        return D(m["saldo_disponivel"]), D(m["saldo_projetado"]), D(cx["total_disponivel"])

    def test_pagamento_em_novembro_fica_no_caixa_de_novembro(self):
        self.pagar("2026-11-10")
        self.assertEqual(self.ver("2026-10"), (D(2000), D(1600), D(2000)))  # antes: 1.600 / 1.600
        self.assertEqual(self.ver("2026-11"), (D(1600), D(1600), D(1600)))
        self.assertEqual(self.ver("2026-12"), (D(1600), D(1600), D(1600)))
        self.assertEqual(D(svc.obter_metricas_resultado_mes("2026-11")["saidas_pagamentos_fatura"]), D(400))
        self.assertEqual(D(svc.obter_metricas_resultado_mes("2026-10")["saidas_pagamentos_fatura"]), D(0))

    def test_pagamento_no_mesmo_mes_nao_muda(self):
        self.pagar("2026-10-28")
        self.assertEqual(self.ver("2026-10"), (D(1600), D(1600), D(1600)))
        self.assertEqual(self.ver("2026-11"), (D(1600), D(1600), D(1600)))

    def test_base_confirmada_em_novembro(self):
        self.pagar("2026-11-10")
        db.definir_saldo_inicial_conta_mes("2026-11", "Itaú", 2000)
        self.assertEqual(self.ver("2026-11")[:2], (D(1600), D(1600)))


if __name__ == "__main__":
    unittest.main()
