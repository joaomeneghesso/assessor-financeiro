"""Gera o mapa de rotas do assessor a partir de docs/mapa/dados/*.json.

Saídas (só estrutura do código, nenhum dado financeiro):
- docs/mapa/mapa.html: grafo interativo autocontido (abre direto no navegador);
- docs/mapa/vault/: uma nota .md por nó com [[links]] (abra a pasta no Obsidian).

Uso: .venv\\Scripts\\python.exe tools\\gerar_mapa.py
"""
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DADOS = BASE / "docs" / "mapa" / "dados"
SAIDA = BASE / "docs" / "mapa"

CORES = {
    "command": "#4f9cf9", "text_trigger": "#5fd3a0", "callback": "#f2c14e", "button": "#f08a4b",
    "screen": "#b58cf2", "action": "#e56b9a", "handler": "#8ea0b5", "state": "#e5534b",
    "service": "#4cc2c4", "route": "#9bd45f", "job": "#c9b037", "security_gate": "#ff7a7a",
    "module": "#7a8699", "command_alias": "#7fd6c2", "service_call": "#4cc2c4",
}


def carregar():
    nos, arestas = {}, []
    for arq in sorted(DADOS.glob("*.json")):
        d = json.loads(arq.read_text(encoding="utf-8"))
        for n in d.get("nodes", []):
            atual = nos.setdefault(n["id"], {"id": n["id"], "fontes": []})
            for k in ("type", "label", "file", "line", "desc"):
                if n.get(k) and not atual.get(k):
                    atual[k] = n[k]
            atual["fontes"].append(arq.stem)
        for e in d.get("edges", []):
            arestas.append((e["from"], e["to"], e.get("kind", ""), e.get("label", "")))
    # arestas para nós inexistentes viram nós "externos" (mostra pontas soltas)
    for a, b, _, _ in arestas:
        for i in (a, b):
            nos.setdefault(i, {"id": i, "type": "indefinido", "label": i, "fontes": ["(solto)"]})
    vistos, unicas = set(), []
    for e in arestas:
        if e not in vistos:
            vistos.add(e)
            unicas.append(e)
    return nos, unicas


def nome_arquivo(i):
    base = re.sub(r"[^\w.\-]+", "_", i, flags=re.UNICODE).strip("_")[:80] or "no"
    # sufixo estável evita colisão entre ids que só diferem por símbolos
    return f"{base}-{hashlib.md5(i.encode('utf-8')).hexdigest()[:5]}"


def gerar_vault(nos, arestas):
    vault = SAIDA / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    for velho in vault.glob("*.md"):
        velho.unlink()
    saidas, entradas = defaultdict(list), defaultdict(list)
    for a, b, k, l in arestas:
        saidas[a].append((b, k, l))
        entradas[b].append((a, k, l))
    for i, n in nos.items():
        linhas = [f"---\ntipo: {n.get('type', 'indefinido')}\narquivo: {n.get('file', '')}\nlinha: {n.get('line', '')}\n---",
                  f"# {n.get('label', i)}", "", n.get("desc", ""), "", f"`{i}`"]
        if saidas[i]:
            linhas += ["", "## Vai para"]
            linhas += [f"- ({k}) [[{nome_arquivo(b)}|{nos[b].get('label', b)}]] {l}" for b, k, l in saidas[i]]
        if entradas[i]:
            linhas += ["", "## Vem de"]
            linhas += [f"- ({k}) [[{nome_arquivo(a)}|{nos[a].get('label', a)}]] {l}" for a, k, l in entradas[i]]
        (vault / f"{nome_arquivo(i)}.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")


