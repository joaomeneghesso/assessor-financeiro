"""Linha de base da arquitetura (Onda 3, etapa 1): mede e TRAVA para não piorar.

Mede, só por AST (sem importar nada do projeto), os módulos ``*.py`` da raiz
(produção; ``test_*.py`` ficam de fora):

- linhas dos 5 maiores módulos;
- número de funções/métodos com mais de 100 linhas;
- ciclos de import entre módulos do projeto (imports tardios incluídos):
  módulos dentro de componentes cíclicos e arestas dentro deles;
- módulos da camada de dados (``database.py``, ``migrations.py``) que importam
  regra de negócio (qualquer módulo do projeto fora de ``config``/``relogio``);
- SQL fora de ``database.py`` (chamadas ``execute*`` cujo texto tem
  SELECT/INSERT/UPDATE/DELETE), por módulo;
- ``date.today()``/``datetime.now()``/``datetime.today()``/``datetime.utcnow()``
  fora de ``relogio.py``, por módulo;
- leituras de ``os.environ``/``os.getenv`` fora de ``config.py``, por módulo.

O teste falha se algum número AUMENTAR em relação a ``LIMITES`` e aceita que
diminua. Módulo novo que não está nos dicionários tem limite 0.

Linha de base medida em 12/11/2026 (commit 6fb2990 + Onda 3 etapa 1).
AO REDUZIR, BAIXE O LIMITE (rode este arquivo direto para ver os números:
``python tests/test_arquitetura_linha_de_base.py``).
"""
import ast
import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MAIORES = ("services.py", "app.py", "telegram_experiencia.py", "compromissos.py", "database.py")
CAMADA_DADOS = ("database", "migrations")
PERMITIDOS_NA_CAMADA_DADOS = {"config", "relogio"}
MODULO_RELOGIO = "relogio"
MODULO_CONFIG = "config"
GERADOS_PELO_GATE = {"release_harness"}  # escrito na raiz da cópia do gate

# Limites (data: 12/11/2026). Ao reduzir, baixe o limite.
LIMITES = {
    "ambiente_fora_de_config": {},
    "arestas_em_ciclo": 33,
    "camada_dados_importa_regra": {
        "database": 5
    },
    "funcoes_mais_de_100_linhas": 36,
    "linhas": {
        "app.py": 5537,
        "compromissos.py": 2175,
        "database.py": 1961,
        "services.py": 11767,
        "telegram_experiencia.py": 5546
    },
    "modulos_em_ciclo": 14,
    "relogio_fora_de_relogio": {
        "ajustar_fatura_itau": 2,
        "app": 1,
        "assessor_orientacao": 1,
        "categorias_pessoais": 1,
        "limitador_persistente": 1,
        "migrations": 4,
        "operacao_bot": 1,
        "parser_financeiro": 1,
        "preparar_seguranca_v40": 1,
        "registro_logs": 1,
        "security": 2,
        "telegram_alertas": 2,
        "telegram_recursos": 1
    },
    "sql_fora_database": {
        "ajustar_fatura_itau": 11,
        "assessor_orientacao": 7,
        "conciliacao": 9,
        "contas_inativas": 1,
        "fatura_conferencia": 12,
        "fixos_edicao": 4,
        "fixos_vigencia": 2,
        "migrations": 5,
        "saldos_edicao": 8,
        "services": 30,
        "sugestoes_lancamento": 3,
        "telegram_alertas": 3,
        "telegram_experiencia": 5,
        "telegram_registros": 25
    }
}

_SQL = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)
_EXECUTE = {"execute", "executemany", "executescript"}
_RELOGIO_CHAMADAS = {("date", "today"), ("datetime", "now"), ("datetime", "today"), ("datetime", "utcnow")}


def modulos_do_projeto():
    return {p.stem: p for p in sorted(RAIZ.glob("*.py")) if not p.name.startswith("test_") and p.stem not in GERADOS_PELO_GATE}


def _arvore(caminho):
    texto = caminho.read_text(encoding="utf-8-sig")
    return texto, ast.parse(texto, filename=str(caminho))


def _imports(arvore, nomes):
    alvos = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for a in no.names:
                raiz = a.name.split(".")[0]
                if raiz in nomes:
                    alvos.add(raiz)
        elif isinstance(no, ast.ImportFrom) and not no.level and no.module:
            raiz = no.module.split(".")[0]
            if raiz in nomes:
                alvos.add(raiz)
    return alvos


def _componentes_ciclicos(grafo):
    """Tarjan: componentes fortemente conexos com mais de um módulo."""
    indice, baixo, pilha, na_pilha, saida = {}, {}, [], set(), []
    contador = [0]
    sys.setrecursionlimit(max(10000, sys.getrecursionlimit()))

    def visitar(v):
        indice[v] = baixo[v] = contador[0]
        contador[0] += 1
        pilha.append(v)
        na_pilha.add(v)
        for w in grafo.get(v, ()):
            if w not in indice:
                visitar(w)
                baixo[v] = min(baixo[v], baixo[w])
            elif w in na_pilha:
                baixo[v] = min(baixo[v], indice[w])
        if baixo[v] == indice[v]:
            comp = set()
            while True:
                w = pilha.pop()
                na_pilha.discard(w)
                comp.add(w)
                if w == v:
                    break
            if len(comp) > 1:
                saida.append(comp)

    for v in sorted(grafo):
        if v not in indice:
            visitar(v)
    return saida


