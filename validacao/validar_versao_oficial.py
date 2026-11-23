"""Gate de release: código copiado, banco temporário e rede externa bloqueada."""
import argparse,ast,json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path

HARNESS=r'''
import json,os,socket,sys,threading,unittest
from pathlib import Path
from collections import Counter
def blocked(*args,**kwargs):raise RuntimeError('Rede externa bloqueada na validacao')
original_connect=socket.socket.connect
original_pair=socket.socketpair
pair_context=threading.local()
def connect(sock,address):
    if getattr(pair_context,'active',False) and isinstance(address,tuple) and address[0] in ('127.0.0.1','::1','localhost'):return original_connect(sock,address)
    return blocked()
def pair(*args,**kwargs):
    pair_context.active=True
    try:return original_pair(*args,**kwargs)
    finally:pair_context.active=False
socket.socketpair=pair
socket.socket.connect=connect
socket.socket.connect_ex=blocked
socket.create_connection=blocked
if os.environ.get('GATE_DATA_FALSA'):
    sys.path.insert(0,str(Path.cwd()/'validacao'))
    import relogio_falso;relogio_falso.ativar_pelo_ambiente()
import database as db,services as svc,telegram_experiencia as ux
from version import VERSION
forbidden_db=Path(os.environ['ASSESSOR_TEST_FORBIDDEN_DB']).resolve()
_chave=lambda p:os.path.normcase(os.path.abspath(os.fspath(p)))
forbidden_keys={_chave(forbidden_db),_chave(os.environ['ASSESSOR_TEST_FORBIDDEN_DB'])}
original_open_connection=db._open_connection
def guarded_open_connection(read_only):
    if _chave(db.DB_PATH) in forbidden_keys:
        raise RuntimeError('Teste tentou acessar o banco oficial: '+str(forbidden_db))
    return original_open_connection(read_only)
db._open_connection=guarded_open_connection
db.DB_PATH=Path.cwd()/'data'/'fixture.db';svc.DB_PATH=db.DB_PATH;db.init_db()
actions=Counter();original_act=ux.Experience.act
def traced_act(self,key,action):
    result=original_act(self,key,action)
    actions[str(action[0])]+=1
    return result
ux.Experience.act=traced_act
loader=unittest.TestLoader();suite=unittest.TestSuite()
modules=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
suite.addTests(loader.loadTestsFromNames(modules))
result=unittest.TextTestRunner(verbosity=2).run(suite)
approved=result.wasSuccessful() and not result.skipped
report={'data_falsa':os.environ.get('GATE_DATA_FALSA'),'version':VERSION,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'approved':approved,'action_successes':dict(actions)}
Path('result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False));sys.exit(0 if approved else 1)
'''

PESOS_CONHECIDOS={
    'tests.test_saldo_ajuste_para_frente':100,'tests.test_percurso_botoes_mapa':15,'testes_v39.test_v39':12,
    'tests.test_contas_gerenciar':10,'testes_v39.test_integracoes_v39':10,'tests.test_bloco_c_ciclo_vida':8,
    'tests.test_revisao_saldo_integridade':8,
}
TIMEOUT_PADRAO=1200

def listar_modulos(stage):
    """Mesma lista que o discover do harness carregava: tests/, testes_v39/ e test_rc307_deduplicacao."""
    stage=Path(stage);modulos=[]
    for pasta in ('tests','testes_v39'):
        modulos+=[pasta+'.'+p.stem for p in sorted((stage/pasta).glob('test*.py'))]
    modulos.append('test_rc307_deduplicacao')
    return modulos

# Módulos lentos demais para um único worker: com --workers>1 viram um item por
# teste (Classe.metodo), distribuídos entre os workers.
DIVIDIR_POR_TESTE={'tests.test_saldo_ajuste_para_frente'}

def testes_do_modulo(stage,modulo):
    """Ids 'modulo.Classe.test_x' dos métodos definidos diretamente em cada classe (AST, sem importar)."""
    arq=Path(stage)/(modulo.replace('.','/')+'.py')
    tree=ast.parse(arq.read_text(encoding='utf-8-sig'))
    return [f'{modulo}.{c.name}.{f.name}' for c in tree.body if isinstance(c,ast.ClassDef)
            for f in c.body if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef)) and f.name.startswith('test')]

