"""Jornadas de ponta a ponta (docs/reavaliacao/04_jornadas.md, famílias A-F).

Cada teste percorre uma jornada inteira pelo motor real do Telegram
(``telegram_experiencia.Experience`` + ``dispatch_text``; texto que o motor não
reconhece cai no legado ``services.processar_mensagem``, como no ``app.py``),
grava DE VERDADE num banco temporário (migrations 0001-0004 aplicadas) e confere
os números contra contas feitas à mão, em ``Decimal``, no próprio teste:

* SALDO: ``saldo_resumo.resumir_saldo(services.obter_metricas_resultado_mes(mês))``,
  o mesmo número de Início/Saldo/Fechamento;
* CAIXA POR CONTA: ``services.calcular_caixa_por_conta_mes`` (Saldos por conta);
* FATURAS: ``compromissos.calcular_fatura_unificada`` (A pagar / fatura do cartão);
* A PAGAR: ``Experience._pay_month_open_items`` (tela "Quanto vou pagar");
* CONTAGEM DE LINHAS: transacoes, compromissos, transferencias_caixa, fatura_movimentos.

A navegação é por AÇÃO dos botões (``('answer', 'pix')``, ``('commit', ...)``) e
pelo estado da sessão, nunca por rótulo ou texto de tela; assim a suíte não quebra
quando uma frente muda redação.

"Hoje" é fixo (09/11/2026; 26/11/2026 nas jornadas do corte da fatura) no motor
e no relógio global (``tests.relogio_fixo``). Nada toca ``data/financeiro.db``.
"""
import asyncio
import importlib.util
import shutil
import sqlite3
import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import compromissos
import database as db
import services as svc
import telegram_experiencia as ux
from saldo_resumo import resumir_saldo
from tests.relogio_fixo import data_fixa

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("migration_runner_jornadas", ROOT / "migrations.py")
runner = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = runner
_spec.loader.exec_module(runner)

MES = "2026-11"
CENTAVO = Decimal("0.01")


def D(valor):
    """Float/str do motor -> Decimal de 2 casas (a conta do teste é sempre em Decimal)."""
    return Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


_MODELO = {}


def setUpModule():
    """Banco modelo (init_db + migrations 0001-0004) criado uma vez; cada teste usa uma cópia."""
    pasta = tempfile.TemporaryDirectory()
    _MODELO["pasta"] = pasta
    modelo = Path(pasta.name) / "modelo.db"
    with patch.object(db, "DB_PATH", modelo), patch.object(svc, "DB_PATH", modelo):
        db.init_db()
        # O banco real tem as migrations 0001-0004; sem a 0004 salvar crédito falha.
        runner.apply_migrations(modelo, ROOT / "migrations", Path(pasta.name) / "mig_backups",
                                executed_by="jornadas")
    _MODELO["arquivo"] = modelo


def tearDownModule():
    pasta = _MODELO.pop("pasta", None)
    if pasta is not None:
        pasta.cleanup()


