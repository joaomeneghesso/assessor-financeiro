"""Sugestões de lançamento derivadas do histórico (somente leitura).

Nenhuma tabela nova: tudo vem de ``transacoes``. Nada aqui grava; o resultado
apenas preenche o rascunho, que continua exigindo confirmação do titular.

Regras:
- descrição comparada por texto normalizado (sem acento, minúsculas);
- só despesas/receitas reais: pagamento de fatura, transferência e parcelas
  ficam fora;
- Pix, crédito, boleto etc. nunca viram conta; ``destino_pagamento`` não existe
  aqui e nunca é considerado;
- evidência mínima: >= 2 ocorrências entre as últimas ``JANELA`` e >= 60% no
  mesmo par (conta, forma). Sem evidência, nada é sugerido (o fluxo pergunta).
"""
from __future__ import annotations

import unicodedata
from collections import Counter
from datetime import date, timedelta

import database as db

JANELA = 6
MIN_OCORRENCIAS = 2
MIN_PROPORCAO = 0.6
DIAS_FREQUENTES = 90
MAX_FREQUENTES = 5

_NAO_CONTA = {'pix', 'boleto', 'credito', 'debito', 'dinheiro', 'transferencia',
              'entrada', 'nao informada', 'nao informado', 'conta principal', ''}
_FORMAS = {'pix', 'débito', 'crédito', 'dinheiro', 'transferência', 'boleto'}


def _norm(valor) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', str(valor or '').lower())
                   if unicodedata.category(c) != 'Mn').strip()


def _forma(valor) -> str:
    n = _norm(valor)
    for f in _FORMAS:
        if _norm(f) == n:
            return f
    return ''


def _fora_do_escopo(row) -> bool:
    texto = _norm(row['descricao']) + ' ' + _norm(row['categoria'])
    return ('fatura' in texto and 'pag' in texto) or 'transferencia' in _norm(row['categoria']) \
        or 'pagamento de fatura' in texto


def _linhas(tipo: str, limite: int = 2000):
    with db.read_only_mode():
        with db.get_connection() as conn:
            cur = conn.execute(
                'SELECT id, data, tipo, valor, categoria, descricao, conta, forma_pagamento, '
                'parcelas_total FROM transacoes WHERE tipo = ? ORDER BY data DESC, id DESC LIMIT ?',
                (tipo, limite))
            return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def _elegivel(row) -> bool:
    if (row.get('parcelas_total') or 1) > 1:
        return False
    return not _fora_do_escopo(row)


def sugerir(descricao: str, tipo: str) -> dict:
    """Devolve {'conta','forma_pagamento','categoria','amostra'} só com o que tem evidência."""
    chave = _norm(descricao)
    if not chave or tipo not in {'despesa', 'receita'}:
        return {}
    try:
        linhas = [r for r in _linhas(tipo) if _elegivel(r) and _norm(r['descricao']) == chave][:JANELA]
    except Exception:  # leitura de apoio nunca derruba o registro
        return {}
    if len(linhas) < MIN_OCORRENCIAS:
        return {}
    out: dict = {}
    pares = Counter()
    for r in linhas:
        conta = str(r['conta'] or '').strip()
        forma = _forma(r['forma_pagamento'])
        if forma and conta and _norm(conta) not in _NAO_CONTA:
            pares[(conta, forma)] += 1
    if pares:
        # desempate pelo mais recente (ordem de inserção do Counter segue linhas recentes primeiro)
        (conta, forma), n = max(pares.items(), key=lambda kv: (kv[1], -list(pares).index(kv[0])))
        if n / len(linhas) >= MIN_PROPORCAO:
            out['conta'] = conta
            out['forma_pagamento'] = forma
    cats = Counter(str(r['categoria'] or '').strip() for r in linhas if str(r['categoria'] or '').strip())
    if cats:
        cat, n = max(cats.items(), key=lambda kv: (kv[1], -list(cats).index(kv[0])))
        if n / len(linhas) >= MIN_PROPORCAO:
            try:
                from categorias import canonicalizar_categoria
                cat = canonicalizar_categoria(cat) or cat
            except Exception:
                pass
            out['categoria'] = cat
    if out:
        out['amostra'] = len(linhas)
    return out


def ordenar_contas(contas: list[str]) -> list[str]:
    """Mais usadas primeiro (contagem em transacoes), depois alfabética."""
    try:
        with db.read_only_mode():
            with db.get_connection() as conn:
                uso = {}
                for nome, n in conn.execute(
                        'SELECT conta, COUNT(*) FROM transacoes WHERE conta IS NOT NULL GROUP BY conta').fetchall():
                    uso[_norm(nome)] = uso.get(_norm(nome), 0) + n
    except Exception:
        uso = {}
    return sorted(contas, key=lambda c: (-uso.get(_norm(c), 0), _norm(c)))


def frequentes(hoje: date, dias: int = DIAS_FREQUENTES, maximo: int = MAX_FREQUENTES) -> list[dict]:
    """Descrições de despesa mais usadas nos últimos ``dias`` (>= 2 usos).

    Cada item: {'descricao','id','valor','usos'}; ``id`` é o lançamento mais
    recente do grupo (alvo de ('repeat', id)). Determinístico: usos desc,
    mais recente, nome.
    """
    inicio = (hoje - timedelta(days=dias)).isoformat()
    try:
        linhas = [r for r in _linhas('despesa') if _elegivel(r) and inicio <= r['data'] <= hoje.isoformat()]
    except Exception:
        return []
    grupos: dict = {}
    for r in linhas:  # já em ordem decrescente de data/id
        k = _norm(r['descricao'])
        if not k:
            continue
        g = grupos.setdefault(k, {'descricao': str(r['descricao']).strip(), 'id': r['id'],
                                  'valor': r['valor'], 'usos': 0, 'data': r['data']})
        g['usos'] += 1
    itens = [g for g in grupos.values() if g['usos'] >= 2]
    itens.sort(key=lambda g: (-g['usos'], _neg(g['data']), _norm(g['descricao'])))
    return itens[:maximo]


def _neg(iso: str) -> tuple:
    # mais recente primeiro dentro de sort ascendente
    return tuple(-ord(c) for c in iso)


def ultimo_repetivel() -> dict | None:
    """Último lançamento (despesa ou receita) elegível para repetir: não parcelado, não fatura."""
    try:
        with db.read_only_mode():
            with db.get_connection() as conn:
                cur = conn.execute(
                    'SELECT id, data, tipo, valor, categoria, descricao, conta, forma_pagamento, parcelas_total '
                    'FROM transacoes ORDER BY id DESC LIMIT 50')
                cols = [c[0] for c in cur.description]
                for r in cur.fetchall():
                    row = dict(zip(cols, r))
                    if _elegivel(row) and row['conta'] and _forma(row['forma_pagamento']):
                        return row
    except Exception:
        return None
    return None
