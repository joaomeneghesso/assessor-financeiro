"""Telas e formulário de edição de fixos. Gravação somente após a prévia."""
import re
import unicodedata
from html import escape
import database as db
import fixos_edicao as fx
from compromissos import compromisso_ocorre_no_mes

_MESES=['janeiro','fevereiro','marco','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro']
_NOMES=['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']

def _sem_acento(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(text or '').lower()) if not unicodedata.combining(c)).strip()

def interpretar_mes(texto,hoje):
    """Converte texto livre de mês em 'AAAA-MM'; None se não for um mês válido.
    Mês sem ano = próxima ocorrência a partir do mês de `hoje` (inclusive)."""
    t=re.sub(r'\s+',' ',_sem_acento(texto))
    if not t:return None
    def ok(y,m):return f'{y:04d}-{m:02d}' if 1<=m<=12 and 1<=y<=9999 else None
    m=re.fullmatch(r'(\d{4})-(\d{1,2})',t)
    if m:return ok(int(m[1]),int(m[2]))
    m=re.fullmatch(r'(\d{1,2})/(\d{4}|\d{2})',t)
    if m:
        y=int(m[2]);y=y+2000 if len(m[2])==2 else y
        return ok(y,int(m[1]))
    m=re.fullmatch(r'([a-z]+)(?: de| /| -)?(?: (\d{4}|\d{2}))?',t)
    if not m or len(m[1])<3:return None
    idx=[i for i,n in enumerate(_MESES) if n.startswith(m[1])]
    if len(idx)!=1:return None
    mes=idx[0]+1
    if m[2]:
        y=int(m[2]);y=y+2000 if len(m[2])==2 else y
        return ok(y,mes)
    y=hoje.year+(1 if mes<hoje.month else 0)
    return ok(y,mes)

def _rotulo_mes(month):
    return f'{_NOMES[int(month[5:7])-1]} {month[:4]}'

_NAV=[('🏠 Início',('view','home')),('☰ Menu',('view','more'))]

def _nav(voltar):
    # Rodapé padrão: ↩ Voltar · 🏠 Início · ☰ Menu, numa mesma linha.
    return [('↩ Voltar',voltar),*_NAV]

def _dica_codigo(ident):
    return f'<i>{fx.DICA_CODIGO} #C{ident}</i>'

def _rotulo_forma(valor):
    t=str(valor or '')
    return t[:1].upper()+t[1:] if t else 'Não informado'

def _exibir(field,valor):
    if field=='forma' and valor:return _rotulo_forma(valor)
    return fx.exibir(field,valor)

def _mes_prox(engine):
    hoje=engine.date_provider();atual=hoje.strftime('%Y-%m')
    y,m=(hoje.year+1,1) if hoje.month==12 else (hoje.year,hoje.month+1)
    return atual,f'{y:04d}-{m:02d}'

def _tela_mes(engine,ident):
    atual,prox=_mes_prox(engine)
    return screen('<b>A partir de qual mês?</b>\n\nEscolha um botão ou digite o mês (ex.: 12/2026 ou dezembro). A condição anterior será preservada até o mês anterior.',
        [[(f'Este mês ({_rotulo_mes(atual)})',('fixed_month_pick',atual))],[(f'Próximo mês ({_rotulo_mes(prox)})',('fixed_month_pick',prox))],[('Cancelar',('fixed_detail',ident))],_nav(('fixed_detail',ident))])


def screen(text,rows):
    from telegram_experiencia import Screen
    return Screen(text,rows)

def detalhe(engine,key,ident):
    s=engine.session(key);s.stage=None;s.fixed_edit=None;s.draft=None
    c=fx.buscar(ident)
    active=bool(c['ativo']) and compromisso_ocorre_no_mes(c,s.month)
    fields=[f'{fx.LABELS[field]}: <b>{escape(_exibir(field,c[fx.CAMPOS[field]]))}</b>' for field in ('valor','forma','conta','vencimento','inicio','termino')]
    import fixos_variaveis_acoes as fva
    variavel=fva.eh_variavel(ident)
    if variavel:
        estimado,_=fva.previsao(c,s.month)
        fields[0]=f'Valor: <b>varia todo mês</b> · estimativa {_rotulo_mes(s.month)}: <b>≈ {fx.dinheiro(estimado)}</b>'
    return screen(f'<b>{escape(c["nome"])}</b>\n\n'+'\n'.join(fields)+f'\n\n{"Vigente" if active else "Fora da previsão"} em {_rotulo_mes(s.month)}.\n\n{_dica_codigo(ident)}',[
        [('✏️ Editar dados',('fixed_edit_fields',ident))],
        [('〰 Valor variável (ativo)' if variavel else '〰 Valor varia todo mês',('fixed_var',ident))],
        _nav(('fixed_list',0))])