def dividir_pesados(stage,pesos):
    """Troca cada módulo de DIVIDIR_POR_TESTE por seus testes, repartindo o peso."""
    saida={}
    for m,p in pesos.items():
        ids=testes_do_modulo(stage,m) if m in DIVIDIR_POR_TESTE else []
        if ids:
            for t in ids:saida[t]=max(1,p/len(ids))
        else:saida[m]=p
    return saida

def pesos_modulos(stage,modulos):
    stage=Path(stage);pesos={}
    for m in modulos:
        if m in PESOS_CONHECIDOS:pesos[m]=PESOS_CONHECIDOS[m];continue
        arq=stage/(m.replace('.','/')+'.py')
        pesos[m]=1+(arq.stat().st_size//20000 if arq.exists() else 0)
    return pesos

def particionar(pesos,n):
    """Guloso: do mais pesado ao mais leve, sempre no lote de menor carga. Retorna n listas (podem ficar vazias)."""
    n=max(1,int(n));lotes=[[] for _ in range(n)];carga=[0]*n
    for m in sorted(pesos,key=lambda k:(-pesos[k],k)):
        i=min(range(n),key=lambda j:(carga[j],j));lotes[i].append(m);carga[i]+=pesos[m]
    return lotes

def agregar(resultados,returncodes):
    """Soma os resultado.json dos workers; resultado ausente conta como erro."""
    total={'version':None,'tests':0,'failures':0,'errors':0,'skipped':0,'approved':True,'action_successes':{}}
    for r,rc in zip(resultados,returncodes):
        if r is None:
            total['errors']+=1;total['approved']=False;continue
        total['version']=total['version'] or r.get('version')
        for k in ('tests','failures','errors','skipped'):total[k]+=int(r.get(k,0))
        for k,v in (r.get('action_successes') or {}).items():total['action_successes'][k]=total['action_successes'].get(k,0)+v
        if not r.get('approved') or rc!=0:total['approved']=False
    if total['skipped']:total['approved']=False
    if not resultados:total['approved']=False;total['errors']=1
    return total

def matar_arvore(proc):
    """Encerra só o processo que este gate iniciou (e seus filhos), sempre pelo PID."""
    if proc.poll() is not None:return
    if sys.platform=='win32':
        subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)
    try:proc.kill()
    except OSError:pass
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:pass

def criar_parser():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--projeto',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--saida',type=Path,required=True,help='Pasta de logs e resultado; não recebe dados pessoais')
    parser.add_argument('--timeout',type=int,default=TIMEOUT_PADRAO,help='Limite em segundos da suíte Python (padrão %(default)s)')
    parser.add_argument('--workers',type=int,default=1,help='Processos paralelos por módulo de teste (padrão 1)')
    parser.add_argument('--data',default=None,metavar='AAAA-MM-DD',help='Roda a suíte com relógio falso começando nesta data (validacao/relogio_falso.py)')
    parser.add_argument('--hora',default='10:00',metavar='HH:MM',help='Hora local inicial do relógio falso (padrão %(default)s)')
    return parser

