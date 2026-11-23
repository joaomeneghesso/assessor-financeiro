"""'Quanto vou pagar de X': faturas dos cartões ou contas de uma categoria (pedido de 19/11/2026).

- "quanto vou pagar de cartão / cartão de crédito / faturas": soma das faturas de
  todos os cartões (Itaú, Mercado Pago, Infinitepay, Nubank...) — total do mês, já
  pago e o que falta, cartão a cartão;
- "quanto vou pagar de moradia": fixos e compromissos da categoria (condomínio, IPTU,
  IPTV, internet, luz ≈ estimada) — total, já pago, falta; fixos da categoria pagos
  no crédito aparecem à parte (já estão dentro das faturas; não são somados de novo);
- períodos: "em dezembro", "nos próximos 3 meses" (``consultas_rapidas``).

Só leitura e mesma fonte do A pagar (``montar_itens_checklist_mes`` +
``aplicar_status_checklist``): os números batem com a tela A pagar. Telas montadas
com os utilitários do motor (``ui`` = ``globals()``), sem importá-lo.
"""
import database as db
import services as svc
from consulta_cache import contexto_consulta

_CARTAO = {'cartao', 'cartoes', 'cartao de credito', 'cartoes de credito', 'credito', 'fatura', 'faturas',
           'fatura do cartao', 'faturas do cartao', 'faturas dos cartoes', 'cartao credito'}


def _norm(texto):
    return svc.normalizar_busca_texto(str(texto or '')).strip()


def _meses(inicio, fim):
    meses, (a, m) = [], (int(inicio[:4]), int(inicio[5:7]))
    while f'{a:04d}-{m:02d}' <= fim and len(meses) < 24:
        meses.append(f'{a:04d}-{m:02d}')
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return meses


def _mesma_categoria(categoria, termo):
    c, t = _norm(categoria), _norm(termo)
    return bool(c) and (c == t or (len(t) >= 4 and (c.startswith(t) or t.startswith(c))))


def _dia(item):
    d = str(item.get('data') or item.get('data_original') or '')
    return f'{d[8:10]}/{d[5:7]}' if len(d) >= 10 else 'sem data'


def itens_do_mes(mes):
    with db.read_only_mode(), contexto_consulta():
        return svc.aplicar_status_checklist(mes, svc.montar_itens_checklist_mes(mes, modo='geral'))


def resumo_faturas(itens, so_cartao=None):
    """[(nome, total, pago, falta, item)] das faturas do mês (opcionalmente de um cartão)."""
    out = []
    for i in itens:
        if i.get('grupo') != 'bancos' or (so_cartao and _norm(i.get('nome')) != so_cartao):
            continue
        falta = 0.0 if i.get('status') == 'pago' else max(0.0, float(i.get('saldo_restante', i.get('valor')) or 0))
        pago = float(i.get('pagamentos_fatura') or 0)
        total = max(float(i.get('valor_bruto') or 0), pago + falta)
        if total > 0.005 or pago > 0.005:
            out.append((i.get('nome') or 'Cartão', total, pago, falta, i))
    return sorted(out, key=lambda x: _norm(x[0]))


def resumo_categoria(itens, termo, mes=None):
    """[(nome, valor, pago?, estimado?, item)] dos fixos/compromissos da categoria no mês.

    Em aberto vem do A pagar; pago vem das baixas (vínculos), porque depois da baixa o
    A pagar troca o item do fixo pelo lançamento do pagamento. Cada compromisso entra
    uma vez como pago (marcação antiga no A pagar OU baixa); parcial = falta + pago.
    """
    out, pagos_ids = [], set()
    for i in itens:
        if i.get('grupo') == 'bancos' or i.get('origem') != 'compromisso' or not _mesma_categoria(i.get('categoria'), termo):
            continue
        pago = i.get('status') == 'pago'
        if pago:
            pagos_ids.add(i.get('id'))
        valor = float(i.get('valor_conciliado') or i.get('valor_original') or i.get('valor') or 0) if pago else float(i.get('valor') or 0)
        out.append((i.get('nome') or 'Conta', valor, pago, bool(i.get('valor_estimado')), i))
    if mes:
        import conciliacao as conc
        for v in conc.listar_vinculos():
            if v['mes'] != mes or v['compromisso_id'] in pagos_ids:
                continue
            c = db.buscar_compromisso_por_id(v['compromisso_id'])
            if c is None or not _mesma_categoria(dict(c)['categoria'], termo) or 'credito' in _norm(dict(c)['forma_pagamento']):
                continue
            out.append((dict(c)['nome'], int(v['centavos']) / 100, True, False, {'data': v['data'], 'id': v['compromisso_id']}))
    return sorted(out, key=lambda x: (str(x[4].get('data') or ''), _norm(x[0])))


