"""Ativar/desligar "valor variável" num fixo e sugerir o histórico (camada de ações).

Usado pela interface (``fixos_interface``). Grava só em ``auditoria_eventos``
(entidade ``fixo_variavel``), depois de prévia e confirmação na tela; nunca altera
lançamentos. Regras em ``fixos_variaveis``; leitura do estado em ``conciliacao``.
"""
import hashlib

import conciliacao as conc
import database as db
import fixos_variaveis as fv


def _limpar_cache_da_consulta():
    from consulta_cache import cache_atual
    cache = cache_atual()
    if cache is not None:
        cache.clear()  # a mesma consulta não pode seguir com o estado antigo


def eh_variavel(compromisso_id):
    return str(compromisso_id) in conc.fixos_variaveis_ativos()


def estado(compromisso_id):
    eventos = db.listar_auditoria(entidade=fv.ENTIDADE, entidade_id=str(compromisso_id), limite=1)
    return fv.estados_de_eventos(eventos).get(str(compromisso_id))


def candidatos(compromisso, ate_mes):
    return fv.candidatos_de(db.buscar_todas_transacoes(), compromisso, ate_mes)


def assinatura(transacoes):
    base = '|'.join(f"{t['id']}:{t['valor']}" for t in sorted(transacoes, key=lambda t: int(t['id'])))
    return hashlib.sha1(base.encode('utf-8')).hexdigest()[:10]


def ativar(compromisso_id, historico_ids, usuario=''):
    c = db.buscar_compromisso_por_id(int(compromisso_id))
    if not c or not c['ativo']:
        raise fv.FixoVariavelErro('Fixo não encontrado ou pausado.')
    motivo = fv.elegivel(c)
    if motivo:
        raise fv.FixoVariavelErro(motivo)
    antes = estado(compromisso_id)
    db.registrar_auditoria(fv.ENTIDADE, str(compromisso_id), 'ativado', antes,
                           {'variavel': True, 'historico': sorted({int(i) for i in historico_ids})},
                           'telegram', str(usuario or ''))
    _limpar_cache_da_consulta()


def desativar(compromisso_id, usuario=''):
    antes = estado(compromisso_id)
    if not antes:
        raise fv.FixoVariavelErro('Este fixo já não é variável.')
    db.registrar_auditoria(fv.ENTIDADE, str(compromisso_id), 'desativado', antes, {'variavel': False},
                           'telegram', str(usuario or ''))
    _limpar_cache_da_consulta()


def previsao(compromisso, mes, historico=None):
    """(valor, meses) da estimativa para ``mes``; ``historico`` (lançamentos) simula antes de gravar."""
    c = dict(compromisso)
    if historico is None:
        return conc.estimativa_fixo_variavel(c['id'], mes, c['valor'])
    baixas = {}
    for v in conc.listar_vinculos():
        if v['compromisso_id'] == int(c['id']):
            baixas[v['mes']] = baixas.get(v['mes'], 0) + v['centavos']
    return fv.estimativa(fv.historico_por_mes(historico), baixas, mes, c['valor'])
