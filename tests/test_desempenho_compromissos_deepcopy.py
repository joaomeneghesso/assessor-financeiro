"""D18: fatura unificada sem ~500 mil deepcopy por toque, com resultado idêntico.

A referência é o comportamento antigo (``copy.deepcopy`` do resultado memoizado
e da lista inteira de itens-base do mês), reinstalado por monkeypatch. A saída
otimizada precisa ser estritamente igual (valores e tipos) e não compartilhar
objetos mutáveis com o cache.
"""
import copy
import importlib.util
import random
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import compromissos as comp
import consulta_cache
import database as db
import services as svc

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("migration_runner_desempenho_deepcopy", ROOT / "migrations.py")
runner = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = runner
_spec.loader.exec_module(runner)

CONTAS = ["Itaú", "Nubank", "Inter", "C6"]
CARTOES = ["Nubank", "Inter", "C6"]
MESES = ["2026-08", "2026-09", "2026-10", "2026-11"]
CATS = ["Mercado", "Transporte", "Lazer", "Saúde", "Casa", "Alimentação"]


def _referencia_itens_da_conta(ano_mes, conta_norm):
    """Comportamento anterior: copia profunda de todos os itens e filtra depois."""
    return [
        item for item in comp.obter_itens_base_pagamentos_mes(ano_mes, incluir_transacoes=True)
        if isinstance(item, dict)
        and comp.normalizar_conta_fatura(item.get("conta_pagamento") or "") == conta_norm
    ]


