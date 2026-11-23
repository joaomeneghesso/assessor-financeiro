"""Interface Telegram 2.0: apresentação curta, navegação e registros revisáveis.

As consultas usam o motor existente. A interface não chama APIs bancárias; a IA local é usada somente para roteamento de intenção.
Tokens de botão pertencem à sessão e expiram; valores são escapados para HTML.
"""
import calendar
import copy
import functools
import html
import logging
import os
import config
import re
import secrets
import time
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime, timedelta, timezone
import relogio
from decimal import Decimal
from pathlib import Path

from faturas_competencia import (
    eh_credito, precisa_escolher, opcoes_fatura, preparar_rascunho,
    contexto_escolha, competencia_transacao, data_real_compra, data_competencia,
)
import database as db
import services as svc
import compromissos as comp
import conciliacao as conc
import assessor_orientacao as orient
import contas_inativas, efeito_baixa  # efeito_baixa: saldo da conta antes → depois na baixa
import telegram_aprendizado as learning
from telegram_design import button_label, button_style, screen_styles, heading, present_text, report_html, rich_message_html, rich_table, superscript_number, registration_progress, selected_style, message_html, mask_money, plural, money_sinal, pct, due_chip
from money import parse_money
from categorias import sugerir_categoria, categoria_permitida_ia
from saldo_resumo import resumir_saldo
from parser_financeiro import parse_mensagem
from registro_conversa import (
    extrair_campos, descricao_valida, categoria_da_descricao, data_informada, valor_informado,
)
from telegram_registros import (
    confirmar_registro,
    confirmar_pagamento_fatura,
    desfazer_registro,
    buscar_duplicata,
    evento_registro_recente,
    corrigir_categoria_registro,
    corrigir_data_registro,
    motivo_bloqueio_data,
    validar_transacao,
    validar_campo_textual,
)
from telegram_execucao import executar_core
import sugestoes_lancamento as sug

from version import VERSION
PAGE_SIZE = 5
TTL = 600


# RC3.0.15 - Central de ajuda orientada por objetivo.
# Somente UX: as ações apontam para fluxos já existentes; nenhuma regra financeira
# é implementada neste catálogo.
HELP_TOPICS = {
    'grupo_pagar': {
        'title': '💳 Pagar e faturas',
        'body': ('Tudo que representa obrigação: faturas, contas previstas, fixos, parcelas e conciliação.\n\n'
                 'Comece por Faturas quando a dúvida for cartão; use Pagar para obrigações abertas e Conciliação quando o movimento real já existir.'),
        'rows': [[('💳 Faturas', ('topic','faturas')), ('🧾 Pagar', ('topic','pagar'))],
                 [('🧾 Fixos e previsões', ('topic','compromissos')), ('🔗 Conciliação', ('topic','conciliar'))]],
    },
    'grupo_dinheiro': {
        'title': '💰 Entender meu dinheiro',
        'body': ('Use este caminho para interpretar caixa, saldo, projeção, categorias e fechamento sem alterar registros.\n\n'
                 'Se um número parecer estranho, abra Analisar/auditar antes de corrigir qualquer dado.'),
        'rows': [[('💰 Saldo e caixa', ('topic','saldo')), ('📊 Analisar/auditar', ('topic','analisar'))],
                 [('📋 Fechamento', ('topic','controle')), ('🧭 Planejar', ('topic','planejar'))]],
    },
    'grupo_consultar': {
        'title': '🔎 Consultar e corrigir',
        'body': ('Encontre o que já aconteceu antes de editar. Histórico é a principal trilha para localizar movimentos, conferir detalhes e rastrear correções.\n\n'
                 'Transferências e recebimentos ficam aqui porque ajudam a conferir movimentos entre contas e entradas realizadas.'),
        'rows': [[('🔎 Histórico', ('topic','historico')), ('✏️ Corrigir', ('topic','corrigir'))],
                 [('🔁 Transferências', ('topic','transferencias')), ('💵 Receber', ('topic','receber'))]],
    },
    'grupo_mais': {
        'title': '⚙️ Mais recursos',
        'body': ('Recursos complementares para automatizar, aprender e proteger o assessor.\n\n'
                 'Aqui ficam alertas, IA local, backup/importação/segurança, aulas e comandos avançados.'),
        'rows': [[('🔔 Alertas', ('topic','alertas')), ('🤖 IA / Ollama', ('topic','ia'))],
                 [('🔐 Dados e segurança', ('topic','dados')), ('⌨️ Comandos avançados', ('view','command_help'))],
                 [('🎓 Aprender', ('legacy','aprender'))]],
    },
    'primeiros': {
        'title': '🚀 Começar sem se perder',
        'body': ('Confira sua base de saldo, cadastre o que é previsto, registre apenas o que realmente aconteceu e revise antes de salvar.\n\n'
                 'O assessor separa caixa, compromissos, faturas e projeção para evitar dupla contagem.'),
        'rows': [[('1. Preparar minha base', ('view','setup'))], [('2. Registrar', ('view','register')), ('3. Ver A pagar', ('view','pay'))], [('🎓 Aprender passo a passo', ('legacy','aprender primeiros passos'))]],
    },
    'registrar': {
        'title': '➕ Registrar gastos e entradas',
        'body': ('Use para movimentos que realmente aconteceram. Você pode seguir por botões ou escrever naturalmente.\n\n'
                 'Despesas perguntam sobre parcelamento quando necessário. No crédito, a partir do corte configurado (por padrão, dia 25), você escolhe a fatura sem alterar a data real da compra.'),
        'rows': [[('− Registrar despesa', ('start','despesa')), ('+ Registrar entrada', ('start','receita'))], [('🔮 Simular', ('start','simulate')), ('🔎 Histórico', ('view','history'))], [('🎓 Aula de lançamentos', ('legacy','aprender lançamentos'))]],
    },
    'compromissos': {
        'title': '🧾 Fixos, parcelas e entradas previstas',
        'body': ('Fixos se repetem, parcelamentos terminam e entradas previstas só viram dinheiro realizado quando você registra o recebimento.\n\nUse A pagar e A receber para acompanhar previsões sem transformá-las em movimento real.'),
        'rows': [[('🧾 A pagar', ('view','pay')), ('💵 A receber', ('view','receivables'))], [('🔁 Recorrências', ('view','recurring'))], [('⌨️ Fixos', ('legacy','/help fixos')), ('⌨️ Entradas', ('legacy','/help entradas'))]],
    },
    'pagar': {
        'title': '🧾 Pagar contas com segurança',
        'body': ('A pagar mostra obrigações abertas. Se a saída já aparece no Histórico, não registre de novo: vincule o lançamento à obrigação.\n\nPagamento parcial mantém somente o restante em aberto.'),
        'rows': [[('🧾 Abrir A pagar', ('view','pay'))], [('🔗 Conciliações', ('view','reconciliations')), ('🔎 Histórico', ('view','history'))]],
    },
    'receber': {
        'title': '💵 Receber e acompanhar entradas',
        'body': ('A receber representa valores esperados. Quando o dinheiro cair, registre o recebimento. Se ele já está no Histórico, vincule em vez de criar outro lançamento.'),
        'rows': [[('💵 Abrir A receber', ('view','receivables'))], [('+ Registrar entrada', ('start','receita')), ('🔎 Histórico', ('view','history'))]],
    },
    'faturas': {
        'title': '💳 Cartões, faturas, parcelas e fechamento',
        'body': ('Compra no crédito e pagamento da fatura são eventos diferentes. A data da compra permanece real; a competência define em qual fatura o valor entra.\n\n'
                 'O corte é configurável por cartão; por padrão, é o dia 25. O fluxo mostra as competências disponíveis a partir desse corte. Em compras parceladas, a primeira competência escolhida determina os meses seguintes.'),
        'rows': [[('➕ Registrar compra', ('view','register')), ('💳 A pagar', ('view','pay'))], [('🔎 Histórico', ('view','history')), ('📊 Análises', ('view','analytics'))], [('🎓 Aula de faturas', ('legacy','aprender faturas'))]],
    },
    'transferencias': {
        'title': '🔁 Transferir entre suas contas',
        'body': ('Transferência entre contas próprias não é receita nem despesa: reduz a origem, aumenta o destino e mantém o total do caixa.\n\nPix é forma de pagamento, não nome de conta.'),
        'rows': [[('💰 Entender saldo', ('view','balance'))], [('⌨️ Guia', ('legacy','/help transferencias')), ('🎓 Aula', ('legacy','aprender transferencias'))]],
    },
    'saldo': {
        'title': '💰 Entender caixa, saldo e projeção',
        'body': ('Disponível é caixa realizado. A pagar são obrigações abertas. Sobra prevista combina caixa e previsões.\n\nCrédito não reduz o caixa no momento da compra.'),
        'rows': [[('💰 Entender saldo', ('view','balance')), ('🏠 Início', ('view','home'))], [('📆 Agenda', ('view','agenda'))]],
    },
    'historico': {
        'title': '🔎 Histórico, busca e rastreabilidade',
        'body': ('Histórico mostra movimentos já registrados. Abra um item para conferir data, conta, forma, categoria, vínculo e, no crédito, data real da compra e competência da fatura.\n\nUse filtros e busca antes de corrigir, excluir ou vincular.'),
        'rows': [[('🔎 Abrir Histórico', ('view','history')), ('🔗 Conciliações', ('view','reconciliations'))], [('✏️ Correções', ('topic','corrigir'))]],
    },
    'analisar': {
        'title': '📊 Análises, diagnóstico e auditoria',
        'body': ('Análises ajudam a entender categorias e evolução. Central de atenção destaca sinais objetivos e Fechamento resume o mês sem criar baixas.\n\nQuando um número parecer estranho, audite antes de corrigir dados.'),
        'rows': [[('📊 Análises', ('view','analytics')), ('⚠️ Atenção', ('view','attention'))], [('📋 Fechamento', ('view','closing')), ('🎓 Aula de auditoria', ('legacy','aprender auditoria'))], [('⌨️ Auditoria', ('legacy','/help auditoria'))]],
    },
    'corrigir': {
        'title': '✏️ Corrigir sem perder rastreabilidade',
        'body': ('Abra o lançamento pelo Histórico antes de alterar. Movimentos conciliados podem exigir desvinculação antes de mudar valor, conta ou forma. Exclusões devem ser feitas só depois de conferir o ID.'),
        'rows': [[('🔎 Histórico', ('view','history'))], [('🔗 Conciliações', ('view','reconciliations')), ('Revisar', ('view','review'))], [('⌨️ Correções', ('legacy','/help corrigir')), ('⌨️ Exclusões', ('legacy','/help excluir'))]],
    },
    'conciliar': {
        'title': '🔗 Conciliação: previsão × movimento real',
        'body': ('Conciliação liga uma previsão ao movimento que realmente aconteceu e evita dupla contagem. “Revisar baixa” indica que falta confirmar qual movimento realizou uma obrigação.'),
        'rows': [[('🔗 Conciliações', ('view','reconciliations')), ('🔎 Revisar baixas', ('view','review'))], [('🎓 Aula', ('legacy','aprender conciliacao'))]],
    },
    'planejar': {
        'title': '🧭 Planejar sem alterar seus registros',
        'body': ('Limites acompanham categorias; Meu plano organiza próximos passos; Simular estima impacto sem gravar. Recorrências identificam padrões históricos, mas não criam compromissos.\n\nPlanejamento nunca vira movimento realizado automaticamente.'),
        'rows': [[('🧭 Meu plano', ('view','plan')), ('🎯 Limites', ('view','budgets'))], [('🔮 Simular', ('start','simulate')), ('🔁 Recorrências', ('view','recurring'))], [('🎓 Aula', ('legacy','aprender planejamento'))]],
    },
    'alertas': {
        'title': '🔔 Alertas, vencimentos e lembretes',
        'body': ('Alertas respeitam horários e pausa. O bot precisa estar ligado. Vencimentos organizam o checklist e alimentam lembretes. Alertas não registram pagamentos.'),
        'rows': [[('🔔 Configurar alertas', ('view','alerts'))], [('🎓 Aula de vencimentos', ('legacy','aprender vencimentos'))]],
    },
    'controle': {
        'title': '📋 Fechamento e central de atenção',
        'body': ('Central de atenção destaca sinais objetivos. Fechamento mensal resume o que foi registrado sem dar baixa, criar movimentos ou transformar projeção em realizado.'),
        'rows': [[('⚠️ Atenção', ('view','attention')), ('📋 Fechamento', ('view','closing'))], [('🏠 Início', ('view','home')), ('📊 Análises', ('view','analytics'))]],
    },
    'ia': {
        'title': '🤖 IA local / Ollama',
        'body': ('O Ollama é uma segunda camada de interpretação. Regras determinísticas têm prioridade e os valores vêm do motor financeiro. A IA não confirma lançamentos sozinha.'),
        'rows': [[('💬 Perguntar', ('view','assistant')), ('Diagnóstico da IA', ('view','local_ai'))]],
    },
    'dados': {
        'title': '🔐 Backup, exportação, importação e segurança',
        'body': ('Backup é a cópia de recuperação. Exportação é para consulta/transporte e não substitui backup. Importação deve ser analisada antes da confirmação.\n\nO acesso diário usa a allowlist do seu Telegram. O PIN reforçado aparece apenas em ações sensíveis; ocultar valores só reduz a exposição da tela.'),
        'rows': [[('💾 Backup', ('legacy','backup')), ('📤 Exportar mês', ('legacy','exportar csv {month}'))], [('📥 Importação', ('legacy','/help importacao')), ('🔐 Segurança', ('topic','privacidade'))], [('🎓 Aula de dados', ('legacy','aprender dados'))]],
    },
    'privacidade': {
        'title': '🔐 Privacidade e bloqueio',
        'body': ('Use Bloquear para encerrar a sessão reforçada de ações sensíveis. Saldo, histórico e lançamentos comuns continuam disponíveis ao Telegram autorizado. O PIN não substitui a segurança do dispositivo e do Telegram.'),
        'rows': [[('🔒 Bloquear agora', ('lock',)), ('⚙️ Mais opções', ('view','more'))]],
    },
}


HELP_PARENT = {
    'faturas': ('grupo_pagar', '← Pagar e faturas'),
    'pagar': ('grupo_pagar', '← Pagar e faturas'),
    'compromissos': ('grupo_pagar', '← Pagar e faturas'),
    'conciliar': ('grupo_pagar', '← Pagar e faturas'),
    'saldo': ('grupo_dinheiro', '← Entender meu dinheiro'),
    'analisar': ('grupo_dinheiro', '← Entender meu dinheiro'),
    'controle': ('grupo_dinheiro', '← Entender meu dinheiro'),
    'planejar': ('grupo_dinheiro', '← Entender meu dinheiro'),
    'historico': ('grupo_consultar', '← Consultar e corrigir'),
    'corrigir': ('grupo_consultar', '← Consultar e corrigir'),
    'transferencias': ('grupo_consultar', '← Consultar e corrigir'),
    'receber': ('grupo_consultar', '← Consultar e corrigir'),
    'alertas': ('grupo_mais', '← Mais recursos'),
    'ia': ('grupo_mais', '← Mais recursos'),
    'dados': ('grupo_mais', '← Mais recursos'),
    'privacidade': ('grupo_mais', '← Mais recursos'),
}

HELP_TOPICS['dashboard']={
    'title':'📊 Ler o painel',
    'body':'O painel principal destaca saldo disponível, reservas e sobra prevista. Esses valores vêm do mesmo cálculo usado em Início; os compromissos no crédito continuam compondo a fatura correspondente.\n\nConfira a competência no título. Um mês futuro é projeção; uma base estimada precisa ser conferida. Entender valores abre a memória do cálculo; Categorias explica onde os gastos registrados se concentram.',
    'rows':[[('📊 Abrir painel',('chart','home')),('🧮 Ver cálculo',('view','balance_details'))],
            [('🏷 Categorias',('chart','analytics')),('🎓 Aula do painel',('lesson','meu mes'))]]}
HELP_PARENT['dashboard']=('grupo_dinheiro','← Entender meu dinheiro')
HELP_TOPICS['grupo_dinheiro']['rows'].append([('📊 Painel',('topic','dashboard'))])
HELP_GUIDANCE={
 'primeiros':'Confira o valor disponível no aplicativo de cada banco. Depois veja Início; as pendências ficam separadas do dinheiro atual.',
 'registrar':'Exemplo ilustrativo: “gastei 35 almoço pix Itaú”. Troque os dados pelos seus e confira a prévia. O Histórico permite verificar o registro salvo.',
 'compromissos':'Confira forma, banco, início e término. A partir de um mês preserva a versão anterior; corrigir cadastro pode alterar os resumos anteriores.',
 'pagar':'Abra uma conta → confira valor e vencimento → registre a saída ou vincule o lançamento existente. Não use uma segunda despesa para corrigir uma baixa.',
 'receber':'Confira o banco onde o dinheiro entrou e a data real. A previsão permanece distinta do recebimento até a conciliação.',
 'faturas':'Exemplo com corte no dia 25: uma compra em 25/09 pode ser direcionada à fatura outubro, preservando a data da compra. Confira a competência antes de salvar.',
 'saldo':'Exemplo: R$ 1.000 disponíveis + R$ 200 a receber − R$ 300 reservados = R$ 900 previstos. Ver cálculo mostra os componentes; Por conta mostra a origem do disponível.',
 'historico':'Use Busca e filtros para localizar descrição, conta ou categoria. Abra o lançamento e confira a referência antes de corrigir.',
 'analisar':'Confira o período e a base de data/fatura. Totais de gastos registrados não são o saldo do banco nem a sobra prevista.',
 'corrigir':'Localize o lançamento no Histórico, confira o ID e escolha o campo. Se estiver vinculado, leia o efeito da desvinculação antes de continuar.',
 'conciliar':'Confira valor, banco e competência dos dois lados. Relacionar um lançamento existente evita criar outro pagamento.',
 'planejar':'Abra uma simulação e compare parcelas e meses. Ela ajuda a decidir; não aparece como uma despesa realizada.',
 'controle':'Compare Início com os saldos das contas e investigue as diferenças no Histórico e na memória do cálculo.',
}


_LOG_UX=logging.getLogger('assessor.ux')

def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value).lower())
                   if unicodedata.category(c) != 'Mn').strip()


def dashboard_route(text):
    """Comandos de gráfico têm prioridade sobre a intenção natural de resumo."""
    clean=re.sub(r'^[📈📊🏷]\s*','',norm(text)).lstrip('/')
    analysis=re.fullmatch(r'(?:dashboard|dash|painel)\s+(evolucao|diagnostico)(?:\s+(.+))?',clean)
    if analysis:return ({'evolucao':'evolution','diagnostico':'diagnosis'}[analysis[1]],analysis[2])
    match=re.fullmatch(r'(?:dashboard|dash|painel)(?:\s+(categorias?|por\s+categorias?))?(?:\s+(.+))?',clean)
    if match:
        return ('categories' if match[1] else 'home',match[2])
    match=re.fullmatch(r'categorias?\s+(?:dashboard|dash|painel)(?:\s+(.+))?',clean)
    return ('categories',match[1]) if match else None


def safe(value, limit=120):
    text = str(value or '').replace('\n', ' ')
    return html.escape(text if len(text) <= limit else text[:limit - 1] + '…')


def cortar(value, limit):
    """Rótulo curto sem cortar no meio da palavra: espaços colapsados e "…" quando encurta."""
    text = re.sub(r'\s+', ' ', str(value or '')).strip()
    if len(text) <= limit:
        return text
    corte = text[:limit - 1].rstrip()
    if ' ' in corte and not text[limit - 1].isspace():
        corte = corte.rsplit(' ', 1)[0].rstrip() or corte
    return corte + '…'


def money(value):
    # −R$ só na camada de UX; services.formatar_moeda continua devolvendo 'R$ -50,00'.
    return money_sinal(svc.formatar_moeda(float(value or 0)))


# Telas de ajuda/aula trazem exemplos, não dados do titular: não passam pelo mascaramento.
HISTORY_FILTER_LABELS = {'all': 'todos', 'despesa': 'despesas', 'receita': 'entradas', 'interno': 'transferências e faturas'}

_PRIVACY_EXEMPT_VIEWS = frozenset({'help','learn','learn_topics','lesson','help_topic','command_help','advanced_help','feature_guide'})


def _private_key_screen(method):
    """Aplica o modo Ocultar a telas que recebem (key, ...) e não passam por render()."""
    @functools.wraps(method)
    def wrapper(self, key, *args, **kwargs):
        return self._apply_privacy(self.session(key), method(self, key, *args, **kwargs))
    return wrapper


def today():
    return relogio.hoje()


def month_shift(month, step):
    year, m = map(int, month.split('-'))
    date(year, m, 1)
    y, mm = divmod(year * 12 + m - 1 + step, 12)
    if not 1 <= y <= 9999:
        raise ValueError('Mês fora do calendário disponível.')
    return f'{y:04d}-{mm+1:02d}'


def data_br(value):
    """'2026-11-10' → '10/11/2026' (só exibição); outro texto volta como veio."""
    text = str(value or '')
    return f'{text[8:10]}/{text[5:7]}/{text[:4]}' if re.fullmatch(r'\d{4}-\d{2}-\d{2}.*', text) else text


def month_label(month):
    names = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
             'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    return f'{names[int(month[5:]) - 1]} {month[:4]}'


def installment_plan(transacao):
    """Retorna o cronograma exato usado por confirmar_registro, em centavos."""
    n = int(transacao.get('parcelas_total') or 1)
    total_centavos = int(parse_money(transacao['valor']) * 100)
    base, resto = divmod(total_centavos, n)
    inicio = date.fromisoformat(transacao.get('data_compra') or transacao['data'])
    ano_inicio, mes_inicio = map(int, competencia_transacao(transacao).split('-'))
    parcelas = []
    for i in range(n):
        indice = ano_inicio * 12 + mes_inicio - 1 + i
        ano, mes0 = divmod(indice, 12)
        dia = min(inicio.day, calendar.monthrange(ano, mes0 + 1)[1])
        valor_centavos = base + (1 if i < resto else 0)
        parcelas.append({
            'numero': i + 1,
            'data': date(ano, mes0 + 1, dia),
            'valor_centavos': valor_centavos,
            'valor': valor_centavos / 100,
        })
    return parcelas


def installment_distribution_text(parcelas):
    """Resume valores distintos sem sugerir que todas as parcelas são idênticas."""
    grupos = []
    for parcela in parcelas:
        valor = parcela['valor_centavos']
        if grupos and grupos[-1][0] == valor:
            grupos[-1][1] += 1
        else:
            grupos.append([valor, 1])
    if len(grupos) == 1:
        valor, qtd = grupos[0]
        return f'{qtd}x de {money(valor / 100)}'
    return ' + '.join(f'{qtd}x de {money(valor / 100)}' for valor, qtd in grupos)


def copy_text_value(value, limit=256):
    """Texto simples seguro para CopyTextButton (limite nativo: 256 chars)."""
    text = str(value or '').strip()
    if not text:
        return ''
    return text if len(text) <= limit else text[:limit - 1] + '…'


@dataclass
class Screen:
    text: str
    rows: list = field(default_factory=list)
    image: dict | None = None
    rich_html: str | None = None
    sensitive: bool = False

    def __post_init__(self):
        self.text = present_text(self.text)
        # Somente classifica a apresentação. Não altera valores nem a lógica
        # financeira; telas monetárias novas ficam protegidas por padrão.
        if 'R$' in html.unescape(self.text) or self.image:
            self.sensitive = True


@dataclass
class Session:
    month: str
    touched: float
    page: int = 0
    view: str = 'home'
    search: str = ''
    draft: dict | None = None
    fixed_edit: dict | None = None
    new_fixed: dict | None = None
    stage: str | None = None
    suspended_draft: dict | None = None
    suspended_stage: str | None = None
    suspended_view: str = ''
    privacy: bool = False
    tokens: dict = field(default_factory=dict)
    last_event: str | None = None
    owner: str = ''
    trail: list = field(default_factory=list)
    pay_filter: str = 'all'
    history_filter: str = 'all'
    history_basis: str = 'data'
    account_filter: str = ''
    pay_account_filter: str = ''
    history_account_filter: str = ''
    history_category_filter: str = ''
    filter_view: str = 'history'
    topic: str = 'primeiros'
    selected_id: int = 0
    selected_obligation: tuple = ('', '')
    target_page: int = 0
    ai_question: str = ''
    settings_draft: dict | None = None
    help_pages: list = field(default_factory=list)
    help_page: int = 0
    help_title: str = ''
    lesson: str = 'primeiros'
    lesson_page: int = 0
    learning_stage: str | None = None
    cash_page: int = 0
    pay_month_page: int = 0
    account_choice_page: int = 0
    media_review: dict | None = None
    compra: dict | None = None  # "Posso comprar?": total em centavos, parcelas, descrição (só leitura)


class Experience:
    def __init__(self, clock=time.monotonic, date_provider=today, state_store=None, wall_clock=time.time):
        self.clock = clock
        self.date_provider = date_provider
        self.wall_clock = wall_clock
        self.state_store = state_store
        self.sessions = {}
        self._restore_sessions()

    @staticmethod
    def _tuple_actions(value):
        if isinstance(value, list):
            return tuple(Experience._tuple_actions(item) for item in value)
        if isinstance(value, dict):
            return {key: Experience._tuple_actions(item) for key, item in value.items()}
        return value

    def _restore_sessions(self):
        if self.state_store is None:
            return
        document = self.state_store.load({})
        if not isinstance(document, dict):
            logging.warning('Estado de sessões em .runtime ignorado (formato inesperado).')
            return
        try:
            saved_at = float(document.get('saved_at') or 0)
        except (TypeError, ValueError):
            return
        if saved_at <= 0 or self.wall_clock() - saved_at > TTL:
            return
        allowed = {item.name for item in fields(Session)} - {'touched'}
        # O tempo parado durante o reinício conta para o TTL: a sessão não
        # ganha 10 minutos novos só porque o processo foi reiniciado.
        idle_since_save = max(0.0, self.wall_clock() - saved_at)
        sessions = document.get('sessions') or {}
        if not isinstance(sessions, dict):
            logging.warning('Estado de sessões em .runtime ignorado (formato inesperado).')
            return
        for key, raw in sessions.items():
            if not isinstance(key, str) or not isinstance(raw, dict):
                continue
            # Um registro estranho não pode impedir o bot de iniciar: é descartado.
            try:
                values = {name: raw[name] for name in allowed if name in raw}
                values['tokens'] = {
                    str(token): self._tuple_actions(action)
                    for token, action in dict(values.get('tokens') or {}).items()
                }
                values['selected_obligation'] = tuple(values.get('selected_obligation') or ('', ''))
                values['touched'] = self.clock() - idle_since_save
                values['owner'] = str(values.get('owner') or key)
                self.sessions[key] = Session(**values)
                self.sessions[key].last_event = 'restored_after_restart'
            except Exception:
                self.sessions.pop(key, None)
                logging.warning('Sessão efêmera inválida foi ignorada: %s', key)

    def persist(self):
        if self.state_store is None:
            return False
        now = self.clock()
        active = {
            key: asdict(session)
            for key, session in self.sessions.items()
            if now - session.touched <= TTL
        }
        try:
            return self.state_store.save({
                'version': 1,
                'saved_at': self.wall_clock(),
                'sessions': active,
            })
        except Exception:
            logging.warning('Não foi possível persistir a sessão efêmera.', exc_info=True)
            return False

    def session(self, key):
        now = self.clock()
        for old in list(self.sessions):
            if now - self.sessions[old].touched > TTL:
                del self.sessions[old]
        if key not in self.sessions:
            if len(self.sessions) >= 100:
                del self.sessions[min(self.sessions, key=lambda k: self.sessions[k].touched)]
            self.sessions[key] = Session(self.date_provider().strftime('%Y-%m'), now, owner=key,
                                         privacy=self._privacy_preference(key))
        self.sessions[key].touched = now
        return self.sessions[key]

    @staticmethod
    def _privacy_preference(key):
        """Ocultar é preferência do titular: sobrevive a cancelar/confirmar e à expiração da sessão."""
        try:
            return bool(orient.preferencias(key).get('ocultar_valores'))
        except Exception:
            return False

    @staticmethod
    def _save_privacy_preference(key, value):
        try:
            orient.salvar_preferencia(key, 'ocultar_valores', bool(value))
        except Exception:
            logging.warning('Não foi possível guardar a preferência Ocultar.', exc_info=True)

    def invalidate(self, key):
        self.sessions.pop(key, None)
        self.persist()

    def _suspend_flow(self, s):
        """Pausa um registro em andamento sem deixar respostas soltas caírem nele."""
        if not s.draft or not s.stage:
            return False
        s.suspended_draft = copy.deepcopy(s.draft)
        s.suspended_stage = s.stage
        s.suspended_view = s.view
        s.draft = None
        s.stage = None
        return True

    def _resume_suspended(self, key):
        s = self.session(key)
        if not s.suspended_draft or not s.suspended_stage:
            raise ValueError('Não há registro pausado para retomar.')
        s.draft = s.suspended_draft
        s.stage = s.suspended_stage
        s.suspended_draft = None
        s.suspended_stage = None
        s.suspended_view = ''
        if s.draft.get('flow') == 'invoice_payment':
            if s.stage == 'invoice_confirm':
                return self.invoice_preview(key)
            return self.invoice_prompt(key)
        return self.preview(key) if s.stage == 'confirm' else self.prompt(s)

    def _paused_draft_guard(self, s):
        """Impede que um novo rascunho substitua, sem aviso, um registro pausado."""
        if s.suspended_draft and s.suspended_stage:
            return Screen('Você já tem um registro pausado. Retome de onde parou ou descarte o rascunho antes de começar outro. '
                          'Depois de descartar, repita o novo registro.',
                          [[('↩ Retomar registro', ('resume_suspended',)), ('Descartar rascunho', ('discard_suspended',))]])
        return None

    def _draft_pause_row(self, s):
        if s.suspended_draft and s.suspended_stage:
            return [('↩ Retomar registro', ('resume_suspended',)), ('Descartar rascunho', ('discard_suspended',))]
        return None

    def tokens_for(self, key, screen):
        s = self.session(key)
        s.tokens.clear()
        result = []
        for row in screen.rows:
            buttons = []
            for label, action in row:
                if isinstance(action, (tuple, list)) and action and action[0] == 'copy_text':
                    buttons.append((label, None))
                    continue
                token = 'ux:' + secrets.token_urlsafe(12)
                s.tokens[token] = action
                buttons.append((label, token))
            result.append(buttons)
        return result

    def resolve(self, key, token):
        # Do not refresh an expired draft by resolving its old token.
        s = self.sessions.get(key)
        if not s or self.clock() - s.touched > TTL:
            self.invalidate(key)
            return None
        action = s.tokens.get(token)
        if action:
            s.touched = self.clock()
        return action

    def _visible(self, s):
        """Formatador único de valores: '••••' com Ocultar ligado, dinheiro normal sem ele."""
        return (lambda v: '••••') if s.privacy else money

    def _apply_privacy(self, s, screen):
        """Com Ocultar ligado, mascara todo valor de uma tela: texto, tabela rica e rótulos de botão."""
        if not s.privacy or not isinstance(screen, Screen):
            return screen
        screen.text = mask_money(screen.text)
        if screen.rich_html:
            screen.rich_html = mask_money(screen.rich_html)
        screen.rows = [[(mask_money(label, bare=True), action) for label, action in row] for row in screen.rows]
        return screen

    # Telas cujo conteúdo depende do mês selecionado: ganham a linha de mês direta.
    _MONTH_NAV_VIEWS = frozenset({'pay', 'balance', 'history', 'closing', 'analytics', 'budgets', 'agenda'})

    def nav(self, view):
        """Rodapé compacto: [‹ Mês · 📅 Período · Mês ›] (só telas de mês) + [Início · Menu].
        O render acrescenta o Voltar à frente da última linha (ver _merge_back)."""
        rows = []
        if view in self._MONTH_NAV_VIEWS:
            rows.append([('‹ Mês', ('month', -1, view)), ('📅 Período', ('period_tools',)), ('Mês ›', ('month', 1, view))])
        rows.append([('🏠 Início', ('view', 'home')), ('☰ Menu', ('view', 'more'))])
        return rows

    @staticmethod
    def _merge_back(screen, trail):
        """Uma só linha 'Voltar · Início · Menu'; nunca um segundo Voltar para o mesmo destino."""
        top = trail[-1][0] if trail else None
        for row in screen.rows:
            for label, action in row:
                if not isinstance(action, (tuple, list)) or not action:
                    continue
                if action[0] == 'back' or str(label).startswith('↩ Voltar') or ('Voltar' in str(label) and action[0] == 'view' and len(action) > 1 and action[1] == top):
                    return
        for row in screen.rows:
            if [a for _, a in row] == [('view', 'home'), ('view', 'more')]:
                row.insert(0, ('↩ Voltar', ('back',)))
                return
        screen.rows.append([('↩ Voltar', ('back',))])

    def transactions(self, month):
        return [dict(t) for t in db.buscar_transacoes_por_competencia(month)]

    def obligations(self, month, include_review=False):
        statuses = {'revisar'} if include_review else None
        current_all = [dict(i, origem_mes=month) for i in svc.aplicar_status_checklist(
            month, svc.montar_itens_checklist_mes(month, modo='geral'))]
        # V40.2: uma cobrança individual em cartão não é uma conta de caixa.
        # O compromisso financeiro a pagar é a fatura agregada. Isso também
        # impede que cadastros antigos de cartões não reconhecidos ressuscitem
        # como dívidas individuais históricas.
        current_all = [i for i in current_all if not svc.item_checklist_eh_credito_individual(i)]
        if include_review:
            current = [i for i in current_all if i.get('status') in statuses]
            old = [dict(i, origem_mes=i.get('ano_mes_origem'))
                   for i in svc.listar_revisoes_baixas_anteriores(month)]
        else:
            # Itens em "revisar" já foram marcados como pagos. A ausência de vínculo
            # é uma revisão de conciliação, não uma conta em aberto.
            current = [i for i in current_all if i.get('status') not in {'pago', 'revisar'}]
            old = [dict(i, origem_mes=i.get('ano_mes_origem'))
                   for i in svc.listar_pendencias_abertas_anteriores(month)
                   if not svc.item_checklist_eh_credito_individual(i)]

            # RC3.0.11 - visão futura é projeção, não hipótese de inadimplência.
            # Ao navegar para um mês posterior ao calendário real, não carregamos
            # obrigações de competências futuras intermediárias e não presumimos
            # que tudo do mês atual ficará sem pagamento. Entram somente:
            #   1) pendências de meses que já terminaram; e
            #   2) obrigações do mês real que já venceram/chegaram ao vencimento.
            # Quando o calendário realmente virar, a regra normal volta a carregar
            # as obrigações ainda abertas do mês anterior.
            today = self.date_provider()
            real_month = today.strftime('%Y-%m')
            if month > real_month:
                today_iso = today.isoformat()
                projected_old = []
                for item in old:
                    origin = item.get('origem_mes') or item.get('ano_mes_origem') or ''
                    if origin < real_month:
                        projected_old.append(item)
                        continue
                    if origin == real_month:
                        due = str(item.get('data') or '')[:10]
                        if due and due <= today_iso:
                            projected_old.append(item)
                old = projected_old
        seen, items = set(), []
        for i in current + old:
            identity = (i.get('origem_mes'), i.get('chave') or i.get('codigo_origem') or i.get('codigo'))
            if identity in seen or float(i.get('valor') or 0) <= .005:
                continue
            seen.add(identity)
            items.append(i)
        return sorted(items, key=lambda i: (i.get('data') or '9999-12-31', i.get('nome') or ''))

    def render(self, key, view=None):
        s=self.session(key)
        if view:s.view=view
        if not re.fullmatch(r'[a-z_]+',s.view) or not callable(getattr(self,'screen_'+s.view,None)):
            raise ValueError('Tela desconhecida. Abra /menu novamente.')
        self._em_render=True;self._retrato=None
        try:
            with db.read_only_mode(), svc.contexto_consulta():
                screen=getattr(self,'screen_'+s.view)(s)
                if s.view not in {'home','help'} and s.trail:
                    self._merge_back(screen,s.trail)
                pause_row=self._draft_pause_row(s)
                if pause_row:
                    screen.rows.append(pause_row)
                if s.view in {'learn','learn_topics','lesson','help','help_topic','command_help','advanced_help'} and s.learning_stage and (s.fixed_edit or s.new_fixed):
                    screen.rows.append([('↩ Retomar cadastro',('learning_resume',))])
                if s.view not in _PRIVACY_EXEMPT_VIEWS:
                    screen = self._apply_privacy(s, screen)
                return screen
        finally:self._em_render=False;self._retrato=None

    def _hoje_linha(self,snap,s,real_month):
        """(texto, botão) da linha "Hoje" no Início. Só no mês vigente e sem valores."""
        if s.month!=real_month or snap.get('future'):return None,None
        from telegram_alertas import contagens
        c=contagens(snap)
        if c['vencidas']:
            n=c['vencidas'];return f'🔴 <b>Hoje:</b> {plural(n,"conta vencida","contas vencidas")}',(f'🔴 Ver {plural(n,"vencida","vencidas")}',('view','pay'))
        if c['hoje']:
            n=c['hoje'];return f'🟡 <b>Hoje:</b> {plural(n,"conta vence hoje","contas vencem hoje")}',(f'🟡 Ver {n} de hoje',('view','pay'))
        if c['amanha']:
            n=c['amanha'];return f'🟡 <b>Amanhã:</b> {plural(n,"conta vence","contas vencem")}',(f'🟡 Ver {n} de amanhã',('view','pay'))
        return '✅ <b>Hoje:</b> nenhuma conta vencendo',None

    @staticmethod
    def _sem_lancamentos():
        """Banco novo: nenhum lançamento e nenhum fixo/compromisso cadastrado."""
        try:
            return not db.buscar_ultimas_transacoes(1) and not db.listar_compromissos()
        except Exception:
            _LOG_UX.warning('Primeiro uso: não foi possível conferir se há lançamentos.', exc_info=True)
            return False

    def _primeiro_uso(self, summary):
        """Banco vazio: conduz saldos → primeiro lançamento → Início. Só orienta; nada grava."""
        if not self._sem_lancamentos():
            return None, None
        if not summary['base_configurada']:
            return ('👋 <b>Primeiros passos</b>\n'
                    '1. Informe o saldo de cada conta (o valor que aparece no app do banco).\n'
                    '2. Registre seu primeiro gasto ou entrada.\n'
                    '3. Volte aqui: o Início mostra saldo, contas a pagar e o que deve sobrar.',
                    ('🚀 1. Informar saldos', ('cash_setup_start',)))
        return ('✅ <b>Saldos informados.</b> Próximo passo: registre seu primeiro gasto ou entrada.',
                ('➕ 2. Primeiro registro', ('view', 'register')))

    @staticmethod
    def _linhas_receber_herdado(summary, visible):
        """Receita prevista de mês anterior ainda não recebida: separada do
        saldo (regra de herança de 09/11/2026). Só orienta; nada é gravado."""
        valor = float(summary.get('a_receber_herdado') or 0)
        if valor <= .005:
            return []
        meses = summary.get('a_receber_herdado_meses') or []
        origem = month_label(meses[0]) if len(meses) == 1 else 'meses anteriores'
        return [f'⏳ Previsto de {origem} não recebido · {visible(valor)}',
                f'<i>Não está no saldo. Já recebeu? Em A receber de {origem}, use Registrar recebimento '
                '(ou vincule pelo Histórico). Não vai receber? Encerre a previsão em Recorrências.</i>']

    def screen_home(self,s):
        snap=orient.coletar(self,s);m=snap['metrics']
        summary=resumir_saldo(m)
        visible=lambda v:'••••' if s.privacy else money(v)
        real_month=self.date_provider().strftime('%Y-%m')
        is_past=s.month < real_month
        falta=float(m.get('saldo_projetado') or 0)<-.005 and not m.get('revisoes_conciliacao')
        forecast='Revisar conciliação' if m.get('revisoes_conciliacao') else visible(abs(float(m['saldo_projetado'])) if falta else m['saldo_projetado'])
        closing_label='Saldo ao final do mês' if is_past else ('Deve faltar no fim do mês' if falta else 'Deve sobrar no fim do mês')
        balance_label='Saldo agora' if s.month==real_month else 'Saldo no período'
        reserve_label='Reservado para pagar' if summary['reservas_liquidas']>=0 else 'Ajustes a favor'
        text=[heading('Início',month_label(s.month)),'<i>Seu dinheiro e os compromissos do mês.</i>','',
              f'🏦 <b>{balance_label}</b>\n<b>{visible(summary["saldo_atual"])}</b>','',
              f'🧾 <b>{reserve_label}</b>\n<b>{visible(abs(summary["reservas_liquidas"]))}</b>',
              '<i>Reserva calculada para as pendências do período.</i>']
        if summary['a_receber']:
            text += [f'↗ A receber · {visible(summary["a_receber"])}']
        text += self._linhas_receber_herdado(summary, visible)
        text += ['', f'🎯 <b>{closing_label}\n{forecast}</b>',
                 '<i>Saldo + entradas previstas − reservas líquidas.</i>']
        if not summary['base_configurada']:
            text += ['', '⚠️ Toque em Ajustar saldo para informar seu dinheiro atual.']
        elif summary['herdado_auto']:
            text += ['', '⚠️ Saldo estimado. Confira em Ajustar saldo.']
        if s.month > real_month:
            text += ['', '<i>Previsão para o mês selecionado.</i>']
        # Linha "Hoje": próxima melhor ação do mês vigente, só com contagens (sem valores).
        hoje_linha,hoje_botao=self._hoje_linha(snap,s,real_month)
        if hoje_linha:text[2:2]=['',hoje_linha]
        primeiro_texto,primeiro_botao=self._primeiro_uso(summary)
        if primeiro_texto:
            text[2:2]=['',primeiro_texto]
            hoje_botao=None
        rows=[
            *([[primeiro_botao]] if primeiro_botao else []),
            *([[hoje_botao]] if hoje_botao else []),
            [('➕ Registrar',('view','register')),('🧾 A pagar',('view','pay'))],
            [('✏️ Ajustar saldo',('cash_setup_start',)),('🔎 Detalhes',('view','month_actions'))],
            [('☰ Menu',('view','more')),('👁 Mostrar' if s.privacy else '◉ Ocultar',('privacy',))],
            [('‹ Mês anterior',('month',-1,'home')),('Próximo mês ›',('month',1,'home'))],
        ]
        if s.month!=real_month:
            rows.append([('↩ Mês atual',('current_month','home'))])
        # O painel visual deixa de ser automático. Continua disponível sob demanda
        # em Mais ações, evitando repetir os mesmos números em texto + imagem.
        screen=Screen('\n'.join(text),rows,sensitive=True)
        home_rows = [('🏦 '+balance_label, visible(summary['saldo_atual']))]
        for label, value in (
            ('🟢 Entradas recebidas', m.get('entradas_realizadas')),
            ('🔴 Saídas já realizadas', m.get('saidas_imediatas_realizadas')),
            ('🟠 Compras lançadas no crédito', m.get('saidas_nao_imediatas_realizadas')),
            ('🟢 Ainda a receber', summary['a_receber']),
        ):
            if abs(float(value or 0)) > .005:
                home_rows.append((label, visible(value)))
        open_items = list(snap.get('items') or [])
        open_total = sum(float(item.get('valor') or 0) for item in open_items)
        home_rows.append(('🧾 Obrigações abertas '+superscript_number(len(open_items)), visible(open_total)))
        if not summary['base_configurada']:
            base_status = 'não configurada'
        elif summary['herdado_auto']:
            base_status = 'estimada por herança'
        else:
            base_status = 'configurada'
        screen.rich_html = (
            '<h2>Início</h2><p><i>'+month_label(s.month)+'</i></p>'
            + rich_table(('Indicador', 'Valor'), home_rows, ('🎯 '+closing_label, forecast))
            + '<details><summary>Entenda o mês</summary><p>'
              '<b>Base de saldo:</b> '+base_status+'.<br><br>'
              'Entradas e saídas realizadas já estão refletidas no saldo atual. Compras no crédito não '
              'retiram dinheiro do banco no momento da compra; elas compõem a fatura e a reserva.<br><br>'
              '<b>Obrigações abertas</b> mostra a quantidade em sobrescrito e o valor pendente. A projeção considera esses valores, '
              'créditos, pagamentos e compensações. Abra <b>A pagar</b> ou <b>Detalhes</b> para conferir.'
              '</p></details>'
        )
        return screen

    def screen_feature_guide(self,s):
        text=[heading('O que você pode fazer',month_label(s.month)), '',
              '<b>Saldo</b> — dinheiro agora e previsão do mês.',
              '<b>Registrar</b> — entrada ou despesa realizada.',
              '<b>A pagar</b> — contas e faturas abertas.',
              '<b>Fixos</b> — previsões que se repetem.',
              '<b>Histórico</b> — consultar e corrigir registros.',
              '<b>Mais recursos</b> — planejamento, conciliação e configurações.']
        return Screen('\n'.join(text),[
            [('☰ Abrir menu',('view','more')),('➕ Registrar',('view','register'))],
            [('📘 Ajuda por assunto',('view','help')),('⋯ Mais recursos',('view','resources'))],
            [('🏠 Início',('view','home'))]])

    def screen_month_actions(self,s):
        snap=orient.coletar(self,s)
        visible=self._visible(s)
        to_pay=sum(float(i['valor']) for i in snap['items'])
        text=(heading('Detalhes do mês',month_label(s.month))+'\n\n'
              f'A pagar na lista: <b>{visible(to_pay)}</b>\n\n'
              'A previsão parte do saldo atual, soma o que falta receber e desconta as reservas. '
              'A lista pode incluir valores já reservados de meses anteriores.\n\nEscolha o que quer conferir.')
        rows=[
                [('📥 Entradas do mês',('home_income',)),('💰 Entender o saldo',('view','balance'))],
                [('✏️ Ajustar saldos',('cash_setup_start',)),('🔗 Conciliação',('view','reconciliations'))],
                [('📋 Fechamento mensal',('view','closing')),('⚠️ Central de atenção',('view','attention'))],
                [('📆 Agenda',('view','agenda')),('📊 Painel',('chart','home'))],
                [('💵 A receber',('view','receivables')),('🧭 Meu plano',('view','plan'))],
                [('↻ Atualizar',('month',0,'month_actions')),('👁 Mostrar valores' if s.privacy else '◉ Ocultar resumo',('privacy',))],
                [('‹ Mês anterior',('month',-1,'month_actions')),('Próximo mês ›',('month',1,'month_actions'))],
            ]
        if s.month!=self.date_provider().strftime('%Y-%m'):
            rows.append([('↩ Mês atual',('current_month','home'))])
        rows.append([('🏠 Início',('view','home'))])
        return Screen(text,rows)

    def _attention_signals(self, s):
        """Sinais determinísticos que exigem conferência, sem criar novas regras financeiras."""
        data = orient.coletar(self, s)
        metrics = data['metrics']
        signals = []

        def add(level, code, title, detail, action, button=''):
            signals.append({'level': level, 'code': code, 'title': title, 'detail': detail, 'action': action,
                            'button': button})

        reviews = metrics.get('revisoes_conciliacao') or []
        if reviews:
            add('high', 'reconciliation', 'Conciliação precisa de conferência',
                f'{plural(len(reviews), "pendência")} {"impede" if len(reviews) == 1 else "impedem"} usar a sobra prevista como referência.',
                ('view', 'review'), 'Conferir ' + plural(len(reviews), 'pendência'))

        if not data.get('future') and data.get('overdue'):
            total = sum(float(i.get('valor') or 0) for i in data['overdue'])
            add('high', 'overdue', 'Há contas vencidas',
                f'{plural(len(data["overdue"]), "obrigação vencida", "obrigações vencidas")}, somando {money(total)}.',
                ('filter', 'pay', 'overdue'), 'Ver ' + plural(len(data["overdue"]), 'vencida', 'vencidas'))

        if not metrics.get('saldo_configurado'):
            add('medium', 'balance_base', 'Falta uma base de saldo',
                'Sem uma base de saldo confiável, a sobra prevista fica menos útil para decisão.',
                ('cash_setup_start',), 'Ajustar saldo')
        elif float(metrics.get('saldo_projetado') or 0) < 0:
            add('high', 'negative_projection', 'A projeção termina negativa',
                f'Sobra prevista de {money(metrics.get("saldo_projetado") or 0)}. Confira obrigações e entradas antes de assumir outra despesa.',
                ('view', 'balance'), 'Ver saldo previsto')

        if not data.get('future') and data.get('soon'):
            total = sum(float(i.get('valor') or 0) for i in data['soon'])
            add('medium', 'soon', 'Próximos 7 dias exigem atenção',
                f'{plural(len(data["soon"]), "obrigação", "obrigações")} no período, somando {money(total)}.',
                ('filter', 'pay', 'soon'), 'Ver ' + str(len(data["soon"])) + ' a vencer')

        exceeded = [b for b in data.get('budgets', []) if b.get('ratio', 0) >= 1]
        if exceeded:
            add('medium', 'budget', 'Um limite informado foi atingido',
                f'{plural(len(exceeded), "categoria")} {"chegou ou passou" if len(exceeded) == 1 else "chegaram ou passaram"} do limite que você configurou.',
                ('view', 'budgets'), 'Ver ' + plural(len(exceeded), 'limite atingido', 'limites atingidos'))

        order = {'high': 0, 'medium': 1}
        return sorted(signals, key=lambda item: (order.get(item['level'], 9), item['code']))

    def screen_attention(self, s):
        signals = self._attention_signals(s)
        text = [f'<b>Central de atenção · {month_label(s.month)}</b>',
                'Pontos para conferir nos registros.', '']
        rows = []
        if not signals:
            text += ['🟢 <b>Nenhum alerta encontrado nos registros.</b>']
            rows += [[('🧾 Conferir A pagar', ('view', 'pay')), ('🔎 Ver Histórico', ('view', 'history'))]]
        else:
            high = sum(item['level'] == 'high' for item in signals)
            medium = len(signals) - high
            text += [f'{plural(high, "prioridade alta", "prioridades altas")} · {plural(medium, "ponto", "pontos")} para acompanhar', '']
            for index, item in enumerate(signals, 1):
                icon = '🔴' if item['level'] == 'high' else '🟡'
                text += [f'{icon} <b>{index}. {safe(item["title"], 58)}</b>', safe(item['detail'], 220), '']
                rows.append([(item.get('button') or f'{index}. Resolver / conferir', item['action'])])
        rows += [[('📋 Fechamento mensal', ('view', 'closing')), ('🏠 Início', ('view', 'home'))]]
        return Screen('\n'.join(text), rows)

    def screen_closing(self, s):
        full=self.screen_closing_details(s)
        if s.month>self.date_provider().strftime('%Y-%m'):return full
        text=full.text.split('<b>Conferência</b>',1)[0].rstrip()
        return Screen(text,[
            [('🔎 Conferência completa',('view','closing_details'))],*self.nav('closing')])

    def screen_closing_details(self, s):
        real_month = self.date_provider().strftime('%Y-%m')
        if s.month > real_month:
            return Screen(
                f'<b>Fechamento mensal · {month_label(s.month)}</b>\n\n'
                'Esse período ainda é futuro. Fechamento usa registros realizados; para projeção, consulte Início ou A pagar.',
                [[('🏠 Início', ('view', 'home')), ('🧾 A pagar', ('view', 'pay'))], *self.nav('closing')]
            )

        data = orient.coletar(self, s)
        metrics = data['metrics']
        current = data['transactions']
        income = float(data.get('income') or 0)
        spending = float(data.get('spending') or 0)
        difference = income - spending
        open_items = data.get('items') or []
        open_total = sum(float(i.get('valor') or 0) for i in open_items)
        reviews = metrics.get('revisoes_conciliacao') or []
        archived_reviews = metrics.get('revisoes_conciliacao_arquivadas') or []
        archived_base = metrics.get('base_saldo_posterior_reconciliacao')
        categories = data.get('categories') or []
        largest = categories[0] if categories else None
        is_current = s.month == real_month
        title = 'Prévia de fechamento' if is_current else 'Fechamento mensal'
        ending = 'Revisar conciliação' if reviews else money(metrics.get('saldo_projetado') or 0)

        text = [f'<b>{title} · {month_label(s.month)}</b>',
                '<i>Resumo dos registros existentes; esta tela não fecha contas nem marca obrigações como pagas.</i>', '',
                f'📥 Entradas registradas: <b>{money(income)}</b>',
                f'📤 Despesas registradas: <b>{money(spending)}</b>',
                f'↔️ Diferença dos registros: <b>{money(difference)}</b>',
                f'💰 Saldo disponível: <b>{money(metrics.get("saldo_disponivel") or 0)}</b>',
                f'{"🔮 Sobra prevista" if is_current else "✅ Sobrou calculado"}: <b>{ending}</b>', '',
                '<b>Conferência</b>',
                f'Obrigações ainda abertas consideradas: <b>{len(open_items)}</b> · {money(open_total)}',
                f'Pendências de conciliação ativas: <b>{len(reviews)}</b>']
        cresceu = self._cresceu_linhas(s) if current else []
        if cresceu:
            at = text.index('<b>Conferência</b>')
            text[at:at] = [*cresceu, '']
        if archived_reviews and archived_base:
            text += [f'Histórico de conciliação já absorvido pela base de {month_label(archived_base)}: <b>{len(archived_reviews)}</b> {"baixa antiga" if len(archived_reviews) == 1 else "baixas antigas"}.']

        if largest:
            text += [f'Maior categoria registrada: <b>{safe(largest[0], 38)}</b> · {money(largest[1])}']
        else:
            text += ['Maior categoria registrada: sem despesas realizadas no período.']

        previous_month = month_shift(s.month, -1)
        previous = self.transactions(previous_month)
        if is_current:
            cutoff = self.date_provider().day
            previous = [t for t in previous if int(t['data'][8:10]) <= min(cutoff, calendar.monthrange(int(previous_month[:4]), int(previous_month[5:]))[1])]
            current_compare = [t for t in current if int(t['data'][8:10]) <= cutoff]
            comparison_label = f'até o dia {cutoff} nos dois meses'
        else:
            current_compare = current
            comparison_label = 'mês completo contra mês completo'
        previous_spending = sum(float(t['valor']) for t in previous if t['tipo'] == 'despesa')
        current_spending = sum(float(t['valor']) for t in current_compare if t['tipo'] == 'despesa')
        if previous_spending > 0:
            delta = current_spending - previous_spending
            pct_text = pct(abs(delta / previous_spending * 100))
            direction = 'acima' if delta >= 0 else 'abaixo'
            text += ['', f'Vs. {month_label(previous_month)}: <b>{money(abs(delta))} {direction}</b> em despesas registradas ({pct_text}), {comparison_label}.']
        else:
            text += ['', f'Vs. {month_label(previous_month)}: sem base suficiente de despesas para comparação.']

        if open_items or reviews:
            text += ['', '⚠️ Este período ainda tem itens para conferir. O resumo não transforma pendência em pagamento realizado.']
        elif not current:
            text += ['', 'Sem movimentos realizados suficientes para um fechamento detalhado.']
        else:
            text += ['', '🟢 Nenhuma pendência aberta foi encontrada pelas regras atuais para este período.']

        rows = [[('🏷 Ver categorias', ('view', 'categories')), ('🧾 Ver contas', ('view', 'pay'))],
                [('🔎 Ver lançamentos', ('view', 'history')), ('⚠️ Central de atenção', ('view', 'attention'))]]
        screen=Screen('\n'.join(text), rows + self.nav('closing'),sensitive=True)
        closing_rows = [
            ('Entradas registradas', money(income)),
            ('Despesas registradas', money(spending)),
            ('Diferença dos registros', money(difference)),
            ('Saldo disponível', money(metrics.get('saldo_disponivel') or 0)),
        ]
        conference_start = next((i for i, line in enumerate(text) if line == '<b>Conferência</b>'), len(text))
        conference = '\n'.join(text[conference_start + 1:]).strip()
        screen.rich_html = (
            '<h2>'+title+'</h2><p><i>'+month_label(s.month)+'</i></p>'
            + rich_table(('Indicador', 'Valor'), closing_rows,
                         ('Sobra prevista' if is_current else 'Sobrou calculado', ending))
            + (rich_message_html('\n'.join(cresceu)) if cresceu else '')
            + '<details><summary>Conferência do período</summary>'
            + rich_message_html(conference)
            + '</details>'
        )
        return screen

    def due_label(self, item):
        raw = item.get('data') or ''
        try:
            due = date.fromisoformat(raw[:10])
        except ValueError:
            return 'Sem vencimento informado'
        delta = (due - self.date_provider()).days
        label = 'Vence hoje' if delta == 0 else 'Vence amanhã' if delta == 1 else (
            f'Vencido há {plural(-delta, "dia")}' if delta < 0 else f'Vence em {plural(delta, "dia")}')
        return f'{due_chip(delta)} {label} · {due:%d/%m/%Y}'

    def screen_balance(self, s):
        summary=resumir_saldo(svc.obter_metricas_resultado_mes(s.month))
        visible=self._visible(s)
        current=s.month==self.date_provider().strftime('%Y-%m')
        text=[heading('Saldo',month_label(s.month)),'<i>Disponível hoje e previsão ao encerrar o período.</i>','',
              ('🏦 Saldo agora' if current else '🏦 Saldo no período')+'\n<b>'+visible(summary['saldo_atual'])+'</b>',
              '', '↗ A receber · '+visible(summary['a_receber']),
              *self._linhas_receber_herdado(summary, visible),
              '↘ Reservas líquidas · '+visible(summary['reservas_liquidas']),
              '', '🎯 <b>Saldo previsto no fim do mês\n'+('Revisar conciliação' if summary['revisar'] else visible(summary['saldo_final']))+'</b>',
              '', '💡 <b>Como usar</b>\nAjuste com o valor disponível agora no banco. Em <b>Por conta</b>, confira cada saldo; em <b>Ver cálculo</b>, entenda a previsão.']
        if not summary['base_configurada'] or summary['herdado_auto']:
            text += ['', '⚠️ Confira o dinheiro disponível em Ajustar saldo.']
        cash_note = self._cash_divergence_line(s.month, summary['saldo_atual'])
        if cash_note:
            text += ['', cash_note]
        screen=Screen('\n'.join(text),[
            [('✏️ Ajustar saldo',('cash_setup_start',)),('🏦 Por conta',('cash_accounts',s.month))],
            [('🔗 Origem do saldo',('origin','saldo')),('🔗 Origem da reserva',('origin','reserva'))],
            [('🧮 Ver cálculo',('view','balance_details'))],*self.nav('balance')],sensitive=True)
        balance_rows = [
            ('🏦 Saldo agora' if current else '🏦 Saldo no período', visible(summary['saldo_atual'])),
            ('↗ A receber', visible(summary['a_receber'])),
            ('↘ Reservas líquidas', visible(summary['reservas_liquidas'])),
        ]
        balance_total = ('Saldo previsto no fim do mês',
                         'Revisar conciliação' if summary['revisar'] else visible(summary['saldo_final']))
        screen.rich_html = (
            '<h2>Saldo</h2><p><i>'+month_label(s.month)+'</i></p>'
            + rich_table(('Indicador', 'Valor'), balance_rows, balance_total)
            + ('<p>'+cash_note+'</p>' if cash_note else '')
            + '<details><summary>Como usar</summary><p>'
              'Ajuste com o valor disponível agora no banco. Abra <b>Por conta</b> para conferir cada saldo '
              'ou <b>Ver cálculo</b> para entender a previsão.'
              '</p></details>'
        )
        return screen

    def _cash_divergence_line(self, month, consolidated):
        """Uma linha quando o Saldo consolidado e a soma de Saldos por conta não batem."""
        try:
            caixa = svc.calcular_caixa_por_conta_mes(month)
        except Exception:
            _LOG_UX.warning('Saldo: soma por conta indisponível.', exc_info=True)
            return ''
        by_account = float(caixa.get('total_disponivel') or 0)
        diff = float(consolidated or 0) - by_account
        if abs(diff) <= .005:
            return ''
        return (f'<i>Saldos por conta somam {money(by_account)}; a diferença de {money(abs(diff))} vem de movimentos '
                'sem banco definido ou de ajustes de conciliação. Confira em Por conta.</i>')

    def screen_balance_details(self, s):
        if s.privacy:
            return Screen('<b>🧮 Memória do cálculo</b>\n\nValores ocultos. A previsão usa saldo disponível + a receber − reservas líquidas.',[[('👁 Mostrar valores',('privacy',))],[('↩ Voltar',('view','balance')),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]])
        m = svc.obter_metricas_resultado_mes(s.month)
        summary = resumir_saldo(m)
        values = [('Saldo inicial livre', m['saldo_inicial']), ('Entradas recebidas', m['entradas_realizadas']),
                  ('Saídas de caixa', -m['saidas_imediatas_realizadas']), ('Disponível em caixa', m['saldo_disponivel']),
                  ('Entradas ainda previstas', m['entradas_previstas']), ('Crédito lançado', -m['saidas_nao_imediatas_realizadas']),
                  ('Despesas ainda esperadas', -m['despesas_esperadas_total'])]
        compensated = m.get('compensacao_pagamentos_fatura', 0)
        if compensated:
            values.append(('Fatura já liquidada: evitar novo desconto', compensated))
        if m.get('ajuste_reserva_faturas'):
            values.append(('Reserva conferida por cartão',m['ajuste_reserva_faturas']))
        values += [('Pendências antigas ainda a reservar', -m['pendencias_herdadas_total']),
                   ('Quanto deve sobrar', m['saldo_projetado'])]
        if m.get('ajuste_conciliacao_heranca'):
            values.insert(3,('Ajuste de previsões já herdadas',m['ajuste_conciliacao_heranca']))
        text = [heading('Como o saldo é calculado',month_label(s.month)), '',
                f'Saldo atual: <b>{money(summary["saldo_atual"])}</b>',
                f'+ Ainda a receber: <b>{money(summary["a_receber"])}</b>',
                f'− Reservas líquidas: <b>{money(summary["reservas_liquidas"])}</b>',
                f'= Saldo no fim do mês: <b>{"Revisar conciliação" if summary["revisar"] else money(summary["saldo_final"])}</b>',
                '', 'Ajustar saldo atual informa o dinheiro que está no banco agora. O assessor deriva a base do mês sem criar receita ou despesa.',
                'Saldo inicial é o dinheiro no primeiro dia do mês. Resultado do mês é a diferença entre entradas e despesas; não é o saldo das contas.',
                '', '<b>Memória dos cálculos</b>', '<b>Caixa do mês</b>']
        for label,value in values:
            if label=='Entradas ainda previstas':text += ['', '<b>Daqui até o fim do mês</b>']
            if label=='Quanto deve sobrar':text += ['']
            text += [f'{safe(label)} · <b>{money(value)}</b>']
        text += ['', 'Caixa é dinheiro registrado como disponível. Previsão considera o que ainda pode entrar e sair.',
                 'O saldo herdado é livre e previsto, com reservas. Movimentos de competências anteriores ajustam essas reservas para evitar nova contagem.',
                 'Marcações antigas sem vínculo exigem revisão. Use A pagar, A receber ou vincule um lançamento existente; confira antes de salvar.']
        screen=Screen('\n'.join(text), [
            [('Memória completa', ('legacy_raw', f'saldo geral {s.month}')),('Como interpretar',('topic','saldo'))],
            [('Saldo na abertura',('balance_initial',)),('Ver gráfico',('chart','balance'))],
            [('↩ Voltar',('view','balance')),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]],sensitive=True)
        summary_rows = [
            ('Saldo atual', money(summary['saldo_atual'])),
            ('Ainda a receber', money(summary['a_receber'])),
            ('Reservas líquidas', money(summary['reservas_liquidas'])),
        ]
        final_value = 'Revisar conciliação' if summary['revisar'] else money(summary['saldo_final'])
        screen.rich_html = (
            '<h2>Como o saldo é calculado</h2><p><i>'+month_label(s.month)+'</i></p>'
            + rich_table(('Resumo', 'Valor'), summary_rows, ('Saldo no fim do mês', final_value))
            + '<details><summary>Memória completa do cálculo</summary>'
            + rich_table(('Componente', 'Valor'), [(label, money(value)) for label, value in values])
            + '<p>Caixa é dinheiro registrado como disponível. A previsão também considera o que ainda pode entrar e sair.</p>'
              '</details>'
        )
        return screen

    def screen_pay(self, s):
        reviewing = s.pay_filter == 'review'
        real_month=self.date_provider().strftime('%Y-%m')
        if reviewing:
            items = self.obligations(s.month, include_review=True)
        else:
            # V40.2: A pagar e Central de atenção consomem o mesmo retrato.
            # Assim, se a Central disser que existem N vencidas, o filtro
            # Vencidas obrigatoriamente abre essas mesmas N obrigações.
            snapshot = orient.coletar(self, s)
            if s.pay_filter == 'overdue':
                items = list(snapshot.get('overdue') or [])
            elif s.pay_filter == 'soon':
                items = list(snapshot.get('soon') or [])
            else:
                items = list(snapshot.get('items') or [])
        if s.pay_account_filter:
            items=[i for i in items if norm(i.get('conta') or i.get('conta_pagamento'))==norm(s.pay_account_filter)]
        page = max(0, min(s.page, max(0, (len(items) - 1) // PAGE_SIZE)))
        s.page = page
        total_items = sum(float(i['valor']) for i in items)
        scope = [] if reviewing else self._pay_scope_lines(s, items, total_items)
        if reviewing:
            text = [heading('Revisar baixas',month_label(s.month)),
                    f'<b>{money(total_items)}</b> · {plural(len(items), "item", "itens")}',
                    'Já marcados pagos. Falta conferir o vínculo; não entram em A pagar.', '']
        else:
            future_projection = s.month > self.date_provider().strftime('%Y-%m')
            title = 'A pagar · projeção' if future_projection else 'A pagar'
            text = [heading(title,month_label(s.month)),
                    f'💰 <b>{money(total_items)}</b> em aberto · {plural(len(items), "item", "itens")}',
                    *scope, '']
            if future_projection:
                text += ['<i>Mês selecionado e atrasos já existentes hoje.</i>', '']
        rows = []
        visible=items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
        for index, i in enumerate(visible, page * PAGE_SIZE + 1):
            text += [f'<b>{index}. {safe(i.get("nome"), 42)} · {"≈ " if i.get("valor_estimado") else ""}{money(i["valor"])}</b>',
                     self.due_label(i)+' · '+safe(i.get('conta') or i.get('conta_pagamento') or 'Sem conta', 30)]
            origin = i.get('origem_mes') or s.month
            if origin != s.month:
                text.append(f'↳ Conta de {month_label(origin)}')
            if i.get('status')=='revisar':
                text.append('Revisar vínculo · confira o Histórico.')
            elif i.get('status')=='parcial':
                text.append('Já conciliado: '+money(i.get('valor_conciliado')))
            text.append('')
            # O número B1/B2 é apenas apresentação e pode mudar quando a lista
            # recebe outra fatura. Callbacks usam sempre a identidade estável.
            code = i.get('chave') or i.get('codigo_origem') or i.get('codigo')
            rows.append([(f'{index}. '+cortar(i.get('nome') or 'Detalhes',27), ('detail_obligation', code, origin))])
        if not items:
            if reviewing:
                text += ['Nenhuma revisão pendente.']
            elif s.pay_filter != 'all' or s.pay_account_filter:
                text += ['Nenhuma conta em aberto com este filtro.']
                rows.append([('🧹 Limpar filtros', ('clear_pay_filters',))])
            else:
                text += ['Nenhuma conta em aberto neste mês. Cadastre as contas que se repetem (aluguel, internet, '
                         'assinaturas) para ver aqui os vencimentos.']
                rows.append([('🔁 Cadastrar um fixo', ('new_fixed_start',))])
        elif reviewing:
            text += ['Use esta lista somente para conciliar registros antigos. Não registre outro pagamento para estes itens.']
        else:
            text += ['💡 <b>Próximo passo</b>\nToque na conta para conferir valor, vencimento e opções de pagamento. Se já pagou, procure o lançamento no Histórico.']
        if len(items) > PAGE_SIZE:
            text += [f'Página {page+1}/{(len(items)+PAGE_SIZE-1)//PAGE_SIZE} · mostrando {len(visible)} de {plural(len(items), "compromisso")}.']
            rows += [[('‹ Anteriores', ('page', max(0, page-1))),
                      ('Próximas ›', ('page', min(page+1, (len(items)-1)//PAGE_SIZE)))]]
        active={'all':'todas','overdue':'vencidas','soon':'próximos 7 dias','review':'revisar baixas'}[s.pay_filter]
        if s.pay_filter!='all' or s.pay_account_filter:
            text += ['Filtro: '+active+((' · '+safe(s.pay_account_filter)) if s.pay_account_filter else '')]
        rows += [[('🔎 Filtrar',('pay_tools',)),('💳 Quanto vou pagar',('pay_month',s.month,0))],*self.nav('pay')]
        screen = Screen('\n'.join(text), rows)
        screen.rich_html = self._pay_rich(s, items, page, reviewing, total_items, scope)
        return screen

    def _pay_scope_lines(self, s, items, total_items):
        """Uma linha do que o total de A pagar inclui; e por que difere de Quanto vou pagar."""
        if s.pay_filter != 'all' or s.pay_account_filter:
            return ['<i>Total só dos itens deste filtro.</i>']
        old = [i for i in items if (i.get('origem_mes') or s.month) != s.month]
        if old:
            line = (f'<i>Inclui {plural(len(old), "conta")} de meses anteriores ({money(sum(float(i["valor"]) for i in old))}). '
                    'Faturas entram pelo valor da fatura; fixos no crédito já estão dentro dela.</i>')
        else:
            line = '<i>Só contas deste mês, sem atrasos anteriores. Fixos no crédito já estão dentro da fatura.</i>'
        lines = [line]
        try:
            month_total = self._pay_month_total(s.month)
        except Exception:
            _LOG_UX.warning('A pagar: total de Quanto vou pagar indisponível.', exc_info=True)
            return lines
        if abs(month_total - total_items) > .005:
            lines.append(f'<i>Quanto vou pagar mostra {money(month_total)}: só as contas de {month_label(s.month)}, '
                         'separadas por conta, sem atrasos de meses anteriores.</i>')
        return lines

    def _pay_month_total(self, month):
        return sum(float(i.get('valor') or 0) for i in self._pay_month_open_items(month))

    def _due_group(self, item):
        """(ordem, chip, rótulo) de urgência: vencida, vence hoje/amanhã ou futura."""
        try:
            delta = (date.fromisoformat(str(item.get('data') or '')[:10]) - self.date_provider()).days
        except ValueError:
            return 2, '⚪', 'Sem vencimento ou futuras'
        chip = due_chip(delta)
        return {'🔴': (0, chip, 'Vencidas'), '🟡': (1, chip, 'Vencem hoje ou amanhã')}.get(chip, (2, chip, 'Futuras'))

    def _due_cell(self, item):
        try:
            due = date.fromisoformat(str(item.get('data') or '')[:10])
        except ValueError:
            return 'sem data'
        delta = (due - self.date_provider()).days
        suffix = f' · há {-delta} d' if delta < 0 else ' · hoje' if delta == 0 else ' · amanhã' if delta == 1 else ''
        return f'{due:%d/%m}{suffix}'

    def _pay_rich(self, s, items, page, reviewing, total_items, scope=()):
        """Tabelas por urgência (🔴/🟡/⚪) com total por grupo; <pre> se a tabela não renderizar."""
        title = 'Revisar baixas' if reviewing else 'A pagar'
        head = ('<h2>' + html.escape(title) + '</h2><p><i>' + month_label(s.month) + '</i><br>'
                + '💰 <b>' + money(total_items) + '</b> · ' + plural(len(items), 'item', 'itens') + '</p>'
                + ''.join('<p>' + line + '</p>' for line in scope))
        if not items:
            return head + '<p>' + ('Nenhuma revisão pendente.' if reviewing else 'Nenhuma conta em aberto encontrada para este período.') + '</p>'
        numbered = list(enumerate(items, 1))
        visible = [(n, i) for n, i in numbered if page * PAGE_SIZE < n <= (page + 1) * PAGE_SIZE]
        groups = {}
        for n, i in numbered:
            groups.setdefault((0, '🔎', 'Revisar vínculo') if reviewing else self._due_group(i), []).append((n, i))
        try:
            body = ''
            for key in sorted(groups):
                _, chip, label = key
                members = groups[key]
                subtotal = sum(float(i['valor']) for _, i in members)
                rows = [(f'{n}. ' + cortar(i.get('nome') or 'Conta',30), self._due_cell(i), money(i['valor']))
                        for n, i in members if (n, i) in visible]
                body += '<p><b>' + chip + ' ' + html.escape(label) + ' · ' + plural(len(members), 'conta') + '</b></p>'
                if rows:
                    body += rich_table(('Conta', 'Vence', 'Valor'), rows, ('Total ' + chip, '', money(subtotal)), ('left', 'left', 'right'))
                else:
                    body += '<p>Total do grupo: ' + money(subtotal) + ' (outra página).</p>'
            if len(items) > PAGE_SIZE:
                body += '<p><i>Página ' + str(page + 1) + '/' + str((len(items) + PAGE_SIZE - 1) // PAGE_SIZE) + '. O total de cada grupo soma todas as páginas.</i></p>'
            return head + body
        except ValueError:
            lines = [f'{n}. {cortar(i.get("nome") or "Conta",30)} · {self._due_cell(i)} · {money(i["valor"])}' for n, i in visible]
            return head + '<pre>' + html.escape('\n'.join(lines)) + '</pre>'

    def _pay_tools_screen(self,s):
        active={'all':'Todas','overdue':'Vencidas','soon':'Próximos 7 dias','review':'Revisar baixas'}[s.pay_filter]
        account=s.pay_account_filter or 'Todas as contas'
        text=(f'<b>Filtros e ferramentas · A pagar</b>\n\n'
              f'Período: {month_label(s.month)}\nFiltro: <b>{active}</b>\nConta: <b>{safe(account,50)}</b>\n\n'
              'Escolha o que deseja ver.')
        return Screen(text,[
            [('Todas',('filter','pay','all')),('Vencidas',('filter','pay','overdue')),('7 dias',('filter','pay','soon'))],
            [('Revisar baixas',('filter','pay','review')),('Filtrar conta',('accounts_for','pay'))],
            [('Limpar filtros',('clear_pay_filters',))],
            [('📊 Painel',('chart','pay')),('Checklist completo',('legacy',f'checklist completo {s.month}'))],
            [('↩ Voltar',('render_current',)),('🏠 Início',('view','home')),('☰ Menu',('view','more'))],
        ])

    def history_items(self, s):
        source = self.transactions(s.month) if s.history_basis == 'fatura' else [dict(t) for t in db.buscar_transacoes_por_mes(s.month)]
        items = sorted(source, key=lambda t: (t['data'], t['id']), reverse=True)
        if s.history_filter!='all':items=[t for t in items if t['tipo']==s.history_filter]
        if s.history_account_filter:
            items=[t for t in items if norm(t.get('conta'))==norm(s.history_account_filter)]
        if s.history_category_filter:
            items = [t for t in items if norm(t.get('categoria')) == norm(s.history_category_filter)]
        if s.search:
            q = norm(s.search)
            items = [t for t in items if q in norm(' '.join(str(t.get(k) or '') for k in ('descricao','categoria','conta')))]
        return items

    def history_internal(self, s):
        """Transferências e pagamentos de fatura do mês (por data): mexem no saldo das contas,
        mas não são gasto nem entrada. Só leitura; aparecem como linhas próprias no Histórico."""
        if s.history_filter not in {'all', 'interno'} or s.history_category_filter:
            return []
        out = []
        try:
            for tr in db.buscar_transferencias_caixa_por_mes(s.month):
                tr = dict(tr)
                out.append({'kind': 'transferencia', 'id': tr['id'], 'data': str(tr['data'])[:10], 'valor': tr['valor'],
                            'origem': tr.get('conta_origem') or '', 'destino': tr.get('conta_destino') or '',
                            'descricao': tr.get('descricao') or 'Transferência'})
            for mov in svc.pagamentos_fatura_caixa_mes(s.month):
                mov = dict(mov)
                out.append({'kind': 'fatura', 'id': mov['id'], 'data': str(mov.get('data_movimento') or '')[:10],
                            'valor': mov['valor'], 'origem': mov.get('conta_origem') or '',
                            'destino': mov.get('conta_cartao') or '', 'competencia': mov.get('ano_mes') or '',
                            'descricao': 'Pagamento da fatura ' + str(mov.get('conta_cartao') or '')})
        except Exception:
            _LOG_UX.warning('Histórico: transferências e pagamentos de fatura indisponíveis.', exc_info=True)
            return []
        if s.history_account_filter:
            wanted = norm(s.history_account_filter)
            out = [m for m in out if wanted in {norm(m['origem']), norm(m['destino'])}]
        if s.search:
            q = norm(s.search)
            out = [m for m in out if q in norm(' '.join((m['descricao'], m['origem'], m['destino'], 'transferencia pagamento fatura')))]
        return out

    @staticmethod
    def _internal_lines(m, index):
        day = f'{m["data"][8:10]}/{m["data"][5:7]}' if len(m['data']) >= 10 else 'sem data'
        if m['kind'] == 'transferencia':
            return [f'⇄ <b>{index}. Transferência · {money(m["valor"])}</b>',
                    f'{day} · {safe(m["origem"], 22)} → {safe(m["destino"], 22)} · não é gasto']
        fatura = f' · fatura de {month_label(m["competencia"])}' if re.fullmatch(r'\d{4}-\d{2}', m.get('competencia') or '') else ''
        return [f'💳 <b>{index}. {safe(m["descricao"], 40)} · {money(m["valor"])}</b>',
                f'{day} · saiu de {safe(m["origem"], 22)}{fatura} · não é gasto']

    def screen_history(self, s):
        transactions = self.history_items(s)
        internal = self.history_internal(s)
        entries = sorted([('t', t) for t in transactions] + [('i', m) for m in internal],
                         key=lambda e: (e[1]['data'], 0 if e[0] == 'i' else 1, e[1]['id']), reverse=True)
        s.page = max(0, min(s.page, max(0, (len(entries)-1)//PAGE_SIZE)))
        visible = entries[s.page*PAGE_SIZE:(s.page+1)*PAGE_SIZE]
        count = plural(len(transactions), 'lançamento')
        if internal:
            count += ' · ' + plural(len(internal), 'transferência ou pagamento de fatura', 'transferências e pagamentos de fatura')
        text = [heading('Histórico', month_label(s.month)),
                count + (f' · busca: {safe(s.search, 35)}' if s.search else ''), '']
        text.insert(1, '💳 Crédito por fatura.' if s.history_basis == 'fatura' else '📅 Por data do lançamento.')
        rows = []
        for index, (kind, t) in enumerate(visible, s.page * PAGE_SIZE + 1):
            if kind == 'i':
                text += self._internal_lines(t, index) + ['']
                continue
            sign = '+' if t['tipo'] == 'receita' else '−'
            icon='↗' if t['tipo']=='receita' else '↘'
            text += [f'{icon} <b>{index}. {safe(t.get("descricao"), 42)} · {sign} {money(t["valor"])}</b>',
                     f'{t["data"][8:10]}/{t["data"][5:7]} · {safe(t.get("conta"), 25)} · {safe(t.get("categoria"), 24)}', '']
            if eh_credito(t):
                text.insert(len(text)-1, 'Fatura: '+month_label(competencia_transacao(t))+ (f' · parcela {t.get("parcela_atual") or 1}/{t.get("parcelas_total") or 1}' if int(t.get('parcelas_total') or 1)>1 else ''))
            # Todas as ações ficam dentro do detalhe. Isso reduz a repetição de
            # botões e evita que Vincular pareça obrigatório na lista principal.
            rows.append([(f'{index}. '+cortar(t.get('descricao') or 'Detalhes',27), ('transaction',t['id']))])
        filtered = s.history_filter != 'all' or s.history_account_filter or s.history_category_filter or s.search
        if not entries:
            text.append('Nenhum lançamento com este filtro.' if filtered else
                        'Nenhum lançamento neste mês ainda. Registre uma despesa ou entrada para acompanhar aqui.')
            rows.append([('🧹 Limpar filtros', ('clear_filters',))] if filtered else [('➕ Registrar', ('view', 'register'))])
        if internal:
            text += ['<i>⇄ e 💳 mudam o saldo das contas, mas não entram em gastos nem entradas.</i>']
        if len(entries) > PAGE_SIZE:
            text += [f'Página {s.page+1}/{(len(entries)+PAGE_SIZE-1)//PAGE_SIZE} · mostrando {len(visible)} de {len(entries)}.']
            rows += [[('‹ Anteriores', ('page', max(0,s.page-1))), ('Próximos ›', ('page', min(s.page+1,(len(entries)-1)//PAGE_SIZE)))]]
        account=s.history_account_filter or 'todas as contas'
        kind=HISTORY_FILTER_LABELS[s.history_filter]
        if filtered:
            text += [f'Filtro: {kind} · {safe(account,45)}'+(f' · categoria: {safe(s.history_category_filter,35)}' if s.history_category_filter else '')+(f' · busca “{safe(s.search,25)}”' if s.search else '')]
        if entries:
            text += ['', '💡 Abra um lançamento para conferir os dados, corrigir ou relacionar a uma previsão.']
        rows += [[('🔎 Busca e filtros',('history_tools',))],*self.nav('history')]
        return Screen('\n'.join(text), rows)

    def _history_tools_screen(self,s):
        account=s.history_account_filter or 'Todas as contas'
        kind=HISTORY_FILTER_LABELS[s.history_filter].capitalize()
        search=s.search or 'Sem busca'
        text=(f'<b>Busca e filtros · Histórico</b>\n\n'
              f'Período: {month_label(s.month)}\nTipo: <b>{kind}</b>\nConta: <b>{safe(account,50)}</b>\nCategoria: <b>{safe(s.history_category_filter or "Todas",50)}</b>\nBusca: <b>{safe(search,60)}</b>\n\n'
              'Escolha o que deseja ver.')
        return Screen(text,[
            [('Todos',('filter','history','all')),('Despesas',('filter','history','despesa')),('Entradas',('filter','history','receita'))],
            [('⇄ Transferências e faturas',('filter','history','interno'))],
            [('🔎 Buscar texto',('search',)),('Filtrar conta',('accounts_for','history'))],
            [('Limpar filtros',('clear_filters',)),('Resumo visual',('chart','history'))],
            [('Por fatura' if s.history_basis == 'data' else 'Por data', ('history_basis', 'fatura' if s.history_basis == 'data' else 'data'))],
            [('↩ Voltar',('render_current',)),('🏠 Início',('view','home')),('☰ Menu',('view','more'))],
        ])

    def screen_analytics(self, s):
        end = min(date.fromisoformat(s.month+'-01').replace(day=calendar.monthrange(int(s.month[:4]),int(s.month[5:]))[1]), self.date_provider())
        current = [t for t in self.transactions(s.month) if t['data'] <= end.isoformat()]
        previous_month = month_shift(s.month, -1)
        cutoff = min(end.day, calendar.monthrange(int(previous_month[:4]),int(previous_month[5:]))[1])
        previous = [t for t in self.transactions(previous_month) if t['data'] <= f'{previous_month}-{cutoff:02d}']
        if s.month > self.date_provider().strftime('%Y-%m'):
            current, previous = [], []
        income = sum(float(t['valor']) for t in current if t['tipo']=='receita')
        spending = sum(float(t['valor']) for t in current if t['tipo']=='despesa')
        old_spending = sum(float(t['valor']) for t in previous if t['tipo']=='despesa')
        categories = defaultdict(float)
        for t in current:
            if t['tipo']=='despesa': categories[t['categoria']] += float(t['valor'])
        text = [heading('Seu dinheiro em perspectiva',month_label(s.month)),
                'Lançamentos até '+f'{end:%d/%m/%Y}' if current else 'Sem dados realizados suficientes neste período.', '']
        if current:
            text += [f'↗ Entradas · <b>{money(income)}</b>', f'↘ Despesas · <b>{money(spending)}</b>',
                     f'Diferença registrada · <b>{money(income-spending)}</b>', '', '<b>Maiores gastos</b>']
            ordered_categories=sorted(categories.items(),key=lambda x:x[1],reverse=True)
            text += [f'{index}. {safe(cat,28)} · <b>{money(value)}</b>' for index,(cat,value) in enumerate(ordered_categories[:4],1)]
            if len(ordered_categories)>4:
                text += [f'<i>Mostrando 4 de {len(ordered_categories)} categorias.</i>']
            if previous and old_spending > 0:
                comparable=sum(float(t['valor']) for t in current if t['tipo']=='despesa' and int(t['data'][8:10])<=cutoff)
                change=(comparable-old_spending)/old_spending*100
                text += ['', f'Gastos {pct(abs(change))} '+('acima' if change>=0 else 'abaixo')+f' de {month_label(previous_month)}, comparando até o dia {cutoff} nos dois meses.']
            else:
                text += ['', 'Sem base anterior suficiente para calcular uma variação percentual.']
        ordered_categories=sorted(categories.items(),key=lambda x:x[1],reverse=True)
        rows=[[('📊 Gráfico',('chart','analytics')),('🏷 Categorias',('view','categories'))]]
        if current:text += ['', *self._cresceu_linhas(s)]
        text += ['', '<i>Crédito segue a fatura escolhida.</i>']
        return Screen('\n'.join(text),rows+self.nav('analytics'))

    def _cresceu_linhas(self, s):
        """B4: top 3 categorias que mais cresceram vs. mesma janela do mês anterior (só leitura)."""
        from dashboard_metricas import variacao_categorias
        try:
            v=variacao_categorias(self,s.month,self.date_provider())
        except Exception:
            logging.warning('O que cresceu: variação por categoria indisponível.',exc_info=True)
            return []
        if v is None:return []
        lines=[f'<b>O que cresceu vs. {month_label(v["previous"])}</b> ({v["mode"]})']
        if not v['base']:
            return lines+['Sem base: não houve despesa registrada na mesma janela do mês anterior, então não calculei variação por categoria.']
        if not v['subiram']:
            lines.append('Nenhuma categoria gastou mais que na mesma janela do mês anterior.')
        for l in v['subiram']:
            if l['percent'] is None:
                parte='categoria sem gasto na janela anterior (sem base para %)'
            else:
                parte=f'+{pct(l["percent"])}'
            extra=''
            if l['um_lancamento']:
                extra=(f' · 1 lançamento de {money(l["maior"])}' if l['lancamentos']==1
                       else f' · um lançamento de {money(l["maior"])} explica a maior parte')
            lines.append(f'↑ <b>{safe(l["categoria"],28)}</b> · +{money(l["delta"])} ({parte}){extra}')
        for l in v['caiu']:
            lines.append(f'↓ {safe(l["categoria"],28)} · −{money(-l["delta"])} ({pct(abs(l["percent"]))} a menos)' if l['percent'] is not None else f'↓ {safe(l["categoria"],28)} · −{money(-l["delta"])}')
        return lines

    def screen_categories(self,s):
        end=min(date.fromisoformat(s.month+'-01').replace(day=calendar.monthrange(int(s.month[:4]),int(s.month[5:]))[1]),self.date_provider())
        transactions=[] if s.month>self.date_provider().strftime('%Y-%m') else [t for t in self.transactions(s.month) if t['tipo']=='despesa' and t['data']<=end.isoformat()]
        categories=defaultdict(float)
        for t in transactions:categories[t['categoria']]+=float(t['valor'])
        ordered=sorted(categories.items(),key=lambda x:x[1],reverse=True)
        page=max(0,min(s.page,max(0,(len(ordered)-1)//PAGE_SIZE)));s.page=page
        visible=ordered[page*PAGE_SIZE:(page+1)*PAGE_SIZE]
        text=[f'<b>Categorias · {month_label(s.month)}</b>',f'{plural(len(ordered), "categoria")} com despesa registrada.','']
        rows=[]
        for index,(category,value) in enumerate(visible,page*PAGE_SIZE+1):
            text.append(f'<b>{index}. {safe(category,38)}</b> · {money(value)}')
            rows.append([('Ver '+cortar(category,24),('category',category))])
        if not ordered:
            text+=['Nenhuma despesa registrada neste mês ainda. Registre um gasto para ver aqui onde o dinheiro foi.']
            rows.append([('➕ Registrar despesa',('start','despesa'))])
        if len(ordered)>PAGE_SIZE:
            text += ['',f'Página {page+1}/{(len(ordered)+PAGE_SIZE-1)//PAGE_SIZE} · mostrando {len(visible)} de {plural(len(ordered), "categoria")}.']
            rows.append([('‹ Anteriores',('page',max(0,page-1))),('Próximas ›',('page',min(page+1,(len(ordered)-1)//PAGE_SIZE)))])
        rows.append([('↩ Voltar',('view','analytics')),('🏠 Início',('view','home')),('☰ Menu',('view','more'))])
        return Screen('\n'.join(text),rows)

    def screen_budgets(self, s):
        metas = [dict(m) for m in db.listar_metas()]
        transactions = [t for t in self.transactions(s.month) if t['tipo']=='despesa' and t['data'] <= self.date_provider().isoformat()]
        hoje = self.date_provider()
        vigente = s.month == hoje.strftime('%Y-%m')
        text = [f'<b>Limites de gastos · {month_label(s.month)}</b>']
        if vigente:
            text.append(f'<i>Hoje é dia {hoje.day} de {calendar.monthrange(hoje.year, hoje.month)[1]}.</i>')
        text.append('')
        itens = orient.situacao_limites(metas, transactions, hoje, s.month)
        emoji = {'estourou': '🔴', 'ritmo': '🟡', 'perto': '🟡', 'ok': '🟢'}
        for i in itens[:10]:
            text += [f'{emoji[i["estado"]]} <b>{safe(i["categoria"],35)}</b>',
                     f'{orient.barra(i["ratio"])} {pct(i["ratio"]*100, 0)} · {money(i["gasto"])} de {money(i["limite"])}']
            if i['estado'] == 'estourou':
                text.append('Acima do limite em '+money(-i['restante']) if i['restante'] < 0 else 'Limite atingido.')
                if i['evento']:
                    valor, desc, qtd = i['evento']
                    text.append(f'Um único lançamento de {money(valor)}'+(f' ({safe(desc,30)})' if desc else '')
                                +(' explica o estouro.' if qtd == 1 else ' pesa mais que o excesso: sem ele ficaria dentro do limite.'))
            elif i['vigente']:
                if i['ritmo'] is not None:
                    text.append(f'Ritmo: esperado até hoje {money(i["esperado"])}; no ritmo atual fecha em ≈ {money(i["ritmo"])}'
                                +(' (acima do limite).' if i['estado'] == 'ritmo' else '.'))
                text.append(f'Restam {money(i["restante"])}'+(f' · ≈ {money(i["por_dia"])}/dia até o fim do mês' if i['por_dia'] is not None else ''))
            else:
                text.append(('Ficou dentro do limite: sobraram ' if i['restante'] >= 0 else 'Passou do limite: ')+money(abs(i['restante'])))
            text.append('')
        if not metas:text += ['Nenhum limite definido ainda. Escolha quanto quer gastar por categoria (ex.: Mercado R$ 800,00) '
                              'e acompanhe aqui o ritmo do mês.']
        if len(itens)>10:text += [f'Mostrando 10 de {len(itens)} limites. Abra a lista completa.']
        if itens:
            text += ['🟢 dentro do ritmo · 🟡 atenção (a partir de 80% ou ritmo acima do limite) · 🔴 limite atingido.',
                     '<i>O ritmo só aparece com 5 dias e 3 lançamentos na categoria.</i>']
        text += ['Despesas registradas; crédito por fatura.']
        return Screen('\n'.join(text), [[('Criar / ajustar limite',('budget_start',)),('Ver gráfico',('chart','budgets'))],[('Lista completa',('legacy','metas'))],*self.nav('budgets')])

    def _reconciliation_review_summary(self, month):
        """Detalha pendências de conciliação sem alterar qualquer registro."""
        metrics=svc.obter_metricas_resultado_mes(month)
        reviews=list(metrics.get('revisoes_conciliacao') or [])
        details=[]
        for item in reviews:
            value=0.0;account=''
            if item.get('tipo')=='baixa_antiga' and item.get('compromisso_id'):
                try:
                    target=conc.alvo(item['compromisso_id'],item['mes'])
                    value=float(target.get('valor') or 0);account=target.get('conta_pagamento') or ''
                except conc.ConciliacaoError:
                    pass  # compromisso pausado/fora da competência: valor fica 0, como antes
                except Exception:
                    logging.warning('Revisão de conciliação: valor de #C%s em %s indisponível.',
                                    item.get('compromisso_id'), item.get('mes'), exc_info=True)
            details.append(dict(item,valor=value,conta=account))
        grouped=defaultdict(lambda:{'count':0,'total':0.0})
        for item in details:
            grouped[item.get('mes') or month]['count']+=1
            grouped[item.get('mes') or month]['total']+=float(item.get('valor') or 0)
        return metrics,details,dict(grouped)

    def screen_review(self, s):
        full=self.screen_review_details(s)
        lines=full.text.splitlines()
        text='\n'.join(lines[:3])
        quality=[line for line in lines if ' sem conta ou na categoria Outros' in line or ' de lançamentos iguais para conferir' in line]
        if quality:text+='\n\n'+'\n'.join(quality)
        return Screen(text,[
            [('🔎 Ver pendências e detalhes',('view','review_details'))],
            [('🔎 Histórico',('view','history'))],*self.nav('review')])

    def screen_review_details(self, s):
        metrics,reviews,review_groups=self._reconciliation_review_summary(s.month)
        rows=self.transactions(s.month)
        missing=[t for t in rows if not t.get('conta') or t.get('categoria')=='Outros']
        grouped=defaultdict(list)
        for t in rows:
            grouped[(t['data'],t['tipo'],round(float(t['valor']),2),norm(t.get('descricao')),norm(t.get('conta')))].append(t)
        duplicate=[v for v in grouped.values() if len(v)>1]
        text=[];actions=[]
        if reviews:
            legacy=[r for r in reviews if r.get('tipo')=='baixa_antiga']
            other=[r for r in reviews if r.get('tipo')!='baixa_antiga']
            legacy_total=sum(float(r.get('valor') or 0) for r in legacy)
            text += [f'<b>Conciliação do saldo · {month_label(s.month)}</b>', '',
                     f'⚠️ <b>{plural(len(reviews), "situação", "situações")}</b> ainda {"impede" if len(reviews) == 1 else "impedem"} afirmar a sobra com confiança.']
            if legacy:
                text += [f'{len(legacy)} são baixas antigas marcadas como pagas, mas sem movimento financeiro vinculado.',
                         f'Valor histórico dessas marcações: <b>{money(legacy_total)}</b>.', '']
                for ym,data in sorted(review_groups.items()):
                    text += [f'{month_label(ym)} · {plural(data["count"], "revisão", "revisões")} · {money(data["total"])}']
                text += ['', 'Essas baixas <b>não entram novamente em A pagar</b>. O bloqueio existe porque o histórico não prova por qual movimento o dinheiro saiu.']
                current=self.date_provider().strftime('%Y-%m')
                historical_only=all((r.get('mes') or '') < current for r in legacy) and not other
                if s.month==current and historical_only:
                    text += ['', f'Se o caixa disponível atual de <b>{money(metrics["saldo_disponivel"])}</b> confere com a realidade, você pode criar uma nova base neste mês.',
                             'Isso não apaga, recria ou duplica pagamentos antigos. Apenas faz o saldo atual virar o novo ponto de verdade e deixa essas marcações históricas como auditoria.']
                    actions.append([('✅ Meu saldo atual confere',('reconcile_baseline_preview',))])
            if other:
                text += ['', f'{plural(len(other), "pendência")} {"exige" if len(other) == 1 else "exigem"} vínculo individual com um movimento real.']
                for item in other[:5]:
                    text += [('Receita e previsão semelhantes: ' if item.get('tipo')=='receita_sem_vinculo' else 'Pendência: ')+safe(item.get('nome'),40)]
                    if item.get('tipo')=='receita_sem_vinculo':
                        actions.append([(f'Revisar · '+cortar(item.get('nome') or 'lançamento',28),('link_existing',item['transacao_id']))])
            actions += [[('🔎 Revisar baixas antigas',('filter','pay','review')),('🔗 Movimentos conciliados',('view','reconciliations'))]]
            text += ['', '<i>Nenhuma correção financeira é feita sem sua confirmação.</i>']
        else:
            text=[f'<b>O que merece revisão · {month_label(s.month)}</b>', '','✅ Nenhuma pendência de conciliação bloqueia a sobra deste mês.']
            archived=metrics.get('revisoes_conciliacao_arquivadas') or []
            archived_base=metrics.get('base_saldo_posterior_reconciliacao')
            if archived and archived_base:
                text += ['', f'📦 {plural(len(archived), "baixa antiga", "baixas antigas")} já {"foi absorvida" if len(archived) == 1 else "foram absorvidas"} pela base de {month_label(archived_base)} e ficam somente na auditoria histórica.']

        # Sinais de qualidade dos lançamentos permanecem separados da conciliação.
        if not rows:
            text += ['', 'Ainda não há registros para revisar nesta competência.']
        elif missing or duplicate:
            text += ['', '<b>Qualidade dos registros</b>']
            if missing:
                text += [f'⚠️ {plural(len(missing), "registro")} sem conta ou na categoria Outros.']
                for t in missing[:4]:text += [f'{data_br(t["data"])[:5]} · {safe(t.get("descricao"),45)} · {money(t["valor"])}']
            if duplicate:
                text += [f'🔎 {plural(len(duplicate), "grupo")} de lançamentos iguais para conferir.']
                for group in duplicate[:3]:text += [f'{len(group)}× {safe(group[0].get("descricao"),36)} · {data_br(group[0]["data"])} · {money(group[0]["valor"])}']
                text += ['Valores iguais podem ser legítimos. Nenhum lançamento foi apagado.']
        actions += [[('Abrir histórico',('view','history'))]]
        return Screen('\n'.join(text),actions+self.nav('review'))

    def screen_register(self, s):
        return Screen('<b>Registrar</b>\n\nO dinheiro saiu ou entrou?\n\n💸 <b>Despesa</b> — uma compra ou pagamento realizado.\n💵 <b>Entrada recebida</b> — dinheiro que já entrou.\n🔮 <b>Simular compra</b> — avalie o impacto antes de gastar.\n🔁 <b>Novo fixo</b> — uma obrigação que se repete.\n\n<i>Você confere os dados antes de salvar.</i>',[
            [('− Despesa',('start','despesa')),('+ Entrada recebida',('start','receita'))],
            *self._register_shortcuts(),
            [('🔮 Simular compra',('start','simulate')),('🔁 Novo fixo',('new_fixed_start',))],
            [('☰ Menu',('view','more')),('🏠 Início',('view','home'))]])

    def _register_shortcuts(self):
        """Atalhos derivados do histórico (somente leitura): repetir último e frequentes.

        Tocar abre o rascunho preenchido (data de hoje) para Confirmar; nunca grava.
        Sem histórico, a tela fica como antes.
        """
        try:
            ultimo=sug.ultimo_repetivel()
            freq=sug.frequentes(self.date_provider())
        except Exception:
            return []
        rows=[]
        if ultimo:rows.append([('🔁 Repetir último',('repeat',ultimo['id']))])
        buttons=[(f'⭐ {cortar(f["descricao"],22)} · {money(f["valor"])}',('repeat',f['id'])) for f in freq]
        rows += [buttons[i:i+2] for i in range(0,len(buttons),2)]
        return rows

    def screen_more(self,s):
        return Screen('<b>Menu</b>\n\nO que você quer consultar?\n\n🏦 <b>Saldo</b> — disponível agora e previsão do mês.\n🧾 <b>A pagar</b> — pendências e vencimentos.\n📒 <b>Histórico</b> — registros e correções.\n🔁 <b>Fixos</b> — cadastros e suas vigências.\n📊 <b>Análises</b> — gastos, categorias e comparações.',[
            [('🏦 Saldo',('view','balance')),('🧾 A pagar',('view','pay'))],
            [('📒 Histórico',('view','history')),('🔁 Fixos',('fixed_list',0))],
            [('📊 Análises',('view','analytics')),('⋯ Mais recursos',('view','resources'))],
            [('📘 Ajuda',('view','help')),('🏠 Início',('view','home'))]])

    def screen_resources(self,s):
        return Screen('<b>Mais recursos</b>\n\nEscolha uma área.\n\n🧭 <b>Planejar</b> — agenda, limites e simulações.\n🔎 <b>Conferir</b> — revisões, conciliações e fechamento.\n🔐 <b>Meus dados</b> — backup, exportação e privacidade.\n💬 <b>Assessor</b> — consultas e perguntas prontas.\n\n<i>A ajuda explica os caminhos e quando usar cada recurso.</i>',[
            [('💵 A receber',('view','receivables')),('🏦 Contas e saldos',('cash_accounts',s.month))],
            [('🧭 Planejar',('view','planning_tools')),('🔎 Conferir',('view','review_tools'))],
            [('🔔 Alertas',('view','alerts')),('🔐 Meus dados',('view','data_tools'))],
            [('💬 Assessor',('view','assistant')),('📘 Ajuda',('view','help'))],
            [('🗂 Gerenciar contas',('view','accounts_manage')),('✨ Facilidades',('innovations',))],
            [('🧭 O que posso fazer?',('view','feature_guide'))],
            [('🏠 Início',('view','home')),('🔒 Bloquear',('lock',))]])

    def screen_accounts_manage(self,s):
        ativas=self.accounts();inativas=[n for n in self.accounts(incluir_inativas=True) if n not in ativas]
        linhas=['<b>🗂 Gerenciar contas</b>','','Desativar tira a conta das listas de escolha, ajuste de saldo e filtros. '
                'Lançamentos, relatórios, exportações e backup continuam com ela; dá para reativar quando quiser.','']
        linhas+=['<b>Ativas</b>']+([f'• {safe(n)}' for n in ativas] or ['Nenhuma conta ainda. Informe o saldo de um banco para começar.'])
        if inativas:linhas+=['','<b>Desativadas</b>']+[f'• {safe(n)}' for n in inativas]
        rows=[[(f'🚫 Desativar {n}',('acct_off',n)) for n in ativas[i:i+2]] for i in range(0,len(ativas),2)]
        rows+=[[(f'↩ Reativar {n}',('acct_on',n)) for n in inativas[i:i+2]] for i in range(0,len(inativas),2)]
        if not ativas:rows.append([('➕ Informar saldo de uma conta',('cash_setup_new_account',))])
        rows+=[[('↩ Voltar',('view','resources')),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]]
        return Screen('\n'.join(linhas),rows)

    def _motivos_bloqueio_conta(self,conta):
        """Motivos para NÃO desativar uma conta agora: saldo no caixa ou obrigações em aberto no mês vigente."""
        mes=self.date_provider().strftime('%Y-%m');motivos=[]
        try:
            caixa=svc.calcular_caixa_por_conta_mes(mes)
            item=next((v for n,v in caixa['contas'].items() if svc.mesma_conta_saldo(n,conta)),None)
            if item and abs(float(item['disponivel']))>.005:
                motivos.append(f'ela tem saldo de {money(item["disponivel"])} em {month_label(mes)}')
        except Exception:
            _LOG_UX.warning('Não foi possível conferir o saldo da conta antes de desativar.',exc_info=True)
        abertas=[i for i in self.obligations(mes) if norm(str(i.get('conta') or i.get('conta_pagamento') or ''))==norm(conta)]
        if abertas:motivos.append(f'há {plural(len(abertas),"conta em aberto","contas em aberto")} nela em {month_label(mes)}')
        return motivos

    def _accounts_manage_notice(self,key,aviso):
        tela=self.render(key,'accounts_manage');tela.text=aviso+'\n\n'+tela.text;return tela

    def _acct_off_confirm(self,key,conta):
        if conta not in self.accounts():return self._accounts_manage_notice(key,'Essa conta não está mais na lista ativa.')
        motivos=self._motivos_bloqueio_conta(conta)
        if motivos:
            return self._accounts_manage_notice(key,f'⚠️ Não dá para desativar <b>{safe(conta)}</b> agora: '+'; '.join(motivos)+'. Resolva isso e tente de novo.')
        return Screen(f'<b>Desativar {safe(conta)}?</b>\n\nEla some das listas de escolha, do ajuste de saldo e dos filtros. '
                      'Todo o histórico, os relatórios, as exportações e o backup continuam com ela, e você pode reativar depois.',
                      [[('✅ Desativar',('acct_off_ok',conta)),('Cancelar',('view','accounts_manage'))]])

    def _acct_off_apply(self,key,conta):
        if conta not in self.accounts():return self._accounts_manage_notice(key,'Essa conta já estava desativada.')
        motivos=self._motivos_bloqueio_conta(conta)
        if motivos:
            return self._accounts_manage_notice(key,f'⚠️ Não dá para desativar <b>{safe(conta)}</b> agora: '+'; '.join(motivos)+'.')
        contas_inativas.desativar(conta,key)
        return self._accounts_manage_notice(key,f'✅ {safe(conta)} desativada. O histórico foi mantido.')

    def _acct_on(self,key,conta):
        contas_inativas.reativar(conta,key)
        return self._accounts_manage_notice(key,f'✅ {safe(conta)} reativada.')

    def screen_planning_tools(self,s):
        return Screen(heading('Seu próximo passo',month_label(s.month))+'\n\nOrganize o que vem pela frente.',[
            [('🧭 Meu plano',('view','plan')),('🎯 Limites',('view','budgets'))],
            [('🔁 Recorrências',('view','recurring')),('📆 Agenda',('view','agenda'))],
            [('💵 A receber',('view','receivables')),('🔮 Simular compra',('start','simulate'))],
            [('↩ Voltar',('view','resources')),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]])

    def screen_review_tools(self,s):
        return Screen(heading('Confira com clareza',month_label(s.month))+'\n\nEncontre a origem dos valores e o que precisa de atenção.',[
            [('◉ Atenção',('view','attention')),('🔎 Revisar registros',('view','review'))],
            [('🔗 Conciliações',('view','reconciliations')),('📋 Fechamento',('view','closing'))],
            [('💰 Entender saldo',('view','balance')),('📊 Painel',('chart','home'))],
            [('↩ Voltar',('view','resources')),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]])

    def screen_data_tools(self,s):
        return Screen('<b>Seus dados, sob seu controle.</b>\n\nBackup para recuperar. CSV para consultar.\nOcultar valores não apaga mensagens anteriores.',[
            [('💾 Criar backup',('legacy','backup')),('📤 Exportar mês',('legacy',f'exportar csv {s.month}'))],
            [('🏦 Contas e saldos',('cash_accounts',s.month)),('⚙️ Preparar base',('view','setup'))],
            [('🩺 Saúde do assessor',('legacy','status')),('🧠 Categorias aprendidas',('view','category_rules'))],
            [('🔐 Privacidade',('topic','privacidade')),('🔒 Bloquear',('lock',))],
            [('↩ Voltar',('view','resources')),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]])

    def screen_category_rules(self,s):
        from categorias_pessoais import listar_regras
        rules=sorted(listar_regras(),key=lambda item:item['phrase'].casefold())
        if not rules:
            return Screen(
                '<b>Categorias aprendidas</b>\n\nAinda não há preferências pessoais. '
                'Quando você corrigir a categoria de um lançamento, o assessor poderá perguntar se deve aprender aquela descrição.',
                [[('↩ Voltar',('view','data_tools')),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]],
            )
        lines=['<b>Categorias aprendidas</b>','',f'{plural(len(rules), "preferência ativa", "preferências ativas")}.','',
               'Toque em uma regra para conferir antes de remover.']
        rows=[]
        for rule in rules[:20]:
            lines.append(f'• {safe(rule["phrase"],55)} → <b>{safe(rule["category"],35)}</b>')
            rows.append([(f'🗑 {cortar(rule["phrase"],28)}',('category_rule_remove',rule['phrase'],rule['category']))])
        if len(rules)>20:
            lines += ['',f'Exibindo 20 de {len(rules)} regras. Remova algumas para visualizar as demais.']
        rows.append([('↩ Voltar',('view','data_tools')),('🏠 Início',('view','home')),('☰ Menu',('view','more'))])
        return Screen('\n'.join(lines),rows)

    def screen_help(self,s):
        text=(
            '<b>Ajuda · encontre o caminho</b>\n\n'
            'Escolha um dos 6 caminhos conforme o que precisa fazer.\n\n'
            '🚀 <b>Começar</b> — preparar saldos e entender a rotina.\n'
            '➕ <b>Registrar</b> — entradas recebidas e despesas realizadas.\n'
            '💳 <b>Pagar e faturas</b> — compromissos, cartões e conciliação.\n'
            '💰 <b>Entender meu dinheiro</b> — saldo, previsão e análises.\n'
            '🔎 <b>Consultar e corrigir</b> — localizar a origem de um valor.\n'
            '⚙️ <b>Mais recursos</b> — alertas, comandos e proteção dos dados.\n\n'
            '🎓 <b>Quer aprender do zero?</b> Envie /aprender para seguir as aulas, com exemplos e conferência do resultado.\n\n'
            '<i>Consultas não alteram registros. Cada tema mostra onde usar o recurso.</i>'
        )
        rows=[
            [('🧭 Ver todos os recursos',('view','feature_guide'))],
            [('🚀 Começar',('topic','primeiros')),('➕ Registrar',('topic','registrar'))],
            [('💳 Pagar e faturas',('topic','grupo_pagar')),('💰 Entender meu dinheiro',('topic','grupo_dinheiro'))],
            [('🔎 Consultar e corrigir',('topic','grupo_consultar')),('⚙️ Mais recursos',('topic','grupo_mais'))],
            [('🏠 Início',('view','home'))],
        ]
        return Screen(text,rows)

    def pause_for_guidance(self,s):
        self._suspend_flow(s)
        if s.stage and (s.fixed_edit or s.new_fixed):
            s.learning_stage=s.stage;s.stage=None

    def open_learning(self,key,topic=''):
        s=self.session(key)
        self.pause_for_guidance(s)
        if s.stage=='ask':s.stage=None
        if not topic:return self.render(key,'learn')
        if topic=='tudo':topic='primeiros'
        if topic not in learning.LESSONS:
            return Screen('<b>🎓 Não encontrei esta aula</b>\n\nEscolha um tema no catálogo ou envie /aprender para começar.',[[('📚 Ver aulas',('view','learn_topics')),('🎓 Começar',('view','learn'))]])
        s.lesson=topic
        return self.render(key,'lesson')

    def screen_learn(self,s):
        return Screen('<b>🎓 Aprender a usar o assessor</b>\n\n'
                      '<b>Comece sem precisar decorar comandos.</b>\n'
                      '1. Prepare o saldo disponível nas contas.\n'
                      '2. Aprenda a registrar o que aconteceu.\n'
                      '3. Confira faturas, pendências e a previsão.\n\n'
                      'Cada aula traz <b>conceito → exemplo → como conferir</b> e um atalho para abrir a ferramenta.\n\n'
                      '<i>Os exemplos são ilustrativos. Abrir uma aula não cria lançamentos nem ajusta saldos.</i>',[
            [('🚀 Começar do zero',('lesson','primeiros'))],
            [('📚 Todas as aulas',('view','learn_topics')),('🗓 Rotina diária',('lesson','rotina'))],
            [('💡 Ajuda por objetivo',('view','help')),('🏠 Início',('view','home'))]])

    def screen_learn_topics(self,s):
        s.lesson_page=max(0,min(s.lesson_page,2))
        keys=learning.ORDER[s.lesson_page*5:s.lesson_page*5+5]
        lines=['<b>📚 Escolha uma aula</b>',f'Página {s.lesson_page+1}/3 · 15 temas','']
        rows=[]
        for key in keys:
            number=learning.ORDER.index(key)+1;title=learning.LESSONS[key][0]
            lines.append(f'<b>{number}. {safe(title)}</b>')
            rows.append([(f'{number}. '+title,('lesson',key))])
        rows += [[('‹ Anteriores',('lesson_page',s.lesson_page-1)),('Próximas ›',('lesson_page',s.lesson_page+1))],
                 [('🎓 Aprender',('view','learn')),('💡 Ajuda',('view','help'))]]
        return Screen('\n'.join(lines),rows)

    def screen_lesson(self,s):
        key=s.lesson;title,concept,example,check,action=learning.LESSONS[key]
        index=learning.ORDER.index(key)
        if action==('cash_accounts',):action=('cash_accounts',s.month)
        rows=[[('🧭 Abrir ferramenta',action)]]
        nav=[]
        if index:nav.append(('‹ Aula anterior',('lesson',learning.ORDER[index-1])))
        if index+1<len(learning.ORDER):nav.append(('Próxima aula ›',('lesson',learning.ORDER[index+1])))
        if nav:rows.append(nav)
        rows += [[('📚 Escolher outra aula',('view','learn_topics')),('💡 Ajuda',('view','help'))]]
        rows.append([('🎯 Praticar esta aula',('quiz',key))])
        screen=Screen(f'<b>🎓 {safe(title)}</b>\n<i>Aula {index+1}/15</i>\n\n'
                      f'💡 <b>Como funciona</b>\n{safe(concept,1000)}\n\n'
                      f'📝 <b>Exemplo ilustrativo</b>\n{safe(example,1000)}\n\n'
                      f'🔎 <b>Como conferir</b>\n{safe(check,1000)}',rows)
        from telegram_recursos import rich_summary
        screen.rich_html=rich_summary(title,safe(concept,1000),'<b>Exemplo ilustrativo</b>\n'+safe(example,1000)+'\n\n<b>Como conferir</b>\n'+safe(check,1000))
        return screen


    def begin_settlement(self,key,compromisso_id,mes):
        paused=self._paused_draft_guard(self.session(key))
        if paused is not None:return paused
        a=conc.alvo(compromisso_id,mes)
        forma = norm(a.get('forma_pagamento') or '')
        if a.get('tipo_transacao') == 'despesa' and any(term in forma for term in ('credito','cartao','fatura')):
            return Screen(
                '<b>Esta cobrança pertence à fatura do cartão.</b>\n\n'
                'Não vou criar uma nova despesa para dar baixa nela. A compra já compõe a fatura; '
                'o movimento de caixa acontece quando a fatura é paga.\n\n'
                'Abra A pagar e liquide a fatura correspondente. Se a compra já estiver no Histórico, não registre novamente.',
                [[('🧾 Voltar a A pagar',('view','pay')),('🔎 Histórico',('view','history'))],
                 [('Entender faturas',('topic','faturas'))]],
            )
        if a['restante']<=0:
            return Screen('Essa ocorrência já está conciliada. Confira os movimentos vinculados.',[[('Conciliações',('view','reconciliations'))]])
        if mes>self.date_provider().strftime('%Y-%m'):
            return Screen('Essa competência é futura. Aguarde o mês ou revise o compromisso antes de antecipar.',[[('Início',('view','home'))]])
        s=self.session(key)
        conta=a.get('conta_origem') or a.get('conta_pagamento') or ''
        forma=a.get('forma_pagamento') or ''
        s.draft=dict(tipo=a['tipo_transacao'],valor=None if a.get('variavel') else a['restante'],descricao=a['nome'],
            categoria=a.get('categoria') or ('Receita' if a['tipo_transacao']=='receita' else 'Outros'),
            conta=conta,forma_pagamento=forma,data=self.date_provider().isoformat(),parcelas_total=1,
            key=secrets.token_urlsafe(18),parsed=True,
            conciliacao={'id':a['id'],'mes':mes,'assinatura':a['assinatura']},
            _cancel_view='receivables' if a['tipo_transacao']=='receita' else 'pay')
        antigos=db.buscar_checklist_status_mes(mes)
        s.draft['_legacy_paid']=any(antigos.get(prefix+str(a['id'])) is not None and antigos[prefix+str(a['id'])]['status']=='pago' for prefix in ('C','P'))
        # De qual conta o dinheiro saiu (ou entrou) é sempre escolha do titular, como nos demais
        # registros: a conta cadastrada no fixo vira só o padrão sugerido (✦), nunca é assumida.
        if conta and norm(conta) not in {'pix','boleto','nao informada','nao informado'}:
            s.draft['_conta_padrao']=conta
        s.draft['conta']=''
        if a.get('variavel') or norm(forma) not in {'pix','debito','credito','dinheiro','transferencia'}:
            s.stage='amount' if a.get('variavel') else 'method';return self.prompt(s)  # valor variável: pergunta quanto veio
        s.stage='account';s.account_choice_page=0;return self.prompt(s)

    def begin_invoice_payment(self, key, invoice_key, month, amount=None, account=None, mode=None):
        """Abre pagamento de fatura usando a chave estável B_<SLUG>."""
        paused=self._paused_draft_guard(self.session(key))
        if paused is not None:return paused
        stable,item=svc.resolver_item_checklist(month,invoice_key)
        if not item or item.get('grupo')!='bancos':
            raise ValueError('Essa fatura não está mais disponível. Atualize A pagar.')
        summary=svc.calcular_resumo_fatura(month,item.get('conta') or item.get('nome'))
        balance=round(float(summary.get('saldo_restante') or 0),2)
        if balance<=.005:
            return Screen('Essa fatura não possui saldo pendente. Atualize A pagar para conferir o estado atual.',[[('🧾 A pagar',('view','pay')),('🔎 Histórico',('view','history'))]])
        if month>self.date_provider().strftime('%Y-%m'):
            return Screen('Essa fatura pertence a uma competência futura. O assessor não registra pagamento antecipado por este fluxo.',[[('🧾 A pagar',('view','pay'))]])
        s=self.session(key)
        account_match=''
        if account:
            account_match=next((name for name in self.accounts() if norm(name)==norm(account)), '')
        s.draft={
            'flow':'invoice_payment','invoice_key':stable,'ano_mes':month,
            'conta_cartao':summary.get('conta_cartao') or item.get('conta') or item.get('nome'),
            'saldo_esperado':balance,'valor':float(amount or 0),'conta_origem':account_match,
            'modo':mode or '', 'key':secrets.token_urlsafe(18), '_cancel_view':'pay',
        }
        s.month=month;s.account_choice_page=0
        if account and not account_match:
            s.stage='invoice_account'
            return self.invoice_prompt(key,'Não encontrei essa conta entre as contas cadastradas. Escolha uma conta existente.')
        if mode in {'total','parcial'}:
            if mode=='total':s.draft['valor']=balance
            if s.draft['valor']<=0 or (mode=='parcial' and s.draft['valor']-balance>.005):
                s.stage='invoice_amount';return self.invoice_prompt(key,'Informe um valor positivo que não ultrapasse o saldo da fatura.')
            if account:
                s.stage='invoice_confirm';return self.invoice_preview(key)
            s.stage='invoice_account';return self.invoice_prompt(key)
        s.stage='invoice_choice'
        return self.invoice_prompt(key)

    def begin_invoice_payment_from_command(self,key,parsed):
        _,tipo,valor,conta,month,origem=parsed
        if tipo not in {'pagamento_total','pagamento_parcial'}:
            return None
        stable,item=svc.resolver_fatura_checklist_por_nome(month,conta)
        if not item:
            return Screen('Não encontrei uma fatura aberta com esse nome nessa competência.',[[('🧾 Abrir A pagar',('view','pay')),('🏠 Início',('view','home'))]])
        return self.begin_invoice_payment(
            key,stable,month,
            amount=valor if tipo=='pagamento_parcial' else None,
            account=origem,
            mode='parcial' if tipo=='pagamento_parcial' else 'total',
        )

    def invoice_prompt(self,key,error=None):
        s=self.session(key);d=s.draft
        if not d or d.get('flow')!='invoice_payment':
            raise ValueError('Esse pagamento expirou. Abra a fatura novamente.')
        card=safe(d.get('conta_cartao'),55);month=d.get('ano_mes')
        if s.stage=='invoice_choice':
            return Screen(
                f'<b>Registrar pagamento da fatura</b>\n<i>{month_label(month)}</i>\n\nFatura: <b>{card}</b>\nSaldo em aberto: <b>{money(d["saldo_esperado"])}</b>\n\nEscolha quanto foi pago. Nada será registrado nesta etapa.',
                [[('Usar saldo restante',('invoice_pay_total',)),('Informar outro valor',('invoice_pay_partial',))],
                 [('Cancelar',('cancel',))]],
            )
        if s.stage=='invoice_amount':
            text=(f'<b>Qual valor foi pago?</b>\n\nFatura: {card} · {month_label(month)}\n'
                  f'Saldo em aberto na última conferência: <b>{money(d["saldo_esperado"])}</b>\n\nDigite o valor pago, por exemplo <code>250,00</code>.')
            if error:text+='\n\n⚠️ '+safe(error)
            return Screen(text,[[('‹ Voltar',('invoice_back_choice',)),('Cancelar',('cancel',))]])
        if s.stage=='invoice_account':
            names=self.accounts();per_page=8;pages=max(1,(len(names)+per_page-1)//per_page)
            s.account_choice_page=max(0,min(s.account_choice_page,pages-1))
            visible=names[s.account_choice_page*per_page:(s.account_choice_page+1)*per_page]
            rows=[[(name,('invoice_account_select',name)) for name in visible[i:i+2]] for i in range(0,len(visible),2)]
            if pages>1:
                nav=[]
                if s.account_choice_page>0:nav.append(('‹ Contas',('invoice_account_page',s.account_choice_page-1)))
                nav.append((f'{s.account_choice_page+1}/{pages}',('invoice_account_page',s.account_choice_page)))
                if s.account_choice_page+1<pages:nav.append(('Mais contas ›',('invoice_account_page',s.account_choice_page+1)))
                rows.append(nav)
            rows.append([('‹ Voltar',('invoice_back_choice',)),('Cancelar',('cancel',))])
            text=(f'<b>De qual conta saiu o pagamento?</b>\n\nFatura: {card} · {month_label(month)}\nValor: <b>{money(d["valor"])}</b>\n\nEscolha uma conta ou digite o nome exato.')
            if error:text+='\n\n⚠️ '+safe(error)
            return Screen(text,rows)
        if s.stage=='invoice_confirm':return self.invoice_preview(key)
        raise ValueError('Etapa de pagamento inválida. Abra a fatura novamente.')

    def invoice_preview(self,key):
        s=self.session(key);d=s.draft
        if not d or d.get('flow')!='invoice_payment':
            raise ValueError('Essa prévia expirou. Abra a fatura novamente.')
        stable,item=svc.resolver_item_checklist(d['ano_mes'],d['invoice_key'])
        if not item or stable!=d['invoice_key'] or item.get('grupo')!='bancos':
            raise ValueError('A fatura mudou ou não está mais disponível. Atualize A pagar.')
        current=svc.calcular_resumo_fatura(d['ano_mes'],d['conta_cartao'])
        balance=round(float(current.get('saldo_restante') or 0),2)
        if abs(balance-round(float(d['saldo_esperado']),2))>.005:
            d['saldo_esperado']=balance
            return Screen('O saldo da fatura mudou desde que você abriu o pagamento. Revise a fatura atual antes de continuar.',[[('Atualizar fatura',('invoice_restart',d['invoice_key'],d['ano_mes'])),('Cancelar',('cancel',))]])
        if d['modo']=='total':d['valor']=balance
        if d['valor']<=0 or d['valor']-balance>.005:
            s.stage='invoice_amount';return self.invoice_prompt(key,'O valor precisa ser maior que zero e não pode ultrapassar o saldo atual.')
        if not str(d.get('conta_origem') or '').strip():
            s.stage='invoice_account';return self.invoice_prompt(key)
        s.stage='invoice_confirm'
        rest=max(0.0,balance-float(d['valor']))
        text=(f'<b>Confirmar pagamento da fatura?</b>\n\n'
              f'Fatura: <b>{safe(d["conta_cartao"],55)}</b> · {month_label(d["ano_mes"])}\n'
              f'Saiu de: <b>{safe(d["conta_origem"],55)}</b>\n'
              f'Valor a registrar: <b>{money(d["valor"])}</b>\n'
              f'Saldo anterior: {money(balance)}\n'
              f'Restante após o pagamento: <b>{money(rest)}</b>\n\n'
              'Isso registra o pagamento no assessor; não executa transferência no banco. O saldo será revalidado ao confirmar.\n'
              '<i>Se essa saída já foi registrada no Histórico, cancele e confira o lançamento antes de criar outro pagamento.</i>')
        return Screen(text,[[('✅ Confirmar pagamento',('invoice_commit',d['key'])),('Editar valor',('invoice_edit_amount',))],
                            [('Trocar conta pagadora',('invoice_edit_account',)),('Cancelar',('cancel',))]])

    def begin_existing_link(self,key,ident):
        paused=self._paused_draft_guard(self.session(key))
        if paused is not None:return paused
        t=db.buscar_transacao_por_id(ident)
        if not t:raise ValueError('Lançamento não encontrado.')
        if any(v['transacao_id']==ident for v in conc.listar_vinculos()):
            return Screen('Este lançamento já está vinculado. Consulte Conciliações para revisar.',[[('Conciliações',('view','reconciliations'))]])
        t=dict(t)
        if (t.get('parcelas_total') or 1)>1:raise ValueError('Para vincular, use um lançamento individual. Parcelamentos exigem revisão por ocorrência.')
        s=self.session(key)
        fields=('tipo','valor','descricao','categoria','conta','forma_pagamento','data')
        s.draft={k:t[k] for k in fields}
        for field in ('data_compra','competencia_fatura'):
            if t.get(field):s.draft[field]=t[field]
        s.draft.update(parcelas_total=1,key=secrets.token_urlsafe(18),existing_id=ident,parsed=True,_cancel_view='history')
        s.stage='confirm';s.month=competencia_transacao(t)
        return self.target_picker(key)

    def target_picker(self,key):
        s=self.session(key);d=s.draft
        if not d:raise ValueError('O registro expirou. Abra o Histórico ou Registrar.')
        targets=[]
        for row in db.listar_compromissos(somente_ativos=True):
            if ('receita' if row['tipo'] in {'entrada_fixa','entrada_avulsa'} else 'despesa')!=d['tipo']:continue
            try:a=conc.alvo(row['id'],s.month)
            except ValueError:continue
            if a['restante']>0:targets.append(a)
        targets.sort(key=lambda a:(norm(a['nome'])!=norm(d['descricao']),a['nome']))
        text=[f'<b>Qual previsão este movimento realiza?</b>',month_label(s.month),
              f'{safe(d["descricao"])} · {money(d["valor"])}','']
        rows=[]
        s.target_page=max(0,min(s.target_page,max(0,(len(targets)-1)//6)))
        for n,a in enumerate(targets[s.target_page*6:(s.target_page+1)*6],s.target_page*6+1):
            text += [f'<b>{n}. {safe(a["nome"],45)}</b> · {money(a["restante"])}',
                     safe(a.get('conta_origem') or a.get('conta_pagamento') or 'Conta não informada',45)]
            rows.append([(f'{n}. '+cortar(a['nome'] or 'Selecionar',28),('choose_target',a['id'],s.month,d.get('key')))])
        if not targets:text+=['Nenhuma previsão aberta deste tipo neste mês.']
        if len(targets)>6:rows += [[('‹ Previsões',('target_page',max(0,s.target_page-1))),(f'{s.target_page+1}/{(len(targets)+5)//6}',('pick_target_page',)),('Mais previsões ›',('target_page',s.target_page+1))]]
        text+=['','A escolha é sua. Valores ou nomes semelhantes não criam vínculos automaticamente.']
        rows += [[('‹ Mês anterior',('target_month',-1)),('Próximo mês ›',('target_month',1))],
                 [('Voltar à prévia',('preview',)),('Cancelar',('cancel',))]]
        return Screen('\n'.join(text),rows)

    def screen_receivables(self,s):
        import compromissos as compromissos_motor
        targets=[]
        future=s.month>self.date_provider().strftime('%Y-%m')
        for item in compromissos_motor.projetar_entradas_programadas_mes(s.month):
            a=conc.alvo(item['id'],s.month)
            if a['restante']>0:targets.append(a)
        s.page=max(0,min(s.page,max(0,(len(targets)-1)//PAGE_SIZE)))
        title='Entradas previstas' if future else 'Entradas a receber'
        text=[f'<b>{title} · {month_label(s.month)}</b>',
              f'{plural(len(targets), "previsão", "previsões")} · {money(sum(a["restante"] for a in targets))}','']
        if future:text += ['Previsão futura; recebimento disponível no mês correspondente.', '']
        rows=[]
        for n,a in enumerate(targets[s.page*PAGE_SIZE:(s.page+1)*PAGE_SIZE],s.page*PAGE_SIZE+1):
            text += [f'<b>{n}. {safe(a["nome"],45)}</b> · {money(a["restante"])}',safe(a.get('conta_origem') or a.get('conta_pagamento'),45),'']
            if not future:rows.append([(f'Registrar recebimento · {n}. '+cortar(a['nome'] or '',20),('settle',a['id'],s.month))])
        if not targets:text+=['Nenhuma entrada prevista em aberto neste mês.']
        if not future:text += ['Já registrou a entrada? Vincule pelo Histórico.']
        if len(targets)>PAGE_SIZE:rows += [[('‹ Anteriores',('page',max(0,s.page-1))),('Próximas ›',('page',s.page+1))]]
        return Screen('\n'.join(text),rows+[[('Abrir Histórico',('view','history'))],*self.nav('receivables')])

    def screen_reconciliations(self,s):
        metrics=svc.obter_metricas_resultado_mes(s.month)
        pending=list(metrics.get('revisoes_conciliacao') or [])
        archived=list(metrics.get('revisoes_conciliacao_arquivadas') or [])
        archived_base=metrics.get('base_saldo_posterior_reconciliacao')
        links=[v for v in conc.listar_vinculos() if v['data'][:7]==s.month]
        s.page=max(0,min(s.page,max(0,(len(links)-1)//PAGE_SIZE)))
        text=[f'<b>Conciliação · {month_label(s.month)}</b>','']
        rows=[]
        if pending:
            text += [f'⚠️ <b>{plural(len(pending), "situação pendente", "situações pendentes")}</b> {"está bloqueando" if len(pending) == 1 else "estão bloqueando"} a sobra prevista.',
                     'Abra Resolver pendências para ver o motivo e a forma segura de regularizar.', '']
            rows.append([('🧩 Resolver pendências',('view','review'))])
        else:
            text += ['✅ Nenhuma pendência de conciliação bloqueia a sobra deste mês.', '']
        if archived and archived_base:
            text += [f'📦 {plural(len(archived), "baixa antiga", "baixas antigas")} {"permanece" if len(archived) == 1 else "permanecem"} apenas como auditoria histórica; a base de {month_label(archived_base)} já absorveu esse histórico.', '']
        text += [f'<b>Vínculos realizados</b> · {plural(len(links), "vínculo")}','']
        for n,v in enumerate(links[s.page*PAGE_SIZE:(s.page+1)*PAGE_SIZE],s.page*PAGE_SIZE+1):
            text += [f'<b>{n}. {safe(v["nome"],45)}</b> · {money(v["centavos"]/100)}',
                     f'Previsão de {month_label(v["mes"])} · movimento em {date.fromisoformat(v["data"]):%d/%m/%Y}','']
            rows.append([(f'Desvincular {n}. '+cortar(v['nome'] or '',22),('unlink_preview',v['chave']))])
        if not links:text+=['Nenhum movimento conciliado nesta competência.']
        text+=['', 'Desvincular mantém o lançamento e reabre a previsão.']
        if len(links)>PAGE_SIZE:
            text += [f'Página {s.page+1}/{(len(links)+PAGE_SIZE-1)//PAGE_SIZE} · mostrando vínculos já realizados.']
            rows += [[('‹ Anteriores',('page',max(0,s.page-1))),('Próximas ›',('page',s.page+1))]]
        return Screen('\n'.join(text),rows+self.nav('reconciliations'))

    def accounts(self,incluir_inativas=False):
        """Retorna todas as contas cadastradas sem limite artificial.

        RC3.0.16: o antigo ``[:8]`` fazia a 9a conta desaparecer dos
        filtros e tambem impedia consultas deterministicas por nome. Conta de
        origem e conta de pagamento sao coletadas separadamente para nao perder
        nenhum banco/cartao existente no cadastro.
        """
        with db.read_only_mode():
            with db.get_connection() as conn:
                rows = conn.execute('''
                    SELECT conta AS nome FROM transacoes WHERE conta IS NOT NULL
                    UNION SELECT conta FROM saldos_mensais_contas WHERE conta IS NOT NULL
                    UNION SELECT conta_pagamento FROM compromissos WHERE conta_pagamento IS NOT NULL
                        AND (conta_origem IS NULL OR trim(conta_origem)='')
                    UNION SELECT conta_origem FROM compromissos WHERE conta_origem IS NOT NULL
                    UNION SELECT conta_cartao FROM fatura_movimentos WHERE conta_cartao IS NOT NULL
                    UNION SELECT conta_origem FROM fatura_movimentos WHERE conta_origem IS NOT NULL
                ''').fetchall()
                inativas=[] if incluir_inativas else [norm(x) for x in contas_inativas.listar(conn)]
        # compromissos.conta_pagamento e o campo antigo: quando ha conta_origem, ela manda (modelo canonico);
        # nomes que so existem como destino (favorecido) nao sao contas.
        excluded={'pix','boleto','entrada','nao informada','nao informado','conta principal',*inativas}
        names={str(r[0]).strip() for r in rows if r and r[0] and norm(r[0]) not in excluded and len(str(r[0]))<=80}
        return sorted(names, key=lambda value: norm(value))

    def begin(self, key, kind):
        s=self.session(key)
        s.account_choice_page=0
        legacy_installment = kind=='parcelada'
        tipo='despesa' if kind in {'simulate','parcelada'} else kind
        s.draft={'tipo':tipo,'parcelas_total':1,
                 'simulate':kind=='simulate','key':secrets.token_urlsafe(18)}
        if legacy_installment:
            # Compatibilidade com botoes antigos do Telegram ja enviados antes da RC3.0.10.
            s.draft['_installment_choice']=True
            s.draft['_force_installment']=True
            s.draft['_installments_pending']=True
            s.draft['forma_pagamento']='crédito'
            s.stage='amount'
        else:
            # P7: "foi parcelada?" só aparece depois que a forma for crédito.
            s.stage='amount'
        return self.prompt(s)

    def prompt(self, s, error=None):
        titles={'installment_choice':('Essa despesa foi parcelada?','Escolha Sim se a compra foi dividida em parcelas. Se escolher Não, o registro segue normalmente.'),
                'amount':('1 · Qual é o valor?','Exemplo: 35,90. Para parcelas, informe o valor total da compra.'),
                'description':('2 · Com o que foi?','Exemplo: almoço iFood.\nSe quiser, complete junto: almoço iFood pix Caju.'),
                'method':('3 · Como foi pago?','Escolha a forma de pagamento.'),
                'category':('Qual categoria?','Digite a categoria deste registro.'),
                'account':('4 · Qual conta?','Escolha uma conta ou digite o nome.'),
                'date':('5 · Quando aconteceu?','Escolha a data ou digite DD/MM/AAAA.'),
                'installments':('Quantas parcelas?','Informe de 1 a 60. O valor informado é o total da compra.'),
                'search':('O que você procura?','Digite um nome, categoria ou conta. A busca usa o mês selecionado.')}
        if s.stage == 'billing_month':
            d = s.draft
            choices = opcoes_fatura(d)
            title = 'Em qual fatura entra esta compra?'
            hint = (f'Compra em {date.fromisoformat(d["data"]):%d/%m/%Y} · Crédito · {safe(d["conta"])}\n'
                    'Escolha o mês da primeira fatura. A data real da compra será preservada.')
            rows = [[(month_label(m).replace(' ', '/'), ('answer', m)) for m in choices],
                    [('‹ Etapa anterior', ('back_step',))], [('Cancelar', ('cancel',))]]
            text = registration_progress(s.stage, d) + f'<b>{title}</b>\n\n{hint}'
            if error:
                text += '\n\n⚠️ ' + safe(error)
            return Screen(text, rows)
        title,hint=titles[s.stage]
        if s.stage=='installments' and s.draft and s.draft.get('_edit'):
            hint='Informe de 1 a 60. O valor total da compra será preservado; apenas o cronograma será recalculado.'
        if s.stage=='method' and s.draft and s.draft['tipo']=='receita':
            title,hint='3 · Como você recebeu?','Escolha como o dinheiro entrou.'
        rows=[]
        if s.stage=='installment_choice':
            rows=[[('Sim',('answer','sim')),('Não',('answer','não'))]]
        if s.stage=='method':
            rows=[[('Pix',('answer','pix')),('Débito',('answer','débito'))], [('Crédito',('answer','crédito')),('Dinheiro',('answer','dinheiro'))], [('Transferência',('answer','transferência'))]]
            rows[-1].append(('Boleto',('answer','boleto')))
            if s.draft['tipo']=='receita':
                rows=[[('Pix',('answer','pix')),('Dinheiro',('answer','dinheiro'))],[('Transferência',('answer','transferência'))]]
        if s.stage=='account':
            names=sug.ordenar_contas(self.accounts())
            padrao=next((n for n in names if norm(n)==norm(s.draft.get('_conta_padrao') or '')),'') if s.draft else ''
            if padrao:
                names=[padrao]+[n for n in names if n!=padrao]
                hint += f' <i>✦ {safe(padrao)} é a conta cadastrada neste item; confirme se foi dela que saiu o dinheiro.</i>'
            per_page=8
            pages=max(1,(len(names)+per_page-1)//per_page)
            s.account_choice_page=max(0,min(s.account_choice_page,pages-1))
            visible=names[s.account_choice_page*per_page:(s.account_choice_page+1)*per_page]
            rows=[[((f'✦ {name}' if name==padrao else name),('answer',name)) for name in visible[i:i+2]] for i in range(0,len(visible),2)]
            if pages>1:
                nav=[]
                if s.account_choice_page>0:nav.append(('‹ Contas',('account_choice_page',s.account_choice_page-1)))
                nav.append((f'{s.account_choice_page+1}/{pages}',('account_choice_page',s.account_choice_page)))
                if s.account_choice_page+1<pages:nav.append(('Mais contas ›',('account_choice_page',s.account_choice_page+1)))
                rows.append(nav)
                hint += f' Página {s.account_choice_page+1}/{pages}; todas as contas continuam acessíveis.'
        if s.stage=='date':rows=[[('Hoje',('answer',self.date_provider().isoformat())),('Ontem',('answer',(self.date_provider()-timedelta(days=1)).isoformat()))]]
        if s.stage not in {'amount','search','installment_choice'}:rows += [[('‹ Etapa anterior',('back_step',))]]
        rows += [[('Cancelar',('cancel',))]]
        title=re.sub(r'^\d+ · ','',title)
        text=registration_progress(s.stage,s.draft)+f'<b>{title}</b>\n\n{hint}'
        if error:text+='\n\n⚠️ '+safe(error)
        if s.stage not in {'amount','search','installment_choice'} and s.draft:
            text+='\n\nValor: <b>'+money(s.draft.get('valor'))+'</b>'
            if s.draft.get('descricao') and s.stage!='description':
                text+='\n'+safe(s.draft['descricao'],80)
        return Screen(text,rows)

    def _registration_stage(self,d):
        """A mesma lista de campos obrigatórios para texto, botões e IA."""
        if (d.get('tipo') == 'despesa' and d.get('_ask_installment_choice')
                and '_installment_choice' not in d and norm(d.get('forma_pagamento'))=='credito'):
            return 'installment_choice'
        if not d.get('valor'):return 'amount'
        if not descricao_valida(d.get('descricao')):return 'description'
        method=norm(d.get('forma_pagamento'))
        allowed={'pix','debito','credito','dinheiro','transferencia','boleto'}
        if d.get('tipo')=='receita':allowed={'pix','dinheiro','transferencia'}
        if method not in allowed:return 'method'
        if not str(d.get('conta') or '').strip() or norm(d.get('conta')) in allowed|{'pix','boleto','credito','debito','transferencia','dinheiro','nao informada','nao informado'}:
            return 'account'
        try:day=date.fromisoformat(d.get('data') or '')
        except (ValueError,TypeError):return 'date'
        if day>self.date_provider() and not d.get('simulate'):return 'date'
        if d.get('_installments_pending') and method=='credito':return 'installments'
        if preparar_rascunho(d):return 'billing_month'
        return 'confirm'

    def _registration_category(self,description,tipo):
        # Reutiliza as regras especializadas existentes (ex.: personal/nutri),
        # sem deixar a conta ou a forma de pagamento influenciarem a categoria.
        if tipo!='receita':
            category=svc.texto_para_categoria(description)
            if category:return category
        return categoria_da_descricao(description,tipo)

    def _advance_registration(self,key):
        s=self.session(key)
        d=s.draft
        if d and not d.get('data') and not d.get('_data_ambigua') and not d.get('simulate'):
            # P7: data padrão = hoje; só é perguntada se o texto trouxe data ambígua.
            d['data']=self.date_provider().isoformat();d['_data_padrao']=True
        s.stage=self._registration_stage(s.draft)
        if s.stage=='account':s.account_choice_page=0
        if s.stage=='confirm':return self.preview(key)
        error=None
        if s.stage=='date' and s.draft.get('data'):
            error='Confira a data. Registros realizados devem ser de hoje ou antes.'
        return self.prompt(s,error)

    def _aplicar_sugestoes(self,d):
        """P3: completa conta/forma/categoria a partir do histórico (somente leitura).

        Só preenche o que falta, nunca sobrescreve escolha do titular e marca os
        campos em ``_sugerido`` (lista; nunca vai ao payload gravado).
        """
        if d.get('simulate') or not d.get('descricao') or d.get('tipo') not in {'despesa','receita'}:return
        h=sug.sugerir(d['descricao'],d['tipo'])
        if not h:return
        marcas=list(d.get('_sugerido') or [])
        forma_ok={'pix','dinheiro','transferência'} if d['tipo']=='receita' else {'pix','débito','crédito','dinheiro','transferência','boleto'}
        conta,forma=h.get('conta'),h.get('forma_pagamento')
        if conta and forma and forma in forma_ok:
            sem_conta=not str(d.get('conta') or '').strip()
            sem_forma=not d.get('forma_pagamento')
            if sem_conta and sem_forma:
                d['conta']=conta;d['forma_pagamento']=forma;marcas+=['conta','forma_pagamento']
            elif sem_conta and norm(d.get('forma_pagamento'))==norm(forma):
                d['conta']=conta;marcas.append('conta')
            elif sem_forma and norm(d.get('conta'))==norm(conta):
                d['forma_pagamento']=forma;marcas.append('forma_pagamento')
        cat=h.get('categoria')
        if cat and not d.get('_categoria_explicita') and norm(cat)!=norm(d.get('categoria')):
            d['categoria']=cat;marcas.append('categoria')
        if marcas:
            d['_sugerido']=sorted(set(marcas));d['_sugerido_amostra']=h.get('amostra',0)

    @staticmethod
    def _marcar_pergunta_parcelas(d):
        """P7: pergunta de parcelas só no crédito escolhido pelo titular (não no sugerido)."""
        if d.get('tipo')!='despesa' or d.get('simulate') or norm(d.get('forma_pagamento'))!='credito':return
        if '_installment_choice' in d or d.get('_installments_pending') or d.get('_force_installment'):return
        if (d.get('parcelas_total') or 1)>1 or 'forma_pagamento' in (d.get('_sugerido') or []):return
        d['_ask_installment_choice']=True;d['_preserve_method_on_installment_choice']=True

    def _registration_answer(self,key,text):
        """Só publica a alteração do rascunho depois de validar toda a resposta."""
        s=self.session(key);stage=s.stage;d=copy.deepcopy(s.draft)
        editing=d.get('_edit',False)
        raw=text.strip()
        try:
            if stage=='installment_choice':
                choice=norm(raw)
                if choice not in {'sim','nao'}:raise ValueError('Escolha Sim ou Não.')
                d['_installment_choice']=(choice=='sim')
                d['parcelas_total']=1
                if choice=='sim':
                    d.update(_force_installment=True,_installments_pending=True,forma_pagamento='crédito')
                else:
                    d.pop('_force_installment',None);d.pop('_installments_pending',None)
                    if not d.get('_preserve_method_on_installment_choice'):
                        d.pop('forma_pagamento',None)
            elif stage in {'amount','description','method'}:
                if editing:
                    if stage=='amount':d['valor']=valor_informado(raw)
                    elif stage=='description':
                        if not descricao_valida(raw):raise ValueError('Diga com o que foi, usando até 160 caracteres.')
                        d['descricao']=raw
                        if not d.get('_categoria_explicita'):
                            d['categoria']=self._registration_category(raw,d['tipo'])
                    else:
                        methods={'pix':'pix','debito':'débito','credito':'crédito','dinheiro':'dinheiro','transferencia':'transferência','boleto':'boleto'}
                        if norm(raw) not in methods:raise ValueError('Escolha uma das formas disponíveis.')
                        d['forma_pagamento']=methods[norm(raw)]
                else:
                    fields=extrair_campos(raw,hoje=self.date_provider(),contas=self.accounts(),
                                         tipo=d['tipo'],extrair_valor=stage=='amount')
                    required={'amount':'valor','description':'descricao','method':'forma_pagamento'}[stage]
                    if not fields.get(required):
                        message={'amount':'Informe um valor positivo, como 35,90.',
                                 'description':'Diga com o que foi, por exemplo: almoço iFood.',
                                 'method':'Escolha a forma: Pix, débito, crédito, dinheiro, transferência ou boleto.'}[stage]
                        raise ValueError(message)
                    if stage=='method':
                        fields.pop('descricao',None)
                        if not fields.get('_categoria_explicita'):fields.pop('categoria',None)
                    if fields.get('descricao') and not fields.get('_categoria_explicita'):
                        fields['categoria']=self._registration_category(fields['descricao'],d['tipo'])
                    if d.get('_categoria_explicita') and not fields.get('_categoria_explicita'):
                        fields.pop('categoria',None)
                    d.update(fields)
                    if 'parcelas_total' in fields:
                        d.pop('_installments_pending',None)
                    if stage=='description' and fields.get('descricao'):
                        self._aplicar_sugestoes(d)
            elif stage=='category':
                if not raw or len(raw)>80:raise ValueError('Use uma categoria de até 80 caracteres.')
                d['categoria']=validar_campo_textual('categoria',raw);d['_categoria_explicita']=True
            elif stage=='account':
                validar_campo_textual('conta',raw)
                if not raw or len(raw)>80:raise ValueError('Use um nome de conta de até 80 caracteres.')
                if norm(raw) in {'pix','boleto','credito','debito','dinheiro','transferencia'}:
                    raise ValueError('Informe a conta, por exemplo Caju ou Itaú. A forma de pagamento é um campo separado.')
                if editing:
                    d['conta']=raw
                else:
                    fields=extrair_campos(raw,hoje=self.date_provider(),contas=self.accounts(),tipo=d['tipo'],extrair_valor=False)
                    if fields.get('conta'):
                        for field in ('conta','forma_pagamento','data'):
                            if field in fields:d[field]=fields[field]
                    elif fields.get('forma_pagamento') or fields.get('data'):
                        raise ValueError('Faltou o nome da conta. Exemplo: Caju ou Itaú.')
                    else:d['conta']=raw
            elif stage=='date':
                day=data_informada(raw,self.date_provider())
                if day>self.date_provider().isoformat() and not d.get('simulate'):
                    raise ValueError('Registros realizados devem ser de hoje ou antes. Use compromissos para previsões futuras.')
                d['data']=day
            elif stage=='billing_month':
                if not eh_credito(d):
                    raise ValueError('Esta escolha e exclusiva de despesas no credito.')
                choices = opcoes_fatura(d)
                aliases = {norm(month_label(m)): m for m in choices}
                aliases.update({norm(month_label(m).replace(' ', '/')): m for m in choices})
                aliases.update({'mes vigente': choices[0], 'mes atual': choices[0]})
                if len(choices)>1:
                    aliases['proximo mes'] = choices[1]
                selected = aliases.get(norm(raw), raw)
                if selected not in choices:
                    raise ValueError('Escolha uma das faturas exibidas nos botoes.')
                d['competencia_fatura'] = selected
                d['data_compra'] = d['data']
                d['_fatura_contexto'] = contexto_escolha(d)
            elif stage=='installments':
                if not re.fullmatch(r'\d{1,2}',raw) or not 1<=int(raw)<=60:raise ValueError('Use de 1 a 60 parcelas.')
                d['parcelas_total']=int(raw);d.pop('_installments_pending',None)
                if int(raw)==1:d.pop('_force_installment',None)
            else:raise ValueError('Abra o registro novamente.')
            if d.get('tipo')=='receita' and norm(d.get('forma_pagamento')) in {'credito','debito','boleto'}:
                raise ValueError('Para recebimentos, escolha Pix, dinheiro ou transferência.')
            if (d.get('parcelas_total',1)>1 or d.get('_force_installment')) and d.get('forma_pagamento')!='crédito':
                raise ValueError('Esta compra está parcelada. Mantenha crédito ou recomece o registro à vista.')
            if d.get('valor') and round(d['valor']*100)<d.get('parcelas_total',1):
                raise ValueError('O total precisa permitir pelo menos um centavo por parcela.')
            d.pop('_edit',None)
            marca={'method':'forma_pagamento','account':'conta','category':'categoria'}.get(stage)
            if marca and d.get('_sugerido'):
                d['_sugerido']=[x for x in d['_sugerido'] if x!=marca]
            if not editing and stage in {'amount','description','method','account'}:
                self._marcar_pergunta_parcelas(d)
            if editing or stage == 'billing_month':
                d['key'] = secrets.token_urlsafe(18)
            s.draft=d
            return self._advance_registration(key)
        except (ValueError,TypeError,KeyError) as exc:
            return self.prompt(s,str(exc))

    def answer(self,key,text):
        s=self.session(key)
        if str(s.stage or '').startswith('media_transfer_'):
            from telegram_midia import answer
            try:return answer(self,key,text)
            except (ValueError,TypeError) as exc:
                rows=[[('↩ Voltar aos dados',('media_transfer_edit',s.media_review['nonce']))]] if s.media_review else [[('🏠 Início',('view','home'))]]
                return Screen(str(exc),rows)
        if s.stage=='cash_setup_account_name':
            account=validar_campo_textual('conta',text)
            if len(account)>80:raise ValueError('Use um nome de conta com até 80 caracteres.')
            account=svc.normalizar_conta_caixa(account)
            if account==svc.CONTA_SEM_BANCO_DEFINIDO or norm(account)=='boleto':
                raise ValueError('Informe o nome do banco ou da conta, como Itaú, Nubank ou carteira.')
            return self._cash_setup_account(key,account)
        if s.draft and s.draft.get('flow')=='invoice_payment':
            if s.stage=='invoice_amount':
                try:value=float(parse_money(text))
                except ValueError:return self.invoice_prompt(key,'Use um valor como 250,00.')
                if value<=0 or value-float(s.draft.get('saldo_esperado') or 0)>.005:
                    return self.invoice_prompt(key,'O valor precisa ser maior que zero e não pode ultrapassar o saldo da fatura.')
                s.draft['valor']=value;s.draft['modo']='parcial';s.stage='invoice_account';s.account_choice_page=0
                return self.invoice_prompt(key)
            if s.stage=='invoice_account':
                account=str(text or '').strip()
                if not account or len(account)>80:return self.invoice_prompt(key,'Informe uma conta válida com até 80 caracteres.')
                matched=next((name for name in self.accounts() if norm(name)==norm(account)), '')
                if not matched:return self.invoice_prompt(key,'Não encontrei essa conta. Escolha uma conta cadastrada ou digite o nome exatamente como aparece na lista.')
                s.draft['conta_origem']=matched;s.stage='invoice_confirm'
                return self.invoice_preview(key)
            if s.stage=='invoice_confirm':
                return Screen('Use os botões para confirmar, editar ou cancelar este pagamento.',[[('Voltar à prévia',('invoice_preview',)),('Cancelar',('cancel',))]])
            if s.stage=='invoice_choice':
                return self.invoice_prompt(key,'Use os botões para escolher pagamento total ou outro valor.')
        if s.stage=='initial_balance':
            try:value=float(parse_money(text,allow_negative=True))
            except ValueError:return Screen('Use um valor como 1000,00, zero ou -100,00 para saldo negativo.',[[('Cancelar',('cancel',))]])
            if abs(value)>100000000:return Screen('Use um saldo de até R$ 100 milhões em valor absoluto.',[[('Cancelar',('cancel',))]])
            s.settings_draft['amount']=value;s.stage='confirm_balance'
            return Screen('<b>Confirmar saldo inicial livre?</b>\n\n'+month_label(s.month)+'\n<b>'+money(value)+'</b>\n\nIsso define uma nova base para a herança a partir desse mês. Não é uma receita e não altera os saldos manuais por conta. Confira antes de substituir.',[[('Confirmar saldo',('save_balance',)),('Cancelar',('cancel',))]])
        if s.stage=='cash_setup_value':
            try:value=float(parse_money(text,allow_negative=True))
            except ValueError:return Screen('Use um valor como 530,28, zero ou -100,00.',[[('Cancelar',('cancel',))]])
            if abs(value)>100000000:return Screen('Use um saldo de até R$ 100 milhões em valor absoluto.',[[('Cancelar',('cancel',))]])
            from saldos_edicao import capturar
            s.settings_draft['expected_cash']=capturar(s.settings_draft['month'])
            s.settings_draft['pending_value']=value;s.stage='cash_setup_confirm'
            account=s.settings_draft['accounts'][s.settings_draft['index']]
            return Screen(f'<b>Confirmar saldo atual?</b>\n\n{safe(account)}\n<b>{money(value)}</b>\n\nEste é o valor que você vê agora no banco. O assessor calcula a base do mês para não contar novamente movimentos já registrados.',[[('Confirmar',('cash_setup_commit',)),('Corrigir valor',('cash_setup_edit',))],[('Cancelar',('cancel',))]])
        if s.stage=='cash_setup_confirm':return Screen('Use os botões para confirmar ou cancelar.',[[('Cancelar',('cancel',))]])
        if s.stage=='ask':return self.question_result(key,text)
        if s.stage=='account_search':
            value=text.strip()[:80]
            if s.filter_view=='pay':s.pay_account_filter=value
            else:s.history_account_filter=value
            s.stage=None;s.page=0
            return self.render(key,s.filter_view)
        if s.stage=='alert_hours':
            parts=text.strip().split()
            if len(parts)!=4 or not all(re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',v) for v in parts):
                return Screen('Use quatro horários HH:MM: agenda, fechamento, início e fim do silêncio. Exemplo: 09:00 20:00 23:00 08:00',[[('Cancelar',('cancel',))]])
            quiet={'silencio_inicio':parts[2],'silencio_fim':parts[3]}
            blocked=[label for label,hour in (('agenda',parts[0]),('fechamento',parts[1])) if orient.em_silencio(hour,quiet)]
            if blocked:
                return Screen('O horário de '+' e de '.join(blocked)+' fica dentro do silêncio ('+parts[2]+'–'+parts[3]+') e o aviso nunca seria enviado. '
                              'Escolha horários fora do silêncio. Exemplo: 09:00 20:00 23:00 08:00',[[('Cancelar',('cancel',))]])
            s.settings_draft=dict(zip(['hora_manha','hora_noite','silencio_inicio','silencio_fim'],parts));s.stage='confirm_settings'
            weekly=orient.preferencias(s.owner).get('hora_semana')
            warning=('\n\n⚠️ A revisão de domingo ('+weekly+') fica dentro desse silêncio e não será enviada.') if weekly and orient.em_silencio(weekly,quiet) else ''
            return Screen('Confirmar horários?\nAgenda: '+parts[0]+'\nFechamento: '+parts[1]+'\nSilêncio: '+parts[2]+'–'+parts[3]+warning,[[('Salvar horários',('save_hours',)),('Cancelar',('cancel',))]])
        if s.stage=='fix_date' and s.settings_draft and s.settings_draft.get('tid'):
            tid=int(s.settings_draft['tid'])
            try:nova=data_informada(text,self.date_provider())
            except ValueError as exc:
                return Screen(safe(str(exc))+'\n\nDigite a data de novo ou cancele.',[[('Cancelar',('transaction',tid))]])
            s.stage=None;s.settings_draft=None
            return self._data_previa(s,tid,nova)
        if s.stage=='budget_category':
            if not text.strip() or len(text.strip())>80:return Screen('Informe uma categoria com até 80 caracteres.',[[('Cancelar',('cancel',))]])
            s.settings_draft={'category':text.strip()};s.stage='budget_amount'
            return Screen('Qual será o limite dessa categoria? Informe seu valor real.',[[('Cancelar',('cancel',))]])
        if s.stage=='budget_amount':
            try:amount=float(parse_money(text))
            except ValueError:return Screen('Use um valor positivo, como 800,00.',[[('Cancelar',('cancel',))]])
            if amount>100000000:return Screen('Use um limite menor que R$ 100 milhões.',[[('Cancelar',('cancel',))]])
            s.settings_draft['amount']=amount;s.stage='confirm_budget'
            return Screen('Definir limite de <b>'+safe(s.settings_draft['category'])+'</b> em <b>'+money(amount)+'</b>?\nIsso substitui o limite anterior da categoria; não cria despesa.',[[('Confirmar limite',('save_budget',)),('Cancelar',('cancel',))]])
        if s.stage in {'confirm_settings','confirm_budget','confirm_balance'}:return Screen('Use os botões para confirmar ou cancelar.',[[('Cancelar',('cancel',))]])
        if s.stage=='search':
            s.search=text.strip()[:80];s.stage=None;s.page=0
            return self.render(key,'history')
        d=s.draft
        if d and s.stage=='confirm' and norm(text).strip(' .!') in {'confirmar','confirmo','salvar','confirmar registro'}:
            # Texto nunca grava: a gravação exige o botão Salvar com a chave do
            # rascunho. Reexibimos a prévia (somente leitura) com o botão ativo.
            return self.preview(key)
        if not d or s.stage=='confirm':
            return Screen('Use os botões para confirmar ou cancelar o registro revisado.',[[('Revisar',('preview',)),('Cancelar',('cancel',))]])
        return self._registration_answer(key,text)

    def payload(self,d):
        return {k:v for k,v in d.items() if not k.startswith('_') and k not in {'simulate','key','parsed','existing_id','ai_interpreted'}}

    def _aviso_saldo_negativo(self,t):
        """Avisa (sem bloquear) quando uma saída imediata deixaria o caixa da conta negativo.

        Só vale para quem já acompanha saldos por conta (existe alguma base cadastrada)."""
        try:
            if t.get('tipo')!='despesa' or not svc.transacao_afeta_saldo_disponivel(t):return ''
            with db.read_only_mode():
                with db.get_connection() as c:
                    if not c.execute('SELECT 1 FROM saldos_mensais_contas LIMIT 1').fetchone():return ''
                caixa=svc.calcular_caixa_por_conta_mes(str(t['data'])[:7])
            item=next((v for nome,v in caixa['contas'].items() if svc.mesma_conta_saldo(nome,t['conta'])),None)
            atual=float(item['disponivel']) if item else 0.0
            depois=round(atual-float(t['valor']),2)
            if depois>=-.005:return ''
            return (f'⚠️ <b>O saldo de {safe(t["conta"])} ficaria negativo</b>: {money(depois)} depois deste pagamento '
                    f'(agora: {money(atual)}). Se o dinheiro saiu de outra conta, troque a conta antes de salvar.')
        except Exception:
            _LOG_UX.warning('Aviso de saldo negativo indisponível.',exc_info=True)
            return ''

    def preview(self,key):
        s=self.session(key);d=s.draft
        if not d:return Screen('Esse registro expirou. Comece novamente.',[[('Registrar',('view','register'))]])
        missing=self._registration_stage(d)
        if missing!='confirm':
            s.stage=missing
            return self.prompt(s)
        try:t=validar_transacao(self.payload(d))
        except (ValueError,TypeError,KeyError) as exc:
            return Screen('Não é possível confirmar: '+safe(exc),[[('Recomeçar',('start',d['tipo'])),('Cancelar',('cancel',))]])
        s.stage='confirm'
        marcas=set(d.get('_sugerido') or [])
        star=lambda campo:' ✦' if campo in marcas else ''
        title='Simulação · nada será gravado' if d.get('simulate') else 'Confira antes de salvar'
        text=[registration_progress('confirm',d)+f'<b>{title}</b>', '', f'<b>{safe(t["descricao"])}</b>', f'<b>{money(t["valor"])}</b> · '+('entrada recebida' if t['tipo']=='receita' else 'despesa'),
              f'{safe(t["categoria"])}{star("categoria")} · {safe(t["forma_pagamento"])}{star("forma_pagamento")}', f'Conta: {safe(t["conta"])}{star("conta")}',
              f'Data: {date.fromisoformat(t["data"]):%d/%m/%Y}']
        if marcas:
            n=d.get('_sugerido_amostra') or 0
            text.insert(text.index(f'Data: {date.fromisoformat(t["data"]):%d/%m/%Y}')+1,f'✦ <i>sugerido pelo seu histórico ({plural(n,"lançamento","lançamentos")} de “{safe(t["descricao"],40)}”). Toque para trocar.</i>')
        if eh_credito(t):
            text[-1] = f'Data da compra: {date.fromisoformat(data_real_compra(t)):%d/%m/%Y}'
            text.append('Fatura escolhida: <b>'+month_label(competencia_transacao(t)).replace(' ', '/')+'</b>')
        if t['parcelas_total']>1:
            parcelas = installment_plan(t)
            primeira, ultima = parcelas[0], parcelas[-1]
            restante = (sum(p['valor_centavos'] for p in parcelas) - primeira['valor_centavos']) / 100
            text += [
                '',
                '<b>💳 Parcelamento</b>',
                f'<b>{installment_distribution_text(parcelas)}</b>',
                f'1ª parcela: {month_label(primeira["data"].strftime("%Y-%m"))} · {money(primeira["valor"])}',
                f'Última parcela: {month_label(ultima["data"].strftime("%Y-%m"))} · {money(ultima["valor"])}',
                f'Total da compra: <b>{money(t["valor"])}</b>',
                f'Impacto na primeira fatura: <b>{money(primeira["valor"])}</b>',
                f'Restante após a 1ª parcela: {money(restante)}',
                'Os centavos são distribuídos automaticamente sem alterar o total da compra.',
            ]
        with db.read_only_mode():
            duplicate=None if d.get('existing_id') else buscar_duplicata(t)
        if duplicate:
            quando=duplicate['data'];quando=f'{quando[8:10]}/{quando[5:7]}'
            text+=['',f'⚠️ <b>Parece duplicado de um lançamento existente</b> ({quando}): {safe(duplicate["descricao"],40)} · {money(duplicate["valor_total_parcelamento"] or duplicate["valor"])}.','Se é outro gasto de verdade, salve mesmo assim; nada foi bloqueado.']
        if not d.get('simulate') and not d.get('existing_id'):
            aviso=self._aviso_saldo_negativo(t)
            if aviso:text+=['',aviso]
            if contas_inativas.esta_inativa(t['conta']):
                text+=['',f'⚠️ <b>A conta {safe(t["conta"])} está desativada</b>. Troque a conta antes de salvar ou reative em Mais recursos → Gerenciar contas.']
        if t['tipo']=='receita':text+=['','Se existe uma receita prevista para esse recebimento, revise a previsão para evitar duplicidade.']
        if d.get('conciliacao'):
            a=conc.alvo(d['conciliacao']['id'],d['conciliacao']['mes'])
            text+=['',f'<b>Vinculado a {safe(a["nome"])}</b>',f'Competência: {month_label(a["mes"])}',
                   f'Estimativa: ≈ {money(a["estimativa"])} · valor real desta baixa: {money(t["valor"])}' if a.get('variavel') else f'Em aberto: {money(a["restante"])} · após esta baixa: {money(a["restante"]-t["valor"])}', *([x] if (x:=efeito_baixa.previa(t,money)) else [])]
            if d.get('_legacy_paid'):
                text+=['','⚠️ Já havia marcação de pago. Se o lançamento existe, cancele e use Histórico → Vincular. Confirmar aqui cria outro movimento.']
            if (t['valor']>a['restante'] and not a.get('variavel')) or a['assinatura']!=d['conciliacao']['assinatura']:
                return Screen('O valor em aberto mudou ou é menor que o lançamento. Revise a prévia.',[[('Editar valor',('edit','amount')),('Cancelar',('cancel',))]])
        elif not d.get('simulate'):
            text+=['','Se este movimento corresponde a uma previsão, você pode relacioná-lo antes de salvar.']
        text+=['','Esse lançamento já existe. Será alterado apenas o vínculo.' if d.get('existing_id') else 'Nenhum lançamento foi salvo nesta etapa.']
        if d.get('simulate'):
            text+=self.simulation_details(t)
            rows=[[('À vista',('simulate_variant',1)),('3x crédito',('simulate_variant',3)),('6x crédito',('simulate_variant',6))],[('Nova simulação',('start','simulate')),('🏠 Início',('cancel',))]]
        else:
            save_label='✅ Salvar entrada' if t['tipo']=='receita' else '✅ Salvar despesa'
            if duplicate:save_label='✅ Salvar mesmo assim'
            rows=[[(save_label,('commit',d['key'])),('✏️ Editar dados',('edit_menu',))],[('Cancelar',('cancel',))]]
            if marcas:
                campos={'forma_pagamento':('💳 Forma',('edit','method')),'conta':('🏦 Conta',('edit','account')),'categoria':('🏷 Categoria',('edit','category'))}
                rows.insert(1,[campos[c] for c in ('forma_pagamento','conta','categoria') if c in marcas])
            if duplicate:rows.insert(1,[('🔎 Ver o parecido',('dup_view',duplicate['id']))])
        if not d.get('simulate'):
            if t['parcelas_total'] > 1:
                rows.insert(-1,[('📅 Ver parcelas',('installment_schedule',0))])
                text += ['', 'Cada parcela pode ser relacionada à previsão correspondente depois de registrada; o parcelamento inteiro não é relacionado de uma vez.']
            else:
                rows.insert(-1,[('🔗 Relacionar a uma previsão',('pick_target',))])
        if d.get('existing_id'):
            rows=([[('Confirmar vínculo',('commit_link',d['key']))]] if d.get('conciliacao') else [])+[[('Relacionar a uma previsão',('pick_target',))],[('Cancelar',('cancel',))]]
            if not d.get('conciliacao'):rows.insert(-1,[('É outra operação; manter separado',('keep_separate',))])
        return Screen('\n'.join(text),rows)

    def _edit_menu_screen(self,s):
        if not s.draft:
            raise ValueError('Essa prévia expirou. Abra Registrar novamente.')
        rows=[
            [('Valor',('edit','amount')),('Descrição',('edit','description'))],
            [('Conta',('edit','account')),('Data',('edit','date'))],
            [('Categoria',('edit','category')),('Forma',('edit','method'))],
        ]
        # Parcelamento só é editável quando faz sentido para o meio de pagamento.
        # Isso evita oferecer uma ação que seria recusada pelo backend para Pix,
        # débito, dinheiro ou transferência.
        if s.draft.get('tipo')=='despesa' and norm(s.draft.get('forma_pagamento'))=='credito':
            rows.append([('Parcelamento',('edit','installments'))])
            if precisa_escolher(s.draft):
                rows.append([('Fatura', ('edit', 'billing_month'))])
        rows.append([('↩ Voltar à prévia',('preview',)),('Cancelar',('cancel',))])
        return Screen('<b>Editar dados do registro</b>\n\nEscolha somente o campo que precisa corrigir. O restante do rascunho será preservado.',rows)

    def installment_schedule(self,key,page=0):
        s=self.session(key)
        if not s.draft:
            return Screen('Esse parcelamento expirou. Abra Registrar novamente.',[[('Registrar',('view','register')),('🏠 Início',('view','home'))]])
        try:
            t=validar_transacao(self.payload(s.draft))
        except (ValueError,TypeError,KeyError) as exc:
            return Screen('Não foi possível montar o cronograma: '+safe(exc),[[('Voltar',('preview',)),('Cancelar',('cancel',))]])
        if t['parcelas_total'] <= 1:
            return self.preview(key)
        parcelas=installment_plan(t)
        per_page=10
        pages=max(1,(len(parcelas)+per_page-1)//per_page)
        page=max(0,min(int(page),pages-1))
        inicio=page*per_page
        fim=min(len(parcelas),inicio+per_page)
        lines=[
            '<b>📅 Cronograma das parcelas</b>',
            f'{safe(t["descricao"])} · {money(t["valor"])}',
            f'{installment_distribution_text(parcelas)}',
            '',
        ]
        for p in parcelas[inicio:fim]:
            lines.append(f'<b>{p["numero"]}/{len(parcelas)}</b> · {month_label(p["data"].strftime("%Y-%m"))} · {money(p["valor"])}')
        lines += ['',f'Página {page+1}/{pages} · soma do cronograma: <b>{money(sum(p["valor_centavos"] for p in parcelas)/100)}</b>',
                  'Cada parcela entra na competência correspondente do cartão; pagar uma fatura não apaga as parcelas dos meses seguintes.']
        nav=[]
        if page>0:nav.append(('‹ Anteriores',('installment_schedule',page-1)))
        if page<pages-1:nav.append(('Próximas ›',('installment_schedule',page+1)))
        rows=[]
        if nav:rows.append(nav)
        rows += [[('↩️ Voltar à prévia',('preview',))],[('Cancelar',('cancel',))]]
        return Screen('\n'.join(lines),rows)

    def simulation_details(self,t):
        n=t['parcelas_total'];total=int(parse_money(t['valor'])*100)
        base,resto=divmod(total,n)
        lines=['','<b>Impacto desta compra</b>']
        for i in range(min(n,6)):
            lines.append(f'{month_label(month_shift(competencia_transacao(t),i))}: {money((base+(i<resto))/100)}')
        if n>6:lines.append(f'+ {n-6} mês(es) · total {money(t["valor"])}')
        if t['forma_pagamento']=='crédito':
            lines+=['No crédito, comprar não retira dinheiro do caixa na hora. As parcelas seguem a fatura escolhida; a data real da compra não muda.']
        if t['tipo']=='despesa':
            # B7: mesmo motor do Início (resumir_saldo); "depois" = antes − parcela, em memória.
            sim=orient.simular_compra(int(parse_money(t['valor'])*100),n,competencia_transacao(t))
            lines+=['',*self._compra_resultado_linhas(sim)]
        else:
            with db.read_only_mode():m=svc.obter_metricas_resultado_mes(t['data'][:7])
            if m.get('saldo_configurado'):
                delta=t['valor']
                lines += [f'Previsão do mês: {money(m["saldo_projetado"])} → {money(m["saldo_projetado"]+delta)}',
                          'Estimativa isolada: mantém as demais previsões iguais. Revise receitas previstas e baixas pendentes.']
            else:lines+=['Falta saldo inicial para comparar a sobra com segurança.']
        return lines

    def _compra_resultado_linhas(self,sim):
        """Conta aberta de uma compra simulada: Deve sobrar antes/depois, mês apertado e leitura descritiva."""
        lines=[]
        primeiro=next((x for x in sim['meses'] if x['antes'] is not None),None)
        if primeiro is None:
            lines+=['<b>Deve sobrar no fim do mês</b>','Sem base de saldo para este período: informe o saldo inicial em Saldo → Ajustar saldo para ver a conta.']
        else:
            lines+=[f'<b>Deve sobrar no fim de {month_label(primeiro["mes"])}</b>',
                    f'Antes da compra: <b>{money(primeiro["antes"])}</b>',
                    f'Depois da compra: <b>{money(primeiro["depois"])}</b> (parcela de {money(primeiro["parcela"])})']
        if len(sim['meses'])>1:
            lines+=['','<b>Mês a mês</b> (antes → depois)']
            for x in sim['meses']:
                marca='²' if x['estimado'] else ''
                lines.append(f'{month_label(x["mes"])}{marca}: '+('sem base' if x['antes'] is None else f'{money(x["antes"])} → {money(x["depois"])}'))
            if sim['omitidas']:lines.append(f'<i>Mostrando os {len(sim["meses"])} primeiros de {sim["parcelas"]} meses.</i>')
            if any(x['estimado'] for x in sim['meses']):lines.append('<i>² saldo estimado (herdado do mês anterior).</i>')
        ap=sim['apertado']
        if ap is not None:lines+=['',f'Mês mais apertado: <b>{month_label(ap["mes"])}</b> · sobra {money(ap["depois"])}']
        v=orient.veredito_compra(sim)
        tom=v['tom']
        if tom=='revisar':frase='Conciliação pendente: a sobra do mês não é confiável para concluir. Resolva a revisão antes de usar esta conta.'
        elif tom=='sem_base':frase='Falta base de saldo para concluir.'
        elif tom=='negativo':
            frase=f'com a compra, {month_label(v["mes"])} fecha com {money(v["valor"])}'+(' (já ficaria negativo mesmo sem a compra).' if v.get('ja_negativo') else '.')
        elif tom=='aperta':frase=f'a parcela consome {pct(v["pct"],0)} da sobra prevista de {month_label(v["mes"])}.'
        else:frase=f'a sobra continua positiva nos meses analisados; a menor é {money(v["valor"])} em {month_label(v["mes"])}.'
        lines+=['',f'{v["emoji"]} <b>Leitura:</b> '+(frase[0].upper()+frase[1:] if tom in {'negativo','aperta','cabe'} else frase),
                '<i>É a conta feita com os seus números, não uma recomendação de comprar ou não comprar. Estimativa: usa a previsão de cada mês (meses com saldo herdado também descontam as parcelas anteriores); entradas e gastos futuros ainda não registrados não entram.</i>']
        return lines

    def begin_can_buy(self,key,text):
        """Pergunta em texto livre "posso comprar X em Nx" entra na simulação canônica (só leitura)."""
        s=self.session(key)
        p=orient.extrair_pergunta_compra(text)
        if p is None:
            return Screen('<b>Posso comprar?</b>\n\nPreciso do valor para fazer a conta. Exemplo: <code>posso comprar um celular de 3000 em 10x</code>',
                          [[('🔮 Simular passo a passo',('start','simulate')),('🏠 Início',('view','home'))]])
        s.compra=dict(p,fatura_prox=True)
        s.month=self.date_provider().strftime('%Y-%m');s.page=0
        return self.act(key,('view','can_buy'))

    def _compra_primeiro_mes(self,c):
        hoje=self.date_provider();mes=hoje.strftime('%Y-%m')
        if not c['credito']:return mes,False
        escolhe=precisa_escolher({'tipo':'despesa','forma_pagamento':'crédito','data':hoje.isoformat(),'conta':''})
        return (month_shift(mes,1) if escolhe and c.get('fatura_prox',True) else mes),escolhe

    def screen_can_buy(self,s):
        c=s.compra
        if not c:
            return Screen('Essa simulação expirou. Pergunte de novo, por exemplo: <code>posso comprar um celular de 3000 em 10x</code>',
                          [[('🔮 Simular',('start','simulate')),('🏠 Início',('view','home'))]])
        n=int(c['parcelas']);total=c['total_centavos']
        mes0,escolhe=self._compra_primeiro_mes(c)
        sim=orient.simular_compra(total,n,mes0)
        base,resto=divmod(total,n)
        plano=[{'valor_centavos':base+(1 if i<resto else 0)} for i in range(n)]
        forma=f'{installment_distribution_text(plano)} no crédito · fatura de {month_label(mes0)}' if c['credito'] else 'à vista (sai do caixa agora)'
        text=['<b>Posso comprar? · simulação</b>','<i>Nada será gravado.</i>','',
              f'<b>{safe(c["descricao"],40)}</b> · {money(total/100)}',forma,'',*self._compra_resultado_linhas(sim)]
        linhas=[[('À vista',('buy_sim',1)),('3x',('buy_sim',3)),('6x',('buy_sim',6)),('10x',('buy_sim',10))]]
        if escolhe:
            outro=month_shift(mes0,-1 if c.get('fatura_prox',True) else 1)
            linhas.append([('Fatura de '+month_label(outro),('buy_fatura',))])
            text+=['','Compra a partir do corte pode entrar na fatura atual ou na seguinte; você escolhe. Mostrei '+month_label(mes0)+'.']
        linhas.append([('🔮 Simular passo a passo',('start','simulate'))])
        return Screen('\n'.join(text),linhas+self.nav('can_buy'))

    def parse_draft(self,key,text,simulation=False):
        s=self.session(key)
        paused=self._paused_draft_guard(s)
        if paused is not None:return paused
        try:
            t=extrair_campos(text,hoje=self.date_provider(),contas=self.accounts())
            if t.get('descricao') and not t.get('_categoria_explicita'):
                t['categoria']=self._registration_category(t['descricao'],t['tipo'])
            # Frases naturais de despesa precisam preservar a mesma pergunta de
            # parcelamento do fluxo por botoes. Se o usuario ja informou um meio
            # nao credito ou uma quantidade de parcelas, nao ha ambiguidade.
            parcelas_explicitas = 'parcelas_total' in t or bool(t.get('_installments_pending'))
            metodo_informado = norm(t.get('forma_pagamento'))
            meio_nao_credito = metodo_informado in {'pix','debito','dinheiro','transferencia','boleto'}
            if t.get('tipo') == 'despesa' and not parcelas_explicitas and metodo_informado == 'credito':
                # P7: com a forma ainda desconhecida a pergunta espera a escolha da forma.
                t['_ask_installment_choice'] = True
                t['_preserve_method_on_installment_choice'] = True
            if 'data' not in t and re.search(r'\b\d{1,2}/\d{1,2}\b|\bdia\s+\d{1,2}\b|anteontem|semana passada|mes passado',norm(text)):
                t['_data_ambigua']=True
            t.setdefault('parcelas_total',1)
            t.setdefault('categoria','Receita' if t['tipo']=='receita' else 'Outros')
            t['mensagem_original']=text
            # Preserva o atalho completo: sem data explícita, a prévia usa hoje.
            # Em frases incompletas, a data faz parte das perguntas restantes.
            if all(t.get(field) for field in ('valor','descricao','forma_pagamento','conta')) and 'data' not in t and not t.get('_data_ambigua'):
                t['data']=self.date_provider().isoformat()
            t['simulate']=simulation
            self._aplicar_sugestoes(t)
            s.draft=dict(t,key=secrets.token_urlsafe(18),simulate=simulation,parsed=True)
            return self._advance_registration(key)
        except (ValueError,TypeError,KeyError) as exc:
            return Screen('Não consegui interpretar com segurança: '+safe(exc),[[('Registrar por etapas',('view','register')),('Cancelar',('cancel',))]])


    def begin_new_fixed(self, key):
        s = self.session(key)
        s.draft = None
        s.fixed_edit = None
        s.new_fixed = {
            "nome": "", "valor": None, "categoria": "", "forma_pagamento": "",
            "conta_pagamento": "", "dia_vencimento": None,
            "data_inicio": self.date_provider().strftime("%Y-%m"), "data_fim": None,
        }
        s.stage = "new_fixed_name"
        return self._new_fixed_prompt(s)

    def _new_fixed_prompt(self, s, error=None):
        d = s.new_fixed or {}
        stage = s.stage
        text = []
        rows = []
        steps = {
            "new_fixed_name": (1, "Qual é o nome do fixo?", "Exemplo: YouTube Premium, Internet, Condominio."),
            "new_fixed_amount": (2, "Qual é o valor mensal?", "Exemplo: 12,95."),
            "new_fixed_category": (3, "Qual é a categoria?", "Escolha a sugestão ou digite outra categoria."),
            "new_fixed_method": (4, "Como esse fixo é pago?", "Crédito entra na fatura do cartão. Pix/débito/transferência viram saída de caixa quando você der baixa."),
            "new_fixed_account": (5, "Qual conta ou cartão?", "Escolha uma conta existente ou digite o nome."),
            "new_fixed_due": (6, "Qual é o dia de vencimento?", "Informe um dia entre 1 e 31."),
            "new_fixed_start": (7, "A partir de qual mês ele vale?", "Escolha um mês ou digite, por exemplo, 12/2026 ou dezembro."),
            "new_fixed_end": (8, "Esse fixo tem término?", "Na maioria das assinaturas, escolha Sem término."),
            "new_fixed_end_month": (8, "Em qual mês termina?", "Digite o mês, por exemplo 12/2027 ou dezembro de 2027. O fixo valerá até o último dia desse mês."),
        }
        if stage not in steps:
            return self._new_fixed_preview(s.owner)
        number, title, hint = steps[stage]
        text = [f'<i>{number}/8 · Novo fixo</i>', f'<b>{title}</b>', '', hint]
        if error:
            text += ['', '\u26a0\ufe0f ' + safe(error)]
        if stage == "new_fixed_category":
            suggestion = d.get("categoria_sugerida") or self._registration_category(d.get("nome") or "", "despesa") or "Outros"
            d["categoria_sugerida"] = suggestion
            rows.append([(f'\u2705 {suggestion}', ('new_fixed_answer', suggestion))])
        elif stage == "new_fixed_method":
            rows = [[('Pix', ('new_fixed_answer', 'pix')), ('Débito', ('new_fixed_answer', 'debito'))],
                    [('Crédito', ('new_fixed_answer', 'credito')), ('Dinheiro', ('new_fixed_answer', 'dinheiro'))],
                    [('Transferência', ('new_fixed_answer', 'transferencia')), ('Boleto', ('new_fixed_answer', 'boleto'))]]
        elif stage == "new_fixed_account":
            names = self.accounts()
            visible = names[:10]
            rows = [[(name, ('new_fixed_answer', name)) for name in visible[i:i+2]] for i in range(0, len(visible), 2)]
        elif stage == "new_fixed_due":
            values = [5, 10, 15, 20, 25, 30]
            rows = [[(f'Dia {v}', ('new_fixed_answer', str(v))) for v in values[i:i+3]] for i in range(0, len(values), 3)]
        elif stage == "new_fixed_start":
            current = self.date_provider().strftime('%Y-%m')
            nxt = month_shift(current, 1)
            rows = [[(month_label(current), ('new_fixed_answer', current)), (month_label(nxt), ('new_fixed_answer', nxt))]]
        elif stage == "new_fixed_end":
            rows = [[('Sem término', ('new_fixed_no_end',)), ('Definir término', ('new_fixed_define_end',))]]
        if stage != "new_fixed_name":
            rows.append([('\u2039 Etapa anterior', ('new_fixed_back',))])
        rows.append([('Cancelar', ('new_fixed_cancel',))])
        return Screen('\n'.join(text), rows)

    def _new_fixed_advance(self, key, next_stage):
        s = self.session(key)
        d = s.new_fixed or {}
        if d.pop('_return_preview', False):
            return self._new_fixed_preview(key)
        s.stage = next_stage
        return self._new_fixed_prompt(s)

    def _new_fixed_text(self, key, text):
        s = self.session(key)
        d = s.new_fixed
        if not d:
            return self.begin_new_fixed(key)
        clean = norm(text)
        if clean in {'cancelar', '/cancelar', 'sair'}:
            s.new_fixed = None; s.stage = None
            return Screen('Cadastro cancelado. Nenhum fixo foi criado.', [[('🏠 Início', ('view', 'home'))]])
        try:
            if s.stage == 'new_fixed_name':
                value = text.strip()
                if not value or len(value) > 160: raise ValueError('Informe um nome de até 160 caracteres.')
                d['nome'] = value
                d['categoria_sugerida'] = self._registration_category(value, 'despesa')
                return self._new_fixed_advance(key, 'new_fixed_amount')
            if s.stage == 'new_fixed_amount':
                value = float(parse_money(text))
                if value <= 0 or value > 100000000: raise ValueError('Informe um valor positivo de até R$ 100 milhões.')
                d['valor'] = value
                return self._new_fixed_advance(key, 'new_fixed_category')
            if s.stage == 'new_fixed_category':
                value = text.strip()
                if not value or len(value) > 80: raise ValueError('Informe uma categoria de até 80 caracteres.')
                d['categoria'] = value
                return self._new_fixed_advance(key, 'new_fixed_method')
            if s.stage == 'new_fixed_method':
                aliases = {'pix':'pix','debito':'d\u00e9bito','credito':'cr\u00e9dito','cartao':'cr\u00e9dito','cartao de credito':'cr\u00e9dito','dinheiro':'dinheiro','transferencia':'transfer\u00eancia','boleto':'boleto'}
                value = aliases.get(clean)
                if not value: raise ValueError('Escolha Pix, débito, crédito, dinheiro, transferência ou boleto.')
                d['forma_pagamento'] = value
                return self._new_fixed_advance(key, 'new_fixed_account')
            if s.stage == 'new_fixed_account':
                value = text.strip()
                if not value or len(value) > 80: raise ValueError('Informe uma conta ou cartão de até 80 caracteres.')
                d['conta_pagamento'] = value
                return self._new_fixed_advance(key, 'new_fixed_due')
            if s.stage == 'new_fixed_due':
                match = re.search(r'\d{1,2}', text)
                if not match: raise ValueError('Informe um dia entre 1 e 31.')
                value = int(match.group())
                if value < 1 or value > 31: raise ValueError('Informe um dia entre 1 e 31.')
                d['dia_vencimento'] = value
                return self._new_fixed_advance(key, 'new_fixed_start')
            if s.stage == 'new_fixed_start':
                from fixos_interface import interpretar_mes
                value = interpretar_mes(text, self.date_provider()) or text.strip()
                if not re.fullmatch(r'\d{4}-\d{2}', value): raise ValueError('Escolha um botão ou digite o mês, por exemplo 12/2026 ou dezembro.')
                date.fromisoformat(value + '-01')
                d['data_inicio'] = value
                return self._new_fixed_advance(key, 'new_fixed_end')
            if s.stage == 'new_fixed_end_month':
                from fixos_interface import interpretar_mes
                value = interpretar_mes(text, self.date_provider()) or text.strip()
                if not re.fullmatch(r'\d{4}-\d{2}', value): raise ValueError('Digite o mês, por exemplo 12/2027 ou dezembro de 2027.')
                date.fromisoformat(value + '-01')
                if value < d['data_inicio']: raise ValueError('O término não pode ser anterior ao início.')
                d['data_fim'] = value
                return self._new_fixed_preview(key)
            if s.stage in {'new_fixed_preview', 'new_fixed_edit_menu'}:
                return self._new_fixed_preview(key)
        except (ValueError, TypeError) as exc:
            return self._new_fixed_prompt(s, str(exc))
        return self._new_fixed_prompt(s)

    def _new_fixed_preview(self, key):
        s = self.session(key)
        d = s.new_fixed
        if not d:
            return self.begin_new_fixed(key)
        required = ['nome','valor','categoria','forma_pagamento','conta_pagamento','dia_vencimento','data_inicio']
        if any(d.get(k) in (None, '') for k in required):
            return self._new_fixed_prompt(s, 'Ainda faltam dados para a conferencia.')
        s.stage = 'new_fixed_preview'
        end = month_label(d['data_fim']) if d.get('data_fim') else 'sem término'
        lines = ['<i>8/8 · Conferência</i>', '<b>Confirmar novo fixo</b>', '',
                 f'<b>{safe(d["nome"])}</b>', f'<b>{money(d["valor"])}</b> · {safe(d["categoria"])}',
                 f'Pagamento: <b>{safe(d["forma_pagamento"])}</b>', f'Conta/cartão: <b>{safe(d["conta_pagamento"])}</b>',
                 f'Vencimento: dia <b>{d["dia_vencimento"]}</b>', f'Início: <b>{month_label(d["data_inicio"])}</b>', f'Término: <b>{end}</b>', '']
        if norm(d['forma_pagamento']) == 'credito':
            try:
                atual = svc.calcular_fatura_unificada(d['data_inicio'], d['conta_pagamento'], somente_cartao=True)['saldo_restante']
                lines += [f'💳 Esse fixo passará a compor a fatura <b>{safe(d["conta_pagamento"])}</b>.',
                          f'Fatura atual de {month_label(d["data_inicio"])}: <b>{money(atual)}</b>.',
                          'Após salvar, o total será recalculado pelo motor da fatura.']
            except Exception:
                lines += [f'💳 Esse fixo passará a compor a fatura <b>{safe(d["conta_pagamento"])}</b>.']
        else:
            lines += ['Esse cadastro é uma previsão. A saída de caixa só será registrada quando você confirmar o pagamento.']
        lines += ['', '<i>Nenhuma despesa foi criada nesta etapa.</i>']
        return Screen('\n'.join(lines), [[('\u2705 Salvar fixo', ('new_fixed_commit',)), ('\u270f\ufe0f Editar dados', ('new_fixed_edit_menu',))], [('Cancelar', ('new_fixed_cancel',))]])

    def _new_fixed_edit_menu(self, key):
        s = self.session(key); s.stage = 'new_fixed_edit_menu'
        return Screen('<b>Editar dados do fixo</b>\n\nEscolha o campo. Depois da correção você volta para a conferência.', [
            [('Nome', ('new_fixed_edit', 'name')), ('Valor', ('new_fixed_edit', 'amount'))],
            [('Categoria', ('new_fixed_edit', 'category')), ('Forma', ('new_fixed_edit', 'method'))],
            [('Conta/cartão', ('new_fixed_edit', 'account')), ('Vencimento', ('new_fixed_edit', 'due'))],
            [('Início', ('new_fixed_edit', 'start')), ('Término', ('new_fixed_edit', 'end'))],
            [('\u2039 Voltar', ('new_fixed_preview',)), ('Cancelar', ('new_fixed_cancel',))],
        ])

    def act(self,key,action):
        s=self.session(key);kind=action[0]
        if kind=='disabled':return Screen('Essa ação não está disponível. Confira a orientação da tela.',[[('🏠 Início',('view','home'))]])
        if kind=='miniapp':return Screen('O painel externo foi retirado desta versão. Digite painel (ou /dashboard) para ver o mês.',[[('✨ Recursos',('innovations',))]])
        if kind in {'buscar_texto','busca','busca_cat','busca_cat_ver','busca_cat_ok','busca_regra'}:from busca_lancamentos import dispatch;return self._apply_privacy(s,dispatch(self,key,action,globals()))
        if kind=='pagar_cat':from consultas_pagar import dispatch;return self._apply_privacy(s,dispatch(self,key,action,globals()))
        if kind in {'origin','invoice_origin','quiz','quiz_answer','innovations','media_help','topics_setup'}:
            from telegram_recursos import dispatch
            return self._apply_privacy(s,dispatch(self,key,action))
        if kind in {'media_kind','media_continue','media_edit','media_transfer_edit','media_transfer_back','media_transfer_field','media_transfer_commit'}:
            from telegram_midia import dispatch
            return dispatch(self,key,action)
        if kind=='topic' and (s.fixed_edit or s.new_fixed):
            self.pause_for_guidance(s);s.topic=action[1];return self.render(key,'help_topic')
        if kind=='view' and action[1] in {'help','command_help'} and (s.fixed_edit or s.new_fixed):
            self.pause_for_guidance(s);return self.render(key,action[1])
        if kind=='lesson':return self.open_learning(key,action[1])
        if kind=='lesson_page':
            s.lesson_page=max(0,min(int(action[1]),2));return self.render(key,'learn_topics')
        if kind=='view' and action[1] in {'learn','learn_topics','lesson'}:
            if action[1]=='learn':return self.open_learning(key)
            return self.render(key,action[1])
        if kind=='learning_resume':
            if not s.learning_stage:raise ValueError('Esta etapa não está mais ativa.')
            s.stage=s.learning_stage;s.learning_stage=None
            if s.fixed_edit:
                from fixos_interface import retomar
                return retomar(self,key)
            if s.new_fixed:return self._new_fixed_prompt(s)
            raise ValueError('Abra o cadastro novamente.')
        if kind=='dashboard_month':
            s.month=month_shift(s.month,int(action[1]))
            return self.act(key,('chart',action[2]))
        if kind == 'new_fixed_start': return self.begin_new_fixed(key)
        if kind == 'new_fixed_answer': return self._new_fixed_text(key, str(action[1]))
        if kind == 'new_fixed_no_end':
            if not s.new_fixed: return self.begin_new_fixed(key)
            s.new_fixed['data_fim']=None
            return self._new_fixed_preview(key)
        if kind == 'new_fixed_define_end':
            if not s.new_fixed: return self.begin_new_fixed(key)
            s.stage='new_fixed_end_month'; return self._new_fixed_prompt(s)
        if kind == 'new_fixed_back':
            previous={'new_fixed_amount':'new_fixed_name','new_fixed_category':'new_fixed_amount','new_fixed_method':'new_fixed_category','new_fixed_account':'new_fixed_method','new_fixed_due':'new_fixed_account','new_fixed_start':'new_fixed_due','new_fixed_end':'new_fixed_start','new_fixed_end_month':'new_fixed_end'}
            s.stage=previous.get(s.stage,'new_fixed_name'); return self._new_fixed_prompt(s)
        if kind == 'new_fixed_edit_menu': return self._new_fixed_edit_menu(key)
        if kind == 'new_fixed_preview': return self._new_fixed_preview(key)
        if kind == 'new_fixed_edit':
            mapping={'name':'new_fixed_name','amount':'new_fixed_amount','category':'new_fixed_category','method':'new_fixed_method','account':'new_fixed_account','due':'new_fixed_due','start':'new_fixed_start','end':'new_fixed_end'}
            if not s.new_fixed or action[1] not in mapping: raise ValueError('Abra o cadastro de fixo novamente.')
            s.new_fixed['_return_preview']=True
            s.stage=mapping[action[1]]
            return self._new_fixed_prompt(s)
        if kind == 'new_fixed_cancel':
            s.new_fixed=None;s.stage=None
            return Screen('Cadastro cancelado. Nenhum fixo foi criado.',[[('🏠 Início',('view','home')),('\u2795 Registrar',('view','register'))]])
        if kind == 'new_fixed_commit':
            if not s.new_fixed or s.stage!='new_fixed_preview': raise ValueError('Abra a conferencia do fixo novamente.')
            s.new_fixed.setdefault('_confirmacao_id',secrets.token_urlsafe(18))
            result=svc.cadastrar_fixo_guiado(dict(s.new_fixed),sessao=key)
            c=result['compromisso']; before=result.get('fatura_antes'); after=result.get('fatura_depois')
            s.new_fixed=None;s.stage=None
            lines=['\u2705 <b>Fixo cadastrado</b>','',f'<b>{safe(c["nome"])}</b>',f'{money(c["valor"])} \u00b7 {safe(c["categoria"])}',f'{safe(c["forma_pagamento"])} \u00b7 {safe(c["conta_pagamento"])}',f'Dia {c["dia_vencimento"]} \u00b7 {month_label(c["data_inicio"][:7])} em diante' if not c.get('data_fim') else f'Dia {c["dia_vencimento"]} \u00b7 {month_label(c["data_inicio"][:7])} até {month_label(c["data_fim"][:7])}']
            if after is not None:
                lines += ['', f'💳 Fatura {safe(c["conta_pagamento"])}', f'Antes: <b>{money(before)}</b>', f'Agora: <b>{money(after)}</b>', f'Impacto do cadastro: <b>{money(after-before)}</b>', '', 'O fixo não foi criado como despesa separada; ele passou a compor a fatura.']
            else:
                lines += ['', 'O fixo foi criado como previsão. O saldo da conta só muda quando o pagamento for registrado.']
            if result.get('resumo_indisponivel'):
                lines += ['', 'O cadastro está salvo. O resumo da fatura não pôde ser atualizado agora; confira A pagar sem cadastrar novamente.']
            lines += ['', f'<i>Código para comandos de texto: #C{c["id"]}</i>']
            return Screen('\n'.join(lines),[*([[('〰 Valor varia todo mês (ex.: luz, água)',('fixed_var',c['id']))]] if c.get('tipo')=='fixo' and 'credito' not in norm(c.get('forma_pagamento')) else []),[('🧾 A pagar',('view','pay')),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]])
        if kind.startswith('fixed_'):
            from fixos_interface import acao
            return acao(self,key,action)
        if s.fixed_edit and kind not in {'chart','dashboard_month','detail_obligation'}:
            s.fixed_edit=None;s.stage=None

        if kind in {'topic','transaction','detail_obligation','accounts_for','ask'}:
            s.trail=(s.trail+[(s.view,s.month,s.page)])[-12:]
        if kind=='back':
            s.stage=None;s.draft=None
            if s.trail:s.view,s.month,s.page=s.trail.pop()
            else:s.view='home'
            return self.render(key)
        if kind=='help_page':s.help_page=max(0,min(int(action[1]),max(0,len(s.help_pages)-1)));return self.render(key,'advanced_help')
        if kind=='back_step':
            previous={'amount':'installment_choice','description':'amount','method':'description','account':'method','date':'account','installments':'date','billing_month':'date','category':'description','installment_choice':'method'}
            if not s.draft or s.stage not in previous:raise ValueError('Abra o registro novamente.')
            if s.stage=='amount':raise ValueError('Esta é a primeira etapa desse registro.')
            if s.draft.get('_edit'):
                s.draft.pop('_edit',None);s.stage='confirm';return self.preview(key)
            s.stage=previous[s.stage];return self.prompt(s)
        if kind=='filter':
            field='pay_filter' if action[1]=='pay' else 'history_filter'
            allowed={'all','overdue','soon','review'} if action[1]=='pay' else set(HISTORY_FILTER_LABELS)
            if action[2] not in allowed:raise ValueError('Filtro inválido.')
            setattr(s,field,action[2]);s.page=0;return self.render(key,action[1])
        if kind=='pay_tools':return self._pay_tools_screen(s)
        if kind=='period_tools':
            return Screen(heading('Período',month_label(s.month))+'\n\nEscolha o mês.',[
                [('‹ Mês anterior',('month',-1,s.view)),('Próximo mês ›',('month',1,s.view))],
                [('Mês atual',('current_month',s.view)),('↻ Atualizar',('render_current',))],
                [('↩ Voltar',('render_current',)),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]])
        if kind=='history_basis':
            if action[1] not in {'data','fatura'}:raise ValueError('Filtro inválido.')
            s.history_basis=action[1];s.page=0
            return self.render(key,'history')
        if kind=='history_tools':return self._history_tools_screen(s)
        if kind=='render_current':return self.render(key)
        if kind=='account_history':
            # Movimentos de UMA conta no Histórico novo: lançamentos, transferências e pagamentos de fatura.
            s.trail=(s.trail+[(s.view,s.month,s.page)])[-12:]
            s.month=str(action[2]) if len(action)>2 and re.fullmatch(r'\d{4}-\d{2}',str(action[2])) else s.month
            s.history_filter='all';s.history_account_filter=str(action[1]);s.history_category_filter='';s.search='';s.page=0
            return self.render(key,'history')
        if kind=='home_income':
            s.trail=(s.trail+[(s.view,s.month,s.page)])[-12:]
            s.history_filter='receita';s.history_account_filter='';s.history_category_filter='';s.search='';s.page=0
            return self.render(key,'history')
        if kind=='flow_resume':
            if not s.draft or not s.stage:raise ValueError('Esse registro não está mais ativo. Abra Registrar novamente.')
            return self.preview(key) if s.stage=='confirm' else self.prompt(s)
        if kind=='conflict_keep':
            if s.new_fixed and str(s.stage or '').startswith('new_fixed'):return self._new_fixed_prompt(s)
            if not s.draft or not s.stage:raise ValueError('Esse registro não está mais ativo. Abra Registrar novamente.')
            if s.draft.get('flow')=='invoice_payment':
                return self.invoice_preview(key) if s.stage=='invoice_confirm' else self.invoice_prompt(key)
            return self.preview(key) if s.stage=='confirm' else self.prompt(s)
        if kind=='conflict_start':
            s.draft=None;s.new_fixed=None;s.stage=None;s.media_review=None
            screen=self.handle_text(key,str(action[1]))
            if screen is None:
                return Screen('Registro anterior descartado. Nada foi gravado.\n\nEnvie de novo a mensagem do novo lançamento.',[[('➕ Registrar',('view','register')),('🏠 Início',('view','home'))]])
            return screen
        if kind=='resume_suspended':return self._resume_suspended(key)
        if kind=='discard_suspended':
            s.suspended_draft=None;s.suspended_stage=None;s.suspended_view=''
            return Screen('Rascunho descartado. Nenhuma alteração foi salva.',[[('🏠 Início',('view','home')),('➕ Registrar',('view','register'))]])
        if kind=='discard_and_start':
            s.suspended_draft=None;s.suspended_stage=None;s.suspended_view=''
            return self.begin(key,action[1])
        if kind=='discard_and_register':
            s.suspended_draft=None;s.suspended_stage=None;s.suspended_view=''
            return self.render(key,'register')
        if kind=='category_rule_remove':
            s.settings_draft={'phrase':str(action[1]),'category':str(action[2])}
            s.stage='confirm_category_rule_remove'
            return Screen(
                '<b>Remover preferência?</b>\n\n'
                f'“{safe(action[1],160)}” deixará de sugerir <b>{safe(action[2],60)}</b>.\n\n'
                'Lançamentos já registrados não serão alterados.',
                [[('🗑 Remover regra',('category_rule_remove_commit',)),('Cancelar',('view','category_rules'))]],
            )
        if kind=='category_rule_remove_commit':
            if s.stage!='confirm_category_rule_remove' or not s.settings_draft:
                raise ValueError('Essa confirmação expirou.')
            from categorias_pessoais import remover_regra
            cfg=dict(s.settings_draft)
            removed=remover_regra(cfg['phrase'])
            if removed:
                db.registrar_auditoria(
                    'regra_categoria_pessoal',cfg['phrase'],'remover',
                    dados_antes=cfg,origem='telegram',usuario_sessao=key,
                )
            s.settings_draft=None;s.stage=None
            message=('Preferência removida. Lançamentos existentes foram preservados.'
                     if removed else 'Essa preferência já não existia.')
            return Screen(message,[[('🧠 Ver regras',('view','category_rules')),('🏠 Início',('view','home'))]])
        if kind=='edit_menu':return self._edit_menu_screen(s)
        if kind=='account_choice_page':
            if s.stage!='account':raise ValueError('A seleção de conta expirou. Abra o registro novamente.')
            s.account_choice_page=max(0,int(action[1]));return self.prompt(s)
        if kind=='clear_pay_filters':
            s.pay_filter='all';s.pay_account_filter='';s.page=0;return self.render(key,'pay')
        if kind=='balance_account':return self._balance_account_screen(key,action[1],action[2])
        if kind=='cash_accounts':return self._cash_accounts_screen(key,action[1] if len(action)>1 else s.month,action[2] if len(action)>2 else None)
        if kind=='cash_account_detail':return self._cash_account_detail_screen(key,action[1],action[2])
        if kind=='cash_setup_start':return self._cash_setup_start(key)
        if kind=='cash_setup_pick':return self._cash_setup_start(key,action[1])
        if kind=='cash_setup_all':return self._cash_setup_all(key)
        if kind=='cash_setup_new_account':
            s.settings_draft={'month':self.date_provider().strftime('%Y-%m'),'changes':[]}
            s.stage='cash_setup_account_name';s.draft=None
            return Screen('<b>Qual conta você quer conferir?</b>\n\nDigite o nome do banco ou da conta. Depois informe o saldo que aparece agora. Nenhuma movimentação será criada.',[[('Cancelar',('cancel',))]])
        if kind=='cash_setup_account':return self._cash_setup_account(key,action[1])
        if kind=='cash_setup_skip':return self._cash_setup_advance(key,skip=True)
        if kind=='cash_setup_edit':
            if s.stage!='cash_setup_confirm' or not s.settings_draft:raise ValueError('Essa confirmação expirou.')
            s.settings_draft.pop('pending_value',None);s.settings_draft.pop('expected_cash',None)
            s.stage='cash_setup_value';return self._cash_setup_prompt(s)
        if kind=='cash_setup_commit':return self._cash_setup_commit(key)
        if kind=='pay_month':return self._pay_month_screen(key,action[1],page=action[2] if len(action)>2 else None)
        if kind=='pay_month_expand':return self._pay_month_screen(key,action[2],action[1],action[3] if len(action)>3 else None)
        if kind=='pay_month_page':return self._pay_month_screen(key,action[1],page=action[2])
        if kind=='pay_month_account_detail':return self._pay_month_account_detail(key,action[1],action[2])
        if kind=='pay_account':return self._pay_account_screen(key,action[1],action[2])
        if kind=='pay_account_detail':return self._pay_account_screen(key,action[1],action[2],True)
        if kind=='pay_account_filter':
            s.month=action[2];s.pay_account_filter=action[1];s.pay_filter='all';s.page=0
            return self.render(key,'pay')
        if kind=='category':s.history_basis='fatura';s.history_category_filter=str(action[1]);s.search='';s.history_filter='despesa';s.history_account_filter='';return self.act(key,('view','history'))
        if kind=='clear_filters':s.history_account_filter='';s.history_category_filter='';s.search='';s.history_filter='all';s.page=0;return self.render(key,'history')
        if kind=='accounts_for':s.filter_view=action[1];return self.render(key,'accounts')
        if kind=='account_filter':
            if s.filter_view=='pay':s.pay_account_filter=action[1]
            else:s.history_account_filter=action[1]
            s.page=0
            if s.trail and s.trail[-1][0]==s.filter_view:s.trail.pop()
            return self.render(key,s.filter_view)
        if kind=='account_page':s.page=max(0,int(action[1]));return self.screen_accounts(s)
        if kind=='account_search':s.stage='account_search';return Screen('Digite o nome exato da conta.',[[('Cancelar',('cancel',))]])
        if kind=='topic':
            # Ajuda é navegação: como em ('view', ...), um registro em andamento
            # é pausado e etapas de configuração (ex.: saldo inicial) são
            # encerradas, para que um texto posterior não caia nelas.
            if s.stage and s.draft:self._suspend_flow(s)
            if s.stage:s.settings_draft=None;s.stage=None
            s.topic=action[1];return self.render(key,'help_topic')
        if kind=='ask':s.stage='ask';s.draft=None;return self.render(key,'question')
        if kind=='transaction':
            if s.stage=='fix_date':s.stage=None;s.settings_draft=None
            s.selected_id=int(action[1]);return self.render(key,'transaction')
        if kind=='detail_obligation':
            self.pause_for_guidance(s)
            s.selected_obligation=(action[1],action[2])
            screen=self.render(key,'obligation')
            from telegram_recursos import _resume
            _resume(self,s,screen)
            return screen
        if kind=='invoice_pay_total':
            if not s.draft or s.draft.get('flow')!='invoice_payment':raise ValueError('Abra a fatura novamente.')
            s.draft['modo']='total';s.draft['valor']=float(s.draft['saldo_esperado']);s.stage='invoice_account';s.account_choice_page=0
            return self.invoice_prompt(key)
        if kind=='invoice_pay_partial':
            if not s.draft or s.draft.get('flow')!='invoice_payment':raise ValueError('Abra a fatura novamente.')
            s.draft['modo']='parcial';s.stage='invoice_amount';return self.invoice_prompt(key)
        if kind=='invoice_back_choice':
            if not s.draft or s.draft.get('flow')!='invoice_payment':raise ValueError('Abra a fatura novamente.')
            s.stage='invoice_choice';return self.invoice_prompt(key)
        if kind=='invoice_account_page':
            s.account_choice_page=max(0,int(action[1]));return self.invoice_prompt(key)
        if kind=='invoice_account_select':
            if not s.draft or s.draft.get('flow')!='invoice_payment':raise ValueError('Abra a fatura novamente.')
            s.draft['conta_origem']=action[1];s.stage='invoice_confirm';return self.invoice_preview(key)
        if kind=='invoice_preview':return self.invoice_preview(key)
        if kind=='invoice_edit_amount':
            if not s.draft or s.draft.get('flow')!='invoice_payment':raise ValueError('Abra a fatura novamente.')
            s.draft['modo']='parcial';s.stage='invoice_amount';return self.invoice_prompt(key)
        if kind=='invoice_edit_account':
            if not s.draft or s.draft.get('flow')!='invoice_payment':raise ValueError('Abra a fatura novamente.')
            s.stage='invoice_account';s.account_choice_page=0;return self.invoice_prompt(key)
        if kind=='invoice_restart':return self.begin_invoice_payment(key,action[1],action[2])
        if kind=='invoice_commit':
            d=s.draft
            if not d or d.get('flow')!='invoice_payment' or s.stage!='invoice_confirm' or d.get('key')!=action[1]:
                return Screen('Essa confirmação expirou ou já foi usada. Atualize a fatura antes de tentar novamente.',[[('🧾 A pagar',('view','pay')),('🔎 Histórico',('view','history'))]])
            payload={k:d.get(k) for k in ('ano_mes','conta_cartao','conta_origem','modo','valor','saldo_esperado')}
            payload['data_movimento']=self.date_provider().isoformat()
            result=confirmar_pagamento_fatura(payload,d['key'],key)
            card=d['conta_cartao'];month=d['ano_mes'];event=d['key']
            return_pay_action=('back',) if s.trail and s.trail[-1][0]=='pay' else ('view','pay')
            s.draft=None;s.stage=None;s.last_event=event;s.month=month
            return Screen(
                '<b>Pagamento registrado no assessor</b>\n\n'
                f'Fatura: <b>{safe(card,55)}</b> · {month_label(month)}\n'
                f'Saiu de: <b>{safe(payload["conta_origem"],55)}</b>\n'
                f'Valor registrado: <b>{money(result["valor_gravado"])}</b>\n'
                f'Restante da fatura: <b>{money(result["saldo_restante"])}</b>\n'
                '\nEste registro atualiza o assessor; nenhuma transferência bancária foi executada.\n\n'
                f'<i>Código para comandos de texto: #F{result["movimento_id"]}</i>',
                [[('💳 Ver fatura',('detail_obligation',f'B_{svc.slug_banco_checklist(card)}',month)),('🧾 Voltar a A pagar',return_pay_action)],
                 [('🔎 Histórico',('view','history')),('🏠 Início',('view','home'))]],
            )
        if kind=='repeat':
            paused=self._paused_draft_guard(s)
            if paused is not None:return paused
            raw=db.buscar_transacao_por_id(action[1])
            if not raw:raise ValueError('Esse lançamento não existe mais.')
            t=dict(raw)
            if (t.get('parcelas_total') or 1)>1:raise ValueError('Parcelamentos não são repetidos automaticamente. Abra Registrar.')
            s.draft={k:t[k] for k in ('tipo','valor','descricao','categoria','conta','forma_pagamento')}
            s.draft.update(data=self.date_provider().isoformat(),parcelas_total=1,key=secrets.token_urlsafe(18),parsed=True)
            s.stage='confirm';return self.preview(key)
        if kind=='target_page':s.target_page=max(0,int(action[1]));return self.target_picker(key)
        if kind=='pick_target_page':return self.target_picker(key)
        if kind=='reconcile_baseline_preview':
            current=self.date_provider().strftime('%Y-%m')
            if s.month!=current:
                s.month=current;s.page=0
            metrics,reviews,_=self._reconciliation_review_summary(current)
            if not reviews:
                return Screen('Não há pendências de conciliação bloqueando o mês atual.',[[('🏠 Início',('view','home'))]])
            legacy=[r for r in reviews if r.get('tipo')=='baixa_antiga']
            other=[r for r in reviews if r.get('tipo')!='baixa_antiga']
            if other or not legacy or not all((r.get('mes') or '') < current for r in legacy):
                return Screen('Existem pendências que precisam ser resolvidas individualmente antes de criar uma nova base.',[[('🧩 Revisar pendências',('view','review'))]])
            available=float(metrics.get('saldo_disponivel') or 0)
            new_initial=(available-float(metrics.get('entradas_realizadas') or 0)
                         +float(metrics.get('saidas_imediatas_realizadas') or 0)
                         -float(metrics.get('ajuste_conciliacao_heranca') or 0))
            raw=db.buscar_saldo_mensal(current)
            expected=dict(raw) if raw else None
            s.settings_draft={'month':current,'amount':new_initial,'expected':expected,
                              'available':round(available,2),'review_count':len(reviews)}
            s.stage='confirm_reconcile_baseline';s.draft=None
            message=(
                '<b>Confirmar nova base de conciliação?</b>\n\n'
                f'Caixa disponível atual: <b>{money(available)}</b>\n'
                f'Revisões históricas que deixarão de bloquear a sobra: <b>{len(reviews)}</b>\n\n'
                'O assessor vai preservar exatamente o caixa atual e criar um novo ponto de partida neste mês. '
                'Nenhum lançamento antigo será apagado, criado ou alterado. As marcações antigas continuam disponíveis para auditoria.'
            )
            return Screen(message,[[('✅ Confirmar nova base',('reconcile_baseline_commit',)),('Cancelar',('cancel',))]])
        if kind=='reconcile_baseline_commit':
            cfg=s.settings_draft
            if s.stage!='confirm_reconcile_baseline' or not cfg:
                raise ValueError('Essa confirmação de conciliação expirou.')
            current=self.date_provider().strftime('%Y-%m')
            if cfg.get('month')!=current:
                raise ValueError('O mês mudou desde a confirmação. Abra a conciliação novamente.')
            metrics,reviews,_=self._reconciliation_review_summary(current)
            if round(float(metrics.get('saldo_disponivel') or 0),2)!=round(float(cfg.get('available') or 0),2) or len(reviews)!=int(cfg.get('review_count') or 0):
                raise ValueError('Os registros mudaram desde a prévia. Abra a conciliação novamente antes de confirmar.')
            orient.configurar_saldo(key,current,float(cfg['amount']),cfg.get('expected'))
            s.settings_draft=None;s.stage=None;s.month=current
            after=svc.obter_metricas_resultado_mes(current)
            remaining=len(after.get('revisoes_conciliacao') or [])
            msg=(
                f'<b>Base conciliada.</b>\n\nO caixa disponível foi preservado em <b>{money(after["saldo_disponivel"])}</b>. '
                f'{plural(int(cfg["review_count"])-remaining, "revisão histórica deixou", "revisões históricas deixaram")} de bloquear a sobra. '
                'Nenhum movimento antigo foi apagado ou recriado.'
            )
            if remaining:
                msg+=f'\n\nAinda {"existe" if remaining == 1 else "existem"} <b>{plural(remaining, "pendência atual", "pendências atuais")}</b> para revisar individualmente.'
            return Screen(msg,[[('🏠 Ver meu mês',('view','home')),('🧩 Revisar pendências',('view','review'))]])
        if kind=='pref':
            if action[1] in {'hora_manha','hora_noite','hora_semana'} and orient.em_silencio(str(action[2]),orient.preferencias(key)):
                p=orient.preferencias(key)
                raise ValueError(f'O horário {action[2]} fica dentro do silêncio ({p["silencio_inicio"]}–{p["silencio_fim"]}) e o aviso nunca seria enviado. Escolha outro horário ou ajuste o silêncio em Escolher horários.')
            orient.salvar_preferencia(key,action[1],action[2])
            return self.render(key,'local_ai' if action[1]=='ia_local' else 'more' if action[1]=='visual' else 'alert_settings' if action[1]=='alerta_valores' else 'alerts')
        if kind=='alert_hours':
            s.stage='alert_hours'
            return Screen('Digite quatro horários: agenda, fechamento, início e fim do silêncio.\nExemplo: 09:00 20:00 23:00 08:00',[[('Cancelar',('cancel',))]])
        if kind=='save_hours':
            if s.stage!='confirm_settings' or not s.settings_draft:raise ValueError('Essa confirmação expirou.')
            orient.salvar_preferencias(key,s.settings_draft)
            s.settings_draft=None;s.stage=None;return self.render(key,'alerts')
        if kind=='alert_preview':
            from telegram_alertas import montar_aviso
            return Screen('<b>Prévia: nenhum aviso foi agendado por este botão</b>\n\n'+montar_aviso('noite',{}),[[('Configurar alertas',('view','alerts'))]])
        if kind=='budget_start':
            s.stage='budget_category';s.settings_draft=None
            cats=self._categorias_limite()
            botoes=[(c,('budget_cat',c)) for c in cats]
            rows=[botoes[i:i+3] for i in range(0,len(botoes),3)]+[[('Cancelar',('cancel',))]]
            return Screen('Qual categoria você quer planejar? Escolha abaixo ou digite o nome usado nos seus registros.',rows)
        if kind=='budget_cat':
            if s.stage!='budget_category':raise ValueError('Essa escolha expirou. Abra Limites novamente.')
            s.settings_draft={'category':str(action[1])[:80]};s.stage='budget_amount'
            return Screen('Qual será o limite de <b>'+safe(s.settings_draft['category'])+'</b>? Informe seu valor real.',[[('Cancelar',('cancel',))]])
        if kind=='balance_start':
            return Screen('<b>Qual saldo você quer informar?</b>\n\n<b>Saldo atual</b>: o dinheiro que você vê agora nos bancos. Use este para conferir a previsão.\n\n<b>Saldo inicial</b>: o dinheiro que havia na abertura do mês. Os movimentos registrados depois serão somados ou descontados.',[
                [('🏦 Ajustar saldo atual',('cash_setup_start',))],
                [('Saldo inicial do mês',('balance_initial',))], [('🏠 Início',('view','home'))]])
        if kind=='balance_initial':
            if db.buscar_saldos_contas_mes(s.month):
                return Screen('<b>Este mês usa saldos por conta.</b>\n\nPara atualizar a previsão, informe o saldo atual de cada banco. Um saldo inicial geral separado não substituiria essas bases.',[
                    [('✏️ Ajustar saldo atual',('cash_setup_start',))], [('🏦 Ver saldos por conta',('cash_accounts',s.month))]])
            raw=db.buscar_saldo_mensal(s.month);s.settings_draft={'month':s.month,'expected':dict(raw) if raw else None};s.stage='initial_balance';s.draft=None
            return Screen('<b>Qual era o saldo inicial livre?</b>\n\n'+month_label(s.month)+'\n\nInforme o valor na abertura desse mês, já considerando as reservas que você adotou. Na próxima etapa, você confere antes de salvar.\n\nUse zero ou um valor negativo quando for o caso.',[[('Cancelar',('cancel',)),('Entender o saldo',('topic','saldo'))]])
        if kind=='save_balance':
            if s.stage!='confirm_balance' or not s.settings_draft:raise ValueError('A confirmação do saldo expirou.')
            cfg=s.settings_draft;orient.configurar_saldo(key,cfg['month'],cfg['amount'],cfg['expected'])
            s.settings_draft=None;s.stage=None;return self.render(key,'balance')
        if kind=='save_budget':
            if s.stage!='confirm_budget' or not s.settings_draft:raise ValueError('Essa confirmação expirou.')
            db.definir_meta(s.settings_draft['category'],s.settings_draft['amount'])
            s.settings_draft=None;s.stage=None;return self.render(key,'budgets')
        if kind=='chart':
            self.pause_for_guidance(s)
            # Compartilha cálculos somente durante esta consulta. Não mantém
            # totais em cache entre cliques nem reaproveita um saldo antigo.
            with db.read_only_mode(),svc.contexto_consulta():
                data=orient.coletar(self,s)
            m=data['metrics'];view=action[1]
            cards=[{'label':'ENTRADAS REGISTRADAS','value':money(data['income'])},{'label':'DESPESAS REGISTRADAS','value':money(data['spending'])},{'label':'DIFERENÇA','value':money(data['income']-data['spending'])}]
            bars=data['categories'];title='Onde você gastou'
            section='MAIORES VALORES · TOP 6'
            if view=='home':
                title='Painel do mês'
                summary=resumir_saldo(m)
                closed=s.month < self.date_provider().strftime('%Y-%m')
                projection='Revisar' if summary['revisar'] else money(summary['saldo_final'])
                current=s.month==self.date_provider().strftime('%Y-%m')
                cards=[{'label':'SALDO AGORA' if current else 'SALDO NO PERÍODO','value':money(summary['saldo_atual'])},
                       {'label':'RESERVADO PARA PAGAR' if summary['reservas_liquidas']>=0 else 'AJUSTES A FAVOR','value':money(abs(summary['reservas_liquidas']))},
                       {'label':'FECHAMENTO CALCULADO' if closed else 'SOBRA PREVISTA','value':projection}]
                bars=data['categories'];section='MAIORES GASTOS REGISTRADOS · TOP 6'
            elif view=='history':
                filtered=self.history_items(s)
                income=sum(float(t['valor']) for t in filtered if t['tipo']=='receita')
                spending=sum(float(t['valor']) for t in filtered if t['tipo']=='despesa')
                grouped=defaultdict(float)
                for t in filtered:
                    if t['tipo']=='despesa':grouped[t['categoria']]+=float(t['valor'])
                bars=sorted(grouped.items(),key=lambda pair:pair[1],reverse=True)
                title='Seu Histórico filtrado'
                cards=[{'label':'ENTRADAS FILTRADAS','value':money(income)},
                       {'label':'DESPESAS FILTRADAS','value':money(spending)},
                       {'label':'LANÇAMENTOS','value':str(len(filtered))}]
            elif view=='pay':
                title='Suas contas em aberto';bars=[(i['nome'],float(i['valor'])) for i in sorted(data['items'],key=lambda x:float(x['valor']),reverse=True)];cards=[{'label':'EM ABERTO','value':money(sum(float(i['valor']) for i in data['items']))},{'label':'VENCIDAS','value':str(len(data['overdue']))},{'label':'PRÓXIMOS 7 DIAS','value':str(len(data['soon']))}]
                section='MAIORES COMPROMISSOS · TOP 6'
            elif view=='balance':
                title='A memória do seu saldo';bars=[('Saldo inicial livre',m['saldo_inicial']),('Entradas realizadas',m['entradas_realizadas']),('Saídas imediatas',-m['saidas_imediatas_realizadas']),('Ajuste de herança',m.get('ajuste_conciliacao_heranca',0))];cards=[{'label':'DISPONÍVEL','value':money(m['saldo_disponivel'])},{'label':'AINDA A RECEBER','value':money(m['entradas_previstas'])},{'label':'SOBRA PREVISTA','value':'Revisar' if m.get('revisoes_conciliacao') else money(m['saldo_projetado'])}]
                section='MEMÓRIA DO SALDO'
            elif view=='budgets':
                title='Gastos por limite definido';bars=[(b['category'],b['spent']) for b in data['budgets']]
                section='GASTO / LIMITE · TOP 6'
            shown=min(6,len(bars));note='O painel não cria nem altera registros.'
            if len(bars)>6:note+=f' Exibindo {shown} de {len(bars)} itens; a lista completa permanece nos detalhes.'
            spec={'title':title,'subtitle':month_label(s.month)+' • até '+date.fromisoformat(data['cutoff']).strftime('%d/%m/%Y'),'cards':cards,'bars':bars,'section':section,'headline':'Seu painel começa por um registro.','detail':'Adicione uma entrada ou despesa para acompanhar seus números aqui.','note':note}
            if view=='analytics':
                spec['footer']='Gastos registrados por competência. Crédito segue a fatura; esses totais não representam o saldo bancário.'
                spec['headline']='Sem gastos registrados neste período'
                spec['detail']='Confira o mês ou abra os detalhes para investigar os lançamentos.'
                if data['future']:
                    spec['subtitle']=month_label(s.month)+' · período futuro'
                    spec['footer']='Este gráfico não antecipa gastos de meses futuros. A pagar mostra faturas e previsões.'
            if view=='home':
                spec['eyebrow']='VISÃO DO MÊS'
                spec['hero']=cards[2]
                spec['cards']=[cards[0],cards[1]]
                spec['hero_tone']='warning' if summary['revisar'] or not summary['base_configurada'] or summary['herdado_auto'] else ('danger' if summary['saldo_final']<0 else 'success')
            if view=='home':
                spec['layout']='summary';spec['details']=[];spec['bars']=[]
                spec['headline']='A RECEBER';spec['detail']=money(summary['a_receber'])
                spec['subtitle']=month_label(s.month)+(' · projeção' if data['future'] else ' · mês encerrado' if closed else ' · consulta em '+self.date_provider().strftime('%d/%m'))
                spec['footer']='Saldo disponível + a receber '+('− reservas líquidas.' if summary['reservas_liquidas']>=0 else '+ ajustes a favor.')
                if summary['revisar']:spec['footer']='Há conciliações pendentes. Abra Entender valores antes de usar a previsão.'
                elif not summary['base_configurada']:spec['footer']='Informe os saldos atuais das contas para conferir esta previsão.'
                elif summary['herdado_auto']:spec['footer']='Base estimada para este período. Confira os saldos das contas.'
            if view=='history':
                spec['subtitle']=month_label(s.month)+' • mesmos filtros do Histórico'
                spec['footer']='Filtro: '+HISTORY_FILTER_LABELS[s.history_filter]+' · '+(s.history_account_filter or 'todas as contas')+' · '+(s.history_category_filter or 'todas as categorias')+((' · busca: '+s.search) if s.search else '')
            if view=='pay':spec['footer']='Todas as contas em aberto da competência e atrasos já existentes. Filtros da lista não são aplicados a este painel geral.'
            if view=='balance':spec['footer']='Memória do caixa e projeção. Os componentes da projeção estão em Abrir detalhes.'
            if view=='budgets':
                spec['bar_limits']=[b['limit'] for b in data['budgets']]
                spec['cards']=[{'label':'LIMITES DEFINIDOS','value':str(len(data['budgets']))},{'label':'ATINGIDOS','value':str(sum(b['ratio']>=1 for b in data['budgets']))},{'label':'PRÓXIMOS DO LIMITE','value':str(sum(.8<=b['ratio']<1 for b in data['budgets']))}]
            if view in {'home','evolution','diagnosis'}:
                from dashboard_metricas import enriquecer
                enriquecer(self,s,data,spec,view)
            if s.privacy:
                # O gráfico é acessível no resumo: também deve respeitar Ocultar.
                spec['cards']=[dict(card,value='••••',hint='') for card in spec['cards']]
                if spec.get('hero'):spec['hero']=dict(spec['hero'],value='••••')
                spec['bars']=[];spec.pop('bar_limits',None)
                spec['details']=[];spec['footer']='Valores ocultos. Use Mostrar no início para revelar os valores.'
                spec['headline']='Valores ocultos';spec['detail']='Use Mostrar no início para revelar os valores.'
                spec['hero_tone']='neutral'
            detail_view='home' if view=='home' else view
            rows=[[('Abrir detalhes',('view',detail_view)),('🏠 Início',('view','home'))]]
            if view=='home':rows=[[('🧮 Entender valores',('origin','previsao')),('🏷 Categorias',('chart','analytics'))]]
            if view in {'home','evolution','diagnosis'}:
                rows=[[('📊 Visão do mês',('chart','home')),('📈 Evolução',('chart','evolution'))],
                      [('🔎 Diagnóstico',('chart','diagnosis')),('🏷 Gastos',('chart','analytics'))],
                      [('🧾 A pagar',('chart','pay')),('🎯 Limites',('chart','budgets'))],
                      [('🧮 Composição',('origin','previsao'))]]
            rows += [[('‹ Mês anterior',('dashboard_month',-1,view)),('Próximo mês ›',('dashboard_month',1,view))],
                     [('↻ Atualizar',('chart',view)),('🏠 Início',('view','home'))]]
            pause_row=self._draft_pause_row(s)
            if pause_row:rows.append(pause_row)
            if s.learning_stage and (s.fixed_edit or s.new_fixed):rows.append([('↩ Retomar cadastro',('learning_resume',))])
            return Screen(heading(spec['title'],month_label(s.month))+'\n\n<i>Caixa, gastos por competência e obrigações têm bases diferentes. Explore Evolução, Diagnóstico e Composição para conferir.</i>' if view in {'home','evolution','diagnosis'} else heading(title,month_label(s.month))+'\n\n<i>Valores dos registros e previsões. Use os detalhes para conferir a composição.</i>',rows,spec)
        if kind=='settle':return self.begin_settlement(key,action[1],action[2])
        if kind=='invoice_begin':return self.begin_invoice_payment(key,action[1],action[2])
        if kind=='installment_schedule':
            return self.installment_schedule(key,action[1] if len(action)>1 else 0)
        if kind=='buy_sim':
            if not s.compra:raise ValueError('Faça a pergunta de novo: posso comprar um celular de 3000 em 10x.')
            if action[1] not in {1,3,6,10}:raise ValueError('Escolha uma opção disponível.')
            s.compra['parcelas']=action[1];s.compra['credito']=action[1]>1
            return self.render(key,'can_buy')
        if kind=='buy_fatura':
            if not s.compra:raise ValueError('Faça a pergunta de novo: posso comprar um celular de 3000 em 10x.')
            s.compra['fatura_prox']=not s.compra.get('fatura_prox',True)
            return self.render(key,'can_buy')
        if kind=='simulate_variant':
            if not s.draft or not s.draft.get('simulate'):raise ValueError('Abra uma simulação primeiro.')
            if action[1] not in {1,3,6}:raise ValueError('Escolha uma opção disponível.')
            s.draft['parcelas_total']=action[1];s.draft['forma_pagamento']='pix' if action[1]==1 else 'crédito'
            return self.preview(key)
        if kind=='pick_target':
            if not s.draft or not s.draft.get('data'):raise ValueError('Essa prévia expirou. Abra Registrar ou o Histórico novamente.')
            s.target_page=0;s.month=competencia_transacao(s.draft);return self.target_picker(key)
        if kind=='target_month':s.target_page=0;s.month=month_shift(s.month,action[1]);return self.target_picker(key)
        if kind=='choose_target':
            if not s.draft:raise ValueError('Esta escolha de previsão expirou. Abra o registro ou o Histórico novamente.')
            if len(action)>3 and action[3] and action[3]!=s.draft.get('key'):
                raise ValueError('Esta escolha pertence a outro registro. Abra a lista de previsões novamente.')
            a=conc.alvo(action[1],action[2]);s.draft['conciliacao']={'id':a['id'],'mes':a['mes'],'assinatura':a['assinatura']}
            return self.preview(key)
        if kind=='link_existing':return self.begin_existing_link(key,action[1])
        if kind=='keep_separate':
            if not s.draft or not s.draft.get('existing_id'):raise ValueError('Abra o Histórico novamente.')
            conc.marcar_separado(s.draft['existing_id'],key,[s.draft[k] for k in ('data','tipo','valor','conta','forma_pagamento')])
            s.stage=None;s.draft=None
            return Screen('Decisão registrada: o movimento foi mantido separado da previsão.',[[('Início',('view','home'))]])
        if kind=='commit_link':
            if not s.draft or s.draft.get('key')!=action[1] or not s.draft.get('existing_id') or not s.draft.get('conciliacao'):
                raise ValueError('Esta confirmação expirou. Abra o Histórico novamente.')
            conc.vincular_existente(s.draft['existing_id'],s.draft['conciliacao'],s.draft['key'],key,
                [s.draft[k] for k in ('data','tipo','valor','conta','forma_pagamento')],
                [s.draft.get('data_compra'),s.draft.get('competencia_fatura')] if s.draft.get('competencia_fatura') else None)
            s.stage=None;s.draft=None
            return Screen('Vínculo salvo. O lançamento existente foi preservado e a previsão foi conciliada.',[[('Conciliações',('view','reconciliations')),('Início',('view','home'))]])
        if kind=='unlink_preview':
            return Screen('Desvincular reabre a previsão e mantém o lançamento real no histórico. Não representa devolução bancária. Deseja continuar?',[[('Sim, desvincular',('unlink',action[1])),('Cancelar',('view','reconciliations'))]])
        if kind=='unlink':
            conc.desvincular(action[1],key)
            return Screen('Vínculo desfeito; o lançamento foi mantido. Revise as previsões antes de usar a sobra.',[[('Conciliações',('view','reconciliations')),('Início',('view','home'))]])
        if kind=='acct_off':return self._acct_off_confirm(key,action[1])
        if kind=='acct_off_ok':return self._acct_off_apply(key,action[1])
        if kind=='acct_on':return self._acct_on(key,action[1])
        if kind=='view':
            target=action[1]
            if target=='register' and s.suspended_draft and s.suspended_stage:
                return Screen('Você já tem um registro pausado. Retome de onde parou ou descarte o rascunho antes de começar outro.',[[('↩ Retomar registro',('resume_suspended',)),('Descartar e abrir novo',('discard_and_register',))]])
            if s.stage and s.draft and target not in {'question'}:
                self._suspend_flow(s)
            if s.view!=target:s.trail=(s.trail+[(s.view,s.month,s.page)])[-12:]
            # Menu/Início (comando /menu, botão 🏠 Início ou ☰) sempre parte do mês vigente,
            # como o atalho de texto "menu"; consultas de outro mês não podem "grudar" aqui.
            if target=='home':s.month=self.date_provider().strftime('%Y-%m')
            s.settings_draft=None;s.stage=None;s.page=0
            return self.render(key,target)
        if kind=='month':s.month=month_shift(s.month,action[1]);s.page=0;return self.render(key,action[2])
        if kind=='current_month':s.month=self.date_provider().strftime('%Y-%m');s.page=0;return self.render(key,action[1])
        if kind=='page':s.page=action[1];return self.render(key)
        if kind=='privacy':
            s.privacy=not s.privacy;self._save_privacy_preference(s.owner or key,s.privacy)
            return self.render(key,'home')
        if kind=='start':
            if s.suspended_draft and s.suspended_stage:
                return Screen('Você tem um registro pausado. Retome-o ou descarte o rascunho para iniciar outro.',[[('↩ Retomar registro',('resume_suspended',)),('Descartar e começar novo',('discard_and_start',action[1]))]])
            return self.begin(key,action[1])
        if kind=='answer':return self.answer(key,action[1])
        if kind=='preview':return self.preview(key)
        if kind=='edit':
            if not s.draft:raise ValueError('Essa prévia expirou. Abra Registrar novamente.')
            s.stage=action[1];s.draft['_edit']=True
            if s.stage=='account':s.account_choice_page=0
            return self.prompt(s)
        if kind=='search':s.stage='search';s.draft=None;return self.prompt(s)
        if kind=='clear_search':s.search='';s.page=0;return self.render(key,'history')
        if kind=='cancel':
            s.media_review=None
            old_stage=s.stage
            cancel_view=(s.draft or {}).get('_cancel_view')
            cash_cfg=s.settings_draft if old_stage in {'cash_setup_value','cash_setup_confirm','cash_setup_account_name'} else None
            if cash_cfg is not None:
                saved=len(cash_cfg.get('changes') or [])
                month=cash_cfg.get('month') or s.month
                s.stage=None;s.draft=None;s.settings_draft=None
                if saved:
                    return Screen(
                        f'<b>Ajuste de saldos encerrado.</b>\n\n{plural(saved, "conta já confirmada continua", "contas já confirmadas continuam")} salva{"" if saved == 1 else "s"}. As demais não foram alteradas.',
                        [[('🏦 Ver saldos por conta',('cash_accounts',month)),('🏠 Início',('view','home'))]])
                return Screen('Ajuste cancelado. Nenhum saldo foi alterado.',[[('🏦 Ver saldos por conta',('cash_accounts',month)),('🏠 Início',('view','home'))]])
            s.stage=None;s.draft=None;s.settings_draft=None
            if str(old_stage or '').startswith('invoice_') and s.trail and s.trail[-1][0]=='pay':
                s.view,s.month,s.page=s.trail.pop()
                return self.render(key)
            target=cancel_view if cancel_view in {'pay','receivables','history'} else 'register'
            if old_stage=='ask':target='assistant'
            elif old_stage=='search':
                return self.render(key,'history')
            elif old_stage=='account_search':
                target=s.filter_view if s.filter_view in {'pay','history'} else 'history'
                if s.trail and s.trail[-1][0]==target:
                    s.view,s.month,s.page=s.trail.pop()
                    return self.render(key)
                return self.render(key,target)
            elif old_stage in {'alert_hours','confirm_settings'}:target='alerts'
            elif old_stage in {'budget_category','budget_amount','confirm_budget'}:target='budgets'
            elif old_stage in {'initial_balance','confirm_balance'}:target='balance'
            elif old_stage=='confirm_reconcile_baseline':target='review'
            elif old_stage=='fix_date':target='history'
            label={'assistant':'Assessor','history':'Histórico','alerts':'Alertas','budgets':'Limites','balance':'Saldo','register':'Registrar','pay':'A pagar','receivables':'A receber','review':'Revisar'}[target]
            return Screen('Cancelado. Nenhuma alteração foi salva.',[[(label,('view',target)),('🏠 Início',('view','home'))]])
        if kind=='commit':
            if not s.draft or s.stage!='confirm' or s.draft['key']!=action[1] or s.draft.get('simulate') or s.draft.get('existing_id'):
                return Screen('Essa confirmação expirou ou já foi usada.',[[('Histórico',('view','history'))]])
            if self._registration_stage(s.draft) != 'confirm':
                return self._advance_registration(key)
            event=s.draft['key'];t=copy.deepcopy(self.payload(s.draft));antes=efeito_baixa.instantaneo(t)  # saldo antes de gravar
            if not t.get('conciliacao'):t['sem_vinculo_confirmado']=True
            result=confirmar_registro(t,event,key);efeito=efeito_baixa.confirmacao(antes,t,money)
            s.draft=None;s.stage=None;s.last_event=event;s.month=t['data'][:7]
            ids=', '.join('#'+str(i) for i in result['ids'][:4])
            invoice_note = ('\nData da compra: '+date.fromisoformat(t['data']).strftime('%d/%m/%Y')+'\nFatura: '+month_label(competencia_transacao(t))) if eh_credito(t) else ''
            unico=len(result['ids'])==1 and int(t.get('parcelas_total') or 1)==1
            barra=[('↩ Desfazer',('undo_preview',event))]
            if unico:barra+=[('🏷 Categoria',('cat_menu',result['ids'][0])),('🔁 Repetir',('repeat',result['ids'][0]))]
            limite_note=self._aviso_limite(t)
            return self._apply_privacy(s,Screen(f'<b>✅ Registro salvo</b>\n\n<b>{safe(t["descricao"])}</b>\n💰 Valor: <b>{money(t["valor"])}</b>\n🏦 Conta: {safe(t["conta"])}\n🏷 Categoria: {safe(t["categoria"])}\n💸 Forma: {safe(t["forma_pagamento"])}\n📅 Data: {date.fromisoformat(t["data"]):%d/%m/%Y}'+invoice_note+'\n\nJá está no seu Histórico.'+efeito+limite_note+f'\n\n<i>Código para comandos de texto: {ids}'+('…' if len(result['ids'])>4 else '')+'</i>',[
                barra,
                *([[('🎯 Ver limites',('view','budgets'))]] if limite_note else []),
                [('🏠 Início',('view','home')),('➕ Outro registro',('view','register'))],
                *([[('Ver fatura escolhida', ('pay_account_detail', t['conta'], competencia_transacao(t)))]] if eh_credito(t) else [])]))
        if kind=='dup_view':
            raw=db.buscar_transacao_por_id(int(action[1]))
            if not raw:raise ValueError('Esse lançamento não existe mais.')
            x=dict(raw)
            return self._apply_privacy(s,Screen(f'<b>Lançamento parecido</b>\n{safe(x["descricao"],160)}\n\n💰 {money(x["valor_total_parcelamento"] or x["valor"])} · {safe(x["forma_pagamento"])}\n📅 {x["data"][8:10]}/{x["data"][5:7]}/{x["data"][:4]}\n🏦 {safe(x["conta"])}\n🏷 {safe(x["categoria"])}\n\nSeu registro novo continua aguardando: nada foi salvo.',
                [[('↩ Voltar ao registro',('dup_back',)),('Cancelar',('cancel',))]]))
        if kind=='dup_back':return self.preview(key)
        if kind=='cat_menu':return self._categoria_menu(int(action[1]))
        if kind=='cat_all':return self._categoria_menu(int(action[1]),todas=True)
        if kind=='cat_preview':
            tid=int(action[1]);raw=db.buscar_transacao_por_id(tid)
            if not raw:raise ValueError('Esse lançamento não existe mais.')
            x=dict(raw);nova=validar_campo_textual('categoria',action[2])
            if norm(nova)==norm(x['categoria']):return self._categoria_menu(tid)
            if any(v['transacao_id']==tid for v in conc.listar_vinculos()):
                return Screen('Esse lançamento está ligado a uma previsão e não pode ser alterado aqui. Desvincule pela tela Conciliações antes.',[[('Ver conciliação',('view','reconciliations')),('↩ Lançamento',('transaction',tid))]])
            return Screen(f'<b>Trocar a categoria?</b>\n{safe(x["descricao"],80)}\n\n🏷 {safe(x["categoria"])} → <b>{safe(nova)}</b>\n\nSó a categoria muda; valor, conta e data ficam iguais. A troca fica na auditoria.',
                [[('✅ Confirmar troca',('cat_confirm',tid,nova,x['categoria'],secrets.token_urlsafe(12))),('Cancelar',('transaction',tid))]])
        if kind=='cat_confirm':
            tid,nova,antiga,chave=int(action[1]),action[2],action[3],action[4]
            mudou=corrigir_categoria_registro(tid,nova,chave,key,antiga)
            rows=[[('🧠 Aprender para próximas vezes',('cat_learn',tid,nova))] if mudou else [],[('↩ Lançamento',('transaction',tid)),('🏠 Início',('view','home'))]]
            return Screen(f'<b>🏷 Categoria atualizada</b>\n\n{self._tx_desc(tid)}: {safe(antiga)} → <b>{safe(nova)}</b>' if mudou else 'Essa troca já havia sido confirmada. Nada foi alterado de novo.',[r for r in rows if r])
        if kind=='cat_learn':
            from categorias_pessoais import salvar_regra
            raw=db.buscar_transacao_por_id(int(action[1]))
            if not raw:raise ValueError('Esse lançamento não existe mais.')
            salvar_regra(dict(raw)['descricao'],action[2])
            return Screen(f'🧠 Combinado. Da próxima vez que aparecer “{safe(dict(raw)["descricao"],60)}”, sugiro {safe(action[2])}. Você pode remover a regra em Meus dados.',[[('↩ Lançamento',('transaction',int(action[1]))),('🏠 Início',('view','home'))]])
        if kind=='date_menu':return self._data_menu(s,int(action[1]))
        if kind=='date_type':
            tid=int(action[1]);self._data_menu(s,tid)  # revalida antes de pedir o texto
            s.stage='fix_date';s.settings_draft={'tid':tid};s.draft=None
            return Screen('<b>📅 Qual é a data certa?</b>\n\nDigite DD/MM/AAAA, DD/MM, "ontem" ou "dia 15". Você confere na próxima tela; nada muda agora.',
                          [[('Cancelar',('transaction',tid))]])
        if kind=='date_preview':return self._data_previa(s,int(action[1]),action[2])
        if kind=='date_confirm':
            tid,nova,antiga,chave=int(action[1]),action[2],action[3],action[4]
            mudou=corrigir_data_registro(tid,nova,chave,key,antiga,hoje=self.date_provider())
            fmt=lambda v:date.fromisoformat(v).strftime('%d/%m/%Y')
            return Screen(f'<b>📅 Data atualizada</b>\n\n{self._tx_desc(tid)}: {fmt(antiga)} → <b>{fmt(nova)}</b>\nA troca fica na auditoria.' if mudou else 'Essa troca já havia sido confirmada. Nada foi alterado de novo.',
                          [[('↩ Lançamento',('transaction',tid)),('🏠 Início',('view','home'))]])
        if kind=='undo_preview':
            return Screen('<b>Desfazer este registro?</b>\n\nSerão removidos somente os lançamentos desta confirmação, incluindo suas parcelas. A ação fica no histórico de auditoria.',[
                [('Sim, desfazer',('undo',action[1])),('Manter registro',('view','history'))]])
        if kind=='undo':
            changed=desfazer_registro(action[1],key)
            return Screen('Registro desfeito.' if changed else 'Esse registro já havia sido desfeito.',[[('🏠 Início',('view','home')),('Histórico',('view','history'))]])
        raise ValueError('Ação desconhecida. Abra /menu novamente.')

    @staticmethod
    def _tx_desc(tid):
        """Descrição curta e escapada de um lançamento, para títulos sem o id interno."""
        raw = db.buscar_transacao_por_id(int(tid))
        return safe((dict(raw).get('descricao') if raw else '') or 'Lançamento', 60)

    def _categoria_menu(self,tid,todas=False):
        raw=db.buscar_transacao_por_id(tid)
        if not raw:raise ValueError('Esse lançamento não existe mais.')
        x=dict(raw);atual=x['categoria'] or 'Outros'
        if todas:
            from categorias import CATEGORIAS_CANONICAS
            opcoes=[c for c in CATEGORIAS_CANONICAS if (c!='Receita' or x['tipo']=='receita')]
        else:opcoes=self._categorias_provaveis(x)
        botoes=[(('✓ ' if norm(c)==norm(atual) else '')+c,('disabled',) if norm(c)==norm(atual) else ('cat_preview',tid,c)) for c in opcoes]
        rows=[botoes[i:i+3] for i in range(0,len(botoes),3)]
        rows.append([('Outra…',('cat_all',tid))] if not todas else [('↩ Mais prováveis',('cat_menu',tid))])
        rows.append([('↩ Lançamento',('transaction',tid)),('🏠 Início',('view','home'))])
        return Screen(f'<b>🏷 Categoria de “{safe(x["descricao"],60)}”</b>\n\nAtual: <b>{safe(atual)}</b>\nEscolha a nova. Você confirma na próxima tela; nada muda agora.',rows)

    def _categorias_limite(self,limite=9):
        """Categorias para o limite: as que já têm limite, as mais usadas em despesas e as canônicas."""
        from categorias import CATEGORIAS_CANONICAS
        vistos=[]
        def add(c):
            if c and c!='Receita' and norm(c) not in {norm(v) for v in vistos} and len(vistos)<limite:vistos.append(c)
        for m in db.listar_metas():add(dict(m)['categoria'])
        with db.get_connection() as conn:
            for (c,) in conn.execute("SELECT categoria FROM transacoes WHERE tipo='despesa' AND categoria<>'' GROUP BY categoria ORDER BY count(*) DESC LIMIT 9").fetchall():add(c)
        for c in CATEGORIAS_CANONICAS:add(c)
        return vistos

    def _aviso_limite(self,t):
        """Só aviso (não bloqueia): a despesa salva levou a categoria a >=80% ou além do limite."""
        try:
            if t.get('tipo')!='despesa':return ''
            alvo=orient.normalizar(t.get('categoria') or '')
            metas=[dict(m) for m in db.listar_metas() if orient.normalizar(dict(m)['categoria'])==alvo]
            if not metas:return ''
            hoje=self.date_provider()
            mes=competencia_transacao(t) if eh_credito(t) else str(t['data'])[:7]
            txs=[x for x in self.transactions(mes) if x['tipo']=='despesa' and x['data']<=max(hoje.isoformat(),str(t['data']))]
            for item in orient.situacao_limites(metas,txs,hoje,mes):
                if item['ratio']<Decimal('0.8'):continue
                pct_txt=pct(float(item['ratio'])*100,0)
                base=f'{money(float(item["gasto"]))} de {money(float(item["limite"]))} ({pct_txt}) em {month_label(mes)}'
                if item['gasto']>item['limite']:
                    return f'\n\n🔴 <b>Limite de {safe(item["categoria"])} estourado</b>: {base}.'
                if item['gasto']==item['limite']:
                    return f'\n\n🔴 <b>Limite de {safe(item["categoria"])} atingido</b>: {base}.'
                return f'\n\n🟡 <b>Limite de {safe(item["categoria"])} perto do fim</b>: {base}.'
        except Exception:
            logging.warning('Aviso de limite indisponível após salvar.',exc_info=True)
        return ''

    def _data_bloqueio(self,tid):
        raw=db.buscar_transacao_por_id(tid)
        if not raw:raise ValueError('Esse lançamento não existe mais.')
        x=dict(raw)
        if any(v['transacao_id']==tid for v in conc.listar_vinculos()):
            return x,Screen('Esse lançamento está ligado a uma previsão e não pode ser alterado aqui. Desvincule pela tela Conciliações antes.',[[('Ver conciliação',('view','reconciliations')),('↩ Lançamento',('transaction',tid))]])
        motivo=motivo_bloqueio_data(x)
        if motivo:return x,Screen(safe(motivo),[[('↩ Lançamento',('transaction',tid)),('🏠 Início',('view','home'))]])
        return x,None

    def _data_menu(self,s,tid):
        x,bloqueio=self._data_bloqueio(tid)
        if bloqueio:return bloqueio
        hoje=self.date_provider()
        dias=[(hoje-timedelta(days=n)) for n in range(0,3)]
        nomes=['Hoje','Ontem','Anteontem']
        botoes=[(f'{nome} ({d:%d/%m})',('date_preview',tid,d.isoformat())) for nome,d in zip(nomes,dias) if d.isoformat()!=x['data']]
        rows=[botoes,[('✏️ Outra data',('date_type',tid))],[('↩ Lançamento',('transaction',tid)),('🏠 Início',('view','home'))]]
        atual=date.fromisoformat(x['data']).strftime('%d/%m/%Y')
        return Screen(f'<b>📅 Data de “{safe(x["descricao"],60)}”</b>\n\nAtual: <b>{atual}</b>\nEscolha a nova. Você confirma na próxima tela; nada muda agora.',[r for r in rows if r])

    def _data_previa(self,s,tid,nova):
        x,bloqueio=self._data_bloqueio(tid)
        if bloqueio:return bloqueio
        nova=date.fromisoformat(str(nova)).isoformat()
        if nova>self.date_provider().isoformat():
            return Screen('A data não pode ser depois de hoje. Para algo que ainda vai acontecer, use uma previsão.',[[('📅 Escolher outra',('date_menu',tid)),('↩ Lançamento',('transaction',tid))]])
        if nova==x['data']:return self._data_menu(s,tid)
        fmt=lambda v:date.fromisoformat(v).strftime('%d/%m/%Y')
        aviso='\n\n⚠️ A data muda de mês: o lançamento passa a contar em '+month_label(nova[:7])+'.' if nova[:7]!=x['data'][:7] else ''
        return Screen(f'<b>Trocar a data?</b>\n{safe(x["descricao"],80)}\n\n📅 {fmt(x["data"])} → <b>{fmt(nova)}</b>{aviso}\n\nSó a data muda; valor, conta e categoria ficam iguais. A troca fica na auditoria.',
            [[('✅ Confirmar data',('date_confirm',tid,nova,x['data'],secrets.token_urlsafe(12))),('Cancelar',('transaction',tid))]])

    def _categorias_provaveis(self,x,limite=5):
        """Atual, histórico da mesma descrição, sugestão do dicionário/regras e as mais usadas."""
        from categorias import CATEGORIAS_CANONICAS
        vistos=[]
        def add(c):
            if c and norm(c) not in {norm(v) for v in vistos} and len(vistos)<limite and (c!='Receita' or x['tipo']=='receita'):vistos.append(c)
        add(x['categoria'])
        with db.get_connection() as conn:
            for (c,) in conn.execute("SELECT categoria FROM transacoes WHERE tipo=? AND lower(descricao)=lower(?) AND categoria<>'' GROUP BY categoria ORDER BY count(*) DESC, max(id) DESC LIMIT 5",(x['tipo'],x['descricao'] or '')).fetchall():add(c)
            add(sugerir_categoria(x['descricao'],x['tipo']))
            for (c,) in conn.execute("SELECT categoria FROM transacoes WHERE tipo=? AND categoria<>'' GROUP BY categoria ORDER BY count(*) DESC LIMIT 8",(x['tipo'],)).fetchall():add(c)
        for c in CATEGORIAS_CANONICAS:add(c)
        return vistos

    def _flow_help_screen(self,s):
        stage_label={
            'installment_choice':'parcelamento', 'amount':'valor', 'description':'descrição',
            'method':'forma de pagamento', 'account':'conta', 'date':'data',
            'installments':'parcelamento', 'billing_month':'fatura', 'category':'categoria', 'confirm':'confirmação',
        }.get(s.stage,'registro')
        return Screen(
            '<b>Ajuda durante o registro</b>\n\n'
            f'Você está na etapa de <b>{safe(stage_label)}</b>. Seu rascunho continua preservado e nada foi salvo por abrir esta ajuda.\n\n'
            'Retome para continuar de onde parou. Se quiser abandonar este registro, use Cancelar.',
            [[('↩ Retomar registro',('flow_resume',)),('Cancelar registro',('cancel',))]],
        )

    # ------------------------------------------------------------------
    # Fechamento do caminho legado: texto sem verbo, "novo fixo ..." e
    # "transferi ..." nunca gravam direto. Viram prévia/rascunho nativo e só
    # gravam pelo botão Salvar do titular.
    # ------------------------------------------------------------------
    _LEGADO_FORMAS={'pix':'pix','debito':'débito','credito':'crédito','cartao':'crédito','dinheiro':'dinheiro','boleto':'boleto','transferencia':'transferência'}
    _LEGADO_LIGACOES={'no','na','em','de','do','da','todo','todos','mes','por','pelo','pela','a','o','com','via','vence','vencimento','mensal','mensalmente','cartao','conta','pago','paga','paguei'}
    _LEGADO_CABECALHOS=re.compile(r'^(?:quanto|qual|quais|onde|como|mostr\w*|ver|listar|lista|extrato|historico|pagar|pagamento|quitar|quitei|baixa|dar|marcar|estorno|reembolso|credito|nova|novo|criar|cadastrar|adicionar|incluir|aprender|simular|posso|vale|saldo|meta|metas|agenda|parcelas?|contas?|formas?|categorias?|detalhar|entradas?|receitas?|fixos?|compromissos?|resumo|relatorio|status|vencimentos?|exportar|importar|analisar|backup|revisar|revisao|registrar|ajustes?|diagnostico|fechamento|assessor|transferencias?|mover|movimentar|passei|transferi|transferir|transferencia|confirmar|cancelar)\b')
    _LEGADO_SUBSTANTIVOS=re.compile(r'^(?:guia|caixa|hoje|dinheiro|aula|manual|tutorial|treinamento)\b')

    def _legado_recusa(self,motivo):
        return Screen('<b>Nada foi registrado.</b>\n\n'+safe(motivo)+'\n\nPara lançar, comece com o verbo (por exemplo: <i>gastei 45 no mercado</i>) ou abra Registrar e preencha por etapas.',
                      [[('➕ Registrar',('view','register')),('🏠 Início',('view','home'))]])

    def _fechar_caminho_legado(self,key,text):
        """Devolve uma Screen quando o texto seria gravado direto pelo roteador legado; None caso contrário."""
        clean=norm(text)
        if re.match(r'^(?:novo|cadastrar|adicionar|incluir|criar)\s+fixo\b',clean):
            return self._legado_novo_fixo(key,text)
        if svc.parsear_comando_transferencia_caixa(text) is not None:
            return self._legado_transferencia(key,text)
        return self._legado_lancamento_livre(key,text)

    def _legado_transferencia(self,key,text):
        s=self.session(key)
        paused=self._paused_draft_guard(s)
        if paused is not None:return paused
        fields=dict(svc.parsear_comando_transferencia_caixa(text) or {})
        if not fields.get('erro'):
            if not re.search(r'\d{4}-\d{2}-\d{2}',text):fields['data']=self.date_provider().isoformat()
            fields['forma_pagamento']='transferência'
        from telegram_midia import _transfer_screen
        s.draft=None;s.stage=None
        s.media_review={'text':str(text).strip()[:5000],'source':'texto','fields':fields,'suggested_kind':'transferencia','nonce':secrets.token_urlsafe(12)}
        return _transfer_screen(s.media_review)

    def _legado_novo_fixo(self,key,text):
        s=self.session(key)
        tokens=re.sub(r'^\s*\S+\s+fixo\b','',text.strip(),count=1,flags=re.I).split()
        ntokens=[norm(t) for t in tokens]
        used=[False]*len(tokens)
        dia=None;forma=None;conta=None;ambiguo_forma=False
        for i,t in enumerate(ntokens):
            if t=='dia' and i+1<len(tokens) and re.fullmatch(r'\d{1,2}',ntokens[i+1]) and dia is None:
                dia=int(ntokens[i+1]);used[i]=used[i+1]=True
        for i,t in enumerate(ntokens):
            if used[i] or t not in self._LEGADO_FORMAS:continue
            valor_forma=self._LEGADO_FORMAS[t]
            if t!='cartao' or forma is None:
                if forma and forma!=valor_forma:ambiguo_forma=True
                forma=forma or valor_forma
            used[i]=True
        if ambiguo_forma:forma=None
        from registro_conversa import CONTAS
        chaves={norm(k):v for k,v in CONTAS.items()}
        for nome in self.accounts():chaves.setdefault(norm(nome),nome)
        for k in sorted(chaves,key=lambda x:-len(x.split())):
            kt=k.split()
            for i in range(len(ntokens)-len(kt)+1):
                if ntokens[i:i+len(kt)]==kt and not any(used[i:i+len(kt)]):
                    conta=chaves[k]
                    for j in range(i,i+len(kt)):used[j]=True
                    break
            if conta:break
        numericos=[i for i,t in enumerate(ntokens) if not used[i] and re.fullmatch(r'(?:r\$)?\d+(?:[.,]\d+)*',t)]
        valor=None
        if len(numericos)==1:
            try:
                valor=float(parse_money(re.sub(r'^r\$','',ntokens[numericos[0]])))
                if valor<=0 or valor>100000000:valor=None
                else:used[numericos[0]]=True
            except (ValueError,ArithmeticError):valor=None
        resto=[tokens[i] for i in range(len(tokens)) if not used[i] and norm(tokens[i])!='r$']
        while resto and norm(resto[0]) in self._LEGADO_LIGACOES:resto.pop(0)
        while resto and norm(resto[-1]) in self._LEGADO_LIGACOES:resto.pop()
        nome=' '.join(resto).strip()
        if len(nome)>160:nome=''
        nome=nome[:1].upper()+nome[1:]
        if dia is not None and not 1<=dia<=31:dia=None
        self.begin_new_fixed(key)
        d=s.new_fixed
        d.update(nome=nome,valor=valor,forma_pagamento=forma or '',conta_pagamento=conta or '',dia_vencimento=dia)
        if nome:
            d['categoria_sugerida']=self._registration_category(nome,'despesa') or 'Outros'
            d['categoria']=d['categoria_sugerida']
        faltando=[st for campo,st in (('nome','new_fixed_name'),('valor','new_fixed_amount'),('forma_pagamento','new_fixed_method'),
                  ('conta_pagamento','new_fixed_account'),('dia_vencimento','new_fixed_due')) if d.get(campo) in (None,'')]
        if not faltando:return self._new_fixed_preview(key)
        if len(faltando)==1:d['_return_preview']=True
        s.stage=faltando[0]
        return self._new_fixed_prompt(s)

    def _legado_lancamento_livre(self,key,text):
        clean=norm(text)
        if '?' in text or re.search(r'\bfaturas?\b',clean):return None
        from roteamento_seguro import comando_operacional
        if comando_operacional(text):return None
        parece_lancamento=len(clean.split())>=3 and re.search(r'\d',clean) and not re.search(r'\d{4}-\d',clean)
        if self._LEGADO_CABECALHOS.match(clean):return None
        if self._LEGADO_SUBSTANTIVOS.match(clean) and not parece_lancamento:return None
        if re.search(r'(?<!\d)\d{4}-\d{2}(?!-?\d)',text):return None
        try:
            tx=parse_mensagem(text,data_referencia=self.date_provider())
        except (ValueError,TypeError,ArithmeticError):
            return None
        if not tx or tx.get('erro'):return None
        try:
            valor=parse_money(str(tx['valor']))
        except (ValueError,ArithmeticError):
            return self._legado_recusa('Não consegui ler o valor com segurança.')
        mascarado=re.sub(r'\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b|\b\d{4}-\d{2}-\d{2}\b|\b\d+\s*x\b',lambda m:' '*len(m.group()),text,flags=re.I)
        achados=list(re.finditer(r'(?<![\w/.,-])(?:r\$\s*)?\d+(?:[.,]\d+)*(?:\s*(?:mil|k)\b)?(?:\s+reais\b)?(?![\w/])',mascarado,re.I))
        if len(achados)!=1:
            return self._legado_recusa('Não consegui separar com segurança o valor do resto da frase: '+text.strip()[:120])
        resto=re.sub(r'\s+',' ',(text[:achados[0].start()]+' '+text[achados[0].end():])).strip()
        verbo='recebi' if tx.get('tipo')=='receita' else 'gastei'
        frase=f'{verbo} {str(valor).replace(".",",")} {resto}'.strip()
        s=self.session(key)
        paused=self._paused_draft_guard(s)
        if paused is not None:return paused
        screen=self.parse_draft(key,frase)
        d=s.draft
        if not d or d.get('valor') is None or parse_money(str(d['valor']))!=valor:
            s.draft=None;s.stage=None
            return self._legado_recusa('Não consegui montar o rascunho com segurança a partir de: '+text.strip()[:120])
        d['mensagem_original']=text
        return screen

    def _conta_citada(self,trecho):
        alvo=norm(re.sub(r'^(?:do|da|de|no|na|em|conta|banco|cartao|cartão)\s+','',trecho.strip()))
        alvo=re.sub(r'^(?:conta|banco|cartao)\s+','',alvo).strip()
        if not alvo:return ''
        nomes=self.accounts()
        return (next((n for n in nomes if norm(n)==alvo),'') or next((n for n in nomes if norm(n).startswith(alvo)),''))

    def _rota_frase_natural(self,s,key,clean):
        """Frases frequentes que caíam em "Comando não reconhecido" e têm tela nativa. Só navega; nunca grava."""
        hoje=self.date_provider().strftime('%Y-%m')
        m=re.fullmatch(r'(?:ver\s+|meu\s+|o\s+)?extrato(?:\s+(.+))?',clean)
        if m:
            s.month=hoje;s.history_filter='all';s.search='';s.history_category_filter='';s.page=0
            if m[1]:
                conta=self._conta_citada(m[1])
                if not conta:
                    s.filter_view='history'
                    nome=re.sub(r'^(?:do|da|de|no|na|em)\s+','',m[1])
                    return Screen(f'Não encontrei a conta “{safe(nome,40)}”. Escolha uma conta para ver o extrato.',
                                  [[('🏦 Escolher conta',('accounts_for','history'))],[('🔎 Histórico completo',('view','history')),('🏠 Início',('view','home'))]])
                s.history_account_filter=conta
            else:s.history_account_filter=''
            return self.act(key,('view','history'))
        m=re.fullmatch(r'(?:ver\s+|minhas?\s+|as\s+)?faturas?(?:\s+(?:do\s+|de\s+)?(?:cartao|cartoes))?(?:\s+(.+))?',clean)
        if m:
            s.month=hoje
            if m[1]:
                conta=self._conta_citada(m[1])
                if conta:return self.act(key,('pay_account_detail',conta,hoje))
                return Screen(f'Não encontrei o cartão “{safe(m[1],40)}”. As faturas do mês estão em A pagar.',
                              [[('🧾 A pagar',('view','pay')),('🏠 Início',('view','home'))]])
            return self.act(key,('view','pay'))
        m=re.fullmatch(r'(?:buscar|procurar|pesquisar|encontrar|historico\s+de|historico\s+do|historico\s+da)\s+(.+)',clean)
        if m:s.month=hoje;s.history_filter='all';s.history_account_filter='';s.history_category_filter='';s.page=0;return self.act(key,('buscar_texto',m[1]))  # todos os meses (busca_lancamentos)
        if clean in {'contas','minhas contas','meus bancos','bancos','gerenciar contas','contas bancarias'}:
            return self.act(key,('view','accounts_manage'))
        if clean in {'limite','limites','meus limites','limites de gastos'}:
            return self.act(key,('view','budgets'))
        if re.fullmatch(r'(?:fazer|criar|gerar)\s+(?:um\s+|o\s+)?backup(?:\s+agora)?',clean):
            return Screen('<b>💾 Backup</b>\n\nToque abaixo para criar a cópia de recuperação agora. Se o PIN estiver ativo, ele será pedido como de costume.',
                          [[('💾 Criar backup',('legacy_raw','backup'))],[('🔐 Meus dados',('view','data_tools')),('🏠 Início',('view','home'))]])
        return None

    def handle_text(self,key,text):
        s=self.session(key);clean=norm(text)
        lesson=learning.route(text)
        if lesson is not None and (not s.stage or s.stage=='ask' or str(text).startswith('/aprender')):
            return self.open_learning(key,lesson)
        if s.stage and str(s.stage).startswith('new_fixed_'):
            return self._new_fixed_text(key,text)
        from fixos_interface import texto as fixed_text
        fixed_screen=fixed_text(self,key,text)
        if fixed_screen is not None:return fixed_screen
        # `norm()` removes Unicode variation selectors (category Mn). Therefore a
        # label such as "⚙️ Mais" becomes "⚙ mais". Keep text aliases as the
        # canonical route and also accept the normalized emoji forms emitted by
        # Telegram keyboards.
        if clean in {'ajuda','help','__help__'} and s.stage and s.draft:
            return self._flow_help_screen(s)
        shortcuts={'🏠 inicio':'home','inicio':'home','menu':'home','central':'home',
                   '➕ registrar':'register','registrar':'register','🧾 a pagar':'pay','a pagar':'pay',
                   '🔎 historico':'history','historico':'history','📊 analises':'analytics','analises':'analytics',
                   '⚙ mais':'more','⚙️ mais':'more','⚙':'more','mais':'more',
                   'engrenagem':'more','configuracoes':'more','ajustes':'more',
                   'ajuda':'help','help':'help','__help__':'help'}
        if clean in shortcuts:
            route=shortcuts[clean]
            if route in {'home','pay','history','analytics','balance','agenda','receivables','reconciliations','recurring','plan'}:
                s.month=self.date_provider().strftime('%Y-%m')
            return self.act(key,('view',route))
        if clean in {'cancelar','/cancelar'} and s.stage:return self.act(key,('cancel',))
        dashboard=dashboard_route(text)
        if dashboard and (not s.stage or s.stage=='ask'):
            view,period=dashboard
            if period:
                month=svc.normalizar_ano_mes_flexivel(period)
                if not month or not svc.validar_ano_mes(month):
                    raise ValueError('Informe o período como Painel AAAA-MM, por exemplo Painel 2026-10.')
                s.month=month
            if s.stage=='ask':s.stage=None
            return self.act(key,('chart',view))
        if s.stage:return self.answer(key,text)
        invoice_cmd=svc.parsear_comando_movimento_fatura(text)
        if invoice_cmd and invoice_cmd[0]=='erro':
            return Screen(safe(invoice_cmd[1]),[[('🧾 A pagar',('view','pay')),('🏠 Início',('view','home'))]])
        if invoice_cmd and invoice_cmd[0]=='registrar' and invoice_cmd[1] in {'pagamento_total','pagamento_parcial'}:
            return self.begin_invoice_payment_from_command(key,invoice_cmd)
        query=re.fullmatch(r'(meu mes|fechamento|fechamento do mes|fechamento mensal|atencao|central de atencao|resumo|diagnostico|quanto vou pagar|quanto pagar|saldo geral|agenda|alertas|a receber|conciliações|conciliacoes|assinaturas|meu plano|assessor)(?:\s+(\d{4}-\d{2}))?',clean)
        if query:
            if query[2]:date.fromisoformat(query[2]+'-01');s.month=query[2]
            else:s.month=self.date_provider().strftime('%Y-%m')
            view={'meu mes':'home','fechamento':'closing','fechamento do mes':'closing','fechamento mensal':'closing','atencao':'attention','central de atencao':'attention','resumo':'home','diagnostico':'plan','quanto vou pagar':'pay','quanto pagar':'pay','saldo geral':'balance','agenda':'agenda','alertas':'alerts','a receber':'receivables','conciliações':'reconciliations','conciliacoes':'reconciliations','assinaturas':'recurring','meu plano':'plan','assessor':'assistant'}[query[1]]
            return self.act(key,('view',view))
        natural=self._rota_frase_natural(s,key,clean)
        if natural is not None:return natural
        if clean.startswith('/help') or clean.startswith('help '):
            topic=clean.split(maxsplit=1)[1] if ' ' in clean else ''
            if not topic:return self.act(key,('view','help'))
            aliases={'lancamentos':'registrar','caixa':'saldo','heranca':'saldo','checklist':'pagar','entradas':'receber','metas':'limites','assessor':'ia','seguranca':'privacidade','primeiros passos':'primeiros','comecar':'primeiros','cartao':'faturas','credito':'faturas','previsoes':'compromissos','analises':'analisar','painel':'dashboard','dash':'dashboard'}
            selected=aliases.get(topic,topic)
            if selected in HELP_TOPICS or selected in orient.TOPICS:return self.act(key,('topic',selected))
            return None
        # Natural-language consultation does not depend on punctuation. Try the
        # deterministic financial-intent router before requiring a question mark.
        # Explicit transaction commands remain reserved for the registration flow.
        if orient.eh_pergunta_compra(text):return self.begin_can_buy(key,text)
        if not re.match(r'^(gastei|recebi|comprei|paguei|ganhei|entrada)\b',clean):
            natural_view=orient.reconhecer_pergunta(text)
            if natural_view:return self.act(key,('view',natural_view))
        if '?' in text and not re.match(r'^(gastei|recebi|comprei|paguei|entrada)\b',clean):return self.question_result(key,text)
        if re.match(r'^entrada\s+(?!fixa\b|avulsa\b)',clean):return self.parse_draft(key,'recebi '+text.split(maxsplit=1)[1])
        baixa=svc.parsear_comando_marcar_checklist(clean)
        if baixa and baixa[2]=='pago':
            _,item=svc.resolver_item_checklist(baixa[0],baixa[1])
            if item and item.get('origem')=='compromisso':return self.begin_settlement(key,int(item['id']),baixa[0])
        if clean.startswith('simular '):return self.parse_draft(key,text[8:].strip(),True)
        if re.match(r'^(gastei|comprei|recebi|ganhei|paguei)(?:\s+|$)',clean):
            # Checklist and invoice commands retain their existing dedicated flow.
            if svc.parsear_comando_marcar_checklist(clean) or svc.parsear_comando_marcar_checklist_multiplo(clean):return None
            if re.search(r'\bfatura\b',clean):return None
            return self.parse_draft(key,text)
        if re.fullmatch(r'[\d\s.,/+\-]+',clean):
            return Screen('Esse valor está sem contexto. Abra Registrar para informar a que ele se refere.',[[('➕ Registrar',('view','register'))]])
        # Nada que o roteador legado gravaria direto passa daqui sem prévia.
        return self._fechar_caminho_legado(key,text)


    def screen_plan(self,s):
        data=orient.coletar(self,s);items=data['insights'];text=[f'<b>Seu plano · {month_label(s.month)}</b>','Uma prioridade por vez. Cada sugestão mostra o motivo.',''];rows=[]
        for i,item in enumerate(items[:5],1):
            text += [f'<b>{i}. {safe(item["title"])}</b>',safe(item['detail'],230),'']
            rows.append([('Abrir: '+cortar(item['title'],30),('view',item['view']))])
        text+=['As sugestões vêm de regras locais e dos registros; não executam operações.']
        return Screen('\n'.join(text),rows+self.nav('plan'))

    def screen_agenda(self,s):
        data=orient.coletar(self,s);items=list(data['items'])+list(data.get('soon_next_month') or []);ref=date.fromisoformat(data['cutoff'])
        if data['future']:ref=date.fromisoformat(s.month+'-01')
        items=[i for i in items if i.get('data') and ref.isoformat()<=i['data']<=(ref+timedelta(days=7)).isoformat()]
        s.page=max(0,min(s.page,max(0,(len(items)-1)//PAGE_SIZE)))
        text=[f'<b>Sua agenda · {month_label(s.month)}</b>',f'De {ref:%d/%m} a {ref+timedelta(days=7):%d/%m} · {plural(len(items), "compromisso")}',''];rows=[]
        for i,item in enumerate(items[s.page*PAGE_SIZE:(s.page+1)*PAGE_SIZE],1):
            text += [f'<b>{i}. {safe(item["nome"],46)}</b> · {money(item["valor"])}',f'{item["data"][8:10]}/{item["data"][5:7]} · {safe(item.get("conta") or item.get("conta_pagamento"),35)}','']
            code=item.get('chave') or item.get('codigo_origem') or item.get('codigo')
            rows.append([(f'{cortar(item["nome"],22)} · {money(item["valor"])}',('detail_obligation',code,item.get('origem_mes') or s.month))])
        if not items:text+=['Nenhum vencimento registrado nesse intervalo.']
        text+=['Contas anteriores a essa janela aparecem no filtro Vencidas de A pagar.']
        if len(items)>PAGE_SIZE:rows+=[[('‹ Anteriores',('page',max(0,s.page-1))),('Próximas ›',('page',s.page+1))]]
        rows+=[[('Ver vencidas',('filter','pay','overdue')),('Configurar alertas',('view','alerts'))]]
        return Screen('\n'.join(text),rows+self.nav('agenda'))

    def screen_assistant(self,s):
        return Screen('<b>Assessor</b>\n\nEscreva sua dúvida ou escolha uma pergunta.',[
            [('Onde gastei?',('view','analytics')),('O que vence?',('view','agenda'))],
            [('Como melhorar meu mês?',('view','plan')),('Posso comprar?',('start','simulate'))],
            [('Escrever uma pergunta',('ask',)),('Diagnóstico da IA',('view','local_ai'))],
            [('🏠 Início',('view','home'))]])

    def screen_local_ai(self,s):
        return Screen('<b>Diagnóstico da interpretação local</b>\n\nO Ollama é usado automaticamente como segunda camada quando as regras não conseguem identificar uma intenção com segurança. Não é necessário ativar ou desativar nada.\n\nSe o modelo local estiver indisponível, o assessor continua funcionando pelas regras e pelos menus, sem bloquear o usuário. A IA recebe somente o texto da pergunta; não recebe o banco e não executa operações financeiras.',[
            [('Verificar Ollama',('ai_status',)),('Testar uma pergunta',('ask',))],
            [('↩ Voltar',('view','assistant')),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]])

    def screen_alerts(self,s):
        p=orient.preferencias(s.owner)
        text=f'<b>Alertas</b>\n\n{"🔔 Ligados" if p["alertas"] else "🔕 Pausados"}\nAgenda: {p["hora_manha"]}\nFechamento: {p["hora_noite"]}'
        if p['pausa_ate']>self.date_provider().isoformat():text+='\nPausa até '+data_br(p['pausa_ate'])
        text+='\nValores nos avisos: '+('incluídos' if p.get('alerta_valores') else 'não incluídos')
        text+='\n\nO bot precisa estar ligado para enviar avisos. O aviso da noite só sai quando há algo a dizer.'
        return Screen(text,[
            [('Pausar' if p['alertas'] else 'Retomar',('pref','alertas',not p['alertas'])),('⚙️ Configurar',('view','alert_settings'))],
            [('Prévia do aviso',('alert_preview',))],*self.nav('alerts')])

    def screen_alert_settings(self,s):
        p=orient.preferencias(s.owner)
        text=f'<b>Alertas do seu jeito</b>\n\nEstado: {"ligados" if p["alertas"] else "pausados"}\nAgenda: {p["hora_manha"]}\nFechamento: {p["hora_noite"]}\nSilêncio: {p["silencio_inicio"]}–{p["silencio_fim"]}'
        if p['pausa_ate']>self.date_provider().isoformat():text+='\nPausa até '+data_br(p['pausa_ate'])
        text+='\nDomingo: '+p['hora_semana']
        muted=[label for label,field in (('agenda','hora_manha'),('fechamento','hora_noite'),('domingo','hora_semana')) if orient.em_silencio(p[field],p)]
        if muted:text+='\n⚠️ Dentro do silêncio, sem envio: '+', '.join(muted)+'.'
        valores=bool(p.get('alerta_valores'))
        text+=('\n\n<b>Incluir valores nos avisos: '+('sim' if valores else 'não')+'</b>\n'
               '🔒 Notificações ficam visíveis na tela bloqueada do celular. Com "sim", o aviso mostra o total '
               'das contas vencidas ou de hoje; nomes e contas nunca aparecem.')
        text+='\n\nO aviso da manhã e o da noite só saem quando há algo a dizer. Escolha os horários ou a pausa.'
        return Screen(text,[[('Pausar alertas' if p['alertas'] else 'Retomar alertas',('pref','alertas',not p['alertas']))],
              [('Agenda 09h',('pref','hora_manha','09:00')),('Agenda 10h',('pref','hora_manha','10:00'))],
              [('Fechamento 20h',('pref','hora_noite','20:00')),('Fechamento 21h',('pref','hora_noite','21:00'))],
              [('Escolher horários',('alert_hours',))],
              [(('Valores nos avisos: sim → não' if p.get('alerta_valores') else 'Valores nos avisos: não → sim'),('pref','alerta_valores',not p.get('alerta_valores')))],
              [('Pausar até amanhã',('pref','pausa_ate',(self.date_provider()+timedelta(days=1)).isoformat())),('Retirar pausa',('pref','pausa_ate',''))],
              [('Prévia do aviso',('alert_preview',))],
              [('↩ Voltar',('view','alerts')),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]])

    def screen_recurring(self,s):
        items=orient.coletar(self,s)['recurring'];s.page=max(0,min(s.page,max(0,(len(items)-1)//PAGE_SIZE)))
        text=[f'<b>Pagamentos que se repetem · {month_label(s.month)}</b>','Padrões observados em pelo menos três meses. Confira se ainda fazem sentido.',''];rows=[]
        for item in items[s.page*PAGE_SIZE:(s.page+1)*PAGE_SIZE]:
            text += [f'<b>{safe(item["name"],50)}</b> · média {money(item["average"])}',f'{item["months"]} meses com valores semelhantes.','']
            rows.append([('Revisar lançamento recente',('transaction',item['ids'][-1]))])
        if not items:text+=['Ainda não há histórico suficiente para identificar esse padrão.']
        text+=['Padrões do histórico; confirme antes de cadastrar um fixo.']
        if len(items)>PAGE_SIZE:rows+=[[('‹ Anteriores',('page',max(0,s.page-1))),('Próximas ›',('page',s.page+1))]]
        return Screen('\n'.join(text),rows+self.nav('recurring'))

    def screen_setup(self,s):
        return Screen('<b>Uma base confiável para começar</b>\n\n1. Informe o dinheiro disponível agora em cada banco.\n2. Cadastre fixos e entradas que ainda espera.\n3. Registre o que aconteceu e confira o Histórico.\n4. Ligue os pagamentos às previsões pela Conciliação.\n\nAjustar saldo atual não cria receita nem despesa. O assessor usa essa base para calcular quanto pode sobrar no fim do mês.',[
            [('Informar saldo atual',('cash_setup_start',)),('Entender o saldo',('view','balance'))],
            [('Contas e saldos',('legacy',f'caixa por conta {s.month}'))],
            [('Novo compromisso',('guided','registrar_fixo')),('Ajuda de previsões',('topic','receber'))],
            [('➕ Primeiro registro',('view','register')),('🧭 Ver recursos',('view','feature_guide'))],
            [('🏠 Início',('view','home'))]])

    def screen_help_topic(self,s):
        data=HELP_TOPICS.get(s.topic)
        if data:
            rows=[]
            for row in data['rows']:
                built=[]
                for label,action in row:
                    if action[0]=='legacy' and '{month}' in str(action[1]):
                        action=(action[0],str(action[1]).format(month=s.month))
                    built.append((label,action))
                rows.append(built)
            parent = HELP_PARENT.get(s.topic)
            if parent:
                rows += [[('↩ Voltar',('topic',parent[0])),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]]
            else:
                rows += [[('↩ Voltar',('view','help')),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]]
            text='<b>'+data['title']+'</b>\n\n'+html.escape(data['body'])
            if s.topic in HELP_GUIDANCE:text+='\n\n🔎 <b>Como usar e conferir</b>\n'+html.escape(HELP_GUIDANCE[s.topic])
            return Screen(text,rows)
        topic=orient.TOPICS.get(s.topic,orient.TOPICS['primeiros'])
        return Screen('<b>'+safe(topic[0])+'</b>\n\n'+html.escape(topic[1]),[
            [('Abrir este recurso',('view',topic[2]))],
            [('↩ Voltar',('view','help')),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]])

    def screen_command_help(self,s):
        return Screen(
            '<b>Comandos avançados</b>\n\n'
            'Use esta área para operações específicas. Para o dia a dia, prefira a Central de ajuda.\n\n'
            'Os exemplos são modelos: <b>revise ID, valor, conta, data e competência antes de enviar</b>.',[
            [('🧾 Fixos',('legacy','/help fixos')),('💳 Parcelamentos',('legacy','/help parcelas'))],
            [('💳 Faturas',('legacy','/help faturas')),('🔁 Transferências',('legacy','/help transferencias'))],
            [('💵 Entradas previstas',('legacy','/help entradas')),('✅ Checklist',('legacy','/help checklist'))],
            [('🏦 Caixa',('legacy','/help caixa')),('🧬 Herança',('legacy','/help heranca'))],
            [('🔎 Consultas',('legacy','/help consultas')),('🧪 Auditoria',('legacy','/help auditoria'))],
            [('🎯 Planejamento',('legacy','/help planejamento')),('📥 Importação',('legacy','/help importacao'))],
            [('📤 Exportação',('topic','exportar')),('💾 Backup',('legacy','/help backup'))],
            [('✏️ Correções',('legacy','/help corrigir')),('🗑 Exclusões',('legacy','/help excluir'))],
            [('🔐 Segurança',('topic','privacidade')),('🎓 Aulas',('legacy','aprender'))],
            [('↩ Voltar',('view','help')),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]])


    def advanced_help(self,key,topic,raw):
        s=self.session(key);s.help_title=topic;s.help_page=0;s.help_pages=[];part=''
        for char in str(raw):
            if len(html.escape(part+char).encode('utf-16-le'))//2>2600:s.help_pages.append(part);part=''
            part+=char
        if part:s.help_pages.append(part)
        s.trail=(s.trail+[(s.view,s.month,s.page)])[-12:]
        return self.render(key,'advanced_help')

    def screen_advanced_help(self,s):
        if not s.help_pages:return self.screen_command_help(s)
        text=f'<b>Guia · {safe(s.help_title or "comando")}</b> · {s.help_page+1}/{len(s.help_pages)}\n\n'+html.escape(s.help_pages[s.help_page])
        rows=[]
        if len(s.help_pages)>1:
            nav=[]
            if s.help_page>0:nav.append(('‹ Anterior',('help_page',s.help_page-1)))
            if s.help_page<len(s.help_pages)-1:nav.append(('Próxima ›',('help_page',s.help_page+1)))
            if nav:rows.append(nav)
        topic=norm(s.help_title)
        quick={
            'fixos': [('Abrir A pagar',('view','pay')),('Cadastrar conta fixa',('guided','registrar_fixo'))],
            'parcelas': [('➕ Registrar despesa',('view','register')),('Abrir A pagar',('view','pay'))],
            'entradas': [('💵 A receber',('view','receivables')),('+ Registrar entrada',('start','receita'))],
            'consultas': [('📊 Análises',('view','analytics')),('🔎 Histórico',('view','history'))],
            'caixa': [('💰 Entender saldo',('view','balance')),('🏠 Resumo',('view','home'))],
            'heranca': [('💰 Entender saldo',('view','balance')),('🧾 A pagar',('view','pay'))],
            'importacao': [('🏠 Início',('view','home'))],
            'corrigir': [('🔎 Histórico',('view','history')),('🔗 Conciliações',('view','reconciliations'))],
            'excluir': [('🔎 Histórico',('view','history'))],
            'backup': [('⚙️ Mais',('view','more'))],
        }.get(topic)
        if quick:rows.append(quick)
        rows += [[('⌨️ Todos os comandos',('view','command_help')),('↩ Voltar',('view','help'))],
                 [('🏠 Início',('view','home'))]]
        return Screen(text,rows)

    def screen_transaction(self,s):
        raw=db.buscar_transacao_por_id(s.selected_id)
        if not raw:return Screen('Esse lançamento não está mais disponível.',[[('Histórico',('view','history'))]])
        t=dict(raw);links=[v for v in conc.listar_vinculos() if v['transacao_id']==t['id']]
        text=['<b>Lançamento</b>',safe(t['descricao'],160),'',f'💰 Valor: <b>{money(t["valor"])}</b> · {safe(t["tipo"])}',
              f'📅 Data: {t["data"][8:10]}/{t["data"][5:7]}/{t["data"][:4]}',f'💸 Forma: {safe(t["forma_pagamento"])}',
              f'🏦 Conta: {safe(t["conta"])}', f'🏷 Categoria: {safe(t["categoria"])}','',
              'Ligado a uma previsão. Alterações financeiras exigem desvincular antes.' if links else 'Sem vínculo com previsão. Vincule somente se este movimento realiza uma obrigação.']
        if eh_credito(t):
            text += ['Data da compra: '+date.fromisoformat(data_real_compra(t)).strftime('%d/%m/%Y'),
                     'Fatura: '+month_label(competencia_transacao(t))]
            if int(t.get('parcelas_total') or 1)>1:
                text.append(f'Parcela {t.get("parcela_atual") or 1}/{t["parcelas_total"]}')
        text += ['', f'<i>Código para comandos de texto: #{t["id"]}</i>']
        copy_line=(f'#{t["id"]} | {t["data"]} | {t["tipo"]} | {money(t["valor"])} | '
                   f'{t.get("descricao") or ""} | {t.get("conta") or ""} | '
                   f'{t.get("categoria") or ""} | {t.get("forma_pagamento") or ""}')
        unico=int(t.get('parcelas_total') or 1)==1
        barra=[]
        evento=evento_registro_recente(t['id'],s.owner)
        if evento:barra.append(('↩ Desfazer',('undo_preview',evento)))
        if unico and not links:barra.append(('🏷 Categoria',('cat_menu',t['id'])))
        barra.append(('🔁 Repetir',('repeat',t['id'])))
        return Screen('\n'.join(text),[barra,[('📋 Copiar referência',('copy_text',copy_text_value(copy_line)))],
            [('Ver conciliação',('view','reconciliations'))] if links else ([('Entender parcelas e fatura',('topic','faturas'))] if int(t.get('parcelas_total') or 1)>1 else [('Vincular a previsão',('link_existing',t['id']))]),
            [('Corrigir valor',('guided',f'corrigir_valor:{t["id"]}')),('📅 Corrigir data',('date_menu',t['id']))],
            # 'legacy_raw': "lançamento N" é comando do legado, nunca uma despesa de R$ N.
            [('Outros ajustes',('legacy_raw',f'lançamento {t["id"]}')),('Entender correções',('topic','corrigir'))]])

    def screen_obligation(self,s):
        code,month=s.selected_obligation
        _,item=svc.resolver_item_checklist(month,code)
        if not item:return Screen('Esse compromisso não está mais disponível.',[[('A pagar',('view','pay'))]])
        status=svc.aplicar_status_checklist(month,[item])[0].get('status')
        future=month>self.date_provider().strftime('%Y-%m')
        text=[f'<b>🧾 {safe(item["nome"],80)}</b>',f'💰 Valor: <b>{money(item["valor"])}</b>',
              f'📅 Competência: {month_label(month)}',
              '🏦 Conta: '+safe(item.get('conta') or item.get('conta_pagamento'),50),'⏰ '+self.due_label(item),'']
        rows=[]
        if status=='revisar':
            text += ['Este item já foi marcado como pago. Falta conferir ou vincular o movimento correspondente; ele não deve ser pago novamente.']
            rows.append([('Buscar baixa no Histórico',('view','history')),('Abrir revisões',('filter','pay','review'))])
        elif status=='pago':
            text += ['Este item já consta como pago. Use Histórico ou Conciliações se precisar conferir a baixa.']
            rows.append([('Abrir Histórico',('view','history')),('Conciliações',('view','reconciliations'))])
        elif future:
            text += ['Esta é uma projeção futura. O assessor não registra pagamento antecipado por este detalhe; volte quando a competência chegar ou ajuste o compromisso pela memória completa.']
            rows.append([('Memória completa',('legacy',f'detalhar {code} {month}'))])
        else:
            if item.get('grupo')=='bancos':
                text += ['Registre aqui o pagamento da fatura somente quando ele realmente tiver saído de uma conta. O assessor mostrará uma prévia e revalidará o saldo antes de salvar.', 'Se a saída já estiver no Histórico, confira esse lançamento antes de registrar outro pagamento para evitar dupla saída.']
                rows.append([('Registrar pagamento',('invoice_begin',item['chave'],month))])
                rows.append([('Procurar no Histórico',('view','history')),('Memória completa',('legacy',f'detalhar {code} {month}'))])
            elif svc.item_checklist_eh_credito_individual(item):
                text += ['Esta cobrança usa crédito e pertence à fatura do cartão. Não existe baixa individual de caixa para ela.',
                         'Pagar este item separadamente criaria uma segunda despesa. Use a fatura correspondente em A pagar.']
                rows.append([('🧾 Voltar a A pagar',('view','pay')),('Procurar no Histórico',('view','history'))])
                rows.append([('Memória completa',('legacy',f'detalhar {code} {month}'))])
            else:
                text += ['Se já foi registrado no Histórico, vincule o lançamento existente. Se ainda não foi registrado, confira a prévia do pagamento.']
                if item.get('origem')=='compromisso':rows.append([('Registrar pagamento',('settle',int(item['id']),month))])
                rows.append([('Procurar no Histórico',('view','history')),('Memória completa',('legacy',f'detalhar {code} {month}'))])
        rows += [[('Entender faturas',('topic','faturas'))]]
        if item.get('grupo')=='bancos':rows.insert(0,[('🔎 De onde veio esta fatura?',('invoice_origin',code,month,0))])
        if s.privacy:
            text=[mask_money(line) for line in text]
        screen=Screen('\n'.join(text),rows)
        from telegram_recursos import rich_summary
        screen.rich_html=rich_summary(str(item['nome']), '\n'.join(text[1:5]),'\n'.join(text[5:]))
        return screen

    def screen_accounts(self,s):
        names=self.accounts()
        total_pages=max(1,(len(names)+PAGE_SIZE-1)//PAGE_SIZE)
        s.page=max(0,min(s.page,total_pages-1))
        start=s.page*PAGE_SIZE
        visible=names[start:start+PAGE_SIZE]
        rows=[[(safe(n,30),('account_filter',n))] for n in visible]
        if total_pages>1:
            nav=[]
            if s.page>0: nav.append(('‹ Anteriores',('account_page',s.page-1)))
            nav.append((f'{s.page+1}/{total_pages}',('account_page',s.page)))
            if s.page+1<total_pages: nav.append(('Próximas ›',('account_page',s.page+1)))
            rows.append(nav)
        text='<b>Filtrar por conta</b>\n\nEscolha uma conta.'
        voltar=s.filter_view if s.filter_view in {'pay','history'} else 'history'
        return Screen(text,[[('Todas as contas',('account_filter',''))]]+rows+[[('Digitar outra conta',('account_search',))],
                            [('↩ Voltar',('view',voltar)),('🏠 Início',('view','home'))]])

    def screen_question(self,s):
        return Screen('<b>Escreva sua pergunta</b>\n\nExemplo: “O que falta pagar?” ou “Onde gastei mais?”. Se houver ambiguidade, vou pedir que escolha um caminho.\n\nPara registrar dinheiro, use Registrar e confira a prévia.',[[('Cancelar',('cancel',)),('Perguntas prontas',('view','assistant'))]])

    def _month_from_text(self, text):
        t = norm(text)
        from consultas_rapidas import MESES as names  # tabela única de meses por extenso
        today = self.date_provider()
        # Pergunta sobre o que ainda vai ser pago/recebido: mês sem ano é a
        # PRÓXIMA ocorrência ("quanto vou pagar em janeiro", em novembro, é
        # janeiro do ano seguinte). Consultas sobre o passado ("quanto gastei
        # em janeiro") continuam no ano corrente.
        futuro = re.search(r'\b(?:vou|vai|vamos|irei|quanto)\s+(?:pagar|receber)\b|\ba\s+(?:pagar|receber)\b'
                           r'|\bvenc(?:e|em|er|imento)\b|\bprevist[oa]s?\b', t)
        if re.search(r'\b(?:mes\s+que\s+vem|proximo\s+mes|mes\s+seguinte)\b', t):
            return month_shift(today.strftime('%Y-%m'), 1)
        for name, number in names.items():
            if re.search(rf'\b{name}\b', t):
                m = re.search(rf'\b{name}\b(?:\s+de)?\s+(20\d{{2}})\b', t)
                year = int(m.group(1)) if m else today.year
                if not m and futuro and number < today.month:
                    year += 1
                return f'{year:04d}-{number:02d}'
        m = re.search(r'\b(20\d{2})[-/](0?[1-9]|1[0-2])\b', t)
        if m:
            return f'{int(m.group(1)):04d}-{int(m.group(2)):02d}'
        return None

    def _ai_months(self,s,period):
        current=self.date_provider().strftime('%Y-%m')
        if period=='previous_month':return [month_shift(current,-1)]
        if period=='current_month':return [current]
        if period=='current_year':
            year=current[:4];last=int(current[5:])
            return [f'{year}-{m:02d}' for m in range(1,last+1)]
        return [s.month]

    def _account_in_text(self, text):
        clean = norm(text)
        matches = []
        for account in self.accounts(incluir_inativas=True):
            n = norm(account)
            if n and re.search(r'(?<!\w)' + re.escape(n) + r'(?!\w)', clean):
                matches.append((len(n), account))
        return max(matches)[1] if matches else None

    @_private_key_screen
    def _cash_accounts_screen(self,key,month=None,page=None):
        s=self.session(key)
        month=month or s.month
        if month!=s.month:
            s.cash_page=0
        s.month=month
        caixa=svc.calcular_caixa_por_conta_mes(month)
        contas=caixa.get('contas') or {}
        names=list(contas.keys())
        per_page=5
        pages=max(1,(len(names)+per_page-1)//per_page)
        if page is not None:s.cash_page=int(page)
        s.cash_page=max(0,min(s.cash_page,pages-1))
        visible_names=names[s.cash_page*per_page:(s.cash_page+1)*per_page]
        lines=[heading('Saldos por conta',month_label(month)),'']
        # O total soma só bancos reais; lançamentos sem banco (ex.: conta "Pix")
        # ficam fora dele, mas entram no Meu mês. Explicitamos a diferença.
        unassigned=caixa.get('sem_conta') or {}
        unassigned_in=float(unassigned.get('entradas') or 0)
        unassigned_out=float(unassigned.get('saidas') or 0)
        unassigned_note=''
        if abs(unassigned_in)>.005 or abs(unassigned_out)>.005:
            unassigned_note=(f'⚠️ Fora do total, sem banco definido: entradas {money(unassigned_in)} · saídas {money(unassigned_out)}. '
                             f'Considerando-os: <b>{money(float(caixa.get("total_disponivel") or 0)+unassigned_in-unassigned_out)}</b>')
        if not contas:
            lines += ['Nenhuma conta com saldo ainda.','Informe uma vez o valor que aparece no aplicativo de cada banco; depois o assessor acompanha as entradas e saídas.']
        else:
            if pages>1:
                lines += [f'Página {s.cash_page+1}/{pages} · mostrando {len(visible_names)} de {len(names)} contas.','']
            for account in visible_names:
                item=contas[account]
                lines += [f'🏦 <b>{safe(account,50)}</b>\nDisponível: <b>{money(item.get("disponivel") or 0)}</b>', '']
            lines += [f'💰 <b>Total disponível: {money(caixa.get("total_disponivel") or 0)}</b>']
            if unassigned_note:
                lines += [unassigned_note]
            try:
                consolidated = float(resumir_saldo(svc.obter_metricas_resultado_mes(month))['saldo_atual'] or 0)
            except Exception:
                _LOG_UX.warning('Saldos por conta: saldo consolidado indisponível.', exc_info=True)
                consolidated = None
            if consolidated is not None and abs(consolidated - float(caixa.get('total_disponivel') or 0)) > .005:
                unassigned_note = (unassigned_note + '<br>' if unassigned_note else '') + (
                    f'<i>O Saldo do Início mostra {money(consolidated)}: ele também conta movimentos sem banco '
                    'definido e ajustes de conciliação.</i>')
                lines += [unassigned_note.split('<br>')[-1]]
            lines += ['', '💡 Toque no banco para conferir os movimentos. Ajustar saldos atuais usa o dinheiro que aparece agora no aplicativo.']
        prev_month=month_shift(month,-1);next_month=month_shift(month,1)
        rows=[]
        rows += [[(name,('cash_account_detail',name,month)) for name in visible_names[i:i+2]] for i in range(0,len(visible_names),2)]
        if pages>1:
            nav=[]
            if s.cash_page>0:nav.append(('‹ Contas',('cash_accounts',month,s.cash_page-1)))
            nav.append((f'{s.cash_page+1}/{pages}',('cash_accounts',month,s.cash_page)))
            if s.cash_page+1<pages:nav.append(('Mais contas ›',('cash_accounts',month,s.cash_page+1)))
            rows.append(nav)
        rows += [[('‹ Mês anterior',('cash_accounts',prev_month,0)),('Próximo mês ›',('cash_accounts',next_month,0))],
                 [('✏️ Ajustar saldos atuais',('cash_setup_start',)),('➕ Outra conta',('cash_setup_new_account',))],
                 [('🏠 Início',('view','home')),('☰ Menu',('view','more'))]]
        screen = Screen('\n'.join(lines), rows, sensitive=True)
        if contas:
            account_rows = [
                (account, money(contas[account].get('disponivel') or 0))
                for account in visible_names
            ]
            screen.rich_html = (
                '<h2>Saldos por conta</h2><p><i>'+month_label(month)+'</i></p>'
                + rich_table(('Conta', 'Disponível'), account_rows,
                             ('Total disponível', money(caixa.get('total_disponivel') or 0)))
                + ('<p>'+unassigned_note+'</p>' if unassigned_note else '')
                + '<details><summary>Como conferir</summary><p>'
                  'Toque no banco para conferir os movimentos. Use <b>Ajustar saldos atuais</b> com o valor '
                  'que aparece agora no aplicativo de cada banco.'
                  '</p></details>'
            )
        else:
            screen.rich_html = (
                '<h2>Saldos por conta</h2><p><i>'+month_label(month)+'</i></p>'
                + rich_table(('Conta', 'Disponível'), [('Nenhuma conta configurada', money(0))],
                             ('Total disponível', money(0)))
            )
        return screen

    @_private_key_screen
    def _cash_account_detail_screen(self,key,account,month):
        s=self.session(key);s.month=month
        caixa=svc.calcular_caixa_por_conta_mes(month);item=(caixa.get('contas') or {}).get(account)
        if not item:
            return Screen(f'<b>{safe(account)} · {month_label(month)}</b>\n\nSem saldo ou movimentos nesta conta neste mês. Informe o saldo que aparece no banco para começar.',[[('✏️ Ajustar saldo',('cash_setup_account',account))],[('↩ Voltar',('cash_accounts',month)),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]])
        block=(f'{account.upper()} · {month_label(month).upper()}\n\n'
               f'Base do mês .......... {money(item.get("inicial") or 0)}\n'
               f'Entradas ............. {money(item.get("entradas") or 0)}\n'
               f'Saídas realizadas .... {money(item.get("saidas") or 0)}\n'
               f'────────────────────────────\n'
               f'SALDO ATUAL .......... {money(item.get("disponivel") or 0)}')
        prev_month=month_shift(month,-1);next_month=month_shift(month,1)
        rows=[[('📋 Copiar resumo',('copy_text',copy_text_value(block)))],
              [('‹ Mês anterior',('cash_account_detail',account,prev_month)),('Próximo mês ›',('cash_account_detail',account,next_month))],
              [('📒 Ver movimentos',('account_history',account,month)),('✏️ Ajustar saldo',('cash_setup_account',account))],
              [('↩ Voltar',('cash_accounts',month)),('🏠 Início',('view','home')),('☰ Menu',('view','more'))]]
        screen = Screen(report_html(block), rows, sensitive=True)
        screen.rich_html = (
            '<h2>'+safe(account, 50)+'</h2><p><i>'+month_label(month)+'</i></p>'
            + rich_table(('Movimento', 'Valor'), [
                ('Base do mês', money(item.get('inicial') or 0)),
                ('Entradas', money(item.get('entradas') or 0)),
                ('Saídas realizadas', money(item.get('saidas') or 0)),
            ], ('Saldo atual', money(item.get('disponivel') or 0)))
        )
        return screen

    def _cash_setup_accounts(self):
        return sug.ordenar_contas(sorted({svc.normalizar_conta_caixa(account) for account in self.accounts()
                                          if not svc.conta_virtual_caixa(account) and norm(account)!='boleto'},key=norm))

    @_private_key_screen
    def _cash_setup_start(self,key,page=0):
        """Seletor de conta: todas com o saldo calculado hoje; o titular toca na que quer ajustar,
        digita o saldo que vê no banco e confirma. O ajuste de todas em sequência segue disponível."""
        s=self.session(key);month=self.date_provider().strftime('%Y-%m');s.month=month
        accounts=self._cash_setup_accounts()
        if not accounts:return self.act(key,('cash_setup_new_account',))
        s.stage=None;s.settings_draft=None
        caixa=svc.calcular_caixa_por_conta_mes(month).get('contas') or {}
        per_page=8;pages=max(1,(len(accounts)+per_page-1)//per_page)
        page=max(0,min(int(page or 0),pages-1))
        visible=accounts[page*per_page:(page+1)*per_page]
        rows=[[(f'{name} · {money((caixa.get(name) or {}).get("disponivel",0))}',('cash_setup_account',name))
               for name in visible[i:i+2]] for i in range(0,len(visible),2)]
        if pages>1:
            nav=[]
            if page>0:nav.append(('‹ Contas',('cash_setup_pick',page-1)))
            nav.append((f'{page+1}/{pages}',('cash_setup_pick',page)))
            if page+1<pages:nav.append(('Mais contas ›',('cash_setup_pick',page+1)))
            rows.append(nav)
        rows+=[[('➕ Outra conta',('cash_setup_new_account',)),('📋 Todas em sequência',('cash_setup_all',))],
               [('🏦 Saldos por conta',('cash_accounts',month)),('🏠 Início',('view','home'))]]
        texto=(heading('Ajustar saldo',month_label(month))+'\n\nToque na conta que quer ajustar. '
               'O valor ao lado é o saldo que o assessor calcula hoje; depois você informa o que vê no banco e confirma.')
        return Screen(texto,rows,sensitive=True)

    def _cash_setup_all(self,key):
        s=self.session(key);month=self.date_provider().strftime('%Y-%m');s.month=month
        accounts=self._cash_setup_accounts()
        if not accounts:return self.act(key,('cash_setup_new_account',))
        s.settings_draft={'month':month,'accounts':accounts,'index':0,'changes':[]};s.stage='cash_setup_value'
        return self._cash_setup_prompt(s)

    def _cash_setup_account(self,key,account):
        s=self.session(key);month=self.date_provider().strftime('%Y-%m');s.month=month
        account=svc.normalizar_conta_caixa(account)
        s.settings_draft={'month':month,'accounts':[account],'index':0,'changes':[]};s.stage='cash_setup_value'
        return self._cash_setup_prompt(s)

    def _cash_setup_prompt(self,s):
        cfg=s.settings_draft;account=cfg['accounts'][cfg['index']];month=cfg['month']
        caixa=svc.calcular_caixa_por_conta_mes(month);current=((caixa.get('contas') or {}).get(account) or {}).get('disponivel',0)
        return Screen(f'<b>{("Ajustar saldo · "+safe(account)) if len(cfg["accounts"])==1 else "Ajustar saldos atuais · "+str(cfg["index"]+1)+"/"+str(len(cfg["accounts"]))}</b>\n\nConta: <b>{safe(account)}</b>\nSaldo calculado hoje: <b>{money(current)}</b>\n\nDigite o saldo que você vê <b>agora</b> no aplicativo do banco.\nIsso não cria receita nem despesa.',([[('Pular esta conta',('cash_setup_skip',)),('Cancelar',('cancel',))]] if len(cfg['accounts'])>1 else [[('↩ Outras contas',('cash_setup_start',)),('Cancelar',('cancel',))]]))

    def _cash_setup_advance(self,key,skip=False):
        s=self.session(key);cfg=s.settings_draft
        if not cfg:raise ValueError('O ajuste de saldos expirou.')
        cfg['index']+=1;s.stage='cash_setup_value'
        if cfg['index']>=len(cfg['accounts']):
            s.stage=None
            primeiro=self._sem_lancamentos()
            return Screen(f'<b>Ajuste de saldos concluído.</b>\n\n{plural(len(cfg["changes"]), "conta atualizada", "contas atualizadas")}. A partir de agora, entradas e saídas registradas em cada banco administram esses saldos.'
                          +('\n\n<b>Próximo passo:</b> registre seu primeiro gasto ou entrada. Depois, o Início mostra o mês completo.' if primeiro else ''),
                          ([[('➕ Primeiro registro',('view','register'))]] if primeiro else [])
                          +[[('✏️ Ajustar outra conta',('cash_setup_start',))],[('🏦 Ver saldos por conta',('cash_accounts',cfg['month'])),('🏠 Início',('view','home'))]])
        return self._cash_setup_prompt(s)

    def _cash_setup_commit(self,key):
        s=self.session(key);cfg=s.settings_draft
        if s.stage!='cash_setup_confirm' or not cfg or 'pending_value' not in cfg:raise ValueError('Essa confirmação expirou.')
        month=cfg['month'];account=cfg['accounts'][cfg['index']];desired=float(cfg['pending_value'])
        if month!=self.date_provider().strftime('%Y-%m'):
            raise ValueError('O mês mudou desde a prévia. Abra Ajustar saldo atual novamente.')
        from saldos_edicao import confirmar
        base=confirmar(month,account,desired,cfg.get('expected_cash'),key)
        # Só consumir a confirmação depois do commit. Falhas mantêm a prévia.
        cfg.pop('pending_value',None);cfg.pop('expected_cash',None)
        cfg['changes'].append({'account':account,'desired':desired,'base':base});s.stage='cash_setup_value'
        return self._cash_setup_advance(key)

    @_private_key_screen
    def _balance_account_screen(self, key, account, month=None):
        """Saldo/caixa de uma conta específica, sem misturar com o consolidado."""
        s=self.session(key)
        month=month or self.date_provider().strftime('%Y-%m')
        s.month=month
        caixa=svc.calcular_caixa_por_conta_mes(month)
        normalized=svc.normalizar_conta_caixa(account)
        item=caixa.get('contas',{}).get(normalized,{})
        title=safe(normalized,50)
        available=float(item.get('disponivel') or 0)
        lines=[f'<b>Caixa {title} · {month_label(month)}</b>','',
               f'🏦 Dinheiro disponível neste banco: <b>{money(available)}</b>']
        adjustment=float(item.get('ajuste_conciliacao_heranca') or 0)
        if abs(adjustment)>.005:
            lines += [f'🔗 Ajuste da herança conciliada: {money(adjustment)}']
        if svc.conta_centraliza_fluxo_mensal(normalized):
            m=svc.obter_metricas_resultado_mes(month)
            lines += ['',f'🔮 Projeção consolidada de todas as contas: <b>{money(m.get("saldo_projetado") or 0)}</b>',
                      '<i>A projeção consolidada considera dinheiro e compromissos de todo o assessor.</i>']
        sem=caixa.get('sem_conta') or {}
        if sem.get('entradas') or sem.get('saidas'):
            lines += ['', '⚠️ Há movimentos sem banco definido. Confira e corrija no Histórico para distribuir o caixa corretamente.']
        prev_month=month_shift(month,-1);next_month=month_shift(month,1)
        rows=[[('‹ Mês anterior',('balance_account',account,prev_month)),('Próximo mês ›',('balance_account',account,next_month))],
              [('Ver composição',('cash_account_detail',normalized,month)),('✏️ Ajustar saldo',('cash_setup_account',normalized))],
              [('📒 Ver movimentos',('account_history',normalized,month)),('Todas as contas',('cash_accounts',month))],
              [('🏠 Início',('view','home')),('☰ Menu',('view','more'))]]
        screen = Screen('\n'.join(lines), rows, sensitive=True)
        account_rows = [('Dinheiro disponível neste banco', money(available))]
        if abs(adjustment) > .005:
            account_rows.append(('Ajuste da herança conciliada', money(adjustment)))
        if svc.conta_centraliza_fluxo_mensal(normalized):
            account_rows.append(('Projeção consolidada', money(m.get('saldo_projetado') or 0)))
        screen.rich_html = (
            '<h2>Caixa '+title+'</h2><p><i>'+month_label(month)+'</i></p>'
            + rich_table(('Indicador', 'Valor'), account_rows)
            + '<details><summary>Como interpretar</summary><p>'
              'O valor disponível pertence somente a este banco. A projeção consolidada, quando exibida, '
              'considera todas as contas e compromissos do assessor.'
              '</p></details>'
        )
        return screen

    def _pay_month_open_items(self, month):
        """Itens realmente abertos da competência, sem misturar baixas antigas em revisão."""
        items = svc.aplicar_status_checklist(month, svc.montar_itens_checklist_mes(month, modo='geral'))
        return [dict(i, origem_mes=month) for i in items
                if i.get('status') not in {'pago', 'revisar'} and float(i.get('valor') or 0) > .005]

    def _pay_summary_rich_body(self, resumo, guidance=False):
        """Representa um resumo canônico sem misturar total e composição da fatura."""
        payable = []
        if resumo.get('possui_fatura'):
            payable.append(('Fatura/cartão', money(resumo.get('fatura'))))
        for key_name, label in (
            ('fixos', 'Fixos'),
            ('emprestimos', 'Empréstimos'),
            ('compromissos', 'Compromissos'),
        ):
            if float(resumo.get(key_name) or 0) > .005:
                payable.append((label, money(resumo.get(key_name))))

        result = rich_table(
            ('Componente', 'Valor'), payable or [('Nenhuma obrigação em aberto', money(0))],
            ('Total a pagar', money(resumo.get('total'))),
        )
        invoice = []
        for key_name, label in (
            ('fatura_bruta', 'Compras/cobranças do mês'),
            ('credito_herdado', 'Crédito anterior aplicado'),
            ('ajuste_conferencia', 'Ajuste de conferência'),
            ('credito_disponivel', 'Crédito disponível'),
        ):
            if float(resumo.get(key_name) or 0) > .005:
                invoice.append((label, money(resumo.get(key_name))))

        if invoice or guidance:
            details = rich_table(('Composição da fatura', 'Valor'), invoice) if invoice else ''
            if guidance:
                details += (
                    '<p>Compras e cobranças exibidas na composição já estão dentro da fatura; '
                    'elas não são somadas novamente ao total.<br><br>'
                    'Use <b>Ver detalhes</b> para auditar a composição ou <b>A pagar filtrado</b> '
                    'para listar as pendências desta conta.</p>'
                )
            result += '<details><summary>Entenda este total</summary>'+details+'</details>'
        return result

    @_private_key_screen
    def _pay_month_screen(self, key, month=None, expanded_account=None, page=None):
        """Resumo mensal paginado por conta, com total global e expansão sob demanda."""
        s = self.session(key)
        month = month or s.month
        if month != s.month:
            s.pay_month_page = 0
        s.month = month
        current = self._pay_month_open_items(month)
        by_account = defaultdict(float)
        for item in current:
            account = (item.get('conta') or '').strip() or 'Sem conta'
            by_account[account] += float(item.get('valor') or 0)

        # Uma conta pode ter compras reais na competência e, ainda assim, não
        # possuir valor líquido a pagar porque um crédito anterior cobriu tudo.
        # Ela continua visível para que o lançamento não pareça ter desaparecido.
        accounts_by_key = {norm(account): account for account in by_account}
        for item in comp.obter_itens_base_pagamentos_mes(month, incluir_transacoes=True):
            if not isinstance(item, dict) or not comp.item_eh_fatura_cartao(item):
                continue
            activity_account = str(item.get('conta_pagamento') or '').strip()
            if not activity_account:
                continue
            display_account = accounts_by_key.get(norm(activity_account), activity_account)
            by_account.setdefault(display_account, 0.0)
            accounts_by_key.setdefault(norm(activity_account), display_account)
        ordered = sorted(by_account.items(), key=lambda kv: (-kv[1], norm(kv[0])))
        total = sum(v for _, v in ordered)

        per_page = 6
        pages = max(1, (len(ordered) + per_page - 1) // per_page)
        if page is not None:
            s.pay_month_page = max(0, min(int(page), pages - 1))
        else:
            s.pay_month_page = max(0, min(s.pay_month_page, pages - 1))
        start = s.pay_month_page * per_page
        visible = ordered[start:start + per_page]
        if expanded_account and expanded_account not in {a for a, _ in visible}:
            expanded_account = None

        expanded_summary = None
        code = [f'QUANTO VOU PAGAR · {month_label(month).upper()}', '']
        if ordered:
            code += [f'PÁGINA {s.pay_month_page + 1}/{pages} · mostrando {len(visible)} de {plural(len(ordered), "conta")}', '']
            for account, value in visible:
                prefix = '▼' if expanded_account == account else '▶'
                code.append(f'{prefix} {account} · {money(value)}')
                if expanded_account == account and account != 'Sem conta':
                    resumo = comp.calcular_resumo_pagamento_conta(month, account)
                    expanded_summary = resumo
                    if resumo.get('possui_fatura'):
                        code.append(f'   💳 Fatura/cartão · {money(resumo.get("fatura"))}')
                    if float(resumo.get('fatura_bruta') or 0) > .005:
                        code.append(f'   🛒 Compras/cobranças · {money(resumo.get("fatura_bruta"))}')
                    if float(resumo.get('credito_herdado') or 0) > .005:
                        code.append(f'   ↩ Crédito anterior · {money(resumo.get("credito_herdado"))}')
                    if float(resumo.get('credito_disponivel') or 0) > .005:
                        code.append(f'   ✅ Crédito restante · {money(resumo.get("credito_disponivel"))}')
                    if float(resumo.get('fixos') or 0) > .005:
                        code.append(f'   🔁 Fixos · {money(resumo.get("fixos"))}')
                    if float(resumo.get('emprestimos') or 0) > .005:
                        code.append(f'   🤝 Empréstimos · {money(resumo.get("emprestimos"))}')
                    if float(resumo.get('compromissos') or 0) > .005:
                        code.append(f'   📝 Compromissos · {money(resumo.get("compromissos"))}')
                code.append('')
        else:
            code += ['Nenhuma obrigação em aberto nesta competência.', '']
        code += ['────────────────────────', f'TOTAL A PAGAR · TODAS AS CONTAS · {money(total)}']
        scope = self._pay_month_scope_lines(month, total)
        code += ['', *scope]

        rows = []
        bank_buttons = []
        for account, _ in visible:
            if account == 'Sem conta':
                continue
            if expanded_account == account:
                bank_buttons.append((f'▲ {account}', ('pay_month', month, s.pay_month_page)))
            else:
                bank_buttons.append((f'▶ {account}', ('pay_month_expand', account, month, s.pay_month_page)))
        for i in range(0, len(bank_buttons), 2):
            rows.append(bank_buttons[i:i + 2])
        if expanded_account and expanded_account != 'Sem conta':
            rows.append([(f'🔎 Ver lançamentos · {expanded_account}', ('pay_month_account_detail', expanded_account, month))])
        if pages > 1:
            nav = []
            if s.pay_month_page > 0:
                nav.append(('‹ Contas', ('pay_month_page', month, s.pay_month_page - 1)))
            nav.append((f'{s.pay_month_page + 1}/{pages}', ('pay_month_page', month, s.pay_month_page)))
            if s.pay_month_page + 1 < pages:
                nav.append(('Mais contas ›', ('pay_month_page', month, s.pay_month_page + 1)))
            rows.append(nav)

        prev_month = month_shift(month, -1)
        next_month = month_shift(month, 1)
        rows += [[('‹ Mês anterior', ('pay_month', prev_month, 0)), ('Próximo mês ›', ('pay_month', next_month, 0))],
                 [('🧾 A pagar', ('view','pay')), ('🏠 Início', ('view','home')), ('☰ Menu', ('view','more'))]]
        screen=Screen(report_html('\n'.join(code)), rows,sensitive=True)
        if visible:
            screen.rich_html=(
                '<h2>Quanto vou pagar</h2><p><i>'+month_label(month)+'</i></p>'
                + rich_table(('Conta', 'Valor'),
                             [(account, money(value)) for account, value in visible],
                             ('Total a pagar · todas as contas', money(total)))
            )
        else:
            screen.rich_html=(
                '<h2>Quanto vou pagar</h2><p><i>'+month_label(month)+'</i></p>'
                + rich_table(('Conta', 'Valor'),
                             [('Nenhuma obrigação em aberto', money(0))],
                             ('Total a pagar · todas as contas', money(total)))
            )
        screen.rich_html += ''.join('<p><i>' + html.escape(line) + '</i></p>' for line in scope)
        if expanded_account and expanded_summary:
            screen.rich_html += (
                '<p><b>Detalhamento · '+safe(expanded_account, 50)+'</b></p>'
                + self._pay_summary_rich_body(expanded_summary)
            )
        return screen

    def _pay_month_scope_lines(self, month, total):
        """O que o total de Quanto vou pagar inclui e por que difere de A pagar (texto puro)."""
        lines = [f'Só contas de {month_label(month)}, por conta. Fixos no crédito já estão dentro da fatura.']
        try:
            items = self.obligations(month)
        except Exception:
            _LOG_UX.warning('Quanto vou pagar: total de A pagar indisponível.', exc_info=True)
            return lines
        old = [i for i in items if (i.get('origem_mes') or month) != month]
        all_total = sum(float(i.get('valor') or 0) for i in items)
        if old:
            lines.append(f'Não inclui {plural(len(old), "conta")} de meses anteriores ({money(sum(float(i["valor"]) for i in old))}). '
                         f'A pagar soma tudo: {money(all_total)}.')
        elif abs(all_total - total) > .005:
            lines.append(f'A pagar mostra {money(all_total)}: lista cada conta e fatura em aberto.')
        return lines

    @_private_key_screen
    def _pay_month_account_detail(self, key, account, month):
        """Detalhamento técnico da conta, retornando ao mesmo ponto do resumo mensal."""
        s = self.session(key)
        s.month = month
        raw = comp.detalhar_pagamento_por_conta(month, account)
        prev_month = month_shift(month, -1)
        next_month = month_shift(month, 1)
        rows = [[('‹ Mês anterior', ('pay_month_account_detail', account, prev_month)),
                 ('Próximo mês ›', ('pay_month_account_detail', account, next_month))],
                [('Resumo da conta', ('pay_account', account, month))],
                [('↩ Voltar', ('pay_month_expand', account, month, s.pay_month_page)), ('🏠 Início', ('view','home')), ('☰ Menu', ('view','more'))]]
        # O detalhamento vem do núcleo com códigos internos (#C2, #1); o titular vê só os nomes.
        return Screen(report_html(re.sub(r'#C?\d+ · ', '', raw)), rows)

    @_private_key_screen
    def _pay_account_screen(self, key, account, month=None, detailed=False):
        s = self.session(key)
        month = month or s.month
        s.month = month
        if detailed:
            raw = comp.detalhar_pagamento_por_conta(month, account)
            prev_month = month_shift(month, -1)
            next_month = month_shift(month, 1)
            rows = [[('‹ Mês anterior', ('pay_account_detail', account, prev_month)),
                     ('Próximo mês ›', ('pay_account_detail', account, next_month))],
                    [('Resumo da conta', ('pay_account', account, month)),
                     ('A pagar filtrado', ('pay_account_filter', account, month))],
                    [('🏠 Início', ('view', 'home'))]]
            return Screen(report_html(re.sub(r'#C?\d+ · ', '', raw)), rows)
        resumo = comp.calcular_resumo_pagamento_conta(month, account)
        title = safe(account, 50)
        if not resumo.get('possui_dados'):
            prev_month = month_shift(month, -1)
            next_month = month_shift(month, 1)
            screen = Screen(f'<b>{title} · {month_label(month)}</b>\n\nNão encontrei pagamentos pendentes para esta conta.',
                            [[('‹ Mês anterior', ('pay_account', account, prev_month)),
                              ('Próximo mês ›', ('pay_account', account, next_month))],
                             [('Abrir A pagar', ('view','pay')), ('🏠 Início', ('view','home'))]],
                            sensitive=True)
            screen.rich_html = (
                '<h2>Quanto vou pagar no '+title+'</h2>'
                '<p><i>'+month_label(month)+'</i></p>'
                + rich_table(('Componente', 'Valor'),
                             [('Nenhuma obrigação em aberto', money(0))],
                             ('Total a pagar', money(0)))
            )
            return screen
        lines = [f'<b>Quanto vou pagar no {title} · {month_label(month)}</b>', '']
        components = []
        if resumo.get('possui_fatura'):
            components.append(('💳 Fatura/cartão', resumo.get('fatura')))
        if float(resumo.get('fatura_bruta') or 0) > .005:
            components.append(('🛒 Compras/cobranças do mês', resumo.get('fatura_bruta')))
        if float(resumo.get('credito_herdado') or 0) > .005:
            components.append(('↩ Crédito anterior aplicado', resumo.get('credito_herdado')))
        if float(resumo.get('ajuste_conferencia') or 0) > .005:
            components.append(('🧮 Ajuste de conferência', resumo.get('ajuste_conferencia')))
        if float(resumo.get('fixos') or 0) > .005:
            components.append(('🔁 Fixos', resumo.get('fixos')))
        if float(resumo.get('emprestimos') or 0) > .005:
            components.append(('🤝 Empréstimos', resumo.get('emprestimos')))
        if float(resumo.get('compromissos') or 0) > .005:
            components.append(('📝 Compromissos', resumo.get('compromissos')))
        lines.extend(f'{label}: <b>{money(value)}</b>' for label, value in components)
        lines += ['', f'🧾 <b>TOTAL A PAGAR: {money(resumo.get("total"))}</b>',
                  '', '💡 <b>O que compõe este valor</b>\nOs fixos no crédito já fazem parte da fatura correspondente. Abra <b>Ver detalhes</b> para conferir a composição ou <b>A pagar filtrado</b> para ver as pendências desta conta.']
        if float(resumo.get('credito_disponivel') or 0) > .005:
            lines += ['', f'Crédito disponível na fatura: {money(resumo.get("credito_disponivel"))}']
        prev_month = month_shift(month, -1)
        next_month = month_shift(month, 1)
        rows = [[('‹ Mês anterior', ('pay_account', account, prev_month)),
                 ('Próximo mês ›', ('pay_account', account, next_month))],
                [('Ver detalhes', ('pay_account_detail', account, month)),
                 ('A pagar filtrado', ('pay_account_filter', account, month))],
                [('🏠 Início', ('view','home'))]]
        screen=Screen('\n'.join(lines), rows,sensitive=True)
        screen.rich_html = (
            '<h2>Quanto vou pagar no '+title+'</h2>'
            '<p><i>'+month_label(month)+'</i></p>'
            + self._pay_summary_rich_body(resumo, guidance=True)
        )
        return screen

    def fast_deterministic_query(self, key, text, deterministic_view=None):
        """Resolve consultas inequívocas sem chamar Ollama.

        A IA fica reservada para linguagem que realmente precisa de interpretação;
        filtros explícitos de conta/mês usam diretamente o motor financeiro existente.
        """
        clean = norm(text)
        s = self.session(key)
        from consultas_rapidas import interpretar_consulta
        query = interpretar_consulta(text)
        if query is not None and not self._account_in_text(text):
            return self._ai_query_result(key, query, text)
        # 'saldo <conta>' é uma consulta inequívoca e deve usar o caixa da conta,
        # nunca o saldo consolidado. Uma nova consulta textual sem mês volta ao
        # mês vigente; os botões preservam a competência escolhida.
        if deterministic_view == 'balance' or re.match(r'^(?:saldo|carteira|caixa)\b', clean):
            account=self._account_in_text(text)
            explicit_month=self._month_from_text(text)
            if account:
                month=explicit_month or self.date_provider().strftime('%Y-%m')
                return self._balance_account_screen(key,account,month)
        if deterministic_view == 'pay' or re.search(r'\bquanto\s+(?:vou\s+)?pagar\b', clean):
            account = self._account_in_text(text)
            explicit_month = self._month_from_text(text)
            # Nova consulta textual sem competencia explicita sempre parte do mes vigente.
            # A navegacao por botoes continua preservando o mes selecionado.
            month = explicit_month or self.date_provider().strftime('%Y-%m')
            if account:
                return self._pay_account_screen(key, account, month)
            if re.fullmatch(r'(?:quanto\s+(?:vou\s+)?pagar|quanto\s+pagar)(?:\s+(?:no\s+mes|no\s+m[eê]s|em)?\s*.*)?', clean):
                s.month = month
                s.pay_month_page = 0
                return self._ai_query_result(key, {'intent':'pay','query_type':'payables','period':''}, text)
        return None

    def _ai_query_result(self,key,parsed,original_text):
        screen=self._ai_query_result_core(key,parsed,original_text)
        # A prévia de um registro precisa mostrar o valor para o titular confirmar.
        if str(parsed.get('query_type') or '').startswith('register_'):
            return screen
        return self._apply_privacy(self.session(key),screen)

    def _ai_query_result_core(self,key,parsed,original_text):
        """Executa somente consultas determinísticas a partir da intenção estruturada."""
        s=self.session(key)
        qtype=parsed.get('query_type') or 'navigate'
        if qtype in {'register_expense','register_income'}:
            return self._ai_registration_preview(key,parsed,original_text)
        # Uma consulta pausa o formulário: a próxima resposta solta não cai no
        # rascunho antigo, e Registrar permite retomar sem perder os campos.
        if s.stage and s.draft:self._suspend_flow(s)
        s.stage=None
        s.draft=None
        s.settings_draft=None
        from consultas_rapidas import PERIODOS_PROPRIOS,PERIODO_INVALIDO,resolver_meses,rotulo_periodo,linhas_por_mes  # período próprio: não reler o texto ("de julho a novembro" ≠ julho)
        months = resolver_meses(parsed,self.date_provider()) if parsed.get('period') in PERIODOS_PROPRIOS else [m] if (m:=self._month_from_text(original_text)) else self._ai_months(s,parsed.get('period'))
        if not months:return Screen(PERIODO_INVALIDO,[[('📊 Análises',('view','analytics'))],*self.nav('analytics')])
        # Os botões de detalhes usam a competência da sessão. Atualizá-la também
        # nas consultas relativas evita mostrar agosto e abrir dezembro depois.
        s.month = months[-1]
        details_suffix = f' · {month_label(months[-1])}' if len(months)>1 else ''

        if qtype == 'payables':return self._pay_month_screen(key, months[-1])
        if qtype == 'payables_category':return self.act(key,('pagar_cat',str(parsed.get('category') or ''),months[0],months[-1]))  # consultas_pagar

        if qtype in {'category_expense','expense_total','income_total','largest_expenses'}:
            rows=[]
            with db.read_only_mode():
                for month in months:
                    rows.extend(dict(t,_mes=month) for t in db.buscar_transacoes_por_mes(month))
            # Consulta sobre o que já aconteceu: lançamentos com data futura (ex.: parcela do dia 14
            # vista no dia 9) ficam de fora, como no Fechamento e nas Análises.
            hoje_iso=self.date_provider().isoformat()
            rows=[t for t in rows if str(t.get('data') or '')[:10]<=hoje_iso]
            kind='receita' if qtype=='income_total' else 'despesa'
            filtered=[t for t in rows if t.get('tipo')==kind]
            category=(parsed.get('category') or '').strip()
            if qtype=='category_expense' and category:
                cat_norm=norm(category)
                exact=[t for t in filtered if norm(t.get('categoria'))==cat_norm]
                if exact:
                    filtered=exact
                else:
                    filtered=[t for t in filtered if cat_norm in norm(t.get('categoria')) or cat_norm in norm(t.get('descricao'))]
            total=sum(float(t.get('valor') or 0) for t in filtered)
            period_label=rotulo_periodo(months,self.date_provider(),month_label)
            by_month=linhas_por_mes(months,filtered,self.date_provider(),month_label,money)
            if qtype=='category_expense':
                title=f'Gastos com {safe(category or "essa categoria",50)}'
                if filtered:
                    top=sorted(filtered,key=lambda t:float(t.get('valor') or 0),reverse=True)[:3]
                    lines=[f'<b>{title}</b>',period_label,'',f'Total registrado: <b>{money(total)}</b>',f'{plural(len(filtered), "lançamento encontrado", "lançamentos encontrados")}.']
                    lines+=by_month
                    lines+=['','<b>Maiores lançamentos</b>']+[f'{safe(t.get("descricao"),45)} · {money(t.get("valor"))}' for t in top]
                    lines+=['','Esse valor usa somente os lançamentos registrados e classificados no assessor.']
                    return Screen('\n'.join(lines),[[('Ver lançamentos'+details_suffix,('category',category)),('📊 Análises'+details_suffix,('view','analytics'))],*self.nav('analytics')])
                cats=defaultdict(float)
                for t in rows:
                    if t.get('tipo')=='despesa':cats[t.get('categoria') or 'Outros']+=float(t.get('valor') or 0)
                suggestions=', '.join(str(c) for c,_ in sorted(cats.items(),key=lambda x:x[1],reverse=True)[:4])
                text=f'<b>{title}</b>\n{period_label}\n\nNão encontrei lançamentos que correspondam a <b>{safe(category,50)}</b>.'
                if suggestions:text+=f'\n\nCategorias com movimento: {safe(suggestions,140)}.'
                text+='\n\nIsso pode significar que a categoria tem outro nome ou que ainda faltam registros.'
                return Screen(text,[[('Ver análises',('view','analytics')),('Revisar registros',('view','review'))],*self.nav('analytics')])
            if qtype in {'expense_total','income_total'}:
                label='despesas' if kind=='despesa' else 'entradas'
                return Screen(f'<b>Total de {label}</b>\n{period_label}\n\n<b>{money(total)}</b>\n{plural(len(filtered), "lançamento")}.'+''.join('\n'+l for l in by_month)+'\n\nO total considera somente os movimentos registrados no assessor.',[[('Abrir detalhes'+details_suffix,('view','analytics' if kind=='despesa' else 'history'))],*self.nav('home')])
            if qtype=='largest_expenses':
                cats=defaultdict(float)
                for t in filtered:cats[t.get('categoria') or 'Outros']+=float(t.get('valor') or 0)
                ranked=sorted(cats.items(),key=lambda x:x[1],reverse=True)
                lines=['<b>O que está pesando mais</b>',period_label,'']
                if not ranked:lines+=['Ainda não há despesas registradas nesse período.']
                else:
                    lines += [f'{i}. {safe(cat,40)} · <b>{money(value)}</b>' for i,(cat,value) in enumerate(ranked[:5],1)]
                    lines += ['',f'Total de despesas registradas: <b>{money(sum(v for _,v in ranked))}</b>.']
                lines+=['','A análise depende da classificação e da completude dos seus registros.']
                return Screen('\n'.join(lines),[[('📊 Análises'+details_suffix,('view','analytics')),('🔎 Revisar registros'+details_suffix,('view','review'))],*self.nav('analytics')])
        route=parsed.get('intent')
        renderable={'home','balance','pay','receivables','history','analytics','budgets','agenda','review','recurring','alerts','help','plan','register','more','reconciliations','assistant','attention','closing','categories','setup','month_actions'}
        if route in renderable:return self.act(key,('view',route))
        return self.question_result(key,original_text)

    def _ai_registration_preview(self,key,parsed,original_text):
        """IA pode preencher uma prévia; confirmar continua sendo ação explícita do usuário."""
        from roteamento_seguro import comando_operacional, campo_ia_valido
        if comando_operacional(original_text):
            raise ValueError('Use o comando de alteração; esta mensagem não é um novo gasto.')
        s=self.session(key)
        paused=self._paused_draft_guard(s)
        if paused is not None:return paused
        tipo='receita' if parsed.get('query_type')=='register_income' else 'despesa' 
        amount=float(parsed.get('amount') or 0)
        installments=int(parsed.get('installments') or 0)
        if tipo=='receita':installments=1
        if installments<=0:installments=1
        desc=(parsed.get('description') or '').strip()
        ai_category=(parsed.get('category') or '').strip()
        category=''
        if not campo_ia_valido(desc):desc=''
        if not campo_ia_valido(ai_category):ai_category=''
        account=(parsed.get('account') or '').strip()
        if not campo_ia_valido(account):account=''
        if desc:
            category=sugerir_categoria(desc,tipo) or ''
        # A IA só pode sugerir um nome da taxonomia e apenas quando o dicionário
        # não encontrou evidência. A prévia continua editável antes de salvar.
        if not category:
            category=categoria_permitida_ia(ai_category) or ''
        method=norm(parsed.get('payment_method') or '')
        methods={'pix':'pix','debito':'débito','credito':'crédito','cartao':'crédito','cartao de credito':'crédito','dinheiro':'dinheiro','transferencia':'transferência'}
        payment=methods.get(method,'')
        if installments>1:payment='crédito'
        s.draft={'tipo':tipo,'valor':amount if amount>0 else None,'descricao':desc,'categoria':category,
                 'conta':account,'forma_pagamento':payment,
                 'data':self.date_provider().isoformat(),'parcelas_total':installments,
                 'mensagem_original':original_text[:500],'key':secrets.token_urlsafe(18),'parsed':True,'ai_interpreted':True}
        if not category:s.draft['categoria']='Outros'
        return self._advance_registration(key)

    def question_result(self,key,text):
        s=self.session(key);s.stage=None
        view=orient.reconhecer_pergunta(text)
        if view:return self.act(key,('view',view))
        s.ai_question=text[:500]
        # A decisão sobre consultar o Ollama é feita de forma automática no dispatcher.
        # Esta tela é apenas o fallback final quando regras + IA local não fecham uma rota.
        return Screen('Quero entender melhor o que você precisa. Qual destes caminhos está mais próximo?',[
            [('Analisar meus gastos',('view','analytics')),('Ver meu saldo',('view','balance'))],
            [('Contas a pagar',('view','pay')),('Entradas previstas',('view','receivables'))],
            [('Planejar meu mês',('view','plan')),('Registrar movimento',('view','register'))],
            [('Perguntar de novo',('ask',)),('🏠 Início',('view','home'))]])


def _runtime_store():
    config.carregar_dotenv()
    enabled=config.ler('ASSESSOR_PERSIST_SESSIONS','true').strip().lower() not in {'0','false','nao','não','off'}
    if not enabled:
        return None
    from estado_runtime import ProtectedJsonStore
    return ProtectedJsonStore(Path(__file__).resolve().parent/'.runtime'/'telegram_sessions.bin')


EXPERIENCE = Experience(state_store=_runtime_store())


async def run_experience(metodo, key, *args):
    """Executa uma operação completa da experiência fora do event loop."""
    try:
        return await executar_core(getattr(EXPERIENCE, metodo), key, *args)
    finally:
        EXPERIENCE.persist()


def session_key(update):
    from telegram_recursos import thread_id
    topic=thread_id(update)
    base=f'{update.effective_user.id}:{update.effective_chat.id}'
    return base+(':topic:'+str(topic) if topic else '')


async def send_screen(update, screen, host, edit=False):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
    try:
        from telegram import CopyTextButton
    except ImportError:  # compatibilidade defensiva; requirements.txt usa 22.8
        CopyTextButton = None
    from telegram.error import BadRequest
    key=session_key(update)
    session=EXPERIENCE.session(key)
    old_tokens=dict(session.tokens)
    if len(screen.text.encode('utf-16-le'))//2>3900:
        raise ValueError('Tela excedeu o limite de texto. Abra uma lista menor.')
    rows=EXPERIENCE.tokens_for(key,screen)
    keyboard=[]
    # Cores pela tela inteira: com uma confirmação verde, "Cancelar" fica vermelho.
    screen_style_rows=screen_styles([[(label, action) for label, action in row] for row in screen.rows])
    for source_row, token_row, style_row in zip(screen.rows, rows, screen_style_rows):
        rendered=[]
        for (label, action), (_, token), base_style in zip(source_row, token_row, style_row):
            label=button_label(label, action)
            style=selected_style(action,session) or base_style
            if isinstance(action, (tuple, list)) and action and action[0]=='copy_text':
                payload=copy_text_value(action[1])
                if not payload or CopyTextButton is None:
                    # Em biblioteca antiga, omita apenas o atalho de copiar. A
                    # informação continua visível em texto; a tela não quebra.
                    continue
                try:
                    rendered.append(InlineKeyboardButton(label,copy_text=CopyTextButton(payload),style=style))
                except TypeError:
                    rendered.append(InlineKeyboardButton(label,copy_text=CopyTextButton(payload)))
            elif action[0]=='disabled':
                rendered.append(InlineKeyboardButton(label,api_kwargs={'disabled':{}},style=style))
            else:
                try:
                    rendered.append(InlineKeyboardButton(label,callback_data=token,style=style))
                except TypeError:
                    rendered.append(InlineKeyboardButton(label,callback_data=token))
        if rendered:
            keyboard.append(rendered)
    markup=InlineKeyboardMarkup(keyboard)
    query=getattr(update,'callback_query',None)
    previous_photo=bool(query and getattr(getattr(query,'message',None),'photo',None))
    previous_protected=bool(query and getattr(getattr(query,'message',None),'has_protected_content',False))
    clear_previous_markup=False
    from telegram_recursos import protect_financial_content
    protected=protect_financial_content(screen)
    # O Telegram não permite transformar uma mensagem antiga desprotegida em
    # protegida por edição. Nessa transição, publique uma nova tela e retire
    # os controles da anterior somente depois que o novo envio for confirmado.
    transport_edit=edit and (not protected or previous_protected)

    async def clear_old_controls():
        if not query:
            return
        try:
            retired=InlineKeyboardMarkup([[
                InlineKeyboardButton('✓ Tela atualizada',api_kwargs={'disabled':{}})
            ]])
            await query.edit_message_reply_markup(reply_markup=retired)
        except BadRequest:
            # Bot API anterior a 10.3: retire os controles sem o estado visual.
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                logging.warning('Não foi possível remover os controles da tela anterior.', exc_info=True)
        except Exception:
            # A nova tela já foi entregue. Falha ao limpar controles antigos não
            # deve invalidar os callbacks recém-publicados.
            logging.warning('Não foi possível remover os controles da tela anterior.', exc_info=True)

    try:
        from telegram_recursos import send_rich,thread_id
        thread_kwargs={'message_thread_id':thread_id(update)} if thread_id(update) else {}
        if await send_rich(update,screen,markup,host,transport_edit,protect=protected):
            if edit and (previous_photo or (protected and not transport_edit)):await clear_old_controls()
            return
        if screen.image and callable(getattr(update.effective_chat,'send_photo',None)):
            try:
                from telegram_visuais import painel
                media=painel(screen.image)
            except (ImportError,OSError,ValueError):
                logging.exception('Painel indisponível; usando os mesmos dados em texto')
            else:
                short=len(screen.text.encode('utf-16-le'))//2<=1024
                caption=screen.text if short else '<b>'+safe(screen.image['title'])+'</b>\nOs detalhes e as ações estão na próxima mensagem.'
                # Edição de uma foto curta é atômica: conteúdo e novos callbacks
                # entram juntos. Para telas longas, preserve os controles antigos
                # até a nova mensagem textual (que contém as ações) ser entregue.
                if transport_edit and previous_photo and short:
                    try:
                        await query.edit_message_media(InputMediaPhoto(media,caption=caption,parse_mode='HTML'),reply_markup=markup)
                        return
                    except BadRequest as exc:
                        if 'not modified' in str(exc).lower():
                            return
                        if not any(x in str(exc).lower() for x in ('not found',"can't be edited")):
                            raise
                if edit and query:
                    clear_previous_markup=True
                message=await update.effective_chat.send_photo(photo=media,caption=caption,parse_mode='HTML',reply_markup=markup if short else None,protect_content=protected,**thread_kwargs)
                host.registrar_mensagem_enviada(message)
                if short:
                    if clear_previous_markup:
                        await clear_old_controls()
                    return
                message=await update.effective_chat.send_message(screen.text,parse_mode='HTML',reply_markup=markup,protect_content=protected,**thread_kwargs)
                host.registrar_mensagem_enviada(message)
                if clear_previous_markup:
                    await clear_old_controls()
                return

        if transport_edit and previous_photo:
            # Uma foto não pode virar texto via editMessageText. Envie a nova
            # tela primeiro; só depois retire os botões da tela anterior.
            clear_previous_markup=True
            transport_edit=False
        if transport_edit and update.callback_query:
            try:
                await update.callback_query.edit_message_text(screen.text,parse_mode='HTML',reply_markup=markup)
                return
            except BadRequest as exc:
                if 'not modified' in str(exc).lower():
                    return
                if not any(x in str(exc).lower() for x in ('message to edit not found','message can\'t be edited','message is not modified')):
                    raise
                clear_previous_markup=True
        if edit and protected and not transport_edit:
            clear_previous_markup=True
        message=await update.effective_chat.send_message(screen.text,parse_mode='HTML',reply_markup=markup,protect_content=protected,**thread_kwargs)
        host.registrar_mensagem_enviada(message)
        if clear_previous_markup:
            await clear_old_controls()
    except Exception:
        # A tela antiga continua visualmente utilizável em falhas de envio.
        # Portanto seus callbacks também precisam continuar válidos.
        session.tokens.clear()
        session.tokens.update(old_tokens)
        raise
    finally:
        EXPERIENCE.persist()


def _invalidar_preservando_pausa(key):
    """Como EXPERIENCE.invalidate, mas um registro pausado continua guardado
    para "↩ Retomar registro" (antes um comando digitado o apagava sem aviso)."""
    antiga=EXPERIENCE.sessions.get(key)
    EXPERIENCE.invalidate(key)
    if antiga is not None and antiga.suspended_draft and antiga.suspended_stage:
        nova=EXPERIENCE.session(key)
        nova.suspended_draft=antiga.suspended_draft
        nova.suspended_stage=antiga.suspended_stage
        nova.suspended_view=antiga.suspended_view
        # Os botões "Retomar/Descartar" já enviados continuam valendo.
        nova.tokens.update({token:acao for token,acao in antiga.tokens.items()
                            if acao and tuple(acao)[:1] in {('resume_suspended',),('discard_suspended',)}})
        EXPERIENCE.persist()


def _draft_summary(draft):
    """Uma linha com o que já foi preenchido no rascunho (ex.: Uber · R$ 13,32)."""
    if not draft:
        return ''
    partes=[]
    if draft.get('descricao'):partes.append(safe(str(draft['descricao']),60))
    try:
        if draft.get('valor'):partes.append(money(float(draft['valor'])))
    except (TypeError,ValueError):
        pass
    return ' · '.join(partes)


_OUTRO_LANCAMENTO=re.compile(r'^(?:gastei|comprei|paguei|recebi|ganhei|transferi|novo fixo|nova despesa|nova entrada)\b')


_RESPOSTAS_DE_ETAPA=frozenset({'sim','nao','pix','debito','credito','dinheiro','boleto','transferencia','hoje','ontem',
                               'anteontem','salvar','confirmar','confirmo','pular','sem termino','a vista','parcelado'})


def _parece_resposta_de_etapa(clean):
    """Resposta curta típica de uma etapa (valor, data, forma, sim/não), sem sentido fora do fluxo."""
    value=clean.strip(' .!')
    return bool(value in _RESPOSTAS_DE_ETAPA or re.fullmatch(r'(?:r\$\s*)?[\d\s.,/+\-]+',value)
                or re.fullmatch(r'(?:dia\s+)?\d{1,2}(?:x|\s*vezes)?',value))


def _tela_fluxo_expirado():
    return Screen('<b>⏱ Esse registro expirou.</b>\n\nEle ficou mais de 10 minutos parado e foi encerrado por segurança. '
                  'Nada foi gravado.\n\nRecomece em Registrar; leva poucos toques.',
                  [[('➕ Registrar',('view','register')),('🔎 Histórico',('view','history'))],[('🏠 Início',('view','home'))]])


def parece_outro_lancamento(text):
    """Frase que claramente é um lançamento novo: verbo de registro + valor (ex.: "gastei 15 no café")."""
    clean=norm(text).strip()
    return bool(_OUTRO_LANCAMENTO.match(clean) and re.search(r'\d',clean) and len(clean.split())>=3)


NATIVE_TEXT_ANSWER_STAGES=frozenset({
    'description','category','account','search','account_search',
    'cash_setup_account_name','budget_category','invoice_account','fix_date',
    'new_fixed_name','new_fixed_category','new_fixed_account',
    'confirm','invoice_confirm','confirm_settings','confirm_budget','confirm_balance','cash_setup_confirm',
})
NATIVE_CONFIRM_STAGES=frozenset({
    'confirm','invoice_confirm','confirm_settings','confirm_budget','confirm_balance','cash_setup_confirm',
})


async def dispatch_text(update,context,host):
    key=session_key(update)
    # The adapter is always called after the existing Telegram allowlist check. PIN is reserved for sensitive actions.
    try:
        text=update.message.text or ''
        clean=norm(text)
        # A number is contextual when an existing guided flow has requested it.
        # Let that flow validate it; do not cancel it as a free-standing expense.
        native=EXPERIENCE.sessions.get(key)
        native_active=bool(native and native.stage and EXPERIENCE.clock()-native.touched<=TTL)
        legacy_guided=getattr(host,'PENDENCIAS_GUIADAS',{}).get(host.obter_chat_id_update(update))
        legacy_pending=any(svc._obter_pendencia(store,key) for store in (
            svc.PENDENCIAS_CONFIRMACAO,svc.PENDENCIAS_IMPORTACAO,
            svc.PENDENCIAS_EXPORTACAO,svc.PENDENCIAS_EXCLUSAO,svc.PENDENCIAS_ALTERACAO))
        if not native_active and (legacy_guided or legacy_pending) and re.fullmatch(r'[\d\s.,/+\-]+',text.strip()):
            return False
        # Respostas e confirmações legadas pertencem ao fluxo que as solicitou.
        # Retornar False mantém as confirmações de exclusão e o PIN no app.
        from roteamento_seguro import comando_operacional
        deletion_pending=getattr(host,'PENDENCIAS_EXCLUSAO',{}).get(host.obter_chat_id_update(update))
        if legacy_guided or legacy_pending or (deletion_pending and not native_active):
            return False
        # Fluxo nativo que expirou (10 min parado): a resposta solta não pode cair
        # no legado com um erro sem relação. Avisa e oferece recomeçar.
        expired_flow=bool(native and not native_active and (native.stage or native.draft or native.new_fixed)
                          and EXPERIENCE.clock()-native.touched>TTL)
        if expired_flow and _parece_resposta_de_etapa(clean):
            EXPERIENCE.session(key)  # descarta a sessão vencida; preferências (Ocultar) continuam
            await send_screen(update,_tela_fluxo_expirado(),host)
            host.marcar_acesso_seguro(update.effective_user.id)
            EXPERIENCE.persist()
            return True
        if native_active and str(native.stage).startswith('fixed_') and comando_operacional(text) and re.match(r'^(?:alterar|mudar|trocar|corrigir)\b',clean):
            EXPERIENCE.invalidate(key)
            return False
        if (native_active and str(native.stage).startswith('fixed_')) or re.fullmatch(r'(?:editar\s+fixos|(?:editar|detalhar)\s+fixo\s+#?c?\d+)',clean):
            from fixos_interface import texto as fixed_text
            try:
                fixed_screen=await executar_core(fixed_text,EXPERIENCE,key,text)
            except ValueError as exc:
                fixed_screen=Screen(safe(str(exc))+'\n\nCorrija a informação ou use /cancelar.',[[('Editar fixos',('fixed_list',0))]])
            if fixed_screen is not None:
                host.marcar_acesso_seguro(update.effective_user.id)
                await send_screen(update,fixed_screen,host)
                return True
        # Em etapas nativas que pedem texto livre (nome, descrição, conta...) ou
        # aguardam a confirmação por botão, a resposta pertence ao formulário:
        # "Trocar óleo do carro" é uma descrição, não um comando operacional.
        # Somente o cancelamento explícito continua saindo do fluxo.
        # "Cancelar.", "cancelar!", "cancelar registro" continuam saindo do fluxo.
        pede_cancelamento=bool(re.match(r'^/?cancelar\b', clean))
        text_answer_stage=bool(native_active and native.stage in NATIVE_TEXT_ANSWER_STAGES
                               and not pede_cancelamento)
        # Nas telas de confirmação só "confirmar/salvar" fica no formulário (reexibe a
        # prévia); outros comandos digitados seguem o comportamento anterior.
        if text_answer_stage and native.stage in NATIVE_CONFIRM_STAGES:
            text_answer_stage=clean.strip(' .!') in {'confirmar','confirmo','salvar','confirmar registro'}
        # Pagamento/estorno/crédito de fatura digitado com um registro aberto:
        # o registro é pausado (com aviso e botões para retomar ou descartar) e
        # o comando segue para a prévia da fatura, em vez de ser lido como
        # resposta da etapa (ex.: "reembolso de 62,16 na fatura Itaú" na data).
        if native_active and native.draft and not text_answer_stage:
            movimento=svc.parsear_comando_movimento_fatura(text)
            valido=bool(movimento and movimento[0]=='registrar' and movimento[2] and float(movimento[2])>0)
            if valido and native.suspended_draft and native.suspended_stage:
                # Já existe um registro pausado: não sobrescreve; o registro
                # atual continua aberto e o comando segue para a fatura.
                return False
            if valido and EXPERIENCE._suspend_flow(native):
                EXPERIENCE.persist()
                resumo=_draft_summary(native.suspended_draft)
                await send_screen(update,Screen(
                    '⏸️ Registro em andamento pausado'+(f'\n\n{resumo}' if resumo else '')+
                    '\n\nNada foi gravado nele. Abaixo segue a prévia da fatura que você enviou.',
                    [[('↩ Retomar registro',('resume_suspended',)),('Descartar rascunho',('discard_suspended',))]]),host)
                return False
        # Uma frase de lançamento completa no meio de outro assistente não é a
        # resposta da etapa: pergunta antes de continuar ou trocar de registro.
        if (native_active and (native.draft or native.new_fixed) and not pede_cancelamento
                and native.stage not in {'amount','new_fixed_amount'} and parece_outro_lancamento(text)):
            resumo=_draft_summary(native.draft or native.new_fixed)
            await send_screen(update,Screen(
                '<b>Você está no meio de um registro.</b>'+(f'\n\n{resumo}' if resumo else '')+
                '\n\nA mensagem que você enviou parece outro lançamento. Nada foi gravado.\n'
                'Quer continuar o registro atual ou começar este?',
                [[('↩ Continuar o atual',('conflict_keep',)),('Começar este',('conflict_start',text[:300]))],
                 [('Cancelar o atual',('cancel',))]]),host)
            host.marcar_acesso_seguro(update.effective_user.id)
            EXPERIENCE.persist()
            return True
        # "entrada freela 800" continua no rascunho nativo de entrada recebida
        # (handle_text); só a forma "nova entrada"/"entrada prevista" sem data
        # completa, que antes caía no legado como despesa, é recusada aqui.
        if not text_answer_stage and re.match(r'^(?:nova\s+(?:entrada|receita)|(?:entrada|receita)\s+previst[ao])\b',clean):
            entrada=svc.parsear_comando_entrada_avulsa(text.lower().strip())
            if entrada and entrada.get('erro')=='data':
                # Entrada prevista sem data completa: nada é gravado (antes virava despesa).
                host.marcar_acesso_seguro(update.effective_user.id)
                await send_screen(update,Screen(
                    '<b>Nada foi registrado.</b>\n\nPara cadastrar uma <b>entrada prevista</b>, informe a data completa: '
                    '<code>entrada freela 800 em 2026-11-20</code>.\n\nSe o dinheiro já entrou na conta, registre como entrada recebida: '
                    'você confere tudo antes de salvar.',
                    [[('+ Registrar entrada',('start','receita')),('💵 A receber',('view','receivables'))],
                     [('🏠 Início',('view','home'))]]),host)
                return True
        if comando_operacional(text) and not text_answer_stage:
            _invalidar_preservando_pausa(key)
            return False
        # Pagamento/estorno/crédito de fatura digitado fora de um formulário é
        # sempre do comando próprio (prévia + botões). Sem isto, a IA local
        # podia ler "Reembolso de 1 na fatura Itaú" como uma despesa nova.
        if not native_active:
            movimento_fatura=svc.parsear_comando_movimento_fatura(text)
            if movimento_fatura and movimento_fatura[0] in {'registrar','erro'}:
                return False
        stage_before=native.stage if native_active else None

        # Intenções globais podem interromper um fluxo guiado. Isso evita que uma
        # pergunta natural enviada enquanto o bot espera, por exemplo, um valor seja
        # tratada como resposta inválida daquele campo. Respostas curtas próprias do
        # formulário (valor, descrição, conta, data etc.) continuam no fluxo atual.
        deterministic_view=orient.reconhecer_pergunta(text)
        consultation_cue=bool(
            '?' in text
            or stage_before=='ask'
            or re.search(r'\b(quero|queria|gostaria|preciso|me mostra|me mostre|me diga|me ajuda|me ajude|entender|analisar|onde|quanto|qual|como|por que|porque|o que|estou sentindo|esta pesando|está pesando)\b',clean)
        )
        transaction_command=bool(re.match(r'^(gastei|recebi|comprei|paguei|ganhei|entrada|simular)\b',clean))
        from consultas_rapidas import interpretar_consulta
        global_candidate=(learning.route(text) is None and dashboard_route(text) is None and not transaction_command and (deterministic_view is not None or interpretar_consulta(text) is not None or (consultation_cue and len(clean.split())>=3)))
        if stage_before in {'description','account','category'}:
            # Um nome como "Restaurante Como Antigamente" é a resposta do
            # formulário. Palavras isoladas dentro dele não devem chamar a IA.
            explicit_question=bool(re.match(r'^(?:quanto|onde|qual|quais|como|por que|porque|o que|quero|queria|gostaria|preciso|me mostr[ae]|me diga|me ajud[ae])\b',clean))
            global_candidate=global_candidate and explicit_question

        if global_candidate:
            fast_screen=await run_experience('fast_deterministic_query',key,text,deterministic_view)
            if fast_screen is not None:
                screen=fast_screen
            else:
                import asyncio
                from assessor_ia_local import interpretar_contexto,LocalUnavailable
                from telegram_streaming import DraftProgress
                progress=DraftProgress(update)
                if not await progress.show('🧠 Analisando sua pergunta localmente…'):
                    try:
                        await host.enviar_acao_digitando(update, context)
                    except Exception:
                        pass
                # Mesmo quando a regra já sabe a tela, o Ollama pode enriquecer a consulta
                # com categoria/período/tipo de pergunta. Se falhar, a regra continua valendo.
                enrich=bool(deterministic_view in {'analytics','balance','pay','receivables'} and re.search(
                    r'\b(quanto|qual|onde|com|em|mes|mês|passado|pesando|maior|total|gastei|gasto|recebi)\b',clean))
                if deterministic_view is not None and not enrich:
                    screen=await run_experience('act',key,('view',deterministic_view))
                else:
                    try:
                        parsed=await asyncio.to_thread(interpretar_contexto,text[:500],True)
                    except LocalUnavailable:
                        screen=(await run_experience('act',key,('view',deterministic_view)) if deterministic_view is not None
                                else await run_experience('question_result',key,text))
                    else:
                        if deterministic_view is not None:
                            parsed=dict(parsed or {})
                            parsed['intent']=deterministic_view
                        await progress.show('📝 Preparando uma resposta conferível…')
                        screen=await run_experience('_ai_query_result',key,parsed,text)
                await progress.close()
        else:
            screen=await run_experience('handle_text',key,text)

            # Segunda camada automática fora de um fluxo guiado: além de navegar,
            # pode responder consultas filtradas ou montar uma prévia de registro.
            looks_natural=(stage_before=='ask' or '?' in text or (len(clean.split())>=4 and not transaction_command))
            needs_ai=looks_natural and screen is None
            if needs_ai:
                import asyncio
                from assessor_ia_local import interpretar_contexto,LocalUnavailable
                from telegram_streaming import DraftProgress
                progress=DraftProgress(update)
                if not await progress.show('🧠 Analisando sua pergunta localmente…'):
                    try:
                        await host.enviar_acao_digitando(update, context)
                    except Exception:
                        pass
                try:
                    parsed=await asyncio.to_thread(interpretar_contexto,text[:500],True)
                except LocalUnavailable:
                    if stage_before=='ask' or '?' in text:
                        screen=await run_experience('question_result',key,text)
                else:
                    await progress.show('📝 Preparando uma resposta conferível…')
                    screen=await run_experience('_ai_query_result',key,parsed,text)
                await progress.close()

        if screen is None:
            if not expired_flow:return False
            screen=_tela_fluxo_expirado()
        host.limpar_pendencia_guiada(host.obter_chat_id_update(update))
        host.limpar_pendencia_exclusao(host.obter_chat_id_update(update))
        clear_service_pending(key)
        host.marcar_acesso_seguro(update.effective_user.id)
        await send_screen(update,screen,host)
    except ValueError as exc:
        await send_screen(update, Screen('Confira esta informação:\n\n'+safe(str(exc),500),
            [[('🏠 Início',('view','home')),('📘 Ajuda',('view','help'))]]), host)
    except Exception:
        logging.exception('Falha na interface Telegram')
        from telegram_recursos import thread_options
        await update.effective_chat.send_message(message_html('Não consegui concluir esta etapa. Confira o Histórico antes de tentar registrar novamente. Use /menu para voltar.'), parse_mode="HTML", **thread_options(update))
    return True


def expired_callback_screen(query, current_month=None):
    """Retoma um clique sem token válido sem presumir o estado financeiro anterior."""
    message=getattr(query,'message',None)
    source=(getattr(message,'text',None) or getattr(message,'caption',None) or '')
    clean=norm(source)
    base='<b>Este botão não está mais ativo.</b>\n\nNenhuma nova alteração foi feita por este clique.'

    # O primeiro clique pode ter funcionado anteriormente. Por isso, em telas
    # de confirmação, orientamos conferir o Histórico em vez de afirmar que
    # nunca houve gravação.
    if any(term in clean for term in ('confira antes de salvar','confirmar despesa','confirmar entrada','parcelamento','cronograma das parcelas')):
        return Screen(
            base+'\n\nSe você já tentou confirmar antes, confira o Histórico. Para registrar outra movimentação, abra um novo registro.',
            [[('🔎 Conferir Histórico',('view','history')),('➕ Registrar novamente',('view','register'))],
             [('🏠 Início',('view','home'))]],
        )
    if any(term in clean for term in ('historico','histórico','detalhes / corrigir','detalhes do lancamento','detalhes do lançamento')):
        return Screen(base+'\n\nAtualize o Histórico para continuar.',[
            [('🔎 Abrir Histórico',('view','history')),('🏠 Início',('view','home'))],
        ])
    if any(term in clean for term in ('a pagar','contas em aberto','compromisso')):
        return Screen(base+'\n\nAtualize A pagar antes de tentar novamente; os valores podem ter mudado.',[
            [('🧾 Abrir A pagar',('view','pay')),('🏠 Início',('view','home'))],
        ])
    if any(term in clean for term in ('ajuste de saldo','saldo atual','saldos por conta')):
        month=current_month or today().strftime('%Y-%m')
        return Screen(base+'\n\nAbra Saldos por conta para conferir o estado atual antes de fazer outro ajuste.',[
            [('🏦 Ver saldos por conta',('cash_accounts',month)),('🏠 Início',('view','home'))],
        ])
    return Screen(base+'\n\nAbra a tela novamente para gerar controles atualizados.',[
        [('🏠 Início',('view','home')),('🔎 Histórico',('view','history'))],
    ])


async def dispatch_callback(update,context,host):
    query=update.callback_query
    if not str(query.data or '').startswith('ux:'):return False
    try:
        await query.answer()
    except Exception:
        # O Telegram pode rejeitar o ACK de callbacks muito antigos. Ainda assim,
        # tente oferecer uma rota segura de retomada em vez de abandonar o clique.
        logging.warning('Não foi possível encerrar o indicador do callback.',exc_info=True)
    key=session_key(update);action=EXPERIENCE.resolve(key,query.data)
    public_help=bool(action and (action[0] in {'topic','lesson','lesson_page','quiz','quiz_answer','media_help'} or (action[0]=='view' and action[1] in {'help','command_help','learn','learn_topics','lesson'})))
    security_command=(action[1] if action and action[0] in {'legacy','legacy_raw'} else '')
    if not public_help and await host.bloquear_se_assessor_travado(update,security_command):
        return True
    if not action:
        current=EXPERIENCE.sessions.get(key)
        current_month=current.month if current else EXPERIENCE.date_provider().strftime('%Y-%m')
        try:
            await send_screen(update,expired_callback_screen(query,current_month),host,edit=False)
        except Exception:
            logging.exception('Falha ao enviar recuperação de callback expirado')
            await query.message.reply_text(message_html('Este botão não está mais ativo. Nenhuma nova alteração foi feita por este clique. Envie /menu para continuar.'), parse_mode="HTML")
        return True
    try:
        if action[0]=='topics_create':
            await host.topics_command(update,context);return True
        if action[0] in {'ai_route','ai_status'}:
            import asyncio
            from assessor_ia_local import interpretar,modelo_local,LocalUnavailable
            from telegram_streaming import DraftProgress
            progress=DraftProgress(update)
            if not await progress.show('🧠 Consultando o assessor local…'):
                try:
                    await host.enviar_acao_digitando(update, context)
                except Exception:
                    pass
            try:
                if action[0]=='ai_status':
                    model=await asyncio.to_thread(modelo_local)
                    screen=Screen('Ollama disponível. Modelo configurado: <b>'+safe(model)+'</b>.\n\nA interpretação automática está pronta para ser usada quando as regras precisarem de uma segunda camada.',[[('Testar uma pergunta',('ask',)),('Voltar',('view','local_ai'))]])
                else:
                    # Compatibilidade com botões antigos ainda presentes em mensagens já enviadas.
                    s=EXPERIENCE.session(key)
                    route=await asyncio.to_thread(interpretar,s.ai_question,True)
                    screen=await run_experience('act',key,('view',route))
            except LocalUnavailable:
                screen=Screen('O Ollama não respondeu com um modelo local válido agora. O assessor continua funcionando normalmente pelas regras.',[[('Tentar novamente',('ai_status',)),('Voltar ao assessor',('view','assistant'))]])
            await progress.close()
            await send_screen(update,screen,host,edit=True);return True
        if action[0]=='guided':
            EXPERIENCE.session(key).stage=None;EXPERIENCE.session(key).draft=None
            clear_service_pending(key)
            if action[1]=='registrar_fixo':
                screen=await run_experience('act',key,('new_fixed_start',))
                await send_screen(update,screen,host,edit=True);return True
            await host.iniciar_fluxo_guiado(update,context,action[1]);return True
        if action[0] in {'legacy','legacy_raw'}:
            cmd=action[1]
            if cmd=='__help__':await send_screen(update,await run_experience('act',key,('view','help')),host,edit=True)
            else:
                screen=await run_experience('handle_text',key,cmd) if action[0]=='legacy' else None
                if screen is not None:
                    await send_screen(update,screen,host,edit=True)
                    return True
                special=getattr(host,'obter_resposta_comando_especial',lambda *_:None)(update,cmd)
                resposta=special if special is not None else await executar_core(svc.processar_mensagem,cmd,sessao=key)
                if cmd.startswith('/help') and isinstance(resposta,str):
                    await send_screen(update,await run_experience('advanced_help',key,cmd[5:].strip(),resposta),host,edit=True)
                    return True
                await host.enviar_resposta(update,resposta,comando_executado=cmd)
            return True
        if action[0]=='lock':
            EXPERIENCE.invalidate(key);host.bloquear_assessor(update.effective_user.id)
            await query.edit_message_text(message_html('🔐 Proteção reforçada bloqueada. O uso diário continua liberado; o PIN será pedido somente em ações sensíveis.'), parse_mode="HTML")
            return True
        if action[0]=='chart':
            try:
                await host.enviar_acao_enviando_foto(update, context)
            except Exception:
                pass
        screen=await run_experience('act',key,action)
        host.marcar_acesso_seguro(update.effective_user.id)
        await send_screen(update,screen,host,edit=True)
    except ValueError as exc:
        await query.message.reply_text(message_html(str(exc)), parse_mode="HTML")
    except Exception:
        logging.exception('Falha no botão Telegram')
        await query.message.reply_text(message_html('Não consegui concluir. Confira o Histórico antes de repetir uma confirmação. Use /menu para continuar.'), parse_mode="HTML")
    return True


def clear_service_pending(key):
    for store in (svc.PENDENCIAS_CONFIRMACAO,svc.PENDENCIAS_IMPORTACAO,
                  svc.PENDENCIAS_EXPORTACAO,svc.PENDENCIAS_EXCLUSAO,
                  svc.PENDENCIAS_PAGAMENTO_FATURA,svc.PENDENCIAS_ALTERACAO):
        svc._limpar_pendencia(store,key)
