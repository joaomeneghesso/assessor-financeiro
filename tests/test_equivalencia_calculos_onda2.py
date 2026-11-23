"""Equivalência numérica dos cálculos de saldo/fatura/checklist (Onda 2).

Protege otimizações de desempenho (cache, memoização, menos consultas): a saída
completa de ``obter_metricas_resultado_mes``, ``calcular_caixa_por_conta_mes``,
``calcular_saldo_mensal`` (geral e por conta), ``calcular_fatura_unificada``,
``montar_itens_checklist_mes`` e ``resumir_saldo`` tem de continuar idêntica
à registrada no golden ``tests/fixtures/equivalencia_calculos_onda2.json``.

O golden foi gerado com o código ORIGINAL do commit afa6933 (cópia limpa via
``git archive afa6933``), rodando este mesmo arquivo com
``REGERAR_GOLDEN_ONDA2=1``. Para regenerar (somente se uma mudança de regra
de negócio for intencional, nunca por causa de otimização)::

    $env:REGERAR_GOLDEN_ONDA2 = '1'
    .\\.venv\\Scripts\\python.exe -m unittest tests.test_equivalencia_calculos_onda2

Cenários (bancos temporários, relógio congelado em 2027-03-15):
  1. 12 meses (2026-04..2027-03) encadeados por herança, base confirmada só
     no 1º mês; contas Itaú, Mercado Pago, C6; cartões Nubank e Inter (corte
     dia 25); parcelado 6x e 3x; fixos (Aluguel, Escola com nova condição,
     Internet nunca paga, Academia no cartão); conciliações (despesa paga em mês
     posterior, receita); transferências; pagamentos de fatura feitos no mês
     posterior; receita prevista não recebida.
  2. Mesmo movimento, porém sem base no 1º mês: bases confirmadas no meio da
     cadeia (2026-09 e 2027-01) e saldo inicial de uma conta levado à frente
     num mês herdado (2026-11).

Cada mês (do mês anterior ao primeiro até o mês seguinte ao último) é
calculado em três passes: ordem cronológica, ordem inversa e dentro de
``db.read_only_mode()`` + ``svc.contexto_consulta()`` (cache de consulta); os
três têm de bater com o mesmo golden. Erros de cálculo também entram no golden
(``{"__erro__": ...}``), pois mudar o erro também é mudar o comportamento.
"""
import datetime as _dt
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from contextlib import ExitStack
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import compromissos
import conciliacao as cc
import consulta_cache  # noqa: F401  (garante o módulo carregado antes do congelamento)
import database as db
import fixos_edicao
import saldo_resumo
import services as svc
import telegram_registros as reg

for _nome in ("reservas_faturas", "saldos_edicao", "pagamentos_canonicos", "fatura_conferencia",
              "faturas_competencia", "fixos_vigencia", "dashboard_metricas", "assessor_orientacao",
              "categorias", "fatura_movimentos", "compromissos_edicao"):
    try:
        __import__(_nome)
    except Exception:  # módulo opcional: o congelamento só atinge o que existe
        pass

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("migration_runner_equivalencia_onda2", ROOT / "migrations.py")
runner = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = runner
_spec.loader.exec_module(runner)
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "equivalencia_calculos_onda2.json"
REGERAR = os.environ.get("REGERAR_GOLDEN_ONDA2") == "1"

def _classe_real(cls):
    """Classe original do módulo datetime, mesmo com o relógio falso do gate (--data) ativo:
    o falso herda da real e usa metaclasse própria; a real tem metaclasse ``type``."""
    return next(c for c in cls.__mro__ if type(c) is type)


_RealDate = _classe_real(_dt.date)
_RealDateTime = _classe_real(_dt.datetime)
HOJE = _RealDate(2027, 3, 15)
AGORA = _RealDateTime(2027, 3, 15, 12, 0, 0)
ULTIMA_DATA_LANCAVEL = "2027-03-14"

MESES = [f"{2026 + (3 + k) // 12}-{(3 + k) % 12 + 1:02d}" for k in range(12)]
assert MESES[0] == "2026-04" and MESES[-1] == "2027-03", MESES
MESES_CALC = ["2026-03"] + MESES + ["2027-04"]
CARTOES = ("Nubank", "Inter")
CONTA_FOCO = "Itaú"


