"""Apresentação Telegram sem I/O, IA ou regras financeiras."""
import html
import re


_SUPERSCRIPT_DIGITS = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')


def superscript_number(value):
    """Número inteiro não negativo em algarismos sobrescritos Unicode."""
    number = int(value)
    if number < 0:
        raise ValueError('Contagem não pode ser negativa.')
    return str(number).translate(_SUPERSCRIPT_DIGITS)


# Vocabulário visual único. Ícones descrevem a função; nunca dependem do valor.
TITLE_ICONS = (
    ('início', '🏠'), ('menu', '🧭'), ('mais recursos', '🧭'), ('registrar', '➕'), ('saldo', '🏦'), ('como o saldo', '🧮'),
    ('a pagar', '🧾'), ('quanto vou pagar', '💳'), ('fatura', '💳'),
    ('fixos', '🔁'), ('pagamentos que se repetem', '🔁'),
    ('seus movimentos', '📒'), ('histórico', '📒'), ('lançamento', '📒'),
    ('seu dinheiro', '📊'), ('análise', '📊'), ('categoria', '🏷'),
    ('orçamento', '🎯'), ('seu plano', '🎯'), ('sua agenda', '📅'),
    ('agenda', '📅'), ('período', '📅'), ('alerta', '🔔'),
    ('concilia', '🔗'), ('revis', '🔎'), ('atenção', '🔎'),
    ('confirm', '✅'), ('confira antes', '📝'), ('simulação', '🔮'), ('registro salvo', '✅'), ('ajuste de saldos concluído', '✅'),
    ('editar', '✏️'), ('ajustar', '✏️'), ('desfazer', '↩️'),
    ('ajuda', '💡'), ('guia', '💡'), ('o que você pode', '🧭'),
    ('uma base', '🧭'), ('assessor', '💬'), ('escreva', '💬'),
    ('filtrar', '🔎'), ('busca', '🔎'), ('diagnóstico', '🛠'),
    ('não ', '⚠️'), ('essa confirmação', '⌛'), ('esse botão', '⌛'),
    ('cancelado', '↩️'), ('cadastro cancelado', '↩️'), ('rascunho descartado', '↩️'),
    # Títulos que antes caíam no 📋 genérico: cada um ganha o ícone da sua função.
    ('central de atenção', '🔎'), ('prévia de fechamento', '📋'), ('fechamento', '📋'),
    ('detalhes do mês', '🔎'), ('limites', '🎯'), ('entradas a receber', '💵'), ('a receber', '💵'),
    ('o que merece revisão', '🔎'), ('painel', '📊'), ('saldos por conta', '🏦'), ('caixa ', '🏦'),
    ('esse compromisso não', '⚠️'), ('esse lançamento não', '⚠️'),
)


def _with_icon(label, default=None):
    label = str(label)
    # Conserva ícones existentes, setas e referências exibidas pelo motor.
    if not label or not label[0].isalnum():
        return label
    lowered = html.unescape(label).casefold()
    icon = next((icon for prefix, icon in TITLE_ICONS if lowered.startswith(prefix)), default)
    return icon + ' ' + label if icon else label


# ---------------------------------------------------------------------------
# Helpers de formatação e privacidade (puros, sem I/O nem regra financeira).
# ---------------------------------------------------------------------------
MASK = '••••'
_MONEY_RE = re.compile(r'(?:−\s?|-)?R\$\s?[−-]?\s?\d[\d.]*(?:,\d+)?')
_BARE_MONEY_RE = re.compile(r'(?<![\d.,])\d{1,3}(?:\.\d{3})*,\d{2}(?![\d,])')


def mask_money(text, bare=False):
    """Troca todo valor monetário por ••••. ``bare`` inclui 210,00 sem R$ (rótulos de botão)."""
    text = _MONEY_RE.sub(MASK, str(text))
    return _BARE_MONEY_RE.sub(MASK, text) if bare else text


def plural(count, singular, plural_=None):
    """'1 conta' / '3 contas' / '0 contas'; plural_ explícito para irregulares (item → itens)."""
    count = int(count)
    word = singular if count == 1 else (plural_ or singular + 's')
    return f'{count} {word}'


def money_sinal(text):
    """'R$ -1.234,56' → '−R$ 1.234,56' (U+2212). Só para a camada de UX."""
    return re.sub(r'R\$ -(?=\d)', '−R$ ', str(text))


