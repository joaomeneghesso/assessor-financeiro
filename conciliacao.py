"""Vínculos explícitos entre uma ocorrência de compromisso e um lançamento.

O registro de eventos já existente é o armazenamento durável. Não há migration,
backfill nem associação automática por descrição. Gravações usam a mesma transação
SQLite do lançamento; projeções e checklist consomem estes mesmos vínculos.
"""
import calendar
import hashlib
import json
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime, timedelta, timezone

import relogio

import database as db
from consulta_cache import obter_ou_calcular as _consulta_cache, escopo as _escopo_consulta
from faturas_competencia import eh_credito, competencia_transacao
from money import parse_money

class ConciliacaoError(ValueError):
    """Falha de validação do vínculo, exibível ao usuário."""


_CORTE = ContextVar('conciliacao_corte', default=None)


def _hoje():
    """Hoje no fuso do titular (UTC-3). Ponto único do relógio da conciliação,
    para que os testes possam fixar a data com ``patch('conciliacao._hoje')``."""
    # relogio.hoje respeita patch.object(conciliacao, 'datetime', ...) de testes antigos.
    return relogio.hoje(fonte_datahora=datetime)


def centavos(valor):
    return int(parse_money(valor) * 100)


def normalizar(texto):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', str(texto or '').lower())
                           if not unicodedata.combining(c)).split())


def fim_mes(mes):
    d = date.fromisoformat(mes + '-01')
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1]).isoformat()


@contextmanager
def referencia(ate):
    token = _CORTE.set(ate)
    try:
        with _escopo_consulta(_escopo_do_corte(ate)):
            yield
    finally:
        _CORTE.reset(token)


def _escopo_do_corte(ate):
    """Escopo do cache de consulta para leituras feitas sob este corte.

    O corte só muda o resultado pelo conjunto de vínculos ativos com data até
    ele (``ajustar_projecao``). Cortes que enxergam o mesmo conjunto dividem o
    mesmo escopo; assim o cache fica correto sem recalcular tudo a cada corte.
    """
    if not ate:
        return None
    try:
        datas = [v['data'] for v in listar_vinculos() if v['data'] <= ate]
    except Exception:
        return ('corte', ate)
    return ('corte_vinculos', max(datas) if datas else '')


def assinatura_alvo(compromisso):
    campos = ('id', 'tipo', 'valor', 'data_inicio', 'data_fim', 'ativo', 'parcelas_total',
              'conta_pagamento','conta_origem','forma_pagamento')
    payload = {k: compromisso.get(k) for k in campos}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _auditar(conn, chave, operacao, dados, usuario):
    db.registrar_auditoria('conciliacao', chave, operacao, dados_depois=dados,
                          usuario_sessao=usuario, origem='telegram', conn=conn)


def _listar_vinculos_conn(conn, ate=None, incluir_inativos=False):
    cursor = conn.execute("SELECT entidade_id, operacao, dados_depois, usuario_sessao FROM auditoria_eventos WHERE entidade='conciliacao' ORDER BY id")
    eventos = {}
    for chave, operacao, payload, usuario in cursor:
        dados = json.loads(payload)
        dados.update(chave=chave, ativo=operacao == 'vinculado', usuario=usuario)
        eventos[chave] = dados
    candidatos = [
        item for item in eventos.values()
        if (incluir_inativos or item['ativo']) and (not ate or item['data'] <= ate)
    ]
    ids = sorted({item['transacao_id'] for item in candidatos})
    movimentos = {}
    if ids:
        marcas = ','.join('?' for _ in ids)
        for row in conn.execute(
            f'SELECT id,data,tipo,valor,conta,forma_pagamento FROM transacoes WHERE id IN ({marcas})',
            ids,
        ):
            movimentos[row[0]] = list(row[1:])
    ids_fatura = sorted({item['transacao_id'] for item in candidatos if item.get('ativo') and 'fatura_v39' in item})
    metadados = {}
    if ids_fatura:
        marcas = ','.join('?' for _ in ids_fatura)
        for row in conn.execute(
            f'SELECT id,data_compra,competencia_fatura FROM transacoes WHERE id IN ({marcas})',
            ids_fatura,
        ):
            metadados[row[0]] = list(row[1:])
    result = []
    for item in candidatos:
        if item['ativo'] and 'fatura_v39' in item and metadados.get(item['transacao_id']) != item['fatura_v39']:
            raise ConciliacaoError('A fatura de um movimento conciliado foi alterada. Revise o vinculo antes de calcular.')
        if item['ativo'] and movimentos.get(item['transacao_id']) != item['movimento']:
            raise ConciliacaoError('Um lançamento conciliado foi alterado fora do fluxo. Restaure a alteração ou revise o vínculo antes de calcular.')
        result.append(item)
    return result