def _variavel(engine,key,action):
    """Telas de "valor variável": escolher o histórico, prévia, ativar/desligar (grava só ao confirmar)."""
    import fixos_variaveis as fv
    import fixos_variaveis_acoes as fva
    s=engine.session(key);s.stage=None;s.fixed_edit=None;s.draft=None
    kind,ident=action[0],int(action[1])
    c=fx.buscar(ident)
    voltar=_nav(('fixed_detail',ident))
    motivo=fv.elegivel(c)
    if motivo:return screen(f'<b>{escape(c["nome"])}</b>\n\n{escape(motivo)}',[voltar])
    mes=engine.date_provider().strftime('%Y-%m')
    if kind=='fixed_var_off':
        return screen(f'<b>Desligar valor variável · {escape(c["nome"])}</b>\n\nA previsão volta a usar o valor cadastrado '
                      f'({fx.dinheiro(c["valor"])}) e a baixa volta a ser pelo valor fixo. Baixas já feitas não mudam.\n\nNada foi alterado ainda.',
                      [[('✅ Confirmar: desligar',('fixed_var_off_ok',ident))],voltar])
    if kind=='fixed_var_off_ok':
        fva.desativar(ident,key)
        return screen(f'✅ <b>{escape(c["nome"])}</b> voltou a ter valor fixo ({fx.dinheiro(c["valor"])}).',[voltar])
    if kind=='fixed_var_ok':
        cands=fva.candidatos(c,mes)
        if action[2]!='-' and fva.assinatura(cands)!=action[2]:
            return screen('⏳ Os lançamentos mudaram desde a prévia. Nada foi alterado. Abra de novo para conferir.',[[('〰 Abrir de novo',('fixed_var',ident))],voltar])
        historico=[] if action[2]=='-' else [t['id'] for t in cands]
        fva.ativar(ident,historico,key)
        estimado,meses=fva.previsao(c,mes)
        base=f'média de {", ".join(_rotulo_mes(m) for m in meses)}' if meses else 'valor cadastrado (ainda sem histórico)'
        return screen(f'✅ <b>{escape(c["nome"])}</b> agora tem valor variável.\n\nPrevisão de {_rotulo_mes(mes)}: <b>≈ {fx.dinheiro(estimado)}</b> ({base}).\n\n'
                      'Na baixa, o bot pergunta quanto veio a conta; qualquer valor fecha o mês e entra na média dos próximos.',[voltar])
    if fva.eh_variavel(ident):
        estimado,meses=fva.previsao(c,mes)
        est=fva.estado(ident) or {}
        base=f'média de {", ".join(_rotulo_mes(m) for m in meses)}' if meses else 'valor cadastrado (ainda sem histórico)'
        return screen(f'<b>〰 {escape(c["nome"])} · valor variável</b>\n\nPrevisão de {_rotulo_mes(mes)}: <b>≈ {fx.dinheiro(estimado)}</b>\nBase: {base}.\n'
                      f'Histórico escolhido: {len(est.get("historico", []))} lançamento(s) anteriores.\n\n'
                      'A média usa os 3 últimos meses com pagamento. Cada baixa entra na média dos meses seguintes.',
                      [[('Desligar valor variável',('fixed_var_off',ident))],voltar])
    cands=fva.candidatos(c,mes)
    estimado,meses=fva.previsao(c,mes,cands)
    texto=[f'<b>〰 Valor varia todo mês · {escape(c["nome"])}</b>','',
           'A previsão passa a usar a <b>média dos 3 últimos meses</b> pagos, e a baixa pergunta o valor real.','']
    if cands:
        texto+=[f'Encontrei {len(cands)} lançamento(s) anteriores parecidos (termo: {", ".join(fv.termos_busca(c["nome"]))}):']
        texto+=[f'• {fx.data_br(t["data"])} · {escape(str(t["descricao"] or "")[:30])} · {fx.dinheiro(t["valor"])}' for t in cands[-12:]]
        texto+=['',f'Usando-os como histórico, a previsão de {_rotulo_mes(mes)} fica <b>≈ {fx.dinheiro(estimado)}</b>'
                   +(f' (média de {", ".join(_rotulo_mes(m) for m in meses)}).' if meses else '.'),
                '','Os lançamentos antigos não são alterados: só entram na média.']
    else:
        texto+=[f'Não encontrei lançamentos anteriores com o nome do fixo. A previsão começa pelo valor cadastrado ({fx.dinheiro(c["valor"])}) e se ajusta a cada baixa.']
    texto+=['','Nada foi alterado ainda.']
    rows=[]
    if cands:rows.append([(f'✅ Ativar com este histórico ({len(cands)})',('fixed_var_ok',ident,fva.assinatura(cands)))])
    rows.append([('Ativar sem histórico' if cands else '✅ Ativar valor variável',('fixed_var_ok',ident,'-'))])
    rows.append(voltar)
    return screen('\n'.join(texto),rows)