def pct(value, decimals=1):
    """Percentual com vírgula decimal: 277.2 → '277,2%'."""
    return f'{float(value):.{decimals}f}'.replace('.', ',') + '%'


def due_chip(delta_days):
    """Chip de vencimento (emoji + palavra no texto que o acompanha)."""
    if delta_days < 0:
        return '🔴'
    if delta_days <= 1:
        return '🟡'
    return '⚪'


def button_label(label, action):
    """Decoração apenas no envio: o texto digitado e o callback ficam intactos."""
    label = str(label)
    if not label or not label[0].isalnum() or label[0].isdigit():
        return label
    key = label.casefold()
    if action and action[0] in {'unlink', 'unlink_preview', 'undo', 'undo_preview'}:
        return ('🔗 ' if action[0].startswith('unlink') else '↩️ ') + label
    # Paginação e escolhas simples (Sim/Não, filtros) ficam só com o texto:
    # um ícone genérico ali confunde mais do que ajuda.
    if key.rstrip().endswith(('›', '▶️', '‹', '◀️')) or key.strip(' .!?') in _BUTTON_PLAIN:
        return label
    if key.strip() in _BUTTON_FIELDS or (action and action[0] in {'new_fixed_edit', 'media_transfer_field'}):
        return '✏️ ' + label
    groups = (
        (('cancelar', 'descartar', 'limpar'), '✖️'),
        (('apagar', 'excluir', 'remover'), '🗑'),
        (('salvar', 'confirmar', 'concluir', 'sim,', 'importar'), '✅'),
        (('editar', 'corrigir', 'ajustar', 'valor', 'descrição', 'forma', 'informar', 'trocar'), '✏️'),
        (('voltar', 'retomar', 'repetir', 'desfazer'), '↩️'),
        (('tentar novamente', 'perguntar de novo', 'recomeçar'), '🔄'),
        (('pausar',), '⏸️'), (('retirar pausa',), '▶️'), (('pular',), '⏭️'),
        (('copiar',), '📋'), (('mostrar valores',), '👁'), (('prévia',), '👁'),
        (('ver', 'abrir', 'detalhes', 'detalhar', 'memória', 'resumo', 'procurar', 'buscar',
          'lista completa', 'checklist completo', 'já registrei', 'conferir'), '🔎'),
        (('conta', 'filtrar conta', 'todas as contas', 'por conta', 'digitar outra conta'), '🏦'),
        (('data', 'mês', 'próximo mês', 'parcel', 'por data', 'hoje', 'ontem', 'dia ',
          'este mês', 'este ano', 'o que vence', 'sem término', 'definir término'), '📅'),
        (('crédito', 'fatura', 'por fatura', 'usar saldo restante'), '💳'),
        (('pix',), '⚡'), (('débito',), '🏧'), (('dinheiro',), '💵'), (('transferência',), '↔️'),
        (('boleto',), '📄'), (('à vista',), '💸'),
        (('categoria',), '🏷'), (('entender', 'como', 'perguntas'), '💡'),
        (('registrar', 'novo', 'nova', 'cadastrar', 'criar'), '➕'),
        (('atualizar',), '🔄'), (('analisar',), '📊'), (('outros ajustes',), '✏️'),
        (('escolher aula',), '🎓'), (('a partir de',), '📅'),
        (('vincular', 'relacionar', 'selecionar #'), '🔗'),
        (('manter', 'é outra operação'), '✔️'),
        (('configurar', 'escolher horários'), '⚙️'),
        (('meu mês', 'onde gastei'), '📊'), (('planejar',), '🎯'), (('posso comprar',), '🔮'),
        (('escrever uma pergunta', 'testar uma pergunta'), '💬'),
        (('entradas',), '💰'), (('fechamento',), '📋'),
        (('tudo',), '📦'),
    )
    icon = next((icon for prefixes, icon in groups if key.startswith(prefixes)), None)
    if icon is None and action and action[0] in {'cash_account_detail', 'account', 'account_filter'}:
        icon = '🏦'
    if icon:
        return icon + ' ' + label
    # Sem correspondência: só o texto (antes caía num 📋 genérico sem sentido).
    lowered = html.unescape(label).casefold()
    icon = next((icon for prefix, icon in TITLE_ICONS if lowered.startswith(prefix)), None)
    return icon + ' ' + label if icon else label


