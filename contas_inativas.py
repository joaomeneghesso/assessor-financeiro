"""Contas desativadas: saem das listas de escolha, mas o histórico, os relatórios e o backup seguem intactos.

Não existe tabela de contas (elas são derivadas dos lançamentos). A lista de desativadas é uma
preferência guardada em auditoria_eventos, como as demais preferências, sem migration.
"""
import json
import unicodedata

import database as db

ENTIDADE = 'contas_inativas'
CHAVE = 'principal'


def normalizar(valor):
    texto = unicodedata.normalize('NFD', str(valor or '').lower())
    return ''.join(c for c in texto if unicodedata.category(c) != 'Mn').strip()


def _ler(conn):
    row = conn.execute(
        'SELECT dados_depois FROM auditoria_eventos WHERE entidade=? AND entidade_id=? ORDER BY id DESC LIMIT 1',
        (ENTIDADE, CHAVE)).fetchone()
    try:
        return [str(x) for x in json.loads(row[0]).get('contas', [])] if row and row[0] else []
    except (ValueError, TypeError, AttributeError):
        return []


def listar(conn=None):
    if conn is None:
        with db.get_connection() as c:
            return _ler(c)
    return _ler(conn)


def esta_inativa(conta, lista=None):
    alvo = normalizar(conta)
    return bool(alvo) and any(normalizar(x) == alvo for x in (listar() if lista is None else lista))


def _alterar(conta, usuario, desativar):
    conta = str(conta or '').strip()
    if not conta:
        raise ValueError('Informe a conta.')
    with db.get_connection() as c:
        c.execute('BEGIN IMMEDIATE')
        antes = _ler(c)
        ja = any(normalizar(x) == normalizar(conta) for x in antes)
        if desativar == ja:
            c.rollback()
            return False
        depois = sorted(set(antes) | {conta}, key=normalizar) if desativar else [
            x for x in antes if normalizar(x) != normalizar(conta)]
        db.registrar_auditoria(ENTIDADE, CHAVE, 'desativada' if desativar else 'reativada',
                               {'contas': antes}, {'contas': depois}, 'telegram', usuario, conn=c)
        c.commit()
        return True


def desativar(conta, usuario=''):
    return _alterar(conta, usuario, True)


def reativar(conta, usuario=''):
    return _alterar(conta, usuario, False)
