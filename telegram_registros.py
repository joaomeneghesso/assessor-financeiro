"""Gravação confirmada, atômica e auditada usando o schema já existente.

Não cria tabelas, não normaliza o histórico e não liquida compromissos.
Uma chave de confirmação identifica um evento, nunca uma descrição/valor.
"""
import calendar
import json
import sqlite3
import re
import unicodedata
from datetime import date, datetime
import relogio
from decimal import Decimal

import database as db
from money import parse_money
from categorias import canonicalizar_categoria
from faturas_competencia import (eh_credito, validar_escolha, exigir_schema, somar_meses)


def validar_campo_textual(campo, valor):
    text = str(valor or '').strip()
    clean = ''.join(c for c in unicodedata.normalize('NFD', text.lower())
                    if unicodedata.category(c) != 'Mn')
    if not text or len(text) > 160 or text.startswith('/'):
        raise ValueError('Informe um texto válido, sem comandos, com até 160 caracteres.')
    if campo in {'conta', 'categoria'}:
        if not any(c.isalpha() for c in text):
            raise ValueError('Informe o nome da '+campo+', não um número.')
        if re.search(r'\b(?:register_expense|register_income)\b', clean):
            raise ValueError('Informe um nome válido, sem identificadores técnicos.')
    if campo == 'conta' and clean in {'pix','debito','credito','dinheiro','boleto','transferencia'}:
        raise ValueError('Informe a conta. A forma de pagamento é um campo separado.')
    return text


def validar_transacao(transacao):
    t = dict(transacao)
    date.fromisoformat(t['data'])
    if t.get('tipo') not in {'receita', 'despesa'}:
        raise ValueError('Escolha entrada ou despesa.')
    t['valor'] = float(parse_money(t['valor']))
    parcelas = t.get('parcelas_total') or 1
    if isinstance(parcelas, bool) or int(parcelas) != parcelas or not 1 <= int(parcelas) <= 60:
        raise ValueError('Use de 1 a 60 parcelas.')
    t['parcelas_total'] = int(parcelas)
    if t['tipo'] == 'receita' and parcelas != 1:
        raise ValueError('Registre cada recebimento separadamente.')
    if parcelas > 1 and t.get('forma_pagamento') != 'crédito':
        raise ValueError('Parcelamento exige a forma crédito.')
    if Decimal(str(t['valor'])) * 100 < parcelas:
        raise ValueError('O total precisa permitir pelo menos um centavo por parcela.')
    for key in ('descricao', 'categoria', 'conta', 'forma_pagamento'):
        t[key] = validar_campo_textual(key, t.get(key))
    allowed = {'pix','débito','crédito','dinheiro','transferência','boleto'}
    if t['forma_pagamento'] not in allowed:
        raise ValueError('Escolha uma forma de pagamento válida.')
    if t['tipo'] == 'receita' and t['forma_pagamento'] not in {'pix','dinheiro','transferência'}:
        raise ValueError('Para recebimentos, escolha Pix, dinheiro ou transferência.')
    # Defesa em profundidade: confirmar_registro grava por conexão própria e não
    # passa por database.inserir_transacao(). Canonize aqui também.
    t['categoria'] = canonicalizar_categoria(t.get('categoria'), 'Outros')
    validar_escolha(t)
    return t