# --------------------------------------------------------------------------- relógio
class _MetaData(type):
    def __instancecheck__(cls, obj):
        return isinstance(obj, _RealDate)


class _MetaDataHora(type):
    def __instancecheck__(cls, obj):
        return isinstance(obj, _RealDateTime)


class FakeDate(_RealDate, metaclass=_MetaData):
    """``date`` com today() fixo; sempre devolve ``date`` real (sqlite/isinstance)."""

    def __new__(cls, *args, **kwargs):
        return _RealDate(*args, **kwargs)

    @classmethod
    def today(cls):
        return HOJE

    @classmethod
    def fromisoformat(cls, texto):
        return _RealDate.fromisoformat(texto)

    @classmethod
    def fromordinal(cls, n):
        return _RealDate.fromordinal(n)

    @classmethod
    def fromtimestamp(cls, ts):
        return _RealDate.fromtimestamp(ts)


class FakeDateTime(_RealDateTime, metaclass=_MetaDataHora):
    """``datetime`` com now()/today()/utcnow() fixos; devolve ``datetime`` real."""

    def __new__(cls, *args, **kwargs):
        return _RealDateTime(*args, **kwargs)

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return AGORA
        return AGORA.replace(tzinfo=_dt.timezone.utc).astimezone(tz)

    @classmethod
    def utcnow(cls):
        return AGORA

    @classmethod
    def today(cls):
        return AGORA

    @classmethod
    def fromisoformat(cls, texto):
        return _RealDateTime.fromisoformat(texto)

    @classmethod
    def strptime(cls, texto, fmt):
        return _RealDateTime.strptime(texto, fmt)

    @classmethod
    def combine(cls, d, t, tzinfo=None):
        return _RealDateTime.combine(d, t, tzinfo) if tzinfo else _RealDateTime.combine(d, t)

    @classmethod
    def fromtimestamp(cls, ts, tz=None):
        return _RealDateTime.fromtimestamp(ts, tz)


def _modulos_do_projeto():
    raiz = str(ROOT).lower()
    for nome, mod in list(sys.modules.items()):
        arquivo = getattr(mod, "__file__", None)
        if not arquivo or nome.startswith("tests") or nome == "__main__":
            continue
        try:
            if str(Path(arquivo).resolve()).lower().startswith(raiz) \
                    and "validacao" not in nome and ".venv" not in str(arquivo).lower():
                yield mod
        except OSError:
            continue


def congelar_relogio(stack: ExitStack):
    """Troca ``date``/``datetime`` (inclusive apelidos) de todo módulo do projeto."""
    for mod in _modulos_do_projeto():
        for atributo, valor in list(vars(mod).items()):
            # Vale tanto para as classes reais quanto para as do relógio falso do gate (--data),
            # que herdam das reais: o relógio deste teste fica por cima dele.
            if not isinstance(valor, type) or valor in (FakeDate, FakeDateTime):
                continue
            if issubclass(valor, _RealDateTime):
                stack.enter_context(patch.object(mod, atributo, FakeDateTime))
            elif issubclass(valor, _RealDate):
                stack.enter_context(patch.object(mod, atributo, FakeDate))
    # conciliacao._hoje usa datetime.now(tz) (UTC-3): já coberto pelo patch acima.
    stack.enter_context(patch.object(cc, "_hoje", lambda: HOJE))


# --------------------------------------------------------------------------- serialização
def _num(x):
    return round(float(x), 6) + 0.0