class JornadaBase(unittest.TestCase):
    HOJE = date(2026, 11, 9)
    KEY = "1:1"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        banco = Path(self.tmp.name) / "jornada.db"
        shutil.copyfile(_MODELO["arquivo"], banco)
        for mod, attr, valor in ((db, "DB_PATH", banco), (svc, "DB_PATH", banco),
                                 (svc, "BACKUPS_DIR", Path(self.tmp.name) / "backups")):
            p = patch.object(mod, attr, valor)
            p.start()
            self.addCleanup(p.stop)
        # Uma conexão ociosa mantém o arquivo -wal vivo: sem ela cada get_connection() recria
        # e apaga o -wal (lento no Windows). Fecha antes de apagar a pasta temporária.
        self.conexao_wal = sqlite3.connect(banco)
        self.conexao_wal.execute("PRAGMA journal_mode = WAL")
        self.addCleanup(self.conexao_wal.close)
        self.enterContext(data_fixa(self.HOJE))
        for pend in (svc.PENDENCIAS_ALTERACAO, svc.PENDENCIAS_EXCLUSAO):
            self.addCleanup(pend.clear)
        self.t = [1000.0]
        self.engine = ux.Experience(date_provider=lambda: self.HOJE, clock=lambda: self.t[0])
        p = patch.object(ux, "EXPERIENCE", self.engine)
        p.start()
        self.addCleanup(p.stop)
        self.enviadas = []

        async def fake_send(update, screen, host, edit=False):
            self.enviadas.append(screen)
        p = patch.object(ux, "send_screen", fake_send)
        p.start()
        self.addCleanup(p.stop)
        self.host = SimpleNamespace(
            PENDENCIAS_GUIADAS={}, PENDENCIAS_EXCLUSAO={}, obter_chat_id_update=lambda u: 1,
            limpar_pendencia_guiada=Mock(), limpar_pendencia_exclusao=Mock(), marcar_acesso_seguro=Mock(),
            registrar_mensagem_enviada=Mock(), bloquear_se_assessor_travado=AsyncMock(return_value=False),
            enviar_acao_digitando=AsyncMock(), enviar_acao_enviando_foto=AsyncMock(),
            enviar_resposta=AsyncMock(), iniciar_fluxo_guiado=AsyncMock(), bloquear_assessor=Mock(),
            topics_command=AsyncMock())
        self.tela = None        # última tela do motor novo (None depois de uma resposta do legado)
        self.legado = None      # última resposta de texto do legado

    # ---------------------------------------------------------------- navegação (por ação)
    @staticmethod
    def acoes_de(tela):
        return [tuple(a) for linha in tela.rows for _, a in linha if a]

    def acoes(self):
        return self.acoes_de(self.tela) if self.tela is not None else []

    def achar(self, tipo, arg=None):
        for a in self.acoes():
            if a[0] == tipo and (arg is None or (len(a) > 1 and a[1] == arg)):
                return a
        return None

    def agir(self, acao):
        self.tela = self.engine.act(self.KEY, tuple(acao))
        return self.tela

    def clicar(self, tipo, arg=None):
        acao = self.achar(tipo, arg)
        self.assertIsNotNone(acao, f"a tela atual não oferece a ação {tipo!r} {arg!r}; "
                                   f"estágio={self.estagio()!r}, ações={self.acoes()}")
        return self.agir(acao)

    def estagio(self):
        return self.engine.session(self.KEY).stage

    def dizer(self, texto):
        """Caminho real do Telegram: dispatch_text; se ele devolve False o app.py manda ao legado."""
        self.enviadas.clear()
        chat = SimpleNamespace(id=1, send_message=AsyncMock(), send_photo=AsyncMock())
        update = SimpleNamespace(message=SimpleNamespace(text=texto, reply_text=AsyncMock()), callback_query=None,
                                 effective_user=SimpleNamespace(id=1), effective_chat=chat,
                                 effective_message=SimpleNamespace(message_thread_id=None))
        tratado = asyncio.run(ux.dispatch_text(update, SimpleNamespace(), self.host))
        if tratado:
            self.tela = self.enviadas[-1] if self.enviadas else None
            self.legado = None
            return self.tela
        self.legado = svc.processar_mensagem(texto, sessao=self.KEY)
        self.tela = None
        return self.legado

    def registrar(self, texto, respostas=(), salvar=True):
        """Digita um lançamento, responde às etapas (botão ('answer', x) ou texto) e salva."""
        self.dizer(texto)
        for resposta in respostas:
            if self.achar("answer", resposta):
                self.clicar("answer", resposta)
            else:
                self.dizer(resposta)
        if salvar:
            self.clicar("commit")
        return self.tela

    def ajustar_saldo(self, conta, valor):
        """Assistente "Ajustar saldo" (cash_setup): conta existente pelo seletor ou conta nova."""
        self.agir(("cash_setup_start",))
        if self.achar("cash_setup_account", conta):
            self.clicar("cash_setup_account", conta)
        else:
            if self.achar("cash_setup_new_account"):
                self.clicar("cash_setup_new_account")
            self.dizer(conta)
        self.assertEqual("cash_setup_value", self.estagio())
        self.dizer(valor)
        self.assertEqual("cash_setup_confirm", self.estagio())
        return self.clicar("cash_setup_commit")

    def base(self, **contas):
        for conta, valor in contas.items():
            self.ajustar_saldo(conta, valor)

    def novo_fixo(self, texto, forma):
        self.dizer(texto)
        if self.estagio() == "new_fixed_method":
            self.clicar("new_fixed_answer", forma)
        self.assertEqual("new_fixed_preview", self.estagio())
        return self.clicar("new_fixed_commit")

    def baixar(self, compromisso_id, conta, mes=MES):
        self.agir(("settle", compromisso_id, mes))
        self.assertEqual("account", self.estagio())
        self.clicar("answer", conta)
        return self.clicar("commit")

    def pagar_fatura(self, cartao, mes, conta_pagadora, valor=None):
        """Fluxo de botões "Registrar pagamento da fatura"; valor None = saldo restante."""
        self.agir(("invoice_begin", "B_" + cartao.upper(), mes))
        if valor is None:
            self.clicar("invoice_pay_total")
        else:
            self.clicar("invoice_pay_partial")
            self.dizer(valor)
        self.assertEqual("invoice_account", self.estagio())
        self.clicar("invoice_account_select", conta_pagadora)
        return self.clicar("invoice_commit")

    # ---------------------------------------------------------------- números (o que as telas usam)
    def saldo(self, mes=MES):
        return D(resumir_saldo(svc.obter_metricas_resultado_mes(mes))["saldo_atual"])

    def reservas(self, mes=MES):
        return D(resumir_saldo(svc.obter_metricas_resultado_mes(mes))["reservas_liquidas"])

    def caixa(self, mes=MES):
        contas = svc.calcular_caixa_por_conta_mes(mes).get("contas") or {}
        return {nome: D(dados["disponivel"]) for nome, dados in contas.items()}

    def fatura(self, cartao, mes):
        f = compromissos.calcular_fatura_unificada(mes, cartao)
        return SimpleNamespace(bruto=D(f["valor_bruto"]), pago=D(f["pagamentos"]),
                               restante=D(f["saldo_restante"]), status=f["status"])

    def a_pagar(self, mes=MES):
        """Total da tela "Quanto vou pagar" e total por conta."""
        por_conta = {}
        for item in self.engine._pay_month_open_items(mes):
            conta = (item.get("conta") or "").strip() or "Sem conta"
            por_conta[conta] = por_conta.get(conta, Decimal("0")) + D(item.get("valor") or 0)
        return sum(por_conta.values(), Decimal("0")), por_conta

    def contagens(self):
        with db.get_connection() as c:
            return {t: c.execute("SELECT count(*) FROM " + t).fetchone()[0]
                    for t in ("transacoes", "compromissos", "transferencias_caixa", "fatura_movimentos")}

    def linhas(self, sql, *params):
        with db.get_connection() as c:
            return [tuple(r) for r in c.execute(sql, params).fetchall()]

    def ultimo_id(self, tabela="transacoes"):
        return self.linhas(f"SELECT max(id) FROM {tabela}")[0][0]


