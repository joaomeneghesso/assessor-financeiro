"""Gera as notas de código do vault Obsidian (docs/codigo/) e a página inicial (docs/00 Início.md).

Uma nota por módulo do projeto (sem testes), com papel (docstring), quem usa, o que usa,
funções mais usadas por fora, testes que cobrem, telas/ações do mapa de rotas e documentos
que citam o arquivo. Índices por grupo. Só análise estática (``ast``): não importa o
projeto, não lê banco nem ``.env``, não usa rede nem IA.

Rodar da raiz do projeto:  python tools/gerar_vault_codigo.py
Abrir no Obsidian:          "Abrir pasta como vault" -> pasta docs/
"""
import ast
import re
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
SAIDA = DOCS / "codigo"
MODULOS_DIR = SAIDA / "modulos"
ROTAS = DOCS / "mapa" / "vault"
INICIO = DOCS / "00 Início.md"

GRUPOS = {
    "Entrada e operação": (
        "Onde o bot começa: inicialização, configuração única, relógio, trava de instância e logs.",
        ["app.py", "assessor.py", "operacao_bot.py", "telegram_execucao.py", "config.py", "relogio.py",
         "registro_logs.py", "version.py"]),
    "Telegram (telas e conversa)": (
        "Tudo que o titular vê e toca: telas, botões, registros revisáveis, alertas, consultas e mídia.",
        ["telegram_experiencia.py", "telegram_design.py", "telegram_registros.py", "telegram_alertas.py",
         "telegram_visuais.py", "telegram_recursos.py", "telegram_aprendizado.py", "telegram_streaming.py",
         "telegram_midia.py", "busca_lancamentos.py", "consultas_pagar.py", "consultas_rapidas.py",
         "fixos_interface.py", "efeito_baixa.py", "sugestoes_comando.py", "sugestoes_lancamento.py",
         "dashboard_metricas.py"]),
    "Camada de negócio e interpretação": (
        "Roteador de comandos por texto, interpretação de registros e orientação local (sem gravar sozinho).",
        ["services.py", "parser_financeiro.py", "registro_conversa.py", "assessor_ia_local.py",
         "assessor_orientacao.py", "roteamento_seguro.py", "consulta_cache.py"]),
    "Núcleo financeiro": (
        "As regras que mexem em dinheiro: compromissos e fixos, conciliação, faturas e competência, saldos e categorias.",
        ["compromissos.py", "conciliacao.py", "faturas_competencia.py", "fatura_conferencia.py",
         "reservas_faturas.py", "saldo_resumo.py", "saldos_edicao.py", "pagamentos_canonicos.py", "money.py",
         "fixos_edicao.py", "fixos_variaveis.py", "fixos_variaveis_acoes.py", "fixos_vigencia.py",
         "categorias.py", "categorias_pessoais.py", "contas_inativas.py", "ajustar_fatura_itau.py"]),
    "Dados, backup e segurança": (
        "Banco SQLite, migrations, backups (local e externo cifrado), PIN, estado protegido e limitador.",
        ["database.py", "migrations.py", "sqlite_backup.py", "backup_externo.py", "backup_externo_cli.py",
         "security.py", "estado_runtime.py", "limitador_persistente.py", "preparar_seguranca_v40.py"]),
    "Mídia e voz": (
        "Transcrição local de áudio (Whisper) em processo isolado.",
        ["transcricao_audio.py", "transcricao_audio_worker.py"]),
    "Ferramentas e validação": (
        "Scripts de apoio: gate oficial, mapa de rotas, medições, MCP somente leitura e este gerador.",
        []),  # preenchido com tools/ e validacao/
}
OUTROS = "Outros"


def slug(texto):
    return re.sub(r"[^a-z0-9]+", "-", texto.lower().translate(str.maketrans("áâãàéêíóôõúç", "aaaaeeiooouc"))).strip("-")


def ler(p):
    return p.read_text(encoding="utf-8", errors="replace")


def _sem_link(texto):
    """Docstring com [[...]] viraria link quebrado no Obsidian."""
    return texto.replace("[[", "[ [").replace("]]", "] ]")


def primeiro_paragrafo(doc, limite=400):
    if not doc:
        return ""
    doc = _sem_link(doc)
    par = doc.strip().split("\n\n")[0]
    par = " ".join(l.strip() for l in par.splitlines())
    return par if len(par) <= limite else par[:limite - 1] + "…"


def primeira_linha(doc, limite=110):
    if not doc:
        return ""
    doc = _sem_link(doc)
    l = doc.strip().splitlines()[0].strip()
    return l if len(l) <= limite else l[:limite - 1] + "…"