def serializar(x):
    if x is None or isinstance(x, (bool, str)):
        return x
    if isinstance(x, (int, float, Decimal)):
        return _num(x)
    if isinstance(x, _RealDateTime):
        return x.isoformat()
    if isinstance(x, _RealDate):
        return x.isoformat()
    if hasattr(x, "keys") and not isinstance(x, dict):  # sqlite3.Row e afins
        x = {k: x[k] for k in x.keys()}
    if isinstance(x, dict):
        return {str(k): serializar(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}
    if isinstance(x, (set, frozenset)):
        return sorted((serializar(v) for v in x), key=lambda v: json.dumps(v, sort_keys=True))
    if isinstance(x, (list, tuple)):
        return [serializar(v) for v in x]
    return "<%s>" % type(x).__name__


def _ou_erro(fn, *args, **kwargs):
    try:
        return serializar(fn(*args, **kwargs))
    except Exception as exc:  # o erro também é parte do comportamento
        return {"__erro__": type(exc).__name__, "mensagem": str(exc)[:200]}


def primeira_diferenca(esperado, obtido, caminho="$"):
    if isinstance(esperado, dict) and isinstance(obtido, dict):
        for k in sorted(set(esperado) | set(obtido)):
            if k not in esperado:
                return f"{caminho}.{k}: chave extra na saída ({obtido[k]!r})"
            if k not in obtido:
                return f"{caminho}.{k}: chave ausente na saída (golden {esperado[k]!r})"
            d = primeira_diferenca(esperado[k], obtido[k], f"{caminho}.{k}")
            if d:
                return d
        return None
    if isinstance(esperado, list) and isinstance(obtido, list):
        for i, (a, b) in enumerate(zip(esperado, obtido)):
            d = primeira_diferenca(a, b, f"{caminho}[{i}]")
            if d:
                return d
        if len(esperado) != len(obtido):
            return f"{caminho}: tamanho {len(obtido)} != golden {len(esperado)}"
        return None
    if isinstance(esperado, bool) or isinstance(obtido, bool) or esperado is None or obtido is None:
        return None if esperado is obtido else f"{caminho}: {obtido!r} != golden {esperado!r}"
    if isinstance(esperado, (int, float)) and isinstance(obtido, (int, float)):
        return None if _num(esperado) == _num(obtido) else f"{caminho}: {obtido!r} != golden {esperado!r}"
    return None if esperado == obtido else f"{caminho}: {obtido!r} != golden {esperado!r}"


# --------------------------------------------------------------------------- cenário
def _soma_mes(mes, n):
    k = int(mes[:4]) * 12 + int(mes[5:]) - 1 + n
    return f"{k // 12}-{k % 12 + 1:02d}"


def _tx(data, tipo, valor, categoria, descricao, conta, forma, **extra):
    if data > ULTIMA_DATA_LANCAVEL:
        return None
    dados = dict(data=data, tipo=tipo, valor=float(valor), categoria=categoria, descricao=descricao,
                 conta=conta, forma_pagamento=forma, mensagem_original="golden")
    dados.update(extra)
    return db.inserir_transacao(dados)


def _credito(data, valor, categoria, descricao, cartao):
    """Compra no crédito; corte inclusivo no dia 25 empurra para a fatura seguinte."""
    mes = data[:7]
    comp = _soma_mes(mes, 1) if int(data[8:]) >= 25 else mes
    return _tx(data, "despesa", valor, categoria, descricao, cartao, "crédito",
               data_compra=data, competencia_fatura=comp)


def _compromisso(**dados):
    base = dict(categoria="Moradia", forma_pagamento="pix", dia_vencimento=5, data_fim=None, ativo=1,
                origem="golden", observacao="", parcelas_total=None)
    base.update(dados)
    base.setdefault("conta_origem", base.get("conta_pagamento"))
    return db.inserir_compromisso(base)


def _vincular(tid, cid, mes, chave):
    row = dict(db.buscar_compromisso_por_id(cid))
    cc.vincular_existente(tid, dict(id=cid, mes=mes, assinatura=cc.assinatura_alvo(row)), chave, "golden")


def semear(cenario):
    """Popula o banco temporário (já patchado) com o movimento do cenário."""
    if cenario == 1:
        db.definir_saldo_inicial_conta_mes("2026-04", "Itaú", 5000)
        db.definir_saldo_inicial_conta_mes("2026-04", "Mercado Pago", 2000.5)
        db.definir_saldo_inicial_conta_mes("2026-04", "C6", 800)
    else:
        db.definir_saldo_inicial_conta_mes("2026-09", "Itaú", 7000)
        db.definir_saldo_inicial_conta_mes("2026-09", "Mercado Pago", 2500)
        db.definir_saldo_inicial_conta_mes("2026-09", "C6", 900)
        db.definir_saldo_inicial_conta_mes("2027-01", "Itaú", 4200.75)
        db.definir_saldo_inicial_conta_mes("2027-01", "Mercado Pago", 1800)

    # --- fixos
    aluguel = _compromisso(tipo="fixo", nome="Aluguel", conta_pagamento="Itaú", valor=1800,
                           dia_vencimento=5, data_inicio="2026-04-01")
    escola = _compromisso(tipo="fixo", nome="Escola", categoria="Educação", conta_pagamento="Mercado Pago",
                          valor=950, dia_vencimento=10, data_inicio="2026-04-01")
    _compromisso(tipo="fixo", nome="Internet", categoria="Casa", conta_pagamento="Itaú", valor=120,
                 dia_vencimento=15, data_inicio="2026-04-01")
    _compromisso(tipo="fixo", nome="Academia", categoria="Saúde", conta_pagamento="Nubank", conta_origem="Nubank",
                 forma_pagamento="crédito", valor=89.9, dia_vencimento=12, data_inicio="2026-05-01")
    # Nova condição: Escola passa a 1.050 a partir de 2026-10.
    prev = fixos_edicao.preparar(escola, "valor", "1050", "2026-10")
    fixos_edicao.salvar(prev, "golden")

    # --- receitas previstas (entrada_avulsa)
    freela = _compromisso(tipo="entrada_avulsa", nome="Freela", categoria="Receita", conta_pagamento="Itaú",
                          forma_pagamento="entrada", valor=400, dia_vencimento=25,
                          data_inicio="2026-07-25", data_fim="2026-07-25")
    _compromisso(tipo="entrada_avulsa", nome="Bônus", categoria="Receita", conta_pagamento="Itaú",
                 forma_pagamento="entrada", valor=1200, dia_vencimento=20,
                 data_inicio="2026-11-20", data_fim="2026-11-20")
    _compromisso(tipo="entrada_avulsa", nome="Reembolso", categoria="Receita", conta_pagamento="Mercado Pago",
                 forma_pagamento="entrada", valor=250, dia_vencimento=15,
                 data_inicio="2026-09-15", data_fim="2026-09-15")

    # --- movimento mensal
    for i, mes in enumerate(MESES):
        _tx(f"{mes}-05", "receita", 6000 + i * 10, "Salário", "Salário", "Itaú", "pix")
        if i % 2 == 0:
            _tx(f"{mes}-12", "receita", 350.5, "Renda extra", "Venda usada", "Mercado Pago", "pix")
        _tx(f"{mes}-08", "despesa", round(400 + 7.35 * i, 2), "Mercado", "Supermercado", "Itaú", "débito")
        _tx(f"{mes}-18", "despesa", round(120.9 + i, 2), "Lazer", "Cinema e jantar", "Mercado Pago", "pix")
        _tx(f"{mes}-20", "despesa", 55.55, "Transporte", "Combustível", "C6", "débito")
        _credito(f"{mes}-10", round(300 + i * 11.11, 2), "Compras", "Loja online", "Nubank")
        _credito(f"{mes}-25", round(210.4 + i, 2), "Mercado", "Compra no corte", "Nubank")
        _credito(f"{mes}-27", 99.99, "Lazer", "Streaming anual", "Inter")
        if i % 3 == 1:
            _credito(f"{mes}-03", round(77.7 + i, 2), "Saúde", "Farmácia", "Inter")
        # aluguel: pago em dia, exceto 2026-07 (paga depois, vinculado) e 2027-02 (não pago)
        if mes not in ("2026-07", "2027-02"):
            _tx(f"{mes}-05", "despesa", 1800, "Moradia", "Aluguel", "Itaú", "pix")
        # escola: valor novo a partir de 2026-10; 2026-08 paga depois (vinculado); sem pagar 2026-12 e 2027-02
        valor_escola = 950 if mes < "2026-10" else 1050
        if mes not in ("2026-08", "2026-12", "2027-02"):
            _tx(f"{mes}-10", "despesa", valor_escola, "Educação", "Escola", "Mercado Pago", "pix")

    # --- parcelados
    def parcelado(inicio, cartao, n, total, desc):
        parcelas = []
        for p in range(1, n + 1):
            comp = _soma_mes(inicio[:7], p - 1)
            parcelas.append(dict(
                data=inicio, tipo="despesa", valor=round(total / n, 2), categoria="Casa", descricao=desc,
                conta=cartao, forma_pagamento="crédito", parcela_atual=p, parcelas_total=n,
                valor_total_parcelamento=total, data_compra=inicio, competencia_fatura=comp,
                mensagem_original="golden"))
        db.inserir_parcelamento_atomico(parcelas)

    parcelado("2026-06-10", "Nubank", 6, 599.94, "Notebook 6x")
    parcelado("2027-01-20", "Inter", 3, 450.0, "Cadeira 3x")

    # --- conciliações: despesa paga em mês posterior; receita
    t_aluguel = _tx("2026-08-02", "despesa", 1800, "Moradia", "Aluguel", "Itaú", "pix")
    _vincular(t_aluguel, aluguel, "2026-07", "golden-vinc-aluguel")
    t_escola = _tx("2026-09-02", "despesa", 950, "Educação", "Escola", "Mercado Pago", "pix")
    _vincular(t_escola, escola, "2026-08", "golden-vinc-escola")
    t_freela = _tx("2026-08-03", "receita", 400, "Receita", "Freela", "Itaú", "pix")
    _vincular(t_freela, freela, "2026-07", "golden-vinc-freela")
    _tx("2026-09-16", "receita", 250, "Receita", "Reembolso", "Mercado Pago", "pix")  # sem vínculo

    # --- transferências entre contas
    db.inserir_transferencia_caixa(dict(data="2026-08-14", valor=800, conta_origem="Itaú",
                                        conta_destino="Mercado Pago", descricao="Reforço", mensagem_original="golden"))
    db.inserir_transferencia_caixa(dict(data="2027-01-09", valor=333.33, conta_origem="Mercado Pago",
                                        conta_destino="C6", descricao="Reserva", mensagem_original="golden"))

    # --- saldo inicial levado à frente em mês herdado (cenário 2)
    if cenario == 2:
        cmd = svc.parsear_comando_saldo_inicial("saldo inicial 2026-11 Itaú 3500")
        assert cmd is not None
        svc.definir_saldo_inicial_formatado(*cmd)

    # --- pagamentos de fatura: no mês posterior ao da competência (e alguns no mesmo mês)
    n = 0
    for cartao in CARTOES:
        for mes in MESES[:-1]:
            if cartao == "Inter" and mes not in ("2026-05", "2026-06", "2026-08", "2026-12"):
                continue  # as demais ficam em aberto
            if cartao == "Nubank" and mes in ("2027-01", "2027-02"):
                continue
            if cartao == "Nubank" and mes == "2026-11":
                modo, frac = "parcial", 0.5
            else:
                modo, frac = "total", 1.0
            data = f"{mes}-28" if (cartao == "Inter" and mes == "2026-06") else f"{_soma_mes(mes, 1)}-10"
            if data > ULTIMA_DATA_LANCAVEL:
                continue
            saldo = round(float(svc.calcular_resumo_fatura(mes, cartao).get("saldo_restante") or 0), 2)
            if saldo <= 0.005:
                continue
            valor = round(saldo * frac, 2)
            n += 1
            reg.confirmar_pagamento_fatura(
                dict(ano_mes=mes, conta_cartao=cartao, conta_origem="Itaú" if n % 2 else "C6", modo=modo,
                     valor=valor, saldo_esperado=saldo, data_movimento=data),
                f"golden-pgto-{n}", "golden")


# --------------------------------------------------------------------------- bateria
def medir_mes(mes):
    out = {}
    bruto = {}

    def _metricas():
        bruto["m"] = svc.obter_metricas_resultado_mes(mes)
        return bruto["m"]

    out["metricas"] = _ou_erro(_metricas)
    out["caixa"] = _ou_erro(svc.calcular_caixa_por_conta_mes, mes)
    out["saldo_mensal"] = _ou_erro(svc.calcular_saldo_mensal, mes)
    out["saldo_mensal_conta"] = _ou_erro(svc.calcular_saldo_mensal, mes, CONTA_FOCO)
    out["checklist"] = _ou_erro(svc.montar_itens_checklist_mes, mes)
    out["checklist_todos"] = _ou_erro(svc.montar_itens_checklist_mes, mes, "todos")
    for cartao in CARTOES:
        out[f"fatura_unificada_{cartao}"] = _ou_erro(compromissos.calcular_fatura_unificada, mes, cartao)
    # resumir_saldo recebe as métricas cruas (já serializadas acima, então pode consumir o objeto).
    out["resumir_saldo"] = _ou_erro(saldo_resumo.resumir_saldo, bruto["m"]) if "m" in bruto \
        else {"__erro__": "sem_metricas"}
    return out


def bateria(meses, somente_leitura=False):
    """Mede ``meses`` na ordem dada; com ``somente_leitura`` usa o cache de consulta."""
    resultado = {}
    with ExitStack() as st:
        if somente_leitura:
            st.enter_context(db.read_only_mode())
            st.enter_context(svc.contexto_consulta())
        for mes in meses:
            resultado[mes] = medir_mes(mes)
    return {m: resultado[m] for m in sorted(resultado)}


# O cálculo sem cache é caro no código original (a herança recalcula a cadeia
# inteira); por isso o passe sem cache cobre só alguns meses.
# Na geração do golden (código original) a conferência sem cache é mais ampla.
MESES_SEM_CACHE = ["2026-06", "2026-10", "2027-02", "2027-04"] if REGERAR else ["2026-10", "2027-04"]

def contar_chamadas(resultado):
    return sum(len(v) for v in resultado.values())


def _montar(stack, cenario):
    tmp = tempfile.TemporaryDirectory()
    stack.callback(tmp.cleanup)
    path = Path(tmp.name) / "financeiro.db"
    mods = {db, svc, compromissos, cc}
    for mod in _modulos_do_projeto():
        if hasattr(mod, "DB_PATH") and mod.__name__ not in {"migrations"}:
            mods.add(mod)
    for mod in mods:
        if hasattr(mod, "DB_PATH"):
            stack.enter_context(patch.object(mod, "DB_PATH", path))
    congelar_relogio(stack)
    db.init_db()
    runner.apply_migrations(path, ROOT / "migrations", Path(tmp.name) / "mig_backups",
                            executed_by="equivalencia_onda2")
    semear(cenario)


_GERADO = {}


class EquivalenciaCalculosOnda2(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        if REGERAR and len(_GERADO) == 2:
            FIXTURE.parent.mkdir(parents=True, exist_ok=True)
            FIXTURE.write_text(json.dumps(_GERADO, sort_keys=True, indent=1, ensure_ascii=False) + "\n",
                               encoding="utf-8")

    def _rodar(self, cenario):
        chave = f"cenario{cenario}"
        with ExitStack() as st:
            _montar(st, cenario)
            cache_direta = bateria(MESES_CALC, somente_leitura=True)
            cache_inversa = bateria(list(reversed(MESES_CALC)), somente_leitura=True)
            sem_cache = bateria(MESES_SEM_CACHE)
        self.assertEqual(14, len(cache_direta))
        self.assertEqual(contar_chamadas(cache_direta), 14 * 9)
        if REGERAR:
            # o próprio golden não pode depender da ordem nem do cache
            sub = {m: cache_direta[m] for m in MESES_SEM_CACHE}
            for nome, obtido, base in (("cache_inversa", cache_inversa, cache_direta), ("sem_cache", sem_cache, sub)):
                d = primeira_diferenca(base, obtido, chave)
                self.assertIsNone(d, f"golden instável em {nome}: {d}")
            _GERADO[chave] = cache_direta
            return
        golden = json.loads(FIXTURE.read_text(encoding="utf-8"))[chave]
        golden_sub = {m: golden[m] for m in MESES_SEM_CACHE}
        for nome, obtido, ref in (("cache_direta", cache_direta, golden), ("cache_inversa", cache_inversa, golden),
                                  ("sem_cache", sem_cache, golden_sub)):
            d = primeira_diferenca(ref, json.loads(json.dumps(obtido)), f"{chave}[{nome}]")
            self.assertIsNone(d, d)
    def test_cenario1_base_so_no_primeiro_mes(self):
        self._rodar(1)

    def test_cenario2_bases_no_meio_e_saldo_levado_a_frente(self):
        self._rodar(2)

    def test_relogio_congelado_e_independente_do_dia_real(self):
        with ExitStack() as st:
            congelar_relogio(st)
            self.assertEqual(HOJE, svc.date.today())
            self.assertEqual(HOJE, compromissos.date.today())
            self.assertEqual(HOJE, cc._hoje())
            self.assertTrue(isinstance(_RealDate(2026, 1, 1), svc.date))
            self.assertEqual(AGORA, db.datetime.now())


if __name__ == "__main__":
    unittest.main()