class JornadasDoMes(JornadaBase):
    """Hoje = 09/11/2026 (antes do corte da fatura, dia 25)."""

    # ------------------------------------------------------------------ A. primeiro uso
    def test_a_primeiro_uso_saldos_por_conta_e_conta_nova(self):
        """Banco vazio -> saldo de Itaú pelo assistente e Nubank como conta nova; nada vira lançamento."""
        self.assertEqual({}, self.caixa())
        self.assertEqual(Decimal("0.00"), self.saldo())
        self.ajustar_saldo("Itaú", "3000")
        self.ajustar_saldo("Nubank", "800")  # conta nova
        # Itaú 3000,00 + Nubank 800,00 = 3800,00
        self.assertEqual({"Itaú": Decimal("3000.00"), "Nubank": Decimal("800.00")}, self.caixa())
        self.assertEqual(Decimal("3800.00"), self.saldo())
        self.assertEqual({"transacoes": 0, "compromissos": 0, "transferencias_caixa": 0, "fatura_movimentos": 0},
                         self.contagens())  # ajuste de saldo não cria receita nem despesa
        self.assertEqual({"Itaú", "Nubank"}, set(self.engine.accounts()))
        # Desistir no meio de um ajuste não grava nada (Inter nunca chega a existir).
        self.agir(("cash_setup_start",))
        self.clicar("cash_setup_new_account")
        self.dizer("Inter")
        self.dizer("999")
        self.assertEqual("cash_setup_confirm", self.estagio())
        self.clicar("cancel")
        self.assertEqual({"Itaú": Decimal("3000.00"), "Nubank": Decimal("800.00")}, self.caixa())
        self.assertEqual(Decimal("3800.00"), self.saldo())
        self.assertNotIn("Inter", self.engine.accounts())

    # ------------------------------------------------------------------ B. mês de vida real
    def test_b1_salario_e_gastos_a_vista_pix_debito_dinheiro(self):
        """Salário + gastos em pix, débito e dinheiro: forma não é conta, o caixa sai da conta escolhida."""
        self.base(**{"Itaú": "3000", "Nubank": "800"})
        self.registrar("recebi salário 3800 no itaú", ["pix"])
        self.registrar("gastei 45,90 no mercado", ["pix", "Itaú"])
        self.registrar("paguei 12 de padaria no débito", ["Itaú"])
        self.registrar("gastei 20 em dinheiro na farmácia", ["Itaú"])
        self.registrar("gastei 30 no pix lanche", ["Nubank"])
        # Itaú: 3000 + 3800 (salário) − 45,90 (pix) − 12 (débito) − 20 (dinheiro) = 6722,10
        # Nubank: 800 − 30 (pix) = 770,00
        self.assertEqual({"Itaú": Decimal("6722.10"), "Nubank": Decimal("770.00")}, self.caixa())
        # Saldo geral: 6722,10 + 770,00 = 7492,10 (Pix/Dinheiro nunca viram conta)
        self.assertEqual(Decimal("7492.10"), self.saldo())
        self.assertEqual({"transacoes": 5, "compromissos": 0, "transferencias_caixa": 0, "fatura_movimentos": 0},
                         self.contagens())
        self.assertEqual(
            [("receita", "pix", "Itaú", "3800.0"), ("despesa", "pix", "Itaú", "45.9"),
             ("despesa", "débito", "Itaú", "12.0"), ("despesa", "dinheiro", "Itaú", "20.0"),
             ("despesa", "pix", "Nubank", "30.0")],
            [(t, f, c, str(v)) for t, f, c, v in self.linhas(
                "SELECT tipo, forma_pagamento, conta, valor FROM transacoes ORDER BY id")])

    def test_b2_credito_a_vista_vai_para_a_fatura_e_nao_para_o_caixa(self):
        """Compra no crédito à vista antes do corte: fatura de novembro, caixa intacto, reserva do mesmo valor."""
        self.base(**{"Itaú": "3000", "Nubank": "800"})
        self.registrar("comprei tênis 200 no crédito no nubank", ["não"])
        self.assertEqual({"Itaú": Decimal("3000.00"), "Nubank": Decimal("800.00")}, self.caixa())
        self.assertEqual(Decimal("3800.00"), self.saldo())
        f = self.fatura("Nubank", MES)
        self.assertEqual((Decimal("200.00"), Decimal("200.00")), (f.bruto, f.restante))
        self.assertEqual(Decimal("0.00"), self.fatura("Nubank", "2026-12").bruto)
        # reservado para pagar = a fatura em aberto (200,00)
        self.assertEqual(Decimal("200.00"), self.reservas())
        self.assertEqual([("crédito", "2026-11", "2026-11-09", "Nubank")],
                         self.linhas("SELECT forma_pagamento, competencia_fatura, data_compra, conta FROM transacoes"))

    def test_b3_parcelado_3x_e_10x_distribui_centavos_e_competencias(self):
        """Parcelamentos 3x (1000) e 10x (3000): linhas, soma exata e uma fatura por mês."""
        self.base(**{"Itaú": "3000", "Nubank": "800"})
        self.registrar("celular 1000 em 3x no nubank")
        self.registrar("tv 3000 em 10x no nubank")
        # 3 + 10 parcelas; nada sai do caixa
        self.assertEqual(13, self.contagens()["transacoes"])
        self.assertEqual({"Itaú": Decimal("3000.00"), "Nubank": Decimal("800.00")}, self.caixa())
        p3 = [D(v) for (v,) in self.linhas(
            "SELECT valor FROM transacoes WHERE parcelas_total=3 ORDER BY parcela_atual")]
        # 1000 / 3 = 333,33 + 333,33 + 333,34 (a diferença de 1 centavo fica numa parcela; o total é exato)
        self.assertEqual(Decimal("1000.00"), sum(p3, Decimal("0")))
        self.assertEqual({Decimal("333.33"), Decimal("333.34")}, set(p3))
        p10 = [D(v) for (v,) in self.linhas("SELECT valor FROM transacoes WHERE parcelas_total=10")]
        self.assertEqual([Decimal("300.00")] * 10, p10)  # 3000 / 10
        # Faturas: nov = 1ª de cada (1ª do 3x + 300), dez = 2ª de cada, jan = 3ª de cada, fev..ago = só a TV (300).
        self.assertEqual(p3[0] + Decimal("300.00"), self.fatura("Nubank", "2026-11").bruto)
        self.assertEqual(p3[1] + Decimal("300.00"), self.fatura("Nubank", "2026-12").bruto)
        self.assertEqual(p3[2] + Decimal("300.00"), self.fatura("Nubank", "2027-01").bruto)
        for mes in ("2027-02", "2027-08"):  # a TV segue em 300 até a 10ª parcela
            self.assertEqual(Decimal("300.00"), self.fatura("Nubank", mes).bruto, mes)
        self.assertEqual(Decimal("0.00"), self.fatura("Nubank", "2027-09").bruto)  # a TV acabou em ago/2027
        # Soma das 13 parcelas = 1000 + 3000 (as faturas intermediárias repetem o mesmo 300)
        self.assertEqual(Decimal("4000.00"), sum(
            (D(v) for (v,) in self.linhas("SELECT valor FROM transacoes")), Decimal("0")))
        # Desfazer (a última confirmação = a TV) apaga o parcelamento inteiro, nunca uma parcela só.
        self.clicar("undo_preview")
        self.clicar("undo")
        self.assertEqual(3, self.contagens()["transacoes"])
        self.assertEqual(Decimal("0.00"), self.fatura("Nubank", "2027-08").bruto)
        self.assertEqual(p3[0], self.fatura("Nubank", "2026-11").bruto)

    def test_b6_fixos_novos_e_baixa_com_escolha_da_conta(self):
        """Novo fixo (pix e crédito) é só previsão; a baixa grava na conta ESCOLHIDA, não na do fixo."""
        self.base(**{"Itaú": "3000", "Nubank": "800"})
        self.novo_fixo("novo fixo aluguel 1500 todo dia 5 no itaú", "pix")
        self.novo_fixo("novo fixo netflix 55 dia 10 crédito nubank", "credito")
        self.novo_fixo("novo fixo academia 120 dia 20 pix itaú", "pix")
        ids = {nome: i for i, nome in self.linhas("SELECT id, nome FROM compromissos")}
        self.assertEqual({"Aluguel", "Netflix", "Academia"}, set(ids))
        # Cadastrar fixo não grava nada de caixa; o Netflix (crédito) compõe a fatura do Nubank.
        self.assertEqual({"transacoes": 0, "compromissos": 3, "transferencias_caixa": 0, "fatura_movimentos": 0},
                         self.contagens())
        self.assertEqual({"Itaú": Decimal("3000.00"), "Nubank": Decimal("800.00")}, self.caixa())
        self.assertEqual(Decimal("3800.00"), self.saldo())
        self.assertEqual(Decimal("55.00"), self.fatura("Nubank", MES).bruto)
        # A pagar em novembro: aluguel 1500 + academia 120 (Itaú) + fatura Nubank 55 = 1675
        total, por_conta = self.a_pagar()
        self.assertEqual(Decimal("1675.00"), total)
        self.assertEqual({"Itaú": Decimal("1620.00"), "Nubank": Decimal("55.00")}, por_conta)
        # Baixa do aluguel na conta cadastrada (Itaú): 3000 − 1500 = 1500
        self.baixar(ids["Aluguel"], "Itaú")
        # Baixa da academia pagando com OUTRA conta (Nubank): 800 − 120 = 680
        self.baixar(ids["Academia"], "Nubank")
        self.assertEqual({"Itaú": Decimal("1500.00"), "Nubank": Decimal("680.00")}, self.caixa())
        self.assertEqual(Decimal("2180.00"), self.saldo())  # 3800 − 1500 − 120
        self.assertEqual([("Aluguel", "Itaú", "1500.0"), ("Academia", "Nubank", "120.0")],
                         [(d, c, str(v)) for d, c, v in self.linhas(
                             "SELECT descricao, conta, valor FROM transacoes ORDER BY id")])
        # Sobrou a fatura do Netflix (55) a pagar.
        total, por_conta = self.a_pagar()
        self.assertEqual((Decimal("55.00"), {"Nubank": Decimal("55.00")}), (total, por_conta))
        self.assertEqual(Decimal("55.00"), self.fatura("Nubank", MES).bruto)  # baixa pix não é compra no cartão
        self.assertEqual({"transacoes": 2, "compromissos": 3, "transferencias_caixa": 0, "fatura_movimentos": 0},
                         self.contagens())

    def test_b7_transferencia_entre_contas_nao_e_receita_nem_despesa(self):
        """Transferência Itaú -> Nubank move o caixa por conta, mantém o total e não cria lançamento."""
        self.base(**{"Itaú": "3000", "Nubank": "800"})
        self.dizer("transferi 100 do itaú para o nubank")
        self.clicar("media_transfer_commit")
        self.assertEqual({"Itaú": Decimal("2900.00"), "Nubank": Decimal("900.00")}, self.caixa())
        self.assertEqual(Decimal("3800.00"), self.saldo())  # 2900 + 900: o total entre as contas não muda
        self.assertEqual({"transacoes": 0, "compromissos": 0, "transferencias_caixa": 1, "fatura_movimentos": 0},
                         self.contagens())
        self.assertEqual([("Itaú", "Nubank", 100.0)],
                         self.linhas("SELECT conta_origem, conta_destino, valor FROM transferencias_caixa"))
        # Descartar a segunda prévia não grava.
        self.dizer("transferi 250 do nubank para o itaú")
        self.agir(("media_kind", self.achar("media_transfer_commit")[1], "discard"))
        self.assertEqual(1, self.contagens()["transferencias_caixa"])
        self.assertEqual({"Itaú": Decimal("2900.00"), "Nubank": Decimal("900.00")}, self.caixa())

    def test_b8_fatura_estorno_pagamento_parcial_e_total(self):
        """Estorno abate a fatura sem tocar o caixa; pagamento (parcial e total) sai da conta e nunca é gasto."""
        self.base(**{"Itaú": "3000", "Nubank": "800"})
        self.registrar("comprei tênis 200 no crédito no nubank", ["não"])
        # Estorno de 50 (texto, prévia + confirmação no legado): fatura 200 − 50 = 150; caixa não muda.
        self.dizer("estorno de 50 na fatura nubank")
        self.assertEqual(0, self.contagens()["fatura_movimentos"])  # só prévia
        self.dizer("confirmar estorno")
        f = self.fatura("Nubank", MES)
        self.assertEqual((Decimal("200.00"), Decimal("150.00")), (f.bruto, f.restante))
        self.assertEqual({"Itaú": Decimal("3000.00"), "Nubank": Decimal("800.00")}, self.caixa())
        # Pagamento parcial de 50 pelo Itaú: restante 150 − 50 = 100; Itaú 3000 − 50 = 2950
        self.pagar_fatura("Nubank", MES, "Itaú", "50")
        f = self.fatura("Nubank", MES)
        self.assertEqual((Decimal("50.00"), Decimal("100.00")), (f.pago, f.restante))
        self.assertEqual({"Itaú": Decimal("2950.00"), "Nubank": Decimal("800.00")}, self.caixa())
        self.assertEqual(Decimal("3750.00"), self.saldo())
        # Pagamento do saldo restante (100) pelo Itaú: 2950 − 100 = 2850; fatura zerada
        self.pagar_fatura("Nubank", MES, "Itaú")
        f = self.fatura("Nubank", MES)
        self.assertEqual((Decimal("150.00"), Decimal("0.00")), (f.pago, f.restante))
        self.assertEqual({"Itaú": Decimal("2850.00"), "Nubank": Decimal("800.00")}, self.caixa())
        # Saldo: 3800 − 150 pagos = 3650; nada mais reservado (o estorno de 50 não saiu do caixa)
        self.assertEqual(Decimal("3650.00"), self.saldo())
        self.assertEqual(Decimal("0.00"), self.reservas())
        # Pagamento de fatura nunca é gasto: segue 1 transação (a compra) e 3 movimentos de fatura.
        self.assertEqual({"transacoes": 1, "compromissos": 0, "transferencias_caixa": 0, "fatura_movimentos": 3},
                         self.contagens())
        self.assertEqual([("estorno", 50.0), ("pagamento_parcial", 50.0), ("pagamento_total", 100.0)],
                         self.linhas("SELECT tipo_movimento, valor FROM fatura_movimentos ORDER BY id"))
        self.assertEqual(Decimal("0.00"), self.a_pagar()[0])

    def test_b9_ajuste_de_saldo_pelo_seletor_nao_cria_lancamento(self):
        """Ajustar o saldo de uma conta existente corrige o caixa e não mexe nos lançamentos; gastos seguintes seguem."""
        self.base(**{"Itaú": "3000", "Nubank": "800"})
        self.registrar("gastei 45,90 no mercado", ["pix", "Itaú"])
        self.assertEqual(Decimal("2954.10"), self.caixa()["Itaú"])  # 3000 − 45,90
        self.ajustar_saldo("Itaú", "2900")  # o banco mostra 2900,00
        self.assertEqual({"Itaú": Decimal("2900.00"), "Nubank": Decimal("800.00")}, self.caixa())
        self.assertEqual(Decimal("3700.00"), self.saldo())  # 2900 + 800
        self.assertEqual(1, self.contagens()["transacoes"])  # nenhuma receita/despesa de ajuste
        self.registrar("gastei 10 de café", ["pix", "Itaú"])
        # depois do ajuste o caixa continua andando: 2900 − 10 = 2890
        self.assertEqual({"Itaú": Decimal("2890.00"), "Nubank": Decimal("800.00")}, self.caixa())
        self.assertEqual(Decimal("3690.00"), self.saldo())
        self.assertEqual(2, self.contagens()["transacoes"])

    def test_b10_desfazer_trocar_categoria_repetir_e_duplicata(self):
        """Desfazer devolve o caixa; trocar categoria só muda a categoria; repetir avisa duplicata e só grava se confirmar."""
        self.base(**{"Itaú": "3000"})
        self.registrar("gastei 45,90 no mercado", ["pix", "Itaú"])
        self.assertEqual(Decimal("2954.10"), self.caixa()["Itaú"])
        # desfazer: prévia -> confirmar; a linha some e o caixa volta a 3000
        self.clicar("undo_preview")
        self.assertEqual(1, self.contagens()["transacoes"])  # prévia não apaga
        self.clicar("undo")
        self.assertEqual(0, self.contagens()["transacoes"])
        self.assertEqual(Decimal("3000.00"), self.caixa()["Itaú"])
        # registrar de novo e trocar a categoria (prévia -> confirmar)
        self.registrar("gastei 45,90 no mercado", ["pix", "Itaú"])
        tid = self.ultimo_id()
        self.agir(("cat_preview", tid, "Alimentação"))
        self.assertEqual("Mercado", self.linhas("SELECT categoria FROM transacoes WHERE id=?", tid)[0][0])
        self.clicar("cat_confirm")
        self.assertEqual(("Alimentação", 45.9, "Itaú"),
                         self.linhas("SELECT categoria, valor, conta FROM transacoes WHERE id=?", tid)[0])
        self.assertEqual(Decimal("2954.10"), self.caixa()["Itaú"])  # categoria não mexe no caixa
        # repetir: a tela avisa duplicata (ação "ver o original"); cancelar não grava
        self.agir(("repeat", tid))
        self.assertIsNotNone(self.achar("dup_view", tid))
        self.clicar("cancel")
        self.assertEqual(1, self.contagens()["transacoes"])
        # repetir e "salvar mesmo assim": 2 linhas, caixa 3000 − 2 × 45,90 = 2908,20
        self.agir(("repeat", tid))
        self.clicar("commit")
        self.assertEqual(2, self.contagens()["transacoes"])
        self.assertEqual(Decimal("2908.20"), self.caixa()["Itaú"])
        self.assertEqual(Decimal("2908.20"), self.saldo())

    def test_b11_correcao_e_exclusao_so_gravam_depois_da_previa_confirmada(self):
        """Corrigir valor e apagar (texto legado): prévia não grava, cancelar não grava, confirmar grava."""
        self.base(**{"Itaú": "3000"})
        self.registrar("gastei 45,90 no mercado", ["pix", "Itaú"])
        tid = self.ultimo_id()
        # correção com prévia
        self.dizer(f"corrigir valor {tid} para 80")
        self.assertEqual(Decimal("2954.10"), self.caixa()["Itaú"])  # prévia: nada mudou
        self.dizer("cancelar alteracao")
        self.assertEqual(45.9, self.linhas("SELECT valor FROM transacoes WHERE id=?", tid)[0][0])
        self.dizer(f"corrigir valor {tid} para 80")
        self.dizer("confirmar alteracao")
        self.assertEqual(80.0, self.linhas("SELECT valor FROM transacoes WHERE id=?", tid)[0][0])
        self.assertEqual(Decimal("2920.00"), self.caixa()["Itaú"])  # 3000 − 80
        # exclusão com prévia: cancelar mantém; confirmar apaga e devolve o caixa
        self.dizer(f"apagar {tid}")
        self.assertEqual(1, self.contagens()["transacoes"])
        self.dizer("cancelar exclusao")
        self.assertEqual(1, self.contagens()["transacoes"])
        self.dizer(f"apagar {tid}")
        self.assertEqual(1, self.contagens()["transacoes"])  # ainda só prévia
        self.dizer("confirmar exclusao")
        self.assertEqual(0, self.contagens()["transacoes"])
        self.assertEqual(Decimal("3000.00"), self.caixa()["Itaú"])
        self.assertEqual(Decimal("3000.00"), self.saldo())

    def test_c_consultas_quanto_vou_pagar_historico_e_fechamento(self):
        """Mês montado: confere NÚMEROS de A pagar (novembro e dezembro), Histórico e Fechamento."""
        self.base(**{"Itaú": "3000", "Nubank": "800"})
        self.registrar("recebi salário 3800 no itaú", ["pix"])
        self.registrar("gastei 45,90 no mercado", ["pix", "Itaú"])
        self.registrar("comprei tênis 200 no crédito no nubank", ["não"])
        self.registrar("celular 900 em 3x no nubank")
        self.novo_fixo("novo fixo aluguel 1500 todo dia 5 no itaú", "pix")
        self.novo_fixo("novo fixo netflix 55 dia 10 crédito nubank", "credito")
        # Quanto vou pagar, novembro: fatura Nubank 200 + 300 (1ª parcela) + 55 (Netflix) = 555; aluguel 1500
        total, por_conta = self.a_pagar("2026-11")
        self.assertEqual(Decimal("2055.00"), total)
        self.assertEqual({"Nubank": Decimal("555.00"), "Itaú": Decimal("1500.00")}, por_conta)
        # dezembro: Nubank 300 (2ª parcela) + 55 (Netflix); aluguel 1500
        total, por_conta = self.a_pagar("2026-12")
        self.assertEqual(Decimal("1855.00"), total)
        self.assertEqual({"Nubank": Decimal("355.00"), "Itaú": Decimal("1500.00")}, por_conta)
        # a mesma pergunta digitada abre a tela de A pagar do mês (ações), sem gravar
        antes = self.contagens()
        self.dizer("quanto vou pagar")
        self.assertIsNotNone(self.achar("view", "pay"))
        self.assertEqual(antes, self.contagens())
        # Histórico de novembro: salário, mercado, tênis e 1ª parcela = 4 linhas; dezembro: 2ª parcela = 1
        self.assertEqual(4, len(db.buscar_transacoes_por_mes("2026-11")))
        self.assertEqual(1, len(db.buscar_transacoes_por_mes("2026-12")))
        # Fechamento / saldo: 3000 + 800 + 3800 − 45,90 = 7554,10 disponíveis (o crédito não sai do caixa)
        self.assertEqual({"Itaú": Decimal("6754.10"), "Nubank": Decimal("800.00")}, self.caixa())
        self.assertEqual(Decimal("7554.10"), self.saldo())
        metricas = svc.obter_metricas_resultado_mes("2026-11")
        self.assertEqual(Decimal("3800.00"), D(metricas["entradas_realizadas"]))

    def test_d_gerenciar_contas_desativar_e_reativar(self):
        """Desativar conta sem saldo mantém o histórico; conta com saldo não desativa; reativar devolve às listas."""
        self.base(**{"Itaú": "3000", "Carteira": "50"})
        self.registrar("gastei 50 na farmácia", ["dinheiro", "Carteira"])
        self.assertEqual({"Itaú": Decimal("3000.00"), "Carteira": Decimal("0.00")}, self.caixa())  # 50 − 50
        self.agir(("acct_off", "Carteira"))
        self.assertIsNotNone(self.achar("acct_off_ok", "Carteira"))  # pede confirmação
        self.assertIn("Carteira", self.engine.accounts())  # a prévia não desativa
        self.clicar("acct_off_ok", "Carteira")
        self.assertNotIn("Carteira", self.engine.accounts())
        self.assertIn("Carteira", self.engine.accounts(incluir_inativas=True))
        self.assertEqual(1, self.contagens()["transacoes"])  # histórico intacto
        self.assertEqual("Carteira", self.linhas("SELECT conta FROM transacoes")[0][0])
        # Itaú tem saldo (3000): mesmo forçando a confirmação a regra vale
        self.agir(("acct_off_ok", "Itaú"))
        self.assertIn("Itaú", self.engine.accounts())
        # reativar
        self.agir(("acct_on", "Carteira"))
        self.assertEqual({"Carteira", "Itaú"}, set(self.engine.accounts()))
        self.assertEqual(Decimal("3000.00"), self.saldo())

    def test_f_bordas_callback_expirado_clique_repetido_cancelar_e_texto_na_confirmacao(self):
        """Callback expirado, Salvar clicado 2x, Cancelar e texto solto na conferência: nada grava duas vezes."""
        self.base(**{"Itaú": "3000"})
        antes = self.contagens()
        # a) callback expirado: o token do Salvar morre depois do TTL e nada é gravado
        self.dizer("gastei 45,90 no mercado")
        self.clicar("answer", "pix")
        self.clicar("answer", "Itaú")
        self.assertEqual("confirm", self.estagio())
        tokens = self.engine.tokens_for(self.KEY, self.tela)
        token_salvar = next(tok for linha in tokens for _, tok in linha
                            if tok and self.engine.session(self.KEY).tokens[tok][0] == "commit")
        self.t[0] += ux.TTL + 1
        self.assertIsNone(self.engine.resolve(self.KEY, token_salvar))
        self.assertEqual(antes, self.contagens())
        self.assertEqual(Decimal("3000.00"), self.caixa()["Itaú"])
        # b) clique repetido em Salvar: o token válido grava uma vez; a segunda confirmação não duplica
        self.dizer("gastei 45,90 no mercado")
        self.clicar("answer", "pix")
        self.clicar("answer", "Itaú")
        tokens = self.engine.tokens_for(self.KEY, self.tela)
        token_salvar = next(tok for linha in tokens for _, tok in linha
                            if tok and self.engine.session(self.KEY).tokens[tok][0] == "commit")
        acao = self.engine.resolve(self.KEY, token_salvar)
        self.assertEqual("commit", acao[0])
        self.agir(acao)
        try:
            self.agir(acao)  # segundo clique no mesmo botão (a tela antiga continua na conversa)
        except ValueError:
            pass  # "Essa confirmação expirou ou já foi usada"
        self.assertEqual(1, self.contagens()["transacoes"])
        self.assertEqual(Decimal("2954.10"), self.caixa()["Itaú"])
        # c) texto solto na conferência não grava; cancelar não grava
        self.dizer("gastei 99 na pizzaria")
        self.clicar("answer", "pix")
        self.clicar("answer", "Itaú")
        self.dizer("99")
        self.assertEqual(1, self.contagens()["transacoes"])
        self.clicar("cancel") if self.achar("cancel") else self.agir(("cancel",))
        self.assertEqual(1, self.contagens()["transacoes"])
        self.assertEqual(Decimal("2954.10"), self.caixa()["Itaú"])
        self.assertEqual(Decimal("2954.10"), self.saldo())