def fontes():
    """(nome_exibido, caminho, é_teste) de todo .py analisado."""
    out = []
    for p in sorted(RAIZ.glob("*.py")):
        out.append((p.name, p, p.name.startswith("test_")))
    for pasta in ("tools", "validacao"):
        for p in sorted((RAIZ / pasta).glob("*.py")):
            out.append((f"{pasta}/{p.name}", p, False))
    for p in sorted((RAIZ / "tests").rglob("*.py")):
        out.append((p.relative_to(RAIZ).as_posix(), p, True))
    return out


def analisar():
    arquivos = fontes()
    internos = {p.stem: nome for nome, p, teste in arquivos if "/" not in nome and not teste}
    info, importa, tardia = {}, defaultdict(set), defaultdict(set)
    usos = defaultdict(lambda: defaultdict(set))  # modulo -> simbolo -> {quem}
    testes_de = defaultdict(set)
    for nome, p, teste in arquivos:
        try:
            arvore = ast.parse(ler(p))
        except SyntaxError:
            continue
        topo = set()
        pilha = list(arvore.body)
        while pilha:
            n = pilha.pop()
            topo.add(id(n))
            if isinstance(n, (ast.If, ast.Try)):
                pilha += n.body + n.orelse + getattr(n, "finalbody", []) + [h for t in getattr(n, "handlers", []) for h in t.body]
        apelidos = {}
        for n in ast.walk(arvore):
            alvos = []
            if isinstance(n, ast.Import):
                for a in n.names:
                    base = a.name.split(".")[0]
                    if base in internos:
                        apelidos[a.asname or base] = base
                        alvos.append(base)
            elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0 and n.module.split(".")[0] in internos:
                base = n.module.split(".")[0]
                alvos.append(base)
                for a in n.names:
                    usos[internos[base]][a.name].add(nome)
            for base in alvos:
                alvo = internos[base]
                if alvo == nome:
                    continue
                if teste:
                    testes_de[alvo].add(nome)
                else:
                    importa[nome].add(alvo)
                    if id(n) not in topo:
                        tardia[nome].add(alvo)
        for n in ast.walk(arvore):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in apelidos:
                alvo = internos[apelidos[n.value.id]]
                if alvo != nome:
                    usos[alvo][n.attr].add(nome)
        if teste:
            continue
        defs = []
        for n in arvore.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defs.append(dict(nome=n.name, linha=n.lineno, tamanho=(n.end_lineno or n.lineno) - n.lineno + 1,
                                 classe=isinstance(n, ast.ClassDef), doc=primeira_linha(ast.get_docstring(n))))
        info[nome] = dict(doc=primeiro_paragrafo(ast.get_docstring(arvore)), linhas=len(ler(p).splitlines()), defs=defs)
    for alvo in info:
        importa[alvo] -= {alvo}
    return info, importa, tardia, usos, testes_de


def grupos_de(info):
    grupo = {}
    for g, (_, mods) in GRUPOS.items():
        for m in mods:
            grupo[m] = g
    for m in info:
        if m.startswith(("tools/", "validacao/")):
            grupo[m] = "Ferramentas e validação"
        grupo.setdefault(m, OUTROS)
    return grupo


def limites_linha_de_base():
    p = RAIZ / "tests" / "test_arquitetura_linha_de_base.py"
    if not p.exists():
        return {}
    return {m: int(n) for m, n in re.findall(r'"([\w]+\.py)":\s*(\d+)', ler(p))}


def notas_de_rota():
    """arquivo -> {tipo: [(nome_nota, titulo)]} a partir do frontmatter do vault de rotas."""
    out = defaultdict(lambda: defaultdict(list))
    if not ROTAS.exists():
        return out
    for p in sorted(ROTAS.glob("*.md")):
        texto = ler(p)
        tipo = re.search(r"^tipo:\s*(\S+)", texto, re.M)
        arq = re.search(r"^arquivo:\s*(\S+)", texto, re.M)
        titulo = re.search(r"^# (.+)$", texto, re.M)
        if tipo and arq:
            out[Path(arq.group(1)).name][tipo.group(1)].append((p.stem, titulo.group(1).strip() if titulo else p.stem))
    return out


def docs_que_citam(modulos):
    out = defaultdict(list)
    for p in sorted(DOCS.rglob("*.md")):
        rel = p.relative_to(DOCS)
        if rel.parts[0] in ("codigo",) or rel.parts[:2] == ("mapa", "vault") or p == INICIO:
            continue
        texto = ler(p)
        for m in modulos:
            if Path(m).name in texto:
                out[m].append(rel.with_suffix("").as_posix())
    return out


def link(m):
    return f"[[{m.replace('/', '__')}|{m}]]" if "/" in m else f"[[{m}]]"