# Escolhas que não precisam de ícone (o texto já é a resposta).
_BUTTON_PLAIN = frozenset({'sim', 'não', 'nao', 'todos', 'todas', 'vencidas', 'despesas', 'agora não'})
# Campos de um formulário de edição: sempre "editar este campo".
_BUTTON_FIELDS = frozenset({'nome', 'origem', 'destino', 'vencimento', 'término'})


# Ações que gravam algo depois de uma prévia (verde). Numa tela que tem uma
# delas, "Cancelar" vira vermelho: verde segue, vermelho desiste.
COMMIT_KINDS = frozenset({
    'commit', 'commit_link', 'invoice_commit', 'save_balance', 'save_budget', 'save_hours',
    'cash_setup_commit', 'reconcile_baseline_commit', 'fixed_save', 'new_fixed_commit',
    'media_transfer_commit',
})
DESTRUCTIVE_KINDS = frozenset({
    'undo', 'undo_preview', 'unlink', 'unlink_preview', 'lock', 'category_rule_remove_commit',
    'discard_suspended', 'discard_and_register', 'discard_and_start',
})


def _is_cancel(label, action):
    kind = action[0] if isinstance(action, (tuple, list)) and action else None
    if kind in {'cancel', 'new_fixed_cancel'}:
        return True
    text = html.unescape(str(label)).casefold().lstrip('✖️❌ ').strip()
    return text.startswith(('cancelar', 'descartar'))


def screen_styles(rows):
    """Estilos de uma tela inteira: [[(label, action)]] -> [[style]].

    Cada botão recebe o estilo próprio (button_style). Se a tela confirma uma
    gravação (verde) e não tem ação destrutiva (vermelho), "Cancelar" fica
    vermelho. Em telas de apagar/desfazer, "Cancelar" continua neutro para não
    haver dois botões vermelhos com sentidos opostos.
    """
    styles = [[button_style(label, action) for label, action in row] for row in rows]
    flat = [(label, action, style) for row, srow in zip(rows, styles) for (label, action), style in zip(row, srow)]
    has_commit = any(style == 'success' and _confirms(action) for _, action, style in flat)
    has_danger = any(style == 'danger' for _, _, style in flat)
    if has_commit and not has_danger:
        styles = [[('danger' if style is None and _is_cancel(label, action) else style)
                   for (label, action), style in zip(row, srow)] for row, srow in zip(rows, styles)]
    return styles


def _confirms(action):
    if not isinstance(action, (tuple, list)) or not action:
        return False
    if action[0] in COMMIT_KINDS:
        return True
    return action[0] in {'legacy', 'legacy_raw'} and len(action) > 1 and _legacy_kind(action[1]) == 'confirm'


def _legacy_kind(command):
    """Classifica um comando legado de botão: confirm, cancel, destroy ou None."""
    command = str(command or '').strip().lower()
    command = re.sub(r'^__legado__(?:\[[^\]]*\])?:', '', command).strip()
    if command == '__confirmar_exclusao__' or command in {'confirmar exclusao', 'confirmar exclusão'}:
        return 'destroy'
    if command.startswith(('excluir ', 'apagar ', 'remover ')):
        return 'destroy'
    if command.startswith('confirmar '):
        return 'confirm'
    if command.startswith('saldo inicial ') and command.endswith((' herdado', ' herdada')):
        return 'destroy'
    if command.startswith('cancelar ') or command in {'__cancelar_exclusao__', '__guiado_cancelar__', 'pin_reset_cancelar'}:
        return 'cancel'
    return None


def heading(title, period=''):
    text='<b>'+html.escape(str(title))+'</b>'
    return text+('\n<i>'+html.escape(str(period))+'</i>' if period else '')


