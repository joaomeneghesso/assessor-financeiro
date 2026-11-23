"""Gerenciar contas: Lia (só destino) sai da lista, conta de fixo conciliado pode mudar e contas
sem uso podem ser desativadas/reativadas sem tocar no histórico."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import compromissos
import conciliacao
import contas_inativas
import database as db
import services as svc
import telegram_experiencia as ux

HOJE = date(2026, 10, 28)
MES = "2026-10"


class GerenciarContasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", Path(self.tmp.name) / "fixture.db")
            p.start()
            self.addCleanup(p.stop)
        db.init_db()
        # A conciliação usa o próprio relógio: fixa a mesma data da Experience
        # para o teste não depender do dia em que roda.
        p = patch.object(conciliacao, "_hoje", lambda: HOJE)
        p.start()
        self.addCleanup(p.stop)
        self.engine = ux.Experience(date_provider=lambda: HOJE)
        self.key = "teste-contas"
        db.definir_saldo_inicial_conta_mes(MES, "Itaú", 0.0, "teste")
        db.definir_saldo_inicial_conta_mes(MES, "Mercado Pago", 5000.0, "teste")
        # BTG: conta antiga, uma compra no crédito em junho, sem saldo nem pendência hoje
        db.inserir_transacao(dict(data="2026-06-21", tipo="despesa", valor=3.56, categoria="Transporte",
                                  descricao="Gasolina", conta="BTG", forma_pagamento="crédito"))
        # a fatura de junho do BTG foi paga (como no uso real); sem isso ela seguiria em aberto
        db.inserir_fatura_movimento(dict(ano_mes="2026-06", conta_cartao="BTG", tipo_movimento="pagamento_total",
                                         valor=3.56, data_movimento="2026-07-10", conta_origem="Mercado Pago"))
        # Compras: veio da coluna Category do CSV; só existe no campo antigo de um parcelamento inativo
        db.inserir_compromisso(dict(
            tipo="parcelamento", nome="Celular firestick", categoria="Eletrônicos", conta_pagamento="Compras",
            forma_pagamento="crédito", valor=44.0, dia_vencimento=20, data_inicio="2026-06-20",
            data_fim="2026-10-20", parcelas_total=5, ativo=0, origem="teste", observacao=""))
        # iCloud: Lia é só destino; o dinheiro sai do Itaú (conta_origem)
        self.icloud = db.inserir_compromisso(dict(
            tipo="fixo", nome="iCloud", categoria="Assinaturas", conta_pagamento="Lia", forma_pagamento="pix",
            valor=33.45, dia_vencimento=30, data_inicio="2026-06-10", data_fim=None, parcelas_total=None,
            ativo=1, origem="teste", observacao=""))
        with db.get_connection() as c:
            c.execute("UPDATE compromissos SET conta_origem='Itaú', destino_pagamento='Lia' WHERE id=?",
                      (self.icloud,))

    def contas(self, **kw):
        return self.engine.accounts(**kw)

    def sessao(self):
        return self.engine.sessions[self.key]

    # 1. Lia ----------------------------------------------------------------------------------
    def test_lia_que_so_e_destino_nao_aparece_como_conta(self):
        self.assertNotIn("Lia", self.contas())
        self.assertIn("Itaú", self.contas())

    def test_conta_so_no_campo_antigo_continua_aparecendo(self):
        # sem conta_origem, o campo antigo ainda é a única informação disponível
        self.assertIn("Compras", self.contas())

    # 2. Conta de fixo conciliado ----------------------------------------------------------------
    def test_conta_de_fixo_conciliado_pode_ser_alterada(self):
        self.engine.act(self.key, ("settle", self.icloud, MES))
        self.engine.act(self.key, ("answer", "Itaú"))
        self.engine.act(self.key, ("commit", self.sessao().draft["key"]))
        self.assertTrue(any(v["compromisso_id"] == self.icloud for v in conciliacao.listar_vinculos()))
        resposta = compromissos.alterar_compromisso_conta(self.icloud, "Mercado Pago")
        self.assertIn("atualizada", resposta)
        with db.get_connection() as c:
            linha = c.execute("SELECT conta_pagamento, conta_origem, destino_pagamento FROM compromissos WHERE id=?",
                              (self.icloud,)).fetchone()
        self.assertEqual(("Mercado Pago", "Mercado Pago", "Lia"), tuple(linha))
        # o vínculo continua válido e os cálculos não falham
        self.assertTrue(any(v["compromisso_id"] == self.icloud for v in conciliacao.listar_vinculos()))
        svc.calcular_caixa_por_conta_mes(MES)

    def test_comando_de_texto_altera_conta_de_fixo_conciliado(self):
        """Caminho real do Telegram: 'alterar conta fixo N para X' -> fixos_edicao.salvar, sem prévia."""
        self.engine.act(self.key, ("settle", self.icloud, MES))
        self.engine.act(self.key, ("answer", "Itaú"))
        self.engine.act(self.key, ("commit", self.sessao().draft["key"]))
        previa = svc.processar_mensagem(f"alterar conta fixo {self.icloud} para Mercado Pago", sessao="t")
        self.assertIn("Responda: confirmar alteracao", previa)  # Onda 1: prévia antes de gravar
        resposta = svc.processar_mensagem("confirmar alteracao", sessao="t")
        self.assertNotIn("conciliações", resposta)
        self.assertIn("Fixo atualizado", resposta)
        with db.get_connection() as c:
            linha = c.execute("SELECT conta_pagamento, conta_origem, destino_pagamento FROM compromissos WHERE id=?",
                              (self.icloud,)).fetchone()
        self.assertEqual(("Mercado Pago", "Mercado Pago", "Lia"), tuple(linha))
        self.assertTrue(any(v["compromisso_id"] == self.icloud for v in conciliacao.listar_vinculos()))

    def test_comando_de_texto_continua_bloqueando_valor_e_forma_de_fixo_conciliado(self):
        self.engine.act(self.key, ("settle", self.icloud, MES))
        self.engine.act(self.key, ("answer", "Itaú"))
        self.engine.act(self.key, ("commit", self.sessao().draft["key"]))
        for comando in (f"alterar valor fixo {self.icloud} para 40", f"alterar forma fixo {self.icloud} para crédito"):
            with self.subTest(comando=comando):
                try:
                    resposta = svc.processar_mensagem(comando, sessao="t")
                except conciliacao.ConciliacaoError as exc:
                    resposta = str(exc)
                self.assertIn("conciliações", resposta)

    def test_valor_de_fixo_conciliado_continua_protegido(self):
        self.engine.act(self.key, ("settle", self.icloud, MES))
        self.engine.act(self.key, ("answer", "Itaú"))
        self.engine.act(self.key, ("commit", self.sessao().draft["key"]))
        with self.assertRaises(conciliacao.ConciliacaoError):
            db.atualizar_campo_compromisso(self.icloud, "forma_pagamento", "crédito")

    # 3. Desativar / reativar --------------------------------------------------------------------
    def test_desativar_conta_sem_uso_mantem_historico(self):
        self.assertIn("BTG", self.contas())
        confirmacao = self.engine.act(self.key, ("acct_off", "BTG"))
        self.assertIn("Desativar BTG?", confirmacao.text)
        tela = self.engine.act(self.key, ("acct_off_ok", "BTG"))
        self.assertIn("desativada", tela.text)
        self.assertNotIn("BTG", self.contas())
        self.assertIn("BTG", self.contas(incluir_inativas=True))
        with db.get_connection() as c:  # histórico intacto
            n = c.execute("SELECT count(*) FROM transacoes WHERE conta='BTG'").fetchone()[0]
        self.assertEqual(1, n)
        self.assertEqual("BTG", db.buscar_transacoes_por_mes("2026-06")[0]["conta"])

    def test_reativar_devolve_a_conta_as_listas(self):
        self.engine.act(self.key, ("acct_off_ok", "BTG"))
        self.assertNotIn("BTG", self.contas())
        self.engine.act(self.key, ("acct_on", "BTG"))
        self.assertIn("BTG", self.contas())

    def test_conta_com_saldo_nao_pode_ser_desativada(self):
        tela = self.engine.act(self.key, ("acct_off", "Mercado Pago"))
        self.assertIn("Não dá para desativar", tela.text)
        self.assertIn("saldo", tela.text)
        self.engine.act(self.key, ("acct_off_ok", "Mercado Pago"))  # mesmo forçando, a regra vale
        self.assertIn("Mercado Pago", self.contas())

    def test_tela_gerenciar_lista_ativas_e_desativadas(self):
        self.engine.act(self.key, ("acct_off_ok", "BTG"))
        tela = self.engine.act(self.key, ("view", "accounts_manage"))
        self.assertIn("Desativadas", tela.text)
        rotulos = [r for linha in tela.rows for r, _ in linha]
        self.assertIn("↩ Reativar BTG", rotulos)
        self.assertIn("🚫 Desativar Itaú", rotulos)

    def test_conta_desativada_continua_encontrada_em_consultas_por_nome(self):
        self.engine.act(self.key, ("acct_off_ok", "BTG"))
        self.assertEqual("BTG", self.engine._account_in_text("extrato btg"))

    def test_registrar_em_conta_desativada_avisa_na_confirmacao(self):
        self.engine.act(self.key, ("acct_off_ok", "BTG"))
        s = self.engine.session(self.key)
        s.draft = dict(tipo="despesa", valor=20, descricao="teste", categoria="Outros", conta="BTG",
                       forma_pagamento="pix", data="2026-10-28", parcelas_total=1, key="k1", parsed=True)
        tela = self.engine.preview(self.key)
        self.assertIn("está desativada", tela.text)
        self.assertTrue(any(a[0] == "commit" for linha in tela.rows for _, a in linha))  # só avisa

    def test_desativar_e_reativar_ficam_na_auditoria(self):
        contas_inativas.desativar("BTG", "u")
        contas_inativas.reativar("BTG", "u")
        with db.get_connection() as c:
            ops = [r[0] for r in c.execute(
                "SELECT operacao FROM auditoria_eventos WHERE entidade='contas_inativas' ORDER BY id")]
        self.assertEqual(["desativada", "reativada"], ops)
        self.assertFalse(contas_inativas.desativar("BTG", "u") and contas_inativas.desativar("BTG", "u"))


if __name__ == "__main__":
    unittest.main()