def nota_modulo(m, d, grupo, importa, tardia, usos, testes, rotas, docs, limite):
    externos = {s: q for s, q in usos.get(m, {}).items() if any(s == x["nome"] for x in d["defs"])}
    L = ["---", "tipo: modulo", f"grupo: {grupo}", f"linhas: {d['linhas']}", f"tags: [modulo, {slug(grupo)}]", "---",
         f"# {m}", ""]
    if d["doc"]:
        L += [f"> {d['doc']}", ""]
    fun = sum(1 for x in d["defs"] if not x["classe"])
    cla = len(d["defs"]) - fun
    L.append(f"**Grupo:** [[{grupo}]] · **Linhas:** {d['linhas']} · **Funções:** {fun} · **Classes:** {cla}")
    if limite:
        L.append(f"\n> [!warning] Linha de base\n> Limite de {limite} linhas (hoje {d['linhas']}). Este arquivo não pode crescer: código novo vai em módulo próprio.")
    L.append("")
    imp = sorted(importa.get(m, ()))
    L += ["## Usa", ""]
    L += [f"- {link(x)}" + (" *(importação tardia, dentro de função)*" if x in tardia.get(m, ()) else "") for x in imp] or ["- (nenhum módulo do projeto)"]
    quem = defaultdict(set)
    for s, q in externos.items():
        for x in q:
            if not x.startswith("tests/") and not Path(x).name.startswith("test_"):
                quem[x].add(s)
    for x, alvos in importa.items():
        if m in alvos:
            quem.setdefault(x, set())
    L += ["", "## Usado por", ""]
    if quem:
        for x in sorted(quem):
            simb = sorted(quem[x])
            txt = ", ".join(f"`{s}`" for s in simb[:8]) + (f" +{len(simb) - 8}" if len(simb) > 8 else "")
            L.append(f"- {link(x)}" + (f" — {txt}" if simb else ""))
    else:
        L.append("- (ninguém no código de produção; ponto de entrada ou script)")
    if externos:
        def peso(s):
            q = externos[s]
            return (-sum(1 for x in q if not ("tests/" in x or Path(x).name.startswith("test_"))), -len(q), s)
        L += ["", "## Funções mais usadas por fora", "", "| Função | Linha | Módulos | Testes | O que faz |", "|---|---|---|---|---|"]
        por_nome = {x["nome"]: x for x in d["defs"]}
        for s in sorted(externos, key=peso)[:25]:
            q = externos[s]
            t = sum(1 for x in q if "tests/" in x or Path(x).name.startswith("test_"))
            x = por_nome[s]
            L.append(f"| `{s}` | {x['linha']} | {len(q) - t} | {t} | {x['doc'].replace('|', '/')} |")
    L += ["", "## Tudo que define", ""]
    if len(d["defs"]) > 80:
        L.append(f"{len(d['defs'])} definições; as 40 maiores:")
        L.append("")
        lista = sorted(d["defs"], key=lambda x: -x["tamanho"])[:40]
    else:
        lista = d["defs"]
    L += [f"- {'classe ' if x['classe'] else ''}`{x['nome']}` (L{x['linha']}, {x['tamanho']} linhas)" + (f" — {x['doc']}" if x["doc"] else "") for x in lista] or ["- (sem funções ou classes no topo)"]
    if testes:
        t = sorted(testes)
        L += ["", f"## Testes que usam ({len(t)})", ""] + [f"- `{x}`" for x in t[:20]] + ([f"- … +{len(t) - 20}"] if len(t) > 20 else [])
    if rotas:
        L += ["", "## No mapa de rotas", ""]
        nomes_tipo = dict(module="Módulo", screen="Telas", job="Rotinas agendadas", security_gate="Travas de segurança",
                          command="Comandos", action="Ações", state="Estado da sessão", service="Funções no mapa",
                          service_call="Chamadas de serviço", callback="Callbacks", handler="Tratadores",
                          text_trigger="Gatilhos de texto", command_alias="Apelidos de comando", button="Botões")
        for tipo, nome_tipo in nomes_tipo.items():
            itens = rotas.get(tipo, [])
            if not itens:
                continue
            mostra = itens[:30]
            L.append(f"- **{nome_tipo} ({len(itens)}):** " + ", ".join(f"[[{n}|{t}]]" for n, t in mostra) + (" …" if len(itens) > 30 else ""))
    if docs:
        L += ["", "## Documentos que citam", ""] + [f"- [[{x}]]" for x in docs[:15]] + ([f"- … +{len(docs) - 15}"] if len(docs) > 15 else [])
    L += ["", "---", "*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*"]
    return "\n".join(L) + "\n"


def nota_grupo(g, desc, membros, info, usados_por):
    L = ["---", "tipo: grupo", f"tags: [grupo, {slug(g)}]", "---", f"# {g}", "", desc, "", "[[00 Início|← Início]]", "",
         "| Módulo | Linhas | Usado por | Papel |", "|---|---|---|---|"]
    for m in sorted(membros, key=lambda x: -info[x]["linhas"]):
        papel = info[m]["doc"].split(". ")[0].replace("|", "/")[:120]
        L.append(f"| {link(m)} | {info[m]['linhas']} | {len(usados_por.get(m, ()))} | {papel} |")
    L += ["", "---", "*Gerado por `tools/gerar_vault_codigo.py`.*"]
    return "\n".join(L) + "\n"