def present_text(text):
    """Uniformiza somente cabeçalhos gerados; nunca interpreta valores ou ações."""
    months = r'(?:Janeiro|Fevereiro|Março|Abril|Maio|Junho|Julho|Agosto|Setembro|Outubro|Novembro|Dezembro) \d{4}'
    text = re.sub(r'^<b>([^\n<>]+?) · ('+months+r')</b>',
                  r'<b>\1</b>\n<i>\2</i>', text)
    # Só o cabeçalho gerado é decorado: não reinterpreta descrições ou cifras.
    decorated = re.sub(r'^<b>([^\n<>]+)</b>',
                       lambda m: '<b>'+_with_icon(m[1])+'</b>', text)
    decorated = re.sub(r'^(.*?\n<i>[1-4]/4 · [^<>]+</i>\n)<b>([^\n<>]+)</b>',
                       lambda m: m[1]+'<b>'+_with_icon(m[2])+'</b>', decorated)
    decorated = re.sub(r'(?m)^<i>('+months+r')</i>$', r'📅 <i>\1</i>', decorated)
    # Mensagens breves de etapa/estado também recebem um título, sem truncar.
    if not decorated.startswith('<') and not decorated.startswith(('📅', '🏠')):
        first, _, rest = decorated.partition('\n')
        if '<' not in first and len(html.unescape(first)) <= 100:
            decorated = '<b>'+_with_icon(first)+'</b>'+('\n'+rest if rest else '')
        elif '<' not in first:
            decorated = '<b>💬 Orientação</b>\n\n'+decorated
    # Uma decoração nunca pode fazer uma tela válida ultrapassar o transporte.
    return decorated if len(decorated.encode('utf-16-le'))//2 <= 3900 else text


def message_html(text):
    """Mensagens diretas (PIN, erros, etapas e avisos): escape antes do HTML."""
    return present_text('\n'.join(legacy_pages(str(text))))


def legacy_pages(text, limit=3500):
    """Apresenta relatórios de texto depois de o adaptador extrair seus comandos.

    Escapa cada fragmento antes de inserir HTML. Cada página fecha suas tags e
    respeita UTF-16; nomes, IDs, comandos e valores não são reinterpretados.
    """
    if limit < 40:
        raise ValueError('Limite de apresentação insuficiente.')
    pages=[];page='';in_card=False
    for original in str(text).splitlines():
        line=original;bold=False
        if re.fullmatch(r'\s*─{3,}\s*',line):
            line=''
        if line.startswith('┌ '):
            in_card=True;line=_with_icon(line[2:]);bold=True
        elif in_card and line.startswith('│'):
            line=line[1:].strip()
            # Apenas espaços de alinhamento do relatório, dentro da moldura.
            line=re.sub(r' {2,}', ' · ', line)
        elif in_card and line.strip()=='└':
            in_card=False;line=''
        elif not pages and not page and line.strip():
            if len(line) <= 120:
                line=_with_icon(line);bold=True
        elif re.match(r'^(?:TOTAL\b|Total\b|Saldo\b|Ainda a pagar\b|Reservado\b|Itens:)', line):
            bold=True
        # Divisão antes do escape impede cortar uma entidade ou uma tag.
        pieces=[];piece='';cost=7 if bold else 0
        for char in line:
            char_cost=len(html.escape(char).encode('utf-16-le'))//2
            if cost+char_cost>limit-2:
                pieces.append(piece);piece='';cost=7 if bold else 0
            piece+=char;cost+=char_cost
        pieces.append(piece)
        for piece in pieces:
            escaped=html.escape(piece)
            rendered='<b>'+escaped+'</b>' if bold and piece else escaped
            candidate=page+('\n' if page else '')+rendered
            if len(candidate.encode('utf-16-le'))//2>limit:
                pages.append(page);page=rendered
            else:page=candidate
    if page.strip():pages.append(page)
    return pages or [html.escape(str(text)) or 'Sem informações para exibir.']


def report_html(text):
    """Relatórios nativos curtos: substitui alinhamento monoespaçado por linhas."""
    lines=[]
    for line in str(text).splitlines():
        if re.fullmatch(r'\s*─{3,}\s*',line):line=''
        line=re.sub(r'\s+\.{3,}\s+', ' · ', line)
        lines.append(line)
    # Estes relatórios já são paginados pelo motor. Sem cortar conteúdo aqui.
    return '\n'.join(legacy_pages('\n'.join(lines),limit=max(3500,len(str(text))*6+20)))


def rich_message_html(text):
    """Converte uma tela HTML existente em blocos de Rich Message.

    A função é deliberadamente apenas visual: não interpreta valores,
    comandos ou regras do assessor. O mesmo texto que alimenta o fallback
    tradicional é repartido em título e parágrafos estruturados.
    """
    source = str(text or '').strip()
    if not source:
        return '<p>Sem informações para exibir.</p>'

    blocks = []
    title = re.match(r'^<b>([^<>\n]+)</b>(?:\n(?:📅\s*)?<i>([^<>\n]+)</i>)?', source)
    if title:
        blocks.append('<h2>' + title.group(1) + '</h2>')
        if title.group(2):
            blocks.append('<p><i>' + title.group(2) + '</i></p>')
        source = source[title.end():].lstrip('\n')

    for paragraph in re.split(r'\n{2,}', source):
        paragraph = paragraph.strip()
        if paragraph:
            blocks.append('<p>' + paragraph.replace('\n', '<br>') + '</p>')
    return ''.join(blocks) or '<p>Sem informações para exibir.</p>'


