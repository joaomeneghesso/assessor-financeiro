"""Rede de segurança: um teste para cada mutante que sobreviveu à suíte.

Reavaliação 05 (09/11/2026), seção 3: 11 de 20 mutações manuais passaram com a
suíte verde. Cada classe abaixo cita o mutante (M01..M20) que ela mata; a prova
(aplicar a mutação numa cópia e ver o teste falhar) está registrada no commit
que criou este arquivo. Inclui também os caminhos "falha fechado" de
conciliacao.py, que antes tinham 0 cobertura.

Tudo em banco temporário; nenhum relógio real (a conciliação é fixada em
conciliacao._hoje).
"""
import os
import sqlite3
import tempfile
import threading
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import compromissos
import conciliacao as conc
import database as db
import faturas_competencia as fc
import fixos_vigencia
import services as svc
import telegram_registros
from money import parse_money

HOJE = date(2026, 10, 28)
_HOJE_REAL = conc._hoje
MES = "2026-09"


class BancoTemporario(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "fixture.db"
        for mod in (db, svc):
            p = patch.object(mod, "DB_PATH", self.path)
            p.start()
            self.addCleanup(p.stop)
        db.init_db()

    def sql(self, comando, *args):
        with db.get_connection() as c:
            c.execute(comando, args)
            c.commit()


# --- M01: money.py ROUND_HALF_UP -> ROUND_DOWN ---------------------------------
class M01ArredondamentoMonetario(unittest.TestCase):
    def test_decimal_com_tres_casas_arredonda_meio_para_cima(self):
        self.assertEqual(Decimal("1.01"), parse_money(Decimal("1.005")))
        self.assertEqual(Decimal("2.68"), parse_money(Decimal("2.675")))
        self.assertEqual(Decimal("0.01"), parse_money(Decimal("0.005")))

    def test_float_com_tres_casas_usa_a_representacao_decimal(self):
        # str(1.005) == '1.005' -> 1.01 (HALF_UP sobre o texto, não sobre o binário)
        self.assertEqual(Decimal("1.01"), parse_money(1.005))
        self.assertEqual(Decimal("10.13"), parse_money(10.125))

    def test_abaixo_da_metade_continua_para_baixo(self):
        self.assertEqual(Decimal("1.00"), parse_money(Decimal("1.004")))

    def test_negativo_permitido_arredonda_simetrico(self):
        self.assertEqual(Decimal("-1.01"), parse_money(Decimal("-1.005"), allow_negative=True))


# --- M02: compromissos tolerância previsto x realizado 0,01 -> 0,10 -----------
class M02ToleranciaPrevistoRealizado(unittest.TestCase):
    def item(self, valor, nome="Monitor Magalu"):
        return {"nome": nome, "conta_pagamento": "Nubank", "valor": valor}

    def test_mesmo_item_mesmo_valor_corresponde(self):
        self.assertTrue(compromissos._previsto_corresponde_realizado(self.item(250.0), self.item(250.0)))

    def test_cinco_centavos_de_diferenca_nao_corresponde(self):
        self.assertFalse(compromissos._previsto_corresponde_realizado(self.item(250.0), self.item(250.05)))
        self.assertFalse(compromissos._previsto_corresponde_realizado(self.item(250.05), self.item(250.0)))

    def test_nove_centavos_de_diferenca_nao_corresponde(self):
        self.assertFalse(compromissos._previsto_corresponde_realizado(self.item(99.91), self.item(100.0)))


# --- M03: faturas_competencia corte padrão 25 -> 24 ---------------------------
class M03CortePadraoSemVariavel(unittest.TestCase):
    def setUp(self):
        p = patch.dict(os.environ, {}, clear=False)
        p.start()
        self.addCleanup(p.stop)
        os.environ.pop("ASSESSOR_FATURA_DIA_CORTE", None)
        os.environ.pop("ASSESSOR_FATURA_CORTES", None)

    def compra(self, data):
        return {"data": data, "conta": "Nubank", "forma_pagamento": "crédito", "tipo": "despesa"}

    def test_corte_padrao_e_dia_25(self):
        self.assertEqual(25, fc.dia_corte("Nubank", "2026-11-10"))

    def test_dia_24_nao_pergunta_e_dia_25_pergunta(self):
        self.assertFalse(fc.precisa_escolher(self.compra("2026-11-24")))
        self.assertEqual(("2026-11",), fc.opcoes_fatura(self.compra("2026-11-24")))
        self.assertTrue(fc.precisa_escolher(self.compra("2026-11-25")))
        self.assertEqual(("2026-11", "2026-12"), fc.opcoes_fatura(self.compra("2026-11-25")))

    def test_fevereiro_curto_limita_ao_ultimo_dia(self):
        os.environ["ASSESSOR_FATURA_DIA_CORTE"] = "31"
        self.assertEqual(28, fc.dia_corte("Nubank", "2027-02-10"))


# --- M05: services.calcular_saldo_disponivel_por_conta sinal das entradas -----
class M05SaldoDisponivelPorConta(unittest.TestCase):
    def test_entradas_somam_e_saidas_subtraem_por_conta(self):
        resultado = svc.calcular_saldo_disponivel_por_conta(
            {"Itaú": 1000.0, "Mercado Pago": 50.0},
            {"Itaú": {"entradas": 200.0, "saidas_imediatas": 300.0},
             "Nubank": {"entradas": 80.0, "saidas_imediatas": 0.0}},
        )
        self.assertEqual({"Itaú": 900.0, "Mercado Pago": 50.0, "Nubank": 80.0}, resultado)

    def test_valores_ausentes_valem_zero(self):
        self.assertEqual({"X": 10.0}, svc.calcular_saldo_disponivel_por_conta({"X": None}, {"X": {"entradas": 10}}))


# --- M10: telegram_registros limite de 60 parcelas ---------------------------
class M10LimiteDeParcelas(unittest.TestCase):
    def transacao(self, parcelas):
        return dict(data="2026-10-10", tipo="despesa", valor="6100,00", parcelas_total=parcelas,
                    descricao="Notebook", categoria="Compras", conta="Nubank", forma_pagamento="crédito")

    def test_sessenta_parcelas_aceitas(self):
        self.assertEqual(60, telegram_registros.validar_transacao(self.transacao(60))["parcelas_total"])

    def test_sessenta_e_uma_parcelas_recusadas(self):
        for parcelas in (61, 120, 600):
            with self.subTest(parcelas=parcelas):
                with self.assertRaisesRegex(ValueError, "1 a 60 parcelas"):
                    telegram_registros.validar_transacao(self.transacao(parcelas))

    def test_zero_e_fracao_recusadas(self):
        for parcelas in (-1, 2.5, True):  # 0/None viram 1 (à vista) por desenho
            with self.subTest(parcelas=parcelas):
                with self.assertRaises(ValueError):
                    telegram_registros.validar_transacao(self.transacao(parcelas))


# --- M13/M14: database.fatura_write_transaction --------------------------------
class M13M14TransacaoDeFatura(BancoTemporario):
    def contar(self):
        with db.get_connection() as c:
            return c.execute("SELECT COUNT(*) FROM auditoria_eventos WHERE entidade='rede_teste'").fetchone()[0]

    def inserir(self, conn):
        db.registrar_auditoria("rede_teste", "1", "x", dados_depois={"a": 1}, usuario_sessao="t",
                               origem="teste", conn=conn)

    def test_m13_lock_de_escrita_e_tomado_no_inicio(self):
        """BEGIN IMMEDIATE: outro escritor fica bloqueado antes mesmo da 1ª escrita."""
        with db.fatura_write_transaction():
            outro = sqlite3.connect(self.path, timeout=0, isolation_level=None)
            try:
                with self.assertRaisesRegex(sqlite3.OperationalError, "locked|busy"):
                    outro.execute("BEGIN IMMEDIATE")
            finally:
                outro.close()
        # Depois do commit o lock foi liberado.
        outro = sqlite3.connect(self.path, timeout=0, isolation_level=None)
        try:
            outro.execute("BEGIN IMMEDIATE")
            outro.execute("ROLLBACK")
        finally:
            outro.close()

    def test_m13_segundo_escritor_espera_e_nao_intercala(self):
        ordem = []
        dentro = threading.Event()

        def segundo():
            dentro.wait(5)
            with db.fatura_write_transaction() as conn:
                ordem.append("segundo")
                self.inserir(conn)

        t = threading.Thread(target=segundo)
        t.start()
        with db.fatura_write_transaction() as conn:
            ordem.append("primeiro-inicio")
            dentro.set()
            t.join(0.5)  # o segundo não pode entrar enquanto este não termina
            ordem.append("primeiro-fim")
            self.inserir(conn)
        t.join(10)
        self.assertEqual(["primeiro-inicio", "primeiro-fim", "segundo"], ordem)
        self.assertEqual(2, self.contar())

    def test_m14_excecao_no_meio_nao_persiste_e_propaga(self):
        with self.assertRaisesRegex(RuntimeError, "falha simulada"):
            with db.fatura_write_transaction() as conn:
                self.inserir(conn)
                raise RuntimeError("falha simulada")
        self.assertEqual(0, self.contar())

    def test_m14_rollback_explicito_antes_de_fechar(self):
        """A transação é desfeita explicitamente (não depende do close implícito)."""
        estados = []
        original = db._open_connection

        def abrir(read_only):
            conn = original(read_only)
            fechar = conn.close

            def close():
                estados.append(conn.in_transaction)
                fechar()

            conn.close = close
            return conn

        with patch.object(db, "_open_connection", abrir):
            with self.assertRaises(RuntimeError):
                with db.fatura_write_transaction() as conn:
                    self.inserir(conn)
                    raise RuntimeError("falha simulada")
        self.assertEqual([False], estados)
        self.assertEqual(0, self.contar())


# --- M20: fixos_vigencia fim inclusivo ----------------------------------------
class M20VigenciaInclusiva(unittest.TestCase):
    def test_fim_igual_ao_inicio_do_outro_sobrepoe(self):
        a = {"data_inicio": "2026-01-01", "data_fim": "2026-03-31"}
        b = {"data_inicio": "2026-03-31", "data_fim": None}
        self.assertTrue(fixos_vigencia.periodos_sobrepostos(a, b))
        self.assertTrue(fixos_vigencia.periodos_sobrepostos(b, a))

    def test_fixo_de_um_dia_sobrepoe_a_si_mesmo(self):
        a = {"data_inicio": "2026-05-10", "data_fim": "2026-05-10"}
        self.assertTrue(fixos_vigencia.periodos_sobrepostos(a, dict(a)))

    def test_dia_seguinte_nao_sobrepoe(self):
        a = {"data_inicio": "2026-01-01", "data_fim": "2026-03-31"}
        b = {"data_inicio": "2026-04-01", "data_fim": None}
        self.assertFalse(fixos_vigencia.periodos_sobrepostos(a, b))

    def test_fim_antes_do_inicio_recusado(self):
        with self.assertRaises(ValueError):
            fixos_vigencia.periodos_sobrepostos({"data_inicio": "2026-05-10", "data_fim": "2026-05-09"},
                                                {"data_inicio": "2026-01-01", "data_fim": None})


# --- M11/M12 e demais "falha fechado" da conciliação ---------------------------
class ConciliacaoFalhaFechado(BancoTemporario):
    def setUp(self):
        super().setUp()
        p = patch.object(conc, "_hoje", lambda: HOJE)
        p.start()
        self.addCleanup(p.stop)
        self.fixo = self.novo_compromisso()
        self.tid = self.nova_transacao()

    def novo_compromisso(self, **extra):
        dados = dict(tipo="fixo", nome="Internet", categoria="Casa", conta_pagamento="Itaú",
                     forma_pagamento="pix", valor=100.0, dia_vencimento=10, data_inicio="2026-06-01",
                     data_fim=None, ativo=True, origem="teste")
        dados.update(extra)
        return db.inserir_compromisso(dados)

    def nova_transacao(self, **extra):
        dados = dict(data="2026-09-10", tipo="despesa", valor=100.0, categoria="Casa", descricao="Internet",
                     conta="Itaú", forma_pagamento="pix", mensagem_original="teste")
        dados.update(extra)
        return db.inserir_transacao(dados)

    def vincular(self, tid=None, alvo=None, chave="k1", usuario="u1"):
        alvo = alvo or conc.alvo(self.fixo, MES)
        with db.fatura_write_transaction() as conn:
            return conc.vincular_conn(conn, self.tid if tid is None else tid, alvo, chave, usuario)

    def eventos(self):
        with db.get_connection() as c:
            return c.execute("SELECT COUNT(*) FROM auditoria_eventos WHERE entidade='conciliacao'").fetchone()[0]

    # caminho feliz, para os negativos abaixo significarem algo
    def test_vinculo_valido_abate_a_projecao(self):
        v = self.vincular()
        self.assertEqual((self.fixo, MES, 10000), (v["compromisso_id"], v["mes"], v["centavos"]))
        item = [i for i in compromissos.projetar_compromissos_mes(MES) if i["id"] == self.fixo][0]
        self.assertEqual((0.0, True), (item["valor"], item.get("conciliado")))

    def test_mesma_confirmacao_repetida_pelo_mesmo_titular_e_idempotente(self):
        self.vincular()
        self.vincular()
        self.assertEqual(1, self.eventos())

    # M11 (:160) replay de confirmação
    def test_m11_confirmacao_reusada_por_outro_usuario_e_recusada(self):
        self.vincular(usuario="u1")
        with self.assertRaisesRegex(conc.ConciliacaoError, "já foi usada"):
            self.vincular(usuario="u2")
        self.assertEqual(1, self.eventos())

    def test_m11_confirmacao_reusada_depois_de_desvincular_e_recusada(self):
        self.vincular()
        self.assertTrue(conc.desvincular("k1", "u1"))
        with self.assertRaisesRegex(conc.ConciliacaoError, "já foi usada"):
            self.vincular()
        self.assertEqual([], conc.listar_vinculos())

    def test_m11_confirmacao_reusada_para_outro_lancamento_e_recusada(self):
        self.vincular()
        outra = self.nova_transacao(valor=0.5)
        with self.assertRaisesRegex(conc.ConciliacaoError, "já foi usada"):
            self.vincular(tid=outra)

    # :162
    def test_confirmacao_apontando_outro_compromisso_e_recusada(self):
        self.vincular()
        outro = self.novo_compromisso(nome="Luz")
        with self.assertRaisesRegex(conc.ConciliacaoError, "outro compromisso"):
            self.vincular(alvo=conc.alvo(outro, MES))

    # :165
    def test_lancamento_ja_vinculado_nao_vincula_de_novo(self):
        self.vincular()
        outro = self.novo_compromisso(nome="Luz")
        with self.assertRaisesRegex(conc.ConciliacaoError, "já está vinculado"):
            self.vincular(alvo=conc.alvo(outro, MES), chave="k2")

    # :168
    def test_compromisso_desativado_depois_da_previa_e_recusado(self):
        alvo = conc.alvo(self.fixo, MES)
        self.sql("UPDATE compromissos SET ativo=0 WHERE id=?", self.fixo)
        with self.assertRaisesRegex(conc.ConciliacaoError, "indisponível"):
            self.vincular(alvo=alvo)
        self.assertEqual(0, self.eventos())

    # :171
    def test_compromisso_alterado_depois_da_previa_e_recusado(self):
        alvo = conc.alvo(self.fixo, MES)
        self.sql("UPDATE compromissos SET valor=120 WHERE id=?", self.fixo)
        with self.assertRaisesRegex(conc.ConciliacaoError, "mudou desde a prévia"):
            self.vincular(alvo=alvo)

    # :175
    def test_tipo_do_lancamento_diferente_e_recusado(self):
        receita = self.nova_transacao(tipo="receita", valor=50.0)
        with self.assertRaisesRegex(conc.ConciliacaoError, "tipo do lançamento"):
            self.vincular(tid=receita)

    # :177 (relógio injetável)
    def test_movimento_futuro_e_recusado_e_o_proprio_dia_aceito(self):
        with patch.object(conc, "_hoje", lambda: date(2026, 9, 9)):
            with self.assertRaisesRegex(conc.ConciliacaoError, "movimento futuro"):
                self.vincular()
        with patch.object(conc, "_hoje", lambda: date(2026, 9, 10)):
            self.vincular()
        self.assertEqual(1, self.eventos())

    def test_relogio_padrao_e_utc_menos_3(self):
        from datetime import datetime, timezone
        instante = datetime(2026, 11, 1, 2, 30, tzinfo=timezone.utc)  # 31/10 23:30 em Brasília

        class Relogio(datetime):
            @classmethod
            def now(cls, tz=None):
                return instante.astimezone(tz)

        with patch.object(conc, "datetime", Relogio):
            self.assertEqual(date(2026, 10, 31), _HOJE_REAL())

    # :178
    def test_conta_que_e_forma_de_pagamento_e_recusada(self):
        self.sql("UPDATE transacoes SET conta='Pix' WHERE id=?", self.tid)
        with self.assertRaisesRegex(conc.ConciliacaoError, "Forma de pagamento não é conta"):
            self.vincular()

    # :188
    def test_antecipacao_para_competencia_futura_e_recusada(self):
        agosto = self.nova_transacao(data="2026-08-10")
        with self.assertRaisesRegex(conc.ConciliacaoError, "Antecipação"):
            self.vincular(tid=agosto)

    # :190
    def test_lancamento_parcelado_e_recusado(self):
        self.sql("UPDATE transacoes SET parcelas_total=2 WHERE id=?", self.tid)
        with self.assertRaisesRegex(conc.ConciliacaoError, "lançamento individual"):
            self.vincular()

    # :194
    def test_valor_acima_do_restante_e_recusado(self):
        maior = self.nova_transacao(valor=100.01)
        with self.assertRaisesRegex(conc.ConciliacaoError, "supera o restante"):
            self.vincular(tid=maior)
        self.vincular(tid=self.nova_transacao(valor=60.0), chave="a")
        with self.assertRaisesRegex(conc.ConciliacaoError, "supera o restante"):
            self.vincular(tid=self.nova_transacao(valor=40.01), chave="b")

    # M12 (:98) adulteração do lançamento conciliado
    def test_m12_lancamento_conciliado_alterado_por_fora_derruba_calculo(self):
        self.vincular()
        self.sql("UPDATE transacoes SET valor=90 WHERE id=?", self.tid)
        with self.assertRaisesRegex(conc.ConciliacaoError, "alterado fora do fluxo"):
            conc.listar_vinculos()
        with self.assertRaises(conc.ConciliacaoError):
            compromissos.projetar_compromissos_mes(MES)

    def test_m12_lancamento_conciliado_apagado_por_fora_derruba_calculo(self):
        self.vincular()
        self.sql("DELETE FROM transacoes WHERE id=?", self.tid)
        with self.assertRaisesRegex(conc.ConciliacaoError, "alterado fora do fluxo"):
            conc.listar_vinculos()

    def test_m12_conta_do_conciliado_alterada_por_fora_derruba_calculo(self):
        self.vincular()
        self.sql("UPDATE transacoes SET conta='Nubank' WHERE id=?", self.tid)
        with self.assertRaisesRegex(conc.ConciliacaoError, "alterado fora do fluxo"):
            conc.listar_vinculos()

    # :130
    def test_compromisso_reduzido_abaixo_do_conciliado_derruba_projecao(self):
        self.vincular()
        with self.assertRaisesRegex(conc.ConciliacaoError, "menor que o já conciliado"):
            conc.ajustar_projecao([{"id": self.fixo, "valor": 50.0}], MES)

    # :142
    def test_alvo_inativo_ou_fora_da_vigencia_e_recusado(self):
        with self.assertRaisesRegex(conc.ConciliacaoError, "não está ativo"):
            conc.alvo(self.fixo, "2026-05")
        self.sql("UPDATE compromissos SET ativo=0 WHERE id=?", self.fixo)
        with self.assertRaisesRegex(conc.ConciliacaoError, "não está ativo"):
            conc.alvo(self.fixo, MES)

    # :209
    def test_lancamento_mudou_desde_a_previa_no_vincular_existente(self):
        alvo = conc.alvo(self.fixo, MES)
        esperado = ["2026-09-10", "despesa", 99.0, "Itaú", "pix"]
        with self.assertRaisesRegex(conc.ConciliacaoError, "mudou desde a prévia"):
            conc.vincular_existente(self.tid, alvo, "k1", "u1", movimento_esperado=esperado)
        self.assertEqual(0, self.eventos())

    # :234 desvincular por outro titular
    def test_desvincular_por_outro_titular_e_recusado(self):
        self.vincular(usuario="1:2")
        with self.assertRaisesRegex(conc.ConciliacaoError, "não encontrado"):
            conc.desvincular("k1", "9:9")
        self.assertTrue(conc.desvincular("k1", "1:2:topic:7"))

    # :250 / :255
    def test_conciliados_bloqueiam_edicao(self):
        self.vincular()
        with db.get_connection() as conn:
            with self.assertRaisesRegex(conc.ConciliacaoError, "Lançamento conciliado"):
                conc.bloquear_alteracao_transacoes(conn, [self.tid])
            with self.assertRaisesRegex(conc.ConciliacaoError, "Compromisso com conciliações"):
                conc.bloquear_alteracao_compromisso(conn, self.fixo)


class GuardaDoBancoOficial(unittest.TestCase):
    """tests/__init__.py: abrir o banco oficial em teste levanta erro."""

    def test_sqlite_connect_no_banco_oficial_levanta(self):
        import tests
        oficial = Path(db.BASE_DIR) / "data" / "financeiro.db"
        for alvo in (oficial, str(oficial), oficial.resolve().as_uri() + "?mode=ro"):
            with self.subTest(alvo=alvo):
                with self.assertRaisesRegex(RuntimeError, "banco oficial"):
                    sqlite3.connect(alvo, uri=str(alvo).startswith("file:"))
        self.assertIsInstance(tests.BancoOficialEmTeste("x"), RuntimeError)

    def test_database_apontando_para_o_oficial_levanta(self):
        oficial = Path(db.BASE_DIR) / "data" / "financeiro.db"
        # mkdir neutralizado: o teste não deve criar data/ na pasta do projeto.
        with patch.object(db, "DB_PATH", oficial), patch.object(Path, "mkdir"):
            with self.assertRaisesRegex(RuntimeError, "banco oficial"):
                db.get_connection()
            with self.assertRaisesRegex(RuntimeError, "banco oficial"):
                with db.read_only_mode():
                    pass

    def test_banco_padrao_da_suite_e_temporario(self):
        import tests
        # No gate o harness usa <stage>/data/fixture.db; fora dele, a pasta temporária.
        self.assertNotIn(tests._chave(db.DB_PATH), tests.bancos_proibidos())
        self.assertNotEqual("financeiro.db", Path(db.DB_PATH).name)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", os.environ)
        self.assertTrue(Path(svc.BACKUPS_DIR).is_absolute())
        self.assertTrue(str(svc.BACKUPS_DIR).startswith(str(tests.PASTA_TEMPORARIA)))

    def test_runtime_do_telegram_fica_na_pasta_temporaria(self):
        import tests
        import estado_runtime
        store = estado_runtime.ProtectedJsonStore(Path(db.BASE_DIR) / ".runtime" / "telegram_sessions.bin")
        self.assertTrue(str(store.path).startswith(str(tests.PASTA_TEMPORARIA)))
        import telegram_experiencia as ux
        if ux.EXPERIENCE.state_store is not None:
            self.assertFalse(str(ux.EXPERIENCE.state_store.path).startswith(str(Path(db.BASE_DIR) / ".runtime")))


if __name__ == "__main__":
    unittest.main()
