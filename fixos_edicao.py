"""Edição de fixos: correção do cadastro ou nova condição mensal, com auditoria."""
import calendar
import json
import re
import sqlite3
import unicodedata
from datetime import date, datetime, timedelta
import relogio
import database as db
from categorias import canonicalizar_categoria
from money import parse_money, formatar_brl
from fixos_vigencia import garantir_sem_sobreposicao

CAMPOS = {'nome':'nome','descricao':'nome','categoria':'categoria','valor':'valor',
          'conta':'conta_pagamento','forma':'forma_pagamento','vencimento':'dia_vencimento',
          'inicio':'data_inicio','termino':'data_fim','fim':'data_fim','status':'ativo'}
LABELS = {'nome':'Nome','categoria':'Categoria','valor':'Valor','conta':'Conta',
          'forma':'Forma de pagamento','vencimento':'Vencimento','inicio':'Início',
          'termino':'Término','status':'Status'}

DICA_CODIGO='Código para comandos de texto:'

def norm(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(text or '').lower()) if not unicodedata.combining(c)).strip()

def data(valor):
    text=str(valor).strip()
    try:
        if re.fullmatch(r'\d{2}/\d{2}/\d{4}',text):
            d,m,y=map(int,text.split('/'));return date(y,m,d).isoformat()
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}',text):return date.fromisoformat(text).isoformat()
    except ValueError:pass
    raise ValueError('Data inválida. Use DD/MM/AAAA.')

def validar(campo,valor):
    if campo not in LABELS:raise ValueError('Campo de fixo inválido.')
    text=str(valor).strip();clean=norm(text)
    if campo=='valor':
        try:n=parse_money(text)
        except Exception as exc:raise ValueError('Informe um valor positivo, por exemplo 48,30.') from exc
        if not n.is_finite() or n<=0 or n>999999999:raise ValueError('Valor deve ser positivo e até 999.999.999.')
        return float(n)
    if campo=='vencimento':
        clean=re.sub(r'^dia\s+','',clean)
        if not clean.isdigit() or not 1<=int(clean)<=31:raise ValueError('Vencimento deve ser um dia de 1 a 31.')
        return int(clean)
    if campo=='inicio':return data(text)
    if campo=='termino':return None if clean in {'sem termino','sem fim','indeterminado','nenhum'} else data(text)
    if campo=='status':
        if clean not in {'ativo','pausado'}:raise ValueError('Informe ativo ou pausado.')
        return int(clean=='ativo')
    if campo=='forma':
        forms={'pix':'pix','debito':'débito','credito':'crédito','cartao':'crédito','cartao de credito':'crédito','cartao de debito':'débito','dinheiro':'dinheiro','boleto':'boleto','transferencia':'transferência'}
        if clean not in forms:raise ValueError('Forma inválida. Use Pix, Débito, Crédito, Dinheiro, Boleto ou Transferência.')
        return forms[clean]
    if text.startswith('/'):
        raise ValueError('Comandos não são valores de cadastro. Use /cancelar para sair.')
    if not text or len(text)>160 or not any(c.isalpha() for c in text):raise ValueError('Informe um texto de até 160 caracteres, contendo letras.')
    if re.search(r'\b(register_expense|register_income)\b',clean):raise ValueError('Informe uma categoria ou nome válido, sem identificadores técnicos.')
    if campo=='categoria':
        if re.match(r'^para\s+',clean):raise ValueError('Categoria começa com “para”. Corrija o comando sem repetir “para”.')
        return canonicalizar_categoria(text.title())
    if campo=='conta':
        if clean in {'pix','debito','credito','dinheiro','boleto','transferencia'}:raise ValueError('Informe a conta; a forma de pagamento é outro campo.')
        from compromissos import normalizar_conta_pagamento_usuario
        return normalizar_conta_pagamento_usuario(text)
    return text

def buscar(ident):
    row=db.buscar_compromisso_por_id(int(ident))
    if row is None:raise ValueError('Não encontrei esse fixo. Abra a lista de fixos e escolha novamente.')
    if row['tipo']!='fixo':raise ValueError('Esse cadastro não é um fixo. Nada foi alterado.')
    return dict(row)

def preparar(ident,campo,valor,mes=None):
    campo=norm(campo);campo={'descricao':'nome','fim':'termino'}.get(campo,campo)
    antes=buscar(ident);novo=validar(campo,valor)
    depois=dict(antes);depois[CAMPOS[campo]]=novo
    # Conta explícita tem precedência sobre uma conta_origem herdada de importação.
    if campo=='conta':depois['conta_origem']=novo
    if depois['data_fim'] and depois['data_fim']<depois['data_inicio']:
        raise ValueError('O término não pode ser anterior ao início. Nada foi alterado.')
    if mes:
        if not re.fullmatch(r'\d{4}-\d{2}',mes):raise ValueError('Mês inválido. Use AAAA-MM.')
        try:inicio=date.fromisoformat(mes+'-01')
        except ValueError as exc:raise ValueError('Mês inválido. Use AAAA-MM.') from exc
        if campo in {'inicio','termino'}:raise ValueError('Para datas de início e término, use corrigir cadastro.')
        if mes<=antes['data_inicio'][:7]:raise ValueError('Escolha um mês posterior ao início, ou use corrigir cadastro.')
        if antes['data_fim'] and antes['data_fim']<inicio.isoformat():raise ValueError('O fixo já termina antes desse mês. Corrija o término primeiro, se necessário.')
    return {'id':int(ident),'campo':campo,'antes':antes,'depois':depois,'mes':mes}