def listar_vinculos(conn=None, ate=None, incluir_inativos=False):
    if conn is None:
        return _consulta_cache(
            ("conciliacao.listar_vinculos", ate, bool(incluir_inativos)),
            lambda: _listar_vinculos_sem_conexao(ate, incluir_inativos),
        )
    return _listar_vinculos_conn(conn, ate, incluir_inativos)


def _listar_vinculos_sem_conexao(ate=None, incluir_inativos=False):
    with db.get_connection() as connection:
        return _listar_vinculos_conn(connection, ate, incluir_inativos)


def fixos_variaveis_ativos():
    """{id (str): histórico {mes: centavos}} dos fixos de valor variável (lido 1x por consulta)."""
    import fixos_variaveis as fv
    def calcular():
        estados = fv.estados_de_eventos(db.listar_auditoria(entidade=fv.ENTIDADE, limite=1000))
        return {cid: fv.historico_por_mes(t for t in (db.buscar_transacao_por_id(i) for i in est.get('historico', []))
                                          if t is not None)
                for cid, est in estados.items()}
    return _consulta_cache(('fixos_variaveis',), calcular)


def estimativa_fixo_variavel(compromisso_id, mes, valor_cadastro, baixas_por_mes=None):
    """(valor, meses usados) da previsão de um fixo variável; baixas lidas dos vínculos se não vierem."""
    import fixos_variaveis as fv
    if baixas_por_mes is None:
        baixas_por_mes = {}
        for v in listar_vinculos():
            if v['compromisso_id'] == int(compromisso_id):
                baixas_por_mes[v['mes']] = baixas_por_mes.get(v['mes'], 0) + v['centavos']
    historico = fixos_variaveis_ativos().get(str(compromisso_id), {})
    return fv.estimativa(historico, baixas_por_mes, mes, valor_cadastro)


def ajustar_projecao(itens, mes):
    corte = _CORTE.get() or fim_mes(mes)
    total = {}
    for v in listar_vinculos(ate=corte):
        key = (v['compromisso_id'], v['mes'])
        total[key] = total.get(key, 0) + v['centavos']
    import fixos_variaveis as fv
    variaveis = fixos_variaveis_ativos()
    resultado = []
    for original in itens:
        item = dict(original)
        pago = total.get((item['id'], mes), 0)
        if (item.get('origem') == 'compromisso' and str(item['id']) in variaveis
                and not fv.elegivel(item)):
            # Fixo de valor variável: qualquer baixa fecha o mês; sem baixa, vale a estimativa.
            if pago:
                item.update(valor=0.0, valor_original=pago/100, valor_conciliado=pago/100, conciliado=True)
            else:
                baixas = {m: c for (cid, m), c in total.items() if cid == item['id']}
                estimado, _ = estimativa_fixo_variavel(item['id'], mes, item['valor'], baixas)
                item.update(valor=estimado, valor_original=estimado, valor_estimado=True)
            resultado.append(item)
            continue
        if pago:
            previsto = centavos(item['valor'])
            if pago > previsto:
                raise ConciliacaoError('O valor de um compromisso ficou menor que o já conciliado. Revise o compromisso e os vínculos.')
            item.update(valor=(previsto-pago)/100, valor_original=previsto/100,
                        valor_conciliado=pago/100, conciliado=True)
        resultado.append(item)
    return resultado