def campos(engine,key,ident):
    s=engine.session(key);s.stage=None;s.fixed_edit=None;s.draft=None
    c=fx.buscar(ident)
    fields='\n'.join(('\n<b>Vigência e situação</b>\n' if field=='inicio' else '')+f'{label}: <b>{escape(_exibir(field,c[fx.CAMPOS[field]]))}</b>' for field,label in fx.LABELS.items())
    month=s.month
    situation=('Pausado: não entra na previsão.' if not c['ativo'] else
               'Ativo e dentro da vigência desta competência.' if compromisso_ocorre_no_mes(c,month) else
               'Ativo, mas fora da vigência: não entra na previsão desta competência. Confira o início e o término.')
    rows=[]
    entries=list(fx.LABELS.items())
    for i in range(0,len(entries),2):rows.append([(label,('fixed_field',ident,field)) for field,label in entries[i:i+2]])
    rows.append(_nav(('fixed_detail',ident)))
    return screen(f'<b>Editar · {escape(c["nome"])}</b>\n\n{fields}\n\n<b>Situação em {_rotulo_mes(month)}</b>\n{situation}\n\nEscolha o campo. Nenhuma mudança ocorre antes de confirmar.',rows)

def _resumo_categorias(engine,s,todos):
    """{categoria: [total do mês, qtd, qtd no cartão]} dos fixos vigentes no mês (variável = estimativa)."""
    import fixos_variaveis_acoes as fva
    resumo={}
    for c in todos:
        if not (c['ativo'] and compromisso_ocorre_no_mes(c,s.month)):continue
        valor=fva.previsao(c,s.month)[0] if fva.eh_variavel(c['id']) else float(c['valor'] or 0)
        r=resumo.setdefault(c['categoria'] or 'Sem categoria',[0.0,0,0])
        r[0]+=valor;r[1]+=1;r[2]+=1 if 'credito' in _sem_acento(c['forma_pagamento']) else 0
    return resumo