def main(argv=None):
    parser=criar_parser()
    args=parser.parse_args(argv);source=args.projeto.resolve();output=args.saida.resolve()
    if args.workers<1:parser.error('--workers precisa ser >= 1')
    if args.timeout<1:parser.error('--timeout precisa ser >= 1')
    if args.data:
        try:time.strptime(args.data,'%Y-%m-%d');time.strptime(args.hora,'%H:%M')
        except ValueError:parser.error('--data precisa ser AAAA-MM-DD e --hora HH:MM')
    output.mkdir(parents=True,exist_ok=True)
    check=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True,timeout=60)
    (output/'dependencias.log').write_text(check.stdout+check.stderr,encoding='utf-8')
    if check.returncode:raise SystemExit('Dependências inconsistentes; consulte dependencias.log.')
    with tempfile.TemporaryDirectory(prefix='assessor_release_') as temp:
        stage=Path(temp)/'base'
        stage.mkdir()
        for p in source.glob('*.py'):
            ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p));shutil.copy2(p,stage/p.name)
        # .env.example (só nomes e padrões, sem segredos): tests/test_config_unica.py confere as variáveis lidas
        shutil.copy2(source/'.env.example',stage/'.env.example')
        ignore=shutil.ignore_patterns('__pycache__','*.pyc')
        for folder in ('tests','migrations','deploy'):shutil.copytree(source/folder,stage/folder,ignore=ignore)
        shutil.copytree(source/'validacao/testes_v39',stage/'testes_v39',ignore=ignore)
        (stage/'tests/__init__.py').touch();(stage/'validacao').mkdir()
        # mapa de rotas + verificador (tests/test_mapa_rotas_atualizado.py); só estrutura, sem dados
        shutil.copytree(source/'docs/mapa/dados',stage/'docs/mapa/dados',ignore=ignore)
        (stage/'tools').mkdir();shutil.copy2(source/'tools/verificar_mapa.py',stage/'tools/verificar_mapa.py')
        for name in ('validar_versao_oficial.py','relogio_falso.py'):
            shutil.copy2(source/'validacao'/name,stage/'validacao'/name)
        (stage/'release_harness.py').write_text(HARNESS,encoding='utf-8')
        modulos=listar_modulos(stage)
        pesos=pesos_modulos(stage,modulos)
        if args.workers>1:pesos=dividir_pesados(stage,pesos)
        lotes=[l for l in particionar(pesos,args.workers) if l]
        stages=[stage]
        for i in range(1,len(lotes)):
            d=Path(temp)/f'w{i}';shutil.copytree(stage,d);stages.append(d)
        for d,lote in zip(stages,lotes):(d/'modulos.json').write_text(json.dumps(lote),encoding='utf-8')
        env={k:v for k,v in os.environ.items() if not k.upper().startswith(('TELEGRAM','ASSESSOR','OPENAI','OLLAMA','PYTHONPATH','PYTHONHOME'))}
        env.update(PYTHON_DOTENV_DISABLED='1',PYTHONIOENCODING='utf-8',MPLBACKEND='Agg',
                   ASSESSOR_TEST_FORBIDDEN_DB=str((source/'data'/'financeiro.db').resolve()))
        env.pop('GATE_DATA_FALSA',None);env.pop('GATE_HORA_FALSA',None)
        if args.data:env.update(GATE_DATA_FALSA=args.data,GATE_HORA_FALSA=args.hora)
        t0=time.monotonic();procs=[];logs=[]
        for d in stages:
            log=(d/'regressao.log').open('w',encoding='utf-8');logs.append(log)
            wenv=dict(env,MPLCONFIGDIR=str(d/'mpl'))
            procs.append((subprocess.Popen([sys.executable,'release_harness.py','modulos.json'],cwd=d,env=wenv,stdout=log,stderr=subprocess.STDOUT),time.monotonic()))
        duracoes=[None]*len(procs);timeout=False;prazo=t0+args.timeout
        try:
            while any(d is None for d in duracoes):
                for i,(p,ini) in enumerate(procs):
                    if duracoes[i] is None and p.poll() is not None:duracoes[i]=round(time.monotonic()-ini,1)
                if all(d is not None for d in duracoes):break
                if time.monotonic()>prazo:
                    timeout=True
                    for i,(p,ini) in enumerate(procs):
                        if duracoes[i] is None:matar_arvore(p);duracoes[i]=round(time.monotonic()-ini,1)
                    break
                time.sleep(0.2)
        finally:
            for p,_ in procs:matar_arvore(p)
            for log in logs:log.close()
        duracao_python=round(time.monotonic()-t0,1)
        with (output/'regressao.log').open('w',encoding='utf-8') as saida:
            for i,d in enumerate(stages):
                saida.write(f'===== worker {i+1}/{len(stages)} ({len(lotes[i])} módulos, {duracoes[i]} s) =====\n')
                saida.write((d/'regressao.log').read_text(encoding='utf-8',errors='replace'))
                if timeout and not (d/'result.json').exists():saida.write('\n[TIMEOUT: worker interrompido pelo gate]\n')
        resultados=[json.loads((d/'result.json').read_text(encoding='utf-8')) if (d/'result.json').exists() else None for d in stages]
        result=agregar(resultados,[p.returncode for p,_ in procs])
        result['python_approved']=bool(result.get('approved')) and not timeout
        result['approved']=result['python_approved']
        result['workers']=len(stages)
        result['data_falsa']=f'{args.data} {args.hora}' if args.data else None
        result['timeout']=timeout
        result['duracao_s']={'python':duracao_python,'total':round(time.monotonic()-t0,1),'por_worker':duracoes}
        (output/'resultado.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        print(f"Duração total {result['duracao_s']['total']} s (python {duracao_python} s); por worker: "+', '.join(f'w{i+1}={d} s' for i,d in enumerate(duracoes)))
        return 0 if result['approved'] else 1

if __name__=='__main__':sys.exit(main())
