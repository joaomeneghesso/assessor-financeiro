"""Busca de lançamentos em todos os meses e troca de categoria em lote (Telegram).

Pedido do titular em 13/11/2026: "buscar bruno" deve achar TODOS os
lançamentos já feitos (antes olhava só o mês atual) e permitir mudar a
categoria de todos de uma vez, com prévia e confirmação, oferecendo depois
aprender a regra para os próximos lançamentos.

Telas montadas com os utilitários do motor (``ui`` = ``globals()`` de
``telegram_experiencia``), sem importar o motor: não cria ciclo de import.

Ações (tuplas de botão):
- ``('busca', termo, periodo, pagina)``: resultado; ``periodo`` = ``'AAAA-MM:AAAA-MM'`` ou ``''`` (todos os meses);
- ``('busca_cat', termo, periodo, pagina)``: escolher a nova categoria;
- ``('busca_cat_ver', termo, periodo, categoria)``: prévia antes → depois;
- ``('busca_cat_ok', termo, periodo, categoria, assinatura)``: grava (só se nada mudou desde a prévia);
- ``('busca_regra', termo, categoria)``: aprende "termo → categoria" para os próximos lançamentos.
"""
import hashlib
import logging
import re

import database as db
import services as svc
from categorias import CATEGORIAS_CANONICAS, canonicalizar_categoria
from consultas_rapidas import _extrair_periodo, resolver_meses, rotulo_periodo

POR_PAGINA = 8
MAX_PREVIA = 15
ACOES = {'busca', 'busca_cat', 'busca_cat_ver', 'busca_cat_ok', 'busca_regra'}


# ----------------------------------------------------------------------------- regras (sem tela)
def interpretar_busca(texto, hoje):
    """'bruno nos últimos 3 meses' -> ('bruno', '2026-09:2026-11'); sem período -> ('bruno', '')."""
    bruto = re.sub(r'\s+', ' ', str(texto or '')).strip()[:80]
    norm = svc.normalizar_busca_texto(bruto).strip(' .?!')
    resto, periodo = _extrair_periodo(norm)
    if periodo is None or resto == norm:
        return bruto, ''
    tipo = periodo['period']
    atual = hoje.strftime('%Y-%m')
    if tipo == 'current_month':
        meses = [atual]
    elif tipo == 'previous_month':
        meses = resolver_meses({'period': 'ultimos_meses', 'n': 2}, hoje)[:1]
    elif tipo == 'current_year':
        meses = resolver_meses({'period': 'ano', 'ano': hoje.year}, hoje)
    else:
        meses = resolver_meses(periodo, hoje)
    if not meses:
        return bruto, ''
    termo = re.sub(r'\s+(?:no|nos|na|nas|em|de|do|da|durante)$', '', resto).strip()
    return termo, f'{meses[0]}:{meses[-1]}'


def _meses_do_periodo(periodo):
    if not periodo:
        return None
    inicio, fim = periodo.split(':')
    return inicio, fim


def buscar(termo, periodo=''):
    """Lançamentos que contêm o termo (descrição, categoria, conta, valor...), do mais recente ao mais antigo."""
    faixa = _meses_do_periodo(periodo)
    with db.read_only_mode():
        todas = [dict(t) for t in db.buscar_todas_transacoes()]
    achados = [t for t in todas if (not termo or svc.transacao_contem_termo(t, termo))
               and (faixa is None or faixa[0] <= str(t.get('data') or '')[:7] <= faixa[1])]
    achados.sort(key=lambda t: (str(t.get('data') or ''), int(t['id'])), reverse=True)
    return achados


def candidatos_categoria(achados, nova_categoria):
    """Despesas encontradas (parcelamentos sempre inteiros) que ainda não estão na nova categoria."""
    despesas = {t['id']: t for t in achados if t.get('tipo') == 'despesa'}
    grupos = {t.get('parcelamento_id') for t in despesas.values() if t.get('parcelamento_id') is not None}
    if grupos:
        with db.read_only_mode():
            for t in map(dict, db.buscar_todas_transacoes()):
                if t.get('parcelamento_id') in grupos:
                    despesas.setdefault(t['id'], t)
    nova = canonicalizar_categoria(nova_categoria, 'Outros')
    itens = [t for t in despesas.values() if t.get('categoria') != nova]
    itens.sort(key=lambda t: (str(t.get('data') or ''), int(t['id'])), reverse=True)
    return nova, itens


def assinatura(itens):
    base = '|'.join(f"{t['id']}:{t.get('categoria')}" for t in sorted(itens, key=lambda t: int(t['id'])))
    return hashlib.sha1(base.encode('utf-8')).hexdigest()[:12]


def categorias_disponiveis():
    usadas = {}
    with db.read_only_mode():
        for t in db.buscar_todas_transacoes():
            if t['tipo'] == 'despesa' and t['categoria']:
                usadas[t['categoria']] = usadas.get(t['categoria'], 0) + 1
    canonicas = [c for c in CATEGORIAS_CANONICAS if c != 'Receita']
    extras = sorted((c for c in usadas if c not in canonicas), key=lambda c: -usadas[c])
    return (canonicas + extras)[:24]