def listar(engine,key,page=0,categoria=None):
    s=engine.session(key);s.stage=None;s.fixed_edit=None;s.draft=None
    todos=[dict(c) for c in db.listar_compromissos(tipo='fixo')]
    items=[c for c in todos if not categoria or _sem_acento(c['categoria'])==_sem_acento(categoria)]
    pages=max(1,(len(items)+7)//8);page=max(0,min(page,pages-1))
    rows=[[(f'{page*8+n}. {c["nome"][:35]}',('fixed_detail',c['id']))] for n,c in enumerate(items[page*8:page*8+8],1)]
    nav=[]
    if page:nav.append(('‹ Anteriores',('fixed_list',page-1,*([categoria] if categoria else []))))
    if page+1<pages:nav.append(('Próximos ›',('fixed_list',page+1,*([categoria] if categoria else []))))
    if nav:rows.append(nav)
    resumo=_resumo_categorias(engine,s,todos)
    if categoria:
        rows.append([('💰 A pagar desta categoria',('pagar_cat',categoria,s.month,s.month)),('✖ Todas as categorias',('fixed_list',0))])
    elif len(resumo)>1:
        botoes=[(f'🏷 {cat[:18]} ({r[1]})',('fixed_list',0,cat)) for cat,r in sorted(resumo.items())]
        rows+=[botoes[i:i+2] for i in range(0,len(botoes),2)]
    rows.append(_nav(('back',)))
    rows.insert(0,[('➕ Novo fixo',('new_fixed_start',))])
    from telegram_experiencia import money
    lines=[f'<b>Fixos · {escape(categoria)}</b>' if categoria else '<b>Fixos · gerenciar cadastros</b>',
           '<i>Consulte as condições atuais e as versões preservadas.</i>', '']
    if resumo and not categoria:
        lines+=[f'<b>Por categoria · {_rotulo_mes(s.month)}</b>']
        lines+=[f'🏷 {escape(cat)} · <b>{money(r[0])}</b> ({r[1]})'+(f' · 💳 {r[2]} no cartão' if r[2] else '')
                for cat,r in sorted(resumo.items(),key=lambda x:-x[1][0])]
        lines+=['<i>Toque numa categoria para filtrar. Fixos no cartão já entram na fatura.</i>','']
    elif categoria and categoria in resumo:
        r=resumo[categoria]
        lines+=[f'Previsto em {_rotulo_mes(s.month)}: <b>{money(r[0])}</b> ({r[1]} vigentes)','']
    for n,c in enumerate(items[page*8:page*8+8],1):
        vigente=bool(c['ativo']) and compromisso_ocorre_no_mes(c,s.month)
        status='🟢 Vigente' if vigente else ('⏸ Pausado' if not c['ativo'] else '📁 Fora da vigência')
        lines += [f'<b>{page*8+n}. {escape(c["nome"])}</b>',
                  f'{escape(_exibir("valor",c["valor"]))} · {escape(_rotulo_forma(c["forma_pagamento"]))}',
                  f'{status} em {_rotulo_mes(s.month)}', '']
    if not items:
        lines += ['Nenhum fixo cadastrado ainda. Cadastre as contas que se repetem (aluguel, internet, assinaturas) '
                  'para o assessor prever os vencimentos.', '']
    lines += [f'Página {page+1}/{pages}.',
              '💡 Selecione um cadastro, incluindo pausados e encerrados para edição. O relatório <b>fixos</b> considera somente os ativos e vigentes no mês atual.']
    return screen('\n'.join(lines),rows)

def previa(engine,key):
    s=engine.session(key);d=s.fixed_edit
    p=d.get('preview') if s.stage=='fixed_confirm' else None
    if p is None:p=fx.preparar(d['id'],d['field'],d['value'],d.get('month'))
    d['preview']=p;s.stage='fixed_confirm'
    field=p['campo'];old=_exibir(field,p['antes'][fx.CAMPOS[field]]);new=_exibir(field,p['depois'][fx.CAMPOS[field]])
    impact=('A condição anterior será encerrada no mês anterior. Uma nova condição valerá a partir de '+_rotulo_mes(p['mes'])+'. Os meses anteriores serão preservados.' if p['mes'] else 'Correção do cadastro: pode alterar os resumos de meses anteriores. Pagamentos registrados não serão editados.')
    return screen(f'<b>Confirmar edição</b>\n{escape(p["antes"]["nome"])}\n\n<b>{fx.LABELS[field]}</b>\nDe: {escape(old)}\nPara: <b>{escape(new)}</b>\n\n{impact}',[[('✅ Salvar',('fixed_save',)),('Cancelar',('fixed_detail',d['id']))],_nav(('fixed_detail',d['id']))])

def retomar(engine,key):
    s=engine.session(key);d=s.fixed_edit
    if not d:raise ValueError('Abra editar fixos novamente.')
    cancel=[('Cancelar',('fixed_detail',d['id']))]
    if s.stage=='fixed_confirm':return previa(engine,key)
    if s.stage=='fixed_scope':
        return screen('<b>Como aplicar a alteração?</b>\n\nCorrigir cadastro pode alterar resumos anteriores. A partir de um mês preserva a condição anterior e cria uma nova condição para o período seguinte.',[[('Corrigir cadastro',('fixed_scope','correction'))],[('A partir de um mês',('fixed_scope','month'))],[cancel[0]],_nav(('fixed_detail',d['id']))])
    if s.stage=='fixed_month':
        return _tela_mes(engine,d['id'])
    examples={'inicio':'DD/MM/AAAA','termino':'DD/MM/AAAA ou sem término','valor':'48,30','vencimento':'dia 25','status':'ativo ou pausado','forma':'Pix, Débito, Crédito, Boleto, Dinheiro ou Transferência'}
    field=d['field']
    current=fx.buscar(d['id'])
    text=(f'<b>{fx.LABELS[field]}</b>\n'
          f'{escape(current["nome"])}\nAtual: <b>{escape(_exibir(field,current[fx.CAMPOS[field]]))}</b>\n\n'
          'Envie o novo valor. '+examples.get(field,'Envie apenas o texto desejado.')+
          '\n\nDepois haverá uma prévia com o botão Salvar. Use /cancelar para sair.')
    return screen(text,[cancel,_nav(('fixed_detail',d['id']))])


def acao(engine,key,action):
    s=engine.session(key);kind=action[0]
    if kind=='fixed_resume':return retomar(engine,key)
    if kind=='fixed_list':return listar(engine,key,int(action[1]),str(action[2]) if len(action)>2 and action[2] else None)
    if kind=='fixed_detail':return detalhe(engine,key,int(action[1]))
    if kind=='fixed_edit_fields':return campos(engine,key,int(action[1]))
    if kind in {'fixed_var','fixed_var_ok','fixed_var_off','fixed_var_off_ok'}:return _variavel(engine,key,action)
    if kind=='fixed_field':
        ident=int(action[1]);field=action[2];fx.buscar(ident)
        if field not in fx.LABELS:raise ValueError('Campo inválido.')
        s.fixed_edit={'id':ident,'field':field};s.stage='fixed_field';s.draft=None
        return retomar(engine,key)
    d=s.fixed_edit
    if not d:raise ValueError('Abra editar fixos novamente.')
    if kind=='fixed_scope':
        if s.stage!='fixed_scope':raise ValueError('Abra a edição novamente.')
        if action[1]=='correction':d['month']=None;return previa(engine,key)
        s.stage='fixed_month'
        return _tela_mes(engine,d['id'])
    if kind=='fixed_month_pick':
        if s.stage!='fixed_month':raise ValueError('Abra a edição novamente.')
        mes=str(action[1])
        if not re.fullmatch(r'\d{4}-\d{2}',mes):raise ValueError('Mês inválido.')
        d['month']=mes;return previa(engine,key)
    if kind=='fixed_save':
        if s.stage!='fixed_confirm' or not d.get('preview'):raise ValueError('Abra a prévia novamente.')
        result=fx.salvar(d['preview'],key)
        s.fixed_edit=None;s.stage=None
        linhas=[escape(l) for l in result.split('\n')]
        if linhas and linhas[-1].startswith(escape(fx.DICA_CODIGO)):linhas[-1]=f'<i>{linhas[-1]}</i>'
        return screen('\n'.join(linhas),[[('Editar fixos',('fixed_list',0))],_nav(('fixed_list',0))])
    raise ValueError('Ação de fixo desconhecida.')

def texto(engine,key,text):
    s=engine.session(key)
    if re.fullmatch(r'editar\s+fixos',text.strip(),re.I):return listar(engine,key)
    m=re.fullmatch(r'(?:editar|detalhar)\s+fixo\s+#?c?(\d+)',text.strip(),re.I)
    if m:return detalhe(engine,key,int(m[1]))
    d=s.fixed_edit
    if not d or not str(s.stage).startswith('fixed_'):return None
    routes={'inicio':'home','🏠 inicio':'home','menu':'home','mais':'more','⚙ mais':'more','historico':'history','🔎 historico':'history','a pagar':'pay','🧾 a pagar':'pay','registrar':'register','➕ registrar':'register','analises':'analytics','📊 analises':'analytics'}
    clean=fx.norm(text)
    clean_route=clean.lstrip('/')
    routes.update({'mes':'home'})
    if clean_route in routes:return engine.act(key,('view',routes[clean_route]))
    if clean_route in {'ajuda','help'}:return retomar(engine,key)
    if fx.norm(text) in {'cancelar','/cancelar'}:return detalhe(engine,key,d['id'])
    if text.strip().startswith('/'):
        return screen('Esse comando não é uma resposta para o campo. Use /cancelar para sair ou retome a edição.',[[('Retomar edição',('fixed_resume',)),('Cancelar',('fixed_detail',d['id']))]])
    if s.stage=='fixed_field':
        fx.validar(d['field'],text)
        d['value']=text
        if d['field'] in {'inicio','termino'}:return previa(engine,key)
        s.stage='fixed_scope'
        return retomar(engine,key)
    if s.stage=='fixed_month':
        mes=interpretar_mes(text,engine.date_provider())
        if mes is None:raise ValueError('Não entendi o mês. Escolha um botão ou digite, por exemplo, 12/2026 ou dezembro.')
        d['month']=mes;return previa(engine,key)
    return retomar(engine,key)