def _credito_da_categoria(termo):
    return [dict(c) for c in db.listar_compromissos(tipo='fixo')
            if dict(c)['ativo'] and 'credito' in _norm(dict(c)['forma_pagamento']) and _mesma_categoria(dict(c)['categoria'], termo)]


def _tela_faturas(ui, engine, meses, por_mes, so_cartao):
    Screen, money, safe, label = ui['Screen'], ui['money'], ui['safe'], ui['month_label']
    titulo = f'💳 Fatura {so_cartao.title()}' if so_cartao else '💳 Faturas dos cartões'
    periodo = label(meses[0]) if len(meses) == 1 else f'{label(meses[0])} a {label(meses[-1])}'
    linhas, rows = [f'<b>{titulo}</b>', f'<i>{periodo}</i>', ''], []
    tot = pag = fal = 0.0
    for mes in meses:
        res = resumo_faturas(por_mes[mes], so_cartao)
        t, p, f = sum(x[1] for x in res), sum(x[2] for x in res), sum(x[3] for x in res)
        tot, pag, fal = tot + t, pag + p, fal + f
        if len(meses) > 1:
            linhas.append(f'{label(mes)} · falta <b>{money(f)}</b> (total {money(t)})')
            continue
        for nome, total, pago, falta, item in res:
            if falta <= 0.005:
                linhas.append(f'✅ <b>{safe(nome, 30)}</b> · paga ({money(pago or total)})')
            else:
                linhas.append(f'• <b>{safe(nome, 30)}</b> · vence {_dia(item)} · <b>{money(falta)}</b>'
                              + (f' (já pago {money(pago)})' if pago > 0.005 else ''))
                rows.append([(f'{ui["cortar"](nome, 24)} · ver fatura', ('pay_account_detail', item.get('conta') or nome, mes))])
    if tot <= 0.005 and pag <= 0.005:
        linhas.append('Nenhuma fatura com valor nesse período.')
    else:
        linhas += ['', f'💰 Falta pagar: <b>{money(fal)}</b>', f'Total das faturas: {money(tot)} · já pago: {money(pag)}',
                   '', '<i>Fixos no crédito (assinaturas etc.) já estão dentro dessas faturas.</i>']
    rows.append([('🧾 A pagar', ('view', 'pay'))])
    return Screen('\n'.join(linhas), rows + engine.nav('pay'))