# ----------------------------------------------------------------------------- telas
def _data_br(valor):
    t = str(valor or '')
    return f'{t[8:10]}/{t[5:7]}/{t[:4]}' if re.fullmatch(r'\d{4}-\d{2}-\d{2}.*', t) else t


def _rotulo(ui, engine, periodo):
    faixa = _meses_do_periodo(periodo)
    if faixa is None:
        return 'Todos os meses'
    meses, (a, b) = [], faixa
    while a <= b and len(meses) < 61:
        meses.append(a)
        a = ui['month_shift'](a, 1)
    return rotulo_periodo(meses, engine.date_provider(), ui['month_label'])


def _tela_resultado(ui, engine, key, termo, periodo, pagina):
    Screen, money, safe, plural = ui['Screen'], ui['money'], ui['safe'], ui['plural']
    s = engine.session(key)
    s.search = termo  # o Histórico do mês continua com o mesmo filtro
    achados = buscar(termo, periodo)
    nav = engine.nav('history')
    titulo = f'<b>🔎 Busca: {safe(termo or "todos", 40)}</b>\n<i>{_rotulo(ui, engine, periodo)}</i>'
    if not achados:
        return Screen(titulo + '\n\nNenhum lançamento encontrado.\n\nTente parte do nome (ex.: <i>buscar bruno</i>) '
                      'ou outro período.', [[('📒 Histórico do mês', ('view', 'history'))], *nav])
    despesas = [t for t in achados if t.get('tipo') == 'despesa']
    receitas = [t for t in achados if t.get('tipo') == 'receita']
    linhas = [titulo, '', plural(len(achados), 'lançamento encontrado', 'lançamentos encontrados') + '.']
    if despesas:
        linhas.append(f'Saídas: <b>{money(sum(float(t["valor"] or 0) for t in despesas))}</b>')
    if receitas:
        linhas.append(f'Entradas: <b>{money(sum(float(t["valor"] or 0) for t in receitas))}</b>')
    por_cat = {}
    for t in despesas:
        por_cat[t.get('categoria') or 'Sem categoria'] = por_cat.get(t.get('categoria') or 'Sem categoria', 0) + 1
    if len(por_cat) > 1:
        linhas += ['', '<b>Categorias</b>'] + [f'{safe(c, 30)} · {n}' for c, n in
                                                sorted(por_cat.items(), key=lambda x: -x[1])[:6]]
    paginas = max(1, (len(achados) + POR_PAGINA - 1) // POR_PAGINA)
    pagina = max(0, min(int(pagina or 0), paginas - 1))
    visiveis = achados[pagina * POR_PAGINA:(pagina + 1) * POR_PAGINA]
    linhas.append('')
    rows = []
    for i, t in enumerate(visiveis, pagina * POR_PAGINA + 1):
        sinal = '↗' if t.get('tipo') == 'receita' else '↘'
        linhas.append(f'{sinal} <b>{i}. {safe(t.get("descricao") or "Sem descrição", 34)} · {money(t.get("valor"))}</b>\n'
                      f'{_data_br(t.get("data"))} · {safe(t.get("categoria") or "Sem categoria", 22)} · '
                      f'{safe(t.get("conta") or "sem conta", 18)}')
        rows.append([(f'{i}. ' + ui['cortar'](t.get('descricao') or 'Detalhes', 27), ('transaction', t['id']))])
    if paginas > 1:
        linhas += ['', f'Página {pagina + 1}/{paginas}']
        rows.append([('‹ Anteriores', ('busca', termo, periodo, max(0, pagina - 1))),
                     ('Próximos ›', ('busca', termo, periodo, min(paginas - 1, pagina + 1)))])
    if despesas:
        rows.append([(f'🏷 Mudar categoria de todos ({len(despesas)})', ('busca_cat', termo, periodo, 0))])
    rows.append([('📒 Histórico do mês', ('view', 'history'))])
    return Screen('\n'.join(linhas), rows + nav)


def _tela_escolher_categoria(ui, engine, termo, periodo):
    Screen, safe = ui['Screen'], ui['safe']
    cats = categorias_disponiveis()
    rows = [[(c, ('busca_cat_ver', termo, periodo, c)) for c in cats[i:i + 3]] for i in range(0, len(cats), 3)]
    rows.append([('↩ Voltar à busca', ('busca', termo, periodo, 0))])
    return Screen(f'<b>🏷 Nova categoria</b>\nBusca: {safe(termo or "todos", 40)} · {_rotulo(ui, engine, periodo)}\n\n'
                  'Escolha a categoria para as saídas encontradas. Você verá a prévia antes de qualquer alteração.', rows)


def _tela_previa(ui, engine, termo, periodo, categoria):
    Screen, money, safe, plural = ui['Screen'], ui['money'], ui['safe'], ui['plural']
    nova, itens = candidatos_categoria(buscar(termo, periodo), categoria)
    voltar = [('↩ Voltar à busca', ('busca', termo, periodo, 0))]
    if not itens:
        return Screen(f'<b>🏷 {safe(nova, 30)}</b>\n\nTodas as saídas encontradas já estão em {safe(nova, 30)}. Nada a alterar.', [voltar])
    linhas = [f'<b>✏️ Confirme a alteração</b>', f'Busca: {safe(termo or "todos", 40)} · {_rotulo(ui, engine, periodo)}', '',
              f'{plural(len(itens), "lançamento muda", "lançamentos mudam")} para <b>{safe(nova, 30)}</b>:', '']
    for t in itens[:MAX_PREVIA]:
        linhas.append(f'{_data_br(t.get("data"))} · {safe(t.get("descricao") or "Sem descrição", 30)} · {money(t.get("valor"))}\n'
                      f'   {safe(t.get("categoria") or "Sem categoria", 25)} → {safe(nova, 25)}')
    if len(itens) > MAX_PREVIA:
        linhas.append(f'… e mais {len(itens) - MAX_PREVIA}.')
    if any(t.get('parcelamento_id') is not None for t in itens):
        linhas += ['', 'Parcelamentos mudam inteiros: todas as parcelas entram, mesmo as de outros meses.']
    linhas += ['', 'Valores, datas e contas não mudam. Nada foi alterado ainda.']
    return Screen('\n'.join(linhas), [
        [(f'✅ Confirmar alteração ({len(itens)})', ('busca_cat_ok', termo, periodo, nova, assinatura(itens)))],
        [('✖️ Cancelar', ('busca', termo, periodo, 0))]], sensitive=True)


def _gravar(ui, engine, key, termo, periodo, categoria, assin):
    Screen, safe, plural = ui['Screen'], ui['safe'], ui['plural']
    nova, itens = candidatos_categoria(buscar(termo, periodo), categoria)
    voltar = [('🔎 Ver a busca', ('busca', termo, periodo, 0))]
    if not itens or assinatura(itens) != assin:
        return Screen('⏳ <b>Esta prévia não vale mais</b>\n\nOs lançamentos mudaram desde a prévia. Nada foi alterado.\n'
                      'Abra a busca de novo para ver a prévia atualizada.', [voltar])
    try:
        db.atualizar_categoria_em_lote({t['id']: t.get('categoria') for t in itens}, nova)
    except ValueError as exc:
        return Screen('⏳ ' + safe(str(exc), 200), [voltar])
    texto = [f'✅ <b>Categoria atualizada</b>', '',
             f'{plural(len(itens), "lançamento agora está", "lançamentos agora estão")} em <b>{safe(nova, 30)}</b>.']
    rows = [voltar]
    if termo and len(svc.normalizar_busca_texto(termo)) >= 3:
        texto += ['', f'Quer que os próximos lançamentos com “{safe(termo, 30)}” já venham como {safe(nova, 30)}?']
        rows = [[(f'🧠 Sim, aprender', ('busca_regra', termo, nova))], [('Agora não', ('busca', termo, periodo, 0))]]
    return Screen('\n'.join(texto), rows)


def _aprender(ui, engine, key, termo, categoria):
    Screen, safe = ui['Screen'], ui['safe']
    from categorias_pessoais import salvar_regra
    voltar = [[('🔎 Ver a busca', ('busca', termo, '', 0)), ('🏠 Início', ('view', 'home'))]]
    try:
        regra = salvar_regra(termo, categoria)
        db.registrar_auditoria('regra_categoria_pessoal', None, 'salvar',
                               dados_depois={'expressao': regra['phrase'], 'categoria': regra['category']},
                               origem='telegram', usuario_sessao=str(key))
    except ValueError as exc:
        return Screen(safe(str(exc), 200) + '\n\nNenhuma regra foi criada.', voltar)
    except Exception:
        logging.exception('Busca: falha ao salvar regra pessoal de categoria.')
        return Screen('Não consegui salvar a regra agora. Nenhuma regra foi criada.', voltar)
    return Screen(f'✅ <b>Preferência aprendida</b>\n\n“{safe(regra["phrase"], 40)}” → {safe(regra["category"], 30)}\n\n'
                  'Vale para os próximos lançamentos por texto e áudio. Você pode remover em Regras de categoria.', voltar)


def dispatch(engine, key, action, ui):
    """Ponto único chamado por ``Experience`` (texto "buscar ..." e botões ``busca*``)."""
    kind = action[0]
    if kind == 'buscar_texto':
        termo, periodo = interpretar_busca(action[1], engine.date_provider())
        return _tela_resultado(ui, engine, key, termo, periodo, 0)
    termo, periodo = str(action[1]), str(action[2] or '')
    if kind == 'busca':
        return _tela_resultado(ui, engine, key, termo, periodo, int(action[3]) if len(action) > 3 else 0)
    if kind == 'busca_cat':
        return _tela_escolher_categoria(ui, engine, termo, periodo)
    if kind == 'busca_cat_ver':
        return _tela_previa(ui, engine, termo, periodo, str(action[3]))
    if kind == 'busca_cat_ok':
        return _gravar(ui, engine, key, termo, periodo, str(action[3]), str(action[4]))
    if kind == 'busca_regra':
        return _aprender(ui, engine, key, str(action[1]), str(action[2]))
    raise ValueError('Ação de busca inválida.')