def _auditar(conn, chave, operacao, usuario, antes=None, depois=None, entidade='telegram_registro'):
    conn.execute('''INSERT INTO auditoria_eventos
        (entidade, entidade_id, operacao, dados_antes, dados_depois,
         origem, usuario_sessao, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (entidade, chave, operacao,
         json.dumps(antes, ensure_ascii=False) if antes is not None else None,
         json.dumps(depois, ensure_ascii=False) if depois is not None else None,
         'telegram', usuario, relogio.agora().isoformat(timespec='seconds')))


def _inserir(conn, t):
    campos = ('data', 'tipo', 'valor', 'categoria', 'descricao', 'conta',
              'forma_pagamento', 'mensagem_original', 'criado_em',
              'parcelamento_id', 'parcela_atual', 'parcelas_total', 'valor_total_parcelamento')
    if eh_credito(t):
        exigir_schema(conn)
        campos += ('data_compra', 'competencia_fatura')
    cursor = conn.execute(
        'INSERT INTO transacoes (' + ','.join(campos) + ') VALUES (' +
        ','.join('?' for _ in campos) + ')', [t.get(k) for k in campos])
    return cursor.lastrowid


def confirmar_registro(transacao, chave, usuario):
    """Uma confirmação repetida não insere novamente, mesmo entre processos."""
    t = validar_transacao(transacao)
    if not chave or not usuario:
        raise ValueError('Confirmação sem identificação. Abra Registrar novamente.')
    with db.fatura_write_transaction() as conn:
        conn.row_factory = sqlite3.Row
        evento = conn.execute('''SELECT * FROM auditoria_eventos WHERE entidade=?
            AND entidade_id=? AND operacao=? ORDER BY id LIMIT 1''',
            ('telegram_registro', chave, 'confirmado')).fetchone()
        if evento:
            if evento['usuario_sessao'] != usuario:
                raise ValueError('Esta confirmação pertence a outra sessão.')
            dados = json.loads(evento['dados_depois'])
            if dados['transacao'] != t:
                raise ValueError('A confirmação não corresponde ao lançamento revisado.')
            return dict(dados, repetido=True)
        validar_escolha(t, obrigatoria=True)
        if eh_credito(t):
            exigir_schema(conn)
        total_centavos = int(parse_money(t['valor']) * 100)
        n = t['parcelas_total']
        base, resto = divmod(total_centavos, n)
        inicio = date.fromisoformat(t['data'])
        ids = []
        for i in range(n):
            indice = inicio.year * 12 + inicio.month - 1 + i
            ano, mes0 = divmod(indice, 12)
            dia = min(inicio.day, calendar.monthrange(ano, mes0 + 1)[1])
            row = dict(t, data=date(ano, mes0 + 1, dia).isoformat(),
                       valor=(base + (1 if i < resto else 0)) / 100,
                       criado_em=relogio.agora().isoformat(timespec='seconds'))
            if eh_credito(t):
                row['data_compra'] = t['data']
                row['competencia_fatura'] = somar_meses(t.get('competencia_fatura') or t['data'][:7], i)
            if n > 1:
                row.update(parcelamento_id=ids[0] if ids else None,
                           parcela_atual=i + 1, valor_total_parcelamento=t['valor'])
            row_id = _inserir(conn, row)
            ids.append(row_id)
            if n > 1 and i == 0:
                conn.execute('UPDATE transacoes SET parcelamento_id=? WHERE id=?', (row_id, row_id))
        rows = [dict(conn.execute('SELECT * FROM transacoes WHERE id=?', (i,)).fetchone()) for i in ids]
        if t.get('conciliacao'):
            if len(ids)!=1:
                raise ValueError('A conciliação exige um lançamento individual.')
            from conciliacao import vincular_conn
            vincular_conn(conn,ids[0],t['conciliacao'],chave,usuario)
        elif t.get('sem_vinculo_confirmado'):
            from conciliacao import marcar_separado_conn
            for ident in ids:
                marcar_separado_conn(conn,ident,usuario)
        dados = {'ids': ids, 'transacao': t, 'linhas': rows}
        _auditar(conn, chave, 'confirmado', usuario, depois=dados)
        return dict(dados, repetido=False)


def _dependencia_posterior(conn, evento, linhas):
    """Mensagem de recusa quando algo gravado DEPOIS do registro depende dele.

    - Compra no crédito: pagamento/crédito/ajuste da mesma fatura (cartão +
      competência) criado ou alterado depois da confirmação. Remover a compra
      deixaria o pagamento sobrando (fatura com saldo credor indevido).
    - Lançamento em caixa: "saldo atual" confirmado depois para a mesma conta
      e mês. A base derivada já absorveu o lançamento; removê-lo contaria o
      valor duas vezes.
    O marco é o próprio evento de auditoria do registro (id e criado_em).
    """
    from compromissos import normalizar_conta_fatura
    from services import normalizar_conta_caixa, mesma_conta_saldo
    marco = str(evento['criado_em'] or '').replace(' ', 'T')
    for linha in linhas:
        if eh_credito(linha):
            competencia = linha.get('competencia_fatura') or str(linha.get('data') or '')[:7]
            cartao = normalizar_conta_fatura(linha.get('conta'))
            for mov in conn.execute('SELECT conta_cartao, criado_em, atualizado_em FROM fatura_movimentos WHERE ano_mes=?',
                                    (competencia,)).fetchall():
                if normalizar_conta_fatura(mov['conta_cartao']) != cartao:
                    continue
                quando = max(str(mov['criado_em'] or ''), str(mov['atualizado_em'] or '')).replace(' ', 'T')
                if quando >= marco:
                    return ('Não desfiz: a fatura dessa compra recebeu pagamento ou ajuste depois do registro. '
                            'Revise a fatura e o lançamento pelo Histórico antes de excluir. Nada foi alterado.')
        else:
            mes = str(linha.get('data') or '')[:7]
            conta = normalizar_conta_caixa(linha.get('conta'))
            for (entidade_id,) in conn.execute("SELECT entidade_id FROM auditoria_eventos "
                    "WHERE entidade='saldo_conta' AND operacao='ajuste_atual_confirmado' "
                    "AND id>? AND entidade_id LIKE ?", (evento['id'], mes + ':%')).fetchall():
                if mesma_conta_saldo(str(entidade_id).split(':', 1)[1], conta):
                    return ('Não desfiz: o saldo atual dessa conta foi ajustado depois do registro e já considera '
                            'este lançamento. Revise pelo Histórico e confira o saldo antes de excluir. Nada foi alterado.')
    return None


def desfazer_registro(chave, usuario):
    """Remove só as linhas inalteradas do evento, em uma única transação."""
    with db.fatura_write_transaction() as conn:
        conn.row_factory = sqlite3.Row
        evento = conn.execute('''SELECT * FROM auditoria_eventos WHERE entidade=?
            AND entidade_id=? AND operacao=? ORDER BY id LIMIT 1''',
            ('telegram_registro', chave, 'confirmado')).fetchone()
        if not evento or evento['usuario_sessao'] != usuario:
            raise ValueError('Não encontrei esse registro nesta sessão.')
        anterior = conn.execute('''SELECT id FROM auditoria_eventos WHERE entidade=?
            AND entidade_id=? AND operacao=?''',
            ('telegram_registro', chave, 'desfeito')).fetchone()
        if anterior:
            return False
        dados = json.loads(evento['dados_depois'])
        for esperada in dados['linhas']:
            atual = conn.execute('SELECT * FROM transacoes WHERE id=?', (esperada['id'],)).fetchone()
            esperada = dict(esperada)
            if atual:
                for campo in ('data_compra', 'competencia_fatura'):
                    if campo in atual.keys():
                        esperada.setdefault(campo, None)
            if not atual or dict(atual) != esperada:
                raise ValueError('Esse lançamento foi alterado. Revise pelo Histórico antes de excluir.')
        dependencia = _dependencia_posterior(conn, evento, dados['linhas'])
        if dependencia:
            raise ValueError(dependencia)
        from conciliacao import listar_vinculos, desvincular_conn
        for vinculo in listar_vinculos(conn):
            if vinculo['transacao_id'] in dados['ids']:
                desvincular_conn(conn,vinculo['chave'],usuario)
        conn.executemany('DELETE FROM transacoes WHERE id=?', [(i,) for i in dados['ids']])
        _auditar(conn, chave, 'desfeito', usuario, antes=dados, depois={'ids': dados['ids']})
        return True


def confirmar_pagamento_fatura(dados, chave, usuario):
    """Confirma um pagamento de fatura de forma idempotente e revalidada.

    A chave identifica *esta confirmação* (não descrição/valor). Antes de gravar,
    o saldo atual da fatura precisa continuar igual ao que foi mostrado na prévia.
    Isso impede que um botão antigo liquide uma fotografia financeira diferente.
    """
    if not chave or not usuario:
        raise ValueError('Confirmação sem identificação. Abra a fatura novamente.')

    from services import calcular_resumo_fatura, nome_conta_fatura_padrao

    req = dict(dados or {})
    mes = str(req.get('ano_mes') or '').strip()
    conta_cartao = nome_conta_fatura_padrao(str(req.get('conta_cartao') or '').strip())
    conta_origem = nome_conta_fatura_padrao(str(req.get('conta_origem') or '').strip())
    modo = str(req.get('modo') or '').strip()
    valor = float(parse_money(req.get('valor') or 0))
    saldo_esperado = round(float(req.get('saldo_esperado') or 0), 2)
    data_movimento = str(req.get('data_movimento') or relogio.hoje().isoformat())
    date.fromisoformat(data_movimento)

    if not mes or len(mes) != 7:
        raise ValueError('Competência inválida. Abra a fatura novamente.')
    if not conta_cartao or not conta_origem:
        raise ValueError('Informe a fatura e a conta pagadora.')
    if modo not in {'total', 'parcial'}:
        raise ValueError('Tipo de pagamento inválido. Abra a fatura novamente.')
    if valor <= 0:
        raise ValueError('O valor do pagamento precisa ser maior que zero.')

    pedido = {
        'ano_mes': mes,
        'conta_cartao': conta_cartao,
        'conta_origem': conta_origem,
        'modo': modo,
        'valor': round(valor, 2),
        'saldo_esperado': saldo_esperado,
        'data_movimento': data_movimento,
    }

    with db.fatura_write_transaction() as conn:
        conn.row_factory = sqlite3.Row
        evento = conn.execute('''SELECT * FROM auditoria_eventos WHERE entidade=?
            AND entidade_id=? AND operacao=? ORDER BY id LIMIT 1''',
            ('telegram_fatura', chave, 'confirmado')).fetchone()
        if evento:
            if evento['usuario_sessao'] != usuario:
                raise ValueError('Esta confirmação pertence a outra sessão.')
            salvo = json.loads(evento['dados_depois'])
            if salvo.get('pedido') != pedido:
                raise ValueError('A confirmação não corresponde à fatura revisada.')
            return dict(salvo, repetido=True)

        antes = calcular_resumo_fatura(mes, conta_cartao)
        saldo_atual = round(float(antes.get('saldo_restante') or 0), 2)
        if abs(saldo_atual - saldo_esperado) > .005:
            raise ValueError('O saldo da fatura mudou desde a prévia. Abra a fatura novamente antes de confirmar.')
        if saldo_atual <= .005:
            raise ValueError('Essa fatura não possui saldo pendente para pagamento.')
        if modo == 'total':
            valor_gravado = saldo_atual
        else:
            if round(valor, 2) - saldo_atual > .005:
                raise ValueError('O pagamento informado é maior que o saldo atual da fatura.')
            valor_gravado = round(valor, 2)

        mov_id = db.inserir_fatura_movimento_conn(conn, {
            'ano_mes': mes,
            'conta_cartao': conta_cartao,
            'tipo_movimento': 'pagamento_total' if modo == 'total' else 'pagamento_parcial',
            'valor': valor_gravado,
            'data_movimento': data_movimento,
            'conta_origem': conta_origem,
            'descricao': 'Pagamento confirmado pelo fluxo revisado do Telegram',
            'mensagem_original': None,
        })
        mov = conn.execute('SELECT * FROM fatura_movimentos WHERE id=?', (mov_id,)).fetchone()
        db.registrar_auditoria(
            'fatura_movimento', mov_id, 'criacao', None, dict(mov),
            'telegram', usuario, conn=conn,
        )
        resultado = {
            'pedido': pedido,
            'movimento_id': mov_id,
            'valor_gravado': valor_gravado,
            'saldo_anterior': saldo_atual,
            'saldo_restante': round(max(0.0, saldo_atual - valor_gravado), 2),
        }
        _auditar(conn, chave, 'confirmado', usuario, depois=resultado, entidade='telegram_fatura')
        return dict(resultado, repetido=False)


# ---------------------------------------------------------------------------
# Fase 2 (P5/P6): pós-salvar, categoria com confirmação e duplicata útil.
# ---------------------------------------------------------------------------
JANELA_DESFAZER_MIN = 30


def _norm_texto(valor):
    texto = unicodedata.normalize('NFD', str(valor or '').lower())
    return re.sub(r'\s+', ' ', ''.join(c for c in texto if unicodedata.category(c) != 'Mn')).strip()


def _centavos(valor):
    return int(parse_money(valor) * 100)


def buscar_duplicata(t, janela_dias=1):
    """Somente leitura. Lançamento existente que parece o mesmo que `t`, ou None.

    Mesma descrição normalizada, mesmo valor (centavos), mesma conta e forma, em
    até `janela_dias` de diferença. Parcelas posteriores à primeira nunca contam;
    a 1ª parcela é comparada pelo total da compra. Só avisa; nunca bloqueia.
    """
    try:
        dia = date.fromisoformat(t['data'])
        alvo = _centavos(t['valor'])
    except (KeyError, ValueError, TypeError, ArithmeticError):
        return None
    ini = (dia.toordinal() - janela_dias)
    fim = (dia.toordinal() + janela_dias)
    with db.get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute('SELECT * FROM transacoes WHERE data BETWEEN ? AND ? AND tipo=? ORDER BY data DESC, id DESC',
                            (date.fromordinal(ini).isoformat(), date.fromordinal(fim).isoformat(), t.get('tipo'))).fetchall()
    melhores = []
    for r in rows:
        r = dict(r)
        if int(r.get('parcela_atual') or 1) > 1:
            continue
        try:
            if _centavos(r.get('valor_total_parcelamento') or r['valor']) != alvo:
                continue
        except (ValueError, TypeError, ArithmeticError):
            continue
        if _norm_texto(r.get('descricao')) != _norm_texto(t.get('descricao')):
            continue
        if _norm_texto(r.get('conta')) != _norm_texto(t.get('conta')):
            continue
        if _norm_texto(r.get('forma_pagamento')) != _norm_texto(t.get('forma_pagamento')):
            continue
        melhores.append((abs(date.fromisoformat(r['data']).toordinal() - dia.toordinal()), -r['id'], r))
    return min(melhores, key=lambda x: x[:2])[2] if melhores else None


def _linhas_inalteradas(conn, dados):
    for esperada in dados['linhas']:
        atual = conn.execute('SELECT * FROM transacoes WHERE id=?', (esperada['id'],)).fetchone()
        esperada = dict(esperada)
        if atual:
            for campo in ('data_compra', 'competencia_fatura'):
                if campo in atual.keys():
                    esperada.setdefault(campo, None)
        if not atual or dict(atual) != esperada:
            return False
    return True


def evento_registro_recente(transacao_id, usuario, agora=None):
    """Chave do evento `telegram_registro` que criou a linha, se ainda dá para desfazer pela barra.

    Exige: evento da própria sessão, dentro de JANELA_DESFAZER_MIN, sem desfeito e
    com todas as linhas inalteradas. Somente leitura; o desfazer real continua
    sendo `desfazer_registro` (que revalida tudo e audita dados_antes).
    """
    agora = agora or relogio.agora()
    with db.get_connection() as conn:
        conn.row_factory = sqlite3.Row
        eventos = conn.execute('''SELECT * FROM auditoria_eventos WHERE entidade=? AND operacao=?
            AND usuario_sessao=? ORDER BY id DESC LIMIT 100''', ('telegram_registro', 'confirmado', usuario)).fetchall()
        for ev in eventos:
            try:
                dados = json.loads(ev['dados_depois'])
            except (TypeError, ValueError):
                continue
            if int(transacao_id) not in [int(i) for i in dados.get('ids', [])]:
                continue
            try:
                quando = datetime.fromisoformat(str(ev['criado_em']))
            except ValueError:
                return None
            if (agora - quando).total_seconds() > JANELA_DESFAZER_MIN * 60:
                return None
            if conn.execute('SELECT 1 FROM auditoria_eventos WHERE entidade=? AND entidade_id=? AND operacao=?',
                            ('telegram_registro', ev['entidade_id'], 'desfeito')).fetchone():
                return None
            return ev['entidade_id'] if _linhas_inalteradas(conn, dados) else None
    return None


def motivo_bloqueio_data(transacao):
    """Por que a data deste lançamento não pode ser corrigida aqui (None = pode).

    Parcelas e compras no crédito ficam de fora: a data define a fatura (competência)
    e a série de parcelas; para elas o caminho seguro é desfazer e registrar de novo.
    """
    t = dict(transacao)
    if int(t.get('parcelas_total') or 1) > 1 or t.get('parcelamento_id'):
        return 'Lançamento parcelado: a data das parcelas segue a compra. Para mudar, desfaça o parcelamento e registre de novo.'
    if eh_credito(t):
        return 'Compra no crédito: a data define em qual fatura ela entra. Para mudar, desfaça e registre de novo escolhendo a fatura certa.'
    return None


def corrigir_data_registro(transacao_id, nova_data, chave, usuario, data_esperada, hoje=None):
    """Troca só a data, uma vez por `chave`, com auditoria antes/depois na mesma transação.

    Recusa conciliado, parcelado, crédito, data futura e lançamento que mudou desde a prévia.
    Retorna True ao alterar e False se esta confirmação já havia sido aplicada.
    """
    if not chave or not usuario:
        raise ValueError('Confirmação sem identificação. Abra o lançamento novamente.')
    nova = date.fromisoformat(str(nova_data)).isoformat()
    if hoje is not None and nova > hoje.isoformat():
        raise ValueError('A data não pode ser depois de hoje. Para algo que ainda vai acontecer, use uma previsão.')
    with db.fatura_write_transaction() as conn:
        conn.row_factory = sqlite3.Row
        feito = conn.execute('SELECT usuario_sessao FROM auditoria_eventos WHERE entidade=? AND entidade_id=? AND operacao=?',
                             ('telegram_data', chave, 'data_alterada')).fetchone()
        if feito:
            if feito['usuario_sessao'] != usuario:
                raise ValueError('Esta confirmação pertence a outra sessão.')
            return False
        atual = conn.execute('SELECT * FROM transacoes WHERE id=?', (int(transacao_id),)).fetchone()
        if not atual:
            raise ValueError('Esse lançamento não existe mais.')
        from conciliacao import bloquear_alteracao_transacoes
        bloquear_alteracao_transacoes(conn, [atual['id']])
        motivo = motivo_bloqueio_data(atual)
        if motivo:
            raise ValueError(motivo)
        if str(atual['data']) != str(data_esperada):
            raise ValueError('Esse lançamento mudou depois da prévia. Abra o lançamento novamente.')
        if str(atual['data']) == nova:
            raise ValueError('O lançamento já está nessa data.')
        antes = dict(atual)
        conn.execute('UPDATE transacoes SET data=? WHERE id=?', (nova, atual['id']))
        depois = dict(conn.execute('SELECT * FROM transacoes WHERE id=?', (atual['id'],)).fetchone())
        _auditar(conn, chave, 'data_alterada', usuario, antes=antes, depois=depois, entidade='telegram_data')
        return True


def corrigir_categoria_registro(transacao_id, nova_categoria, chave, usuario, categoria_esperada):
    """Troca só a categoria, uma vez por `chave`, com auditoria antes/depois.

    Retorna True ao alterar e False se esta mesma confirmação já havia sido aplicada.
    Recusa lançamento conciliado e lançamento que mudou desde a prévia.
    """
    if not chave or not usuario:
        raise ValueError('Confirmação sem identificação. Abra o lançamento novamente.')
    nova = canonicalizar_categoria(validar_campo_textual('categoria', nova_categoria), 'Outros')
    with db.fatura_write_transaction() as conn:
        conn.row_factory = sqlite3.Row
        feito = conn.execute('SELECT usuario_sessao FROM auditoria_eventos WHERE entidade=? AND entidade_id=? AND operacao=?',
                             ('telegram_categoria', chave, 'categoria_alterada')).fetchone()
        if feito:
            if feito['usuario_sessao'] != usuario:
                raise ValueError('Esta confirmação pertence a outra sessão.')
            return False
        atual = conn.execute('SELECT * FROM transacoes WHERE id=?', (int(transacao_id),)).fetchone()
        if not atual:
            raise ValueError('Esse lançamento não existe mais.')
        from conciliacao import bloquear_alteracao_transacoes
        bloquear_alteracao_transacoes(conn, [atual['id']])
        if _norm_texto(atual['categoria']) != _norm_texto(categoria_esperada):
            raise ValueError('Esse lançamento mudou depois da prévia. Abra o lançamento novamente.')
        if _norm_texto(atual['categoria']) == _norm_texto(nova):
            raise ValueError('O lançamento já está nessa categoria.')
        antes = dict(atual)
        conn.execute('UPDATE transacoes SET categoria=? WHERE id=?', (nova, atual['id']))
        depois = dict(conn.execute('SELECT * FROM transacoes WHERE id=?', (atual['id'],)).fetchone())
        _auditar(conn, chave, 'categoria_alterada', usuario, antes=antes, depois=depois, entidade='telegram_categoria')
        return True