class JornadaCorteDaFatura(JornadaBase):
    """Hoje = 26/11/2026: depois do corte (dia 25, inclusivo) o titular escolhe o mês da fatura."""
    HOJE = date(2026, 11, 26)

    def test_e_compra_apos_o_corte_exige_escolher_a_competencia(self):
        """Crédito à vista e parcelado depois do corte: escolha respeitada, data real preservada, pix não pergunta."""
        self.base(**{"Itaú": "3000", "Nubank": "800"})
        # pix no dia do corte não tem fatura: não pergunta competência
        self.dizer("gastei 30 no pix lanche")
        self.clicar("answer", "Nubank")
        self.assertNotEqual("billing_month", self.estagio())
        self.clicar("commit")
        # crédito à vista: pergunta; escolhe dezembro
        self.dizer("comprei jaqueta 100 no crédito no nubank")
        if self.estagio() == "installment_choice":
            self.clicar("answer", "não")
        self.assertEqual("billing_month", self.estagio())
        self.assertIsNotNone(self.achar("answer", "2026-11"))
        self.assertIsNotNone(self.achar("answer", "2026-12"))
        self.clicar("answer", "2026-12")
        self.clicar("commit")
        self.assertEqual(Decimal("0.00"), self.fatura("Nubank", "2026-11").bruto)
        self.assertEqual(Decimal("100.00"), self.fatura("Nubank", "2026-12").bruto)
        # outra compra à vista, agora escolhendo a fatura que fecha (novembro)
        self.dizer("comprei livro 60 no crédito no nubank")
        if self.estagio() == "installment_choice":
            self.clicar("answer", "não")
        self.clicar("answer", "2026-11")
        self.clicar("commit")
        self.assertEqual(Decimal("60.00"), self.fatura("Nubank", "2026-11").bruto)
        self.assertEqual(Decimal("100.00"), self.fatura("Nubank", "2026-12").bruto)
        # parcelado 3x de 900 com a 1ª parcela em dezembro: 300 em dez, jan e fev
        self.registrar("celular 900 em 3x no nubank", ["2026-12"])
        self.assertEqual(Decimal("400.00"), self.fatura("Nubank", "2026-12").bruto)  # 100 + 300
        self.assertEqual(Decimal("300.00"), self.fatura("Nubank", "2027-01").bruto)
        self.assertEqual(Decimal("300.00"), self.fatura("Nubank", "2027-02").bruto)
        self.assertEqual(Decimal("0.00"), self.fatura("Nubank", "2027-03").bruto)
        # data_compra guarda o dia real (26/11) em todas as parcelas; a competência é a escolhida
        self.assertEqual([("2026-11-26", "2026-12"), ("2026-11-26", "2027-01"), ("2026-11-26", "2027-02")],
                         self.linhas("SELECT data_compra, competencia_fatura FROM transacoes "
                                     "WHERE parcelas_total=3 ORDER BY parcela_atual"))
        # o crédito nunca sai do caixa: só o pix de 30 do Nubank (800 − 30 = 770)
        self.assertEqual({"Itaú": Decimal("3000.00"), "Nubank": Decimal("770.00")}, self.caixa())
        self.assertEqual(Decimal("3770.00"), self.saldo())
        self.assertEqual(6, self.contagens()["transacoes"])  # pix + 100 + 60 + 3 parcelas
        # desfazer o parcelado apaga as 3 parcelas de uma vez
        self.clicar("undo_preview")
        self.clicar("undo")
        self.assertEqual(3, self.contagens()["transacoes"])
        self.assertEqual(Decimal("100.00"), self.fatura("Nubank", "2026-12").bruto)
        self.assertEqual(Decimal("0.00"), self.fatura("Nubank", "2027-01").bruto)