def salvar(preview,sessao=None):
    from conciliacao import bloquear_alteracao_compromisso
    ident=preview['id'];campo=preview['campo'];antes=preview['antes'];depois=preview['depois'];mes=preview['mes']
    with db.get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE');conn.row_factory=sqlite3.Row
        atual=conn.execute('SELECT * FROM compromissos WHERE id=?',(ident,)).fetchone()
        if atual is None or dict(atual)!=antes:raise ValueError('O fixo mudou desde a prévia. Abra a edição novamente.')
        changed={k:v for k,v in depois.items() if antes[k]!=v}
        if not changed:return f'{antes["nome"]}: o cadastro já tem esse valor. Nada foi alterado.\n{DICA_CODIGO} #C{ident}'
        candidato=dict(depois)
        if mes:candidato['data_inicio']=mes+'-01'
        garantir_sem_sobreposicao(conn,ident,candidato)
        if mes:
            # Nova condição: a versão atual continua valendo (com seus vínculos)
            # até o mês anterior. Só bloqueia conciliação do mês novo em diante,
            # que ficaria sem a ocorrência correspondente.
            from conciliacao import listar_vinculos, ConciliacaoError
            if any(v['compromisso_id']==ident and v['mes']>=mes for v in listar_vinculos(conn)):
                raise ConciliacaoError(f'Compromisso com conciliações em {mes_extenso(mes)} ou depois: desvincule esses movimentos '
                                       'ou escolha um mês posterior para a nova condição. Nada foi alterado.')
        elif campo not in {'nome','categoria','vencimento','conta'}:
            # A conta de pagamento não invalida conciliações: o vínculo guarda o lançamento e só
            # confere a assinatura do compromisso na hora de vincular. Valor, forma e datas seguem protegidos.
            bloquear_alteracao_compromisso(conn,ident)
        agora=relogio.agora().isoformat(timespec='seconds')
        if mes:
            inicio=date.fromisoformat(mes+'-01')
            old=dict(antes);old['data_fim']=(inicio-timedelta(days=1)).isoformat();old['atualizado_em']=agora
            conn.execute('UPDATE compromissos SET data_fim=?, atualizado_em=? WHERE id=?',(old['data_fim'],agora,ident))
            novo=dict(depois);novo.pop('id');novo.update(data_inicio=inicio.isoformat(),criado_em=agora,atualizado_em=agora)
            columns=list(novo)
            new_id=conn.execute('INSERT INTO compromissos ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',list(novo.values())).lastrowid
            novo['id']=new_id
            db.registrar_auditoria('compromissos',ident,'encerrar_condicao',antes,old,'telegram',str(sessao),conn)
            db.registrar_auditoria('compromissos',new_id,'nova_condicao',{'origem_id':ident},novo,'telegram',str(sessao),conn)
            return f'✅ Nova condição a partir de {mes_extenso(mes)}\n{novo["nome"]}: a condição anterior foi preservada até {data_br(old["data_fim"])} e a nova passa a valer em {mes_extenso(mes)}.\nPagamentos registrados não foram alterados.\n{DICA_CODIGO} #C{new_id}'
        changed['atualizado_em']=agora
        conn.execute('UPDATE compromissos SET '+','.join(k+'=?' for k in changed)+' WHERE id=?',[*changed.values(),ident])
        final=dict(antes);final.update(changed)
        db.registrar_auditoria('compromissos',ident,'editar_fixo',antes,final,'telegram',str(sessao),conn)
    value=exibir(campo,depois[CAMPOS[campo]])
    return f'✅ Fixo atualizado\n{depois["nome"]}\n{LABELS[campo]}: {value}\nCadastro corrigido; os resumos podem refletir a correção em meses anteriores. Pagamentos registrados preservados.\n{DICA_CODIGO} #C{ident}'

_NOMES_MES=['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']

def mes_extenso(mes):
    """'2026-11' -> 'Novembro 2026' (só exibição)."""
    t=str(mes or '')
    if re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',t):return f'{_NOMES_MES[int(t[5:7])-1]} {t[:4]}'
    return t

def data_br(valor):
    """'2026-06-01' -> '01/06/2026' (só exibição)."""
    t=str(valor or '')
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}.*',t):return f'{t[8:10]}/{t[5:7]}/{t[:4]}'
    return t

def dinheiro(valor):
    return re.sub(r'R\$ -(?=\d)','−R$ ',formatar_brl(valor))

def exibir(campo,valor):
    if campo=='valor':return dinheiro(valor)
    if campo=='termino' and not valor:return 'sem término'
    if campo in {'inicio','termino'}:return data_br(valor)
    if campo=='status':return 'ativo' if valor else 'pausado'
    return str(valor or 'não informado')

def parse(text):
    # Mantém a grafia original dos valores; normaliza somente o nome do campo.
    m=re.fullmatch(r'(?:alterar|mudar|trocar|corrigir|editar)\s+(nome|descri[cç][aã]o|categoria|valor|conta|forma|vencimento|in[ií]cio|t[eé]rmino|fim|status)\s+(?:do\s+)?fixo\s+#?c?(\d+)\s+(?:para|por)\s+(.+?)(?:\s+a partir de\s+(\d{4}-\d{2}))?',text.strip(),re.I)
    if m:return int(m[2]),norm(m[1]),m[3],m[4]
    m=re.fullmatch(r'alterar\s+fixo\s+#?c?(\d+)\s+para\s+(.+?)(?:\s+a partir de\s+(\d{4}-\d{2}))?',text.strip(),re.I)
    if m:return int(m[1]),'valor',m[2],m[3]
    return None