def _chamada_relogio(no):
    if not (isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)):
        return False
    base = no.func.value
    nome_base = base.id if isinstance(base, ast.Name) else base.attr if isinstance(base, ast.Attribute) else None
    return (nome_base, no.func.attr) in _RELOGIO_CHAMADAS


def _leituras_ambiente(arvore):
    total = 0
    for no in ast.walk(arvore):
        if isinstance(no, ast.Attribute) and no.attr == "environ" and isinstance(no.value, ast.Name) and no.value.id == "os":
            total += 1
        elif isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) and no.func.attr == "getenv" \
                and isinstance(no.func.value, ast.Name) and no.func.value.id == "os":
            total += 1
        elif isinstance(no, ast.Subscript) and isinstance(no.ctx, (ast.Store, ast.Del)) \
                and isinstance(no.value, ast.Attribute) and no.value.attr == "environ":
            total -= 1  # escrita não é leitura (o os.environ dela já foi contado acima)
    return total


def medir():
    mods = modulos_do_projeto()
    nomes = set(mods)
    medidas = {
        "linhas": {}, "funcoes_mais_de_100_linhas": 0, "modulos_em_ciclo": 0, "arestas_em_ciclo": 0,
        "camada_dados_importa_regra": {}, "sql_fora_database": {}, "relogio_fora_de_relogio": {},
        "ambiente_fora_de_config": {},
    }
    grafo = {}
    for nome, caminho in mods.items():
        texto, arvore = _arvore(caminho)
        if caminho.name in MAIORES:
            medidas["linhas"][caminho.name] = len(texto.splitlines())
        for no in ast.walk(arvore):
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.end_lineno - no.lineno + 1 > 100:
                medidas["funcoes_mais_de_100_linhas"] += 1
        grafo[nome] = _imports(arvore, nomes) - {nome}
        if nome in CAMADA_DADOS:
            regra = sorted(grafo[nome] - PERMITIDOS_NA_CAMADA_DADOS)
            if regra:
                medidas["camada_dados_importa_regra"][nome] = len(regra)
        if nome != "database":
            sql = sum(1 for no in ast.walk(arvore)
                      if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) and no.func.attr in _EXECUTE
                      and _SQL.search(ast.get_source_segment(texto, no) or ""))
            if sql:
                medidas["sql_fora_database"][nome] = sql
        if nome != MODULO_RELOGIO:
            rel = sum(1 for no in ast.walk(arvore) if _chamada_relogio(no))
            if rel:
                medidas["relogio_fora_de_relogio"][nome] = rel
        if nome != MODULO_CONFIG:
            amb = _leituras_ambiente(arvore)
            if amb > 0:
                medidas["ambiente_fora_de_config"][nome] = amb
    for comp in _componentes_ciclicos(grafo):
        medidas["modulos_em_ciclo"] += len(comp)
        medidas["arestas_em_ciclo"] += sum(len(grafo[v] & comp) for v in comp)
    return medidas


def _excessos(medidas, limites):
    erros = []
    for chave, limite in limites.items():
        valor = medidas[chave]
        if isinstance(limite, dict):
            for item in sorted(set(valor) | set(limite)):
                atual, teto = valor.get(item, 0), limite.get(item, 0)
                if atual > teto:
                    erros.append(f"{chave}[{item}]: {atual} > limite {teto}")
        elif valor > limite:
            erros.append(f"{chave}: {valor} > limite {limite}")
    return erros


class ArquiteturaLinhaDeBaseTest(unittest.TestCase):
    def test_nao_piora_em_relacao_a_linha_de_base(self):
        erros = _excessos(medir(), LIMITES)
        self.assertEqual(erros, [], "Arquitetura piorou (se a mudança é intencional e justificada, discuta antes de subir o limite):\n" + "\n".join(erros))

    def test_medidor_enxerga_o_projeto(self):
        medidas = medir()
        self.assertEqual(set(medidas["linhas"]), set(MAIORES))
        self.assertGreater(medidas["funcoes_mais_de_100_linhas"], 0)

    def test_medidor_detecta_violacoes(self):
        arvore = ast.parse("import os\nfrom datetime import date\nx = os.getenv('A')\ny = os.environ.get('B')\nos.environ['C'] = '1'\nd = date.today()\n")
        self.assertEqual(_leituras_ambiente(arvore), 2)
        self.assertEqual(sum(1 for no in ast.walk(arvore) if _chamada_relogio(no)), 1)
        self.assertEqual(_componentes_ciclicos({"a": {"b"}, "b": {"a"}, "c": {"a"}}), [{"a", "b"}])
        self.assertEqual(_excessos({"x": 2, "d": {"m": 1}}, {"x": 1, "d": {}}), ["x: 2 > limite 1", "d[m]: 1 > limite 0"])


if __name__ == "__main__":
    import json
    print(json.dumps(medir(), ensure_ascii=False, indent=2, sort_keys=True))