def alvo(compromisso_id, mes):
    import compromissos as c
    fim_mes(mes)
    row = db.buscar_compromisso_por_id(int(compromisso_id))
    if not row or not row['ativo'] or not c.compromisso_ocorre_no_mes(row, mes):
        raise ConciliacaoError('Esse compromisso não está ativo nessa competência.')
    item = dict(row)
    item['assinatura'] = assinatura_alvo(item)
    item['mes'] = mes
    item['tipo_transacao'] = 'receita' if item['tipo'] in {'entrada_fixa','entrada_avulsa'} else 'despesa'
    total = sum(v['centavos'] for v in listar_vinculos() if v['compromisso_id']==item['id'] and v['mes']==mes)
    item['restante'] = max(0, centavos(item['valor'])-total)/100
    import fixos_variaveis as fv
    if str(item['id']) in fixos_variaveis_ativos() and not fv.elegivel(item):
        # Valor variável: a baixa pergunta o valor real; a estimativa é só sugestão.
        item['variavel'] = True
        item['estimativa'], _ = estimativa_fixo_variavel(item['id'], mes, item['valor'])
        item['restante'] = 0.0 if total else item['estimativa']
    return item


def vincular_conn(conn, transacao_id, referencia_alvo, chave, usuario):
    """Revalida alvo, saldo e lançamento sob BEGIN IMMEDIATE antes de vincular."""
    import compromissos as c
    conn.row_factory = sqlite3.Row
    anteriores = listar_vinculos(conn, incluir_inativos=True)
    for v in anteriores:
        if v['chave'] == chave:
            if not v['ativo'] or v['usuario'] != usuario or v['transacao_id'] != transacao_id:
                raise ConciliacaoError('Esta confirmação de conciliação já foi usada.')
            if v['compromisso_id'] != referencia_alvo['id'] or v['mes'] != referencia_alvo['mes']:
                raise ConciliacaoError('A confirmação aponta para outro compromisso.')
            return v
    if any(v['ativo'] and v['transacao_id']==transacao_id for v in anteriores):
        raise ConciliacaoError('Este lançamento já está vinculado. Desvincule antes de escolher outro compromisso.')
    row = conn.execute('SELECT * FROM compromissos WHERE id=?', (referencia_alvo['id'],)).fetchone()
    if not row or not row['ativo']:
        raise ConciliacaoError('Compromisso indisponível. Abra a lista novamente.')
    comp = dict(row); mes = referencia_alvo['mes']; fim_mes(mes)
    if not c.compromisso_ocorre_no_mes(row,mes) or assinatura_alvo(comp)!=referencia_alvo['assinatura']:
        raise ConciliacaoError('O compromisso mudou desde a prévia. Confira novamente antes de salvar.')
    t = conn.execute('SELECT * FROM transacoes WHERE id=?',(transacao_id,)).fetchone()
    tipo = 'receita' if comp['tipo'] in {'entrada_fixa','entrada_avulsa'} else 'despesa'
    if not t or t['tipo'] != tipo:
        raise ConciliacaoError('O tipo do lançamento não corresponde ao compromisso.')
    if date.fromisoformat(t['data']) > _hoje():
        raise ConciliacaoError('Um movimento futuro ainda não pode liquidar uma previsão. Confirme a data real do pagamento ou recebimento.')
    if normalizar(t['conta']) in {'','pix','boleto','entrada','nao informada','nao informado'}:
        raise ConciliacaoError('Corrija a conta do lançamento antes de vinculá-lo. Forma de pagamento não é conta.')
    fatura_proxima = (eh_credito(t) and 'competencia_fatura' in t.keys() and t['competencia_fatura']
                       and competencia_transacao(t) == mes
                       and normalizar(t['conta']) == normalizar(comp.get('conta_origem') or comp.get('conta_pagamento'))
                       and normalizar(comp.get('forma_pagamento')) == 'credito')
    if (eh_credito(t) and 'competencia_fatura' in t.keys() and t['competencia_fatura']
            and competencia_transacao(t) != t['data'][:7] and not fatura_proxima):
        raise ConciliacaoError('A compra com fatura escolhida so pode conciliar a mesma competencia e o mesmo cartao no credito.')
    if t['data'][:7] < mes and not fatura_proxima:
        raise ConciliacaoError('Antecipação para uma competência futura exige revisão específica. Escolha a competência do movimento ou anterior.')
    if (t['parcelas_total'] or 1)>1:
        raise ConciliacaoError('Vincule um lançamento individual à ocorrência correspondente.')
    pago = sum(v['centavos'] for v in anteriores if v['ativo'] and v['compromisso_id']==comp['id'] and v['mes']==mes)
    valor = centavos(t['valor'])
    import fixos_variaveis as fv
    if str(comp['id']) in fixos_variaveis_ativos() and not fv.elegivel(comp):
        if pago:  # valor variável: uma baixa por mês, de qualquer valor
            raise ConciliacaoError('Esta conta de valor variável já tem baixa neste mês. Desvincule a anterior para trocar o valor.')
    elif valor > centavos(comp['valor'])-pago:
        raise ConciliacaoError('O valor supera o restante desse compromisso. Atualize a prévia ou registre a diferença separadamente.')
    dados = dict(compromisso_id=comp['id'],mes=mes,tipo=tipo,transacao_id=transacao_id,
                 centavos=valor,data=t['data'],conta=t['conta'],nome=comp['nome'],
                 movimento=[t['data'],t['tipo'],t['valor'],t['conta'],t['forma_pagamento']])
    if 'competencia_fatura' in t.keys() and t['competencia_fatura']:
        dados['fatura_v39'] = [t['data_compra'],t['competencia_fatura']]
    _auditar(conn,chave,'vinculado',dados,usuario)
    return dict(dados,chave=chave,usuario=usuario,ativo=True)