def _tipos(valor):
    """Árvore de tipos para garantir igualdade estrita (Decimal != float, etc.)."""
    if isinstance(valor, dict):
        return {k: _tipos(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [type(valor).__name__] + [_tipos(v) for v in valor]
    return type(valor).__name__


class DesempenhoCompromissosDeepcopy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.patches = [
            patch.object(mod, "DB_PATH", Path(cls.tmp.name) / "fixture.db") for mod in (db, svc)
        ]
        for p in cls.patches:
            p.start()
        db.init_db()
        banco = Path(cls.tmp.name) / "fixture.db"
        runner.apply_migrations(banco, ROOT / "migrations", Path(cls.tmp.name) / "mig_backups",
                                executed_by="desempenho_deepcopy")
        cls._semear()

    @classmethod
    def tearDownClass(cls):
        for p in cls.patches:
            p.stop()
        cls.tmp.cleanup()

    @classmethod
    def _semear(cls):
        rnd = random.Random(18)
        for i, conta in enumerate(CONTAS):
            db.definir_saldo_inicial_conta_mes("2026-08", conta, 1500.0 + i * 700)
        for ano, mes in [(2026, 8), (2026, 9), (2026, 10), (2026, 11)]:
            db.inserir_transacao(dict(
                data=f"{ano}-{mes:02d}-05", tipo="receita", valor=9500, categoria="Salário",
                descricao="Salário", conta="Itaú", forma_pagamento="pix", parcelas_total=1))
            ultimo = 9 if mes == 11 else 28
            for k in range(80):
                dia = rnd.randint(1, ultimo)
                forma = rnd.choice(["pix", "débito", "crédito", "crédito", "boleto"])
                conta = rnd.choice(CARTOES if forma == "crédito" else CONTAS)
                t = dict(
                    data=f"{ano}-{mes:02d}-{dia:02d}", tipo="despesa",
                    valor=round(rnd.uniform(8, 900), 2), categoria=rnd.choice(CATS),
                    descricao=f"Compra {k} no mercado {rnd.randint(1, 9)}", conta=conta,
                    forma_pagamento=forma, parcelas_total=1)
                if forma == "crédito":
                    mm, aa = (mes + 1, ano) if dia >= 25 else (mes, ano)
                    if mm > 12:
                        mm, aa = 1, aa + 1
                    t["data_compra"] = t["data"]
                    t["competencia_fatura"] = f"{aa}-{mm:02d}"
                db.inserir_transacao(t)
            if mes in (8, 9, 10):
                cartao = CARTOES[mes % 3]
                n, total = 3, 900.0
                parcelas = []
                for p in range(1, n + 1):
                    mm, aa = mes + p - 1, ano
                    if mm > 12:
                        mm, aa = mm - 12, aa + 1
                    parcelas.append(dict(
                        data=f"{ano}-{mes:02d}-10", tipo="despesa", valor=round(total / n, 2),
                        categoria="Casa", descricao=f"Notebook parcelado {mes}", conta=cartao,
                        forma_pagamento="crédito", parcela_atual=p, parcelas_total=n,
                        valor_total_parcelamento=total, data_compra=f"{ano}-{mes:02d}-10",
                        competencia_fatura=f"{aa}-{mm:02d}"))
                db.inserir_parcelamento_atomico(parcelas)
        nomes = ["Internet", "Aluguel", "Condomínio", "Netflix", "Spotify", "Academia", "Seguro",
                 "Celular", "Luz", "Água", "Gás", "Escola", "Plano de saúde", "IPTU", "Terapia",
                 "Diarista", "Cloud", "Pet shop", "Revista", "Estacionamento", "Previdência",
                 "Clube", "Yoga", "Streaming", "Telefone fixo"]
        for i, nome in enumerate(nomes):
            db.inserir_compromisso(dict(
                tipo="fixo", nome=nome, categoria=CATS[i % len(CATS)], valor=round(30 + i * 37.3, 2),
                data_inicio="2026-08-01", dia_vencimento=1 + i % 28,
                conta_pagamento=(CARTOES + ["Itaú"])[i % 4],
                forma_pagamento=["pix", "crédito", "débito", "boleto"][i % 4], ativo=1))
        for i in range(2):
            db.inserir_compromisso(dict(
                tipo="entrada_fixa", nome=f"Aluguel recebido {i}", categoria="Renda",
                valor=800.0 + i * 150, data_inicio="2026-08-01", dia_vencimento=10 + i,
                conta_pagamento="Itaú", forma_pagamento="pix", ativo=1))

    # -- util -----------------------------------------------------------------
    def _resultados(self):
        """Saldo mensal por mês + fatura unificada (cartão e geral) por cartão/mês."""
        saida = {}
        for mes in MESES:
            with consulta_cache.contexto_consulta():
                saida[("saldo", mes)] = svc.calcular_saldo_mensal(mes)
                for cartao in CARTOES:
                    saida[("fatura_cartao", mes, cartao)] = comp.calcular_fatura_unificada(
                        mes, cartao, somente_cartao=True)
                    saida[("fatura", mes, cartao)] = comp.calcular_fatura_unificada(mes, cartao)
        return saida

    def _resultados_referencia(self):
        with patch.object(comp, "_copia_rapida", lambda valor, _memo=None: copy.deepcopy(valor)), \
                patch.object(comp, "_itens_base_da_conta", _referencia_itens_da_conta):
            return self._resultados()

    # -- testes ---------------------------------------------------------------
    def test_cenario_tem_volume_e_exercita_cartoes(self):
        with db.get_connection() as conn:
            n = conn.execute("SELECT count(*) FROM transacoes").fetchone()[0]
        self.assertGreaterEqual(n, 300)
        with consulta_cache.contexto_consulta():
            fatura = comp.calcular_fatura_unificada("2026-10", "Nubank", somente_cartao=True)
        self.assertTrue(fatura["itens"])
        self.assertTrue(fatura["valor_bruto"] > 0)

    def test_equivalencia_estrita_com_referencia_deepcopy(self):
        esperado = self._resultados_referencia()
        obtido = self._resultados()
        self.assertEqual(esperado.keys(), obtido.keys())
        for chave in esperado:
            self.assertEqual(esperado[chave], obtido[chave], chave)
            self.assertEqual(repr(esperado[chave]), repr(obtido[chave]), chave)
            self.assertEqual(_tipos(esperado[chave]), _tipos(obtido[chave]), chave)

    def test_ajustar_reservas_equivalente(self):
        from reservas_faturas import ajustar_reservas
        mes = "2026-10"

        def rodar():
            with consulta_cache.contexto_consulta():
                trans = [dict(t) for t in db.buscar_transacoes_por_mes(mes)]
                itens = comp.projetar_pagamentos_mes(mes, incluir_transacoes=False)
                esperados = [i for i in itens if comp.item_eh_fatura_cartao(i)]
                return ajustar_reservas(mes, trans, esperados, [])

        with patch.object(comp, "_copia_rapida", lambda valor, _memo=None: copy.deepcopy(valor)), \
                patch.object(comp, "_itens_base_da_conta", _referencia_itens_da_conta):
            ref = rodar()
        novo = rodar()
        self.assertTrue(ref[1], "cenario deve gerar reservas de fatura")
        self.assertEqual(ref, novo)
        self.assertEqual(repr(ref), repr(novo))

    def test_resultado_nao_compartilha_objetos_mutaveis_com_o_cache(self):
        mes, cartao = "2026-10", "Nubank"
        with consulta_cache.contexto_consulta():
            primeiro = comp.calcular_fatura_unificada(mes, cartao, somente_cartao=True)
            snapshot = copy.deepcopy(primeiro)
            # muta tudo que é mutável, em profundidade
            for item in primeiro["itens"] + primeiro["movimentos"] + primeiro["itens_imediatos_ignorados"]:
                item["valor"] = -999
                item["nome"] = "MUTADO"
            primeiro["itens"].clear()
            primeiro["movimentos"].append({"x": 1})
            if primeiro["conferencia"]:
                primeiro["conferencia"]["ajuste_composicao"] = 12345
            primeiro["saldo_restante"] = 1e9
            segundo = comp.calcular_fatura_unificada(mes, cartao, somente_cartao=True)
            self.assertEqual(snapshot, segundo)
            self.assertIsNot(primeiro["itens"], segundo["itens"])
            # a mutação também não vaza para a leitura de itens-base do mesmo mês
            base = comp.obter_itens_base_pagamentos_mes(mes, incluir_transacoes=True)
            self.assertFalse(any(i.get("nome") == "MUTADO" for i in base))

    def test_itens_da_conta_nao_alteram_o_cache_de_itens_base(self):
        mes, cartao = "2026-09", "Inter"
        conta_norm = comp.normalizar_conta_fatura(cartao)
        with consulta_cache.contexto_consulta():
            base_antes = copy.deepcopy(comp.obter_itens_base_pagamentos_mes(mes, incluir_transacoes=True))
            itens = comp._itens_base_da_conta(mes, conta_norm)
            self.assertTrue(itens)
            for item in itens:
                item["valor"] = 0
                item["extra"] = [1]
            base_depois = comp.obter_itens_base_pagamentos_mes(mes, incluir_transacoes=True)
            self.assertEqual(base_antes, base_depois)

    def test_copia_rapida_equivale_a_deepcopy(self):
        from decimal import Decimal
        compartilhado = {"a": [1, 2]}
        original = {
            "d": Decimal("1.10"), "f": 1.5, "i": 2, "s": "x", "n": None, "b": True,
            "dt": date(2026, 1, 2), "l": [compartilhado, compartilhado, (1, [2])],
            "t": (Decimal("3"), {"k": [4]}), "set": {1, 2},
        }
        copia = comp._copia_rapida(original)
        self.assertEqual(original, copia)
        self.assertEqual(_tipos(original), _tipos(copia))
        self.assertIsNot(original["l"], copia["l"])
        self.assertIsNot(original["l"][0], copia["l"][0])
        self.assertIsNot(original["t"][1]["k"], copia["t"][1]["k"])
        # identidade compartilhada preservada, como no deepcopy
        self.assertIs(copia["l"][0], copia["l"][1])

    def test_numero_de_deepcopy_cai_drasticamente(self):
        contagem = {"n": 0}
        original = copy.deepcopy

        def contando(valor, *a, **k):
            contagem["n"] += 1
            return original(valor, *a, **k)

        def medir(ref):
            contagem["n"] = 0
            with patch.object(consulta_cache, "deepcopy", contando), \
                    patch.object(comp, "deepcopy", contando):
                if ref:
                    with patch.object(comp, "_copia_rapida", lambda v, _m=None: contando(v)), \
                            patch.object(comp, "_itens_base_da_conta", _referencia_itens_da_conta):
                        self._resultados()
                else:
                    self._resultados()
            return contagem["n"]

        referencia = medir(True)
        otimizado = medir(False)
        self.assertLess(otimizado, referencia)


if __name__ == "__main__":
    unittest.main()
