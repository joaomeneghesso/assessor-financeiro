"""Compara o mapa de rotas (docs/mapa/dados/*.json) com o código, por análise estática simples.

O que é extraído do código (AST, sem importar nada):

- ``act:<kind>``: cada ``kind == '...'`` / ``kind in {...}`` dentro de ``Experience.act``
  (telegram_experiencia.py);
- ``screen:<nome>``: cada ``def screen_<nome>`` de telegram_experiencia.py;
- ``cmd:/<nome>``: cada ``CommandHandler("<nome>", ...)`` de app.py;
- ``fn:services.<f>``: cada função de services.py chamada diretamente dentro do roteador
  ``_processar_mensagem_core`` (os destinos dos gatilhos de texto do legado).

No sentido inverso, aponta nós do mapa que não existem mais no código: ``act:``, ``cmd:``,
``screen:`` (sem ``screen_<nome>`` nem literal ``'<nome>'`` nos módulos de UX),
``fn:services.*``, ``fn:app.*`` e ``fn:ux.*`` (função/método inexistente).

Uso: python tools/verificar_mapa.py [--json]   (código de saída 0 sempre; o teste
``tests/test_mapa_rotas_atualizado.py`` decide o limite aceitável).
"""
import ast
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DADOS = BASE / "docs" / "mapa" / "dados"
MODULOS_UX = ("telegram_experiencia.py", "telegram_recursos.py", "telegram_midia.py", "fixos_interface.py",
              "telegram_design.py", "telegram_visuais.py")


def _arvore(nome):
    caminho = BASE / nome
    return ast.parse(caminho.read_text(encoding="utf-8-sig"), filename=str(caminho)) if caminho.exists() else None


