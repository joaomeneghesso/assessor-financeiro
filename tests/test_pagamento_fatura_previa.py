"""Movimentos de fatura por texto (pagamento, restante, estorno, crédito) só
gravam depois da prévia e da frase de confirmação própria.

Também garante que o fluxo nativo do Telegram (invoice_* com prévia e
invoice_commit) continua igual e não passa pelo comando de texto.
"""
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import database as db
import services as svc
import telegram_experiencia as ux

HOJE = date(2026, 10, 13)
MES = "2026-10"


class PreviaPagamentoFaturaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", Path(self.tmp.name) / "fixture.db")
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        svc.PENDENCIAS_PAGAMENTO_FATURA.clear()
        self.addCleanup(svc.PENDENCIAS_PAGAMENTO_FATURA.clear)
        self.compra(100)
        db.inserir_transacao(dict(data=f"{MES}-01", tipo="receita", valor=1000, categoria="Salário",
                                  descricao="Salário", conta="Itaú", forma_pagamento="pix"))

    def compra(self, valor):
        db.inserir_transacao(dict(data=f"{MES}-05", tipo="despesa", valor=valor, categoria="Compras",
                                  descricao="Loja", conta="Nubank", forma_pagamento="crédito"))

    def movimentos(self):
        return db.listar_fatura_movimentos(MES)

    def saldo(self):
        return svc.calcular_resumo_fatura(MES, "Nubank")["saldo_restante"]

    def msg(self, texto, sessao="s1"):
        return svc.processar_mensagem(texto, sessao=sessao)

    def test_previa_do_restante_mostra_campos_e_nao_grava(self):
        r = self.msg(f"paguei o restante da fatura nubank usando itau {MES}")
        for trecho in ("Prévia", "Fatura: Nubank", f"({MES})", "Tipo: pagamento do restante",
                       "Valor: R$ 100,00", "Conta pagadora: Itaú",
                       "Saldo da fatura: R$ 100,00 → R$ 0,00", "Nada foi registrado ainda",
                       "confirmar pagamento", "cancelar pagamento"):
            self.assertIn(trecho, r)
        self.assertEqual([], self.movimentos())
        self.assertEqual(100, self.saldo())

    def test_confirmar_grava_uma_unica_vez(self):
        self.msg(f"paguei 40 da fatura nubank usando itau {MES}")
        r = self.msg("confirmar pagamento")
        self.assertIn("Movimento de fatura registrado", r)
        self.assertIn("Valor: R$ 40,00", r)
        self.assertEqual(1, len(self.movimentos()))
        self.assertIn("Não há pagamento de fatura pendente", self.msg("confirmar pagamento"))
        self.assertEqual(1, len(self.movimentos()))
        self.assertEqual(60, self.saldo())

    def test_cancelar_descarta(self):
        self.msg(f"paguei o restante da fatura nubank usando itau {MES}")
        self.assertIn("Nada foi registrado", self.msg("cancelar pagamento"))
        self.assertIn("Não há pagamento de fatura pendente", self.msg("confirmar pagamento"))
        self.assertEqual([], self.movimentos())

    def test_cancelar_sozinho_tambem_descarta(self):
        self.msg(f"paguei o restante da fatura nubank usando itau {MES}")
        r = self.msg("cancelar")
        self.assertIn("Pagamento de fatura cancelado", r)
        self.assertIn("Não há pagamento de fatura pendente", self.msg("confirmar pagamento"))
        self.assertEqual([], self.movimentos())
        # Sem nada pendente, a resposta antiga continua.
        self.assertIn("Não há lançamento pendente para cancelar", self.msg("cancelar"))

    def test_cancelar_sozinho_prioriza_lancamento_pendente(self):
        self.msg(f"paguei 40 da fatura nubank usando itau {MES}")
        svc._definir_pendencia(svc.PENDENCIAS_CONFIRMACAO, "s1", {"valor": 1})
        self.addCleanup(svc.PENDENCIAS_CONFIRMACAO.clear)
        self.assertIn("Lançamento pendente cancelado", self.msg("cancelar"))
        # A prévia de fatura continua e pode ser confirmada.
        self.assertIn("Movimento de fatura registrado", self.msg("confirmar pagamento"))
        self.assertEqual(1, len(self.movimentos()))

    def test_segunda_previa_avisa_que_descartou_a_primeira(self):
        primeira = self.msg(f"paguei 40 da fatura nubank usando itau {MES}")
        self.assertNotIn("foi descartada", primeira)
        self.assertNotIn("foi descartada", self.msg(f"paguei 40 da fatura nubank usando itau {MES}"))
        segunda = self.msg(f"paguei 30 da fatura nubank usando itau {MES}")
        self.assertIn("prévia de fatura anterior, ainda não confirmada, foi descartada", segunda)
        self.msg("confirmar pagamento")
        self.assertEqual(70, self.saldo())

    def test_textos_de_ajuda_citam_a_confirmacao(self):
        r = self.msg("paguei a fatura do nubank 100")
        self.assertIn("Nada foi registrado", r)
        self.assertIn("confirmar pagamento", r)
        self.assertEqual([], self.movimentos())

    def test_ttl_expirado_e_outra_sessao_nao_confirmam(self):
        self.msg(f"paguei o restante da fatura nubank usando itau {MES}", sessao="s1")
        self.assertIn("Não há pagamento", self.msg("confirmar pagamento", sessao="s2"))
        self.assertEqual([], self.movimentos())
        item = svc.PENDENCIAS_PAGAMENTO_FATURA["s1"]
        item["criado_em"] = datetime.now() - timedelta(seconds=svc.PENDENCIA_TTL_SEGUNDOS + 1)
        self.assertIn("Não há pagamento", self.msg("confirmar pagamento", sessao="s1"))
        self.assertEqual([], self.movimentos())

    def test_saldo_alterado_depois_da_previa_aborta(self):
        self.msg(f"paguei o restante da fatura nubank usando itau {MES}")
        self.compra(30)  # nova compra: o "restante" mostrado não vale mais
        r = self.msg("confirmar pagamento")
        self.assertIn("mudou desde a prévia", r)
        self.assertEqual([], self.movimentos())
        self.assertIn("Não há pagamento", self.msg("confirmar pagamento"))

    def test_revalidacao_dentro_da_transacao(self):
        # Mesmo se o saldo mudar entre a comparação e a gravação, nada é gravado.
        r = svc.registrar_movimento_fatura_formatado(
            "pagamento_total", 1, "Nubank", MES, conta_origem="Itaú", saldo_esperado=70)
        self.assertIn("mudou desde a prévia", r)
        self.assertEqual([], self.movimentos())

    def test_outras_confirmacoes_nao_confirmam_pagamento(self):
        self.msg(f"paguei o restante da fatura nubank usando itau {MES}")
        for texto in ("confirmar", "confirmar exclusao", "confirmar importacao", "confirmar estorno"):
            with self.subTest(texto=texto):
                self.assertNotIn("Movimento de fatura registrado", self.msg(texto))
                self.assertEqual([], self.movimentos())
        self.assertIn("Movimento de fatura registrado", self.msg("confirmar pagamento"))
        self.assertEqual(1, len(self.movimentos()))

    def test_estorno_e_credito_tambem_tem_previa(self):
        r = self.msg(f"estorno de 10 na fatura nubank {MES}")
        self.assertIn("Tipo: estorno", r)
        self.assertIn("Saldo da fatura: R$ 100,00 → R$ 90,00", r)
        self.assertIn("confirmar estorno", r)
        self.assertNotIn("Conta pagadora", r)
        self.assertEqual([], self.movimentos())
        self.assertIn("Movimento de fatura registrado", self.msg("confirmar estorno"))
        r = self.msg(f"credito de 5 na fatura nubank {MES}")
        self.assertIn("confirmar credito", r)
        self.assertIn("Movimento de fatura registrado", self.msg("confirmar crédito"))
        self.assertEqual(["estorno", "credito"], [m["tipo_movimento"] for m in self.movimentos()])
        self.assertEqual(85, self.saldo())

    def test_parcial_acima_do_saldo_avisa_limite(self):
        r = self.msg(f"paguei 150 da fatura nubank usando itau {MES}")
        self.assertIn("Valor: R$ 100,00", r)
        self.assertIn("limitado ao saldo", r)
        self.msg("confirmar pagamento")
        self.assertEqual(0, self.saldo())

    def test_fatura_sem_saldo_recusa_sem_pendencia(self):
        db.inserir_fatura_movimento({"ano_mes": MES, "conta_cartao": "Nubank", "tipo_movimento": "credito",
                                     "valor": 100, "data_movimento": f"{MES}-06", "conta_origem": None})
        r = self.msg(f"paguei o restante da fatura nubank usando itau {MES}")
        self.assertIn("não possui saldo pendente", r)
        self.assertEqual({}, svc.PENDENCIAS_PAGAMENTO_FATURA)

    def test_clear_service_pending_limpa_pagamento(self):
        self.msg(f"paguei o restante da fatura nubank usando itau {MES}", sessao="k")
        ux.clear_service_pending("k")
        self.assertIn("Não há pagamento", self.msg("confirmar pagamento", sessao="k"))
        self.assertEqual([], self.movimentos())

    def test_fluxo_nativo_do_telegram_inalterado(self):
        engine = ux.Experience(date_provider=lambda: HOJE)
        tela = engine.handle_text("k", f"paguei o restante da fatura nubank usando itau {MES}")
        self.assertIn("Confirmar pagamento da fatura?", tela.text)
        self.assertEqual({}, svc.PENDENCIAS_PAGAMENTO_FATURA)  # não passou pelo comando de texto
        self.assertEqual([], self.movimentos())
        s = engine.session("k")
        self.assertEqual("invoice_confirm", s.stage)
        fim = engine.act("k", ("invoice_commit", s.draft["key"]))
        self.assertIn("Pagamento registrado no assessor", fim.text)
        self.assertEqual(1, len(self.movimentos()))
        self.assertEqual(0, self.saldo())


if __name__ == "__main__":
    unittest.main()