def nota_inicio(grupos_membros, info):
    total = sum(d["linhas"] for d in info.values())
    def existe(rel):
        return (DOCS / f"{rel}.md").exists()
    chaves = [("reavaliacao/00_veredito", "Veredito da reavaliação (comece por aqui)"),
              ("BUGS_CONHECIDOS", "Bugs conhecidos"),
              ("mapa/LEIA-ME", "Mapa de rotas: como ler e manter"),
              ("pluggy/RELATORIO_FINAL", "Análise Meu Pluggy (descartada em 19/11/2026)"),
              ("DECISAO_ARQUITETURAL_MIGRATIONS", "Decisão sobre migrations")]
    L = ["---", "tipo: inicio", "tags: [inicio]", "---", "# Assessor financeiro — Início", "",
         "Mapa do projeto para navegar no Obsidian. Só estrutura de código e documentos: **nenhum dado financeiro real entra neste vault** "
         "(banco, `.env`, backups e `.runtime` ficam fora da pasta `docs/`).", "",
         "## Como navegar", "",
         "1. Escolha uma área abaixo e clique no módulo.",
         "2. Em cada módulo: **Usa** (o que ele chama), **Usado por** (quem depende dele), funções mais usadas, testes e as telas/ações do mapa de rotas.",
         "3. Visão de grafo (Ctrl+G): cores por área. Para ver só o código, filtre por `path:codigo`.",
         "4. Para ver as rotas (botões, telas, ações) abra [[mapa/LEIA-ME]] ou qualquer tela pelo módulo.", "",
         f"## Áreas do código ({len(info)} módulos, {f'{total:,}'.replace(',', '.')} linhas)", ""]
    for g, membros in grupos_membros.items():
        if membros:
            L.append(f"- [[{g}]] — {len(membros)} módulos · {GRUPOS.get(g, ('',))[0] if g in GRUPOS else 'Sem grupo definido.'}")
    L += ["", "## Documentos-chave", ""] + [f"- [[{r}|{t}]]" for r, t in chaves if existe(r)]
    L += ["", "## Manter atualizado", "",
          "- Notas de código: `python tools/gerar_vault_codigo.py` (rode depois de mudar o código).",
          "- Mapa de rotas: `python tools/gerar_mapa.py` e `tools/verificar_mapa.py` (ver [[mapa/LEIA-ME]]).",
          "- Módulo novo sem área: entra em *Outros*; ajuste `GRUPOS` no gerador.", "",
          "---", "*Gerado por `tools/gerar_vault_codigo.py`.*"]
    return "\n".join(L) + "\n"


def main():
    info, importa, tardia, usos, testes_de = analisar()
    grupo = grupos_de(info)
    limites = limites_linha_de_base()
    rotas = notas_de_rota()
    docs = docs_que_citam(list(info))
    usados_por = defaultdict(set)
    for x, alvos in importa.items():
        for a in alvos:
            usados_por[a].add(x)
    MODULOS_DIR.mkdir(parents=True, exist_ok=True)
    for velho in list(MODULOS_DIR.glob("*.md")) + list(SAIDA.glob("*.md")):
        velho.unlink()
    for m, d in info.items():
        nome = m.replace("/", "__")
        texto = nota_modulo(m, d, grupo[m], importa, tardia, usos, testes_de.get(m, ()), rotas.get(Path(m).name) if "/" not in m else None,
                            docs.get(m, []), limites.get(m))
        if "/" in m:  # tools/x.py -> nota "tools__x.py" com título e alias legíveis
            texto = texto.replace("---\n# ", f"aliases: [{m}]\n---\n# ", 1)
        (MODULOS_DIR / f"{nome}.md").write_text(texto, encoding="utf-8")
    membros = defaultdict(list)
    for m, g in grupo.items():
        membros[g].append(m)
    ordem = {g: membros.get(g, []) for g in list(GRUPOS) + [OUTROS]}
    for g, ms in ordem.items():
        if ms:
            (SAIDA / f"{g}.md").write_text(nota_grupo(g, GRUPOS.get(g, ("Módulos sem área definida.",))[0], ms, info, usados_por), encoding="utf-8")
    INICIO.write_text(nota_inicio(ordem, info), encoding="utf-8")
    print(f"{len(info)} notas de modulo, {sum(1 for ms in ordem.values() if ms)} grupos, inicio em {INICIO.relative_to(RAIZ)}")
    if ordem.get(OUTROS):
        print("sem grupo:", ", ".join(sorted(ordem[OUTROS])))


if __name__ == "__main__":
    main()