def rich_table(headers, rows, total=None, aligns=None):
    """Tabela segura com total destacado pelo tema nativo do Telegram.

    Cabeçalhos e células são sempre escapados. A linha final usa ``th`` para
    receber o mesmo contraste do cabeçalho em temas claro e escuro, sem CSS.
    """
    aligns = tuple(aligns or ('left',) + ('right',) * max(0, len(headers) - 1))
    if len(aligns) != len(headers) or any(value not in {'left', 'center', 'right'} for value in aligns):
        raise ValueError('Alinhamento inválido para a tabela.')
    if any(len(row) != len(headers) for row in rows) or (total is not None and len(total) != len(headers)):
        raise ValueError('Todas as linhas da tabela devem ter o mesmo número de colunas.')

    def cells(tag, values):
        return ''.join(
            '<'+tag+' align="'+align+'">'+html.escape(str(value))+'</'+tag+'>'
            for value, align in zip(values, aligns)
        )

    head = cells('th', headers)
    body = ''.join(
        '<tr>' + cells('td', row) + '</tr>'
        for row in rows
    )
    if total is not None:
        body += '<tr>' + cells('th', total) + '</tr>'
    return '<table striped compact><tr>' + head + '</tr>' + body + '</table>'


def button_style(label, action):
    """Cores são redundantes com rótulos: azul ação, verde confirmação, vermelho remoção."""
    if not isinstance(action,(tuple,list)) or not action:
        return None
    kind=action[0]
    if kind in DESTRUCTIVE_KINDS:
        return 'danger'
    if kind in COMMIT_KINDS:
        return 'success'
    if kind=='start':
        return 'success' if action[1]=='receita' else ('primary' if action[1]=='despesa' else None)
    if kind=='view' and action[1] in {'register','pay','attention','receivables'}:
        return 'success' if action[1]=='receivables' else 'primary'
    if kind in {'edit_menu','flow_resume','resume_suspended','invoice_pay_total',
                'invoice_pay_partial','invoice_begin','settle','home_income','chart','ask',
                'fixed_resume','fixed_edit','fixed_edit_fields','budget_start','cash_setup_start'}:
        return 'primary'
    # Legado: inspecionar o comando, não descrições financeiras vindas do banco.
    if kind in {'legacy','legacy_raw'} and len(action)>1:
        command=str(action[1]).strip().lower()
        legacy=_legacy_kind(command)
        if legacy=='confirm':
            return 'success'
        if legacy=='destroy':
            return 'danger'
        if legacy=='cancel':
            return None
        if command.startswith(('excluir ','apagar ','remover ')):
            return 'danger'
        if command.startswith(('saldo', 'quanto ', 'detalhar ', 'dashboard', 'fixos', 'histórico', 'agenda')):
            return 'primary'
    if kind=='fixed_scope':return 'primary'
    # Botões guiados do fluxo antigo (Apagar lançamento/fixo).
    if kind=='guided' and len(action)>1 and str(action[1]).startswith(('apagar_lancamento','apagar_fixo')):
        return 'danger'
    return None


def selected_style(action, session):
    """Realça o filtro atual sem alterar seu estado."""
    if action and action[0]=='filter' and len(action)>2:
        active=session.pay_filter if action[1]=='pay' else session.history_filter
        return 'primary' if active==action[2] else None
    return None


def registration_progress(stage,draft):
    """Etapas lógicas: dados → pagamento → data → conferência."""
    if not draft or draft.get('flow') or stage in {'search','account_search'}:
        return ''
    steps={'installment_choice':1,'amount':1,'description':1,'category':1,
           'method':2,'account':2,'date':3,'installments':3,'billing_month':3,'confirm':4}
    if stage not in steps:return ''
    current=steps[stage]
    data_label='Data, parcelas e fatura' if draft.get('forma_pagamento')=='crédito' else 'Data e parcelas'
    labels=('Dados','Pagamento',data_label,'Conferência')
    dots=' '.join('🔵' if i == current else '○' for i in range(1,5))
    return f'{dots}\n<i>{current}/4 · {labels[current-1]}</i>\n'