class JornadaMesCompleto(JornadaBase):
    """Um mês inteiro de uso, com todos os recursos juntos e uma conferência final única."""

    def test_mes_completo_integrado(self):
        # Primeiro uso: Itaú 3000, Nubank 800.
        self.base(**{"Itaú": "3000", "Nubank": "800"})
        # Salário e gastos à vista no Itaú.
        self.registrar("recebi salário 3800 no itaú", ["pix"])
        self.registrar("gastei 45,90 no mercado", ["pix", "Itaú"])
        self.registrar("paguei 12 de padaria no débito", ["Itaú"])
        # Crédito: à vista 200 e 3x de 900 no Nubank.
        self.registrar("comprei tênis 200 no crédito no nubank", ["não"])
        self.registrar("celular 900 em 3x no nubank")
        # Fixos: aluguel (pix, Itaú) e netflix (crédito, Nubank); baixa do aluguel.
        self.novo_fixo("novo fixo aluguel 1500 todo dia 5 no itaú", "pix")
        self.novo_fixo("novo fixo netflix 55 dia 10 crédito nubank", "credito")
        aluguel = {n: i for i, n in self.linhas("SELECT id, nome FROM compromissos")}["Aluguel"]
        self.baixar(aluguel, "Itaú")
        # Transferência Itaú -> Nubank de 500.
        self.dizer("transferi 500 do itaú para o nubank")
        self.clicar("media_transfer_commit")
        # Estorno de 40 e pagamento parcial de 100 da fatura de novembro, pelo Nubank.
        self.dizer("estorno de 40 na fatura nubank")
        self.dizer("confirmar estorno")
        self.pagar_fatura("Nubank", MES, "Nubank", "100")
        # Itaú: 3000 + 3800 − 45,90 − 12 − 1500 (aluguel) − 500 (transferência) = 4742,10
        # Nubank: 800 + 500 (transferência) − 100 (pagamento de fatura) = 1200,00
        self.assertEqual({"Itaú": Decimal("4742.10"), "Nubank": Decimal("1200.00")}, self.caixa())
        self.assertEqual(Decimal("5942.10"), self.saldo())
        # Fatura de novembro: 200 + 300 (1ª parcela) + 55 (Netflix) = 555; − 40 (estorno) − 100 (pago) = 415
        f = self.fatura("Nubank", MES)
        self.assertEqual((Decimal("555.00"), Decimal("100.00"), Decimal("415.00")), (f.bruto, f.pago, f.restante))
        # Dezembro e janeiro: 2ª e 3ª parcelas (300) + Netflix recorrente (55) em dezembro e janeiro
        self.assertEqual(Decimal("355.00"), self.fatura("Nubank", "2026-12").bruto)
        self.assertEqual(Decimal("355.00"), self.fatura("Nubank", "2027-01").bruto)
        # Linhas: salário, mercado, padaria, tênis, 3 parcelas, baixa do aluguel = 8; 2 fixos; 1 transferência;
        # 2 movimentos de fatura (estorno + pagamento).
        self.assertEqual({"transacoes": 8, "compromissos": 2, "transferencias_caixa": 1, "fatura_movimentos": 2},
                         self.contagens())
        # O que sobra a pagar em novembro: fatura Nubank 415 (aluguel já baixado)
        total, por_conta = self.a_pagar()
        self.assertEqual((Decimal("415.00"), {"Nubank": Decimal("415.00")}), (total, por_conta))
        # Pagamento de fatura e transferência nunca viram despesa/receita em transacoes.
        self.assertEqual({"receita": 1, "despesa": 7},
                         dict(self.linhas("SELECT tipo, count(*) FROM transacoes GROUP BY tipo")))


if __name__ == "__main__":
    unittest.main()