def _tela_categoria(ui, engine, termo, meses, por_mes):
    Screen, money, safe, label = ui['Screen'], ui['money'], ui['safe'], ui['month_label']
    periodo = label(meses[0]) if len(meses) == 1 else f'{label(meses[0])} a {label(meses[-1])}'
    achados = {mes: resumo_categoria(por_mes[mes], termo, mes) for mes in meses}
    cartao = _credito_da_categoria(termo)
    if not any(achados.values()) and cartao:
        return Screen(f'<b>🏷 {safe(cartao[0]["categoria"], 30)} · a pagar</b>\n<i>{periodo}</i>\n\nNada a pagar fora do cartão nessa categoria.\n\n'
                      '<i>No cartão (já dentro das faturas, não somado aqui): '
                      + safe(', '.join(f'{c["nome"]} {money(c["valor"])}' for c in cartao), 200)
                      + '.</i>\n\nPara o total das faturas, pergunte <i>quanto vou pagar de cartão</i>.',
                      [[('🧾 A pagar', ('view', 'pay')), ('📌 Fixos', ('fixed_list', 0))], *engine.nav('pay')])
    if not any(achados.values()):
        cats = sorted({str(i.get('categoria')) for itens in por_mes.values() for i in itens
                       if i.get('origem') == 'compromisso' and i.get('categoria')})
        return Screen(f'<b>🔎 A pagar de “{safe(termo, 30)}”</b>\n<i>{periodo}</i>\n\nNão encontrei contas previstas nessa categoria.'
                      + (f'\n\nCategorias com contas previstas: {safe(", ".join(cats), 200)}.' if cats else '')
                      + '\n\nPara as faturas dos cartões, pergunte <i>quanto vou pagar de cartão</i>.',
                      [[('🧾 A pagar', ('view', 'pay')), ('📌 Fixos', ('fixed_list', 0))], *engine.nav('pay')])
    nome_cat = next(x[4].get('categoria') for v in achados.values() for x in v)
    linhas, rows = [f'<b>🏷 {safe(nome_cat, 30)} · a pagar</b>', f'<i>{periodo}</i>', ''], []
    total = pago = 0.0
    if len(meses) == 1:
        for nome, valor, quitado, estimado, item in achados[meses[0]]:
            total += valor
            if quitado:
                pago += valor
                linhas.append(f'✅ {safe(nome, 30)} · pago {money(valor)}')
            else:
                linhas.append(f'• <b>{safe(nome, 30)}</b> · vence {_dia(item)} · <b>{"≈ " if estimado else ""}{money(valor)}</b>')
                code = item.get('chave') or item.get('codigo_origem') or item.get('codigo')
                rows.append([(ui['cortar'](nome, 27), ('detail_obligation', code, meses[0]))])
    else:
        por_conta = {}
        for mes in meses:
            for nome, valor, quitado, estimado, item in achados[mes]:
                total += valor
                pago += valor if quitado else 0.0
                c = por_conta.setdefault(nome, [0.0, 0, False])
                c[0] += valor; c[1] += 1; c[2] = c[2] or estimado
        for mes in meses:
            linhas.append(f'{label(mes)} · {money(sum(x[1] for x in achados[mes]))}')
        linhas += [''] + [f'• {safe(nome, 30)} · {"≈ " if est else ""}{money(v)} ({n} {"mês" if n == 1 else "meses"})'
                          for nome, (v, n, est) in sorted(por_conta.items())]
    linhas += ['', f'💰 Falta pagar: <b>{money(total - pago)}</b>', f'Total: {money(total)} · já pago: {money(pago)}']
    if any(x[3] for v in achados.values() for x in v):
        linhas.append('<i>≈ valor estimado (conta de valor variável: média dos 3 últimos meses).</i>')
    if cartao:
        linhas += ['', '<i>No cartão (já dentro das faturas, não somado aqui): '
                   + safe(', '.join(f'{c["nome"]} {money(c["valor"])}' for c in cartao), 200) + '.</i>']
    rows.append([('🧾 A pagar', ('view', 'pay')), ('📌 Fixos', ('fixed_list', 0))])
    return Screen('\n'.join(linhas), rows + engine.nav('pay'))


def dispatch(engine, key, action, ui):
    if action[0] != 'pagar_cat':
        raise ValueError('Consulta a pagar inválida.')
    termo, inicio, fim = str(action[1] or ''), str(action[2]), str(action[3])
    meses = _meses(inicio, fim) or [engine.date_provider().strftime('%Y-%m')]
    engine.session(key).month = meses[0]
    por_mes = {mes: itens_do_mes(mes) for mes in meses}
    t = _norm(termo)
    if t in _CARTAO or t.startswith('fatura') or t.startswith('cartao'):
        cartoes = {_norm(i.get('nome')) for itens in por_mes.values() for i in itens if i.get('grupo') == 'bancos'}
        so = next((c for c in cartoes if c and c in t.split(' ', 1)[-1] and t not in _CARTAO), None)
        return _tela_faturas(ui, engine, meses, por_mes, so)
    if t in {_norm(i.get('nome')) for itens in por_mes.values() for i in itens if i.get('grupo') == 'bancos'}:
        return _tela_faturas(ui, engine, meses, por_mes, t)
    return _tela_categoria(ui, engine, termo, meses, por_mes)