def vincular_existente(transacao_id, referencia_alvo, chave, usuario, movimento_esperado=None, fatura_esperada=None):
    with db.fatura_write_transaction() as conn:
        if movimento_esperado is not None:
            row=conn.execute("SELECT data,tipo,valor,conta,forma_pagamento FROM transacoes WHERE id=?",(transacao_id,)).fetchone()
            if not row or list(row)!=movimento_esperado:
                raise ConciliacaoError("O lançamento mudou desde a prévia. Abra o Histórico novamente.")
        if fatura_esperada is not None:
            meta=conn.execute('SELECT data_compra,competencia_fatura FROM transacoes WHERE id=?',(transacao_id,)).fetchone()
            if not meta or list(meta)!=list(fatura_esperada):
                raise ConciliacaoError('A fatura mudou desde a previa. Abra o Historico novamente.')
        return vincular_conn(conn,transacao_id,referencia_alvo,chave,usuario)


def _mesmo_titular(a, b):
    """Mesmo usuário e mesmo chat, ignorando apenas o tópico do Telegram.

    `1:2:topic:7` e `1:2` pertencem ao mesmo titular no mesmo chat; outro
    usuário ou outro chat continuam distintos."""
    if a == b:
        return True
    if not isinstance(a, str) or not isinstance(b, str) or not a or not b:
        return False
    base = lambda s: re.sub(r':topic:[^:]+$', '', s)
    return bool(base(a)) and base(a) == base(b)