def _strings(no):
    if isinstance(no, ast.Constant) and isinstance(no.value, str):
        return [no.value]
    if isinstance(no, (ast.Set, ast.Tuple, ast.List)):
        return [e.value for e in no.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    return []


def _metodo(arvore, classe, metodo):
    for c in ast.walk(arvore):
        if isinstance(c, ast.ClassDef) and c.name == classe:
            for f in c.body:
                if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name == metodo:
                    return f
    return None


def acoes_ux(arvore):
    act = _metodo(arvore, "Experience", "act")
    kinds = set()
    for no in ast.walk(act) if act else ():
        if (isinstance(no, ast.Compare) and isinstance(no.left, ast.Name) and no.left.id == "kind"
                and len(no.ops) == 1 and isinstance(no.ops[0], (ast.Eq, ast.In))):
            kinds.update(_strings(no.comparators[0]))
    return {f"act:{k}" for k in kinds}


def telas_ux(arvore):
    return {f"screen:{f.name[len('screen_'):]}" for f in ast.walk(arvore)
            if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name.startswith("screen_")}


def comandos_app(arvore):
    saida = set()
    for no in ast.walk(arvore):
        if (isinstance(no, ast.Call) and getattr(no.func, "id", getattr(no.func, "attr", None)) == "CommandHandler"
                and no.args):
            for nome in _strings(no.args[0]):
                saida.add(f"cmd:/{nome}")
    return saida


def funcoes_de_modulo(arvore):
    return {n.name for n in arvore.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def todas_funcoes(arvore):
    """Funções, métodos, classes e atributos ``self.x = ...`` (o mapa usa ``fn:`` para todos)."""
    nomes = {n.name for n in ast.walk(arvore) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    for n in ast.walk(arvore):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "self" \
                and isinstance(n.ctx, ast.Store):
            nomes.add(n.attr)
    return nomes


def acoes_em_qualquer_lugar(arvores):
    """``kind == 'x'`` ou ``action[0] == 'x'`` em qualquer função dos módulos de UX
    (ações tratadas fora de ``act``, como em ``dispatch_callback``)."""
    kinds = set()
    for arv in arvores:
        for no in ast.walk(arv):
            if not (isinstance(no, ast.Compare) and len(no.ops) == 1 and isinstance(no.ops[0], (ast.Eq, ast.In))):
                continue
            esq = no.left
            eh_kind = isinstance(esq, ast.Name) and esq.id in ("kind", "acao", "tipo_acao")
            eh_action0 = (isinstance(esq, ast.Subscript) and isinstance(esq.value, ast.Name)
                          and esq.value.id in ("action", "acao") and isinstance(esq.slice, ast.Constant)
                          and esq.slice.value == 0)
            if eh_kind or eh_action0:
                kinds.update(_strings(no.comparators[0]))
    return {f"act:{k}" for k in kinds}


def destinos_roteador(arvore):
    nomes = funcoes_de_modulo(arvore)
    core = next((n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name == "_processar_mensagem_core"), None)
    chamadas = set()
    for no in ast.walk(core) if core else ():
        if (isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id in nomes
                and not no.func.id.startswith("_")):
            chamadas.add(f"fn:services.{no.func.id}")
    return chamadas


def literais(arvores):
    saida = set()
    for arv in arvores:
        for no in ast.walk(arv):
            if isinstance(no, ast.Constant) and isinstance(no.value, str):
                saida.add(no.value)
    return saida


def carregar_mapa(dados=DADOS):
    ids = set()
    for arq in sorted(Path(dados).glob("*.json")):
        d = json.loads(arq.read_text(encoding="utf-8"))
        ids.update(n["id"] for n in d.get("nodes", []))
        for e in d.get("edges", []):
            ids.update((e["from"], e["to"]))
    return ids


def verificar(dados=DADOS):
    ux = _arvore("telegram_experiencia.py")
    app = _arvore("app.py")
    svc = _arvore("services.py")
    mapa = carregar_mapa(dados)
    codigo = {
        "acoes": acoes_ux(ux),
        "telas": telas_ux(ux),
        "comandos": comandos_app(app),
        "roteador": destinos_roteador(svc),
    }
    faltam_no_mapa = {cat: sorted(ids - mapa) for cat, ids in codigo.items()}

    arvores_ux = [a for a in (_arvore(m) for m in MODULOS_UX) if a is not None]
    nomes_ux = literais(arvores_ux) | {t.split(":", 1)[1] for t in codigo["telas"]}
    funcs_svc, funcs_app, funcs_ux = todas_funcoes(svc), todas_funcoes(app), set().union(*(todas_funcoes(a) for a in arvores_ux))
    acoes_existentes = codigo["acoes"] | acoes_em_qualquer_lugar(arvores_ux + [app])
    sobram = {"acoes": [], "telas": [], "comandos": [], "funcoes": []}
    for i in sorted(mapa):
        if i.startswith("act:") and i not in acoes_existentes and not i.endswith("*"):
            sobram["acoes"].append(i)
        elif i.startswith("screen:") and i.split(":", 1)[1] not in nomes_ux:
            sobram["telas"].append(i)
        elif i.startswith("cmd:/") and i not in codigo["comandos"]:
            sobram["comandos"].append(i)
        elif i.startswith("fn:services.") and i.split(".", 1)[1] not in funcs_svc:
            sobram["funcoes"].append(i)
        elif i.startswith("fn:app.") and i.split(".", 1)[1] not in funcs_app:
            sobram["funcoes"].append(i)
        elif i.startswith("fn:ux.") and i.split(".", 1)[1] not in funcs_ux:
            sobram["funcoes"].append(i)
    total = sum(map(len, faltam_no_mapa.values())) + sum(map(len, sobram.values()))
    return {"faltam_no_mapa": faltam_no_mapa, "sobram_no_mapa": sobram, "defasagem": total,
            "contagem_codigo": {k: len(v) for k, v in codigo.items()}}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    r = verificar()
    if "--json" in argv:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    print(f"Defasagem total: {r['defasagem']} itens  (no código: {r['contagem_codigo']})")
    for titulo, grupo in (("No código e FALTANDO no mapa", r["faltam_no_mapa"]),
                          ("No mapa e INEXISTENTE no código", r["sobram_no_mapa"])):
        print(f"\n{titulo}:")
        for cat, ids in grupo.items():
            print(f"  {cat} ({len(ids)}): {', '.join(ids) if ids else '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