MODELO = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Mapa do Assessor</title>
<style>
:root{--bg:#1e2128;--fg:#d6dbe3;--mut:#8a93a2;--pn:#262a33}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px system-ui,sans-serif;display:flex;height:100vh;overflow:hidden}
#lado{width:300px;background:var(--pn);padding:12px;overflow:auto;border-right:1px solid #333}
#lado h1{font-size:15px;margin:0 0 8px}#q{width:100%;padding:6px;border-radius:6px;border:1px solid #444;background:#1b1e25;color:var(--fg)}
.leg{display:flex;align-items:center;gap:6px;margin:3px 0;cursor:pointer;font-size:12px}.leg i{width:10px;height:10px;border-radius:50%;display:inline-block}
.leg.off{opacity:.35}#info{margin-top:12px;font-size:12px;line-height:1.5;word-break:break-word}#info b{color:#fff}
#c{flex:1;display:block}small{color:var(--mut)}a{color:#7fb7ff;cursor:pointer}
</style></head><body><div id="lado"><h1>Mapa do Assessor</h1><small id="cont"></small>
<input id="q" placeholder="Buscar nó (ex.: menu, quanto vou pagar, state:)"><div id="legs" style="margin-top:10px"></div>
<div id="info"><small>Clique num nó para ver de onde vem e para onde vai. Arraste para mover; role para dar zoom.</small></div></div>
<canvas id="c"></canvas>
<script>
const NOS=__NOS__,ARE=__ARE__,COR=__COR__;
const cv=document.getElementById('c'),cx=cv.getContext('2d');let W,H;
function rs(){W=cv.width=cv.clientWidth*devicePixelRatio;H=cv.height=cv.clientHeight*devicePixelRatio}addEventListener('resize',rs);rs();
const idx={};NOS.forEach((n,i)=>{idx[n.id]=i;n.x=(Math.random()-.5)*900;n.y=(Math.random()-.5)*900;n.vx=n.vy=0;n.deg=0});
const E=ARE.map(e=>({a:idx[e[0]],b:idx[e[1]],k:e[2],l:e[3]}));E.forEach(e=>{NOS[e.a].deg++;NOS[e.b].deg++});
const viz={};NOS.forEach(n=>viz[n.t]=true);
let cam={x:0,y:0,z:.7},sel=-1,hov=-1,drag=-1,pan=false,busca='',ticks=0;
const rad=n=>3+Math.min(10,Math.sqrt(n.deg)*1.6);
function passo(){const N=NOS.length,cel={},S=60;
 NOS.forEach((n,i)=>{const k=Math.floor(n.x/S)+','+Math.floor(n.y/S);(cel[k]=cel[k]||[]).push(i)});
 NOS.forEach((n,i)=>{const cxx=Math.floor(n.x/S),cyy=Math.floor(n.y/S);
  for(let dx=-2;dx<=2;dx++)for(let dy=-2;dy<=2;dy++){const L=cel[(cxx+dx)+','+(cyy+dy)];if(!L)continue;
   for(const j of L){if(j<=i)continue;const m=NOS[j];let ddx=n.x-m.x,ddy=n.y-m.y,d2=ddx*ddx+ddy*ddy+.01;if(d2>20000)continue;
    const f=900/d2,d=Math.sqrt(d2);ddx/=d;ddy/=d;n.vx+=ddx*f;n.vy+=ddy*f;m.vx-=ddx*f;m.vy-=ddy*f}}});
 E.forEach(e=>{const a=NOS[e.a],b=NOS[e.b];let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,f=(d-55)*.012;dx/=d;dy/=d;a.vx+=dx*f;a.vy+=dy*f;b.vx-=dx*f;b.vy-=dy*f});
 NOS.forEach(n=>{n.vx-=n.x*.0009;n.vy-=n.y*.0009;if(n.i!==drag){n.x+=n.vx*.6;n.y+=n.vy*.6}n.vx*=.8;n.vy*=.8})}
NOS.forEach((n,i)=>n.i=i);
const ok=n=>viz[n.t]&&(!busca||(n.id+' '+n.l).toLowerCase().includes(busca));
const viz1=n=>viz[n.t];
function desenha(){cx.setTransform(1,0,0,1,0,0);cx.clearRect(0,0,W,H);cx.translate(W/2+cam.x*devicePixelRatio,H/2+cam.y*devicePixelRatio);const z=cam.z*devicePixelRatio;cx.scale(z,z);
 const foco=sel>=0?new Set([sel,...E.filter(e=>e.a===sel||e.b===sel).flatMap(e=>[e.a,e.b])]):null;
 cx.lineWidth=.6/cam.z;E.forEach(e=>{const a=NOS[e.a],b=NOS[e.b];if(!viz1(a)||!viz1(b))return;
  const on=foco&&(e.a===sel||e.b===sel);cx.strokeStyle=on?'#ffffffcc':(foco?'#ffffff10':'#ffffff26');cx.lineWidth=(on?1.6:.6)/cam.z;
  cx.beginPath();cx.moveTo(a.x,a.y);cx.lineTo(b.x,b.y);cx.stroke()});
 NOS.forEach((n,i)=>{if(!viz1(n))return;const hit=ok(n),r=rad(n);cx.globalAlpha=(foco&&!foco.has(i))||(busca&&!hit)?.15:1;
  cx.fillStyle=COR[n.t]||'#999';cx.beginPath();cx.arc(n.x,n.y,r,0,7);cx.fill();
  if(i===sel||i===hov||(busca&&hit)||(cam.z>1.3&&r>5)||(foco&&foco.has(i))){cx.fillStyle='#fff';cx.font=(11/cam.z)+'px system-ui';cx.fillText(n.l,n.x+r+2,n.y+3/cam.z)}});cx.globalAlpha=1}
function loop(){if(ticks<600){passo();ticks++}desenha();requestAnimationFrame(loop)}loop();
const pos=ev=>({x:((ev.offsetX-cv.clientWidth/2-cam.x)/cam.z),y:((ev.offsetY-cv.clientHeight/2-cam.y)/cam.z)});
function acha(ev){const p=pos(ev);let best=-1,bd=1e9;NOS.forEach((n,i)=>{if(!viz1(n))return;const d=Math.hypot(n.x-p.x,n.y-p.y);if(d<rad(n)+4/cam.z&&d<bd){bd=d;best=i}});return best}
cv.addEventListener('mousedown',ev=>{const i=acha(ev);if(i>=0){drag=i;sel=i;ticks=Math.min(ticks,500);mostra(i)}else{pan=true;sel=-1}});
addEventListener('mouseup',()=>{drag=-1;pan=false});
cv.addEventListener('mousemove',ev=>{if(drag>=0){const p=pos(ev);NOS[drag].x=p.x;NOS[drag].y=p.y}else if(pan){cam.x+=ev.movementX;cam.y+=ev.movementY}else hov=acha(ev)});
cv.addEventListener('wheel',ev=>{ev.preventDefault();cam.z=Math.max(.15,Math.min(5,cam.z*(ev.deltaY<0?1.12:.89)))},{passive:false});
function mostra(i){const n=NOS[i],s=E.filter(e=>e.a===i),en=E.filter(e=>e.b===i);
 const li=(L,c)=>L.map(e=>`<div>• <a onclick="ir(${e[c]})">${NOS[e[c]].l}</a> <small>${e.k||''} ${e.l||''}</small></div>`).join('')||'<small>nenhum</small>';
 document.getElementById('info').innerHTML=`<b>${n.l}</b><br><small>${n.t} · ${n.f||''}${n.n?':'+n.n:''}</small><br>${n.d||''}<br><code>${n.id}</code><h4>Vai para (${s.length})</h4>${li(s,'b')}<h4>Vem de (${en.length})</h4>${li(en,'a')}`}
window.ir=i=>{sel=i;mostra(i);cam.x=-NOS[i].x*cam.z;cam.y=-NOS[i].y*cam.z};
document.getElementById('q').oninput=e=>busca=e.target.value.toLowerCase().trim();
const tipos=[...new Set(NOS.map(n=>n.t))].sort(),lg=document.getElementById('legs');
tipos.forEach(t=>{const d=document.createElement('div');d.className='leg';d.innerHTML=`<i style="background:${COR[t]||'#999'}"></i>${t} <small>(${NOS.filter(n=>n.t===t).length})</small>`;
 d.onclick=()=>{viz[t]=!viz[t];d.classList.toggle('off',!viz[t])};lg.appendChild(d)});
document.getElementById('cont').textContent=NOS.length+' nós · '+E.length+' ligações';
</script></body></html>"""


def gerar_html(nos, arestas):
    lista = [{"id": n["id"], "l": n.get("label", n["id"]), "t": n.get("type", "indefinido"),
              "f": n.get("file", ""), "n": n.get("line", ""), "d": n.get("desc", "")} for n in nos.values()]
    cores = {**CORES, "indefinido": "#666"}
    corpo = (MODELO.replace("__NOS__", json.dumps(lista, ensure_ascii=False))
             .replace("__ARE__", json.dumps([list(a) for a in arestas], ensure_ascii=False))
             .replace("__COR__", json.dumps(cores)))
    (SAIDA / "mapa.html").write_text(corpo, encoding="utf-8")


def resumo(nos, arestas):
    por_tipo = defaultdict(int)
    for n in nos.values():
        por_tipo[n.get("type", "indefinido")] += 1
    soltos = [i for i, n in nos.items() if n.get("type") == "indefinido"]
    grau = defaultdict(int)
    for a, b, _, _ in arestas:
        grau[a] += 1
        grau[b] += 1
    isolados = [i for i in nos if grau[i] == 0]
    return por_tipo, soltos, isolados


if __name__ == "__main__":
    nos, arestas = carregar()
    gerar_html(nos, arestas)
    gerar_vault(nos, arestas)
    por_tipo, soltos, isolados = resumo(nos, arestas)
    print(f"{len(nos)} nós, {len(arestas)} ligações")
    print("por tipo:", dict(por_tipo))
    print(f"pontas soltas (referenciadas mas não definidas): {len(soltos)}")
    print(f"nós isolados (sem nenhuma ligação): {len(isolados)}")