def desvincular_conn(conn, chave, usuario):
    eventos = listar_vinculos(conn,incluir_inativos=True)
    event = next((v for v in eventos if v['chave']==chave),None)
    if not event or not _mesmo_titular(event['usuario'],usuario):
        raise ConciliacaoError('Vínculo não encontrado nesta sessão.')
    if not event['ativo']:
        return False
    _auditar(conn,chave,'desvinculado',event,usuario)
    return True


def desvincular(chave,usuario):
    """Reabre a previsão e preserva o movimento real; não simula devolução bancária."""
    with db.fatura_write_transaction() as conn:
        return desvincular_conn(conn,chave,usuario)


def bloquear_alteracao_transacoes(conn, ids):
    ids = set(ids)
    if any(v['transacao_id'] in ids for v in listar_vinculos(conn)):
        raise ConciliacaoError('Lançamento conciliado: use Desfazer este registro ou desvincule pela tela Conciliações antes de editar/excluir.')


def bloquear_alteracao_compromisso(conn, compromisso_id):
    if any(v['compromisso_id']==compromisso_id for v in listar_vinculos(conn)):
        raise ConciliacaoError('Compromisso com conciliações: desvincule os movimentos antes de alterar valor, período ou excluir. Nome e vencimento podem ser ajustados.')


def _revisoes_pendentes(mes):
    """Sinaliza ambiguidades; não associa nem altera movimentos por semelhança."""
    import compromissos as c
    revisoes=[]
    status={k:dict(v) for k,v in db.buscar_checklist_status_mes(mes).items()}
    for item in c.projetar_compromissos_mes(mes):
        aliases=('C'+str(item['id']),'P'+str(item['id']))
        if not item.get('conciliado') and any(status.get(a,{}).get('status')=='pago' for a in aliases):
            revisoes.append(dict(tipo='baixa_antiga',compromisso_id=item['id'],nome=item['nome'],mes=mes))
    vinculados={v['transacao_id'] for v in listar_vinculos()}
    separados={}
    with db.get_connection() as conn:
        for payload, in conn.execute("SELECT dados_depois FROM auditoria_eventos WHERE entidade='conciliacao_revisao' ORDER BY id"):
            item=json.loads(payload);separados[item['id']]=item['movimento']
    receitas=[dict(t) for t in db.buscar_transacoes_por_mes(mes) if t['tipo']=='receita' and t['id'] not in vinculados]
    for t in receitas:
        movimento=[t[k] for k in ('data','tipo','valor','conta','forma_pagamento')]
        if separados.get(t['id'])==movimento:continue
        for item in c.projetar_entradas_programadas_mes(mes):
            if item['valor']>0 and normalizar(item['nome'])==normalizar(t['descricao']) and normalizar(item['conta_pagamento'])==normalizar(t['conta']):
                revisoes.append(dict(tipo='receita_sem_vinculo',transacao_id=t['id'],compromisso_id=item['id'],nome=item['nome'],mes=mes))
    return revisoes


def revisoes_pendentes(mes):
    return _consulta_cache(
        ("conciliacao.revisoes_pendentes", str(mes)),
        lambda: _revisoes_pendentes(mes),
    )


def marcar_separado_conn(conn,transacao_id,usuario,movimento_esperado=None):
    row=conn.execute('SELECT data,tipo,valor,conta,forma_pagamento FROM transacoes WHERE id=?',(transacao_id,)).fetchone()
    if not row or (movimento_esperado is not None and list(row)!=movimento_esperado):
        raise ConciliacaoError('O lançamento mudou. Abra o Histórico novamente.')
    dados={'id':transacao_id,'movimento':list(row)}
    db.registrar_auditoria('conciliacao_revisao',transacao_id,'manter_separado',dados_depois=dados,
                          origem='telegram',usuario_sessao=usuario,conn=conn)


def marcar_separado(transacao_id,usuario,movimento_esperado):
    with db.fatura_write_transaction() as conn:
        marcar_separado_conn(conn,transacao_id,usuario,movimento_esperado)
