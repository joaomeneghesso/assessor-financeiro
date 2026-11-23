import re
import csv
import shutil
import uuid
import math
import logging
import calendar
import sqlite3
import unicodedata
import os
import config
from datetime import date, datetime, timedelta
import relogio
from pathlib import Path

from contextlib import closing, contextmanager
from functools import lru_cache
from consulta_cache import (
    CONTEXTO_CONSULTA as _CONTEXTO_CONSULTA,
    contexto_consulta,
    obter_ou_calcular as _consulta_cache,
    namespace as _namespace_consulta,
    chave_no_escopo as _chave_no_escopo_consulta,
)

from categorias import canonicalizar_categoria, sugerir_categoria
from faturas_competencia import (competencia_transacao, data_competencia, precisa_escolher, eh_credito)
from version import VERSION

from money import parse_money
from database import (
    DB_PATH,
    get_connection,
    inserir_transacao,
    inserir_parcelamento_atomico,
    inserir_compromisso,
    atualizar_dados_parcelamento,
    buscar_ultimas_transacoes,
    buscar_transacoes_por_mes,
    buscar_transacoes_por_competencia,
    buscar_todas_transacoes,
    buscar_saldo_mensal,
    definir_saldo_inicial_mes,
    listar_saldos_mensais,
    buscar_saldos_contas_mes,
    buscar_saldo_conta_mes,
    definir_saldo_inicial_conta_mes,
    buscar_transacao_por_id,
    apagar_ultima_transacao,
    resumo_mes,
    total_por_tipo_mes,
    total_por_categoria_mes,
    total_gastos_por_data,
    atualizar_categoria_ultima_transacao,
    apagar_transacao_por_id,
    apagar_transacoes_por_intervalo_ids,
    apagar_transacoes_por_ids,
    atualizar_categoria_por_id,
    atualizar_categoria_por_intervalo_ids,
    atualizar_conta_por_id,
    atualizar_forma_por_id,
    atualizar_valor_por_id,
    definir_meta,
    listar_metas,
    buscar_meta_por_categoria,
    apagar_meta_por_categoria,
    listar_compromissos,
    buscar_compromisso_por_id,
    buscar_checklist_status_mes,
    marcar_checklist_pagamento,
    resetar_checklist_pagamentos_mes,
    definir_checklist_data_pagamento,
    buscar_checklist_datas_pagamento_mes,
    apagar_checklist_data_pagamento,
    definir_checklist_data_pagamento_padrao,
    buscar_checklist_datas_pagamento_padrao,
    apagar_checklist_data_pagamento_padrao,
    inserir_transferencia_caixa,
    buscar_transferencias_caixa_por_mes,
    apagar_transferencia_caixa_por_id,
    inserir_fatura_movimento,
    listar_fatura_movimentos,
    buscar_fatura_movimento_por_id,
    atualizar_fatura_movimento,
    apagar_fatura_movimento,
    fatura_write_transaction,
    inserir_fatura_movimento_conn,
    registrar_auditoria,
    listar_auditoria,
    ExclusaoParcialParcelamentoError,
    parcelamentos_incompletos_conn,
    mensagem_exclusao_parcial_parcelamento,
)

from parser_financeiro import parse_mensagem, detectar_categoria_explicita
from money import parse_money_float

from assessor import (
    gerar_simulacao_transacao,
    gerar_analise_compra,
    gerar_diagnostico_financeiro,
    gerar_fechamento_semanal,
    gerar_fechamento_mensal,
)

from compromissos import (
    buscar_csv_mais_recente,
    classificar_csv,
    resumir_previa_importacao,
    importar_preview,
    resumo_pagamento_por_conta,
    detalhar_pagamento_por_conta,
    resumo_pagamento_mes_consolidado,
    resumo_contas_mes,
    listar_fixos_formatado,
    listar_compromissos_formatado,
    cadastrar_fixo_manual_formatado,
    alterar_fixo_valor,
    alterar_fixo_vencimento,
    alterar_compromisso_conta,
    alterar_compromisso_forma,
    alterar_compromisso_categoria,
    pausar_compromisso,
    reativar_compromisso,
    apagar_compromisso_formatado,
    projetar_pagamentos_mes,
    projetar_entradas_mes,
    cadastrar_entrada_fixa_formatado,
    cadastrar_entrada_avulsa_formatado,
    listar_entradas_formatado,
    listar_entradas_mes_formatado,
    alterar_entrada_valor,
    pausar_entrada,
    reativar_entrada,
    apagar_entrada_formatado,
    normalizar_conta_fatura,
    item_eh_fatura_cartao,
    TIPOS_LIQUIDACAO_FATURA,
    item_eh_liquidacao_fatura,
    remover_liquidacoes_fatura,
    total_movimentos_fatura,
    calcular_fatura_unificada,
)




def _normalizar_forma_fixo_guiado(valor: str | None) -> str:
    texto = normalizar_texto(valor or "")
    aliases = {
        "cartao": "cr\u00e9dito", "cartao de credito": "cr\u00e9dito", "credito": "cr\u00e9dito",
        "debito": "d\u00e9bito", "transferencia": "transfer\u00eancia",
        "pix": "pix", "dinheiro": "dinheiro", "boleto": "boleto",
    }
    forma = aliases.get(texto, texto)
    if forma not in {"pix", "d\u00e9bito", "cr\u00e9dito", "dinheiro", "transfer\u00eancia", "boleto"}:
        raise ValueError("Escolha Pix, d\u00e9bito, cr\u00e9dito, dinheiro, transfer\u00eancia ou boleto.")
    return forma


def _mes_para_inicio_fixo(valor: str) -> str:
    texto = str(valor or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}", texto):
        try:
            return date.fromisoformat(texto + "-01").isoformat()
        except ValueError as exc:
            raise ValueError("M\u00eas inicial inv\u00e1lido. Use AAAA-MM.") from exc
    try:
        data = date.fromisoformat(texto)
    except ValueError as exc:
        raise ValueError("M\u00eas inicial inv\u00e1lido. Use AAAA-MM.") from exc
    return data.replace(day=1).isoformat()


def _mes_para_fim_fixo(valor: str | None) -> str | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    if not re.fullmatch(r"\d{4}-\d{2}", texto):
        raise ValueError("M\u00eas final inv\u00e1lido. Use AAAA-MM ou escolha sem t\u00e9rmino.")
    try:
        base = date.fromisoformat(texto + "-01")
    except ValueError as exc:
        raise ValueError("M\u00eas final inv\u00e1lido. Use AAAA-MM.") from exc
    return date(base.year, base.month, calendar.monthrange(base.year, base.month)[1]).isoformat()


def _fixo_guiado_duplicado(dados: dict):
    inicio = dados["data_inicio"]
    fim = dados.get("data_fim") or "9999-12-31"
    nome = normalizar_texto(dados["nome"])
    conta = normalizar_texto(dados["conta_pagamento"])
    forma = normalizar_texto(dados["forma_pagamento"])
    for row in listar_compromissos(tipo="fixo", somente_ativos=True):
        existente_inicio = row["data_inicio"] or "0001-01-01"
        existente_fim = row["data_fim"] or "9999-12-31"
        sobrepoe = existente_inicio <= fim and existente_fim >= inicio
        if not sobrepoe:
            continue
        if (
            normalizar_texto(row["nome"]) == nome
            and normalizar_texto(row["conta_pagamento"]) == conta
            and normalizar_texto(row["forma_pagamento"]) == forma
            and abs(float(row["valor"] or 0) - float(dados["valor"])) < 0.005
            and int(row["dia_vencimento"] or 0) == int(dados["dia_vencimento"])
        ):
            return dict(row)
    return None


def cadastrar_fixo_guiado(dados: dict, sessao: str | None = None):
    """Cadastra um fixo com campos expl\u00edcitos; n\u00e3o cria transa\u00e7\u00e3o/despesa."""
    nome = str(dados.get("nome") or "").strip()
    if not nome or len(nome) > 160:
        raise ValueError("Informe um nome de at\u00e9 160 caracteres.")
    try:
        valor = float(parse_money_float(dados.get("valor")))
    except Exception as exc:
        raise ValueError("Informe um valor positivo, como 12,95.") from exc
    if valor <= 0 or valor > 100000000:
        raise ValueError("Informe um valor positivo de at\u00e9 R$ 100 milh\u00f5es.")
    categoria = canonicalizar_categoria(str(dados.get("categoria") or "Outros").strip(), "Outros")
    forma = _normalizar_forma_fixo_guiado(dados.get("forma_pagamento"))
    conta = str(dados.get("conta_pagamento") or "").strip()
    if not conta or len(conta) > 80:
        raise ValueError("Informe uma conta/cart\u00e3o com at\u00e9 80 caracteres.")
    try:
        dia = int(dados.get("dia_vencimento"))
    except Exception as exc:
        raise ValueError("Informe um dia de vencimento entre 1 e 31.") from exc
    if dia < 1 or dia > 31:
        raise ValueError("Informe um dia de vencimento entre 1 e 31.")
    data_inicio = _mes_para_inicio_fixo(str(dados.get("data_inicio") or ""))
    data_fim = _mes_para_fim_fixo(dados.get("data_fim"))
    if data_fim and data_fim < data_inicio:
        raise ValueError("O t\u00e9rmino n\u00e3o pode ser anterior ao in\u00edcio.")

    compromisso = {
        "tipo": "fixo", "nome": nome, "categoria": categoria,
        "conta_pagamento": conta, "forma_pagamento": forma, "valor": valor,
        "dia_vencimento": dia, "data_inicio": data_inicio, "data_fim": data_fim,
        "parcelas_total": None, "ativo": True, "origem": "telegram:fixo_guiado_v403",
        "observacao": "Fixo cadastrado pelo fluxo guiado nativo do Telegram.",
    }
    mes_inicio = data_inicio[:7]
    chave = dados.get('_confirmacao_id')
    usuario = str(sessao or 'telegram')
    import json
    pedido = dict(compromisso)
    with fatura_write_transaction() as conn:
        conn.row_factory = sqlite3.Row
        evento = conn.execute(
            "SELECT usuario_sessao,dados_depois FROM auditoria_eventos "
            "WHERE entidade='fixo_confirmacao' AND entidade_id=? AND operacao='confirmado' ORDER BY id LIMIT 1",
            (str(chave),)).fetchone() if chave else None
        if evento:
            salvo = json.loads(evento['dados_depois'])
            if evento['usuario_sessao'] != usuario or salvo['pedido'] != pedido:
                raise ValueError('A confirmação não corresponde ao fixo revisado nesta sessão.')
            result = dict(salvo['resultado'], repetido=True)
        else:
            # A verificação e a inserção ficam sob o MESMO bloqueio de escrita.
            duplicado = _fixo_guiado_duplicado(compromisso)
            if duplicado:
                raise ValueError(f"Já existe um fixo equivalente ativo: #C{duplicado['id']} · {duplicado['nome']}. Revise esse cadastro antes de criar outro.")
            antes_fatura = None
            if forma == 'crédito':
                antes_fatura = float(calcular_fatura_unificada(mes_inicio, conta, somente_cartao=True)['saldo_restante'] or 0)
            agora = relogio.agora().isoformat(timespec='seconds')
            campos = ('tipo','nome','categoria','conta_pagamento','forma_pagamento','valor',
                      'dia_vencimento','data_inicio','data_fim','parcelas_total','ativo',
                      'origem','observacao','criado_em','atualizado_em')
            valores = dict(compromisso, criado_em=agora, atualizado_em=agora)
            ident = conn.execute('INSERT INTO compromissos ('+','.join(campos)+') VALUES ('
                                 +','.join('?' for _ in campos)+')', [valores.get(k) for k in campos]).lastrowid
            compromisso['id'] = ident
            registrar_auditoria('compromissos', ident, 'criar_fixo_guiado', None, compromisso,
                                'telegram', usuario, conn=conn)
            result = {'compromisso':compromisso, 'mes_inicio':mes_inicio,
                      'fatura_antes':antes_fatura, 'fatura_depois':None, 'repetido':False}
            if chave:
                registrar_auditoria('fixo_confirmacao',str(chave),'confirmado',None,
                                    {'pedido':pedido,'resultado':result},'telegram',usuario,conn=conn)
    # Depois do commit, uma falha de consulta NÃO deve ser reportada como falha
    # de gravação nem induzir a repetição de um cadastro já salvo.
    if forma == 'crédito':
        try:
            result['fatura_depois'] = float(calcular_fatura_unificada(mes_inicio, conta, somente_cartao=True)['saldo_restante'] or 0)
        except Exception:
            logging.exception('Fixo salvo; resumo da fatura indisponível após a confirmação')
            result['resumo_indisponivel'] = True
    return result

# Pastas ancoradas no projeto (config.py); nomes mantidos como apelidos patcháveis.
EXPORTS_DIR = config.EXPORTS_DIR
BACKUPS_DIR = config.BACKUPS_DIR
PROCESS_STARTED_AT = relogio.agora()
DASHBOARDS_DIR = config.DASHBOARDS_DIR

_LOG_CALCULOS = logging.getLogger("assessor.calculos")

PENDENCIAS_CONFIRMACAO = {}
PENDENCIAS_IMPORTACAO = {}
PENDENCIAS_EXPORTACAO = {}
PENDENCIAS_EXCLUSAO = {}
PENDENCIAS_PAGAMENTO_FATURA = {}
PENDENCIAS_ALTERACAO = {}
PENDENCIA_TTL_SEGUNDOS = 600


def _chave_sessao(chave=None):
    return str(chave or "__local__")


def _definir_pendencia(store: dict, chave, valor):
    store[_chave_sessao(chave)] = {"valor": valor, "criado_em": relogio.agora()}


def _obter_pendencia(store: dict, chave):
    item = store.get(_chave_sessao(chave))
    if not item:
        return None
    criado_em = item.get("criado_em")
    if criado_em and (relogio.agora() - criado_em).total_seconds() > PENDENCIA_TTL_SEGUNDOS:
        store.pop(_chave_sessao(chave), None)
        return None
    return item.get("valor")


def _limpar_pendencia(store: dict, chave):
    store.pop(_chave_sessao(chave), None)


def assinatura_pendencia(tipo: str, chave):
    """Identifica a prévia pendente atual (fatura, exclusão ou importação).

    Os botões de uma prévia carregam esta assinatura: tocar no botão de uma
    prévia antiga, depois que outra a substituiu, não confirma a mais nova.
    Devolve None quando não há pendência.
    """
    import hashlib
    import json

    store = {"fatura": PENDENCIAS_PAGAMENTO_FATURA, "exclusao": PENDENCIAS_EXCLUSAO,
             "importacao": PENDENCIAS_IMPORTACAO, "alteracao": PENDENCIAS_ALTERACAO}.get(tipo)
    if store is None or _obter_pendencia(store, chave) is None:
        return None
    item = store.get(_chave_sessao(chave)) or {}
    bruto = json.dumps({"valor": item.get("valor"), "criado_em": item.get("criado_em")},
                       sort_keys=True, default=str)
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:12]


def normalizar_valor_monetario(valor: float, tolerancia: float = 0.005):
    """Evita exibir resíduos de ponto flutuante como -R$ 0,00."""
    valor = float(valor or 0.0)
    return 0.0 if abs(valor) < tolerancia else valor


def formatar_moeda(valor: float):
    # Regra única (Decimal HALF_UP, sem -0,00) compartilhada com compromissos e
    # com o money() da UX, que só troca o sinal para "−R$" (D5/D6).
    from money import formatar_brl
    return formatar_brl(valor)


MESES_PT = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}


def formatar_ano_mes_visual(ano_mes: str):
    match = re.match(r"^(20\d{2})-(\d{2})$", str(ano_mes or ""))
    if not match:
        return ano_mes
    ano = int(match.group(1))
    mes = int(match.group(2))
    if mes < 1 or mes > 12:
        return ano_mes
    return f"{MESES_PT[mes]}/{ano}"


def formatar_data_visual(data_texto: str):
    match = re.match(r"^(20\d{2})-(\d{2})-(\d{2})$", str(data_texto or ""))
    if not match:
        return data_texto
    ano = int(match.group(1))
    mes = int(match.group(2))
    dia = int(match.group(3))
    if mes < 1 or mes > 12:
        return data_texto
    return f"{dia:02d}/{MESES_PT[mes]}/{ano}"


def validar_data_iso(data_texto: str):
    data_texto = str(data_texto or "").strip()

    try:
        data_obj = date.fromisoformat(data_texto)
    except ValueError:
        return None

    if data_obj.year < 2000 or data_obj.year > 2100:
        return None

    return data_obj.isoformat()


def extrair_periodo_exportacao(texto: str):
    texto = (texto or "").lower().strip()

    datas = re.findall(r"20\d{2}-\d{2}-\d{2}", texto)
    if len(datas) >= 2:
        data_inicio = validar_data_iso(datas[0])
        data_fim = validar_data_iso(datas[1])

        if not data_inicio or not data_fim:
            return None

        if data_inicio > data_fim:
            data_inicio, data_fim = data_fim, data_inicio

        return data_inicio, data_fim

    return None


LIMITE_EXPORTACAO_SEM_PIN_DIAS = 366
_EXPORTACAO_TOTAL = {"tudo", "base inteira", "completo", "completa"}


def exportacao_exige_pin(texto, sessao=None):
    """True se o texto pede exportar mais que o limite sem PIN (ou a base inteira).

    Cobre o comando direto ("exportar csv 2000-01-01 2100-12-31") e a resposta ao
    fluxo guiado de período ("tudo" ou duas datas), que não repete o comando.
    """
    clean = re.sub(r"\s+", " ", texto or "").lower().strip()
    m = re.match(r"^exportar csv\s+(.+)$", clean)
    if m:
        candidato = m.group(1).strip()
    elif _obter_pendencia(PENDENCIAS_EXPORTACAO, sessao):
        candidato = clean
    else:
        return False
    if candidato in _EXPORTACAO_TOTAL:
        return True
    periodo = extrair_periodo_exportacao(candidato)
    if periodo:
        dias = (date.fromisoformat(periodo[1]) - date.fromisoformat(periodo[0])).days
        return dias > LIMITE_EXPORTACAO_SEM_PIN_DIAS
    return False


def formatar_periodo_visual(data_inicio: str, data_fim: str):
    return f"{formatar_data_visual(data_inicio)} a {formatar_data_visual(data_fim)}"


def iterar_ano_mes_periodo(data_inicio: str, data_fim: str):
    inicio = date.fromisoformat(data_inicio).replace(day=1)
    fim = date.fromisoformat(data_fim).replace(day=1)

    atual = inicio
    while atual <= fim:
        yield atual.strftime("%Y-%m")

        if atual.month == 12:
            atual = date(atual.year + 1, 1, 1)
        else:
            atual = date(atual.year, atual.month + 1, 1)




def sanitizar_celula_csv(valor):
    """Neutraliza fórmulas ao abrir o CSV em Excel/LibreOffice."""
    if valor is None:
        return ""
    texto = str(valor)
    if texto.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + texto
    return texto

def montar_linha_exportacao_unificada(item: dict):
    origem = item.get("origem") or "desconhecida"
    prefixo_id = "T"

    if origem == "compromisso":
        prefixo_id = "C"
    elif origem == "entrada":
        prefixo_id = "E"
    elif origem == "transacao":
        prefixo_id = "T"

    valor = item.get("valor") or 0

    linha = [
        origem,
        f"{prefixo_id}{item.get('id')}",
        item.get("data"),
        item.get("tipo"),
        f"{valor:.2f}".replace(".", ","),
        item.get("categoria") or "",
        item.get("nome") or item.get("descricao") or "",
        item.get("conta_pagamento") or item.get("conta") or "",
        item.get("forma_pagamento") or "",
        item.get("parcela_atual") or "",
        item.get("parcelas_total") or "",
        item.get("ativo"),
        item.get("data_compra") or "",
        item.get("competencia_fatura") or "",
    ]
    return [sanitizar_celula_csv(valor) for valor in linha]


def buscar_itens_financeiros_periodo(data_inicio: str, data_fim: str):
    itens_por_chave = {}

    for ano_mes in iterar_ano_mes_periodo(data_inicio, data_fim):
        for item in projetar_entradas_mes(ano_mes, incluir_transacoes=True):
            data_item = item.get("data")
            if data_item and data_inicio <= data_item <= data_fim:
                chave = (
                    item.get("origem"),
                    item.get("id"),
                    item.get("data"),
                    item.get("tipo"),
                    item.get("parcela_atual"),
                    "entrada",
                )
                itens_por_chave[chave] = item

        for item in projetar_pagamentos_mes(ano_mes, incluir_transacoes=True):
            data_item = item.get("data")
            if data_item and data_inicio <= data_item <= data_fim:
                chave = (
                    item.get("origem"),
                    item.get("id"),
                    item.get("data"),
                    item.get("tipo"),
                    item.get("parcela_atual"),
                    "saida",
                )
                itens_por_chave[chave] = item

    return sorted(
        itens_por_chave.values(),
        key=lambda item: (
            item.get("data") or "",
            item.get("origem") or "",
            str(item.get("id") or ""),
            str(item.get("parcela_atual") or ""),
        )
    )


def descobrir_periodo_base_exportavel():
    datas = []

    for t in buscar_todas_transacoes():
        if t["data"]:
            datas.append(t["data"])
            # V39: exportar tudo tambem deve alcancar a ultima fatura escolhida.
            datas.append(data_competencia(t))

    for c in listar_compromissos(somente_ativos=False):
        if c["data_inicio"]:
            datas.append(c["data_inicio"])
        if c["data_fim"]:
            datas.append(c["data_fim"])

    if not datas:
        return None

    data_inicio = min(datas)
    data_fim = max(datas)

    # Se houver fixos/entradas sem fim, evita exportação infinita.
    # Exporta até 12 meses depois de hoje quando isso for maior que o fim conhecido.
    tem_recorrente_sem_fim = any(
        c["ativo"] and c["tipo"] in ["fixo", "entrada_fixa"] and not c["data_fim"]
        for c in listar_compromissos(somente_ativos=False)
    )

    if tem_recorrente_sem_fim:
        hoje = relogio.hoje(date)
        limite_recorrente = date(hoje.year + 1, hoje.month, 1).isoformat()
        if limite_recorrente > data_fim:
            data_fim = limite_recorrente

    return data_inicio, data_fim


def formatar_percentual(valor: float, total: float):
    if not total:
        return "0,0%"
    return f"{(valor / total) * 100:.1f}%".replace(".", ",")


def formatar_barra_percentual(valor: float, total: float, tamanho: int = 10):
    if not total or valor <= 0:
        preenchidos = 0
    else:
        preenchidos = round(min(max(valor / total, 0), 1) * tamanho)
    return "█" * preenchidos + "░" * (tamanho - preenchidos)


def formatar_sinal_moeda(valor: float):
    valor = normalizar_valor_monetario(valor)
    sinal = "+" if valor >= 0 else "-"
    return f"{sinal}{formatar_moeda(abs(valor))}"


def formatar_status_saldo(valor: float):
    valor = normalizar_valor_monetario(valor)
    if valor < 0:
        return f"🔴 {formatar_sinal_moeda(valor)}"
    if valor == 0:
        return f"🟡 {formatar_moeda(valor)}"
    return f"🟢 {formatar_sinal_moeda(valor)}"


def linha_valor(rotulo: str, valor: float, largura: int = 24):
    return f"│ {rotulo:<{largura}} {formatar_moeda(valor):>14}"


def linha_status_valor(rotulo: str, valor: float, largura: int = 24):
    return f"│ {rotulo:<{largura}} {formatar_status_saldo(valor):>14}"


def linha_sinal_valor(rotulo: str, valor: float, largura: int = 24):
    sinal = "+" if valor >= 0 else "-"
    return f"│ {rotulo:<{largura}} {sinal}{formatar_moeda(abs(valor)):>13}"


def bloco_total(titulo: str, linhas: list[str]):
    return "\n".join([f"┌ {titulo}", *linhas, "└"])


def formatar_item_card(identificador: str, data_item: str, valor: float, categoria: str, nome: str, conta: str | None = None, forma: str | None = None, extra: str | None = None, tipo_valor: str = "saida"):
    valor_formatado = formatar_moeda(valor)
    if tipo_valor == "entrada":
        valor_formatado = "+" + valor_formatado
        icone_valor = "💰"
    else:
        icone_valor = "💸"

    linhas = [
        f"┌ {identificador} · {nome}",
        f"│ 📅 {formatar_data_visual(data_item)}",
        f"│ {icone_valor} {valor_formatado}",
        f"│ 🏷 {categoria}",
    ]

    if conta:
        linhas.append(f"│ 🏦 {conta}")

    if forma and forma != "não informada":
        linhas.append(f"│ 💳 {forma}")

    if extra:
        linhas.append(f"│ 🔎 {extra}")

    linhas.append("└")
    return "\n".join(linhas)



def formatar_tamanho_bytes(tamanho: int):
    if tamanho < 1024:
        return f"{tamanho} bytes"
    if tamanho < 1024 * 1024:
        return f"{tamanho / 1024:.1f} KB"
    return f"{tamanho / (1024 * 1024):.1f} MB"


def somar_meses(data_base: date, meses: int):
    mes_total = data_base.month - 1 + meses
    ano = data_base.year + mes_total // 12
    mes = mes_total % 12 + 1
    ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
    dia = min(data_base.day, ultimo_dia_mes)
    return date(ano, mes, dia)


def validar_ano_mes(texto: str):
    if not isinstance(texto, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", texto):
        return None

    ano, mes = texto.split("-")
    mes_int = int(mes)

    if int(ano) < 1 or mes_int < 1 or mes_int > 12:
        return None

    return f"{ano}-{mes}"


def converter_valor_texto(valor_texto: str):
    try:
        return parse_money_float(valor_texto)
    except (TypeError, ValueError):
        return None


def row_get(row, campo, padrao=None):
    try:
        if campo in row.keys():
            return row[campo]
    except Exception:
        pass
    return padrao



def normalizar_texto(texto: str | None):
    if texto is None:
        return ""
    return _normalizar_texto_str(str(texto))


@lru_cache(maxsize=8192)
def _normalizar_texto_str(texto: str):
    # Função pura de texto: memoizada (muito chamada no cálculo de saldo).
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"\s+", " ", texto)
    return texto


def obter_nome_item(item: dict):
    return (
        item.get("nome")
        or item.get("descricao")
        or item.get("mensagem_original")
        or "Sem descrição"
    )


def obter_conta_item(item: dict):
    return (
        item.get("conta_pagamento")
        or item.get("conta")
        or "Não informada"
    )


def obter_forma_item(item: dict):
    return (
        item.get("forma_pagamento")
        or item.get("forma")
        or "não informada"
    )


def obter_categoria_item(item: dict):
    return canonicalizar_categoria(item.get("categoria"), "Outros")


def obter_id_item_formatado(item: dict):
    item_id = item.get("id")

    if item_id is None:
        return "#?"

    if item.get("origem") == "entrada":
        return f"#E{item_id}"

    if item.get("origem") == "compromisso":
        return f"#C{item_id}"

    return f"#{item_id}"


def ordenar_itens_agenda(itens: list):
    return sorted(
        itens,
        key=lambda item: (
            item.get("data") or "9999-12-31",
            normalizar_texto(obter_conta_item(item)),
            normalizar_texto(obter_categoria_item(item)),
            normalizar_texto(obter_nome_item(item)),
            item.get("id") or 0,
        )
    )


def formatar_linha_item_agenda(item: dict):
    identificador = obter_id_item_formatado(item)
    data_item = item.get("data") or "sem data"
    valor = item.get("valor") or 0
    conta = obter_conta_item(item)
    forma = obter_forma_item(item)
    categoria = obter_categoria_item(item)
    nome = obter_nome_item(item)

    extra = None
    if item.get("parcela_atual") and item.get("parcelas_total"):
        extra = f"Parcela {item['parcela_atual']}/{item['parcelas_total']}"

    tipo_valor = "entrada" if item.get("origem") == "entrada" or str(item.get("tipo", "")).startswith("receita") or str(item.get("tipo", "")).startswith("entrada") else "saida"

    return formatar_item_card(
        identificador=identificador,
        data_item=data_item,
        valor=valor,
        categoria=categoria,
        nome=nome,
        conta=conta,
        forma=forma,
        extra=extra,
        tipo_valor=tipo_valor,
    )


def agrupar_itens_por_campo(itens: list, campo_func):
    grupos = {}

    for item in itens:
        chave = campo_func(item) or "Não informado"
        grupos[chave] = grupos.get(chave, 0) + (item.get("valor") or 0)

    return sorted(grupos.items(), key=lambda kv: kv[1], reverse=True)


def filtrar_itens_por_categoria(itens: list, categoria: str):
    categoria_normalizada = normalizar_texto(categoria)

    return [
        item for item in itens
        if normalizar_texto(obter_categoria_item(item)) == categoria_normalizada
    ]


def listar_categorias_mes(ano_mes: str):
    # Pagamento de fatura não é gasto de categoria (B1); estornos seguem abatendo.
    itens = remover_liquidacoes_fatura(projetar_pagamentos_mes(ano_mes, incluir_transacoes=True))

    if not itens:
        return f"🏷 Categorias — {formatar_ano_mes_visual(ano_mes)}\n\nNão encontrei lançamentos ou agenda financeira para este mês."

    grupos = agrupar_itens_por_campo(itens, obter_categoria_item)
    total = sum(valor for _, valor in grupos)

    linhas = [
        f"🏷 Categorias — {formatar_ano_mes_visual(ano_mes)}",
        "",
        bloco_total("Visão geral", [
            linha_valor("Total previsto", total),
        ]),
        "",
        "Ranking de categorias:"
    ]

    for indice, (categoria, valor) in enumerate(grupos, start=1):
        linhas.extend([
            "",
            f"{indice:02d}. {categoria}",
            f"    {formatar_moeda(valor)} · {formatar_percentual(valor, total)}",
            f"    {formatar_barra_percentual(valor, total)}",
        ])

    linhas.extend(["", "Toque em uma categoria nos botões abaixo para detalhar."])

    return "\n".join(linhas)


def listar_formas_mes(ano_mes: str):
    itens = projetar_pagamentos_mes(ano_mes, incluir_transacoes=True)

    if not itens:
        return f"💳 Formas — {formatar_ano_mes_visual(ano_mes)}\n\nNão encontrei lançamentos ou agenda financeira para este mês."

    grupos = agrupar_itens_por_campo(itens, obter_forma_item)
    total = sum(valor for _, valor in grupos)

    linhas = [
        f"💳 Formas de pagamento — {formatar_ano_mes_visual(ano_mes)}",
        "",
        bloco_total("Visão geral", [
            linha_valor("Total previsto", total),
        ]),
        "",
        "Ranking de formas:"
    ]

    for indice, (forma, valor) in enumerate(grupos, start=1):
        linhas.extend([
            "",
            f"{indice:02d}. {forma}",
            f"    {formatar_moeda(valor)} · {formatar_percentual(valor, total)}",
            f"    {formatar_barra_percentual(valor, total)}",
        ])

    return "\n".join(linhas)


def detalhar_mes(ano_mes: str):
    pagamentos = ordenar_itens_agenda(projetar_pagamentos_mes(ano_mes, incluir_transacoes=True))
    entradas = ordenar_itens_agenda(projetar_entradas_mes(ano_mes, incluir_transacoes=True))

    if not pagamentos and not entradas:
        return f"📋 Detalhamento — {formatar_ano_mes_visual(ano_mes)}\n\nNão encontrei entradas, lançamentos ou agenda financeira para este mês."

    dados = obter_metricas_resultado_mes(ano_mes)

    total_pagamentos = sum(item.get("valor") or 0 for item in pagamentos)

    por_conta = agrupar_itens_por_campo(pagamentos, obter_conta_item)
    por_categoria = agrupar_itens_por_campo(pagamentos, obter_categoria_item)

    linhas = [
        f"📋 Detalhamento — {formatar_ano_mes_visual(ano_mes)}",
        "",
        bloco_resultado_mes(dados),
        "",
        bloco_caixa_acumulado(dados),
    ]

    if entradas:
        linhas.extend(["", "💰 Entradas"])
        for item in entradas:
            linhas.extend(["", formatar_linha_item_agenda(item)])

    if pagamentos:
        linhas.extend(["", "🏦 Saídas por conta/meio"])
        for conta, valor in por_conta:
            linhas.append(f"- {conta}: {formatar_moeda(valor)} · {formatar_percentual(valor, total_pagamentos)}")

        linhas.extend(["", "🏷 Saídas por categoria"])
        for categoria, valor in por_categoria:
            linhas.append(f"- {categoria}: {formatar_moeda(valor)} · {formatar_percentual(valor, total_pagamentos)}")

        linhas.extend(["", "💸 Saídas"])
        for item in pagamentos:
            linhas.extend(["", formatar_linha_item_agenda(item)])

    return "\n".join(linhas)


def avisos_fixos_fora_do_mes(categoria, ano_mes):
    from compromissos import compromisso_ocorre_no_mes
    linhas=[]
    for c in listar_compromissos(tipo='fixo', somente_ativos=True):
        if normalizar_texto(canonicalizar_categoria(c['categoria'])) != normalizar_texto(canonicalizar_categoria(categoria)):
            continue
        if not compromisso_ocorre_no_mes(c,ano_mes):
            linhas.append(f"#C{c['id']} · {c['nome']} — início {c['data_inicio']}; término {c['data_fim'] or 'sem término'}.")
    return (['', 'Fixos ativos fora da vigência deste mês (não somados):']+linhas) if linhas else []


def detalhar_categoria_mes(categoria: str, ano_mes: str):
    # Mesmo universo de "categorias": sem pagamentos de fatura (B1).
    itens_mes = remover_liquidacoes_fatura(projetar_pagamentos_mes(ano_mes, incluir_transacoes=True))
    itens = ordenar_itens_agenda(filtrar_itens_por_categoria(itens_mes, categoria))

    if not itens:
        categorias_disponiveis = agrupar_itens_por_campo(itens_mes, obter_categoria_item)

        linhas = [
            f"📋 {categoria.title()} — {formatar_ano_mes_visual(ano_mes)}",
            "",
            "Não encontrei itens nessa categoria."
        ]

        if categorias_disponiveis:
            linhas.extend(["", "Categorias disponíveis:"])
            for categoria_disponivel, valor in categorias_disponiveis:
                linhas.append(f"- {categoria_disponivel}: {formatar_moeda(valor)}")

        return "\n".join(linhas + avisos_fixos_fora_do_mes(categoria, ano_mes))

    categoria_exibicao = obter_categoria_item(itens[0])
    total = sum(item.get("valor") or 0 for item in itens)
    por_conta = agrupar_itens_por_campo(itens, obter_conta_item)

    linhas = [
        f"📋 {categoria_exibicao} — {formatar_ano_mes_visual(ano_mes)}",
        "",
        bloco_total("Resumo da categoria", [
            linha_valor("Total", total),
            f"│ {'Itens':<24} {len(itens):>14}",
        ]),
        "",
        "🏦 Por conta/meio"
    ]

    for conta, valor in por_conta:
        linhas.append(f"- {conta}: {formatar_moeda(valor)} · {formatar_percentual(valor, total)}")

    linhas.extend(["", "Itens"])

    for item in itens:
        linhas.extend(["", formatar_linha_item_agenda(item)])

    return "\n".join(linhas + avisos_fixos_fora_do_mes(categoria, ano_mes))


def detalhar_categoria_futuro(categoria: str, meses: int = 6):
    hoje = relogio.hoje(date)
    categoria_normalizada = normalizar_texto(categoria)

    linhas = [
        f"📆 {categoria.title()} nos próximos meses",
        ""
    ]

    encontrou = False

    for i in range(0, meses):
        ano_mes = somar_meses(hoje, i).strftime("%Y-%m")
        itens_mes = projetar_pagamentos_mes(ano_mes, incluir_transacoes=True)
        itens = ordenar_itens_agenda([
            item for item in itens_mes
            if normalizar_texto(obter_categoria_item(item)) == categoria_normalizada
        ])

        if not itens:
            continue

        encontrou = True
        total = sum(item.get("valor") or 0 for item in itens)

        marcador = " — mês atual" if ano_mes == hoje.strftime("%Y-%m") else ""
        linhas.append(f"{ano_mes}{marcador}: {formatar_moeda(total)}")

        for item in itens:
            nome = obter_nome_item(item)
            conta = obter_conta_item(item)
            valor = item.get("valor") or 0

            parcela = ""
            if item.get("parcela_atual") and item.get("parcelas_total"):
                parcela = f" ({item['parcela_atual']}/{item['parcelas_total']})"

            linhas.append(f"- {nome}: {formatar_moeda(valor)} | {conta}{parcela}")

        linhas.append("")

    if not encontrou:
        return f"Não encontrei itens de {categoria.title()} nos próximos {meses} meses."

    linhas.append("Para detalhar um mês específico, envie:")
    linhas.append(f"detalhar categoria {categoria} {hoje.strftime('%Y-%m')}")

    return "\n".join(linhas).strip()


def limpar_conta_entrada(conta: str | None):
    if not conta:
        return None

    conta = conta.strip()
    conta = re.sub(r"^(no|na|nos|nas|pelo|pela|com|via|em)\s+", "", conta).strip()
    conta = re.sub(r"^(conta|banco)\s+", "", conta).strip()

    return conta or None


def parsear_comando_entrada_fixa(texto_limpo: str):
    prefixos = [
        "nova entrada fixa ",
        "entrada fixa ",
        "nova receita fixa ",
        "receita fixa ",
        "cadastrar entrada fixa ",
    ]

    corpo = None

    for prefixo in prefixos:
        if texto_limpo.startswith(prefixo):
            corpo = texto_limpo[len(prefixo):].strip()
            break

    if not corpo:
        return None

    dia = None
    match_dia = re.search(r"(?:\s+|^)(?:dia|recebimento)\s+(\d{1,2})\s*$", corpo)
    if match_dia:
        dia = int(match_dia.group(1))
        corpo = corpo[:match_dia.start()].strip()

    match_valor = re.search(r"(?<!\d)(\d+(?:[.,]\d{1,2})?)(?!\d)", corpo)

    if not match_valor:
        return {
            "erro": "valor",
            "exemplo": "nova entrada fixa salário 3800 dia 5"
        }

    nome = corpo[:match_valor.start()].strip()
    valor_texto = match_valor.group(1)
    conta = corpo[match_valor.end():].strip()
    conta = limpar_conta_entrada(conta)
    valor = converter_valor_texto(valor_texto)

    if not nome:
        return {
            "erro": "nome",
            "exemplo": "nova entrada fixa salário 3800 dia 5"
        }

    return {
        "nome": nome,
        "valor": valor,
        "dia": dia,
        "conta": conta,
    }


def parsear_comando_entrada_avulsa(texto_limpo: str):
    prefixos = [
        "nova entrada ",
        "entrada ",
        "nova receita ",
        "receita ",
    ]

    corpo = None
    prefixo_usado = ""

    for prefixo in prefixos:
        if texto_limpo.startswith(prefixo):
            corpo = texto_limpo[len(prefixo):].strip()
            prefixo_usado = prefixo
            break

    if not corpo:
        return None

    # Não confundir "entrada fixa" com entrada avulsa.
    if corpo.startswith("fixa "):
        return None

    match_data = re.search(r"\s+em\s+(\d{4}-\d{2}-\d{2})\s*$", corpo)
    if not match_data:
        # "nova entrada prevista freela 800 dia 20" não pode cair no parser de
        # despesa (gravava uma DESPESA no mês passado, sem prévia). Entrada sem a
        # data completa é recusada sem gravar nada. "receita ..." solto continua
        # livre (ex.: "receita federal 300" é uma despesa legítima), salvo quando
        # a frase é claramente uma entrada prevista.
        claramente_entrada = (
            prefixo_usado in ("nova entrada ", "entrada ", "nova receita ")
            or re.match(r"^previst[ao]s?\b", corpo)
            or re.search(r"\bdia\s+\d{1,2}\s*$", corpo)
        )
        if claramente_entrada:
            return {
                "erro": "data",
                "exemplo": ("entrada freela 800 em 2026-11-20 (data completa, AAAA-MM-DD). "
                            "Nada foi registrado. Se o dinheiro já entrou, use ➕ Registrar → + Registrar entrada."),
            }
        return None

    data_entrada = match_data.group(1)
    corpo = corpo[:match_data.start()].strip()

    match_valor = re.search(r"(?<!\d)(\d+(?:[.,]\d{1,2})?)(?!\d)", corpo)

    if not match_valor:
        return {
            "erro": "valor",
            "exemplo": "entrada décimo terceiro 1900,00 em 2026-12-20"
        }

    nome = corpo[:match_valor.start()].strip()
    valor_texto = match_valor.group(1)
    conta = corpo[match_valor.end():].strip()
    conta = limpar_conta_entrada(conta)
    valor = converter_valor_texto(valor_texto)

    if not nome:
        return {
            "erro": "nome",
            "exemplo": "entrada décimo terceiro 1900,00 em 2026-12-20"
        }

    return {
        "nome": nome,
        "valor": valor,
        "data": data_entrada,
        "conta": conta,
    }


def limpar_conta_fixo(conta: str | None):
    if not conta:
        return None

    conta = conta.strip()
    conta = re.sub(r"^(no|na|nos|nas|pelo|pela|com|via)\s+", "", conta).strip()
    conta = re.sub(r"^(cartao|cartão)\s+", "", conta).strip()
    conta = re.sub(r"^(do|da)\s+(cartao|cartão)\s+", "", conta).strip()

    return conta or None


def parsear_comando_novo_fixo(texto_limpo: str):
    prefixos = [
        "novo fixo ",
        "fixo novo ",
        "cadastrar fixo ",
        "adicionar fixo ",
        "novo "
    ]

    corpo = None

    for prefixo in prefixos:
        if texto_limpo.startswith(prefixo):
            corpo = texto_limpo[len(prefixo):].strip()
            break

    if not corpo:
        return None

    # Segurança: quando o usuário usa apenas "novo ...", só tratamos como fixo
    # se houver um dia de vencimento ou uma palavra típica de conta fixa.
    if texto_limpo.startswith("novo ") and not texto_limpo.startswith("novo fixo "):
        palavras_fixo = [
            "agua", "água", "luz", "energia", "internet", "condominio",
            "condomínio", "iptu", "aluguel", "academia", "icloud", "youtube",
            "netflix", "spotify", "plano", "celular", "iptv"
        ]

        tem_dia = re.search(r"\b(dia|vencimento)\s+\d{1,2}\b", corpo) is not None
        tem_palavra_fixo = any(palavra in corpo for palavra in palavras_fixo)

        if not tem_dia and not tem_palavra_fixo:
            return None

    dia = None

    match_dia = re.search(r"(?:\s+|^)(?:dia|vencimento)\s+(\d{1,2})\s*$", corpo)
    if match_dia:
        dia = int(match_dia.group(1))
        corpo = corpo[:match_dia.start()].strip()

    match_valor = re.search(r"(?<!\d)(\d+(?:[.,]\d{1,2})?)(?!\d)", corpo)

    if not match_valor:
        return {
            "erro": "valor",
            "exemplo": "novo fixo água 150 no pix dia 25"
        }

    nome = corpo[:match_valor.start()].strip()
    valor_texto = match_valor.group(1)
    conta = corpo[match_valor.end():].strip()

    conta = limpar_conta_fixo(conta)
    valor = converter_valor_texto(valor_texto)

    if not nome:
        return {
            "erro": "nome",
            "exemplo": "novo fixo água 150 no pix dia 25"
        }

    return {
        "nome": nome,
        "valor": valor,
        "conta": conta,
        "dia": dia
    }

def texto_para_categoria(texto: str):
    return sugerir_categoria(texto, "despesa")


PROVEDORES_PAGAMENTO_CATEGORIA = [
    "mercado pago",
    "nubank",
    "btg",
    "itau",
    "itaú",
    "inter",
    "c6",
    "picpay",
    "santander",
    "bradesco",
    "caju",
    "vr caju",
    "vale refeição",
    "vale refeicao",
    "vale alimentação",
    "vale alimentacao",
]


def limpar_texto_pagamento_para_categoria(texto: str):
    texto = normalizar_texto(texto or "").lower()

    # Remove provedores de pagamento completos.
    # Importante: remove "mercado pago", mas não remove "mercado" sozinho.
    for provedor in PROVEDORES_PAGAMENTO_CATEGORIA:
        provedor_norm = normalizar_texto(provedor).lower()
        texto = re.sub(rf"(?<![a-z0-9]){re.escape(provedor_norm)}(?![a-z0-9])", " ", texto)

    # Remove cauda de meio de pagamento quando o usuário escreve no fim:
    # "personal nutricionista pix mercado pago"
    # "uber credito nubank"
    texto = re.sub(
        r"\b(no|na|com|pelo|pela)?\s*(cartao|cartão|credito|crédito|debito|débito|pix|transferencia|transferência|dinheiro|caju|vr caju|vale refeicao|vale refeição|vale alimentacao|vale alimentação)\b.*$",
        " ",
        texto,
    )

    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def limpar_descricao_transacao_pagamento(transacao: dict):
    if not transacao:
        return transacao

    descricao_original = transacao.get("descricao") or ""
    descricao_limpa = descricao_original

    # Remove provedores de pagamento que vazaram para a descrição.
    # Exemplo:
    # "Personal/ nutricionista mercado pago" -> "Personal/ nutricionista"
    for provedor in PROVEDORES_PAGAMENTO_CATEGORIA:
        descricao_limpa = re.sub(
            rf"(?i)(?:\s+|^){re.escape(provedor)}(?:\s+|$)",
            " ",
            descricao_limpa,
        )

    # Remove meio de pagamento no fim da descrição, se o parser deixar escapar.
    descricao_limpa = re.sub(
        r"(?i)\s+\b(pix|cartao|cartão|credito|crédito|debito|débito|transferencia|transferência|dinheiro|caju|vr caju|vale refeicao|vale refeição|vale alimentacao|vale alimentação)\b\s*$",
        "",
        descricao_limpa,
    )

    descricao_limpa = re.sub(r"\s+", " ", descricao_limpa).strip(" -/")

    if descricao_limpa and descricao_limpa != descricao_original:
        transacao["descricao"] = descricao_limpa

    return transacao



CAJU_ALIASES_CONTA = [
    "caju",
    "vr caju",
    "vale refeição",
    "vale refeicao",
    "vale alimentação",
    "vale alimentacao",
]


def texto_menciona_caju(texto: str):
    texto_norm = normalizar_texto(texto or "").lower()
    for termo in CAJU_ALIASES_CONTA:
        termo_norm = normalizar_texto(termo).lower()
        if re.search(rf"(?<![a-z0-9]){re.escape(termo_norm)}(?![a-z0-9])", texto_norm):
            return True
    return False


def aplicar_correcao_conta_caju(transacao: dict):
    """
    Caju/VR é conta de saldo própria. Mantemos forma pix quando informada,
    pois pix reduz saldo imediatamente.
    """
    if not transacao:
        return transacao

    mensagem = transacao.get("mensagem_original") or ""
    descricao = transacao.get("descricao") or ""

    if not (texto_menciona_caju(mensagem) or texto_menciona_caju(descricao)):
        return transacao

    transacao["conta"] = "Caju"

    forma = (transacao.get("forma_pagamento") or "").strip()
    if not forma:
        transacao["forma_pagamento"] = "pix"

    return transacao



def aplicar_correcao_categoria_transacao(transacao: dict):
    if not transacao:
        return transacao

    transacao = aplicar_correcao_conta_caju(transacao)
    transacao = limpar_descricao_transacao_pagamento(transacao)

    descricao = transacao.get("descricao") or ""
    mensagem_original = transacao.get("mensagem_original") or ""

    # A categoria deve vir do produto/serviço comprado.
    # A conta/cartão usado, como Mercado Pago, Nubank ou BTG, não deve virar categoria.
    texto_descricao = limpar_texto_pagamento_para_categoria(descricao)
    categoria_por_descricao = texto_para_categoria(texto_descricao)

    if not categoria_por_descricao:
        texto_mensagem = limpar_texto_pagamento_para_categoria(mensagem_original)
        categoria_por_descricao = texto_para_categoria(texto_mensagem)

    # Categoria dita pelo titular ("... categoria Lazer") nunca é sobrescrita pela inferência.
    if categoria_por_descricao and not detectar_categoria_explicita(mensagem_original):
        transacao["categoria"] = categoria_por_descricao

    # Última normalização no serviço: inferências como "Assinatura" também
    # precisam convergir para a categoria canônica antes da prévia/gravação.
    transacao["categoria"] = canonicalizar_categoria(transacao.get("categoria"), "Outros")
    return transacao



def chave_duplicidade_fixo_revisao(compromisso):
    nome = normalizar_texto(compromisso["nome"] or "").lower()

    sinonimos = [
        ("internet banda larga", "internet"),
        ("banda larga", "internet"),
        ("wi fi", "internet"),
        ("wifi", "internet"),
    ]

    for antigo, novo in sinonimos:
        nome = nome.replace(antigo, novo)

    nome = re.sub(r"\s+", " ", nome).strip()

    return (
        nome,
        round(float(compromisso["valor"] or 0), 2),
        compromisso["dia_vencimento"] or 0,
        normalizar_texto(compromisso["conta_pagamento"] or "").lower(),
        normalizar_texto(compromisso["forma_pagamento"] or "").lower(),
        normalizar_texto(compromisso["categoria"] or "").lower(),
    )


def sugerir_categoria_para_transacao(transacao):
    descricao = transacao["descricao"] or ""
    mensagem = transacao["mensagem_original"] or ""

    categoria_sugerida = texto_para_categoria(descricao)

    if not categoria_sugerida:
        texto = normalizar_texto(mensagem).lower()
        texto = re.sub(r"\b(no|na|com|pelo|pela)\s+(cartao|cartão|credito|crédito|debito|débito|pix)\b.*$", "", texto)
        texto = re.sub(r"\bmercado pago\b", "", texto)
        texto = re.sub(r"\bnubank\b|\bbtg\b|\bitau\b|\bitaú\b|\binter\b|\bc6\b|\bpicpay\b", "", texto)
        categoria_sugerida = texto_para_categoria(texto)

    return categoria_sugerida


def revisar_categorias_suspeitas():
    problemas = []

    categorias_conta_cartao = {
        "mercado",
        "mercado pago",
        "nubank",
        "btg",
        "itau",
        "itaú",
        "inter",
        "picpay",
        "c6",
    }

    descricoes_transporte_fortes = {
        "uber",
        "99",
        "99pop",
        "taxi",
        "táxi",
        "gasolina",
        "pedagio",
        "pedágio",
        "estacionamento",
    }

    for transacao in buscar_todas_transacoes():
        if transacao["tipo"] != "despesa":
            continue

        categoria_atual = transacao["categoria"] or "Outros"
        categoria_atual_normalizada = normalizar_texto(categoria_atual).lower()
        descricao_normalizada = normalizar_texto(transacao["descricao"] or "").lower()
        categoria_sugerida = sugerir_categoria_para_transacao(transacao)

        categoria_sugerida_normalizada = normalizar_texto(categoria_sugerida or "").lower()

        termo_forte_detectado = descricao_normalizada in descricoes_transporte_fortes

        if (
            categoria_sugerida
            and categoria_sugerida_normalizada != categoria_atual_normalizada
            and (
                categoria_atual_normalizada in categorias_conta_cartao
                or categoria_atual_normalizada == "outros"
                or termo_forte_detectado
            )
        ):
            problemas.append({
                "id": transacao["id"],
                "data": transacao["data"],
                "descricao": transacao["descricao"] or "Sem descrição",
                "valor": transacao["valor"],
                "categoria_atual": categoria_atual,
                "categoria_sugerida": categoria_sugerida,
                "acao": f"mudar {transacao['id']} para {categoria_sugerida}",
            })

    return problemas


def revisar_fixos_duplicados():
    from fixos_vigencia import periodos_sobrepostos
    grupos = {}

    for compromisso in listar_compromissos(tipo="fixo", somente_ativos=True):
        if not compromisso["ativo"]:
            continue

        chave = chave_duplicidade_fixo_revisao(compromisso)
        grupos.setdefault(chave, []).append(compromisso)

    problemas = []

    for itens in grupos.values():
        if len(itens) <= 1:
            continue

        # Componentes conectados somente por vigências que se sobrepõem.
        restantes = sorted(itens, key=lambda item: item['id'])
        while restantes:
            grupo = [restantes.pop(0)]
            mudou = True
            while mudou:
                mudou = False
                for item in restantes[:]:
                    if any(periodos_sobrepostos(item, membro) for membro in grupo):
                        grupo.append(item);restantes.remove(item);mudou=True
            if len(grupo)>1:
                grupo.sort(key=lambda item:item['id'])
                problemas.append({'manter':grupo[0], 'remover':grupo[1:]})

    return sorted(problemas, key=lambda item: item["manter"]["id"])


def revisar_lancamentos_incompletos():
    problemas = []

    for transacao in buscar_todas_transacoes():
        faltas = []

        conta = (transacao["conta"] or "").strip().lower()
        forma = (transacao["forma_pagamento"] or "").strip().lower()

        if not conta or conta in ["não informada", "nao informada", "outros"]:
            faltas.append("conta")

        if not forma or forma in ["não informada", "nao informada", "outros"]:
            faltas.append("forma")

        if faltas:
            problemas.append({
                "id": transacao["id"],
                "data": transacao["data"],
                "descricao": transacao["descricao"] or "Sem descrição",
                "valor": transacao["valor"],
                "faltas": faltas,
            })

    return problemas[:10]


def revisar_valores_fora_do_padrao():
    transacoes = [t for t in buscar_todas_transacoes() if t["tipo"] == "despesa"]
    por_categoria = {}

    for t in transacoes:
        categoria = t["categoria"] or "Outros"
        por_categoria.setdefault(categoria, []).append(t)

    problemas = []

    for categoria, itens in por_categoria.items():
        if len(itens) < 5:
            continue

        valores = [float(t["valor"] or 0) for t in itens]
        media = sum(valores) / len(valores)

        if media <= 0:
            continue

        for t in itens:
            valor = float(t["valor"] or 0)
            if valor >= media * 3 and valor >= 100:
                problemas.append({
                    "id": t["id"],
                    "data": t["data"],
                    "descricao": t["descricao"] or "Sem descrição",
                    "categoria": categoria,
                    "valor": valor,
                    "media": media,
                })

    return sorted(problemas, key=lambda item: item["valor"], reverse=True)[:10]


def chave_duplicidade_transacao(transacao):
    descricao = normalizar_texto(transacao["descricao"] or "").lower()
    descricao = re.sub(r"\s+", " ", descricao).strip()

    return (
        transacao["data"],
        transacao["tipo"],
        round(float(transacao["valor"] or 0), 2),
        descricao,
        normalizar_texto(transacao["conta"] or "").lower(),
        normalizar_texto(transacao["forma_pagamento"] or "").lower(),
    )


def revisar_transacoes_duplicadas():
    grupos = {}

    for transacao in buscar_todas_transacoes():
        chave = chave_duplicidade_transacao(transacao)
        grupos.setdefault(chave, []).append(transacao)

    problemas = []

    for itens in grupos.values():
        if len(itens) <= 1:
            continue

        itens_ordenados = sorted(itens, key=lambda item: item["id"])
        problemas.append({
            "manter": itens_ordenados[0],
            "remover": itens_ordenados[1:],
        })

    return sorted(problemas, key=lambda item: item["manter"]["id"])[:10]


def revisar_descricoes_suspeitas():
    problemas = []

    termos_pagamento = [
        "mercado pago",
        "nubank",
        "btg",
        "itau",
        "itaú",
        "inter",
        "picpay",
        "c6",
        "cartao",
        "cartão",
        "credito",
        "crédito",
        "debito",
        "débito",
        "pix",
    ]

    for transacao in buscar_todas_transacoes():
        descricao = normalizar_texto(transacao["descricao"] or "").lower()

        if not descricao:
            continue

        # Se a descrição ficou parecendo meio de pagamento/conta, provavelmente o parser limpou mal.
        if descricao in termos_pagamento:
            problemas.append({
                "id": transacao["id"],
                "data": transacao["data"],
                "descricao": transacao["descricao"] or "Sem descrição",
                "valor": transacao["valor"],
                "categoria": transacao["categoria"] or "Outros",
                "motivo": "descrição parece conta ou forma de pagamento",
            })

    return problemas[:10]


def revisar_datas_suspeitas():
    problemas = []
    hoje = relogio.hoje(date)

    for transacao in buscar_todas_transacoes():
        try:
            data_transacao = date.fromisoformat(transacao["data"])
        except ValueError:
            problemas.append({
                "id": transacao["id"],
                "data": transacao["data"],
                "descricao": transacao["descricao"] or "Sem descrição",
                "valor": transacao["valor"],
                "motivo": "data inválida",
            })
            continue

        parcela_atual = row_get(transacao, "parcela_atual")
        parcelas_total = row_get(transacao, "parcelas_total")

        # Compras parceladas podem ter datas futuras. Lançamento avulso futuro é mais suspeito.
        if data_transacao > hoje + timedelta(days=2) and not parcela_atual and not parcelas_total:
            problemas.append({
                "id": transacao["id"],
                "data": transacao["data"],
                "descricao": transacao["descricao"] or "Sem descrição",
                "valor": transacao["valor"],
                "motivo": "lançamento avulso com data futura",
            })

    return problemas[:10]


def revisar_categorias_genericas():
    problemas = []

    genericas = {"outros", "geral", "diversos", "sem categoria"}

    for transacao in buscar_todas_transacoes():
        categoria = normalizar_texto(transacao["categoria"] or "").lower()

        if categoria in genericas:
            problemas.append({
                "id": transacao["id"],
                "data": transacao["data"],
                "descricao": transacao["descricao"] or "Sem descrição",
                "valor": transacao["valor"],
                "categoria": transacao["categoria"] or "Outros",
            })

    return problemas[:10]




def gerar_revisao_inteligente():
    categorias = revisar_categorias_suspeitas()
    duplicados_fixos = revisar_fixos_duplicados()
    duplicados_transacoes = revisar_transacoes_duplicadas()
    incompletos = revisar_lancamentos_incompletos()
    fora_padrao = revisar_valores_fora_do_padrao()
    descricoes = revisar_descricoes_suspeitas()
    datas = revisar_datas_suspeitas()
    categorias_genericas = revisar_categorias_genericas()

    total_alertas = (
        len(categorias)
        + len(duplicados_fixos)
        + len(duplicados_transacoes)
        + len(incompletos)
        + len(fora_padrao)
        + len(descricoes)
        + len(datas)
        + len(categorias_genericas)
    )

    linhas = [
        "🔎 Revisão inteligente",
        "",
        bloco_total("Resumo", [
            f"│ {'Alertas encontrados':<24} {total_alertas:>14}",
            f"│ {'Categorias suspeitas':<24} {len(categorias):>14}",
            f"│ {'Fixos duplicados':<24} {len(duplicados_fixos):>14}",
            f"│ {'Transações duplicadas':<24} {len(duplicados_transacoes):>14}",
            f"│ {'Dados incompletos':<24} {len(incompletos):>14}",
            f"│ {'Valores fora padrão':<24} {len(fora_padrao):>14}",
        ]),
    ]

    if total_alertas == 0:
        linhas.extend([
            "",
            "✅ Não encontrei inconsistências relevantes agora.",
            "",
            "Isso não garante que tudo esteja perfeito, mas não há nada gritante para revisar.",
        ])
        return "\n".join(linhas)

    if categorias:
        linhas.extend(["", "🏷 Categorias suspeitas"])
        for item in categorias[:10]:
            linhas.extend([
                "",
                f"┌ #{item['id']} · {item['descricao']}",
                f"│ 📅 {formatar_data_visual(item['data'])}",
                f"│ 💸 {formatar_moeda(item['valor'])}",
                f"│ Atual: {item['categoria_atual']}",
                f"│ Sugestão: {item['categoria_sugerida']}",
                "└",
                f"Ação: {item['acao']}",
            ])

    if categorias_genericas:
        linhas.extend(["", "🏷 Categorias genéricas"])
        for item in categorias_genericas[:10]:
            linhas.extend([
                "",
                f"#{item['id']} · {item['descricao']} · {formatar_moeda(item['valor'])}",
                f"Categoria atual: {item['categoria']}",
                f"Ação sugerida: mudar {item['id']} para CATEGORIA_CORRETA",
            ])

    if duplicados_fixos:
        linhas.extend(["", "🔁 Possíveis fixos duplicados"])
        for grupo in duplicados_fixos[:10]:
            manter = grupo["manter"]
            linhas.extend([
                "",
                f"┌ Manter #C{manter['id']} · {manter['nome']}",
                f"│ 💸 {formatar_moeda(manter['valor'])}",
                f"│ 📅 dia {manter['dia_vencimento']}",
                "└",
            ])

            for item in grupo["remover"]:
                linhas.extend([
                    f"┌ Possível remover #C{item['id']} · {item['nome']}",
                    f"│ 💸 {formatar_moeda(item['valor'])}",
                    f"│ 📅 dia {item['dia_vencimento']}",
                    "└",
                    f"Ação: apagar fixo {item['id']}",
                ])

    if duplicados_transacoes:
        linhas.extend(["", "📌 Possíveis transações duplicadas"])
        for grupo in duplicados_transacoes[:10]:
            manter = grupo["manter"]
            linhas.extend(["", f"Manter #{manter['id']} · {manter['descricao'] or 'Sem descrição'} · {formatar_moeda(manter['valor'])}"])

            for item in grupo["remover"]:
                linhas.extend([
                    f"Possível remover #{item['id']} · {item['descricao'] or 'Sem descrição'} · {formatar_moeda(item['valor'])}",
                    f"Ação: apagar {item['id']}",
                ])

    if descricoes:
        linhas.extend(["", "📝 Descrições suspeitas"])
        for item in descricoes[:10]:
            linhas.extend([
                "",
                f"#{item['id']} · {item['descricao']} · {formatar_moeda(item['valor'])}",
                f"Motivo: {item['motivo']}",
                "Ação sugerida: revisar manualmente esse lançamento",
            ])

    if incompletos:
        linhas.extend(["", "🧩 Lançamentos com dados incompletos"])
        for item in incompletos[:10]:
            linhas.extend([
                "",
                f"#{item['id']} · {item['descricao']} · {formatar_moeda(item['valor'])}",
                f"Falta revisar: {', '.join(item['faltas'])}",
            ])

            if "conta" in item["faltas"]:
                linhas.append(f"Ação sugerida: corrigir conta {item['id']} para NOME_DA_CONTA")

            if "forma" in item["faltas"]:
                linhas.append(f"Ação sugerida: corrigir forma {item['id']} para transferência")

    if datas:
        linhas.extend(["", "📅 Datas suspeitas"])
        for item in datas[:10]:
            linhas.extend([
                "",
                f"#{item['id']} · {item['descricao']} · {formatar_moeda(item['valor'])}",
                f"Data: {item['data']}",
                f"Motivo: {item['motivo']}",
            ])

    if fora_padrao:
        linhas.extend(["", "⚠️ Valores fora do padrão"])
        for item in fora_padrao[:10]:
            linhas.extend([
                "",
                f"#{item['id']} · {item['descricao']}",
                f"{formatar_moeda(item['valor'])} em {item['categoria']}",
                f"Média da categoria: {formatar_moeda(item['media'])}",
            ])

    linhas.extend([
        "",
        "Nada foi alterado automaticamente.",
        "Execute as ações sugeridas apenas se fizerem sentido.",
    ])

    return "\n".join(linhas)


# ============================================================
# UX v3 — telas principais do assessor pessoal
# ============================================================

FORMAS_SAIDA_IMEDIATA_SALDO = ["pix", "débito", "debito", "dinheiro", "transferência", "transferencia"]

# A conta Itaú é a conta centralizadora do caixa pessoal: salários/entradas e
# pagamentos das demais faturas e compromissos convergem para ela. Portanto,
# consultar "saldo Itaú" deve responder quanto restará no caixa principal após
# todas as obrigações do mês, usando a mesma ponte financeira de "meu mês".
CONTA_CENTRALIZADORA_SALDO = "Itaú"


def conta_centraliza_fluxo_mensal(conta: str | None) -> bool:
    return mesma_conta_saldo(conta, CONTA_CENTRALIZADORA_SALDO)


def texto_chave_saldo(valor: str):
    texto = (valor or "").lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"\s+", " ", texto)
    return texto


def nome_conta_padrao(valor: str | None):
    texto = (valor or "").strip()
    return texto if texto else "Não informada"


def formatar_nome_conta_saldo(valor: str | None):
    texto = (valor or "").strip()
    chave = texto_chave_saldo(texto)

    nomes = {
        "btg": "BTG",
        "nubank": "Nubank",
        "mercado pago": "Mercado Pago",
        "mercado livre": "Mercado Livre",
        "ml": "Mercado Livre",
        "pix": "Pix",
        "itau": "Itaú",
        "itaú": "Itaú",
        "caju": "Caju",
        "vr caju": "Caju",
        "c6": "C6",
        "xp": "XP",
        "picpay": "PicPay",
        "inter": "Inter",
        "compras": "Compras",
        "lia": "Lia",
    }

    return nomes.get(chave, texto.title() if texto else "Geral")


def mesma_conta_saldo(a: str | None, b: str | None):
    return texto_chave_saldo(a or "") == texto_chave_saldo(b or "")


def eh_alias_saldo_geral(valor: str | None):
    chave = texto_chave_saldo(valor or "")
    return chave in [
        "geral",
        "total",
        "todos",
        "tudo",
        "consolidado",
        "saldo geral",
        "saldo total",
        "saldo consolidado",
    ]


def transacao_afeta_saldo_disponivel(transacao):
    if transacao["tipo"] == "receita":
        return True

    texto = texto_chave_saldo(f"{transacao['conta'] or ''} {transacao['forma_pagamento'] or ''}")
    return any(forma in texto for forma in FORMAS_SAIDA_IMEDIATA_SALDO)


def item_esperado_por_origem(item: dict):
    return item.get("origem") != "transacao"


# TIPOS_LIQUIDACAO_FATURA, item_eh_liquidacao_fatura e remover_liquidacoes_fatura
# vivem em compromissos.py (onde o item ``fatura_movimento`` nasce) para que a
# agenda/contas de pagamento usem o mesmo critério; são reexportados daqui.


def obter_conta_transacao_saldo(transacao):
    return nome_conta_padrao(transacao["conta"] or transacao["forma_pagamento"])


def obter_conta_item_saldo(item: dict):
    return nome_conta_padrao(item.get("conta_pagamento") or item.get("conta") or item.get("forma_pagamento") or item.get("forma"))


def obter_saldos_iniciais_por_conta(ano_mes: str):
    saldos = {}

    for row in buscar_saldos_contas_mes(ano_mes):
        saldos[row["conta"]] = float(row["saldo_inicial"] or 0)

    # Compatibilidade: se existir saldo mensal geral antigo e ainda não houver saldo por conta,
    # ele entra como "Geral".
    if not saldos:
        legado = buscar_saldo_mensal(ano_mes)
        if legado:
            saldos["Geral"] = float(legado["saldo_inicial"] or 0)

    return saldos



def obter_mes_anterior(ano_mes: str):
    ano, mes = map(int, ano_mes.split("-"))
    if mes == 1:
        return f"{ano - 1:04d}-12"
    return f"{ano:04d}-{mes - 1:02d}"


def calcular_saldo_disponivel_por_conta(saldos_por_conta: dict, transacoes_por_conta: dict):
    contas = set(saldos_por_conta.keys()) | set(transacoes_por_conta.keys())
    resultado = {}

    for nome in contas:
        saldo_inicial = float(saldos_por_conta.get(nome, 0.0) or 0.0)
        movimento = transacoes_por_conta.get(nome, {}) or {}
        entradas = float(movimento.get("entradas", 0.0) or 0.0)
        saidas_imediatas = float(movimento.get("saidas_imediatas", 0.0) or 0.0)
        resultado[nome] = saldo_inicial + entradas - saidas_imediatas

    return resultado



def comparar_ano_mes(a: str, b: str):
    return (a > b) - (a < b)


def gerar_meses_entre(inicio: str, fim: str, limite: int | None = None):
    """
    Gera meses de inicio até fim, inclusive, sem passar do limite.
    Exemplo: 2026-06 até 2026-08.
    """
    inicio = validar_ano_mes(inicio)
    fim = validar_ano_mes(fim)
    if not inicio or not fim:
        return []

    meses = []
    ano, mes = map(int, inicio.split("-"))
    ano_fim, mes_fim = map(int, fim.split("-"))

    while (ano < ano_fim or (ano == ano_fim and mes <= mes_fim)) and (limite is None or len(meses) < limite):
        meses.append(f"{ano:04d}-{mes:02d}")
        mes += 1
        if mes == 13:
            mes = 1
            ano += 1

    return meses


def obter_primeiro_mes_relevante(fallback: str):
    """
    Define a partir de onde vamos procurar pendências herdadas.

    Usa o menor mês encontrado em:
    - saldos configurados
    - saldos por conta
    - transações
    - checklist manual

    Isso evita voltar infinitamente em compromissos recorrentes antigos.
    """
    fallback = validar_ano_mes(fallback) or relogio.hoje(date).strftime("%Y-%m")
    candidatos = []

    try:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT MIN(ano_mes) AS mes FROM saldos_mensais
                UNION ALL
                SELECT MIN(ano_mes) AS mes FROM saldos_mensais_contas
                UNION ALL
                SELECT MIN(substr(data, 1, 7)) AS mes FROM transacoes
                UNION ALL
                SELECT MIN(ano_mes) AS mes FROM checklist_pagamentos
                UNION ALL
                SELECT MIN(substr(data_inicio, 1, 7)) AS mes FROM compromissos
            """).fetchall()

        for row in rows:
            mes = row[0] if row else None
            if validar_ano_mes(mes):
                candidatos.append(mes)
    except Exception:
        candidatos = []

    if candidatos:
        return min(candidatos)

    return fallback


def obter_meses_anteriores_relevantes(ano_mes: str, limite: int | None = None):
    ano_mes = validar_ano_mes(ano_mes) or relogio.hoje(date).strftime("%Y-%m")
    if ano_mes == '0001-01':
        return []
    mes_anterior = obter_mes_anterior(ano_mes)
    primeiro = obter_primeiro_mes_relevante(mes_anterior)

    if comparar_ano_mes(primeiro, mes_anterior) > 0:
        primeiro = mes_anterior

    return gerar_meses_entre(primeiro, mes_anterior, limite=limite)


def item_checklist_eh_credito_individual(item: dict) -> bool:
    """Identifica cobrança de compromisso no crédito que não deve virar dívida individual.

    Compras/fixos no crédito pertencem à fatura do cartão. Quando o item já está
    agregado em ``grupo=bancos``, a própria fatura é a obrigação. Para contas
    antigas que ainda não eram reconhecidas como cartão, evitamos ressuscitar
    cada cobrança individual como vencida de meses anteriores.
    """
    if not isinstance(item, dict):
        return False
    if normalizar_texto(item.get("grupo") or "") == "bancos":
        return False
    if normalizar_texto(item.get("origem") or "") != "compromisso":
        return False
    forma = normalizar_texto(item.get("forma") or item.get("forma_pagamento") or "")
    return any(termo in forma for termo in ("credito", "cartao", "fatura"))


def item_checklist_afeta_pendencia_herdada(item: dict):
    """
    Pendência herdada é obrigação não paga de mês anterior.

    Excluímos transações avulsas porque elas já foram realizadas e entram como
    pago automático no checklist. Cobranças individuais no crédito também não
    são herdadas: o evento de caixa é o pagamento da fatura, não cada compra.
    """
    if item.get("origem") == "transacao":
        return False

    if item_checklist_eh_credito_individual(item):
        return False

    # "revisar" significa que o usuário já marcou a obrigação como paga em uma
    # versão anterior, porém ainda não existe um vínculo de conciliação com a
    # transação correspondente. Isso é uma pendência de qualidade/auditoria,
    # não uma dívida financeira em aberto. Portanto, não deve contaminar A pagar,
    # projeção de saldo nem totais herdados.
    if item.get("status") in {"pago", "revisar"}:
        return False

    return True


def listar_pendencias_abertas_anteriores(ano_mes: str, conta: str | None = None, limite_meses: int | None = None):
    """
    Lista pendências de meses anteriores que continuam abertas.

    A obrigação permanece no mês de origem. Ela só é carregada para o mês atual
    como pendência herdada enquanto não for marcada como paga no checklist do
    mês de origem.

    Exemplo:
    - B3 Nubank de 2026-06 pendente
    - em 2026-07, 2026-08 etc., aparece como pendência herdada de junho
    - quando fizer "paguei B3 2026-06", ela deixa de ser carregada
    """
    ano_mes = validar_ano_mes(ano_mes) or relogio.hoje(date).strftime("%Y-%m")
    conta_filtro = (conta or "").strip() or None

    pendencias = []

    for mes in obter_meses_anteriores_relevantes(ano_mes, limite=limite_meses):
        import conciliacao as conciliacao_motor
        with conciliacao_motor.referencia(conciliacao_motor.fim_mes(ano_mes)):
            itens = aplicar_status_checklist(mes, montar_itens_checklist_mes(mes))

        for item in itens:
            if not item_checklist_afeta_pendencia_herdada(item):
                continue

            if conta_filtro and not mesma_conta_saldo(obter_conta_item_saldo(item), conta_filtro):
                continue

            item_copia = dict(item)
            item_copia["ano_mes_origem"] = mes
            item_copia["codigo_origem"] = item.get("codigo") or item.get("chave")
            pendencias.append(item_copia)

    return pendencias


def listar_revisoes_baixas_anteriores(ano_mes: str, conta: str | None = None, limite_meses: int | None = None):
    """Lista marcações antigas de pago que ainda precisam ser conciliadas.

    Esses itens são exibidos apenas na área de revisão. Eles NÃO são contas a
    pagar e não entram em total financeiro, projeção ou pendência herdada.
    """
    ano_mes = validar_ano_mes(ano_mes) or relogio.hoje(date).strftime("%Y-%m")
    conta_filtro = (conta or "").strip() or None
    revisoes = []

    for mes in obter_meses_anteriores_relevantes(ano_mes, limite=limite_meses):
        import conciliacao as conciliacao_motor
        with conciliacao_motor.referencia(conciliacao_motor.fim_mes(ano_mes)):
            itens = aplicar_status_checklist(mes, montar_itens_checklist_mes(mes))

        for item in itens:
            if item.get("status") != "revisar":
                continue
            if conta_filtro and not mesma_conta_saldo(obter_conta_item_saldo(item), conta_filtro):
                continue
            item_copia = dict(item)
            item_copia["ano_mes_origem"] = mes
            item_copia["codigo_origem"] = item.get("codigo") or item.get("chave")
            revisoes.append(item_copia)

    return revisoes


def resumir_pendencias_herdadas(pendencias: list):
    total = sum(float(item.get("valor") or 0) for item in pendencias)

    por_mes = {}
    por_grupo = {"faturas": 0.0, "individuais": 0.0}
    por_conta = {}

    for item in pendencias:
        valor = float(item.get("valor") or 0)
        mes = item.get("ano_mes_origem") or "sem mês"
        por_mes[mes] = por_mes.get(mes, 0.0) + valor

        grupo = "faturas" if item.get("grupo") == "bancos" else "individuais"
        por_grupo[grupo] = por_grupo.get(grupo, 0.0) + valor

        conta_nome = obter_conta_item_saldo(item)
        por_conta[conta_nome] = por_conta.get(conta_nome, 0.0) + valor

    return {
        "total": total,
        "quantidade": len(pendencias),
        "por_mes": por_mes,
        "por_grupo": por_grupo,
        "por_conta": por_conta,
    }


def formatar_resumo_pendencias_herdadas(pendencias: list, limite: int = 8):
    resumo = resumir_pendencias_herdadas(pendencias)

    if not pendencias:
        return ["🔴 Pendências herdadas: R$ 0,00"]

    linhas = [
        "🔴 Pendências abertas de meses anteriores",
        f"Total: {formatar_moeda(resumo['total'])}",
        f"Itens: {resumo['quantidade']}",
    ]

    if resumo["por_mes"]:
        linhas.append("")
        linhas.append("Por mês de origem:")
        for mes, valor in sorted(resumo["por_mes"].items()):
            linhas.append(f"- {formatar_ano_mes_visual(mes)}: {formatar_moeda(valor)}")

    linhas.append("")
    linhas.append("Principais pendências:")
    for item in pendencias[:limite]:
        codigo = item.get("codigo_origem") or item.get("codigo") or item.get("chave")
        mes = item.get("ano_mes_origem")
        nome = item.get("nome") or "Item"
        valor = float(item.get("valor") or 0)
        linhas.append(f"- {codigo} · {nome} · {formatar_moeda(valor)} · {formatar_ano_mes_visual(mes)}")

    restante = len(pendencias) - limite
    if restante > 0:
        linhas.append(f"+{restante} item(ns)")

    return linhas


def gerar_pendencias_abertas_formatado(ano_mes: str | None = None, conta: str | None = None):
    ano_mes = validar_ano_mes(ano_mes) if ano_mes else relogio.hoje(date).strftime("%Y-%m")
    conta_filtro = (conta or "").strip() or None

    pendencias = listar_pendencias_abertas_anteriores(ano_mes, conta_filtro)
    resumo = resumir_pendencias_herdadas(pendencias)

    titulo_conta = f" — {formatar_nome_conta_saldo(conta_filtro)}" if conta_filtro else ""
    linhas = [
        f"🔴 Pendências herdadas{titulo_conta} — até {formatar_ano_mes_visual(ano_mes)}",
        "",
    ]

    if not pendencias:
        linhas.extend([
            "Não encontrei pendências abertas de meses anteriores.",
            "",
            "Isso significa que, até o mês anterior, o checklist está quitado ou não há itens projetados em aberto.",
        ])
        return "\n".join(linhas)

    linhas.extend([
        f"Total em aberto: {formatar_moeda(resumo['total'])}",
        f"Itens em aberto: {resumo['quantidade']}",
        "",
        "Quebra:",
        f"- Faturas/cartões: {formatar_moeda(resumo['por_grupo'].get('faturas', 0.0))}",
        f"- Fixos/compromissos/parcelas: {formatar_moeda(resumo['por_grupo'].get('individuais', 0.0))}",
    ])

    if resumo["por_mes"]:
        linhas.extend(["", "Por mês de origem:"])
        for mes, valor in sorted(resumo["por_mes"].items()):
            linhas.append(f"- {formatar_ano_mes_visual(mes)}: {formatar_moeda(valor)}")

    linhas.extend(["", "Itens:"])
    for item in pendencias[:30]:
        codigo = item.get("codigo_origem") or item.get("codigo") or item.get("chave")
        mes = item.get("ano_mes_origem")
        nome = item.get("nome") or "Item"
        valor = float(item.get("valor") or 0)
        conta_item = item.get("conta") or item.get("conta_pagamento") or "Não informada"
        linhas.append(
            f"- {codigo} · {nome} · {formatar_moeda(valor)} · {formatar_ano_mes_visual(mes)} · {conta_item}"
        )

    restante = len(pendencias) - 30
    if restante > 0:
        linhas.append(f"+{restante} item(ns)")

    linhas.extend([
        "",
        "Para quitar uma pendência, marque o checklist do mês de origem:",
        "paguei B3 2026-06",
        "paguei C10 2026-06",
        "",
        "Observação:",
        "Se o mês herdou automaticamente o saldo livre provável do mês anterior, essas pendências podem já estar abatidas na herança para não duplicar desconto.",
    ])

    return "\n".join(linhas)


def parsear_comando_pendencias_abertas(texto_limpo: str):
    texto = normalizar_texto(texto_limpo)

    match = re.match(
        r"^(?:pendencias abertas|pendências abertas|dividas abertas|dívidas abertas|pendencias herdadas|pendências herdadas)(?:\s+(\d{4}-\d{2}))?(?:\s+(.+))?$",
        texto
    )
    if not match:
        return None

    ano_mes = validar_ano_mes(match.group(1)) if match.group(1) else relogio.hoje(date).strftime("%Y-%m")
    conta = (match.group(2) or "").strip() or None

    if conta and eh_alias_saldo_geral(conta):
        conta = None

    return ano_mes, conta



def pagamentos_fatura_caixa_mes(ano_mes: str):
    """Pagamentos de fatura cujo dinheiro saiu em ``ano_mes`` (data_movimento).

    O caixa segue a data do pagamento; a fatura (competência) continua em
    ``ano_mes`` do movimento. Pagar em novembro a fatura de outubro não muda o
    "Saldo agora" de outubro (D3, reavaliação 02).
    """
    return [
        mov for mov in listar_fatura_movimentos()
        if mov["tipo_movimento"] in {"pagamento_parcial", "pagamento_total"}
        and str(mov["data_movimento"] or mov["ano_mes"] or "")[:7] == ano_mes
    ]


def pagamentos_fatura_posteriores(ano_mes: str):
    """Pagamentos da fatura de competência ``ano_mes`` feitos em mês posterior."""
    return [
        mov for mov in listar_fatura_movimentos(ano_mes)
        if mov["tipo_movimento"] in {"pagamento_parcial", "pagamento_total"}
        and str(mov["data_movimento"] or "")[:7] > ano_mes
    ]


def _receitas_previstas_herdadas(ano_mes: str, anterior: dict):
    """Receitas previstas de meses anteriores ainda não recebidas em ``ano_mes``.

    Regra de 09/11/2026 (docs/reavaliacao/06_regra_heranca.md): a herança não
    leva receita prevista como saldo. Ela segue como "a receber herdado" e entra
    na projeção uma única vez, até ser vinculada a um recebimento (o vínculo
    abate o restante) ou descartada na previsão de origem.

    Devolve (itens, suspeitas). ``suspeitas`` são previsões com um recebimento
    de mesmo nome e conta lançado depois, sem vínculo: ficam fora da projeção
    (o recebimento já está no saldo; somar de novo contaria em dobro) e viram
    revisão de conciliação. Nada é gravado aqui.
    """
    import json
    import conciliacao as conciliacao_motor

    candidatos = [dict(item, ano_mes_origem=anterior.get("ano_mes"))
                  for item in anterior.get("entradas_previstas_itens") or []]
    candidatos += [dict(item) for item in anterior.get("receitas_previstas_herdadas_itens") or []]
    candidatos += [dict(item) for item in anterior.get("receitas_previstas_herdadas_suspeitas") or []]
    if not candidatos:
        return [], []

    fim = conciliacao_motor.fim_mes(ano_mes)
    pagos = {}
    for v in conciliacao_motor.listar_vinculos(ate=fim):
        chave = (v["compromisso_id"], v["mes"])
        pagos[chave] = pagos.get(chave, 0) + int(v["centavos"])
    vinculados = {v["transacao_id"] for v in conciliacao_motor.listar_vinculos()}

    with get_connection() as conn:
        separados = {}
        for (payload,) in conn.execute(
                "SELECT dados_depois FROM auditoria_eventos WHERE entidade='conciliacao_revisao' ORDER BY id"):
            dados = json.loads(payload or "null") or {}
            separados[dados.get("id")] = dados.get("movimento")
        inicio_busca = min(conciliacao_motor.fim_mes(str(c["ano_mes_origem"])) for c in candidatos)
        receitas = [
            dict(zip(("id", "data", "tipo", "valor", "conta", "forma_pagamento", "descricao"), row))
            for row in conn.execute(
                "SELECT id, data, tipo, valor, conta, forma_pagamento, descricao FROM transacoes "
                "WHERE tipo='receita' AND data > ? AND data <= ? ORDER BY data, id",
                (inicio_busca, fim))
        ]

    itens, suspeitas = [], []
    for item in candidatos:
        origem = str(item["ano_mes_origem"])
        original = item.get("valor_original", item.get("valor"))
        if not original or float(original) <= 0:
            continue
        # Mesma conversão de ajustar_projecao (conciliação), em centavos inteiros.
        previsto = conciliacao_motor.centavos(original)
        restante = previsto - pagos.get((item.get("id"), origem), 0)
        if restante <= 0:
            continue
        item.update(valor=restante / 100, valor_original=previsto / 100)
        nome = conciliacao_motor.normalizar(item.get("nome"))
        conta_item = conciliacao_motor.normalizar(item.get("conta_pagamento"))
        recebimento = next((
            t for t in receitas
            if t["data"] > conciliacao_motor.fim_mes(origem)
            and t["id"] not in vinculados
            and separados.get(t["id"]) != [t["data"], t["tipo"], t["valor"], t["conta"], t["forma_pagamento"]]
            and conciliacao_motor.normalizar(t["descricao"]) == nome
            and conciliacao_motor.normalizar(t["conta"]) == conta_item
        ), None)
        if recebimento:
            suspeitas.append(dict(item, transacao_suspeita_id=recebimento["id"]))
        else:
            itens.append(item)
    return itens, suspeitas


def _calcular_saldo_mensal_etapa(
    ano_mes: str | None = None,
    conta: str | None = None,
    permitir_heranca: bool = True,
    profundidade_heranca: int = 0,
):
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")

    conta_solicitada = (conta or "").strip() or None

    # Itaú é a conta centralizadora: o saldo solicitado precisa refletir todas
    # as entradas e obrigações que formam "meu mês", inclusive faturas de
    # outros cartões pagas com o caixa do Itaú. Outras contas continuam com
    # visão individual.
    conta_filtro = None if conta_centraliza_fluxo_mensal(conta_solicitada) else conta_solicitada
    saldos_por_conta = obter_saldos_iniciais_por_conta(ano_mes)

    saldo_herdado_auto = False
    ano_mes_saldo_herdado = None
    saldos_herdados_por_conta = {}
    saldo_herdado_caixa_origem = 0.0
    saldo_herdado_livre_origem = 0.0
    saldo_herdado_ajustes_origem = 0.0
    saldos_definidos_heranca = {}

    if conta_filtro:
        saldo_inicial = sum(
            valor for nome, valor in saldos_por_conta.items()
            if mesma_conta_saldo(nome, conta_filtro)
        )
        saldo_configurado = any(mesma_conta_saldo(nome, conta_filtro) for nome in saldos_por_conta)
    else:
        saldo_inicial = sum(saldos_por_conta.values())
        saldo_configurado = bool(saldos_por_conta)

    # Regra de virada de mês:
    # se o mês atual não tem saldo inicial manual/configurado, herdamos somente
    # o saldo livre/provável do mês imediatamente anterior. Não somamos meses futuros.
    if permitir_heranca and not saldo_configurado:
        mes_anterior = obter_mes_anterior(ano_mes)
        # Conta sem caixa próprio no caixa reconciliado (ex.: cartão Nubank).
        # Suas obrigações do mês anterior já foram abatidas no caixa
        # reconciliado; herdá-las de novo descontaria o mesmo valor duas vezes.
        caixa_reconciliado_sem_conta = None

        if conta_filtro:
            # Para saldo por conta, a herança precisa usar a MESMA reconciliação
            # do comando "caixa". Antes, "saldo Itaú" herdava o caixa bruto da
            # conta no mês anterior, enquanto "meu mês" e "caixa" já usavam o
            # saldo livre reconciliado. Isso gerava divergência.
            try:
                caixa_reconciliado = calcular_caixa_por_conta_mes(ano_mes)
                contas_caixa = caixa_reconciliado.get("contas", {}) or {}

                for nome_conta, item_caixa in contas_caixa.items():
                    if mesma_conta_saldo(nome_conta, conta_filtro):
                        saldo_inicial = float(item_caixa.get("inicial", 0.0) or 0.0)
                        saldo_configurado = True
                        saldo_herdado_auto = bool(caixa_reconciliado.get("herdado_auto"))
                        ano_mes_saldo_herdado = caixa_reconciliado.get("mes_origem") or mes_anterior

                        saldo_herdado_livre_origem = saldo_inicial
                        saldo_herdado_caixa_origem = saldo_inicial
                        saldo_herdado_ajustes_origem = 0.0
                        saldos_herdados_por_conta = {
                            nome: float(valores.get("inicial", 0.0) or 0.0)
                            for nome, valores in contas_caixa.items()
                        }
                        saldos_definidos_heranca = {
                            nome: item
                            for nome, item in (caixa_reconciliado.get("saldos_iniciais_definidos_heranca") or {}).items()
                            if mesma_conta_saldo(nome, conta_filtro)
                        }
                        break
                else:
                    caixa_reconciliado_sem_conta = caixa_reconciliado
            except Exception:
                # fallback para lógica antiga abaixo (comportamento mantido);
                # agora fica registrado para não esconder um erro de cálculo.
                _LOG_CALCULOS.warning(
                    "Saldo herdado por conta (%s, %s): usando a lógica antiga após erro.",
                    ano_mes, conta_filtro, exc_info=True,
                )

        if not saldo_configurado:
            dados_anterior = calcular_saldo_mensal(
                mes_anterior,
                conta_filtro,
                permitir_heranca=True,
                profundidade_heranca=profundidade_heranca + 1,
            )

            if dados_anterior.get("saldo_configurado") and caixa_reconciliado_sem_conta is not None:
                # A conta não tem dinheiro no caixa reconciliado: começa o mês
                # zerada, como no "caixa" e no total consolidado.
                saldo_inicial = 0.0
                saldo_configurado = True
                saldo_herdado_auto = True
                ano_mes_saldo_herdado = caixa_reconciliado_sem_conta.get("mes_origem") or mes_anterior
                saldo_herdado_caixa_origem = 0.0
                saldo_herdado_livre_origem = 0.0
                saldo_herdado_ajustes_origem = 0.0
                saldos_herdados_por_conta = {
                    nome: float(valores.get("inicial", 0.0) or 0.0)
                    for nome, valores in (caixa_reconciliado_sem_conta.get("contas", {}) or {}).items()
                }
            elif dados_anterior.get("saldo_configurado"):
                # Virada: herdar o saldo livre provável do mês anterior SEM as
                # receitas previstas e não recebidas (regra de 09/11/2026,
                # docs/reavaliacao/06_regra_heranca.md). Receita esperada não
                # vira dinheiro em conta; ela segue separada como "a receber
                # herdado". Despesas esperadas continuam abatidas (conservador).
                saldo_caixa_origem = float(dados_anterior.get("saldo_disponivel", 0.0) or 0.0)
                saldo_livre_origem = float(dados_anterior.get(
                    "saldo_herdavel", dados_anterior.get("saldo_projetado", saldo_caixa_origem)) or 0.0)
                ajuste_origem = saldo_caixa_origem - saldo_livre_origem

                saldo_inicial = saldo_livre_origem
                saldo_configurado = True
                saldo_herdado_auto = True
                ano_mes_saldo_herdado = mes_anterior

                saldo_herdado_caixa_origem = saldo_caixa_origem
                saldo_herdado_livre_origem = saldo_livre_origem
                saldo_herdado_ajustes_origem = ajuste_origem

                saldos_herdados_por_conta = dados_anterior.get("saldo_disponivel_por_conta", {}) or {}
                if not conta_filtro and saldos_herdados_por_conta:
                    saldos_por_conta = dict(saldos_herdados_por_conta)

                if not conta_filtro:
                    # Saldo inicial definido para uma conta neste mês herdado:
                    # o total muda só pela diferença dessa conta (definido -
                    # herdado no caixa por conta). O mês continua herdado, então
                    # as pendências já abatidas não são descontadas de novo.
                    definidos = saldos_iniciais_definidos_heranca(ano_mes)
                    base_caixa = _saldos_herdados_caixa_reconciliados(ano_mes) if definidos else {}
                    if base_caixa:
                        saldos_definidos_heranca = _aplicar_saldos_definidos_heranca(base_caixa, definidos)
                        saldos_por_conta = dict(saldos_por_conta)
                        for nome, item in saldos_definidos_heranca.items():
                            diferenca = item["definido"] - item["herdado"]
                            saldo_inicial += diferenca
                            chave = next((c for c in saldos_por_conta if mesma_conta_saldo(c, nome)), nome)
                            saldos_por_conta[chave] = float(saldos_por_conta.get(chave, 0.0) or 0.0) + diferenca

    transacoes_mes = list(buscar_transacoes_por_competencia(ano_mes))

    if conta_filtro:
        transacoes_mes = [
            t for t in transacoes_mes
            if mesma_conta_saldo(obter_conta_transacao_saldo(t), conta_filtro)
        ]

    entradas_realizadas = sum(
        float(t["valor"] or 0)
        for t in transacoes_mes
        if t["tipo"] == "receita"
    )

    saidas_imediatas_realizadas = sum(
        float(t["valor"] or 0)
        for t in transacoes_mes
        if t["tipo"] == "despesa" and transacao_afeta_saldo_disponivel(t)
    )

    # Caixa pela data do pagamento (D3); a fatura continua na competência.
    pagamentos_fatura_caixa = [
        mov for mov in pagamentos_fatura_caixa_mes(ano_mes)
        if (not conta_filtro or mesma_conta_saldo(mov["conta_origem"] or "", conta_filtro))
    ]
    saidas_pagamentos_fatura = sum(float(mov["valor"] or 0) for mov in pagamentos_fatura_caixa)
    saidas_imediatas_realizadas += saidas_pagamentos_fatura

    saidas_nao_imediatas_realizadas = sum(
        float(t["valor"] or 0)
        for t in transacoes_mes
        if t["tipo"] == "despesa" and not transacao_afeta_saldo_disponivel(t)
    )

    import conciliacao as conciliacao_motor
    vinculos_anteriores = [v for v in conciliacao_motor.listar_vinculos()
        if v['data'][:7] == ano_mes and v['mes'] < ano_mes
        and (not conta_filtro or mesma_conta_saldo(v['conta'],conta_filtro))]
    pagamentos_competencias_anteriores = sum(v['centavos'] for v in vinculos_anteriores if v['tipo']=='despesa')/100
    receitas_competencias_anteriores = sum(v['centavos'] for v in vinculos_anteriores if v['tipo']=='receita')/100
    ajustes_conciliacao_por_conta = {}
    if saldo_herdado_auto:
        contexto_heranca = _CONTEXTO_HERANCA.get() or {'memo':{}}
        anterior_geral = contexto_heranca['memo'].get(('saldo',obter_mes_anterior(ano_mes),None),{})
        ancora = anterior_geral.get('ano_mes_ancora_saldo')
        for v in vinculos_anteriores:
            # Receita prevista não recebida nunca é herdada como saldo (regra de
            # 09/11/2026). O recebimento vinculado entra uma vez, como entrada
            # realizada; não há o que compensar.
            if v['tipo']=='receita':
                continue
            nome = nome_conta_padrao(v['conta'])
            ajuste = v['centavos']/100 * (1 if v['tipo']=='despesa' else -1)
            ajustes_conciliacao_por_conta[nome] = ajustes_conciliacao_por_conta.get(nome,0)+ajuste
        # Fatura de competência anterior paga neste mês: a herança já trouxe a
        # fatura reservada (abatida); o pagamento sai do caixa agora e não pode
        # descontar de novo (D3). Mesma ideia dos vínculos de despesa acima.
        for mov in pagamentos_fatura_caixa:
            if str(mov["ano_mes"] or "") >= ano_mes:
                continue
            nome = nome_conta_fatura_padrao(mov["conta_origem"] or CONTA_SEM_BANCO_DEFINIDO)
            ajustes_conciliacao_por_conta[nome] = ajustes_conciliacao_por_conta.get(nome, 0) + float(mov["valor"] or 0)
    ajuste_conciliacao_heranca = sum(ajustes_conciliacao_por_conta.values())

    receitas_previstas_herdadas_itens = []
    receitas_previstas_herdadas_suspeitas = []
    if saldo_herdado_auto and permitir_heranca:
        anterior_receitas = calcular_saldo_mensal(obter_mes_anterior(ano_mes), conta_filtro)
        receitas_previstas_herdadas_itens, receitas_previstas_herdadas_suspeitas = (
            _receitas_previstas_herdadas(ano_mes, anterior_receitas))
    receitas_previstas_herdadas_total = sum(
        float(item.get("valor") or 0) for item in receitas_previstas_herdadas_itens)

    entradas_previstas_itens = [
        item for item in projetar_entradas_mes(ano_mes, incluir_transacoes=False)
        if item.get("origem") != "transacao"
    ]

    pagamentos_itens = projetar_pagamentos_mes(ano_mes, incluir_transacoes=True)
    # Pagamento desta fatura feito num mês posterior (D3): o dinheiro ainda não
    # saiu neste mês, então a fatura segue reservada aqui e o pagamento entra
    # no caixa do mês em que ocorreu.
    pagamentos_itens = [item for item in pagamentos_itens
        if not (item.get('origem') == 'fatura_movimento'
                and item.get('tipo_movimento') in {'pagamento_parcial', 'pagamento_total'}
                and str(item.get('data') or '')[:7] > ano_mes)]
    # Liquidação de fatura não é estorno de despesa. Sua compensação pertence
    # somente à ponte de caixa, onde evita descontar a mesma compra duas vezes.
    liquidacoes_fatura = [item for item in pagamentos_itens
        if item.get('origem') == 'fatura_movimento'
        and item.get('tipo_movimento') in {'pagamento_parcial', 'pagamento_total'}]
    despesas_esperadas_itens = [item for item in pagamentos_itens
        if item_esperado_por_origem(item) and item not in liquidacoes_fatura]
    despesas_realizadas_itens = [item for item in pagamentos_itens if item.get("origem") == "transacao"]

    if conta_filtro:
        liquidacoes_fatura = [item for item in liquidacoes_fatura
            if mesma_conta_saldo(obter_conta_item_saldo(item), conta_filtro)]
        entradas_previstas_itens = [
            item for item in entradas_previstas_itens
            if mesma_conta_saldo(obter_conta_item_saldo(item), conta_filtro)
        ]
        despesas_esperadas_itens = [
            item for item in despesas_esperadas_itens
            if mesma_conta_saldo(obter_conta_item_saldo(item), conta_filtro)
        ]
        despesas_realizadas_itens = [
            item for item in despesas_realizadas_itens
            if mesma_conta_saldo(obter_conta_item_saldo(item), conta_filtro)
        ]

    pendencias_herdadas_itens = listar_pendencias_abertas_anteriores(ano_mes, conta_filtro)
    resumo_pendencias_herdadas = resumir_pendencias_herdadas(pendencias_herdadas_itens)
    pendencias_herdadas_total_bruto = float(resumo_pendencias_herdadas.get("total") or 0.0)

    # Se herdamos o saldo livre provável do mês anterior, as obrigações antigas
    # já estão abatidas no saldo inicial. Mantemos a lista visível, mas não
    # descontamos novamente para evitar duplicidade.
    pendencias_herdadas_total = 0.0 if saldo_herdado_auto else pendencias_herdadas_total_bruto

    entradas_previstas = sum(float(item.get("valor") or 0) for item in entradas_previstas_itens)
    despesas_esperadas_total = sum(float(item.get("valor") or 0) for item in despesas_esperadas_itens)
    compensacao_pagamentos_fatura = -sum(float(item.get('valor') or 0) for item in liquidacoes_fatura)
    from reservas_faturas import ajustar_reservas
    ajuste_reserva_faturas, detalhes_reservas_faturas = ajustar_reservas(
        ano_mes, [dict(t) for t in transacoes_mes], despesas_esperadas_itens,
        liquidacoes_fatura, conta_filtro)

    esperado_por_conta = {}
    for item in despesas_esperadas_itens:
        nome = obter_conta_item_saldo(item)
        esperado_por_conta[nome] = esperado_por_conta.get(nome, 0.0) + float(item.get("valor") or 0)

    realizado_por_conta = {}
    for item in despesas_realizadas_itens:
        nome = obter_conta_item_saldo(item)
        realizado_por_conta[nome] = realizado_por_conta.get(nome, 0.0) + float(item.get("valor") or 0)

    transacoes_por_conta = {}
    for t in transacoes_mes:
        nome = obter_conta_transacao_saldo(t)
        if nome not in transacoes_por_conta:
            transacoes_por_conta[nome] = {"entradas": 0.0, "saidas_imediatas": 0.0}
        if t["tipo"] == "receita":
            transacoes_por_conta[nome]["entradas"] += float(t["valor"] or 0)
        elif transacao_afeta_saldo_disponivel(t):
            transacoes_por_conta[nome]["saidas_imediatas"] += float(t["valor"] or 0)

    for mov in pagamentos_fatura_caixa_mes(ano_mes):
        nome = nome_conta_fatura_padrao(mov["conta_origem"] or CONTA_SEM_BANCO_DEFINIDO)
        if conta_filtro and not mesma_conta_saldo(nome, conta_filtro):
            continue
        if nome not in transacoes_por_conta:
            transacoes_por_conta[nome] = {"entradas": 0.0, "saidas_imediatas": 0.0}
        transacoes_por_conta[nome]["saidas_imediatas"] += float(mov["valor"] or 0)

    saldo_disponivel_por_conta = calcular_saldo_disponivel_por_conta(
        saldos_por_conta,
        transacoes_por_conta,
    )
    for nome, ajuste in ajustes_conciliacao_por_conta.items():
        saldo_disponivel_por_conta[nome] = saldo_disponivel_por_conta.get(nome,0)+ajuste

    despesas_realizadas_total = (
        saidas_imediatas_realizadas
        - saidas_pagamentos_fatura
        + saidas_nao_imediatas_realizadas
        - pagamentos_competencias_anteriores
    )

    # Saldo disponível é caixa: só saídas imediatas mexem no dinheiro agora.
    saldo_disponivel = saldo_inicial + entradas_realizadas - saidas_imediatas_realizadas + ajuste_conciliacao_heranca

    # Saldo projetado é competência do mês: considera também crédito/despesas já lançadas,
    # mesmo que não tenham saído do caixa imediatamente.
    saldo_projetado = (
        saldo_disponivel
        + entradas_previstas
        - saidas_nao_imediatas_realizadas
        - despesas_esperadas_total
        - pendencias_herdadas_total
        + compensacao_pagamentos_fatura
        + ajuste_reserva_faturas
        + receitas_previstas_herdadas_total
    )

    extras = {"saldos_iniciais_definidos_heranca": saldos_definidos_heranca} if saldos_definidos_heranca else {}
    return {
        **extras,
        "ano_mes": ano_mes,
        "conta": conta_solicitada,
        "conta_filtro_efetivo": conta_filtro,
        "saldo_centralizado": bool(conta_solicitada and conta_filtro is None),
        "saldo_configurado": saldo_configurado,
        "saldo_inicial": saldo_inicial,
        "saldo_herdado_auto": saldo_herdado_auto,
        "ano_mes_saldo_herdado": ano_mes_saldo_herdado,
        "saldo_herdado_caixa_origem": saldo_herdado_caixa_origem,
        "saldo_herdado_livre_origem": saldo_herdado_livre_origem,
        "saldo_herdado_ajustes_origem": saldo_herdado_ajustes_origem,
        "saldos_por_conta": saldos_por_conta,
        "saldos_herdados_por_conta": saldos_herdados_por_conta,
        "transacoes_por_conta": transacoes_por_conta,
        "saldo_disponivel_por_conta": saldo_disponivel_por_conta,
        "entradas_realizadas": entradas_realizadas,
        "entradas_competencia_mes": entradas_realizadas - receitas_competencias_anteriores,
        "pagamentos_competencias_anteriores": pagamentos_competencias_anteriores,
        "receitas_competencias_anteriores": receitas_competencias_anteriores,
        "ajuste_conciliacao_heranca": ajuste_conciliacao_heranca,
        "ajustes_conciliacao_por_conta": ajustes_conciliacao_por_conta,
        "entradas_previstas": entradas_previstas,
        "entradas_total_mes": entradas_realizadas + entradas_previstas,
        "saidas_imediatas_realizadas": saidas_imediatas_realizadas,
        "saidas_pagamentos_fatura": saidas_pagamentos_fatura,
        "saidas_nao_imediatas_realizadas": saidas_nao_imediatas_realizadas,
        "despesas_realizadas_total": despesas_realizadas_total,
        "despesas_esperadas_total": despesas_esperadas_total,
        "compensacao_pagamentos_fatura": compensacao_pagamentos_fatura,
        "ajuste_reserva_faturas": ajuste_reserva_faturas,
        "detalhes_reservas_faturas": detalhes_reservas_faturas,
        "pendencias_herdadas_total": pendencias_herdadas_total,
        "pendencias_herdadas_total_bruto": pendencias_herdadas_total_bruto,
        "pendencias_herdadas_ja_abatidas_na_heranca": bool(saldo_herdado_auto and pendencias_herdadas_total_bruto > 0),
        "pendencias_herdadas_itens": pendencias_herdadas_itens,
        "resumo_pendencias_herdadas": resumo_pendencias_herdadas,
        "saldo_disponivel": saldo_disponivel,
        "saldo_livre_disponivel": saldo_disponivel - pendencias_herdadas_total,
        "saldo_projetado": saldo_projetado,
        # O que o próximo mês herda: a projeção sem nenhuma receita ainda esperada.
        "saldo_herdavel": saldo_projetado - entradas_previstas - receitas_previstas_herdadas_total,
        "receitas_previstas_herdadas_itens": receitas_previstas_herdadas_itens,
        "receitas_previstas_herdadas_suspeitas": receitas_previstas_herdadas_suspeitas,
        "receitas_previstas_herdadas_total": receitas_previstas_herdadas_total,
        "esperado_por_conta": esperado_por_conta,
        "realizado_por_conta": realizado_por_conta,
        "entradas_previstas_itens": entradas_previstas_itens,
        "despesas_esperadas_itens": despesas_esperadas_itens,
        "despesas_realizadas_itens": despesas_realizadas_itens,
    }


def formatar_top_valores_saldo(titulo: str, valores: dict, limite: int = 4):
    if not valores:
        return [f"{titulo}: R$ 0,00"]

    linhas = [titulo]
    for nome, valor in sorted(valores.items(), key=lambda kv: kv[1], reverse=True)[:limite]:
        linhas.append(f"- {nome}: {formatar_moeda(valor)}")
    return linhas


def formatar_saldos_iniciais_por_conta(saldos: dict):
    if not saldos:
        return ["🏦 Saldo inicial por conta: não configurado"]

    linhas = ["🏦 Saldo inicial por conta"]
    for nome, valor in sorted(saldos.items(), key=lambda kv: kv[0].lower()):
        linhas.append(f"- {nome}: {formatar_moeda(valor)}")
    return linhas



def valor_campo(obj, campo, padrao=None):
    try:
        return obj[campo]
    except Exception:
        try:
            return obj.get(campo, padrao)
        except Exception:
            return padrao


def formatar_item_valor_simples(nome: str, valor: float):
    return f"- {nome}: {formatar_moeda(valor)}"


def gerar_auditoria_despesas_mes(ano_mes: str | None = None, conta: str | None = None):
    ano_mes = validar_ano_mes(ano_mes) if ano_mes else relogio.hoje(date).strftime("%Y-%m")
    conta_filtro = (conta or "").strip() or None

    dados = obter_metricas_resultado_mes(ano_mes, conta_filtro)

    transacoes_mes = list(buscar_transacoes_por_competencia(ano_mes))
    if conta_filtro:
        transacoes_mes = [
            t for t in transacoes_mes
            if mesma_conta_saldo(obter_conta_transacao_saldo(t), conta_filtro)
        ]

    despesas_transacoes = [t for t in transacoes_mes if valor_campo(t, "tipo") == "despesa"]
    imediatas = [t for t in despesas_transacoes if transacao_afeta_saldo_disponivel(t)]
    credito = [t for t in despesas_transacoes if not transacao_afeta_saldo_disponivel(t)]

    pagamentos_itens = projetar_pagamentos_mes(ano_mes, incluir_transacoes=True)
    esperados = [item for item in pagamentos_itens if item_esperado_por_origem(item)]

    if conta_filtro:
        esperados = [
            item for item in esperados
            if mesma_conta_saldo(obter_conta_item_saldo(item), conta_filtro)
        ]

    total_imediatas = sum(float(valor_campo(t, "valor", 0) or 0) for t in imediatas)
    total_credito = sum(float(valor_campo(t, "valor", 0) or 0) for t in credito)
    total_esperados = sum(float(item.get("valor") or 0) for item in esperados)

    pendencias_brutas = float(dados.get("pendencias_herdadas_total_bruto", dados.get("pendencias_herdadas_total", 0.0)) or 0.0)
    pendencias_impacto = float(dados.get("pendencias_herdadas_total", 0.0) or 0.0)

    titulo_conta = f" — {formatar_nome_conta_saldo(conta_filtro)}" if conta_filtro else ""
    linhas = [
        f"🔎 De onde vêm as despesas{titulo_conta} — {formatar_ano_mes_visual(ano_mes)}",
        "",
        "Resumo:",
        formatar_item_valor_simples("Saídas imediatas já pagas", total_imediatas),
        formatar_item_valor_simples("Crédito já lançado", total_credito),
        formatar_item_valor_simples("Ainda esperado no mês", total_esperados),
        formatar_item_valor_simples("Pendências antigas abertas", pendencias_brutas),
    ]

    if dados.get("pendencias_herdadas_ja_abatidas_na_heranca"):
        linhas.append("Obs.: as pendências antigas já foram abatidas no saldo livre herdado, então não entram de novo no saldo livre provável.")
    elif pendencias_impacto > 0:
        linhas.append(formatar_item_valor_simples("Pendências antigas impactando este mês", pendencias_impacto))

    linhas.extend([
        "",
        "Interpretação:",
        "Saídas imediatas já pagas = Pix, débito, dinheiro ou transferência que já saíram do caixa.",
        "Crédito já lançado = gasto registrado no cartão/crédito; compromete o saldo livre, mas ainda não saiu do caixa.",
        "Ainda esperado = fixos, compromissos, parcelas e faturas previstas para o mês.",
        "",
        "Isso não significa que tudo isso é boleto para pagar agora.",
    ])

    def adicionar_top_transacoes(titulo: str, itens: list, limite: int = 8):
        linhas.extend(["", titulo])
        if not itens:
            linhas.append("- Nenhum item.")
            return
        itens_ordenados = sorted(itens, key=lambda t: float(valor_campo(t, "valor", 0) or 0), reverse=True)
        for t in itens_ordenados[:limite]:
            desc = valor_campo(t, "descricao") or valor_campo(t, "categoria") or "Sem descrição"
            conta_nome = obter_conta_transacao_saldo(t)
            forma = valor_campo(t, "forma_pagamento") or "sem forma"
            linhas.append(f"- #{valor_campo(t, 'id')} · {desc} · {formatar_moeda(valor_campo(t, 'valor', 0))} · {conta_nome} · {forma}")
        restante = len(itens_ordenados) - limite
        if restante > 0:
            linhas.append(f"+{restante} item(ns)")

    def adicionar_top_esperados(titulo: str, itens: list, limite: int = 10):
        linhas.extend(["", titulo])
        if not itens:
            linhas.append("- Nenhum item.")
            return
        itens_ordenados = sorted(itens, key=lambda i: float(i.get("valor") or 0), reverse=True)
        for item in itens_ordenados[:limite]:
            nome = item.get("nome") or item.get("descricao") or item.get("categoria") or "Item"
            origem = item.get("origem") or "esperado"
            conta_nome = obter_conta_item_saldo(item)
            linhas.append(f"- {nome} · {formatar_moeda(item.get('valor') or 0)} · {conta_nome} · {origem}")
        restante = len(itens_ordenados) - limite
        if restante > 0:
            linhas.append(f"+{restante} item(ns)")

    adicionar_top_transacoes("Saídas imediatas já pagas:", imediatas)
    adicionar_top_transacoes("Crédito já lançado:", credito)
    adicionar_top_esperados("Ainda esperado no mês:", esperados)

    linhas.extend([
        "",
        "Comandos úteis:",
        f"saldo geral {ano_mes}",
        f"checklist {ano_mes}",
        f"pendências abertas {ano_mes}",
        f"auditar despesas {ano_mes}",
    ])

    return "\n".join(linhas)


def parsear_comando_auditoria_despesas(texto_limpo: str):
    texto = normalizar_texto(texto_limpo)

    match = re.match(
        r"^(?:de onde vem as despesas|de onde vêm as despesas|detalhar despesas|auditar despesas|auditoria despesas|despesas detalhadas)(?:\s+(\d{4}-\d{2}))?(?:\s+(.+))?$",
        texto
    )
    if not match:
        return None

    ano_mes = validar_ano_mes(match.group(1)) if match.group(1) else relogio.hoje(date).strftime("%Y-%m")
    conta = (match.group(2) or "").strip() or None

    if conta and eh_alias_saldo_geral(conta):
        conta = None

    return ano_mes, conta



def parsear_comando_dashboard(texto_limpo: str):
    texto = normalizar_texto(texto_limpo)
    match = re.match(r"^(?:dashboard|dash|painel)(?:\s+(.+))?$", texto)

    if not match:
        return None

    alvo = (match.group(1) or "").strip()

    if not alvo:
        return relogio.hoje(date).strftime("%Y-%m")

    ano_mes = None

    try:
        ano_mes = normalizar_ano_mes_flexivel(alvo)
    except Exception:
        ano_mes = None

    if not ano_mes:
        ano_mes = validar_ano_mes(alvo)

    return ano_mes or relogio.hoje(date).strftime("%Y-%m")


def _dashboard_cor(hex_color: str):
    hex_color = str(hex_color or "").strip().lstrip("#")
    if len(hex_color) != 6:
        return (0, 0, 0)
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _dashboard_texto(draw, xy, texto, fonte, fill="#111827"):
    draw.text(xy, str(texto), font=fonte, fill=_dashboard_cor(fill))


def _dashboard_retangulo(draw, xy, fill="#ffffff", outline=None, radius=18):
    fill_rgb = _dashboard_cor(fill)
    outline_rgb = _dashboard_cor(outline) if outline else None
    try:
        draw.rounded_rectangle(xy, radius=radius, fill=fill_rgb, outline=outline_rgb, width=1 if outline else 0)
    except Exception:
        draw.rectangle(xy, fill=fill_rgb, outline=outline_rgb)


def _dashboard_barra(draw, x, y, largura, altura, valor, maximo, cor, fundo="#e5e7eb"):
    _dashboard_retangulo(draw, (x, y, x + largura, y + altura), fill=fundo, radius=8)
    if maximo and maximo > 0 and valor > 0:
        w = int(largura * min(float(valor) / float(maximo), 1.0))
        if w > 0:
            _dashboard_retangulo(draw, (x, y, x + w, y + altura), fill=cor, radius=8)


def _dashboard_carregar_fonte(tamanho: int, negrito: bool = False):
    from PIL import ImageFont

    candidatos = []
    if negrito:
        candidatos.extend(["DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"])
    candidatos.extend(["DejaVuSans.ttf", "Arial.ttf", "arial.ttf"])

    for nome in candidatos:
        try:
            return ImageFont.truetype(nome, tamanho)
        except Exception:
            continue

    return ImageFont.load_default()


def gerar_dashboard_visual_mes(ano_mes: str | None = None):
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")

    ano_mes = validar_ano_mes(ano_mes) or relogio.hoje(date).strftime("%Y-%m")
    dados = obter_metricas_resultado_mes(ano_mes)

    saidas_mes = projetar_pagamentos_mes(ano_mes, incluir_transacoes=True)
    categorias = agrupar_itens_por_campo(saidas_mes, obter_categoria_item)[:5]
    contas = agrupar_itens_por_campo(saidas_mes, obter_conta_item)

    inicio = date(int(ano_mes[:4]), int(ano_mes[5:7]), 1)
    meses_base = [somar_meses(inicio, i).strftime("%Y-%m") for i in range(0, 4)]

    futuro = []
    for mes in meses_base:
        metrica = obter_metricas_resultado_mes(mes)
        futuro.append((mes, metrica["resultado_projetado_mes"]))

    try:
        from PIL import Image, ImageDraw
    except Exception:
        return {
            "texto": (
                "📈 Dashboard visual indisponível\n\n"
                "Para gerar imagem PNG, instale a dependência:\n"
                "pip install pillow\n\n"
                f"Enquanto isso, use: meu mês {ano_mes}"
            )
        }

    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)

    largura = 1080
    contas_card_h = max(330, 105 + 43 * max(len(contas), 5))
    altura = max(1650, 1190 + contas_card_h + 130)
    margem = 50

    img = Image.new("RGB", (largura, altura), _dashboard_cor("#f3f4f6"))
    draw = ImageDraw.Draw(img)

    fonte_titulo = _dashboard_carregar_fonte(46, True)
    fonte_sub = _dashboard_carregar_fonte(24, False)
    fonte_card_titulo = _dashboard_carregar_fonte(26, True)
    fonte_numero = _dashboard_carregar_fonte(34, True)
    fonte_normal = _dashboard_carregar_fonte(24, False)
    fonte_pequena = _dashboard_carregar_fonte(20, False)
    fonte_mini = _dashboard_carregar_fonte(18, False)

    resultado = dados["resultado_projetado_mes"]
    cor_resultado = "#16a34a" if resultado >= 0 else "#dc2626"
    status = "POSITIVO" if resultado >= 0 else "NEGATIVO"

    _dashboard_texto(draw, (margem, 38), "Dashboard Financeiro", fonte_titulo, "#111827")
    _dashboard_texto(draw, (margem, 92), formatar_ano_mes_visual(ano_mes), fonte_sub, "#6b7280")

    _dashboard_retangulo(draw, (margem, 135, largura - margem, 330), fill="#ffffff", outline="#e5e7eb", radius=26)
    _dashboard_texto(draw, (margem + 30, 165), "Resultado do mês", fonte_card_titulo, "#374151")
    _dashboard_texto(draw, (margem + 30, 205), formatar_sinal_moeda(resultado), fonte_titulo, cor_resultado)
    _dashboard_retangulo(draw, (largura - margem - 220, 170, largura - margem - 35, 245), fill=cor_resultado, radius=20)
    _dashboard_texto(draw, (largura - margem - 185, 194), status, fonte_card_titulo, "#ffffff")
    _dashboard_texto(draw, (margem + 30, 275), "Entradas - despesas realizadas - despesas esperadas", fonte_pequena, "#6b7280")

    card_y = 365
    card_w = (largura - 2 * margem - 24) // 3
    cards = [
        ("Entradas", dados["total_entradas_mes"], "#16a34a"),
        ("Despesas", dados["total_saidas_mes"], "#dc2626"),
        ("Fechamento", dados["saldo_projetado"], "#2563eb" if dados["saldo_projetado"] >= 0 else "#dc2626"),
    ]

    for i, (titulo, valor, cor) in enumerate(cards):
        x = margem + i * (card_w + 12)
        _dashboard_retangulo(draw, (x, card_y, x + card_w, card_y + 155), fill="#ffffff", outline="#e5e7eb", radius=22)
        _dashboard_texto(draw, (x + 22, card_y + 24), titulo, fonte_normal, "#4b5563")
        texto_valor = formatar_sinal_moeda(valor) if titulo != "Entradas" else formatar_moeda(valor)
        _dashboard_texto(draw, (x + 22, card_y + 70), texto_valor, fonte_numero, cor)

    y = 555
    _dashboard_retangulo(draw, (margem, y, largura - margem, y + 235), fill="#ffffff", outline="#e5e7eb", radius=24)
    _dashboard_texto(draw, (margem + 28, y + 25), "Entradas x despesas", fonte_card_titulo, "#111827")

    max_bar = max(dados["total_entradas_mes"], dados["total_saidas_realizadas_mes"], dados["despesas_esperadas_total"], 1)
    barras = [
        ("Entradas", dados["total_entradas_mes"], "#16a34a"),
        ("Despesas realizadas", dados["total_saidas_realizadas_mes"], "#dc2626"),
        ("Despesas esperadas", dados["despesas_esperadas_total"], "#f97316"),
    ]
    by = y + 75
    for nome, valor, cor in barras:
        _dashboard_texto(draw, (margem + 28, by - 4), nome, fonte_pequena, "#374151")
        _dashboard_texto(draw, (largura - margem - 205, by - 4), formatar_moeda(valor), fonte_pequena, "#374151")
        _dashboard_barra(draw, margem + 28, by + 28, largura - 2 * margem - 56, 20, valor, max_bar, cor)
        by += 55

    y = 825
    _dashboard_retangulo(draw, (margem, y, largura - margem, y + 330), fill="#ffffff", outline="#e5e7eb", radius=24)
    _dashboard_texto(draw, (margem + 28, y + 24), "Top categorias", fonte_card_titulo, "#111827")
    total_cat = max(sum(v for _, v in categorias), 1)
    by = y + 76
    for nome, valor in categorias[:5]:
        _dashboard_texto(draw, (margem + 28, by), str(nome)[:28], fonte_pequena, "#374151")
        _dashboard_texto(draw, (largura - margem - 205, by), formatar_moeda(valor), fonte_pequena, "#374151")
        _dashboard_barra(draw, margem + 28, by + 34, largura - 2 * margem - 56, 18, valor, total_cat, "#7c3aed")
        by += 50

    y = 1190
    box_w = (largura - 2 * margem - 24) // 2
    _dashboard_retangulo(draw, (margem, y, margem + box_w, y + contas_card_h), fill="#ffffff", outline="#e5e7eb", radius=24)
    _dashboard_retangulo(draw, (margem + box_w + 24, y, largura - margem, y + contas_card_h), fill="#ffffff", outline="#e5e7eb", radius=24)

    _dashboard_texto(draw, (margem + 24, y + 24), "Contas do mês", fonte_card_titulo, "#111827")
    by = y + 78
    for nome, valor in contas:
        _dashboard_texto(draw, (margem + 24, by), str(nome)[:18], fonte_mini, "#374151")
        _dashboard_texto(draw, (margem + box_w - 185, by), formatar_moeda(valor), fonte_mini, "#374151")
        by += 43

    x2 = margem + box_w + 24
    _dashboard_texto(draw, (x2 + 24, y + 24), "Próximos meses", fonte_card_titulo, "#111827")
    by = y + 78
    for mes, valor in futuro:
        cor = "#16a34a" if valor >= 0 else "#dc2626"
        _dashboard_texto(draw, (x2 + 24, by), formatar_ano_mes_visual(mes).split("/")[0].title()[:10], fonte_mini, "#374151")
        _dashboard_texto(draw, (x2 + box_w - 210, by), formatar_sinal_moeda(valor), fonte_mini, cor)
        by += 50

    _dashboard_texto(draw, (margem, altura - 65), "Gerado pelo Assessor Financeiro Pessoal", fonte_mini, "#9ca3af")

    nome_arquivo = f"dashboard_{ano_mes}_{relogio.agora().strftime('%Y%m%d_%H%M%S')}.png"
    caminho = DASHBOARDS_DIR / nome_arquivo
    img.save(caminho, "PNG", optimize=True)

    legenda = (
        f"📈 Dashboard — {formatar_ano_mes_visual(ano_mes)}\n\n"
        f"Resultado do mês: {formatar_status_saldo(resultado)}\n"
        f"Fechamento provável: {formatar_status_saldo(dados['saldo_projetado'])}"
    )

    return {"texto": legenda, "imagem": str(caminho)}


def parsear_comando_dashboard_categorias(texto_limpo: str):
    texto = normalizar_texto(texto_limpo)
    padroes = [
        r"^(?:dashboard|dash|painel)\s+(?:categorias|categoria)(?:\s+(.+))?$",
        r"^(?:categorias|categoria)\s+(?:dashboard|dash|painel)(?:\s+(.+))?$",
        r"^(?:dashboard|dash|painel)\s+(?:por\s+)?(?:categorias|categoria)(?:\s+(.+))?$",
    ]

    for padrao in padroes:
        match = re.match(padrao, texto)
        if not match:
            continue

        alvo = (match.group(1) or "").strip()
        if not alvo:
            return relogio.hoje(date).strftime("%Y-%m")

        ano_mes = None

        try:
            ano_mes = normalizar_ano_mes_flexivel(alvo)
        except Exception:
            ano_mes = None

        if not ano_mes:
            ano_mes = validar_ano_mes(alvo)

        return ano_mes or relogio.hoje(date).strftime("%Y-%m")

    return None


def _dashboard_quebrar_texto(texto: str, limite: int):
    texto = str(texto or "")
    if len(texto) <= limite:
        return texto

    if limite <= 1:
        return texto[:limite]

    return texto[:limite - 1].rstrip() + "…"


def gerar_dashboard_categorias_visual_mes(ano_mes: str | None = None):
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")

    ano_mes = validar_ano_mes(ano_mes) or relogio.hoje(date).strftime("%Y-%m")
    saidas_mes = projetar_pagamentos_mes(ano_mes, incluir_transacoes=True)
    categorias = agrupar_itens_por_campo(saidas_mes, obter_categoria_item)
    total = sum(valor for _, valor in categorias)

    try:
        from PIL import Image, ImageDraw
    except Exception:
        return {
            "texto": (
                "🏷 Dashboard de categorias indisponível\n\n"
                "Para gerar imagem PNG, instale a dependência:\n"
                "pip install pillow\n\n"
                f"Enquanto isso, use: categorias {ano_mes}"
            )
        }

    if total <= 0 or not categorias:
        return {
            "texto": f"🏷 Dashboard de categorias — {formatar_ano_mes_visual(ano_mes)}\n\nNão encontrei despesas no mês.",
        }

    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)

    cores = [
        "#7c3aed", "#2563eb", "#16a34a", "#f97316", "#dc2626",
        "#0891b2", "#ca8a04", "#db2777", "#4f46e5", "#65a30d",
        "#9333ea", "#0f766e", "#ea580c", "#be123c", "#64748b",
    ]

    qtd = len(categorias)
    altura = max(1450, 760 + qtd * 58)
    largura = 1080
    margem = 50

    img = Image.new("RGB", (largura, altura), _dashboard_cor("#f3f4f6"))
    draw = ImageDraw.Draw(img)

    fonte_titulo = _dashboard_carregar_fonte(44, True)
    fonte_sub = _dashboard_carregar_fonte(22, False)
    fonte_card_titulo = _dashboard_carregar_fonte(26, True)
    fonte_numero = _dashboard_carregar_fonte(34, True)
    fonte_normal = _dashboard_carregar_fonte(23, False)
    fonte_pequena = _dashboard_carregar_fonte(19, False)
    fonte_mini = _dashboard_carregar_fonte(17, False)

    maior_categoria, maior_valor = categorias[0]
    top3 = sum(valor for _, valor in categorias[:3])
    top3_pct = (top3 / total * 100) if total else 0

    _dashboard_texto(draw, (margem, 36), "Dashboard de Categorias", fonte_titulo, "#111827")
    _dashboard_texto(draw, (margem, 88), formatar_ano_mes_visual(ano_mes), fonte_sub, "#6b7280")

    # Cards resumo
    card_y = 132
    card_w = (largura - 2 * margem - 24) // 3
    cards = [
        ("Total despesas", formatar_moeda(total), "#dc2626"),
        ("Maior categoria", _dashboard_quebrar_texto(maior_categoria, 16), "#7c3aed"),
        ("Top 3 concentram", f"{top3_pct:.1f}%".replace(".", ","), "#2563eb"),
    ]

    for i, (titulo, valor, cor) in enumerate(cards):
        x = margem + i * (card_w + 12)
        _dashboard_retangulo(draw, (x, card_y, x + card_w, card_y + 160), fill="#ffffff", outline="#e5e7eb", radius=22)
        _dashboard_texto(draw, (x + 20, card_y + 24), titulo, fonte_pequena, "#4b5563")
        _dashboard_texto(draw, (x + 20, card_y + 68), valor, fonte_numero if i != 1 else fonte_card_titulo, cor)

    # Card pizza
    y = 330
    pizza_card_h = 505
    _dashboard_retangulo(draw, (margem, y, largura - margem, y + pizza_card_h), fill="#ffffff", outline="#e5e7eb", radius=26)
    _dashboard_texto(draw, (margem + 28, y + 24), "Distribuição por categoria", fonte_card_titulo, "#111827")

    cx = margem + 275
    cy = y + 285
    raio = 175
    bbox = (cx - raio, cy - raio, cx + raio, cy + raio)

    inicio = -90
    for idx, (categoria, valor) in enumerate(categorias):
        angulo = 360 * (valor / total)
        cor = cores[idx % len(cores)]
        draw.pieslice(bbox, start=inicio, end=inicio + angulo, fill=_dashboard_cor(cor), outline=_dashboard_cor("#ffffff"), width=2)
        inicio += angulo

    # Furo central para estilo donut
    _dashboard_retangulo(draw, (cx - 72, cy - 72, cx + 72, cy + 72), fill="#ffffff", radius=72)
    _dashboard_texto(draw, (cx - 58, cy - 18), "Total", fonte_pequena, "#6b7280")
    _dashboard_texto(draw, (cx - 83, cy + 10), formatar_moeda(total), fonte_pequena, "#111827")

    # Legenda lateral
    legenda_x = margem + 530
    legenda_y = y + 92
    _dashboard_texto(draw, (legenda_x, y + 58), "Legenda", fonte_normal, "#111827")

    for idx, (categoria, valor) in enumerate(categorias[:9]):
        pct = valor / total * 100 if total else 0
        yy = legenda_y + idx * 42
        cor = cores[idx % len(cores)]
        _dashboard_retangulo(draw, (legenda_x, yy + 5, legenda_x + 24, yy + 29), fill=cor, radius=6)
        _dashboard_texto(draw, (legenda_x + 34, yy), _dashboard_quebrar_texto(categoria, 18), fonte_mini, "#374151")
        _dashboard_texto(draw, (largura - margem - 155, yy), f"{pct:.1f}%".replace(".", ","), fonte_mini, "#374151")

    if len(categorias) > 9:
        _dashboard_texto(draw, (legenda_x + 34, legenda_y + 9 * 42), f"+{len(categorias) - 9} categorias", fonte_mini, "#6b7280")

    # Ranking completo
    y = y + pizza_card_h + 35
    ranking_h = max(420, 100 + qtd * 54)
    _dashboard_retangulo(draw, (margem, y, largura - margem, y + ranking_h), fill="#ffffff", outline="#e5e7eb", radius=26)
    _dashboard_texto(draw, (margem + 28, y + 24), "Ranking de categorias", fonte_card_titulo, "#111827")

    maximo = max(valor for _, valor in categorias) if categorias else 1
    by = y + 78

    for idx, (categoria, valor) in enumerate(categorias, start=1):
        pct = valor / total * 100 if total else 0
        cor = cores[(idx - 1) % len(cores)]
        nome = _dashboard_quebrar_texto(categoria, 25)

        _dashboard_texto(draw, (margem + 28, by), f"{idx:02d}. {nome}", fonte_pequena, "#374151")
        _dashboard_texto(draw, (largura - margem - 275, by), formatar_moeda(valor), fonte_pequena, "#374151")
        _dashboard_texto(draw, (largura - margem - 85, by), f"{pct:.1f}%".replace(".", ","), fonte_pequena, "#374151")
        _dashboard_barra(draw, margem + 28, by + 30, largura - 2 * margem - 56, 16, valor, maximo, cor)
        by += 54

    # Rodapé
    _dashboard_texto(draw, (margem, altura - 62), "Gerado pelo Assessor Financeiro Pessoal", fonte_mini, "#9ca3af")

    nome_arquivo = f"dashboard_categorias_{ano_mes}_{relogio.agora().strftime('%Y%m%d_%H%M%S')}.png"
    caminho = DASHBOARDS_DIR / nome_arquivo
    img.save(caminho, "PNG", optimize=True)

    legenda = (
        f"🏷 Dashboard categorias — {formatar_ano_mes_visual(ano_mes)}\n\n"
        f"Total de despesas: {formatar_moeda(total)}\n"
        f"Maior categoria: {maior_categoria} · {formatar_moeda(maior_valor)}"
    )

    return {
        "texto": legenda,
        "imagem": str(caminho),
    }



def _linhas_saldos_definidos_heranca(dados: dict):
    """Linhas do saldo herdado quando uma conta teve o saldo inicial definido
    neste mês (as demais seguem com o valor herdado)."""
    definidos = dados.get("saldos_iniciais_definidos_heranca") or {}
    saldo_inicial = float(dados.get("saldo_inicial", 0.0) or 0.0)
    diferenca = sum(float(item["definido"]) - float(item["herdado"]) for item in definidos.values())
    linhas = [f"Saldo livre herdado: {formatar_moeda(saldo_inicial - diferenca)}"]
    for nome, item in sorted(definidos.items(), key=lambda kv: kv[0].lower()):
        linhas.append(
            f"✏️ {nome}: saldo inicial definido em {formatar_moeda(item['definido'])} "
            f"(herdado: {formatar_moeda(item['herdado'])})"
        )
    linhas.append(f"Saldo inicial do mês: {formatar_moeda(saldo_inicial)}")
    return linhas


def bloco_heranca_mes_anterior(dados: dict, compacto: bool = False):
    """
    Bloco visual para deixar claro no 'meu mês' de onde veio o saldo inicial
    e se existem pendências antigas sendo carregadas.
    """
    linhas = []
    if dados.get('ajuste_conciliacao_heranca'):
        linhas.append('Ajuste de previsões já herdadas: '+formatar_moeda(dados['ajuste_conciliacao_heranca']))
    if dados.get('revisoes_conciliacao'):
        linhas.append('⚠️ Há situações de conciliação a revisar. Confira /menu → Revisar antes de usar a sobra prevista.')

    if dados.get("saldo_herdado_auto"):
        mes_origem = dados.get("ano_mes_saldo_herdado")
        livre_origem = float(dados.get("saldo_herdado_livre_origem", dados.get("saldo_inicial", 0.0)) or 0.0)

        linhas.append(f"🔁 Herança de {formatar_ano_mes_visual(mes_origem)}")
        if dados.get("saldos_iniciais_definidos_heranca"):
            linhas.extend(_linhas_saldos_definidos_heranca(dados))
        else:
            linhas.append(f"Saldo livre herdado: {formatar_moeda(livre_origem)}")
    elif dados.get("saldo_configurado"):
        linhas.append("🏦 Saldo inicial configurado manualmente")
        linhas.append(f"Valor inicial: {formatar_moeda(dados.get('saldo_inicial', 0.0))}")
    else:
        linhas.append("⚠️ Saldo inicial não configurado")
        linhas.append(f"Usando R$ 0,00 como início de {formatar_ano_mes_visual(dados.get('ano_mes'))}.")

    pendencias = float(dados.get("pendencias_herdadas_total", 0.0) or 0.0)
    pendencias_brutas = float(dados.get("pendencias_herdadas_total_bruto", pendencias) or 0.0)

    if pendencias > 0:
        linhas.append(f"Pendências antigas em aberto: -{formatar_moeda(pendencias)}")
        linhas.append(f"Saldo livre inicial: {formatar_moeda(dados.get('saldo_inicial', 0.0) - pendencias)}")
    elif pendencias_brutas > 0 and dados.get("pendencias_herdadas_ja_abatidas_na_heranca"):
        linhas.append(f"Pendências antigas em aberto: {formatar_moeda(pendencias_brutas)}")
        linhas.append("Status: já abatidas no saldo livre herdado")
    else:
        linhas.append("Pendências antigas em aberto: R$ 0,00")

    if not compacto and dados.get("pendencias_herdadas_itens"):
        linhas.append("")
        linhas.append("Principais pendências herdadas:")
        for item in dados.get("pendencias_herdadas_itens", [])[:5]:
            codigo = item.get("codigo_origem") or item.get("codigo") or item.get("chave")
            mes = item.get("ano_mes_origem")
            nome = item.get("nome") or "Item"
            valor = float(item.get("valor") or 0)
            linhas.append(f"- {codigo} · {nome} · {formatar_moeda(valor)} · {formatar_ano_mes_visual(mes)}")

    return "\n".join(linhas)




CONTAS_VIRTUAIS_CAIXA = {
    "pix",
    "debito",
    "débito",
    "dinheiro",
    "transferencia",
    "transferência",
    "credito",
    "crédito",
    "cartao",
    "cartão",
    "nao informada",
    "não informada",
    "",
}

CONTA_SEM_BANCO_DEFINIDO = "Sem conta definida"


def conta_virtual_caixa(nome: str | None):
    nome_norm = normalizar_texto(nome or "").lower().strip()
    return nome_norm in CONTAS_VIRTUAIS_CAIXA


def normalizar_conta_caixa(nome: str | None):
    """
    Para caixa, Pix/débito/dinheiro/transferência não são contas.
    São formas de saída/entrada imediata.

    Se o lançamento não informa o banco real, cai como "Sem conta definida",
    para o usuário corrigir a conta do lançamento.
    """
    nome_limpo = (nome or "").strip()
    if conta_virtual_caixa(nome_limpo):
        return CONTA_SEM_BANCO_DEFINIDO
    return formatar_nome_conta_saldo(nome_limpo)


def obter_conta_caixa_transacao(transacao):
    return normalizar_conta_caixa(transacao["conta"] or "")


def saldos_iniciais_caixa_configurados(ano_mes: str):
    saldos = {}
    for conta, valor in (obter_saldos_iniciais_por_conta(ano_mes) or {}).items():
        conta_caixa = normalizar_conta_caixa(conta)
        if conta_caixa == CONTA_SEM_BANCO_DEFINIDO:
            # Nunca carregar Pix/débito/dinheiro/transferência como conta de caixa.
            continue
        saldos[conta_caixa] = saldos.get(conta_caixa, 0.0) + float(valor or 0.0)
    return saldos


def movimentos_caixa_por_conta_mes(ano_mes: str):
    movimentos = {}
    saidas_sem_conta = 0.0
    entradas_sem_conta = 0.0

    for t in buscar_transacoes_por_mes(ano_mes):
        conta = obter_conta_caixa_transacao(t)

        if conta not in movimentos:
            movimentos[conta] = {"entradas": 0.0, "saidas_imediatas": 0.0}

        if t["tipo"] == "receita":
            valor = float(t["valor"] or 0)
            movimentos[conta]["entradas"] += valor
            if conta == CONTA_SEM_BANCO_DEFINIDO:
                entradas_sem_conta += valor

        elif t["tipo"] == "despesa" and transacao_afeta_saldo_disponivel(t):
            valor = float(t["valor"] or 0)
            movimentos[conta]["saidas_imediatas"] += valor
            if conta == CONTA_SEM_BANCO_DEFINIDO:
                saidas_sem_conta += valor

    for mov in pagamentos_fatura_caixa_mes(ano_mes):
        conta_origem = normalizar_conta_caixa(mov["conta_origem"])
        valor = float(mov["valor"] or 0)
        if conta_origem not in movimentos:
            movimentos[conta_origem] = {"entradas": 0.0, "saidas_imediatas": 0.0}
        movimentos[conta_origem]["saidas_imediatas"] += valor
        if conta_origem == CONTA_SEM_BANCO_DEFINIDO:
            saidas_sem_conta += valor

    for tr in buscar_transferencias_caixa_por_mes(ano_mes):
        origem = normalizar_conta_caixa(tr["conta_origem"])
        destino = normalizar_conta_caixa(tr["conta_destino"])
        valor = float(tr["valor"] or 0)

        if origem != CONTA_SEM_BANCO_DEFINIDO:
            if origem not in movimentos:
                movimentos[origem] = {"entradas": 0.0, "saidas_imediatas": 0.0}
            movimentos[origem]["saidas_imediatas"] += valor

        if destino != CONTA_SEM_BANCO_DEFINIDO:
            if destino not in movimentos:
                movimentos[destino] = {"entradas": 0.0, "saidas_imediatas": 0.0}
            movimentos[destino]["entradas"] += valor

    return movimentos, entradas_sem_conta, saidas_sem_conta



def parsear_valor_transferencia(texto: str):
    try:
        return parse_money_float(texto)
    except (TypeError, ValueError):
        return None


def limpar_conta_comando_transferencia(texto: str):
    """Remove apenas palavras de ligação ditadas antes da conta real."""
    conta = str(texto or "").strip(" .,;:!?")
    conta = re.sub(
        r"^(?:a|o)?\s*conta(?:\s+(?:corrente|bancaria|bancária))?\s+(?:do|da|de)\s+",
        "",
        conta,
        flags=re.IGNORECASE,
    ).strip()
    # "para o nubank": o artigo ditado não faz parte do nome da conta.
    sem_artigo = re.sub(r"^(?:o|a)\s+(?=\S)", "", conta, flags=re.IGNORECASE).strip()
    return sem_artigo or conta


def parsear_comando_transferencia_caixa(texto_original: str):
    texto = normalizar_texto(texto_original or "").strip()

    padroes = [
        r"^(?:transferi|transferir|transfere|transferencia|transferência)\s+r?\$?\s*([0-9][0-9\.\,]*)\s+(?:reais\s+)?(?:da|do|de)\s+(.+?)\s+(?:para|pra)\s+(.+?)(?:\s+em\s+(\d{4}-\d{2}-\d{2}))?$",
        r"^(?:mover|movimentar|passei)\s+r?\$?\s*([0-9][0-9\.\,]*)\s+(?:reais\s+)?(?:da|do|de)\s+(.+?)\s+(?:para|pra)\s+(.+?)(?:\s+em\s+(\d{4}-\d{2}-\d{2}))?$",
    ]

    for padrao in padroes:
        match = re.match(padrao, texto)
        if not match:
            continue

        valor = parsear_valor_transferencia(match.group(1))
        origem = normalizar_conta_caixa(limpar_conta_comando_transferencia(match.group(2)))
        destino = normalizar_conta_caixa(limpar_conta_comando_transferencia(match.group(3)))
        data = match.group(4) or relogio.hoje(date).isoformat()

        if not valor or valor <= 0:
            return {"erro": "valor"}

        if origem == CONTA_SEM_BANCO_DEFINIDO or destino == CONTA_SEM_BANCO_DEFINIDO:
            return {"erro": "conta"}

        if mesma_conta_saldo(origem, destino):
            return {"erro": "mesma_conta"}

        return {
            "valor": valor,
            "conta_origem": origem,
            "conta_destino": destino,
            "data": data,
            "descricao": f"Transferência de {origem} para {destino}",
            "mensagem_original": texto_original,
        }

    return None


def registrar_transferencia_caixa_formatado(texto_original: str):
    transferencia = parsear_comando_transferencia_caixa(texto_original)

    if not transferencia:
        return None

    if transferencia.get("erro") == "valor":
        return "Não consegui registrar a transferência. Valor inválido. Exemplo: transferi 100 do Itaú para Caju"

    if transferencia.get("erro") == "conta":
        return (
            "Não consegui registrar a transferência porque origem ou destino não é uma conta de caixa válida.\\n\\n"
            "Pix, débito, dinheiro e transferência são formas, não contas.\\n\\n"
            "Exemplo válido:\\n"
            "transferi 100 do Itaú para Caju"
        )

    if transferencia.get("erro") == "mesma_conta":
        return "Não registrei a transferência porque origem e destino são a mesma conta."

    try:
        transferencia_id = inserir_transferencia_caixa(transferencia)
    except ValueError as exc:
        # D7: data inexistente (ex.: 2026-02-30) ou valor fora do limite.
        return f"Não registrei a transferência. {exc}"

    return "\n".join([
        "🔁 Transferência registrada no caixa",
        "",
        f"#{transferencia_id}",
        f"Data: {formatar_data_visual(transferencia['data'])}",
        f"Valor: {formatar_moeda(transferencia['valor'])}",
        f"Origem: {transferencia['conta_origem']}",
        f"Destino: {transferencia['conta_destino']}",
        "",
        "Essa transferência mexe apenas no caixa por conta.",
        "Não entra como receita, despesa, Meu mês, categorias ou checklist.",
        "",
        f"Para conferir: caixa {transferencia['data'][:7]}",
    ])


def listar_transferencias_caixa_formatado(ano_mes: str | None = None):
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")

    transferencias = buscar_transferencias_caixa_por_mes(ano_mes)

    linhas = [
        f"🔁 Transferências de caixa — {formatar_ano_mes_visual(ano_mes)}",
        "",
    ]

    if not transferencias:
        linhas.extend([
            "Não encontrei transferências de caixa neste mês.",
            "",
            "Exemplo:",
            "transferi 100 do Itaú para Caju",
        ])
        return "\n".join(linhas)

    total = sum(float(t["valor"] or 0) for t in transferencias)
    linhas.append(f"Total movimentado entre contas: {formatar_moeda(total)}")
    linhas.append("")

    for t in transferencias:
        linhas.append(
            f"#{t['id']} | {formatar_data_visual(t['data'])} | {formatar_moeda(t['valor'])} | "
            f"{t['conta_origem']} → {t['conta_destino']}"
        )

    linhas.extend([
        "",
        "Para remover uma transferência:",
        "apagar transferencia caixa ID",
    ])

    return "\n".join(linhas)


def apagar_transferencia_caixa_formatado(transferencia_id: int):
    apagados = apagar_transferencia_caixa_por_id(transferencia_id)

    if apagados:
        return f"🗑️ Transferência de caixa #{transferencia_id} apagada."

    return f"Não encontrei transferência de caixa #{transferencia_id}."



def _saldos_herdados_caixa_reconciliados(ano_mes: str, profundidade: int = 0):
    """Saldo inicial herdado por conta (caixa) de um mês sem base própria.

    Parte do disponível por conta do mês anterior e reconcilia o total com o
    saldo livre provável desse mês. Devolve {} quando não há o que herdar.
    """
    mes_anterior = obter_mes_anterior(ano_mes)
    anterior = calcular_caixa_por_conta_mes(mes_anterior, permitir_heranca=True, profundidade=profundidade + 1)

    saldos_base = {
        conta: float(item.get("disponivel", 0.0) or 0.0)
        for conta, item in anterior.get("contas", {}).items()
        if conta != CONTA_SEM_BANCO_DEFINIDO and not conta_virtual_caixa(conta)
    }

    if saldos_base:
        # O caixa por conta precisa bater com o mesmo saldo inicial livre usado em "meu mês".
        #
        # O mês anterior pode ter caixa bruto por banco maior do que o saldo livre provável,
        # porque o saldo livre já desconta faturas, crédito lançado, pendências e esperado.
        # Como nem sempre sabemos de qual banco cada obrigação antiga sairia, reconciliamos
        # a diferença no maior saldo positivo. Assim o TOTAL do caixa por conta bate com
        # "Saldo livre herdado" de meu mês, sem inventar uma conta Pix ou herdar caixa bruto.
        try:
            saldo_mes_anterior = calcular_saldo_mensal(mes_anterior, permitir_heranca=True)
            # Mesmo valor herdado por "meu mês": sem receita prevista não recebida.
            saldo_livre_anterior = float(saldo_mes_anterior.get(
                "saldo_herdavel", saldo_mes_anterior.get("saldo_projetado", sum(saldos_base.values()))) or 0.0)
        except Exception:
            _LOG_CALCULOS.warning(
                "Caixa por conta (%s): saldo livre de %s indisponível; usando a soma dos saldos.",
                ano_mes, mes_anterior, exc_info=True,
            )
            saldo_livre_anterior = sum(saldos_base.values())

        total_caixa_anterior = sum(float(v or 0.0) for v in saldos_base.values())
        ajuste_livre = saldo_livre_anterior - total_caixa_anterior

        if abs(ajuste_livre) >= 0.005:
            positivos = [c for c in saldos_base if float(saldos_base.get(c, 0.0) or 0.0) > 0.005]
            if positivos:
                conta_ajuste = max(positivos, key=lambda c: float(saldos_base.get(c, 0.0) or 0.0))
            else:
                # Sem saldo positivo: mantém o critério anterior (maior saldo absoluto).
                conta_ajuste = max(saldos_base, key=lambda c: abs(float(saldos_base.get(c, 0.0) or 0.0)))
            saldos_base[conta_ajuste] = float(saldos_base.get(conta_ajuste, 0.0) or 0.0) + ajuste_livre

    return saldos_base


# Saldo inicial de UMA conta definido em mês que herda o saldo do anterior.
# Fica como evento de auditoria (o último evento de cada mês/conta vale), sem
# criar base em saldos_mensais_contas: uma base desligaria a herança do mês e
# as pendências herdadas, já abatidas no saldo livre herdado, seriam
# descontadas de novo. Meses anteriores não mudam; os seguintes herdam.
ENTIDADE_SALDO_INICIAL_HERANCA = "saldo_inicial_heranca_conta"


def saldos_iniciais_definidos_heranca(ano_mes: str):
    """{conta: saldo inicial definido} para o mês (vale o evento mais recente)."""
    import json

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT dados_depois FROM auditoria_eventos WHERE entidade = ? AND entidade_id LIKE ? ORDER BY id",
            (ENTIDADE_SALDO_INICIAL_HERANCA, f"{ano_mes}:%"),
        ).fetchall()
    definidos = {}
    for row in rows:
        dados = json.loads(row[0] or "null") or {}
        conta = normalizar_conta_caixa(dados.get("conta"))
        if conta == CONTA_SEM_BANCO_DEFINIDO:
            continue
        chave = next((nome for nome in definidos if mesma_conta_saldo(nome, conta)), conta)
        if dados.get("removido"):
            # A conta volta a herdar do mês anterior.
            definidos.pop(chave, None)
            continue
        if dados.get("saldo_inicial") is None:
            continue
        definidos[chave] = float(dados["saldo_inicial"])
    return definidos


def _aplicar_saldos_definidos_heranca(saldos_base: dict, definidos: dict):
    """Troca, em saldos_base, o valor herdado das contas definidas pelo valor
    definido. Devolve {conta: {"herdado": x, "definido": y}}."""
    aplicados = {}
    for conta, valor in definidos.items():
        chave = next((nome for nome in saldos_base if mesma_conta_saldo(nome, conta)), conta)
        herdado = float(saldos_base.get(chave, 0.0) or 0.0)
        saldos_base[chave] = float(valor)
        aplicados[chave] = {"herdado": herdado, "definido": float(valor)}
    return aplicados


def _calcular_caixa_por_conta_etapa(ano_mes: str, permitir_heranca: bool = True, profundidade: int = 0):
    """
    Calcula caixa por conta/banco de forma conservadora.

    Regra:
    - Se o mês tem saldo inicial por conta configurado, usa esse saldo.
    - Se não tem, herda o que SOBROU no caixa por conta do mês anterior.
    - Nunca herda "Pix" como conta, porque Pix é forma de pagamento.
    - Se um lançamento Pix não informa o banco de origem, aparece como
      "Sem conta definida" para correção, mas não vira conta Pix.
    """
    ano_mes = validar_ano_mes(ano_mes) or relogio.hoje(date).strftime("%Y-%m")

    saldos_configurados = saldos_iniciais_caixa_configurados(ano_mes)
    herdado_auto = False
    mes_origem = None
    saldos_definidos_heranca = {}

    if saldos_configurados:
        saldos_base = dict(saldos_configurados)
    elif permitir_heranca:
        mes_anterior = obter_mes_anterior(ano_mes)
        saldos_base = _saldos_herdados_caixa_reconciliados(ano_mes, profundidade)

        if saldos_base:
            herdado_auto = True
            mes_origem = mes_anterior
            # Saldo inicial definido para uma conta neste mês herdado: só essa
            # conta muda; as demais seguem com o valor herdado. Aplicado só
            # quando o "meu mês" deste mês também herda (ele aplica a mesma
            # diferença no total), para os dois continuarem batendo.
            contexto = _CONTEXTO_HERANCA.get() or {'memo':{}}
            if contexto['memo'].get(('saldo',ano_mes,None),{}).get('saldo_herdado_auto'):
                saldos_definidos_heranca = _aplicar_saldos_definidos_heranca(
                    saldos_base, saldos_iniciais_definidos_heranca(ano_mes))
    else:
        saldos_base = {}

    movimentos, entradas_sem_conta, saidas_sem_conta = movimentos_caixa_por_conta_mes(ano_mes)
    contexto = _CONTEXTO_HERANCA.get() or {'memo':{}}
    resumo_mes_canonico = contexto['memo'].get(('saldo',ano_mes,None),{})
    ajustes_conciliacao = resumo_mes_canonico.get('ajustes_conciliacao_por_conta',{}) if herdado_auto else {}

    contas = set(saldos_base.keys()) | set(movimentos.keys())
    contas.discard(CONTA_SEM_BANCO_DEFINIDO)

    contas_resultado = {}
    for conta in sorted(contas, key=lambda c: c.lower()):
        inicial = float(saldos_base.get(conta, 0.0) or 0.0)
        mov = movimentos.get(conta, {}) or {}
        entradas = float(mov.get("entradas", 0.0) or 0.0)
        saidas = float(mov.get("saidas_imediatas", 0.0) or 0.0)
        ajuste_conciliacao = sum(v for nome,v in ajustes_conciliacao.items() if mesma_conta_saldo(nome,conta))
        disponivel = inicial + entradas - saidas + ajuste_conciliacao

        if abs(inicial) < 0.005 and abs(entradas) < 0.005 and abs(saidas) < 0.005 and abs(disponivel) < 0.005:
            continue

        contas_resultado[conta] = {
            "inicial": inicial,
            "entradas": entradas,
            "saidas": saidas,
            "ajuste_conciliacao_heranca": ajuste_conciliacao,
            "disponivel": disponivel,
        }

    total_inicial = sum(item["inicial"] for item in contas_resultado.values())
    total_entradas = sum(item["entradas"] for item in contas_resultado.values())
    total_saidas = sum(item["saidas"] for item in contas_resultado.values())
    total_disponivel = sum(item["disponivel"] for item in contas_resultado.values())

    sem_conta = movimentos.get(CONTA_SEM_BANCO_DEFINIDO, {"entradas": 0.0, "saidas_imediatas": 0.0})

    extras = {"saldos_iniciais_definidos_heranca": saldos_definidos_heranca} if saldos_definidos_heranca else {}
    return {
        **extras,
        "ano_mes": ano_mes,
        "contas": contas_resultado,
        "total_inicial": total_inicial,
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "total_disponivel": total_disponivel,
        "herdado_auto": herdado_auto,
        "mes_origem": mes_origem,
        "sem_conta": {
            "entradas": float(sem_conta.get("entradas", 0.0) or 0.0),
            "saidas": float(sem_conta.get("saidas_imediatas", 0.0) or 0.0),
            "entradas_sem_conta": entradas_sem_conta,
            "saidas_sem_conta": saidas_sem_conta,
        },
    }


def gerar_caixa_por_conta_mes(ano_mes: str | None = None):
    """
    Mostra dinheiro em caixa por banco/conta.

    "contas" continua sendo a visão de obrigações/gastos.
    "caixa" é a visão de dinheiro disponível.
    """
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")

    caixa = calcular_caixa_por_conta_mes(ano_mes)

    linhas = [
        f"🏦 Caixa por conta — {formatar_ano_mes_visual(ano_mes)}",
        "",
        bloco_total("Resumo do caixa", [
            linha_valor("Saldo inicial", caixa["total_inicial"]),
            linha_sinal_valor("Entradas realizadas", caixa["total_entradas"]),
            linha_sinal_valor("Saídas imediatas", -caixa["total_saidas"]),
            linha_status_valor("Disponível em caixa", caixa["total_disponivel"]),
        ]),
    ]

    definidos_heranca = caixa.get("saldos_iniciais_definidos_heranca") or {}
    if caixa.get("herdado_auto") and definidos_heranca:
        linhas.extend([
            "",
            f"🔁 Herança reconciliada com {formatar_ano_mes_visual(caixa.get('mes_origem'))}. "
            "Saldo inicial definido neste mês (as outras contas seguem herdadas):",
        ])
        for nome, item in sorted(definidos_heranca.items(), key=lambda kv: kv[0].lower()):
            linhas.append(
                f"✏️ {nome}: {formatar_moeda(item['definido'])} (herdado: {formatar_moeda(item['herdado'])})"
            )
    elif caixa.get("herdado_auto"):
        linhas.extend([
            "",
            f"🔁 Herança reconciliada com {formatar_ano_mes_visual(caixa.get('mes_origem'))}: o total bate com o Saldo livre herdado do Meu mês.",
        ])

    sem_conta = caixa.get("sem_conta", {})
    entradas_sem_conta = float(sem_conta.get("entradas", 0.0) or 0.0)
    saidas_sem_conta = float(sem_conta.get("saidas", 0.0) or 0.0)

    if abs(entradas_sem_conta) > 0.005 or abs(saidas_sem_conta) > 0.005:
        linhas.extend([
            "",
            "⚠️ Lançamentos sem banco definido",
        ])
        if abs(entradas_sem_conta) > 0.005:
            linhas.append(f"Entradas sem conta: {formatar_moeda(entradas_sem_conta)}")
        if abs(saidas_sem_conta) > 0.005:
            linhas.append(f"Saídas imediatas sem conta: -{formatar_moeda(saidas_sem_conta)}")
        # O "Disponível em caixa" acima soma só as contas reais; o Meu mês
        # também desconta/soma estes lançamentos. Mostramos os dois números.
        disponivel_com_sem_conta = caixa["total_disponivel"] + entradas_sem_conta - saidas_sem_conta
        linhas.append(
            f"Disponível em caixa considerando estes lançamentos: {formatar_moeda(disponivel_com_sem_conta)}"
        )
        linhas.extend([
            "Pix/débito/dinheiro/transferência são formas, não contas.",
            "Corrija a conta do lançamento para Itaú, Mercado Pago, Caju, BTG etc.",
        ])

    if not caixa["contas"]:
        linhas.extend([
            "",
            "Não encontrei saldo ou movimentação de caixa por banco neste mês.",
            "",
            "Para configurar no mês atual:",
            "Contas e saldos → Ajustar saldos atuais (valor que aparece agora no banco).",
            "",
            "Ou informe o saldo inicial de cada conta neste mês:",
            f"ajustar saldo {ano_mes} Itaú para 1000",
            f"ajustar saldo {ano_mes} Caju para 800",
        ])
        return "\n".join(linhas)

    linhas.extend(["", "Contas:"])

    for conta, item in sorted(caixa["contas"].items(), key=lambda kv: kv[1]["disponivel"], reverse=True):
        linhas.extend([
            "",
            f"🏦 {conta}",
            f"Saldo inicial: {formatar_moeda(item['inicial'])}",
            f"Entradas: {formatar_moeda(item['entradas'])}",
            f"Saídas imediatas: -{formatar_moeda(item['saidas'])}",
            f"Disponível: {formatar_status_saldo(item['disponivel'])}",
        ])

    return "\n".join(linhas)


def parsear_comando_caixa_por_conta(texto_limpo: str):
    texto = normalizar_texto(texto_limpo)

    if texto in [
        "caixa",
        "meu caixa",
        "caixa por conta",
        "saldo das contas",
        "saldos das contas",
        "saldo dos bancos",
        "saldos dos bancos",
        "dinheiro em caixa",
        "dinheiro nas contas",
        "dinheiro nos bancos",
        "meu dinheiro",
        "meu dinheiro em caixa",
    ]:
        return relogio.hoje(date).strftime("%Y-%m")

    match = re.match(
        r"^(?:caixa|meu caixa|caixa por conta|saldo das contas|saldos das contas|saldo dos bancos|saldos dos bancos|dinheiro em caixa|dinheiro nas contas|dinheiro nos bancos|meu dinheiro|meu dinheiro em caixa)\s+(\d{4}-\d{2})$",
        texto
    )
    if match:
        return validar_ano_mes(match.group(1))

    return None





def gerar_saldo_mes_ux(ano_mes: str | None = None, conta: str | None = None):
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")

    dados = obter_metricas_resultado_mes(ano_mes, conta)
    titulo_conta = f" — {conta}" if conta else ""

    linhas = [
        f"🏦 Saldo do mês{titulo_conta} — {formatar_ano_mes_visual(ano_mes)}",
        "",
    ]

    if dados.get("saldo_centralizado"):
        linhas.extend([
            "🏦 Visão centralizada: o Itaú considera todas as obrigações do mês,",
            "inclusive faturas de outros cartões pagas por essa conta.",
            "",
        ])

    if dados.get("saldo_herdado_auto"):
        mes_origem = dados.get("ano_mes_saldo_herdado")

        if dados.get("saldos_iniciais_definidos_heranca"):
            linhas.extend([
                f"🔁 Saldo livre herdado automaticamente de {formatar_ano_mes_visual(mes_origem)}.",
                *_linhas_saldos_definidos_heranca(dados),
                "",
            ])
        else:
            linhas.extend([
                f"🔁 Saldo livre herdado automaticamente de {formatar_ano_mes_visual(mes_origem)}.",
                f"Saldo livre herdado: {formatar_moeda(dados['saldo_inicial'])}",
                "",
            ])
    elif not dados["saldo_configurado"]:
        if conta:
            exemplo = f"saldo inicial {ano_mes} {conta} 1000"
        else:
            exemplo = f"saldo inicial {ano_mes} 1000"

        linhas.extend([
            "⚠️ Saldo inicial ainda não configurado.",
            "",
            "Não encontrei saldo inicial neste mês nem saldo configurado no mês anterior.",
            "",
            "Para começar certo, envie:",
            exemplo,
            "",
            "Enquanto isso, estou calculando como se o saldo inicial fosse R$ 0,00.",
            "",
        ])

    if dados.get("pendencias_herdadas_total", 0.0) > 0:
        linhas.extend([
            *formatar_resumo_pendencias_herdadas(dados.get("pendencias_herdadas_itens", []), limite=6),
            "",
        ])

    linhas.extend([
        bloco_resultado_mes(dados),
        "",
        bloco_caixa_acumulado(dados),
    ])

    if not conta:
        linhas.extend(["", *formatar_saldos_iniciais_por_conta(dados["saldos_por_conta"])])

    if dados["esperado_por_conta"]:
        linhas.extend(["", *formatar_top_valores_saldo("🟠 Esperado por conta", dados["esperado_por_conta"])])

    if dados["realizado_por_conta"]:
        linhas.extend(["", *formatar_top_valores_saldo("🔴 Realizado por conta", dados["realizado_por_conta"])])

    # Resultado objetivo: sem recomendações genéricas.

    if dados.get('ajuste_conciliacao_heranca'):
        linhas += ['', 'Ajuste de previsões já herdadas: '+formatar_moeda(dados['ajuste_conciliacao_heranca'])]
    if dados.get('revisoes_conciliacao'):
        linhas += ['', '⚠️ Há baixas antigas ou receitas sem vínculo para revisar. Abra /menu → Revisar antes de usar a sobra prevista.']

    return "\n".join(linhas)


def _mes_tem_base_inicial_de_outra_origem(ano_mes: str) -> bool:
    """True quando o mês ainda não tem base por conta, mas já tem saldo inicial
    vindo de outro lugar (base geral do mês ou herança automática do mês
    anterior). Nesse caso, gravar a base de UMA conta pelo comando de texto
    interromperia a herança/base geral e zeraria o saldo inicial das demais."""
    if buscar_saldos_contas_mes(ano_mes):
        return False
    if buscar_saldo_mensal(ano_mes):
        return True
    if calcular_caixa_por_conta_mes(ano_mes).get("herdado_auto"):
        return True
    return bool(calcular_saldo_mensal(ano_mes).get("saldo_herdado_auto"))


_MSG_SALDO_INICIAL_CONTA_COM_HERANCA = (
    'Este mês usa um saldo inicial geral, sem divisão por conta (definido neste mês '
    'ou herdado de um mês sem saldos por conta).\n'
    'Gravar o saldo inicial de uma só conta por este comando zeraria o saldo inicial das outras.\n'
    'Abra Contas e saldos → Ajustar saldos atuais e informe o dinheiro que está agora em cada banco.'
)

_MSG_SALDOS_MES_MUDARAM = 'Os saldos deste mês mudaram enquanto eu gravava. Nada foi alterado; envie o comando de novo.'


def _mes_herda_saldo_por_conta(ano_mes: str) -> bool:
    """True quando o mês não tem base própria (nem por conta nem geral) e herda
    do mês anterior um saldo dividido por conta."""
    if buscar_saldos_contas_mes(ano_mes) or buscar_saldo_mensal(ano_mes):
        return False
    return bool(calcular_caixa_por_conta_mes(ano_mes).get("herdado_auto")
                and calcular_saldo_mensal(ano_mes).get("saldo_herdado_auto"))


def _definir_saldo_inicial_conta_herdada(ano_mes: str, conta: str, valor: float):
    """Define o saldo inicial de UMA conta em mês que herda o saldo.

    Não cria base em saldos_mensais_contas (isso desligaria a herança de todas
    as contas e descontaria de novo as pendências já abatidas no saldo livre
    herdado). Grava um evento de auditoria que o cálculo aplica sobre a
    herança: só essa conta muda neste mês, os meses seguintes herdam o novo
    valor e os anteriores não mudam.

    valor None (ou igual ao herdado) remove a definição: a conta volta a
    herdar e as correções feitas depois nos meses anteriores voltam a chegar.
    """
    conta = normalizar_conta_caixa(conta)
    if conta == CONTA_SEM_BANCO_DEFINIDO:
        raise ValueError('Informe uma conta real (Itaú, Mercado Pago, Caju...). '
                         'Pix, débito, dinheiro e transferência são formas de pagamento, não contas.')
    remover = valor is None
    valor = None if remover else float(valor)
    with fatura_write_transaction() as conn:
        # Releitura sob o bloqueio de escrita: nenhuma base pode ter surgido.
        if (conn.execute("SELECT 1 FROM saldos_mensais_contas WHERE ano_mes = ? LIMIT 1", (ano_mes,)).fetchone()
                or conn.execute("SELECT 1 FROM saldos_mensais WHERE ano_mes = ?", (ano_mes,)).fetchone()):
            raise ValueError(_MSG_SALDOS_MES_MUDARAM)
        caixa = calcular_caixa_por_conta_mes(ano_mes)
        saldo = calcular_saldo_mensal(ano_mes)
        if not caixa.get("herdado_auto") or not saldo.get("saldo_herdado_auto"):
            raise ValueError(_MSG_SALDOS_MES_MUDARAM)
        contas = caixa.get("contas") or {}
        chave = next((nome for nome in contas if mesma_conta_saldo(nome, conta)), None)
        atual = float((contas.get(chave) or {}).get("inicial", 0.0) or 0.0) if chave else 0.0
        definido = next((item for nome, item in (caixa.get("saldos_iniciais_definidos_heranca") or {}).items()
                         if mesma_conta_saldo(nome, conta)), None)
        herdado = float(definido["herdado"]) if definido else atual
        total_antes = float(saldo.get("saldo_inicial", 0.0) or 0.0)
        if not remover and definido and abs(valor - herdado) < 0.005:
            # Definir o mesmo valor herdado = voltar a herdar.
            remover = True
        if remover:
            if not definido:
                raise ValueError(
                    f"{chave or conta} já usa o saldo herdado em {formatar_ano_mes_visual(ano_mes)}. Nada foi alterado.")
            total_depois = total_antes + (herdado - atual)
            registrar_auditoria(
                ENTIDADE_SALDO_INICIAL_HERANCA, f"{ano_mes}:{conta}", "saldo_inicial_herdado",
                {"conta": conta, "saldo_inicial": atual, "saldo_herdado": herdado,
                 "saldo_inicial_mes": total_antes},
                {"conta": conta, "removido": True, "saldo_inicial": None, "saldo_herdado": herdado,
                 "saldo_inicial_mes": total_depois, "mes_origem": caixa.get("mes_origem")},
                "telegram", None, conn=conn,
            )
            return {"conta": conta, "anterior": atual, "herdado": herdado, "valor": herdado, "removido": True,
                    "total_antes": total_antes, "total_depois": total_depois, "mes_origem": caixa.get("mes_origem")}
        total_depois = total_antes + (valor - atual)
        registrar_auditoria(
            ENTIDADE_SALDO_INICIAL_HERANCA, f"{ano_mes}:{conta}", "saldo_inicial_definido",
            {"conta": conta, "saldo_inicial": atual, "saldo_herdado": herdado,
             "definido_anterior": float(definido["definido"]) if definido else None,
             "saldo_inicial_mes": total_antes},
            {"conta": conta, "saldo_inicial": valor, "saldo_herdado": herdado,
             "saldo_inicial_mes": total_depois, "mes_origem": caixa.get("mes_origem")},
            "telegram", None, conn=conn,
        )
    return {"conta": conta, "anterior": atual, "herdado": herdado, "valor": valor,
            "total_antes": total_antes, "total_depois": total_depois, "mes_origem": caixa.get("mes_origem")}


def _valor_para_comando(valor: float) -> str:
    return f"{float(valor):.2f}".replace(".", ",")


def _gravar_saldo_inicial_conta_auditado(ano_mes: str, conta: str, valor: float):
    """Grava a base de uma conta em mês que já usa bases por conta, sincroniza a
    base geral (soma das bases, como em saldos_edicao) e audita na mesma transação."""
    from decimal import Decimal

    conta = (conta or "Geral").strip() or "Geral"
    agora = relogio.agora().isoformat(timespec="seconds")
    with fatura_write_transaction() as conn:
        conn.row_factory = sqlite3.Row
        bases = conn.execute("SELECT * FROM saldos_mensais_contas WHERE ano_mes = ?", (ano_mes,)).fetchall()
        if not bases:
            # Nenhuma base existia na verificação anterior? Então só pode ser a
            # primeira configuração; se surgiu herança/base geral no meio, recusa.
            if conn.execute("SELECT 1 FROM saldos_mensais WHERE ano_mes = ?", (ano_mes,)).fetchone():
                raise ValueError(_MSG_SALDO_INICIAL_CONTA_COM_HERANCA)
        existente = next((row for row in bases if str(row["conta"]).lower() == conta.lower()), None)
        geral_antes = conn.execute("SELECT * FROM saldos_mensais WHERE ano_mes = ?", (ano_mes,)).fetchone()
        if existente:
            conn.execute(
                "UPDATE saldos_mensais_contas SET saldo_inicial = ?, observacao = ?, atualizado_em = ? WHERE id = ?",
                (valor, "Definido pelo Telegram.", agora, existente["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO saldos_mensais_contas (ano_mes, conta, saldo_inicial, observacao, criado_em, atualizado_em) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ano_mes, conta, valor, "Definido pelo Telegram.", agora, agora),
            )
        total = float(sum(
            (Decimal(str(row[0] or 0)) for row in conn.execute(
                "SELECT saldo_inicial FROM saldos_mensais_contas WHERE ano_mes = ?", (ano_mes,))),
            Decimal("0"),
        ))
        nota_geral = "Sincronizado com a base de saldos por conta definida pelo Telegram."
        if geral_antes:
            conn.execute(
                "UPDATE saldos_mensais SET saldo_inicial = ?, observacao = ?, atualizado_em = ? WHERE ano_mes = ?",
                (total, nota_geral, agora, ano_mes),
            )
        else:
            conn.execute(
                "INSERT INTO saldos_mensais (ano_mes, saldo_inicial, observacao, criado_em, atualizado_em) VALUES (?, ?, ?, ?, ?)",
                (ano_mes, total, nota_geral, agora, agora),
            )
        registrar_auditoria(
            "saldo_conta", f"{ano_mes}:{conta}", "saldo_inicial_comando_texto",
            {"conta": dict(existente) if existente else None, "geral": dict(geral_antes) if geral_antes else None},
            {"conta": conta, "base_conta": float(valor), "base_geral": total},
            "telegram", None, conn=conn,
        )
        return conn.execute(
            "SELECT * FROM saldos_mensais_contas WHERE ano_mes = ? AND lower(conta) = lower(?)", (ano_mes, conta)
        ).fetchone()


def _gravar_saldo_inicial_geral_auditado(ano_mes: str, valor: float):
    """Mesma gravação de definir_saldo_inicial_mes, com auditoria na mesma transação."""
    agora = relogio.agora().isoformat(timespec="seconds")
    with fatura_write_transaction() as conn:
        conn.row_factory = sqlite3.Row
        if conn.execute("SELECT 1 FROM saldos_mensais_contas WHERE ano_mes = ? LIMIT 1", (ano_mes,)).fetchone():
            raise ValueError('Este mês usa saldos por conta. Um saldo inicial geral separado não substituiria essas bases.\n'
                             'Abra Contas e saldos → Ajustar saldos atuais e informe o dinheiro que está agora em cada banco.')
        antes = conn.execute("SELECT * FROM saldos_mensais WHERE ano_mes = ?", (ano_mes,)).fetchone()
        if antes:
            conn.execute(
                "UPDATE saldos_mensais SET saldo_inicial = ?, observacao = ?, atualizado_em = ? WHERE ano_mes = ?",
                (valor, "Definido pelo Telegram.", agora, ano_mes),
            )
        else:
            conn.execute(
                "INSERT INTO saldos_mensais (ano_mes, saldo_inicial, observacao, criado_em, atualizado_em) VALUES (?, ?, ?, ?, ?)",
                (ano_mes, valor, "Definido pelo Telegram.", agora, agora),
            )
        registrar_auditoria(
            "saldo_mensal", ano_mes, "saldo_inicial_comando_texto",
            dict(antes) if antes else None, {"saldo_inicial": float(valor)},
            "telegram", None, conn=conn,
        )
        return conn.execute("SELECT * FROM saldos_mensais WHERE ano_mes = ?", (ano_mes,)).fetchone()


def definir_saldo_inicial_formatado(ano_mes: str, valor: float, conta: str | None = None):
    conta_limpa = (conta or "").strip()

    if not conta_limpa and buscar_saldos_contas_mes(ano_mes):
        return ('Este mês usa saldos por conta. Um saldo inicial geral separado não substituiria essas bases.\n'
                'Abra Contas e saldos → Ajustar saldos atuais e informe o dinheiro que está agora em cada banco.')

    if valor is None:
        # "saldo inicial <mês> <conta> herdado": só existe em mês que herda.
        if not (conta_limpa and _mes_herda_saldo_por_conta(ano_mes)):
            return (f"{formatar_ano_mes_visual(ano_mes)} não herda o saldo do mês anterior por conta; "
                    "não há saldo herdado para voltar. Nada foi alterado.")

    if conta_limpa:
        # Mês que herda o saldo por conta: muda só esta conta, sobre a herança
        # (os meses seguintes herdam o novo valor; os anteriores não mudam).
        if _mes_herda_saldo_por_conta(ano_mes):
            try:
                r = _definir_saldo_inicial_conta_herdada(ano_mes, conta_limpa, valor)
            except ValueError as exc:
                return str(exc)
            if r.get("removido"):
                return "\n".join([
                    "🔁 Saldo inicial voltou a ser herdado",
                    "",
                    f"Mês: {formatar_ano_mes_visual(ano_mes)}",
                    f"Conta: {r['conta']}",
                    f"Saldo inicial: {formatar_moeda(r['herdado'])} (herdado de "
                    f"{formatar_ano_mes_visual(r['mes_origem'])}; antes: {formatar_moeda(r['anterior'])})",
                    f"Saldo inicial do mês: {formatar_moeda(r['total_antes'])} → {formatar_moeda(r['total_depois'])}",
                    "",
                    "Correções feitas nos meses anteriores voltam a chegar a esta conta.",
                    "",
                    "Agora use:",
                    f"caixa {ano_mes}",
                ])
            return "\n".join([
                "🏦 Saldo inicial definido",
                "",
                f"Mês: {formatar_ano_mes_visual(ano_mes)}",
                f"Conta: {r['conta']}",
                f"Saldo inicial: {formatar_moeda(r['valor'])} (antes: {formatar_moeda(r['anterior'])})",
                f"Saldo inicial do mês: {formatar_moeda(r['total_antes'])} → {formatar_moeda(r['total_depois'])}",
                "",
                f"As outras contas continuam com o saldo herdado de {formatar_ano_mes_visual(r['mes_origem'])}.",
                "Os meses seguintes herdam este novo saldo; os meses anteriores não mudam.",
                "",
                "Para voltar a herdar o saldo desta conta, envie:",
                f"saldo inicial {ano_mes} {r['conta']} herdado",
                "",
                "Agora use:",
                f"caixa {ano_mes}",
            ])
        # B3: em mês com saldo inicial geral (sem divisão por conta), a
        # primeira base por conta substituiria esse valor e zeraria as outras
        # contas. Aqui só gravamos quando o mês já usa bases por conta ou
        # quando não há nenhuma base/herança a perder (primeira configuração).
        if _mes_tem_base_inicial_de_outra_origem(ano_mes):
            return _MSG_SALDO_INICIAL_CONTA_COM_HERANCA
        try:
            registro = _gravar_saldo_inicial_conta_auditado(ano_mes, formatar_nome_conta_saldo(conta_limpa), valor)
        except ValueError as exc:
            return str(exc)
        return "\n".join([
            "🏦 Saldo inicial definido",
            "",
            f"Mês: {formatar_ano_mes_visual(ano_mes)}",
            f"Conta: {registro['conta']}",
            f"Saldo inicial: {formatar_moeda(registro['saldo_inicial'])}",
            "",
            "Agora use:",
            f"saldo {ano_mes} {registro['conta']}",
        ])

    try:
        registro = _gravar_saldo_inicial_geral_auditado(ano_mes, valor)
    except ValueError as exc:
        return str(exc)
    return "\n".join([
        "🏦 Saldo inicial definido",
        "",
        f"Mês: {formatar_ano_mes_visual(ano_mes)}",
        f"Saldo inicial geral: {formatar_moeda(registro['saldo_inicial'])}",
        "",
        "Este mês passa a usar um saldo inicial geral, sem divisão por conta.",
        "Por isso, o saldo inicial por conta deste mês não é aceito por comando",
        "(ele substituiria este valor). No mês atual, use Contas e saldos →",
        "Ajustar saldos atuais para informar o dinheiro de cada banco.",
        "",
        "Agora use:",
        f"saldo do mês {ano_mes}",
    ])


def _converter_valor_saldo_conta(valor_texto: str):
    try:
        valor = parse_money_float(valor_texto, allow_negative=True)
    except (TypeError, ValueError):
        return None
    return valor if abs(valor) <= 100000000 else None


def parsear_comando_saldo_inicial(texto_limpo: str):
    # Formatos com conta:
    # saldo inicial BTG 1000
    # saldo inicial 2026-06 BTG 1000
    # ajustar saldo BTG para 1000
    # ajustar saldo 2026-06 BTG para 1000
    # Voltar a herdar o saldo de uma conta (desfaz o saldo inicial definido
    # em mês que herda): "saldo inicial 2026-11 Mercado Pago herdado".
    match = re.match(r"^saldo inicial\s+(?:(\d{4}-\d{2})\s+)?(.+?)\s+herdad[oa]$", texto_limpo)
    if match:
        ano_mes = validar_ano_mes(match.group(1)) if match.group(1) else relogio.hoje(date).strftime("%Y-%m")
        conta = match.group(2).strip()
        if ano_mes and conta and not re.match(r"^\d{4}-\d{2}$", conta):
            return ano_mes, None, conta

    padroes_conta = [
        r"^saldo inicial\s+(\d{4}-\d{2})\s+(.+?)\s+(-?[0-9][0-9\.,]*)$",
        r"^saldo inicial\s+(.+?)\s+(-?[0-9][0-9\.,]*)$",
        r"^ajustar saldo\s+(\d{4}-\d{2})\s+(.+?)\s+para\s+(.+)$",
        r"^ajustar saldo\s+(.+?)\s+para\s+(.+)$",
        r"^corrigir saldo\s+(\d{4}-\d{2})\s+(.+?)\s+para\s+(.+)$",
        r"^corrigir saldo\s+(.+?)\s+para\s+(.+)$",
    ]

    for padrao in padroes_conta:
        match = re.match(padrao, texto_limpo)
        if not match:
            continue

        grupos = match.groups()

        if len(grupos) == 3:
            ano_mes = validar_ano_mes(grupos[0])
            conta = grupos[1].strip()
            valor_texto = grupos[2]
        else:
            conta = grupos[0].strip()
            valor_texto = grupos[1]

            # Caso especial: "saldo inicial 2026-07 2000" é saldo geral do mês,
            # não conta chamada "2026-07".
            if re.match(r"^\d{4}-\d{2}$", conta):
                ano_mes = validar_ano_mes(conta)
                conta = None
            else:
                ano_mes = relogio.hoje(date).strftime("%Y-%m")

        # Se o "conta" for só um número, é saldo geral do mês atual.
        if conta and converter_valor_texto(conta) is not None:
            valor = converter_valor_texto(conta)
            if valor is not None:
                return ano_mes, valor, None

        # Saldo de uma conta pode ser zero ou negativo (ex.: desfazer um
        # saldo inicial definido voltando ao valor anterior).
        valor = _converter_valor_saldo_conta(valor_texto) if conta else converter_valor_texto(valor_texto)
        if ano_mes and valor is not None:
            return ano_mes, valor, conta

    # Formatos gerais explícitos:
    # saldo inicial 2026-06 1000
    # ajustar saldo para 1000
    padroes_gerais = [
        r"^saldo inicial\s+(\d{4}-\d{2})\s+(.+)$",
        r"^saldo inicial\s+(.+)$",
        r"^ajustar saldo\s+para\s+(.+)$",
        r"^corrigir saldo\s+para\s+(.+)$",
    ]

    for padrao in padroes_gerais:
        match = re.match(padrao, texto_limpo)
        if not match:
            continue

        grupos = match.groups()

        if len(grupos) == 2:
            ano_mes = validar_ano_mes(grupos[0])
            valor_texto = grupos[1]
        else:
            ano_mes = relogio.hoje(date).strftime("%Y-%m")
            valor_texto = grupos[0]

        valor = converter_valor_texto(valor_texto)
        if ano_mes and valor is not None:
            return ano_mes, valor, None

    return None


def gerar_tela_registrar_ux():
    return "\n".join([
        "➕ Registrar",
        "",
        "Escolha um botão abaixo ou envie uma frase simples.",
        "",
        "Botões recomendados:",
        "💸 Despesa",
        "💰 Entrada",
        "🧾 Fixo mensal",
        "💳 Compra parcelada",
        "",
        "Exemplos se preferir digitar direto:",
        "gastei 49,90 de Uber no crédito mercado pago",
        "recebi 3800 de salário",
        "novo fixo internet 120 pix dia 10",
        "comprei celular em 12x de 250 no cartão nubank",
        "",
        "Depois de registrar, eu mostro botões para corrigir, apagar ou consultar."
    ])


def gerar_tela_ajustes_ux():
    return "\n".join([
        "⚙️ Ajustes",
        "",
        "Aqui ficam ações de manutenção e segurança.",
        "",
        "🔐 Segurança",
        "bloquear",
        "esqueci pin",
        "/seguranca",
        "",
        "📤 Dados",
        "exportar csv",
        "exportar csv tudo",
        "backup",
        "",
        "🧹 Conversa",
        "/limpar",
        "",
        "📘 Ajuda",
        "/help",
        "/help fixos",
        "/help parcelas",
        "/help entradas",
    ])


def gerar_painel_hoje_ux():
    hoje = relogio.hoje(date)
    hoje_iso = hoje.isoformat()
    transacoes = buscar_todas_transacoes()

    receitas = 0
    despesas = 0
    quantidade = 0

    for t in transacoes:
        if t["data"] != hoje_iso:
            continue

        quantidade += 1

        if t["tipo"] == "receita":
            receitas += t["valor"] or 0
        elif t["tipo"] == "despesa":
            despesas += t["valor"] or 0

    saldo = receitas - despesas

    linhas = [
        f"📆 Hoje — {formatar_data_visual(hoje_iso)}",
        "",
        bloco_total("Movimentação registrada", [
            linha_valor("Entradas", receitas),
            linha_valor("Despesas", despesas),
            f"│ {'Lançamentos':<24} {quantidade:>14}",
            f"│ {'Saldo do dia':<24} {formatar_status_saldo(saldo):>14}",
        ]),
        "",
        "Checklist rápido:",
        "• despesas pequenas",
        "• compras no crédito",
        "• entradas recebidas",
        "• gastos que passaram batido",
        "",
        "Para registrar, envie algo como:",
        "gastei 49,90 de Uber no crédito mercado pago",
        "entrada bônus 500 hoje",
    ]

    return "\n".join(linhas)


def _calcular_metricas_resultado_mes(ano_mes: str, conta: str | None = None):
    dados = calcular_saldo_mensal(ano_mes, conta)

    entradas_realizadas = dados["entradas_realizadas"]
    entradas_previstas = dados["entradas_previstas"]
    saidas_imediatas = dados["saidas_imediatas_realizadas"]
    saidas_nao_imediatas = dados["saidas_nao_imediatas_realizadas"]
    despesas_realizadas_total = dados.get(
        "despesas_realizadas_total",
        saidas_imediatas + saidas_nao_imediatas,
    )
    despesas_esperadas = dados["despesas_esperadas_total"]

    resultado_caixa_realizado = entradas_realizadas - saidas_imediatas
    entradas_competencia = dados.get('entradas_competencia_mes', entradas_realizadas)
    resultado_realizado_mes = entradas_competencia - despesas_realizadas_total
    resultado_projetado_mes = entradas_competencia + entradas_previstas - despesas_realizadas_total - despesas_esperadas

    dados["resultado_caixa_realizado"] = resultado_caixa_realizado
    dados["resultado_realizado"] = resultado_realizado_mes
    dados["resultado_projetado_mes"] = resultado_projetado_mes
    dados["total_entradas_mes"] = entradas_competencia + entradas_previstas
    dados["total_saidas_realizadas_mes"] = despesas_realizadas_total
    dados["total_saidas_mes"] = despesas_realizadas_total + despesas_esperadas
    pendencias_herdadas = dados.get("pendencias_herdadas_total", 0.0) or 0.0
    dados["falta_considerar"] = (entradas_previstas - saidas_nao_imediatas - despesas_esperadas
        - pendencias_herdadas + dados.get('compensacao_pagamentos_fatura', 0)
        + dados.get('ajuste_reserva_faturas', 0)
        + dados.get('receitas_previstas_herdadas_total', 0))
    dados["saldo_livre_projetado"] = dados.get("saldo_projetado", 0.0)
    from conciliacao import revisoes_pendentes
    ancora = dados.get('ano_mes_ancora_saldo') or ano_mes
    revisoes = [r for mes in gerar_meses_entre(ancora,ano_mes) for r in revisoes_pendentes(mes)]
    chaves = {(r['tipo'],r.get('compromisso_id'),r['mes'],r.get('transacao_id')) for r in revisoes}
    # Recebimento lançado num mês posterior com o mesmo nome e conta de uma
    # receita prevista herdada, sem vínculo: o titular confirma (vinculando) ou
    # mantém separado. Nada é associado automaticamente.
    for item in dados.get('receitas_previstas_herdadas_suspeitas') or []:
        chave = ('receita_sem_vinculo', item.get('id'), item.get('ano_mes_origem'), item.get('transacao_suspeita_id'))
        if chave not in chaves:
            revisoes.append(dict(tipo=chave[0], compromisso_id=chave[1], nome=item.get('nome'),
                                 mes=chave[2], transacao_id=chave[3]))
            chaves.add(chave)
    for item in dados.get('pendencias_herdadas_itens',[]):
        if item.get('status_origem')=='marcacao_sem_vinculo':
            chave=('baixa_antiga',item['id'],item['ano_mes_origem'],None)
            if chave not in chaves:
                revisoes.append(dict(tipo=chave[0],compromisso_id=item['id'],nome=item['nome'],mes=item['ano_mes_origem']))
                chaves.add(chave)

    # Uma base de saldo posterior e explicitamente registrada pelo usuário é um
    # novo ponto de verdade do caixa. Marcações legadas de "pago" sem vínculo
    # anteriores a essa base continuam na auditoria, mas não devem reaparecer
    # como pendências ativas ao consultar fechamentos históricos.
    bases_posteriores = [dict(r) for r in listar_saldos_mensais() if r['ano_mes'] > ano_mes]
    base_posterior = bases_posteriores[0]['ano_mes'] if bases_posteriores else None
    arquivadas = []
    ativas = []
    for revisao in revisoes:
        if (base_posterior and revisao.get('tipo') == 'baixa_antiga'
                and (revisao.get('mes') or ano_mes) < base_posterior):
            arquivadas.append(dict(revisao, resolvida_por_base=base_posterior))
        else:
            ativas.append(revisao)

    dados['revisoes_conciliacao_brutas'] = revisoes
    dados['revisoes_conciliacao_arquivadas'] = arquivadas
    dados['revisoes_conciliacao'] = ativas
    dados['base_saldo_posterior_reconciliacao'] = base_posterior if arquivadas else None

    return dados


def obter_metricas_resultado_mes(ano_mes: str, conta: str | None = None):
    with _leitura_calculo():
        return _consulta_cache(
            ("obter_metricas_resultado_mes", str(ano_mes), conta),
            lambda: _calcular_metricas_resultado_mes(ano_mes, conta),
        )


def bloco_resultado_mes(dados: dict, compacto: bool = False):
    # Pagamento de fatura mexe no caixa, mas não entra no resultado operacional
    # (a compra já contou como crédito/esperado). Ele sai da linha de saídas
    # imediatas e aparece numa linha informativa, fora da soma (B5). O valor
    # do resultado não muda.
    pagamentos_fatura = dados.get("saidas_pagamentos_fatura", 0.0) or 0.0
    saidas_imediatas = dados.get("saidas_imediatas_realizadas", 0.0) - pagamentos_fatura
    credito_lancado = dados.get("saidas_nao_imediatas_realizadas", 0.0)
    despesas_esperadas = dados.get("despesas_esperadas_total", 0.0)
    linhas_info = []
    if abs(pagamentos_fatura) > 0.005:
        linhas_info.append(linha_valor("↩️ Fatura paga, não soma", pagamentos_fatura))

    if compacto:
        return bloco_total("Movimento do mês, sem herança", [
            linha_sinal_valor("🟢 Entradas do mês", dados["total_entradas_mes"]),
            linha_sinal_valor("🔴 Saídas imediatas", -saidas_imediatas),
            linha_sinal_valor("💳 Crédito lançado", -credito_lancado),
            linha_sinal_valor("🟠 Ainda esperado", -despesas_esperadas),
            linha_status_valor("⚖️ Resultado operacional", dados["resultado_projetado_mes"]),
            *linhas_info,
        ])

    return bloco_total("Movimento do mês, sem herança", [
        linha_sinal_valor("🟢 Entradas recebidas", dados["entradas_realizadas"]),
        linha_sinal_valor("🟢 Entradas previstas", dados["entradas_previstas"]),
        linha_sinal_valor("🔴 Saídas imediatas já pagas", -saidas_imediatas),
        linha_sinal_valor("💳 Crédito já lançado", -credito_lancado),
        linha_sinal_valor("🟠 Ainda esperado no mês", -despesas_esperadas),
        linha_status_valor("⚖️ Resultado operacional", dados["resultado_projetado_mes"]),
        *linhas_info,
    ])


def bloco_caixa_acumulado(dados: dict, compacto: bool = False):
    falta_considerar = dados.get(
        "falta_considerar",
        dados["entradas_previstas"] - dados["saidas_nao_imediatas_realizadas"] - dados["despesas_esperadas_total"],
    )

    if compacto:
        return bloco_total("Ponte do saldo", [
            linha_valor("🏦 Saldo inicial livre", dados["saldo_inicial"]),
            linha_status_valor("📌 Caixa já mexeu", dados["resultado_caixa_realizado"]),
            linha_valor("💰 Disponível em caixa", dados["saldo_disponivel"]),
            linha_status_valor("🔴 Pendências herdadas", -dados.get("pendencias_herdadas_total", 0.0)),
            linha_status_valor("🔮 Falta considerar", falta_considerar),
            linha_status_valor("🏁 Saldo livre provável", dados["saldo_projetado"]),
        ])

    return "\n".join([
        bloco_total("Ponte do saldo", [
            linha_valor("🏦 Saldo inicial livre", dados["saldo_inicial"]),
            linha_status_valor("📌 Caixa já mexeu", dados["resultado_caixa_realizado"]),
            linha_valor("💰 Disponível em caixa", dados["saldo_disponivel"]),
            linha_status_valor("💳 Crédito já lançado", -dados["saidas_nao_imediatas_realizadas"]),
            linha_valor("↩️ Fatura já liquidada", dados.get('compensacao_pagamentos_fatura', 0)),
            linha_status_valor("🟠 Esperado/pendente do mês", dados["entradas_previstas"] - dados["despesas_esperadas_total"]),
            linha_status_valor("🔴 Pendências herdadas", -dados.get("pendencias_herdadas_total", 0.0)),
            linha_status_valor("🏁 Saldo livre provável", dados["saldo_projetado"]),
        ]),
        "",
        "Conta da ponte:",
        "Disponível em caixa = comecei o mês + entradas - saídas imediatas.",
        "Saldo livre provável = caixa - crédito já lançado + entradas previstas - despesas esperadas - pendências herdadas + compensação da fatura já liquidada.",
    ])



def gerar_auditoria_resultado_mes_ux(ano_mes: str | None = None):
    """Explica, item a item, a formação do resultado operacional do mês.

    A auditoria usa exatamente os mesmos critérios de ``calcular_saldo_mensal``.
    Assim, os subtotais exibidos precisam reconciliar com o bloco "Meu mês".
    Nenhum lançamento é alterado por esta consulta.
    """
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")

    ano_mes = validar_ano_mes(ano_mes)
    if not ano_mes:
        return "Mês inválido. Use: auditar mês 2026-07"

    dados = obter_metricas_resultado_mes(ano_mes)
    transacoes = list(buscar_transacoes_por_competencia(ano_mes))

    entradas_realizadas = [t for t in transacoes if t["tipo"] == "receita"]
    saidas_imediatas = [
        t for t in transacoes
        if t["tipo"] == "despesa" and transacao_afeta_saldo_disponivel(t)
    ]
    credito_lancado = [
        t for t in transacoes
        if t["tipo"] == "despesa" and not transacao_afeta_saldo_disponivel(t)
    ]

    pagamentos_fatura = pagamentos_fatura_caixa_mes(ano_mes)

    entradas_previstas = [
        item for item in projetar_entradas_mes(ano_mes, incluir_transacoes=False)
        if item.get("origem") != "transacao"
    ]
    itens_pagamentos = projetar_pagamentos_mes(ano_mes, incluir_transacoes=True)
    # Mesma apresentação de "Meu mês" (B5): o pagamento de fatura sai de
    # "Saídas imediatas" e de "Ainda esperado" (onde entrava negativo e se
    # anulava) e aparece numa linha informativa, fora da soma. O resultado
    # não muda.
    ainda_esperado = [
        item for item in itens_pagamentos
        if item_esperado_por_origem(item) and not item_eh_liquidacao_fatura(item)
    ]

    def descricao_transacao(t):
        return (t["descricao"] or t["categoria"] or "Sem descrição").strip()

    def descricao_item(item):
        return (item.get("nome") or item.get("categoria") or "Sem descrição").strip()

    def conta_transacao(t):
        return formatar_nome_conta_saldo(t["conta"] or t["forma_pagamento"] or "Não informada")

    def conta_item(item):
        return formatar_nome_conta_saldo(item.get("conta_pagamento") or item.get("forma_pagamento") or "Não informada")

    def linha_item(data_item, descricao, conta, valor, prefixo=""):
        data_visual = formatar_data_visual(data_item) if data_item else "sem data"
        sinal = "+" if valor >= 0 else "-"
        return f"{prefixo}• {data_visual} | {descricao} | {conta} | {sinal}{formatar_moeda(abs(valor))}"

    def adicionar_secao(linhas, titulo, itens, total, montador, vazio="Nenhum item."):
        linhas.extend(["", titulo, f"Subtotal: {formatar_moeda(total)}"])
        if not itens:
            linhas.append(f"• {vazio}")
            return
        for item in itens:
            linhas.append(montador(item))

    total_entradas_realizadas = sum(float(t["valor"] or 0) for t in entradas_realizadas)
    total_entradas_previstas = sum(float(i.get("valor") or 0) for i in entradas_previstas)
    total_saidas_imediatas = sum(float(t["valor"] or 0) for t in saidas_imediatas)
    total_pagamentos_fatura = sum(float(m["valor"] or 0) for m in pagamentos_fatura)
    total_credito = sum(float(t["valor"] or 0) for t in credito_lancado)
    total_esperado = sum(float(i.get("valor") or 0) for i in ainda_esperado)

    linhas = [
        f"🔎 Auditoria do resultado — {formatar_ano_mes_visual(ano_mes)}",
        "",
        "Esta consulta não altera dados. Ela usa a mesma classificação do comando Meu mês.",
        "",
        bloco_total("Reconciliação", [
            linha_sinal_valor("🟢 Entradas recebidas", total_entradas_realizadas),
            linha_sinal_valor("🟢 Entradas previstas", total_entradas_previstas),
            linha_sinal_valor("🔴 Saídas imediatas", -total_saidas_imediatas),
            linha_sinal_valor("💳 Crédito lançado", -total_credito),
            linha_sinal_valor("🟠 Ainda esperado", -total_esperado),
            linha_status_valor("⚖️ Resultado operacional", dados["resultado_projetado_mes"]),
            *([linha_valor("↩️ Fatura paga, não soma", total_pagamentos_fatura)]
              if abs(total_pagamentos_fatura) > 0.005 else []),
        ]),
    ]

    adicionar_secao(
        linhas,
        "🟢 Entradas recebidas",
        entradas_realizadas,
        total_entradas_realizadas,
        lambda t: linha_item(t["data"], descricao_transacao(t), conta_transacao(t), float(t["valor"] or 0)),
    )
    adicionar_secao(
        linhas,
        "🟢 Entradas previstas",
        entradas_previstas,
        total_entradas_previstas,
        lambda i: linha_item(i.get("data"), descricao_item(i), conta_item(i), float(i.get("valor") or 0)),
    )
    adicionar_secao(
        linhas,
        "🔴 Saídas imediatas já realizadas",
        saidas_imediatas,
        total_saidas_imediatas,
        lambda t: linha_item(t["data"], descricao_transacao(t), conta_transacao(t), -float(t["valor"] or 0)),
    )

    if pagamentos_fatura:
        adicionar_secao(
            linhas,
            "↩️ Pagamentos de fatura já realizados (não somam no resultado)",
            pagamentos_fatura,
            total_pagamentos_fatura,
            lambda m: linha_item(
                m["data_movimento"],
                m["descricao"] or f"Pagamento da fatura {m['conta_cartao']}",
                formatar_nome_conta_saldo(m["conta_origem"] or m["conta_cartao"]),
                -float(m["valor"] or 0),
            ),
        )

    adicionar_secao(
        linhas,
        "💳 Crédito lançado",
        credito_lancado,
        total_credito,
        lambda t: linha_item(t["data"], descricao_transacao(t), conta_transacao(t), -float(t["valor"] or 0)),
    )
    adicionar_secao(
        linhas,
        "🟠 Ainda esperado",
        ainda_esperado,
        total_esperado,
        lambda i: linha_item(i.get("data"), descricao_item(i), conta_item(i), -float(i.get("valor") or 0)),
    )

    # Verificações automáticas, sem tentar corrigir ou reclassificar dados.
    resultado_recalculado = (
        total_entradas_realizadas
        + total_entradas_previstas
        - total_saidas_imediatas
        - total_credito
        - total_esperado
    )
    diferenca = resultado_recalculado - float(dados["resultado_projetado_mes"] or 0)

    assinaturas = {}
    grupos = []
    grupos.extend(("saída imediata", descricao_transacao(t), float(t["valor"] or 0)) for t in saidas_imediatas)
    grupos.extend(("crédito lançado", descricao_transacao(t), float(t["valor"] or 0)) for t in credito_lancado)
    grupos.extend(("ainda esperado", descricao_item(i), float(i.get("valor") or 0)) for i in ainda_esperado if float(i.get("valor") or 0) > 0)
    for grupo, nome, valor in grupos:
        chave = (texto_chave_saldo(nome), round(abs(valor), 2))
        assinaturas.setdefault(chave, []).append(grupo)
    suspeitas = [
        (nome, valor, sorted(set(lista)))
        for (nome, valor), lista in assinaturas.items()
        if len(set(lista)) > 1 and nome
    ]

    linhas.extend(["", "🧪 Verificações automáticas"])
    if abs(diferenca) < 0.01:
        linhas.append("✅ Os subtotais reconciliam com o Resultado operacional.")
    else:
        linhas.append(f"⚠️ Diferença de reconciliação: {formatar_moeda(diferenca)}")

    negativos_esperados = [i for i in ainda_esperado if float(i.get("valor") or 0) < 0]
    if negativos_esperados:
        linhas.append(f"⚠️ Existem {len(negativos_esperados)} item(ns) negativo(s) em Ainda esperado; revise créditos/estornos.")

    if suspeitas:
        linhas.append("⚠️ Possíveis duplicidades entre grupos (mesma descrição e valor):")
        for nome, valor, grupos_item in suspeitas[:10]:
            linhas.append(f"• {nome.title()} | {formatar_moeda(valor)} | {', '.join(grupos_item)}")
    else:
        linhas.append("✅ Nenhuma possível duplicidade entre grupos foi detectada pela regra simples.")

    linhas.extend([
        "",
        "Leitura dos grupos:",
        "• Saída imediata: Pix, débito, dinheiro e transferência já realizados.",
        "• Fatura paga: mexe no caixa, mas não soma no resultado; a compra já contou como crédito/esperado.",
        "• Crédito lançado: compras já registradas no cartão/crédito, mas ainda não saíram do caixa.",
        "• Ainda esperado: fixos, compromissos, parcelas e demais obrigações projetadas.",
    ])

    return "\n".join(linhas)


def gerar_meu_mes_ux(ano_mes: str | None = None):
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")

    dados = obter_metricas_resultado_mes(ano_mes)
    resumo = gerar_resumo_mes(ano_mes)

    if dados.get("saldo_herdado_auto"):
        leitura = "O mês está usando o saldo herdado do mês anterior."
    elif not dados["saldo_configurado"]:
        leitura = "Configure o saldo inicial para a ponte do saldo ficar fiel."
    elif dados["resultado_projetado_mes"] < 0:
        leitura = "O resultado do mês está negativo antes de considerar o saldo inicial."
    elif dados["total_saidas_mes"] > dados["total_entradas_mes"] * 0.85 and dados["total_entradas_mes"] > 0:
        leitura = "O mês está apertado: despesas estão consumindo boa parte das entradas."
    else:
        leitura = "O resultado do mês está controlado."

    return "\n".join([
        f"📊 Meu mês — {formatar_ano_mes_visual(ano_mes)}",
        "",
        bloco_heranca_mes_anterior(dados),
        "",
        bloco_resultado_mes(dados),
        "",
        bloco_caixa_acumulado(dados),
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        resumo,
    ])


def gerar_meu_mes_curto_ux(ano_mes: str | None = None):
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")

    dados = obter_metricas_resultado_mes(ano_mes)

    itens_saida = projetar_pagamentos_mes(ano_mes, incluir_transacoes=True)
    por_categoria = {}

    for item in itens_saida:
        categoria = obter_categoria_item(item)
        por_categoria[categoria] = por_categoria.get(categoria, 0) + (item.get("valor") or 0)

    categorias_top = sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)[:3]

    if dados.get("saldo_herdado_auto"):
        leitura = "O mês está usando o saldo herdado do mês anterior."
        acao = f"Confira as pendências antigas: pendências abertas {ano_mes}"
    elif not dados["saldo_configurado"]:
        leitura = "Configure o saldo inicial para a ponte do saldo ficar fiel."
        acao = f"Envie: saldo inicial {ano_mes} 1000"
    elif dados["resultado_projetado_mes"] < 0:
        leitura = "O resultado do mês está negativo antes de considerar o saldo inicial."
        acao = "Abra o saldo geral e revise despesas esperadas."
    elif dados["total_saidas_mes"] > dados["total_entradas_mes"] * 0.85 and dados["total_entradas_mes"] > 0:
        leitura = "O mês está apertado: despesas estão consumindo boa parte das entradas."
        acao = "Evite novas parcelas e acompanhe as contas principais."
    else:
        leitura = "O resultado do mês está controlado."
        acao = "Continue registrando gastos avulsos quando acontecerem."

    linhas = [
        f"📊 Meu mês — {formatar_ano_mes_visual(ano_mes)}",
        "",
        bloco_heranca_mes_anterior(dados, compacto=True),
        "",
        bloco_resultado_mes(dados, compacto=True),
        "",
        bloco_caixa_acumulado(dados, compacto=True),
    ]

    return "\n".join(linhas)


def gerar_compromissos_ux(ano_mes: str | None = None):
    """
    Visão operacional do que ainda pesa no mês.

    Conceito corrigido:
    - Compromissos esperados: fixos, parcelas e compromissos cadastrados.
    - Crédito lançado: despesa já lançada no cartão/crédito que ainda não saiu do caixa.
    - Pix/débito/dinheiro/transferência não entram aqui, pois já mexeram no caixa.

    Assim, se o Itaú tem R$ 50,00 de compromisso esperado e o usuário lança
    R$ 14,18 no crédito Itaú, a tela deve mostrar R$ 64,18 para o Itaú.
    """
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")

    entradas = projetar_entradas_mes(ano_mes, incluir_transacoes=False)
    # Movimentos de fatura (estornos, pagamentos, ajustes) já entram nas linhas
    # próprias abaixo, a partir de listar_fatura_movimentos. Mantê-los também
    # nos compromissos os descontava duas vezes do "Saldo a pagar" (B1).
    compromissos_esperados = [
        item for item in projetar_pagamentos_mes(ano_mes, incluir_transacoes=False)
        if item.get("origem") != "fatura_movimento"
    ]

    credito_lancado = []
    for t in buscar_transacoes_por_competencia(ano_mes):
        if t["tipo"] != "despesa":
            continue

        # Despesas imediatas já saíram do caixa. Não são "a pagar".
        if transacao_afeta_saldo_disponivel(t):
            continue

        credito_lancado.append({
            "origem": "credito_lancado",
            "id": t["id"],
            "tipo": "credito_lancado",
            "nome": t["descricao"] or "Lançamento no crédito",
            "categoria": t["categoria"] or "Outros",
            "conta_pagamento": t["conta"] or t["forma_pagamento"] or "Não informada",
            "forma_pagamento": t["forma_pagamento"] or "crédito",
            "valor": float(t["valor"] or 0),
            "data": t["data"],
            "parcela_atual": t["parcela_atual"] if "parcela_atual" in t.keys() else None,
            "parcelas_total": t["parcelas_total"] if "parcelas_total" in t.keys() else None,
            "ativo": True,
        })

    saidas = compromissos_esperados + credito_lancado

    total_entradas = sum(float(item.get("valor") or 0) for item in entradas)
    total_compromissos = sum(float(item.get("valor") or 0) for item in compromissos_esperados)
    total_credito_lancado = sum(float(item.get("valor") or 0) for item in credito_lancado)
    movimentos_fatura_mes = list(listar_fatura_movimentos(ano_mes))
    total_creditos_fatura = sum(
        float(m["valor"] or 0) for m in movimentos_fatura_mes
        if m["tipo_movimento"] in {"estorno", "credito", "ajuste_credito"}
    )
    total_pagamentos_fatura = sum(
        float(m["valor"] or 0) for m in movimentos_fatura_mes
        if m["tipo_movimento"] in {"pagamento_parcial", "pagamento_total"}
    )
    total_ajustes_debito_fatura = sum(
        float(m["valor"] or 0) for m in movimentos_fatura_mes
        if m["tipo_movimento"] == "ajuste_debito"
    )
    total_a_pagar_bruto = total_compromissos + total_credito_lancado
    total_a_pagar = (
        total_a_pagar_bruto
        - total_creditos_fatura
        - total_pagamentos_fatura
        + total_ajustes_debito_fatura
    )
    saldo_previsto = total_entradas - total_a_pagar

    por_categoria = {}
    por_conta = {}
    por_tipo = {
        "Compromissos esperados": total_compromissos,
        "Crédito lançado": total_credito_lancado,
    }

    for item in saidas:
        categoria = obter_categoria_item(item)
        conta = obter_conta_item(item)
        por_categoria[categoria] = por_categoria.get(categoria, 0) + (item.get("valor") or 0)
        por_conta[conta] = por_conta.get(conta, 0) + (item.get("valor") or 0)

    categorias_top = sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)[:5]
    contas_top = sorted(por_conta.items(), key=lambda x: x[1], reverse=True)

    linhas = [
        f"💳 Compromissos — {formatar_ano_mes_visual(ano_mes)}",
        "",
        bloco_total("A pagar no mês", [
            linha_valor("Entradas previstas", total_entradas),
            linha_valor("Compromissos esperados", total_compromissos),
            linha_valor("Crédito lançado", total_credito_lancado),
            linha_valor("Total bruto", total_a_pagar_bruto),
            linha_sinal_valor("Créditos/estornos", -total_creditos_fatura),
            linha_sinal_valor("Pagamentos de fatura", -total_pagamentos_fatura),
            linha_sinal_valor("Ajustes de débito", total_ajustes_debito_fatura),
            linha_valor("Saldo a pagar", total_a_pagar),
            f"│ {'Impacto previsto':<24} {formatar_status_saldo(saldo_previsto):>14}",
        ]),
        "",
        "Critério:",
        "Inclui fixos, parcelas, compromissos e crédito já lançado.",
        "Não inclui Pix, débito, dinheiro ou transferência já consolidados no caixa.",
    ]

    linhas.extend(["", "📌 Por tipo"])
    for tipo, valor in por_tipo.items():
        linhas.append(f"- {tipo}: {formatar_moeda(valor)}")

    if categorias_top:
        linhas.extend(["", "🏷 Principais categorias"])
        for categoria, valor in categorias_top:
            linhas.append(f"- {categoria}: {formatar_moeda(valor)}")

    if contas_top:
        linhas.extend(["", "🏦 Principais contas/meios"])
        for conta, valor in contas_top:
            linhas.append(f"- {conta}: {formatar_moeda(valor)}")

    if credito_lancado:
        linhas.extend(["", "💳 Crédito lançado no mês"])
        for item in sorted(credito_lancado, key=lambda i: (i.get("data") or "", i.get("id") or 0))[:12]:
            linhas.append(
                f"#{item['id']} | {formatar_data_visual(item['data'])} | {formatar_moeda(item['valor'])} | "
                f"{item['conta_pagamento']} | {item['nome']}"
            )
        if len(credito_lancado) > 12:
            linhas.append(f"... mais {len(credito_lancado) - 12} lançamento(s) no crédito")

    linhas.extend([
        "",
        "Atalhos úteis:",
        "fixos",
        "parcelamentos",
        f"quanto vou pagar no itaú em {ano_mes}",
        f"contas {ano_mes}",
        f"checklist pendentes {ano_mes}",
    ])

    return "\n".join(linhas)



def gerar_agenda_assessor_ux():
    hoje = relogio.hoje(date)
    meses = [somar_meses(hoje, i).strftime("%Y-%m") for i in range(0, 6)]

    linhas = [
        "📆 Agenda geral",
        "",
        "Mapa mensal de entradas e saídas previstas/lançadas.",
        "Aqui o foco é resultado do mês, não saldo inicial acumulado.",
    ]

    encontrou = False

    for ano_mes in meses:
        entradas = projetar_entradas_mes(ano_mes, incluir_transacoes=True)
        saidas = projetar_pagamentos_mes(ano_mes, incluir_transacoes=True)

        total_entradas = sum(item["valor"] for item in entradas)
        total_saidas = sum(item["valor"] for item in saidas)
        saldo = total_entradas - total_saidas

        if total_entradas <= 0 and total_saidas <= 0:
            continue

        encontrou = True
        marcador = " · mês atual" if ano_mes == hoje.strftime("%Y-%m") else ""

        linhas.extend([
            "",
            f"┌ {formatar_ano_mes_visual(ano_mes)}{marcador}",
            linha_valor("Entradas", total_entradas),
            linha_valor("Saídas", total_saidas),
            f"│ {'Resultado do mês':<24} {formatar_status_saldo(saldo):>14}",
            "└",
        ])

    if not encontrou:
        linhas.extend(["", "Não há entradas ou saídas previstas na agenda."])

    linhas.extend([
        "",
        "Para abrir um mês específico:",
        f"detalhar {hoje.strftime('%Y-%m')}",
        f"contas {hoje.strftime('%Y-%m')}",
    ])

    return "\n".join(linhas)



# ============================================================
# Checklist operacional de pagamentos
# ============================================================

def normalizar_chave_checklist(texto: str | None):
    texto = (texto or "").upper().strip()
    texto = texto.replace("#", "")
    texto = re.sub(r"\s+", "", texto)

    match = re.match(r"^([BCPT])(\d+)$", texto)
    if match:
        return f"{match.group(1)}{int(match.group(2))}"

    match_banco_slug = re.match(r"^B[_-]([A-Z0-9_\\-]+)$", texto)
    if match_banco_slug:
        slug = match_banco_slug.group(1).replace("-", "_")
        return f"B_{slug}"

    match_numero = re.match(r"^(\d+)$", texto)
    if match_numero:
        return f"C{int(match_numero.group(1))}"

    return None


def slug_banco_checklist(texto: str | None):
    texto = normalizar_texto(texto or "Nao informado").upper()
    texto = re.sub(r"[^A-Z0-9]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")
    return texto or "NAO_INFORMADO"



def eh_fatura_banco_checklist(item: dict):
    """
    Só agrega em B1/B2/B3 quando for realmente fatura/cartão de banco.
    Pix, débito, transferência, dinheiro e contas genéricas ficam individuais.
    """
    return item_eh_fatura_cartao(item)


def item_deve_entrar_no_checklist(item: dict, modo: str = "pendentes") -> bool:
    """Decide a elegibilidade operacional sem consultar ou alterar estado."""
    if not isinstance(item, dict):
        return False

    try:
        valor = float(item.get("valor") or 0)
    except (TypeError, ValueError):
        return False
    if valor <= 0.005:
        return False

    origem = normalizar_texto(item.get("origem") or "")
    tipo = normalizar_texto(item.get("tipo") or item.get("tipo_movimento") or "")
    forma = normalizar_texto(item.get("forma_pagamento") or item.get("forma") or "")
    status = normalizar_texto(item.get("status") or "")
    modo = normalizar_texto(modo or "pendentes")

    if origem == "fatura_movimento" or tipo in {
        "fatura_movimento", "estorno", "credito", "pagamento", "ajuste_debito",
    }:
        return False

    formas_imediatas = {"pix", "debito", "dinheiro", "transferencia"}
    transacao_imediata_realizada = (
        origem == "transacao" and forma in formas_imediatas
    )
    concluido = status in {"pago", "concluido"} or transacao_imediata_realizada

    if modo in {"geral", "todos", "completo"}:
        return True
    if modo in {"concluidos", "concluido", "pagos", "pago"}:
        return concluido
    return not concluido


def data_por_dia_no_mes(ano_mes: str, dia: int):
    ano, mes = map(int, ano_mes.split("-"))
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    dia_ajustado = min(max(int(dia), 1), ultimo_dia)
    return date(ano, mes, dia_ajustado).isoformat()


def buscar_data_padrao_item(item: dict, padroes: dict):
    possibilidades = [item.get("chave"), item.get("codigo")]
    if item.get("alias"):
        aliases = item["alias"] if isinstance(item["alias"], list) else [item["alias"]]
        possibilidades.extend(aliases)

    for chave in [p for p in possibilidades if p]:
        if chave in padroes:
            return padroes[chave]

    return None


def aplicar_datas_pagamento_checklist(ano_mes: str, itens: list):
    datas_por_chave = buscar_checklist_datas_pagamento_mes(ano_mes)
    padroes_por_chave = buscar_checklist_datas_pagamento_padrao()

    for item in itens:
        status = datas_por_chave.get(item["chave"])

        if not status and item.get("alias"):
            aliases = item["alias"] if isinstance(item["alias"], list) else [item["alias"]]
            for alias in aliases:
                status = datas_por_chave.get(alias)
                if status:
                    break

        if status:
            item["data_original"] = item.get("data")
            item["data"] = status["data_pagamento"]
            item["data_pagamento_manual"] = True
            item["data_pagamento_padrao"] = False
            item["observacao_data_pagamento"] = status["observacao"]
            continue

        padrao = buscar_data_padrao_item(item, padroes_por_chave)
        if padrao:
            item["data_original"] = item.get("data")
            item["data"] = data_por_dia_no_mes(ano_mes, int(padrao["dia_pagamento"]))
            item["data_pagamento_manual"] = False
            item["data_pagamento_padrao"] = True
            item["observacao_data_pagamento"] = padrao["observacao"]
        else:
            item["data_pagamento_manual"] = False
            item["data_pagamento_padrao"] = False

    return itens




def parsear_data_pagamento_usuario(texto_data: str, ano_mes: str):
    texto = normalizar_texto(texto_data or "").strip()
    texto = texto.replace("dia ", "").strip()

    if re.match(r"^\d{4}-\d{2}-\d{2}$", texto):
        try:
            return date.fromisoformat(texto).isoformat()
        except ValueError:
            return None

    match = re.match(r"^(\d{1,2})$", texto)
    if match:
        dia = int(match.group(1))
        try:
            ano, mes = map(int, ano_mes.split("-"))
            return date(ano, mes, dia).isoformat()
        except ValueError:
            return None

    match = re.match(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$", texto)
    if match:
        dia = int(match.group(1))
        mes = int(match.group(2))
        ano = int(match.group(3)) if match.group(3) else int(ano_mes[:4])
        if ano < 100:
            ano += 2000
        try:
            return date(ano, mes, dia).isoformat()
        except ValueError:
            return None

    return None



def montar_itens_checklist_mes(ano_mes: str, modo: str = "pendentes"):
    cache = _CONTEXTO_CONSULTA.get()
    cache_key = _chave_no_escopo_consulta(("montar_itens_checklist_mes", str(ano_mes), str(modo)))
    if cache is not None and cache_key in cache:
        # aplicar_status_checklist e outras camadas enriquecem/mutam os itens.
        # Entregamos uma cópia para manter a entrada cacheada sempre imutável.
        return [dict(item) for item in cache[cache_key]]
    """
    Monta o checklist operacional do mês usando a mesma base do comando:
    "quanto vou pagar no BANCO em AAAA-MM".

    Regra:
    - Usa projetar_pagamentos_mes(..., incluir_transacoes=True).
    - Não adiciona construir_grupos_parcelamentos() por fora, para evitar duplicidade.
    - Pix/débito/transferência/dinheiro e contas não bancárias ficam individuais.
    - Crédito em bancos reais fica agrupado por fatura/banco.
    """
    individuais = []
    bancos_por_slug = {}

    def adicionar_individual(item: dict):
        item = dict(item)
        item["grupo"] = "individuais"
        item["codigo"] = item.get("chave")
        if item.get("alias") and not isinstance(item["alias"], list):
            item["alias"] = [item["alias"]]
        elif not item.get("alias"):
            item["alias"] = []
        individuais.append(item)

    def adicionar_banco(item: dict):
        conta = item.get("conta") or item.get("conta_pagamento") or "Não informada"
        slug = slug_banco_checklist(conta)
        chave = f"B_{slug}"

        if chave not in bancos_por_slug:
            bancos_por_slug[chave] = {
                "chave": chave,
                "codigo": None,
                "alias": [],
                "grupo": "bancos",
                "origem": "banco_agregado",
                "id": None,
                "data": item.get("data") or "",
                "nome": str(conta).strip() or "Banco",
                "categoria": "Fatura/cartão",
                "conta": conta,
                "forma": "fatura",
                "valor": 0.0,
                "extra": "",
                "qtd_itens": 0,
                "detalhes": [],
                "fixos_credito_bruto": 0.0,
                "emprestimos_credito_bruto": 0.0,
                "outros_credito_bruto": 0.0,
            }

        banco = bancos_por_slug[chave]
        valor_item = float(item.get("valor") or 0)
        banco["valor"] += valor_item
        banco["qtd_itens"] += 1

        tipo_item = normalizar_texto(item.get("tipo") or "")
        origem_item = normalizar_texto(item.get("origem") or "")
        categoria_item = normalizar_texto(item.get("categoria") or "")
        nome_item_norm = normalizar_texto(item.get("nome") or "")
        if origem_item == "compromisso" and tipo_item == "fixo":
            if "emprest" in categoria_item or "emprest" in nome_item_norm:
                banco["emprestimos_credito_bruto"] += valor_item
            else:
                banco["fixos_credito_bruto"] += valor_item
        elif origem_item == "compromisso" and tipo_item not in {"parcelamento"}:
            banco["outros_credito_bruto"] += valor_item

        if item.get("data") and (not banco.get("data") or item["data"] > banco["data"]):
            banco["data"] = item["data"]

        nome_item = item.get("nome") or "Item"
        banco["detalhes"].append(f"{nome_item} · {formatar_moeda(float(item.get('valor') or 0))}")

    for item in projetar_pagamentos_mes(ano_mes, incluir_transacoes=True):
        # Movimentos de fatura (estornos, créditos, pagamentos e ajustes)
        # reconciliam o saldo agregado da fatura, mas não são obrigações a pagar
        # e, portanto, não devem virar tarefas individuais no checklist.
        if not item_deve_entrar_no_checklist(item, modo=modo):
            continue

        checklist_item = {
            "chave": f"T{item.get('id')}" if item.get("origem") == "transacao" else ("P" if str(item.get("tipo") or "").lower() == "parcelamento" or item.get("parcela_atual") or item.get("parcelas_total") else "C") + str(item.get("id")),
            "alias": [],
            "grupo": "individuais",
            "origem": item.get("origem"),
            "id": item.get("id"),
            "tipo": item.get("tipo"),
            "data": item.get("data") or "",
            "nome": item.get("nome") or "Pagamento",
            "categoria": item.get("categoria") or "Outros",
            "conta": item.get("conta_pagamento") or "Não informada",
            "forma": item.get("forma_pagamento") or "não informada",
            "valor": float(item.get("valor") or 0),
            "valor_original": float(item.get("valor_original", item.get("valor")) or 0),
            "valor_conciliado": float(item.get("valor_conciliado") or 0),
            "conciliado": bool(item.get("conciliado")), **({"valor_estimado": True} if item.get("valor_estimado") else {}),  # só fixo de valor variável
            "extra": "",
            "parcela_atual": item.get("parcela_atual"),
            "parcelas_total": item.get("parcelas_total"),
        }

        if checklist_item.get("parcela_atual") and checklist_item.get("parcelas_total"):
            checklist_item["extra"] = f" · {checklist_item['parcela_atual']}/{checklist_item['parcelas_total']}"

        if eh_fatura_banco_checklist(checklist_item):
            adicionar_banco(checklist_item)
        else:
            adicionar_individual(checklist_item)

    bancos = sorted(bancos_por_slug.values(), key=lambda item: (normalizar_texto(item["conta"]), item["chave"]))
    for banco in bancos:
        resumo_fatura = calcular_resumo_fatura(ano_mes, banco["conta"])
        banco["valor_bruto"] = resumo_fatura["valor_bruto"]
        banco["creditos_fatura"] = resumo_fatura["creditos"]
        banco["pagamentos_fatura"] = resumo_fatura["pagamentos"]
        banco["ajuste_conferencia"] = resumo_fatura.get("ajuste_conferencia", 0)
        banco["saldo_restante"] = resumo_fatura["saldo_restante"]
        banco["status_fatura"] = resumo_fatura["status"]
        banco["fonte_fatura"] = resumo_fatura.get("fonte_fatura")
        banco["itens_previstos_ignorados"] = len(resumo_fatura.get("itens_previstos_ignorados") or [])
        banco["valor"] = float(resumo_fatura["saldo_restante"] or 0)
        banco["fixos_credito"] = float(banco.pop("fixos_credito_bruto", 0.0) or 0)
        banco["emprestimos"] = float(banco.pop("emprestimos_credito_bruto", 0.0) or 0)
        banco["outros_compromissos"] = float(banco.pop("outros_credito_bruto", 0.0) or 0)
        banco["cartao_parcelas"] = max(
            0.0,
            banco["valor"]
            - banco["fixos_credito"]
            - banco["emprestimos"]
            - banco["outros_compromissos"],
        )

    bancos = [
        banco for banco in bancos
        if item_deve_entrar_no_checklist(banco, modo=modo)
    ]

    for indice, banco in enumerate(bancos, start=1):
        banco["codigo"] = f"B{indice}"
        banco["alias"] = [banco["codigo"], banco["chave"]]
        banco["extra"] = f" · {banco['qtd_itens']} item(ns)"

    individuais = sorted(individuais, key=lambda item: (item["data"], item["conta"], item["nome"], item["chave"]))
    resultado = aplicar_datas_pagamento_checklist(ano_mes, individuais + bancos)

    # RC3.0.14: para um cartao descoberto dinamicamente e ainda sem dia de
    # pagamento configurado, a data da compra nao pode virar vencimento da
    # fatura. Usamos o fim da competencia como fallback conservador. Quando o
    # usuario configurar uma data manual/padrao, ela continua tendo prioridade.
    # Fatura sem vencimento configurado (manual ou padrão): não afirmamos
    # vencimento. Antes, a data da compra mais recente virava "vencimento" e o
    # Início mostrava "vence hoje"/"vencido" falsos (D06 das jornadas, D11).
    # Data vazia é tratada pelas telas como "sem vencimento informado".
    for item in resultado:
        if item.get("grupo") != "bancos":
            continue
        if item.get("data_pagamento_manual") or item.get("data_pagamento_padrao"):
            item["vencimento_definido"] = True
            continue
        item["data_ultima_compra"] = item.get("data")
        item["data_original"] = item.get("data")
        item["data"] = ""
        item["vencimento_definido"] = False

    if cache is not None:
        cache[cache_key] = [dict(item) for item in resultado]
    return resultado


def aplicar_status_checklist(ano_mes: str, itens: list):
    status_por_chave = buscar_checklist_status_mes(ano_mes)

    for item in itens:
        status = status_por_chave.get(item["chave"])
        if item.get('conciliado'):
            item['status'] = 'pago' if float(item['valor']) <= .005 else 'parcial'
            item['status_origem'] = 'conciliacao'
            item['pago_em'] = None
            continue

        # Compatibilidade: aceita aliases de exibição como B1/C11/P11.
        if not status and item.get("alias"):
            aliases = item["alias"] if isinstance(item["alias"], list) else [item["alias"]]
            for alias in aliases:
                status = status_por_chave.get(alias)
                if status:
                    break

        if status:
            item["status"] = status["status"]
            item["pago_em"] = status["pago_em"]
            item["status_origem"] = "manual"
            if item.get('origem')=='compromisso' and status['status']=='pago':
                item['status']='revisar'
                item['status_origem']='marcacao_sem_vinculo'
        elif item.get("grupo") == "bancos" and float(item.get("valor") or 0) <= 0.005:
            item["status"] = "pago"
            item["pago_em"] = relogio.hoje(date).isoformat()
            item["status_origem"] = "automatico_fatura"
        elif item.get("origem") == "transacao":
            # Lançamento avulso/realizado já entrou no financeiro como pago.
            # Ele aparece no checklist geral para dar visão completa,
            # mas não aparece em checklist pendentes.
            item["status"] = "pago"
            item["pago_em"] = item.get("data")
            item["status_origem"] = "automatico"
        else:
            item["status"] = "pendente"
            item["pago_em"] = None
            item["status_origem"] = "pendente"

    return itens


def resolver_item_checklist(ano_mes: str, chave_usuario: str):
    chave = normalizar_chave_checklist(chave_usuario)
    if not chave:
        return None, None

    itens = aplicar_status_checklist(
        ano_mes, montar_itens_checklist_mes(ano_mes, modo="geral")
    )

    for item in itens:
        possibilidades = [item["chave"], item.get("codigo")]
        if item.get("alias"):
            aliases = item["alias"] if isinstance(item["alias"], list) else [item["alias"]]
            possibilidades.extend(aliases)

        possibilidades = [p for p in possibilidades if p]
        if chave in possibilidades:
            return item["chave"], item

    return chave, None



def resolver_fatura_recorrente_por_nome(ano_mes: str, nome_cartao: str):
    """Resolve o cartão para um ajuste RECORRENTE (sem mês explícito).

    O cartão pode não ter fatura no mês de hoje (ex.: sem compras em dezembro);
    nesse caso procura a fatura mais recente dele nos 12 meses anteriores e nos
    2 seguintes, só para obter a chave estável B_<SLUG> e o nome.
    """
    chave, item = resolver_fatura_checklist_por_nome(ano_mes, nome_cartao)
    if item:
        return chave, item
    base = date.fromisoformat(ano_mes + "-01")
    for passo in [-n for n in range(1, 13)] + [1, 2]:
        chave, item = resolver_fatura_checklist_por_nome(somar_meses(base, passo).strftime("%Y-%m"), nome_cartao)
        if item:
            return chave, item
    return None, None


def resolver_fatura_checklist_por_nome(ano_mes: str, nome_cartao: str):
    """Resolve uma fatura pelo nome e retorna sua chave estável B_<SLUG>."""
    nome_norm = normalizar_texto(nome_cartao or "").strip()
    if not nome_norm:
        return None, None

    itens = aplicar_status_checklist(
        ano_mes, montar_itens_checklist_mes(ano_mes, modo="geral")
    )
    faturas = [item for item in itens if item.get("grupo") == "bancos"]

    slug_procurado = slug_banco_checklist(nome_cartao)
    for item in faturas:
        if item.get("chave") == f"B_{slug_procurado}":
            return item["chave"], item
        if normalizar_texto(item.get("nome") or "") == nome_norm:
            return item["chave"], item
        if normalizar_texto(item.get("conta") or "") == nome_norm:
            return item["chave"], item

    return None, None


def definir_vencimento_fatura_por_nome_formatado(texto_limpo: str):
    """Configura vencimento mensal ou recorrente usando o nome do cartão."""
    texto = normalizar_texto(texto_limpo)
    padrao = re.match(
        r"^(?:vencimento|data de vencimento|data pagamento|data de pagamento)\s+"
        r"(?:da\s+)?(?:fatura|cartao|cartão)\s+(.+?)\s+"
        r"(?:(\d{4}-\d{2})\s+)?(?:para\s+)?(?:dia\s+)?(\d{1,2})$",
        texto,
    )
    if not padrao:
        return None

    nome_cartao = padrao.group(1).strip()
    ano_mes_explicito = validar_ano_mes(padrao.group(2)) if padrao.group(2) else None
    ano_mes = ano_mes_explicito or relogio.hoje(date).strftime("%Y-%m")
    dia = int(padrao.group(3))
    if dia < 1 or dia > 31:
        return "Dia inválido. Informe um dia entre 1 e 31."

    if ano_mes_explicito:
        chave, item = resolver_fatura_checklist_por_nome(ano_mes, nome_cartao)
    else:
        chave, item = resolver_fatura_recorrente_por_nome(ano_mes, nome_cartao)
    if not item:
        return (
            f"Não encontrei uma fatura chamada {nome_cartao!r} em {ano_mes}. "
            f"Use 'checklist faturas {ano_mes}' para conferir os nomes disponíveis."
        )

    if ano_mes_explicito:
        data_pagamento = data_por_dia_no_mes(ano_mes, dia)
        definir_checklist_data_pagamento(
            ano_mes,
            chave,
            data_pagamento,
            "Vencimento da fatura definido pelo usuário para esta competência.",
        )
        return "\n".join([
            "📅 Vencimento da fatura ajustado",
            "",
            f"Cartão: {item.get('nome')}",
            f"Competência: {formatar_ano_mes_visual(ano_mes)}",
            f"Vencimento: {formatar_data_visual(data_pagamento)}",
            "",
            "Este ajuste vale somente para esta fatura.",
        ])

    definir_checklist_data_pagamento_padrao(
        chave,
        dia,
        "Dia de vencimento recorrente da fatura definido pelo usuário.",
    )
    data_mes_atual = data_por_dia_no_mes(ano_mes, dia)
    return "\n".join([
        "📅 Vencimento recorrente da fatura ajustado",
        "",
        f"Cartão: {item.get('nome')}",
        f"Dia padrão: {dia:02d}",
        f"Neste mês: {formatar_data_visual(data_mes_atual)}",
        "",
        "O alerta das 10h passará a incluir esta fatura no dia do vencimento,",
        "desde que ela esteja pendente e tenha saldo a pagar.",
    ])


def definir_data_pagamento_checklist_formatado(texto_limpo: str):
    texto = normalizar_texto(texto_limpo)

    # Regra:
    # - Com mês explícito: ajusta só aquele mês.
    #   Ex.: vencimento B2 2026-07 para dia 10
    # - Sem mês explícito: fixa um vencimento padrão para todos os meses futuros.
    #   Ex.: vencimento C7 para dia 25
    padroes = [
        r"^(?:data pagamento|data de pagamento|vencimento|alterar vencimento|mudar vencimento|pagar em)\s+([a-zA-Z]?\d+|B_[a-z0-9_]+|b_[a-z0-9_]+|[cCpPtT]\d+)\s+(\d{4}-\d{2})\s+(?:para|em|dia)\s+(.+)$",
        r"^(?:data pagamento|data de pagamento|vencimento|alterar vencimento|mudar vencimento|pagar em)\s+([a-zA-Z]?\d+|B_[a-z0-9_]+|b_[a-z0-9_]+|[cCpPtT]\d+)\s+(?:para|em|dia)\s+(.+?)(?:\s+(\d{4}-\d{2}))?$",
    ]

    for indice, padrao in enumerate(padroes):
        match = re.match(padrao, texto)
        if not match:
            continue

        codigo = match.group(1)

        if indice == 0:
            ano_mes = validar_ano_mes(match.group(2))
            data_txt = match.group(3)
            escopo = "mes"
        else:
            ano_mes_explicito = validar_ano_mes(match.group(3)) if match.group(3) else None
            ano_mes = ano_mes_explicito or relogio.hoje(date).strftime("%Y-%m")
            data_txt = match.group(2)
            escopo = "mes" if ano_mes_explicito else "padrao"

        if not ano_mes:
            return "Mês inválido. Use: vencimento B2 2026-07 para dia 10"

        data_pagamento = parsear_data_pagamento_usuario(data_txt, ano_mes)
        if not data_pagamento:
            return "Data inválida. Use exemplos como: dia 10, 10/07 ou 2026-07-10"

        chave, item = resolver_item_checklist(ano_mes, codigo)
        if not item:
            return f"Não encontrei o item {codigo} no checklist de {ano_mes}."

        codigo_exibicao = item.get("codigo") or codigo

        if escopo == "padrao":
            dia = int(data_pagamento[-2:])
            definir_checklist_data_pagamento_padrao(
                chave,
                dia,
                "Dia de pagamento padrão definido pelo usuário.",
            )

            return "\n".join([
                "📅 Vencimento fixo ajustado",
                "",
                f"Item: {codigo_exibicao} · {item.get('nome')}",
                f"Valor atual: {formatar_moeda(float(item.get('valor') or 0))}",
                f"Dia padrão: todo mês dia {dia:02d}",
                "",
                "Esse ajuste vale para os próximos meses enquanto o item existir no checklist.",
                f"Para conferir este mês: vencimentos {ano_mes}",
                "",
                "Para alterar só um mês específico, use:",
                f"vencimento {codigo_exibicao} {ano_mes} para dia {dia:02d}",
            ])

        definir_checklist_data_pagamento(
            ano_mes,
            chave,
            data_pagamento,
            "Data de pagamento definida manualmente pelo usuário.",
        )

        return "\n".join([
            "📅 Data de pagamento ajustada",
            "",
            f"Item: {codigo_exibicao} · {item.get('nome')}",
            f"Valor: {formatar_moeda(float(item.get('valor') or 0))}",
            f"Nova data: {formatar_data_visual(data_pagamento)}",
            "",
            "Esse ajuste vale apenas para este mês.",
            f"Para conferir: checklist {ano_mes}",
            f"Para lembretes do dia: vencimentos hoje",
        ])

    return None




def apagar_data_pagamento_checklist_formatado(texto_limpo: str):
    texto = normalizar_texto(texto_limpo)

    match_fixo = re.match(
        r"^(?:apagar|remover|tirar|limpar)\s+(?:vencimento fixo|data pagamento fixa|data de pagamento fixa)\s+([a-zA-Z]?\d+|B_[a-z0-9_]+|b_[a-z0-9_]+|[cCpPtT]\d+)(?:\s+(\d{4}-\d{2}))?$",
        texto
    )
    if match_fixo:
        codigo = match_fixo.group(1)
        ano_mes = validar_ano_mes(match_fixo.group(2)) if match_fixo.group(2) else relogio.hoje(date).strftime("%Y-%m")
        chave, item = resolver_item_checklist(ano_mes, codigo)
        if not item:
            return f"Não encontrei o item {codigo} no checklist de {ano_mes}."

        apagar_checklist_data_pagamento_padrao(chave)
        return "\n".join([
            "🗑️ Vencimento fixo removido",
            "",
            f"Item: {item.get('codigo') or codigo} · {item.get('nome')}",
            "Os próximos meses voltam a usar a data original do item.",
        ])

    match = re.match(
        r"^(?:apagar|remover|tirar|limpar)\s+(?:data pagamento|data de pagamento|vencimento)\s+([a-zA-Z]?\d+|B_[a-z0-9_]+|b_[a-z0-9_]+|[cCpPtT]\d+)(?:\s+(\d{4}-\d{2}))?$",
        texto
    )

    if not match:
        return None

    codigo = match.group(1)
    ano_mes = validar_ano_mes(match.group(2)) if match.group(2) else relogio.hoje(date).strftime("%Y-%m")

    if not ano_mes:
        return "Mês inválido. Use: apagar vencimento B2 2026-07"

    chave, item = resolver_item_checklist(ano_mes, codigo)
    if not item:
        return f"Não encontrei o item {codigo} no checklist de {ano_mes}."

    apagar_checklist_data_pagamento(ano_mes, chave)

    return "\n".join([
        "🗑️ Data de pagamento do mês removida",
        "",
        f"Item: {item.get('codigo') or codigo} · {item.get('nome')}",
        f"Checklist: {formatar_ano_mes_visual(ano_mes)}",
        "Se existir vencimento fixo, ele continuará valendo.",
    ])




def listar_vencimentos_checklist_formatado(ano_mes: str | None = None):
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")

    itens = aplicar_status_checklist(ano_mes, montar_itens_checklist_mes(ano_mes))
    itens = [item for item in itens if item.get("status") != "pago"]
    itens.sort(key=lambda item: (item.get("data") or "9999-99-99", item.get("codigo") or item.get("chave") or ""))

    linhas = [
        f"📅 Vencimentos do checklist — {formatar_ano_mes_visual(ano_mes)}",
        "",
    ]

    if not itens:
        linhas.append("Nenhum item pendente no checklist.")
        return "\n".join(linhas)

    data_atual = None
    for item in itens:
        data_item = item.get("data") or "sem data"
        if data_item != data_atual:
            data_atual = data_item
            linhas.append("")
            linhas.append(f"🗓 {formatar_data_visual(data_item) if data_item != 'sem data' else 'Sem data'}")

        codigo = item.get("codigo") or item.get("chave")
        if item.get("data_pagamento_manual"):
            marcador_data = " · manual"
        elif item.get("data_pagamento_padrao"):
            marcador_data = " · fixo"
        else:
            marcador_data = ""
        linhas.append(f"☐ {codigo} {item.get('nome')} — {formatar_moeda(float(item.get('valor') or 0))}{marcador_data}")

    linhas.extend([
        "",
        "Para alterar:",
        f"vencimento B2 {ano_mes} para dia 10",
    ])

    return "\n".join(linhas)


def gerar_lembrete_pagamentos_data(data_ref: str | None = None):
    if data_ref is None:
        data_ref = relogio.hoje(date).isoformat()

    ano_mes = data_ref[:7]
    itens = aplicar_status_checklist(ano_mes, montar_itens_checklist_mes(ano_mes))
    itens = [
        item for item in itens
        if item.get("status") != "pago"
        and item.get("data") == data_ref
        and float(item.get("valor") or 0) > 0.005
    ]
    itens.sort(key=lambda item: (item.get("grupo") or "", item.get("codigo") or item.get("chave") or ""))

    linhas = [f"🔔 Pagamentos de hoje — {formatar_data_visual(data_ref)}", ""]
    if not itens:
        linhas.append("Nenhum compromisso ou fatura pendente vence hoje.")
        return "\n".join(linhas)

    compromissos = [item for item in itens if item.get("grupo") != "bancos"]
    faturas = [item for item in itens if item.get("grupo") == "bancos"]
    total = sum(float(item.get("valor") or 0) for item in itens)
    linhas.append(f"Total previsto: {formatar_moeda(total)}")

    codigos = []
    if compromissos:
        linhas.extend(["", "🧾 Compromissos"])
        for item in compromissos:
            codigo = item.get("codigo") or item.get("chave")
            codigos.append(str(codigo))
            linhas.append(f"☐ {codigo} {item.get('nome')} — {formatar_moeda(float(item.get('valor') or 0))}")

    if faturas:
        linhas.extend(["", "💳 Faturas"])
        for item in faturas:
            codigo = item.get("codigo") or item.get("chave")
            codigos.append(str(codigo))
            linhas.append(f"☐ {codigo} {item.get('nome')} — {formatar_moeda(float(item.get('valor') or 0))}")

    if codigos:
        linhas.extend(["", "Depois de pagar:", f"paguei {' '.join(codigos)} {ano_mes}"])
    return "\n".join(linhas)





def gerar_checklist_pagamentos(ano_mes: str | None = None, filtro: str | None = None):
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")

    ano_mes = validar_ano_mes(ano_mes) or relogio.hoje(date).strftime("%Y-%m")
    filtro = normalizar_texto(filtro) if filtro else ""

    filtros_completos = {"completo", "completa", "geral", "todos", "todas"}
    filtro_pendentes = not filtro or filtro in {"pendentes", "pendente"}
    modo_base = "pendentes" if filtro_pendentes else "geral"

    todos_itens = aplicar_status_checklist(
        ano_mes, montar_itens_checklist_mes(ano_mes, modo=modo_base)
    )

    individuais = [item for item in todos_itens if item["grupo"] == "individuais"]
    bancos = [item for item in todos_itens if item["grupo"] == "bancos"]

    if filtro in ["bancos", "banco", "faturas", "fatura", "parcelas", "parcelamentos", "cartoes", "cartões"]:
        itens = bancos
        titulo_filtro = " · faturas"
        modo = "bancos"
    elif filtro in ["fixos", "fixo", "compromissos", "compromisso"]:
        itens = individuais
        titulo_filtro = " · compromissos"
        modo = "fixos"
    elif filtro in ["pagos", "pago"]:
        itens = [item for item in todos_itens if item["status"] == "pago"]
        titulo_filtro = " · pagos"
        modo = "pagos"
    elif filtro_pendentes:
        # "revisar" já foi marcado como pago em versão anterior e precisa
        # apenas de conciliação. Não é obrigação financeira em aberto.
        itens = [item for item in todos_itens if item["status"] not in {"pago", "revisar"}]
        titulo_filtro = ""
        modo = "pendentes"
    elif filtro in filtros_completos:
        itens = todos_itens
        titulo_filtro = " · completo"
        modo = "completo"
    else:
        itens = todos_itens
        titulo_filtro = ""
        modo = "completo"

    total_pago = sum(item['valor'] for item in itens if item['status']=='pago')
    total_revisar = sum(item['valor'] for item in itens if item['status']=='revisar')
    total_pendente = sum(item["valor"] for item in itens if item["status"] not in {"pago", "revisar"})
    qtd_pago = sum(1 for item in itens if item["status"] == "pago")
    qtd_revisar = sum(1 for item in itens if item["status"] == "revisar")
    qtd_pendente = sum(1 for item in itens if item["status"] not in {"pago", "revisar"})

    linhas = [f"✅ Checklist{titulo_filtro} — {formatar_ano_mes_visual(ano_mes)}", ""]

    if modo == "pagos":
        linhas.extend([
            f"✅ Total pago: {formatar_moeda(total_pago)}",
            f"📌 {qtd_pago} item(ns) pago(s)",
        ])
    elif modo == "completo":
        linhas.extend([
            f"☐ Pendentes: {formatar_moeda(total_pendente)}",
            f"✅ Pagos: {formatar_moeda(total_pago)}",
            f"🔎 Revisar baixas: {formatar_moeda(total_revisar)}" if qtd_revisar else "",
            f"📌 Itens pendentes: {qtd_pendente}",
        ])
        linhas[:] = [linha for linha in linhas if linha != ""]
        linhas.append("")
    else:
        linhas.extend([
            f"☐ Total pendente: {formatar_moeda(total_pendente)}",
            f"📌 {qtd_pendente} item(ns) pendente(s)",
        ])

    if not itens:
        linhas.extend(["", "Nada encontrado para este filtro."])
        return "\n".join(linhas)

    def linha_curta(item: dict):
        marcado = "✅" if item.get("status") == "pago" else "☐"
        codigo = item.get("codigo") or item["chave"]
        sufixo = " · auto" if str(item.get("status_origem") or "").startswith("automatico") else ""
        if item.get("grupo") == "bancos":
            if item.get("data"):
                sufixo += f" · vence {formatar_data_visual(item['data'])}"
            else:
                sufixo += (" · sem vencimento definido (configure: "
                           f"vencimento fatura {item.get('nome') or item.get('conta') or 'Nubank'} dia 10)")
            if item.get("fonte_fatura") == "real":
                sufixo += " · realizada"
            elif item.get("fonte_fatura") == "prevista":
                sufixo += " · prevista"
            if item.get("status_fatura") in {"parcialmente paga", "parcialmente abatida", "saldo credor"}:
                sufixo += f" · {item['status_fatura']}"
        valor_exibido = item.get('valor_conciliado',item['valor']) if item.get('conciliado') and item['status']=='pago' else item['valor']
        if item.get('status')=='parcial':sufixo += ' · pago '+formatar_moeda(item.get('valor_conciliado',0))
        if item.get('status')=='revisar':sufixo += ' · marcação antiga; falta vínculo'
        linha = f"{marcado} {codigo} {item['nome']} — {formatar_moeda(valor_exibido)}{sufixo}"
        if item.get("grupo") == "bancos":
            partes = []
            cartao = float(item.get("cartao_parcelas") or 0)
            fixos = float(item.get("fixos_credito") or 0)
            emprestimos = float(item.get("emprestimos") or 0)
            outros = float(item.get("outros_compromissos") or 0)
            if abs(cartao) > 0.005:
                partes.append(f"   Cartão e parcelas: {formatar_moeda(cartao)}")
            if abs(fixos) > 0.005:
                partes.append(f"   Fixos no crédito: {formatar_moeda(fixos)}")
            if abs(emprestimos) > 0.005:
                partes.append(f"   Empréstimos: {formatar_moeda(emprestimos)}")
            if abs(outros) > 0.005:
                partes.append(f"   Outros compromissos: {formatar_moeda(outros)}")
            if partes:
                linha += "\n" + "\n".join(partes)
        return linha

    def adicionar_lista_compacta(titulo: str, lista: list, limite: int):
        if not lista:
            return
        linhas.extend(["", titulo])
        for item in lista[:limite]:
            linhas.append(linha_curta(item))
        restante = len(lista) - limite
        if restante > 0:
            linhas.append(f"+{restante} item(ns)")

    lista_individuais = [item for item in itens if item["grupo"] == "individuais"]
    lista_bancos = [item for item in itens if item["grupo"] == "bancos"]

    if modo == "bancos":
        adicionar_lista_compacta("💳 Faturas", lista_bancos, 50)
    elif modo == "fixos":
        adicionar_lista_compacta("🧾 Compromissos", lista_individuais, 50)
    else:
        adicionar_lista_compacta("🧾 Compromissos", lista_individuais, 30)
        adicionar_lista_compacta("💳 Faturas", lista_bancos, 30)

    return "\n".join(linhas)

def detalhar_item_checklist_formatado(ano_mes: str, chave_usuario: str):
    ano_mes = validar_ano_mes(ano_mes) or relogio.hoje(date).strftime("%Y-%m")
    chave_real, item = resolver_item_checklist(ano_mes, chave_usuario)

    if not chave_real or not item:
        return "\n".join([
            "✅ Checklist",
            "",
            f"Não encontrei {chave_usuario} em {formatar_ano_mes_visual(ano_mes)}.",
            "",
            f"Use: checklist {ano_mes}",
        ])

    codigo = item.get("codigo") or item["chave"]
    marcado = "✅ Pago automático" if item.get("status_origem") == "automatico" else ("✅ Pago" if item.get("status") == "pago" else "☐ Pendente")
    data_visual = formatar_data_visual(item["data"]) if item.get("data") else "sem data"

    if item.get("grupo") == "bancos":
        linhas = [
            f"💳 {codigo} · {item['nome']}",
            "",
            f"Status: {marcado}",
            f"Fatura bruta: {formatar_moeda(item.get('valor_bruto', item['valor']))}",
            f"Créditos/estornos: -{formatar_moeda(item.get('creditos_fatura', 0.0))}",
            f"Pagamentos: -{formatar_moeda(item.get('pagamentos_fatura', 0.0))}",
            f"Conferência do total no banco: {formatar_moeda(item.get('ajuste_conferencia', 0.0))}",
            f"Saldo restante: {formatar_moeda(item['valor'])}",
            f"Status da fatura: {item.get('status_fatura', marcado)}",
            f"Vencimento: {data_visual}",
            f"Itens na fatura: {item.get('qtd_itens', 0)}",
        ]

        detalhes = item.get("detalhes") or []
        if detalhes:
            linhas.extend(["", "Composição:"])
            for detalhe in detalhes[:12]:
                linhas.append(f"- {detalhe}")
            restante = len(detalhes) - 12
            if restante > 0:
                linhas.append(f"+{restante} item(ns)")

        linhas.extend([
            "",
            "Ações:",
            f"paguei {codigo} {ano_mes}",
            f"marcar pendente {codigo} {ano_mes}",
        ])
        return "\n".join(linhas)

    return "\n".join([
        f"🧾 {codigo} · {item['nome']}",
        "",
        f"Status: {marcado}",
        f"Valor: {formatar_moeda(item['valor'])}",
        f"Data: {data_visual}",
        f"Conta: {item['conta']}",
        f"Forma: {item['forma']}",
        f"Categoria: {item['categoria']}",
        "",
        "Ações:",
        f"paguei {codigo} {ano_mes}",
        f"marcar pendente {codigo} {ano_mes}",
    ])


def parsear_comando_detalhar_checklist(texto_limpo: str):
    texto = normalizar_texto(texto_limpo)

    match = re.match(r"^(?:detalhar|detalhe|abrir|ver)\s+#?([bcpt]?\d+)(?:\s+(\d{4}-\d{2}))?$", texto)
    if match:
        chave = match.group(1)
        ano_mes = validar_ano_mes(match.group(2)) if match.group(2) else relogio.hoje(date).strftime("%Y-%m")
        return ano_mes, chave

    return None


def parsear_comando_checklist(texto_limpo: str):
    texto = normalizar_texto(texto_limpo)

    if texto in ["checklist", "lista pagamentos", "lista de pagamentos", "pagamentos"]:
        return relogio.hoje(date).strftime("%Y-%m"), None

    match = re.match(r"^(?:checklist|lista pagamentos|lista de pagamentos|pagamentos)\s+(\d{4}-\d{2})$", texto)
    if match:
        return validar_ano_mes(match.group(1)), None

    match = re.match(r"^(?:checklist|lista pagamentos|lista de pagamentos|pagamentos)\s+(fixos|fixo|bancos|banco|faturas|fatura|parcelas|parcelamentos|pagos|pago|pendentes|pendente|compromissos|compromisso|cartoes|cartões|completo|completa|geral|todos|todas)(?:\s+(\d{4}-\d{2}))?$", texto)
    if match:
        filtro = match.group(1)
        ano_mes = validar_ano_mes(match.group(2)) if match.group(2) else relogio.hoje(date).strftime("%Y-%m")
        return ano_mes, filtro

    return None


def texto_parece_lista_checklist(texto_chaves: str):
    """
    Evita falso positivo:
    'paguei 100,00 personal nutricionista pix mercado pago'
    não é checklist; é lançamento financeiro.

    Checklist só pode ter códigos C/P/T/B + números, separados por espaço,
    vírgula, ponto e vírgula, +, / ou 'e'.
    """
    texto = normalizar_texto(texto_chaves or "").strip()

    if not texto:
        return False

    # Valor monetário é forte sinal de lançamento financeiro, não checklist.
    if re.search(r"\d+[,.]\d{1,2}", texto):
        return False

    texto_sem_mes = re.sub(r"\b20\d{2}-\d{2}\b", " ", texto)
    texto_sem_mes = re.sub(r"\be\b", " ", texto_sem_mes)
    texto_sem_mes = texto_sem_mes.replace(",", " ")
    texto_sem_mes = texto_sem_mes.replace(";", " ")
    texto_sem_mes = texto_sem_mes.replace("+", " ")
    texto_sem_mes = texto_sem_mes.replace("/", " ")
    texto_sem_mes = re.sub(r"\s+", " ", texto_sem_mes).strip()

    if not texto_sem_mes:
        return False

    partes = texto_sem_mes.split(" ")

    # Não permitir números soltos em marcação múltipla, porque 'paguei 100'
    # é ambíguo e provavelmente é lançamento financeiro.
    for parte in partes:
        if not re.match(r"^[bcpt]\d+$", parte):
            return False

    return True


def extrair_chaves_checklist_multiplas(texto_chaves: str):
    texto = normalizar_texto(texto_chaves or "")
    texto = re.sub(r"\be\b", ",", texto)
    texto = texto.replace(";", ",").replace("+", ",").replace("/", ",")
    texto = re.sub(r"\s+", " ", texto)

    chaves = []
    for parte in re.split(r"[,\s]+", texto):
        parte = parte.strip()
        if not parte:
            continue
        chave = normalizar_chave_checklist(parte)
        if chave and chave not in chaves:
            chaves.append(chave)

    return chaves


def _fatura_checklist_com_saldo(item) -> bool:
    """Fatura (B) ainda com saldo restante: marcar "pago" não registra pagamento.

    A marcação manual escondia a fatura do checklist sem gravar a saída nem
    abater o saldo; compras novas da mesma fatura também deixavam de aparecer.
    """
    return bool(item) and item.get("grupo") == "bancos" and float(item.get("valor") or 0) > 0.005


def _mensagem_fatura_exige_pagamento(item, ano_mes: str) -> str:
    nome = item.get("nome") or item.get("conta") or "do cartão"
    return "\n".join([
        "💳 Fatura com saldo restante",
        "",
        f"{item.get('codigo') or item['chave']} · {nome} · saldo {formatar_moeda(item['valor'])}",
        "",
        "Marcar a fatura como paga não registra o pagamento: o saldo continuaria em aberto e "
        "compras novas desta fatura deixariam de aparecer. Nada foi gravado.",
        "",
        "Registre o pagamento da fatura (valor e conta de saída):",
        "/menu → A pagar → fatura → Registrar pagamento",
        f"ou: paguei o restante da fatura {nome} usando <conta> {ano_mes}",
        "(por texto, eu mostro uma prévia e só gravo depois de: confirmar pagamento)",
    ])


def marcar_itens_checklist_formatado(ano_mes: str, chaves_usuario: list[str], status: str):
    ano_mes = validar_ano_mes(ano_mes) or relogio.hoje(date).strftime("%Y-%m")
    status = "pago" if status == "pago" else "pendente"

    if not chaves_usuario:
        return "✅ Checklist\n\nNão identifiquei os itens. Exemplo: paguei C7 B1 B3"
    resolvidos = [resolver_item_checklist(ano_mes,chave)[1] for chave in chaves_usuario]
    if any(i and (i.get('conciliado') or (status=='pago' and i.get('origem')=='compromisso')) for i in resolvidos):
        return 'Para baixar compromissos, abra /menu → A pagar e confirme cada movimento com valor, conta e data. Nenhuma marcação deste lote foi alterada. Vínculos existentes são revisados em Conciliações.'
    if status == 'pago':
        fatura_aberta = next((i for i in resolvidos if _fatura_checklist_com_saldo(i)), None)
        if fatura_aberta:
            return (_mensagem_fatura_exige_pagamento(fatura_aberta, ano_mes)
                    + '\n\nNenhuma marcação deste lote foi alterada.')

    atualizados = []
    nao_encontrados = []

    for chave_usuario in chaves_usuario:
        chave_real, item = resolver_item_checklist(ano_mes, chave_usuario)

        if not chave_real or not item:
            nao_encontrados.append(str(chave_usuario).upper())
            continue

        marcar_checklist_pagamento(ano_mes, chave_real, status)
        atualizados.append(item)

    total = sum(float(item.get("valor") or 0) for item in atualizados)
    status_texto = "pagos" if status == "pago" else "pendentes"
    icone = "✅" if status == "pago" else "☐"

    linhas = [
        f"{icone} Checklist atualizado",
        "",
        f"Mês: {formatar_ano_mes_visual(ano_mes)}",
        f"Itens marcados como {status_texto}: {len(atualizados)}",
        f"Total: {formatar_moeda(total)}",
    ]

    if atualizados:
        linhas.extend(["", "Atualizados:"])
        for item in atualizados:
            codigo = item.get("codigo") or item["chave"]
            linhas.append(f"- {codigo} · {item['nome']} · {formatar_moeda(item['valor'])}")

    if nao_encontrados:
        linhas.extend(["", "Não encontrados:"])
        for chave in nao_encontrados:
            linhas.append(f"- {chave}")

    linhas.extend([
        "",
        "Para ver:",
        f"checklist {ano_mes}",
    ])

    return "\n".join(linhas)


def parsear_comando_marcar_checklist_multiplo(texto_limpo: str):
    texto = normalizar_texto(texto_limpo)

    match = re.match(r"^(?:paguei|pago|marcar pago|marcar como pago|quitar|quitei)\s+(.+?)(?:\s+(\d{4}-\d{2}))?$", texto)
    if match:
        texto_chaves = match.group(1)
        if texto_parece_lista_checklist(texto_chaves):
            chaves = extrair_chaves_checklist_multiplas(texto_chaves)
            if len(chaves) >= 2:
                ano_mes = validar_ano_mes(match.group(2)) if match.group(2) else relogio.hoje(date).strftime("%Y-%m")
                return ano_mes, chaves, "pago"

    match = re.match(r"^(?:desmarcar|marcar pendente|marcar como pendente|pendente)\s+(.+?)(?:\s+(\d{4}-\d{2}))?$", texto)
    if match:
        texto_chaves = match.group(1)
        if texto_parece_lista_checklist(texto_chaves):
            chaves = extrair_chaves_checklist_multiplas(texto_chaves)
            if len(chaves) >= 2:
                ano_mes = validar_ano_mes(match.group(2)) if match.group(2) else relogio.hoje(date).strftime("%Y-%m")
                return ano_mes, chaves, "pendente"

    return None


def marcar_item_checklist_formatado(ano_mes: str, chave_usuario: str, status: str):
    ano_mes = validar_ano_mes(ano_mes) or relogio.hoje(date).strftime("%Y-%m")
    status = "pago" if status == "pago" else "pendente"

    chave_real, item = resolver_item_checklist(ano_mes, chave_usuario)

    if not chave_real:
        return "✅ Checklist\n\nNão entendi o item. Use algo como: paguei C1 ou paguei P11"

    if not item:
        return "\n".join([
            "✅ Checklist",
            "",
            f"Não encontrei o item {chave_real} em {formatar_ano_mes_visual(ano_mes)}.",
            "",
            "Abra a lista com:",
            f"checklist {ano_mes}",
        ])

    if item.get('conciliado'):
        return 'Este item possui movimento conciliado. Revise em /menu → Conciliações. Mudar uma marcação não estorna dinheiro.'
    if status=='pago' and item.get('origem')=='compromisso':
        return 'A baixa financeira exige conferir valor, conta e data. Abra /menu → A pagar → Registrar pagamento. Nada foi gravado nesta etapa.'
    if status == 'pago' and _fatura_checklist_com_saldo(item):
        return _mensagem_fatura_exige_pagamento(item, ano_mes)
    marcar_checklist_pagamento(ano_mes, chave_real, status)

    status_texto = "marcado como pago" if status == "pago" else "marcado como pendente"
    icone = "✅" if status == "pago" else "☐"

    return "\n".join([
        f"{icone} Checklist atualizado",
        "",
        f"{item.get('codigo') or item['chave']} · {item['nome']}",
        f"Status: {status_texto}",
        f"Valor: {formatar_moeda(item['valor'])}",
        f"Mês: {formatar_ano_mes_visual(ano_mes)}",
        "",
        "Para ver:",
        f"checklist {ano_mes}",
    ])


def parsear_comando_marcar_checklist(texto_limpo: str):
    texto = normalizar_texto(texto_limpo)

    match = re.match(r"^(?:paguei|pago|marcar pago|marcar como pago|quitar|quitei)\s+#?([bcpt]\d+)(?:\s+(\d{4}-\d{2}))?$", texto)
    if match:
        chave = match.group(1)
        ano_mes = validar_ano_mes(match.group(2)) if match.group(2) else relogio.hoje(date).strftime("%Y-%m")
        return ano_mes, chave, "pago"

    match = re.match(r"^(?:desmarcar|marcar pendente|marcar como pendente|pendente)\s+#?([bcpt]\d+)(?:\s+(\d{4}-\d{2}))?$", texto)
    if match:
        chave = match.group(1)
        ano_mes = validar_ano_mes(match.group(2)) if match.group(2) else relogio.hoje(date).strftime("%Y-%m")
        return ano_mes, chave, "pendente"

    return None


def parsear_comando_resetar_checklist(texto_limpo: str):
    texto = normalizar_texto(texto_limpo)
    match = re.match(r"^(?:resetar|limpar|zerar)\s+checklist(?:\s+(\d{4}-\d{2}))?$", texto)
    if not match:
        return None
    return validar_ano_mes(match.group(1)) if match.group(1) else relogio.hoje(date).strftime("%Y-%m")


def resetar_checklist_formatado(ano_mes: str):
    ano_mes = validar_ano_mes(ano_mes) or relogio.hoje(date).strftime("%Y-%m")
    quantidade = resetar_checklist_pagamentos_mes(ano_mes)

    return "\n".join([
        "✅ Checklist resetado",
        "",
        f"Mês: {formatar_ano_mes_visual(ano_mes)}",
        f"Marcações removidas: {quantidade}",
        "",
        f"Para abrir de novo: checklist {ano_mes}",
    ])


# ============================================================
# Normalização segura de comandos por intenção
# ============================================================

def normalizar_comando_sinonimos(texto_limpo: str):
    """
    Converte sinônimos comuns para comandos canônicos antes do parser financeiro.

    Regras de QA:
    - Só normaliza quando a estrutura tem intenção administrativa clara.
    - Não transforma frases financeiras naturais em comando.
    - Mantém compatibilidade com comandos antigos.
    - Roda antes do parse_mensagem para evitar lançamentos indevidos.
    """

    texto = (texto_limpo or "").lower().strip()
    texto = re.sub(r"\s+", " ", texto)

    if not texto:
        return texto

    # -----------------------------
    # Consultas simples
    # -----------------------------
    consultas = {
        "fixo": "fixos",
        "fixos": "fixos",
        "compromisso": "compromissos",
        "compromissos": "compromissos",
        "parcela": "parcelamentos",
        "parcelas": "parcelamentos",
        "parcelamento": "parcelamentos",
        "parcelamentos": "parcelamentos",
        "entrada": "entradas",
        "entradas": "entradas",
        "receita": "entradas",
        "receitas": "entradas",
        "categoria": "categorias",
        "categorias": "categorias",
        "conta": "contas",
        "contas": "contas",
        "forma": "formas",
        "formas": "formas",
        "agenda": "agenda",
        "compromisso geral": "compromissos",
        "compromissos gerais": "compromissos",
        "ultimas": "últimas 10",
        "últimas": "últimas 10",
        "ultimas transacoes": "últimas 10",
        "últimas transações": "últimas 10",
        "ultimos": "últimas 10",
        "últimos": "últimas 10",
    }

    match_consulta = re.match(r"^(?:ver|listar|mostrar|consultar|abrir|exibir)\s+(.+)$", texto)
    if match_consulta:
        alvo = match_consulta.group(1).strip()

        if alvo in consultas:
            return consultas[alvo]

        match_ultimas_numero = re.match(r"^(?:ultimas|últimas|ultimos|últimos)(?:\s+transacoes|\s+transações)?\s+(\d+)$", alvo)
        if match_ultimas_numero:
            return f"últimas {match_ultimas_numero.group(1)}"

        match_mes = re.match(r"^(fixos|entradas|receitas|categorias|contas|formas|parcelas|agenda|compromissos)\s+(\d{4}-\d{2})$", alvo)
        if match_mes:
            nome = match_mes.group(1)
            ano_mes = match_mes.group(2)
            if nome == "receitas":
                nome = "entradas"
            if nome == "parcelas":
                nome = "parcelas"
            return f"{nome} {ano_mes}"

    # -----------------------------
    # Apagar/remover com alvo claro
    # -----------------------------
    verbos_apagar = r"(?:apagar|excluir|deletar|remover|tirar)"

    # deletar fixo 46 -> apagar fixo 46
    match = re.match(rf"^{verbos_apagar}\s+(fixo|compromisso)\s+#?c?(\d+)$", texto)
    if match:
        return f"apagar {match.group(1)} {match.group(2)}"

    # deletar entrada 2 -> apagar entrada 2
    match = re.match(rf"^{verbos_apagar}\s+(entrada|receita)\s+#?e?(\d+)$", texto)
    if match:
        return f"apagar entrada {match.group(2)}"

    # deletar parcelamento P1/C1 -> apagar parcelamento P1/C1
    match = re.match(rf"^{verbos_apagar}\s+(parcelamento|parcela)\s+#?([pc]?\d+)$", texto)
    if match:
        return f"apagar parcelamento {match.group(2)}"

    # deletar lançamento 7 / remover transação 7 -> apagar 7
    match = re.match(rf"^{verbos_apagar}\s+(?:lancamento|lançamento|transacao|transação|movimentacao|movimentação)\s+#?(\d+)$", texto)
    if match:
        return f"apagar {match.group(1)}"

    # deletar 7 -> apagar 7
    match = re.match(rf"^{verbos_apagar}\s+#?(\d+)$", texto)
    if match:
        return f"apagar {match.group(1)}"

    # deletar 7-10 -> apagar 7-10
    match = re.match(rf"^{verbos_apagar}\s+(\d+)\s*-\s*(\d+)$", texto)
    if match:
        return f"apagar {match.group(1)}-{match.group(2)}"

    # deletar meta mercado -> apagar meta mercado
    match = re.match(rf"^{verbos_apagar}\s+meta\s+(.+)$", texto)
    if match:
        return f"apagar meta {match.group(1).strip()}"

    # cancelar com alvo claro. Não normaliza "cancelar" solto nem frase financeira natural.
    match = re.match(r"^cancelar\s+(fixo|compromisso)\s+#?c?(\d+)$", texto)
    if match:
        return f"apagar {match.group(1)} {match.group(2)}"

    match = re.match(r"^cancelar\s+(parcelamento|parcela)\s+#?([pc]?\d+)$", texto)
    if match:
        return f"apagar parcelamento {match.group(2)}"

    # -----------------------------
    # Alterar/mudar/trocar/editar/ajustar/atualizar
    # -----------------------------
    verbos_alterar = r"(?:alterar|mudar|trocar|editar|ajustar|atualizar)"

    # trocar conta fixo 1 para BTG -> alterar conta fixo 1 para BTG
    match = re.match(
        rf"^{verbos_alterar}\s+conta\s+(?:do\s+)?(fixo|compromisso|parcela|parcelamento)\s+#?[cp]?(\d+)\s+(?:para|por)\s+(.+)$",
        texto
    )
    if match:
        return f"alterar conta {match.group(1)} {match.group(2)} para {match.group(3).strip()}"

    # trocar forma fixo 1 para pix -> alterar forma fixo 1 para pix
    match = re.match(
        rf"^{verbos_alterar}\s+forma\s+(?:do\s+)?(fixo|compromisso|parcela|parcelamento)\s+#?[cp]?(\d+)\s+(?:para|por)\s+(.+)$",
        texto
    )
    if match:
        return f"alterar forma {match.group(1)} {match.group(2)} para {match.group(3).strip()}"

    # trocar categoria fixo 1 para Telefonia -> alterar categoria fixo 1 para Telefonia
    match = re.match(
        rf"^{verbos_alterar}\s+categoria\s+(?:do\s+)?(fixo|compromisso|parcela|parcelamento)\s+#?[cp]?(\d+)\s+(?:para|por)\s+(.+)$",
        texto
    )
    if match:
        return f"alterar categoria {match.group(1)} {match.group(2)} para {match.group(3).strip()}"

    # editar vencimento fixo 3 para dia 10 -> alterar vencimento fixo 3 para dia 10
    match = re.match(
        rf"^{verbos_alterar}\s+vencimento\s+(?:do\s+)?(fixo|compromisso)\s+#?c?(\d+)\s+(?:para|por)\s+(?:dia\s+)?(\d{{1,2}})$",
        texto
    )
    if match:
        return f"alterar vencimento fixo {match.group(2)} para dia {match.group(3)}"

    # ajustar valor 7 para 42,90 -> corrigir 7 para 42,90
    match = re.match(rf"^{verbos_alterar}\s+valor\s+(?:do\s+)?(?:lancamento|lançamento|transacao|transação)?\s*#?(\d+)\s+(?:para|por)\s+(.+)$", texto)
    if match:
        return f"corrigir {match.group(1)} para {match.group(2).strip()}"

    # editar categoria 7 para Transporte -> mudar 7 para Transporte
    match = re.match(rf"^{verbos_alterar}\s+categoria\s+(?:do\s+)?(?:lancamento|lançamento|transacao|transação)?\s*#?(\d+)\s+(?:para|por)\s+(.+)$", texto)
    if match:
        return f"mudar {match.group(1)} para {match.group(2).strip()}"

    # corrigir valor 7 para 42,90 já existe; preserva.
    # mudar 7 para Transporte já existe; preserva.

    # -----------------------------
    # Pausar/reativar com alvo claro
    # -----------------------------
    match = re.match(r"^(?:pausar|suspender|desativar|parar|congelar)\s+(fixo|compromisso)\s+#?c?(\d+)$", texto)
    if match:
        return f"pausar {match.group(1)} {match.group(2)}"

    match = re.match(r"^(?:pausar|suspender|desativar|parar|congelar)\s+(entrada|receita)\s+#?e?(\d+)$", texto)
    if match:
        return f"pausar entrada {match.group(2)}"

    match = re.match(r"^(?:reativar|ativar|retomar|religar|voltar)\s+(fixo|compromisso)\s+#?c?(\d+)$", texto)
    if match:
        return f"reativar {match.group(1)} {match.group(2)}"

    match = re.match(r"^(?:reativar|ativar|retomar|religar|voltar)\s+(entrada|receita)\s+#?e?(\d+)$", texto)
    if match:
        return f"reativar entrada {match.group(2)}"

    # -----------------------------
    # Cadastro com alvo claro
    # -----------------------------
    # criar fixo internet 120 dia 10 -> novo fixo internet 120 dia 10
    match = re.match(r"^(?:cadastrar|adicionar|incluir|criar)\s+fixo\s+(.+)$", texto)
    if match:
        return f"novo fixo {match.group(1).strip()}"

    # adicionar entrada fixa salário 3800 dia 5 -> nova entrada fixa salário 3800 dia 5
    match = re.match(r"^(?:cadastrar|adicionar|incluir|criar)\s+entrada\s+fixa\s+(.+)$", texto)
    if match:
        return f"nova entrada fixa {match.group(1).strip()}"

    return texto



def _formatar_row_transacao_previa(transacao):
    if not transacao:
        return "Transação não encontrada."

    tipo_valor = "entrada" if transacao["tipo"] == "receita" else "saída"

    return formatar_item_card(
        identificador=f"#{transacao['id']}",
        data_item=transacao["data"],
        valor=transacao["valor"],
        categoria=transacao["categoria"],
        nome=transacao["descricao"] or "Sem descrição",
        conta=transacao["conta"] or "Não informada",
        forma=transacao["forma_pagamento"] or "não informada",
        tipo_valor=tipo_valor,
    )


PREFIXO_EXCLUSAO_PARCIAL_PARCELAMENTO = "⚠️ Exclusão parcial de parcelamento bloqueada"


def previa_exclusao_recusada(previa) -> bool:
    """Prévia que já é uma recusa: não há o que confirmar (nenhuma pendência)."""
    from database import PREFIXO_EXCLUSAO_FIXO_SERIE
    return str(previa or "").startswith((PREFIXO_EXCLUSAO_PARCIAL_PARCELAMENTO, PREFIXO_EXCLUSAO_FIXO_SERIE))


def _previa_parcelamento_incompleto(transacao_ids):
    """Recusa (texto) quando a exclusão levaria só parte de um parcelamento."""
    with get_connection() as conn:
        incompletos = parcelamentos_incompletos_conn(conn, transacao_ids)
    return mensagem_exclusao_parcial_parcelamento(incompletos) if incompletos else None


def preparar_previa_exclusao(comando: str):
    texto = normalizar_comando_sinonimos((comando or "").lower().strip())

    if not texto:
        return None

    match_ultimo = re.match(r"^apagar\s+(?:ultimo|último)$", texto)
    if match_ultimo:
        ultimas = buscar_ultimas_transacoes(1)
        if not ultimas:
            return "Não encontrei lançamento para apagar."

        bloqueio = _previa_parcelamento_incompleto([ultimas[0]["id"]])
        if bloqueio:
            return bloqueio

        return "\n".join([
            "Você está prestes a apagar o último lançamento:",
            "",
            _formatar_row_transacao_previa(ultimas[0]),
        ])

    match_faixa = re.match(r"^apagar\s+(\d+)\s*-\s*(\d+)$", texto)
    if match_faixa:
        id_inicio = int(match_faixa.group(1))
        id_fim = int(match_faixa.group(2))

        if id_inicio > id_fim:
            id_inicio, id_fim = id_fim, id_inicio

        transacoes = [
            t for t in buscar_todas_transacoes()
            if id_inicio <= int(t["id"]) <= id_fim
        ]

        if not transacoes:
            return f"Não encontrei lançamentos entre #{id_inicio} e #{id_fim}."

        bloqueio = _previa_parcelamento_incompleto([t["id"] for t in transacoes])
        if bloqueio:
            return bloqueio

        total = sum(t["valor"] for t in transacoes)
        ids = ", ".join(str(t["id"]) for t in transacoes[:8])
        if len(transacoes) > 8:
            ids += ", ..."

        return "\n".join([
            f"Você está prestes a apagar {len(transacoes)} lançamento(s):",
            "",
            bloco_total("Faixa", [
                f"│ {'IDs':<24} {(str(id_inicio) + ' a ' + str(id_fim)):>14}",
                f"│ {'Encontrados':<24} {str(len(transacoes)):>14}",
                linha_valor("Valor total", total),
            ]),
            "",
            f"IDs encontrados: {ids}",
            "",
            "Essa ação só será executada depois da sua confirmação.",
        ])

    match_transacao = re.match(r"^apagar\s+#?(\d+)$", texto)
    if match_transacao:
        transacao_id = int(match_transacao.group(1))
        transacao = buscar_transacao_por_id(transacao_id)

        if not transacao:
            return f"Não encontrei lançamento #{transacao_id}."

        bloqueio = _previa_parcelamento_incompleto([transacao_id])
        if bloqueio:
            return bloqueio

        return "\n".join([
            "Você está prestes a apagar este lançamento:",
            "",
            _formatar_row_transacao_previa(transacao),
        ])

    match_fixo = re.match(r"^apagar\s+(fixo|compromisso)\s+#?c?(\d+)$", texto)
    if match_fixo:
        compromisso_id = int(match_fixo.group(2))
        compromisso = buscar_compromisso_por_id(compromisso_id)

        if not compromisso:
            return f"Não encontrei fixo/compromisso #{compromisso_id}."

        from database import bloqueio_exclusao_fixo_serie_conn
        with get_connection() as conn:
            bloqueio = bloqueio_exclusao_fixo_serie_conn(conn, compromisso)
        if bloqueio:
            return bloqueio

        return "\n".join([
            "Você está prestes a apagar este compromisso:",
            "",
            bloco_total(f"#C{compromisso['id']} · {compromisso['nome']}", [
                f"│ {'Tipo':<24} {str(compromisso['tipo']):>14}",
                f"│ {'Categoria':<24} {str(compromisso['categoria'] or 'Não informada')[-14:]:>14}",
                f"│ {'Conta':<24} {str(compromisso['conta_pagamento'] or 'Não informada')[-14:]:>14}",
                f"│ {'Dia':<24} {str(compromisso['dia_vencimento'] or 'N/D'):>14}",
                linha_valor("Valor", compromisso["valor"]),
            ]),
        ])

    match_entrada = re.match(r"^apagar\s+entrada\s+#?e?(\d+)$", texto)
    if match_entrada:
        entrada_id = int(match_entrada.group(1))
        entrada = buscar_compromisso_por_id(entrada_id)

        if not entrada or entrada["tipo"] not in ["entrada_fixa", "entrada_avulsa"]:
            return f"Não encontrei entrada #E{entrada_id}."

        data_ref = entrada["data_inicio"] if entrada["tipo"] == "entrada_avulsa" else f"dia {entrada['dia_vencimento']}"

        return "\n".join([
            "Você está prestes a apagar esta entrada:",
            "",
            bloco_total(f"#E{entrada['id']} · {entrada['nome']}", [
                f"│ {'Tipo':<24} {str(entrada['tipo']):>14}",
                f"│ {'Data':<24} {str(data_ref)[-14:]:>14}",
                f"│ {'Conta':<24} {str(entrada['conta_pagamento'] or 'Não informada')[-14:]:>14}",
                linha_valor("Valor", entrada["valor"]),
            ]),
        ])

    match_parcelamento = re.match(r"^apagar\s+parcelamento\s+#?([pc]?\d+)$", texto)
    if match_parcelamento:
        identificador = match_parcelamento.group(1).upper()

        return "\n".join([
            "Você está prestes a apagar um parcelamento:",
            "",
            bloco_total("Parcelamento", [
                f"│ {'Identificador':<24} {identificador:>14}",
            ]),
            "",
            "Confirme apenas se tem certeza.",
        ])

    match_meta = re.match(r"^apagar\s+meta\s+(.+)$", texto)
    if match_meta:
        categoria = match_meta.group(1).strip()
        meta = buscar_meta_por_categoria(categoria)

        if not meta:
            return f"Não encontrei meta para a categoria: {categoria}"

        return "\n".join([
            "Você está prestes a apagar esta meta:",
            "",
            bloco_total(meta["categoria"], [
                linha_valor("Valor da meta", meta["valor"]),
            ]),
        ])

    return _previa_exclusao_extras(texto)


# Exclusões que antes apagavam direto (sem prévia, backup nem auditoria).
# app.comando_exige_confirmacao_exclusao usa a mesma lista.
PADROES_EXCLUSAO_EXTRAS = (
    r"^(?:apagar|excluir|deletar|remover)\s+transfer[eê]ncia(?:\s+de)?\s+caixa\s+#?\d+$",
)
_RE_APAGAR_TRANSFERENCIA_CAIXA = r"^(?:apagar|excluir|deletar|remover)\s+transfer[eê]ncia(?:\s+de)?\s+caixa\s+#?(\d+)$"


def _parse_apagar_data_pagamento(texto_limpo: str):
    """(fixa: bool, codigo, ano_mes) de "apagar data pagamento|vencimento [fixo] X [AAAA-MM]"."""
    texto = normalizar_texto(texto_limpo or "")
    codigo = r"([a-zA-Z]?\d+|B_[a-z0-9_]+|b_[a-z0-9_]+|[cCpPtT]\d+)"
    for fixa, alvo in ((True, r"(?:vencimento fixo|data pagamento fixa|data de pagamento fixa)"),
                       (False, r"(?:data pagamento|data de pagamento|vencimento)")):
        m = re.match(rf"^(?:apagar|remover|tirar|limpar)\s+{alvo}\s+{codigo}(?:\s+(\d{{4}}-\d{{2}}))?$", texto)
        if m:
            ano_mes = validar_ano_mes(m.group(2)) if m.group(2) else relogio.hoje(date).strftime("%Y-%m")
            return fixa, m.group(1), ano_mes
    return None


def _previa_exclusao_extras(texto: str):
    m = re.match(_RE_APAGAR_TRANSFERENCIA_CAIXA, texto)
    if m:
        from database import buscar_transferencia_caixa_por_id
        t = buscar_transferencia_caixa_por_id(int(m.group(1)))
        if not t:
            return f"Não encontrei transferência de caixa #{m.group(1)}."
        return "\n".join([
            "Você está prestes a apagar esta transferência de caixa:",
            "",
            f"#{t['id']} | {formatar_data_visual(t['data'])} | {formatar_moeda(float(t['valor'] or 0))} | "
            f"{t['conta_origem']} → {t['conta_destino']}",
            "",
            "O saldo das duas contas volta ao que era sem esta transferência.",
        ])
    mes_reset = parsear_comando_resetar_checklist(texto)
    if mes_reset:
        marcacoes = buscar_checklist_status_mes(mes_reset)
        return "\n".join([
            "Você está prestes a resetar o checklist:",
            "",
            f"Mês: {formatar_ano_mes_visual(mes_reset)}",
            f"Marcações que serão removidas: {len(marcacoes)}",
            "Lançamentos e pagamentos registrados não são apagados.",
        ])
    data_pag = _parse_apagar_data_pagamento(texto)
    if data_pag:
        fixa, codigo, ano_mes = data_pag
        if fixa:
            return f"Você está prestes a remover o vencimento fixo do item {codigo}.\nOs próximos meses voltam a usar a data original do item."
        return f"Você está prestes a remover a data de pagamento do item {codigo} em {formatar_ano_mes_visual(ano_mes)}."
    return None


def comando_destrutivo_exclusao(texto_limpo: str):
    texto = normalizar_comando_sinonimos((texto_limpo or "").lower().strip())

    if not texto:
        return False

    verbos = r"(?:apagar|excluir|deletar|remover|tirar|cancelar)"

    padroes = [
        rf"^{verbos}\s+(?:ultimo|último)$",
        rf"^{verbos}\s+#?\d+$",
        rf"^{verbos}\s+\d+\s*-\s*\d+$",
        rf"^{verbos}\s+(?:lançamento|lancamento|transação|transacao|movimentação|movimentacao)\s+#?\d+$",
        rf"^{verbos}\s+(?:fixo|compromisso)\s+#?c?\d+$",
        rf"^{verbos}\s+(?:entrada|receita)\s+#?e?\d+$",
        rf"^{verbos}\s+(?:parcelamento|parcela)\s+#?[pc]?\d+$",
        rf"^{verbos}\s+meta\s+.+$",
        *PADROES_EXCLUSAO_EXTRAS,
    ]

    return any(re.match(padrao, texto) for padrao in padroes) or bool(
        parsear_comando_resetar_checklist(texto) or _parse_apagar_data_pagamento(texto))


def mensagem_exclusao_bloqueada_por_confirmacao(texto_limpo: str):
    return (
        "⚠️ Exclusão bloqueada por segurança\n\n"
        "Nada foi apagado.\n\n"
        "Esse comando precisa passar pela confirmação do assessor.\n"
        "Envie novamente o comando e confirme quando o bot perguntar.\n\n"
        "Exemplos:\n"
        "apagar 7\n"
        "apagar fixo 46\n"
        "deletar parcelamento P1"
    )



def conta_transacao_bate(transacao, conta_busca: str):
    busca = texto_chave_saldo(conta_busca)
    conta = texto_chave_saldo(transacao["conta"] or "")
    forma = texto_chave_saldo(transacao["forma_pagamento"] or "")

    if not busca:
        return False

    return (
        busca in conta
        or busca in forma
        or conta in busca and conta
        or forma in busca and forma
    )


def titulo_modo_lancamentos(modo: str):
    if modo == "despesas":
        return "💸 Despesas"
    if modo == "receitas":
        return "🟢 Receitas"
    return "📒 Lançamentos"


def filtrar_transacoes_conta_mes(conta: str, ano_mes: str, modo: str = "todos"):
    itens = []

    for t in buscar_transacoes_por_mes(ano_mes):
        if not conta_transacao_bate(t, conta):
            continue

        if modo == "despesas" and t["tipo"] != "despesa":
            continue

        if modo == "receitas" and t["tipo"] != "receita":
            continue

        itens.append(t)

    return itens


def listar_contas_movimentadas_mes(ano_mes: str):
    contas = {}

    for t in buscar_transacoes_por_mes(ano_mes):
        conta = nome_conta_padrao(t["conta"] or t["forma_pagamento"])
        if conta not in contas:
            contas[conta] = {"entradas": 0.0, "despesas": 0.0, "qtd": 0}

        contas[conta]["qtd"] += 1

        if t["tipo"] == "receita":
            contas[conta]["entradas"] += float(t["valor"] or 0)
        elif t["tipo"] == "despesa":
            contas[conta]["despesas"] += float(t["valor"] or 0)

    return contas


def formatar_linha_lancamento_conta(transacao):
    sinal = "+" if transacao["tipo"] == "receita" else "-"
    emoji = "🟢" if transacao["tipo"] == "receita" else "💸"
    valor = formatar_moeda(float(transacao["valor"] or 0))
    descricao = transacao["descricao"] or "Sem descrição"
    categoria = transacao["categoria"] or "Sem categoria"
    conta = transacao["conta"] or "Sem conta"
    forma = transacao["forma_pagamento"] or "Sem forma"

    return "\n".join([
        f"{emoji} #{transacao['id']} · {formatar_data_visual(transacao['data'])}",
        f"   {descricao}",
        f"   {sinal}{valor} · {categoria}",
        f"   {conta} · {forma}",
    ])


def extrato_conta_mes_formatado(conta: str, ano_mes: str, modo: str = "todos", pagina: int = 1):
    conta = formatar_nome_conta_saldo(conta)
    modo = modo if modo in ["todos", "despesas", "receitas"] else "todos"
    pagina = max(int(pagina or 1), 1)
    por_pagina = 10

    itens = filtrar_transacoes_conta_mes(conta, ano_mes, modo)

    total_entradas = sum(float(t["valor"] or 0) for t in itens if t["tipo"] == "receita")
    total_despesas = sum(float(t["valor"] or 0) for t in itens if t["tipo"] == "despesa")
    saldo_liquido = total_entradas - total_despesas

    total_paginas = max(math.ceil(len(itens) / por_pagina), 1)
    pagina = min(pagina, total_paginas)
    inicio = (pagina - 1) * por_pagina
    fim = inicio + por_pagina
    pagina_itens = itens[inicio:fim]

    titulo = titulo_modo_lancamentos(modo)

    linhas = [
        f"{titulo} — {conta} — {formatar_ano_mes_visual(ano_mes)}",
        "",
        bloco_total("Resumo filtrado", [
            linha_valor("Entradas", total_entradas),
            linha_valor("Despesas", total_despesas),
            f"│ {'Líquido lançado':<24} {formatar_status_saldo(saldo_liquido):>14}",
        ]),
        "",
        f"Filtro: transações reais · conta/forma contendo \"{conta}\"",
        f"Registros encontrados: {len(itens)}",
    ]

    if modo == "despesas":
        linhas.append(f"Total de despesas: {formatar_moeda(total_despesas)}")
    elif modo == "receitas":
        linhas.append(f"Total de receitas: {formatar_moeda(total_entradas)}")

    if not itens:
        contas_mes = listar_contas_movimentadas_mes(ano_mes)
        linhas.extend([
            "",
            "Não encontrei lançamentos com esse filtro.",
        ])

        if contas_mes:
            linhas.extend(["", "Contas encontradas no mês:"])
            for nome, valores in sorted(contas_mes.items(), key=lambda kv: kv[1]["despesas"], reverse=True):
                linhas.append(
                    f"- {nome}: {valores['qtd']} lanç. · despesas {formatar_moeda(valores['despesas'])} · entradas {formatar_moeda(valores['entradas'])}"
                )

        linhas.extend([
            "",
            "Exemplos:",
            f"despesas mercado pago {ano_mes}",
            f"extrato mercado pago {ano_mes}",
            f"receitas mercado pago {ano_mes}",
        ])

        return "\n".join(linhas)

    linhas.extend([
        "",
        f"Página {pagina} de {total_paginas}",
        "",
    ])

    for i, transacao in enumerate(pagina_itens, start=inicio + 1):
        linhas.append(f"{i}) {formatar_linha_lancamento_conta(transacao)}")
        linhas.append("")

    if total_paginas > 1:
        proxima = pagina + 1 if pagina < total_paginas else total_paginas
        anterior = pagina - 1 if pagina > 1 else 1

        linhas.extend([
            "Paginação:",
            f"{modo if modo != 'todos' else 'extrato'} {conta} {ano_mes} pagina {proxima}",
            f"{modo if modo != 'todos' else 'extrato'} {conta} {ano_mes} pagina {anterior}",
        ])

    linhas.extend([
        "Para corrigir um lançamento:",
        "toque no número em Últimos ou envie: lançamento #ID",
    ])

    return "\n".join(linhas)


def conta_item_bate(item: dict, conta_busca: str):
    busca = texto_chave_saldo(conta_busca)
    conta = texto_chave_saldo(obter_conta_item_saldo(item))
    forma = texto_chave_saldo(item.get("forma_pagamento") or "")

    if not busca:
        return False

    return (
        busca in conta
        or busca in forma
        or conta in busca and conta
        or forma in busca and forma
    )


def filtrar_esperados_conta_mes(conta: str, ano_mes: str):
    itens = []

    for item in projetar_pagamentos_mes(ano_mes, incluir_transacoes=False):
        if conta_item_bate(item, conta):
            itens.append(item)

    return itens


def formatar_linha_esperado_conta(item: dict):
    valor = formatar_moeda(float(item.get("valor") or 0))
    nome = item.get("nome") or "Compromisso"
    categoria = item.get("categoria") or "Sem categoria"
    conta = item.get("conta_pagamento") or "Sem conta"
    forma = item.get("forma_pagamento") or "Sem forma"
    tipo = item.get("tipo") or "compromisso"
    identificador = item.get("id") or "-"

    parcela = ""
    if item.get("parcela_atual") and item.get("parcelas_total"):
        parcela = f" · {item.get('parcela_atual')}/{item.get('parcelas_total')}"

    return "\n".join([
        f"📌 #C{identificador} · {nome}{parcela}",
        f"   -{valor} · {categoria}",
        f"   {conta} · {forma} · {tipo}",
    ])


def movimentacoes_conta_mes_formatado(conta: str, ano_mes: str, somente_despesas: bool = False, pagina: int = 1):
    conta = formatar_nome_conta_saldo(conta)
    pagina = max(int(pagina or 1), 1)
    por_pagina = 8

    transacoes = filtrar_transacoes_conta_mes(conta, ano_mes, "despesas" if somente_despesas else "todos")
    esperados = filtrar_esperados_conta_mes(conta, ano_mes)

    entradas_realizadas = sum(float(t["valor"] or 0) for t in transacoes if t["tipo"] == "receita")
    despesas_realizadas = sum(float(t["valor"] or 0) for t in transacoes if t["tipo"] == "despesa")
    despesas_esperadas = sum(float(item.get("valor") or 0) for item in esperados)
    total_saida_mes = despesas_realizadas + despesas_esperadas
    liquido_realizado = entradas_realizadas - despesas_realizadas
    saldo_considerado = entradas_realizadas - total_saida_mes

    # Monta uma lista paginada única, mantendo a origem visível.
    linhas_itens = []
    for t in transacoes:
        if somente_despesas and t["tipo"] != "despesa":
            continue
        linhas_itens.append(("realizado", t["data"], t["id"], t))

    for item in esperados:
        data_item = item.get("data") or f"{ano_mes}-01"
        linhas_itens.append(("esperado", data_item, item.get("id") or 0, item))

    linhas_itens.sort(key=lambda x: (x[1], str(x[0]), int(x[2] or 0)))

    total_paginas = max(math.ceil(len(linhas_itens) / por_pagina), 1)
    pagina = min(pagina, total_paginas)
    inicio = (pagina - 1) * por_pagina
    fim = inicio + por_pagina
    pagina_itens = linhas_itens[inicio:fim]

    titulo = "💸 Despesas" if somente_despesas else "📒 Movimentações"
    linhas = [
        f"{titulo} — {conta} — {formatar_ano_mes_visual(ano_mes)}",
        "",
        bloco_total("Resumo da conta", [
            linha_valor("Entradas realizadas", entradas_realizadas),
            linha_valor("Despesas realizadas", despesas_realizadas),
            linha_valor("Despesas esperadas", despesas_esperadas),
            linha_valor("Total saídas mês", total_saida_mes),
            f"│ {'Líquido realizado':<24} {formatar_status_saldo(liquido_realizado):>14}",
            f"│ {'Saldo considerado':<24} {formatar_status_saldo(saldo_considerado):>14}",
        ]),
        "",
        "Critério:",
        "Realizado = transações já lançadas.",
        "Esperado = fixos, compromissos e parcelas da conta no mês.",
        "",
        f"Registros: {len(transacoes)} realizados + {len(esperados)} esperados",
    ]

    if not linhas_itens:
        contas_mes = listar_contas_movimentadas_mes(ano_mes)
        linhas.extend([
            "",
            "Não encontrei movimentações para essa conta.",
        ])

        if contas_mes:
            linhas.extend(["", "Contas encontradas nas transações do mês:"])
            for nome, valores in sorted(contas_mes.items(), key=lambda kv: kv[1]["despesas"], reverse=True):
                linhas.append(
                    f"- {nome}: {valores['qtd']} lanç. · despesas {formatar_moeda(valores['despesas'])} · entradas {formatar_moeda(valores['entradas'])}"
                )

        linhas.extend([
            "",
            "Exemplos:",
            f"movimentações mercado pago {ano_mes}",
            f"despesas mercado pago {ano_mes}",
            f"extrato mercado pago {ano_mes}",
        ])

        return "\n".join(linhas)

    linhas.extend(["", f"Página {pagina} de {total_paginas}", ""])

    for pos, (origem, _data, _id, item) in enumerate(pagina_itens, start=inicio + 1):
        if origem == "realizado":
            linhas.append(f"{pos}) ✅ Realizado")
            linhas.append(formatar_linha_lancamento_conta(item))
        else:
            linhas.append(f"{pos}) 📌 Esperado")
            linhas.append(formatar_linha_esperado_conta(item))
        linhas.append("")

    if total_paginas > 1:
        proxima = pagina + 1 if pagina < total_paginas else total_paginas
        anterior = pagina - 1 if pagina > 1 else 1
        comando = "despesas" if somente_despesas else "movimentações"

        linhas.extend([
            "Paginação:",
            f"{comando} {conta} {ano_mes} pagina {proxima}",
            f"{comando} {conta} {ano_mes} pagina {anterior}",
            "",
        ])

    linhas.extend([
        "Para ver só transações reais:",
        f"extrato {conta} {ano_mes}",
        "",
        "Para corrigir transação real:",
        "envie: lançamento #ID",
    ])

    return "\n".join(linhas)


def parsear_comando_movimentacoes_conta_mes(texto_limpo: str):
    padrao = (
        r"^(despesas|gastos|saidas|saídas|movimentações|movimentacoes|lançamentos|lancamentos)"
        r"(?:\s+da conta|\s+do banco|\s+no banco|\s+na conta)?"
        r"\s+(.+?)\s+(\d{4}-\d{2}|\d{1,2}/\d{4}|[a-záàâãéêíóôõúç]+/\d{4}|[a-záàâãéêíóôõúç]+\s+\d{4})(?:\s+pagina\s+(\d+))?$"
    )

    match = re.match(padrao, texto_limpo)
    if not match:
        return None

    comando = match.group(1)
    conta = match.group(2).strip()
    ano_mes = normalizar_ano_mes_flexivel(match.group(3))
    pagina = int(match.group(4) or 1)

    if not ano_mes:
        return None

    somente_despesas = comando in ["despesas", "gastos", "saidas", "saídas"]
    return conta, ano_mes, somente_despesas, pagina


def normalizar_ano_mes_flexivel(texto: str | None):
    texto_original = (texto or "").strip()
    if not texto_original:
        return None

    direto = validar_ano_mes(texto_original)
    if direto:
        return direto

    match_num = re.match(r"^(\d{1,2})/(\d{4})$", texto_original)
    if match_num:
        mes = int(match_num.group(1))
        ano = int(match_num.group(2))
        if 1 <= mes <= 12:
            return f"{ano:04d}-{mes:02d}"

    chave = texto_chave_saldo(texto_original.replace("/", " "))
    match_nome = re.match(r"^([a-z\s]+)\s+(\d{4})$", chave)
    if not match_nome:
        return None

    mes_texto = match_nome.group(1).strip()
    ano = int(match_nome.group(2))

    meses = {
        "janeiro": 1, "jan": 1,
        "fevereiro": 2, "fev": 2,
        "marco": 3, "mar": 3,
        "março": 3,
        "abril": 4, "abr": 4,
        "maio": 5, "mai": 5,
        "junho": 6, "jun": 6,
        "julho": 7, "jul": 7,
        "agosto": 8, "ago": 8,
        "setembro": 9, "set": 9,
        "outubro": 10, "out": 10,
        "novembro": 11, "nov": 11,
        "dezembro": 12, "dez": 12,
    }

    mes = meses.get(mes_texto)
    if not mes:
        return None

    return f"{ano:04d}-{mes:02d}"


def parsear_comando_extrato_conta_mes(texto_limpo: str):
    # Exemplos:
    # despesas mercado pago 2026-06
    # extrato mercado pago 2026-06
    # lancamentos mercado pago 2026-06 pagina 2
    # receitas itau 2026-06
    padrao = (
        r"^(despesas|gastos|saidas|saídas|receitas|entradas|extrato|lançamentos|lancamentos|movimentações|movimentacoes)"
        r"(?:\s+da conta|\s+do banco|\s+no banco|\s+na conta)?"
        r"\s+(.+?)\s+(\d{4}-\d{2}|\d{1,2}/\d{4}|[a-záàâãéêíóôõúç]+/\d{4}|[a-záàâãéêíóôõúç]+\s+\d{4})(?:\s+pagina\s+(\d+))?$"
    )

    match = re.match(padrao, texto_limpo)
    if not match:
        return None

    comando = match.group(1)
    conta = match.group(2).strip()
    ano_mes = normalizar_ano_mes_flexivel(match.group(3))
    pagina = int(match.group(4) or 1)

    if not ano_mes:
        return None

    if comando in ["despesas", "gastos", "saidas", "saídas"]:
        modo = "despesas"
    elif comando in ["receitas", "entradas"]:
        modo = "receitas"
    else:
        modo = "todos"

    return conta, ano_mes, modo, pagina



def montar_aprender_menu():
    return "\n".join([
        "🎓 Aprender a usar o Assessor",
        "",
        "Escolha um tema. As aulas explicam conceito, exemplo e como conferir o resultado.",
        "",
        "Comece por aqui:",
        "aprender primeiros passos",
        "aprender lançamentos",
        "aprender faturas",
        "aprender rotina",
        "",
        "Temas disponíveis:",
        "1. primeiros passos",
        "2. lançamentos",
        "3. faturas e fechamento",
        "4. caixa",
        "5. transferências",
        "6. fixos e entradas previstas",
        "7. meu mês e análises",
        "8. compromissos / quanto vou pagar",
        "9. checklist e vencimentos",
        "10. conciliação",
        "11. planejamento e limites",
        "12. auditoria e correções",
        "13. dados, backup e segurança",
        "14. Caju / VR",
        "15. rotina diária",
        "16. tudo",
        "",
        "Você também pode enviar: aprender <tema>.",
    ])


def montar_aula_primeiros_passos():
    return "\n".join([
        "🎓 Aula: primeiros passos", "",
        "Pense no assessor em quatro camadas:",
        "1) Caixa: dinheiro realizado por conta.",
        "2) Compromissos: o que ainda pode pesar ou entrar.",
        "3) Histórico: o que realmente aconteceu.",
        "4) Meu mês: combinação dessas informações em uma visão financeira.", "",
        "Rotina inicial:",
        "• confira Contas e saldos",
        "• cadastre fixos/entradas previstas",
        "• registre movimentos reais",
        "• use A pagar/A receber e Conciliação para evitar dupla contagem", "",
        "Regra de ouro: previsão não é realizado.",
        "Próxima aula: aprender lançamentos",
    ])


def montar_aula_lancamentos():
    return "\n".join([
        "🎓 Aula: lançamentos", "",
        "Use frases naturais ou o fluxo por botões. Informe valor, descrição, forma e conta quando souber.", "",
        "Exemplos:",
        "gastei 35 almoço pix Itaú",
        "gastei 70 mercado crédito Itaú",
        "recebi 3800 salário", "",
        "Parcelamento:",
        "Se você não informar parcelas, o fluxo pergunta quando aplicável.",
        "Se já souber: comprei celular em 12x de 50 no crédito Nubank.", "",
        "No crédito, a partir do dia 25, o assessor pergunta em qual fatura a compra entra.",
        "A data real da compra continua preservada.", "",
        "Confira antes de salvar e use Histórico depois.",
    ])


def montar_aula_faturas():
    return "\n".join([
        "🎓 Aula: faturas e fechamento do cartão", "",
        "Compra no crédito e pagamento da fatura são eventos diferentes.",
        "A compra mantém a data real; a competência define a fatura.", "",
        "Até o dia 24:",
        "o fluxo segue a competência do mês da compra.", "",
        "A partir do dia 25:",
        "você escolhe fatura atual ou próxima.",
        "Ex.: compra em 25/09 escolhendo outubro → data 25/09 e fatura outubro.", "",
        "Parcelado:",
        "3x escolhendo outubro → outubro, novembro e dezembro.", "",
        "Pagamento da fatura:",
        "use A pagar e o fluxo da própria fatura; não registre o pagamento como nova compra.",
        "Pagar uma fatura não apaga parcelas futuras.",
    ])


def montar_aula_caixa():
    return "\n".join([
        "🎓 Aula: caixa por conta", "",
        "Caixa é o dinheiro disponível em cada banco/conta.",
        "Pix, débito, dinheiro e transferências de saída mexem no caixa imediatamente.",
        "Crédito/fatura não reduz caixa na compra.", "",
        "Use: caixa | saldo 2026-09 Itaú | Contas e saldos.",
        "Ajuste saldo somente quando estiver reconciliando a base real.",
    ])


def montar_aula_transferencias():
    return "\n".join([
        "🎓 Aula: transferências entre contas", "",
        "Transferência própria não é receita nem despesa.",
        "Ela reduz a conta de origem, aumenta a de destino e mantém o total do caixa.", "",
        "Exemplo: transferi 100 do Itaú para Caju", "",
        "Consultar: transferências caixa 2026-09",
        "Apagar: apagar transferencia caixa 3", "",
        "Pix é forma; Itaú/Caju/Mercado Pago são contas.",
    ])


def montar_aula_previsoes():
    return "\n".join([
        "🎓 Aula: fixos e entradas previstas", "",
        "Fixos representam obrigações recorrentes; parcelamentos têm começo e fim; entradas previstas ainda não são dinheiro recebido.", "",
        "Use A pagar e A receber para acompanhar.",
        "Quando algo acontecer de verdade, registre/vincule o movimento real em vez de duplicar.", "",
        "Guias avançados: /help fixos e /help entradas.",
    ])


def montar_aula_meu_mes():
    return "\n".join([
        "🎓 Aula: Meu mês e análises", "",
        "Meu mês resume saldo herdado, movimentos realizados, obrigações e sobra prevista.",
        "Análises mostram distribuição e evolução; Central de atenção destaca sinais objetivos.", "",
        "Quando um valor parecer estranho, não corrija no escuro: use auditoria primeiro.",
        "Ex.: auditar despesas 2026-09 | de onde vem as despesas 2026-09.",
    ])


def montar_aula_compromissos():
    return "\n".join([
        "🎓 Aula: compromissos e quanto vou pagar", "",
        "Compromissos mostram o que ainda pesa no mês: fixos, parcelas e crédito/faturas conforme a regra do motor.",
        "Movimentos imediatos como Pix já foram para o caixa e não devem ser cobrados de novo.", "",
        "Use A pagar ou: quanto vou pagar no Itaú em 2026-09.",
    ])


def montar_aula_checklist():
    return "\n".join([
        "🎓 Aula: checklist e vencimentos", "",
        "Checklist organiza obrigações abertas, pagas e revisões.",
        "Abra o detalhe antes de dar baixa; se a saída já está no Histórico, vincule-a.", "",
        "Vencimentos alimentam a agenda e lembretes.",
        "Ex.: vencimentos hoje | vencimentos 2026-09.",
    ])


def montar_aula_conciliacao():
    return "\n".join([
        "🎓 Aula: conciliação", "",
        "Conciliação liga uma previsão ao movimento que realmente aconteceu.",
        "Isso evita somar previsão + realização duas vezes.", "",
        "Se um movimento já existe no Histórico, prefira vincular em vez de criar outro.",
        "Movimentos vinculados podem exigir desvinculação antes de alterações financeiras.",
    ])


def montar_aula_planejamento():
    return "\n".join([
        "🎓 Aula: planejamento e limites", "",
        "Limites acompanham categorias; Meu plano organiza próximos passos; Simular estima impacto sem gravar.",
        "Recorrências são padrões observados e não criam/cancelam compromissos automaticamente.", "",
        "Regra: hipótese de planejamento nunca vira movimento realizado sem confirmação.",
    ])


def montar_aula_auditoria():
    return "\n".join([
        "🎓 Aula: auditoria e correções", "",
        "Quando um número parecer errado, primeiro descubra a origem.",
        "Use Histórico, detalhes, auditoria do mês e auditoria de despesas.", "",
        "Exemplos:",
        "auditar mês 2026-09",
        "auditar despesas 2026-09",
        "de onde vem as despesas 2026-09", "",
        "Só depois corrija valor, categoria, conta ou forma. Exclusões devem usar o ID correto e confirmação.",
    ])


def montar_aula_dados():
    return "\n".join([
        "🎓 Aula: dados, backup e segurança", "",
        "Backup é a cópia de recuperação do assessor. Exportar CSV é consulta/transporte e não substitui backup.",
        "Importação deve ser analisada antes da confirmação.", "",
        "PIN protege o acesso ao assessor; ocultar valores não apaga mensagens antigas do Telegram.",
        "Ao terminar, bloqueie o assessor quando fizer sentido.",
    ])


def montar_aula_caju():
    return "\n".join([
        "🎓 Aula: Caju / VR", "",
        "Caju é tratado como conta própria. Registre o crédito do benefício quando ele realmente cair.",
        "Gastos que reduzem o saldo imediatamente devem usar a forma adequada, por exemplo pix Caju.",
        "Confira em Contas e saldos ou no extrato da conta.",
    ])




def montar_aula_rotina():
    return "\n".join([
        "🎓 Aula: rotina diária", "",
        "Manhã: confira vencimentos/alertas e Central de atenção.",
        "Durante o dia: registre somente o que aconteceu; no crédito, revise parcelamento e competência da fatura.",
        "Ao receber: registre ou vincule a entrada real.",
        "Ao pagar: use A pagar; se a saída já existe, vincule.",
        "Fim do dia: confira Meu mês, Contas e saldos e Histórico.",
        "Fim do mês: use Fechamento e auditoria se houver divergência.",
    ])


def montar_aula_tudo():
    return "\n\n━━━━━━━━━━━━━━━━━━━━\n\n".join([
        montar_aula_primeiros_passos(), montar_aula_lancamentos(), montar_aula_faturas(),
        montar_aula_caixa(), montar_aula_transferencias(), montar_aula_previsoes(),
        montar_aula_meu_mes(), montar_aula_compromissos(), montar_aula_checklist(),
        montar_aula_conciliacao(), montar_aula_planejamento(), montar_aula_auditoria(),
        montar_aula_dados(), montar_aula_caju(), montar_aula_rotina(),
    ])


def montar_aprender_tema(tema: str):
    tema = normalizar_texto(tema or "").strip().lower()
    aliases = {
        "1":"primeiros", "primeiros passos":"primeiros", "inicio":"primeiros", "começar":"primeiros", "comecar":"primeiros",
        "2":"lancamentos", "lançamento":"lancamentos", "lançamentos":"lancamentos", "gastos":"lancamentos", "receitas":"lancamentos",
        "3":"faturas", "fatura":"faturas", "cartao":"faturas", "cartão":"faturas", "credito":"faturas", "crédito":"faturas", "fechamento cartão":"faturas",
        "4":"caixa", "saldo":"caixa", "saldos":"caixa",
        "5":"transferencias", "transferencia":"transferencias", "transferência":"transferencias", "transferências":"transferencias",
        "6":"previsoes", "previsões":"previsoes", "fixos":"previsoes", "entradas previstas":"previsoes",
        "7":"meu mes", "meu mês":"meu mes", "analises":"meu mes", "análises":"meu mes",
        "8":"compromissos", "quanto pagar":"compromissos", "quanto vou pagar":"compromissos",
        "9":"checklist", "vencimentos":"checklist", "alertas":"checklist",
        "10":"conciliacao", "conciliação":"conciliacao", "conciliar":"conciliacao",
        "11":"planejamento", "limites":"planejamento", "planejar":"planejamento", "simular":"planejamento",
        "12":"auditoria", "corrigir":"auditoria", "correção":"auditoria", "correcao":"auditoria", "auditar":"auditoria",
        "13":"dados", "backup":"dados", "seguranca":"dados", "segurança":"dados", "exportar":"dados", "importar":"dados",
        "14":"caju", "vr":"caju", "caju/vr":"caju",
        "15":"rotina", "rotina diária":"rotina", "rotina diaria":"rotina", "dia a dia":"rotina",
        "16":"tudo", "completo":"tudo", "aula completa":"tudo",
    }
    tema = aliases.get(tema, tema)
    aulas = {
        "primeiros": montar_aula_primeiros_passos,
        "lancamentos": montar_aula_lancamentos,
        "faturas": montar_aula_faturas,
        "caixa": montar_aula_caixa,
        "transferencias": montar_aula_transferencias,
        "previsoes": montar_aula_previsoes,
        "meu mes": montar_aula_meu_mes,
        "compromissos": montar_aula_compromissos,
        "checklist": montar_aula_checklist,
        "conciliacao": montar_aula_conciliacao,
        "planejamento": montar_aula_planejamento,
        "auditoria": montar_aula_auditoria,
        "dados": montar_aula_dados,
        "caju": montar_aula_caju,
        "rotina": montar_aula_rotina,
        "tudo": montar_aula_tudo,
    }
    if tema in aulas:
        return aulas[tema]()
    return "\n".join([
        f"Não encontrei uma aula para: {tema}", "",
        "Envie apenas: aprender", "ou tente:",
        "aprender faturas", "aprender conciliação", "aprender planejamento", "aprender auditoria",
    ])


def parsear_comando_aprender(texto_limpo: str):
    texto = normalizar_texto(texto_limpo or "").strip()
    if texto in ["aprender", "aula", "treinamento", "manual", "tutorial", "guia"]:
        return montar_aprender_menu()
    match = re.match(r"^(?:aprender|aula|treinamento|manual|tutorial|guia)\s+(.+)$", texto)
    # "guia IPTU 300" é um gasto: tema de aula não leva valor numa frase de 3+ palavras.
    if match and not texto.startswith("aprender") and len(texto.split()) >= 3 and re.search(r"\d", texto):
        return None
    if match:
        return montar_aprender_tema(match.group(1))
    return None


def nome_conta_fatura_padrao(valor: str):
    texto = (valor or "").strip()
    mapa = {
        "itau": "Itaú", "itaú": "Itaú",
        "mercado pago": "Mercado Pago",
        "nubank": "Nubank", "nu bank": "Nubank",
        "btg": "BTG", "inter": "Inter", "c6": "C6",
        "bradesco": "Bradesco", "santander": "Santander",
        "banco do brasil": "Banco do Brasil", "bb": "Banco do Brasil",
        "caixa": "Caixa", "picpay": "PicPay", "xp": "XP",
    }
    return mapa.get(normalizar_texto(texto), texto.title())


def calcular_resumo_fatura(ano_mes: str, conta_cartao: str):
    # Checklist, alertas e detalhamento de B1/B2/B3 representam somente a
    # fatura do cartão. Fixos e empréstimos permanecem em seus próprios grupos.
    resumo = calcular_fatura_unificada(ano_mes, conta_cartao, somente_cartao=True)
    resumo["conta_cartao"] = nome_conta_fatura_padrao(conta_cartao)
    return resumo


def formatar_resumo_fatura(ano_mes: str, conta_cartao: str):
    r = calcular_resumo_fatura(ano_mes, conta_cartao)
    linhas = [
        f"💳 Fatura {r['conta_cartao']} — {formatar_ano_mes_visual(ano_mes)}",
        "",
        bloco_total("Resumo da fatura", [
            linha_valor("Valor bruto", r["valor_bruto"]),
            linha_sinal_valor("Crédito herdado", -r.get("credito_herdado", 0)),
            linha_sinal_valor("Créditos/estornos", -r["creditos"]),
            linha_sinal_valor("Pagamentos", -r["pagamentos"]),
            linha_sinal_valor("Ajustes de débito", r["ajustes_debito"]),
            linha_sinal_valor("Conferência do total no banco", r.get("ajuste_conferencia", 0)),
            linha_status_valor("Saldo restante", r["saldo_restante"]),
        ]),
        "",
        f"Status: {r['status']}",
    ]
    if r["itens"]:
        linhas.extend(["", "Composição:"])
        for item in r["itens"][:20]:
            parcela = ""
            if item.get("parcela_atual") and item.get("parcelas_total"):
                parcela = f" · {item['parcela_atual']}/{item['parcelas_total']}"
            # R6: a lista mostra a data real da compra; item["data"] é a data
            # de referência da competência (usada só para agregação).
            linhas.append(
                f"- {formatar_data_visual(item.get('data_compra') or item['data'])} · {item['nome']} · "
                f"{formatar_moeda(float(item.get('valor') or 0))}{parcela}"
            )
    if r["movimentos"]:
        linhas.extend(["", "Movimentos:"])
        for mov in r["movimentos"][-20:]:
            sinal = "+" if mov["tipo_movimento"] == "ajuste_debito" else "-"
            origem = f" · origem {mov['conta_origem']}" if mov["conta_origem"] else ""
            linhas.append(
                f"#F{mov['id']} · {formatar_data_visual(mov['data_movimento'])} · "
                f"{mov['tipo_movimento'].replace('_', ' ')} · "
                f"{sinal}{formatar_moeda(float(mov['valor'] or 0))}{origem}"
            )
    return "\n".join(linhas)


def listar_movimentos_fatura_formatado(ano_mes: str, conta_cartao: str):
    movimentos = [
        mov for mov in listar_fatura_movimentos(ano_mes)
        if normalizar_conta_fatura(mov["conta_cartao"]) == normalizar_conta_fatura(conta_cartao)
    ]
    if not movimentos:
        return (
            f"💳 Movimentos da fatura {nome_conta_fatura_padrao(conta_cartao)} — "
            f"{formatar_ano_mes_visual(ano_mes)}\n\nNenhum movimento registrado."
        )
    linhas = [
        f"💳 Movimentos da fatura {nome_conta_fatura_padrao(conta_cartao)} — {formatar_ano_mes_visual(ano_mes)}",
        "",
    ]
    for mov in movimentos:
        sinal = "+" if mov["tipo_movimento"] == "ajuste_debito" else "-"
        origem = f" | origem: {mov['conta_origem']}" if mov["conta_origem"] else ""
        linhas.append(
            f"#F{mov['id']} | {formatar_data_visual(mov['data_movimento'])} | "
            f"{mov['tipo_movimento'].replace('_', ' ')} | "
            f"{sinal}{formatar_moeda(float(mov['valor'] or 0))}{origem}"
        )
    return "\n".join(linhas)


def registrar_movimento_fatura_formatado(
    tipo_movimento: str, valor: float, conta_cartao: str, ano_mes: str,
    conta_origem: str | None = None, mensagem_original: str | None = None,
    saldo_esperado: float | None = None,
):
    conta_cartao = nome_conta_fatura_padrao(conta_cartao)
    ano_mes_validado = validar_ano_mes(ano_mes)
    if not ano_mes_validado:
        return "Competência inválida. Use o formato AAAA-MM com um mês entre 01 e 12."
    ano_mes = ano_mes_validado
    if valor is None or valor <= 0:
        return "O valor precisa ser maior que zero."
    if tipo_movimento in {"pagamento_parcial", "pagamento_total"} and not conta_origem:
        return "Informe a conta pagadora. Exemplo: paguei 500 da fatura Itaú usando Mercado Pago 2026-07"

    with fatura_write_transaction() as conn:
        conn.row_factory = sqlite3.Row
        antes = calcular_resumo_fatura(ano_mes, conta_cartao)
        saldo_atual = float(antes["saldo_restante"] or 0)
        # Confirmação de prévia: o saldo revalidado dentro da transação precisa
        # ser o mesmo que a prévia mostrou; senão nada é gravado.
        if saldo_esperado is not None and abs(saldo_atual - float(saldo_esperado)) > 0.005:
            return MENSAGEM_PREVIA_MOVIMENTO_FATURA_MUDOU
        if tipo_movimento in {"pagamento_parcial", "pagamento_total"}:
            if saldo_atual <= 0.005:
                return f"A fatura não possui saldo pendente para pagamento. Status atual: {antes['status']}."
            valor = saldo_atual if tipo_movimento == "pagamento_total" else min(float(valor), saldo_atual)
        mov_id = inserir_fatura_movimento_conn(conn, {
            "ano_mes": ano_mes, "conta_cartao": conta_cartao,
            "tipo_movimento": tipo_movimento, "valor": valor,
            "data_movimento": relogio.hoje(date).isoformat(),
            "conta_origem": nome_conta_fatura_padrao(conta_origem) if conta_origem else None,
            "descricao": None, "mensagem_original": mensagem_original,
        })
        novo_movimento = conn.execute("SELECT * FROM fatura_movimentos WHERE id = ?", (mov_id,)).fetchone()
        registrar_auditoria(
            "fatura_movimento", mov_id, "criacao", None, dict(novo_movimento),
            "telegram", None, conn=conn,
        )
    depois = calcular_resumo_fatura(ano_mes, conta_cartao)
    linhas = [
        "✅ Movimento de fatura registrado", "", f"ID: #F{mov_id}",
        f"Fatura: {conta_cartao}", f"Mês: {formatar_ano_mes_visual(ano_mes)}",
        f"Tipo: {tipo_movimento.replace('_', ' ')}", f"Valor: {formatar_moeda(valor)}",
    ]
    if conta_origem:
        linhas.append(f"Conta pagadora: {nome_conta_fatura_padrao(conta_origem)}")
    linhas.extend(["", f"Saldo anterior: {formatar_moeda(antes['saldo_restante'])}",
                  f"Saldo restante: {formatar_moeda(depois['saldo_restante'])}",
                  f"Status: {depois['status']}", "",
                  "Atualizado em: quanto vou pagar, checklist, compromissos, meu mês e caixa."])
    return "\n".join(linhas)


# Prévia dos movimentos de fatura enviados por texto (pagamento, estorno,
# crédito): nada é gravado até a frase de confirmação própria do tipo, que não
# colide com "confirmar", "confirmar exclusao" ou "confirmar importacao".
_ROTULO_CONFIRMACAO_FATURA = {
    "pagamento_total": "pagamento", "pagamento_parcial": "pagamento",
    "estorno": "estorno", "credito": "credito",
}
_NOME_ROTULO_FATURA = {"pagamento": "pagamento", "estorno": "estorno", "credito": "crédito"}

MENSAGEM_PREVIA_MOVIMENTO_FATURA_MUDOU = (
    "⚠️ A fatura mudou desde a prévia (saldo, competência ou valor). Nada foi registrado.\n\n"
    "Envie o comando de novo para ver a prévia atualizada."
)


def previa_movimento_fatura_atual(tipo_movimento, valor, conta_cartao, ano_mes, conta_origem=None):
    """Prévia do movimento como seria gravado agora.

    Retorna (texto, saldo_antes); saldo_antes é None quando o texto é uma
    recusa (nada a confirmar). Não grava nada.
    """
    conta_cartao = nome_conta_fatura_padrao(conta_cartao)
    ano_mes_validado = validar_ano_mes(ano_mes)
    if not ano_mes_validado:
        return "Competência inválida. Use o formato AAAA-MM com um mês entre 01 e 12.", None
    ano_mes = ano_mes_validado
    if valor is None or valor <= 0:
        return "O valor precisa ser maior que zero.", None
    pagamento = tipo_movimento in {"pagamento_parcial", "pagamento_total"}
    if pagamento and not conta_origem:
        return "Informe a conta pagadora. Exemplo: paguei 500 da fatura Itaú usando Mercado Pago 2026-07", None
    antes = calcular_resumo_fatura(ano_mes, conta_cartao)
    saldo = float(antes["saldo_restante"] or 0)
    observacao = None
    if pagamento:
        if saldo <= 0.005:
            return f"A fatura não possui saldo pendente para pagamento. Status atual: {antes['status']}.", None
        if tipo_movimento == "pagamento_total":
            valor_final = saldo
        else:
            valor_final = min(float(valor), saldo)
            if float(valor) - saldo > 0.005:
                observacao = f"Valor informado {formatar_moeda(float(valor))} limitado ao saldo em aberto."
    else:
        valor_final = float(valor)
    depois = normalizar_valor_monetario(saldo - valor_final)
    rotulo = _ROTULO_CONFIRMACAO_FATURA[tipo_movimento]
    tipo_visual = {
        "pagamento_total": "pagamento do restante", "pagamento_parcial": "pagamento parcial",
        "estorno": "estorno", "credito": "crédito",
    }[tipo_movimento]
    linhas = [
        f"💳 Prévia — {_NOME_ROTULO_FATURA[rotulo]} de fatura", "",
        f"Fatura: {conta_cartao}",
        f"Competência: {formatar_ano_mes_visual(ano_mes)} ({ano_mes})",
        f"Tipo: {tipo_visual}",
        f"Valor: {formatar_moeda(valor_final)}",
    ]
    if observacao:
        linhas.append(observacao)
    if pagamento:
        linhas.append(f"Conta pagadora: {nome_conta_fatura_padrao(conta_origem)}")
    linhas.append(f"Saldo da fatura: {formatar_moeda(saldo)} → {formatar_moeda(depois)}")
    return "\n".join(linhas), saldo


def _preparar_movimento_fatura_sessao(tipo_movimento, valor, conta_cartao, ano_mes,
                                      conta_origem=None, mensagem_original=None, sessao=None):
    previa, saldo = previa_movimento_fatura_atual(tipo_movimento, valor, conta_cartao, ano_mes, conta_origem)
    if saldo is None:
        return previa
    rotulo = _ROTULO_CONFIRMACAO_FATURA[tipo_movimento]
    anterior = _obter_pendencia(PENDENCIAS_PAGAMENTO_FATURA, sessao)
    _definir_pendencia(PENDENCIAS_PAGAMENTO_FATURA, sessao, {
        "rotulo": rotulo, "previa": previa, "saldo": saldo,
        "args": (tipo_movimento, valor, conta_cartao, ano_mes, conta_origem),
        "mensagem_original": mensagem_original,
    })
    aviso_anterior = ("\nA prévia de fatura anterior, ainda não confirmada, foi descartada."
                      if anterior and anterior.get("previa") != previa else "")
    return (previa + "\n\n⚠️ Nada foi registrado ainda." + aviso_anterior + "\n"
            f"Responda: confirmar {rotulo}\nPara desistir: cancelar {rotulo}")


def confirmar_movimento_fatura_pendente(rotulo, sessao=None):
    nome = _NOME_ROTULO_FATURA[rotulo]
    pendencia = _obter_pendencia(PENDENCIAS_PAGAMENTO_FATURA, sessao)
    if not pendencia or pendencia.get("rotulo") != rotulo:
        return f"Não há {nome} de fatura pendente para confirmar."
    _limpar_pendencia(PENDENCIAS_PAGAMENTO_FATURA, sessao)
    tipo_movimento, valor, conta_cartao, ano_mes, conta_origem = pendencia["args"]
    # Grava exatamente o que a prévia mostrou: "restante" e o saldo são
    # recalculados agora, então qualquer mudança aborta.
    previa, saldo = previa_movimento_fatura_atual(tipo_movimento, valor, conta_cartao, ano_mes, conta_origem)
    if saldo is None or previa != pendencia["previa"]:
        return MENSAGEM_PREVIA_MOVIMENTO_FATURA_MUDOU
    return registrar_movimento_fatura_formatado(
        tipo_movimento, valor, conta_cartao, ano_mes,
        conta_origem=conta_origem,
        mensagem_original=pendencia.get("mensagem_original"),
        saldo_esperado=pendencia["saldo"],
    )


def cancelar_movimento_fatura_pendente(rotulo, sessao=None):
    nome = _NOME_ROTULO_FATURA[rotulo]
    pendencia = _obter_pendencia(PENDENCIAS_PAGAMENTO_FATURA, sessao)
    if not pendencia or pendencia.get("rotulo") != rotulo:
        return f"Não há {nome} de fatura pendente para cancelar."
    _limpar_pendencia(PENDENCIAS_PAGAMENTO_FATURA, sessao)
    return f"{nome.capitalize()} de fatura cancelado. Nada foi registrado."


def apagar_movimento_fatura_formatado(movimento_id: int, sessao=None):
    mov = apagar_fatura_movimento(movimento_id, usuario_sessao=_chave_sessao(sessao), origem="telegram")
    if not mov:
        return f"Não encontrei o movimento #F{movimento_id}."
    resumo = calcular_resumo_fatura(mov["ano_mes"], mov["conta_cartao"])
    return "\n".join([
        "🗑 Movimento de fatura apagado",
        "",
        f"ID: #F{movimento_id}",
        f"Fatura: {mov['conta_cartao']}",
        f"Valor: {formatar_moeda(float(mov['valor'] or 0))}",
        f"Saldo recalculado: {formatar_moeda(resumo['saldo_restante'])}",
        f"Status: {resumo['status']}",
    ])


def parsear_comando_movimento_fatura(texto_original: str):
    texto = normalizar_texto(texto_original)
    mes_padrao = relogio.hoje(date).strftime("%Y-%m")

    match_mes = re.search(r"\s+(20\d{2}-\d{2})$", texto)
    if match_mes:
        mes_final = validar_ano_mes(match_mes.group(1))
        if not mes_final:
            return ("erro", "Competência inválida. Use AAAA-MM com mês entre 01 e 12.")
        texto_sem_mes = texto[:match_mes.start()].strip()
    else:
        mes_final = mes_padrao
        texto_sem_mes = texto

    m = re.match(r"^fatura\s+(.+)$", texto_sem_mes)
    if m:
        return ("consultar", m.group(1).strip(), mes_final)

    m = re.match(r"^(?:movimentos|movimentações|movimentacoes)\s+da\s+fatura\s+(.+)$", texto_sem_mes)
    if m:
        return ("movimentos", m.group(1).strip(), mes_final)

    m = re.match(r"^(?:apagar|excluir|deletar|remover)\s+(?:movimento\s+)?#?f(\d+)$", texto_sem_mes)
    if m:
        return ("apagar", int(m.group(1)))

    m = re.match(
        r"^(estorno|credito|crédito|abatimento|reembolso)\s+(?:de\s+)?"
        r"([0-9\.,]+)\s+(?:na|da|em)\s+fatura\s+(.+)$",
        texto_sem_mes,
    )
    if m:
        tipo_raw = m.group(1)
        valor = converter_valor_texto(m.group(2))
        conta = m.group(3).strip()
        tipo = "estorno" if tipo_raw in {"estorno", "reembolso"} else "credito"
        return ("registrar", tipo, valor, conta, mes_final, None)

    m = re.match(
        r"^paguei\s+o\s+restante\s+da\s+fatura\s+(.+?)\s+usando\s+(.+)$",
        texto_sem_mes,
    )
    if m:
        conta = m.group(1).strip()
        origem = m.group(2).strip()
        return ("registrar", "pagamento_total", 1.0, conta, mes_final, origem)

    m = re.match(
        r"^paguei\s+([0-9\.,]+)\s+da\s+fatura\s+(.+?)\s+usando\s+(.+)$",
        texto_sem_mes,
    )
    if m:
        valor = converter_valor_texto(m.group(1))
        conta = m.group(2).strip()
        origem = m.group(3).strip()
        return ("registrar", "pagamento_parcial", valor, conta, mes_final, origem)

    return None


def previa_exclusao_atual(comando: str):
    """Texto da prévia de exclusão como seria mostrado agora (None se não houver)."""
    preview = preparar_previa_exclusao(comando)
    if preview is None:
        mov = parsear_comando_movimento_fatura(comando)
        if mov and mov[0] == "apagar":
            row = buscar_fatura_movimento_por_id(mov[1])
            if not row:
                return f"Não encontrei o movimento #F{mov[1]}."
            preview = "\n".join([
                "Você está prestes a apagar este movimento de fatura:", "",
                f"ID: #F{row['id']}", f"Fatura: {row['conta_cartao']}",
                f"Competência: {row['ano_mes']}", f"Tipo: {row['tipo_movimento']}",
                f"Valor: {formatar_moeda(float(row['valor'] or 0))}",
            ])
    return preview


MENSAGEM_PREVIA_EXCLUSAO_MUDOU = (
    "⚠️ Os lançamentos mudaram desde a prévia (por exemplo, um registro novo entrou "
    "na faixa ou virou o \"último\"). Nada foi apagado.\n\n"
    "Envie o comando de exclusão de novo para ver a prévia atualizada."
)


def _preparar_exclusao_sessao(comando: str, sessao=None):
    preview = previa_exclusao_atual(comando)
    if preview is None:
        return None
    if previa_exclusao_recusada(preview):
        # Recusa: não há o que confirmar.
        return preview
    _definir_pendencia(PENDENCIAS_EXCLUSAO, sessao, {"comando": comando, "previa": preview})
    return preview + "\n\n⚠️ Nada foi apagado ainda.\nResponda: confirmar exclusao\nPara desistir: cancelar exclusao"


# A confirmação de exclusão é um estado interno (ContextVar), nunca parte do texto
# digitado: quem escreve "__executar_exclusao__ ..." no chat é recusado.
from contextvars import ContextVar as _ContextVarExclusao
_EXCLUSAO_CONFIRMADA = _ContextVarExclusao("exclusao_confirmada", default=False)
_PREFIXO_INTERNO_EXCLUSAO = "__executar_exclusao__"


def executar_exclusao_confirmada(comando, sessao=None):
    """Executa uma exclusão já prévia-validada e confirmada pelo titular."""
    token = _EXCLUSAO_CONFIRMADA.set(True)
    try:
        return processar_mensagem(comando, sessao=sessao)
    finally:
        _EXCLUSAO_CONFIRMADA.reset(token)


def confirmar_exclusao_pendente(sessao=None):
    pendencia = _obter_pendencia(PENDENCIAS_EXCLUSAO, sessao)
    if not pendencia:
        return "Não há exclusão pendente para confirmar."
    _limpar_pendencia(PENDENCIAS_EXCLUSAO, sessao)
    # Apaga exatamente o que a prévia mostrou: "apagar último" e faixas de IDs
    # são recalculados na execução, então qualquer mudança aborta.
    if "previa" in pendencia and previa_exclusao_atual(pendencia["comando"]) != pendencia["previa"]:
        return MENSAGEM_PREVIA_EXCLUSAO_MUDOU
    if str(pendencia.get("previa") or "").startswith("Não encontrei"):
        return executar_exclusao_confirmada(pendencia["comando"], sessao=sessao)
    try:
        criar_backup_pre_exclusao()
    except Exception as exc:
        _LOG_CALCULOS.error("Backup antes da exclusão falhou; exclusão cancelada.", exc_info=True)
        return ("⚠️ Não consegui gerar o backup de segurança antes de apagar. Nada foi apagado.\n\n"
                f"Motivo: {exc}")
    return executar_exclusao_confirmada(pendencia["comando"], sessao=sessao)


def cancelar_exclusao_pendente(sessao=None):
    if not _obter_pendencia(PENDENCIAS_EXCLUSAO, sessao):
        return "Não há exclusão pendente para cancelar."
    _limpar_pendencia(PENDENCIAS_EXCLUSAO, sessao)
    return "Exclusão cancelada. Nada foi apagado."


# ------------------------------------------------------------
# Alterações por texto (legado): prévia "antes → depois" + confirmação
# ------------------------------------------------------------
# Regra do projeto: nada financeiro grava sem prévia e confirmação do titular.
# Os comandos de edição digitados (mudar/corrigir/meta/fixos/entradas) mostram a
# prévia e só gravam com "confirmar alteracao" (ou o botão vinculado à prévia).
# A execução confirmada é um estado interno (ContextVar), nunca parte do texto.
_ALTERACAO_CONFIRMADA = _ContextVarExclusao("alteracao_confirmada", default=False)

PREFIXO_ALTERACAO_BLOQUEADA = "⚠️ Alteração bloqueada"

MENSAGEM_PREVIA_ALTERACAO_MUDOU = (
    "⚠️ Os dados mudaram desde a prévia. Nada foi alterado.\n\n"
    "Envie o comando de novo para ver a prévia atualizada."
)

_RE_ALT_MUDAR_FAIXA = r"^mudar\s+(\d+)\s*-\s*(\d+)\s+para\s+(.+)$"
_RE_ALT_MUDAR_ID = r"^mudar\s+(\d+)\s+para\s+(.+)$"
_RE_ALT_MUDAR_ULTIMO = r"^mudar\s+(?:último|ultimo)\s+para\s+(.+)$"
_RE_ALT_CONTA = r"^(?:corrigir|alterar|mudar|trocar|editar|ajustar)\s+conta\s+(?:do\s+)?(?:lançamento|lancamento|transação|transacao)?\s*#?(\d+)\s+(?:para|por)\s+(.+)$"
_RE_ALT_FORMA = r"^(?:corrigir|alterar|mudar|trocar|editar|ajustar)\s+forma\s+(?:do\s+)?(?:lançamento|lancamento|transação|transacao)?\s*#?(\d+)\s+(?:para|por)\s+(.+)$"
_RE_ALT_VALOR = r"^corrigir valor\s+(\d+)\s+para\s+(.+)$"
_RE_ALT_VALOR_CURTO = r"^corrigir\s+(\d+)\s+para\s+(.+)$"
_RE_ALT_META = r"^meta\s+(.+)\s+(\d+(?:[.,]\d{1,2})?)$"
_RE_ALT_COMPROMISSO = r"^(?:alterar|mudar|trocar)\s+(conta|forma|categoria)\s+(?:do\s+)?(?:fixo|compromisso|parcela|parcelamento)\s+(\d+)\s+(?:para|por)\s+(.+)$"
_RE_ALT_PAUSAR_COMPROMISSO = r"^(pausar|desativar|reativar|ativar)\s+(?:fixo|compromisso)\s+(\d+)$"
_RE_ALT_PAUSAR_ENTRADA = r"^(pausar|desativar|reativar|ativar)\s+entrada\s+#?e?(\d+)$"
_RE_ALT_ENTRADA_VALOR = r"^alterar entrada\s+#?e?(\d+)\s+para\s+(.+)$"
_RE_ALT_SEM_TERMINO = r"alterar\s+t[eé]rmino\s+fixo\s+#?c?(\d+)\s+para\s+sem\s+t[eé]rmino"


def _linha_transacao_alteracao(t):
    return (f"#{t['id']} · {t['data']} · {t['descricao'] or 'Sem descrição'} · "
            f"{formatar_moeda(float(t['valor'] or 0))}")


def _previa_alteracao_texto(titulo, linhas):
    return "\n".join(["✏️ Confirme a alteração", "", titulo, *linhas])


def _bloqueio_parcela_isolada(transacao, campo):
    if row_get(transacao, "parcelamento_id") is None:
        return None
    return "\n".join([
        f"{PREFIXO_ALTERACAO_BLOQUEADA}: parcela de parcelamento",
        "",
        _linha_transacao_alteracao(transacao),
        "",
        f"A {campo} vale para o parcelamento inteiro: mudar só esta parcela deixaria o "
        f"parcelamento P{transacao['parcelamento_id']} com parcelas em {campo}s diferentes.",
        "Nada foi alterado.",
    ])


def _forma_canonica_texto(nova_forma):
    mapa = {"transferencia": "transferência", "transf": "transferência", "pix": "pix",
            "debito": "débito", "credito": "crédito", "cartao": "crédito", "dinheiro": "dinheiro",
            "cash": "dinheiro"}
    return mapa.get(normalizar_texto(nova_forma), nova_forma.lower())


def _previa_alteracao_fixo(texto):
    """Prévia das edições de fixo (fixos_edicao), com as mesmas travas do salvar."""
    from fixos_edicao import parse as parse_fixo, preparar as preparar_fixo, exibir, LABELS, CAMPOS
    sem_termino = re.fullmatch(_RE_ALT_SEM_TERMINO, texto.strip(), re.I)
    if sem_termino:
        ident = int(sem_termino.group(1))
        c = buscar_compromisso_por_id(ident)
        if not c or c["tipo"] != "fixo" or not c["data_fim"]:
            return None  # o executor responde com a mensagem própria, sem gravar
        return _previa_alteracao_texto(f"#C{ident} · {c['nome']}", [f"Término: {c['data_fim']} → sem término"])
    edicao = parse_fixo(texto)
    if not edicao:
        return None
    try:
        plano = preparar_fixo(*edicao)
    except ValueError:
        return None  # o executor devolve o erro de validação, sem gravar
    campo = plano["campo"]
    if not plano["mes"] and campo not in {"nome", "categoria", "vencimento", "conta"}:
        from conciliacao import bloquear_alteracao_compromisso
        with get_connection() as conn:
            bloquear_alteracao_compromisso(conn, plano["id"])
    antes = exibir(campo, plano["antes"][CAMPOS[campo]])
    depois = exibir(campo, plano["depois"][CAMPOS[campo]])
    linhas = [f"{LABELS[campo]}: {antes} → {depois}"]
    if plano["mes"]:
        linhas.append(f"Nova condição a partir de {plano['mes']} (meses anteriores preservados).")
    return _previa_alteracao_texto(f"#C{plano['id']} · {plano['antes']['nome']}", linhas)


def previa_alteracao(comando: str):
    """Prévia (antes → depois) de um comando de texto que altera dados.

    Devolve None quando o texto não é uma alteração coberta (segue o roteador).
    Uma prévia que começa com PREFIXO_ALTERACAO_BLOQUEADA é recusa: não há o
    que confirmar. É recalculada na confirmação: se mudou, nada é gravado.
    """
    previa_fixo = _previa_alteracao_fixo(comando or "")
    if previa_fixo is not None:
        return previa_fixo

    texto = normalizar_comando_sinonimos((comando or "").lower().strip())
    if not texto:
        return None

    m = re.match(_RE_ALT_MUDAR_FAIXA, texto)
    if m:
        inicio, fim = sorted((int(m.group(1)), int(m.group(2))))
        nova = m.group(3).strip().title()
        transacoes = [t for t in buscar_todas_transacoes() if inicio <= int(t["id"]) <= fim]
        if not transacoes:
            return None
        linhas = [f"{_linha_transacao_alteracao(t)}\n   Categoria: {t['categoria'] or 'Sem categoria'} → {nova}"
                  for t in transacoes[:15]]
        if len(transacoes) > 15:
            linhas.append(f"… e mais {len(transacoes) - 15} lançamento(s).")
        return _previa_alteracao_texto(f"{len(transacoes)} lançamento(s) entre #{inicio} e #{fim}:", linhas)

    m = re.match(_RE_ALT_MUDAR_ID, texto)
    if m:
        t = buscar_transacao_por_id(int(m.group(1)))
        if not t:
            return None
        return _previa_alteracao_texto(_linha_transacao_alteracao(t),
                                       [f"Categoria: {t['categoria'] or 'Sem categoria'} → {m.group(2).strip().title()}"])

    m = re.match(_RE_ALT_MUDAR_ULTIMO, texto)
    if m:
        ultimas = buscar_ultimas_transacoes(1)
        if not ultimas:
            return None
        t = ultimas[0]
        return _previa_alteracao_texto("Último lançamento: " + _linha_transacao_alteracao(t),
                                       [f"Categoria: {t['categoria'] or 'Sem categoria'} → {m.group(1).strip().title()}"])

    for padrao, campo in ((_RE_ALT_CONTA, "conta"), (_RE_ALT_FORMA, "forma")):
        m = re.match(padrao, texto)
        if m:
            t = buscar_transacao_por_id(int(m.group(1)))
            novo = m.group(2).strip()
            if not t or not novo:
                return None
            bloqueio = _bloqueio_parcela_isolada(t, campo)
            if bloqueio:
                return bloqueio
            if campo == "conta":
                linha = f"Conta: {t['conta'] or 'Não informada'} → {novo.title()}"
            else:
                linha = f"Forma: {t['forma_pagamento'] or 'não informada'} → {_forma_canonica_texto(novo)}"
            return _previa_alteracao_texto(_linha_transacao_alteracao(t), [linha])

    for padrao in (_RE_ALT_VALOR, _RE_ALT_VALOR_CURTO):
        m = re.match(padrao, texto)
        if m:
            t = buscar_transacao_por_id(int(m.group(1)))
            novo = converter_valor_texto(m.group(2))
            if not t or novo is None:
                return None
            linhas = [f"Valor: {formatar_moeda(float(t['valor'] or 0))} → {formatar_moeda(novo)}"]
            if row_get(t, "parcelamento_id") is not None:
                linhas.append(f"O total do parcelamento P{t['parcelamento_id']} será recalculado.")
            return _previa_alteracao_texto(_linha_transacao_alteracao(t), linhas)

    m = re.match(_RE_ALT_META, texto)
    if m:
        categoria = m.group(1).strip().title()
        valor = converter_valor_texto(m.group(2))
        if valor is None or valor <= 0:
            return None
        atual = buscar_meta_por_categoria(categoria)
        antes = formatar_moeda(float(atual["valor"])) if atual else "sem meta"
        return _previa_alteracao_texto(f"Meta mensal · {categoria}", [f"Limite: {antes} → {formatar_moeda(valor)}"])

    m = re.match(_RE_ALT_COMPROMISSO, texto)
    if m:
        campo, ident, novo = m.group(1), int(m.group(2)), m.group(3).strip()
        c = buscar_compromisso_por_id(ident)
        if not c:
            return None
        coluna = {"conta": "conta_pagamento", "forma": "forma_pagamento", "categoria": "categoria"}[campo]
        return _previa_alteracao_texto(f"#C{ident} · {c['nome']}",
                                       [f"{campo.title()}: {c[coluna] or 'não informada'} → {novo}"])

    m = re.match(_RE_ALT_PAUSAR_COMPROMISSO, texto) or re.match(_RE_ALT_PAUSAR_ENTRADA, texto)
    if m:
        ident = int(m.group(2))
        c = buscar_compromisso_por_id(ident)
        if not c:
            return None
        pausar = m.group(1) in {"pausar", "desativar"}
        antes = "ativo" if c["ativo"] else "pausado"
        depois = "pausado" if pausar else "ativo"
        prefixo = "#E" if c["tipo"] in ("entrada_fixa", "entrada_avulsa") else "#C"
        return _previa_alteracao_texto(f"{prefixo}{ident} · {c['nome']}", [f"Situação: {antes} → {depois}"])

    m = re.match(_RE_ALT_ENTRADA_VALOR, texto)
    if m:
        c = buscar_compromisso_por_id(int(m.group(1)))
        valor = converter_valor_texto(m.group(2))
        if not c or valor is None or valor <= 0:
            return None
        return _previa_alteracao_texto(f"#E{c['id']} · {c['nome']}",
                                       [f"Valor: {formatar_moeda(float(c['valor'] or 0))} → {formatar_moeda(valor)}"])

    # Cadastros por texto: nada antes, só o que será criado.
    for parser, rotulo in ((parsear_comando_entrada_fixa, "Nova entrada fixa"),
                           (parsear_comando_entrada_avulsa, "Nova entrada prevista"),
                           (parsear_comando_novo_fixo, "Novo fixo")):
        dados = parser(texto)
        if dados:
            if dados.get("erro") or dados.get("valor") is None or dados["valor"] <= 0:
                return None  # o executor explica o formato, sem gravar
            linhas = [f"Nome: {dados.get('nome')}", f"Valor: {formatar_moeda(dados['valor'])}"]
            if dados.get("dia"):
                linhas.append(f"Dia: {dados['dia']}")
            if dados.get("data"):
                linhas.append(f"Data prevista: {dados['data']}")
            linhas.append(f"Conta: {dados.get('conta') or 'não informada'}")
            return _previa_alteracao_texto(f"{rotulo} (cadastro novo):", linhas)

    return None


# Recalcular a prévia na confirmação roda o próprio roteador em "modo prévia":
# o primeiro ramo que pediria confirmação devolve a prévia (exceção interna) em
# vez de criar pendência. Assim todo ramo de gravação do roteador que passa por
# _gravacao_pede_confirmacao é recalculado do mesmo jeito, sem lista paralela.
_COLETANDO_PREVIA = _ContextVarExclusao("coletando_previa", default=False)
_SESSAO_PREVIA = "__recalculo_previa__"


class _PreviaColetada(Exception):
    def __init__(self, previa):
        super().__init__("prévia coletada")
        self.previa = previa


def _preparar_alteracao_sessao(comando: str, previa: str, sessao=None):
    if _COLETANDO_PREVIA.get():
        raise _PreviaColetada(previa)
    if str(previa).startswith(PREFIXO_ALTERACAO_BLOQUEADA):
        return previa
    _definir_pendencia(PENDENCIAS_ALTERACAO, sessao, {"comando": comando, "previa": previa})
    return previa + "\n\nNada foi alterado ainda.\nResponda: confirmar alteracao\nPara desistir: cancelar alteracao"


def executar_alteracao_confirmada(comando, sessao=None):
    token = _ALTERACAO_CONFIRMADA.set(True)
    try:
        return processar_mensagem(comando, sessao=sessao)
    finally:
        _ALTERACAO_CONFIRMADA.reset(token)


def confirmar_alteracao_pendente(sessao=None):
    pendencia = _obter_pendencia(PENDENCIAS_ALTERACAO, sessao)
    if not pendencia:
        return "Não há alteração pendente para confirmar. Nada foi alterado."
    # Consome antes de executar: confirmar duas vezes não grava duas vezes.
    _limpar_pendencia(PENDENCIAS_ALTERACAO, sessao)
    atual = recalcular_previa_gravacao(pendencia["comando"])
    if atual != pendencia["previa"]:
        return MENSAGEM_PREVIA_ALTERACAO_MUDOU
    return executar_alteracao_confirmada(pendencia["comando"], sessao=sessao)


def recalcular_previa_gravacao(comando: str):
    """Prévia que o roteador mostraria hoje para `comando` (None se não grava)."""
    token = _COLETANDO_PREVIA.set(True)
    try:
        _processar_mensagem_core(comando, sessao=_SESSAO_PREVIA)
    except _PreviaColetada as coletada:
        return coletada.previa
    except Exception:
        logging.getLogger(__name__).warning("Falha ao recalcular a prévia.", exc_info=True)
        return None
    finally:
        _COLETANDO_PREVIA.reset(token)
    return None


def _gravacao_pede_confirmacao(comando: str, previa: str, sessao=None):
    """Ponto único dos ramos do roteador que gravam.

    Sem confirmação: guarda a pendência e devolve a prévia (nada grava).
    Confirmado (``confirmar alteracao`` ou botão vinculado): devolve None e o
    ramo segue gravando.
    """
    if _ALTERACAO_CONFIRMADA.get():
        return None
    return _preparar_alteracao_sessao(comando, previa, sessao)


def _auditar_roteador(entidade, entidade_id, operacao, sessao, antes=None, depois=None):
    try:
        registrar_auditoria(entidade, entidade_id, operacao, dados_antes=antes, dados_depois=depois,
                            origem="telegram", usuario_sessao=_chave_sessao(sessao))
    except Exception:
        # A gravação já ocorreu; a falha de auditoria fica no log, sem esconder o resultado.
        logging.getLogger(__name__).exception("Falha ao auditar %s %s.", entidade, operacao)


def _previa_texto_simples(titulo, linhas):
    return "\n".join([titulo, "", *linhas])


def _previa_editar_fatura(movimento_id: int, campo: str, valor_texto: str):
    """(tipo, texto): 'recusa' (responde sem gravar) ou 'previa'."""
    atual = buscar_fatura_movimento_por_id(movimento_id)
    if not atual:
        return "recusa", f"Não encontrei o movimento #F{movimento_id}."
    mapa = {"competencia": "ano_mes", "competência": "ano_mes", "valor": "valor", "data": "data_movimento",
            "origem": "conta_origem", "conta": "conta_origem"}
    campo_db = mapa.get(campo.lower())
    if not campo_db:
        return "recusa", "Campo inválido. Use valor, competência, data ou conta."
    try:
        if campo_db == "valor":
            novo = converter_valor_texto(str(valor_texto))
            if novo is None or novo <= 0:
                return "recusa", "Valor inválido. Nada foi alterado."
            antes_txt, depois_txt = formatar_moeda(float(atual["valor"] or 0)), formatar_moeda(novo)
        elif campo_db == "ano_mes":
            novo = validar_ano_mes(str(valor_texto))
            if not novo:
                return "recusa", "Competência inválida. Use AAAA-MM."
            antes_txt, depois_txt = atual["ano_mes"], novo
        elif campo_db == "data_movimento":
            novo = date.fromisoformat(str(valor_texto)).isoformat()
            antes_txt, depois_txt = formatar_data_visual(atual["data_movimento"]), formatar_data_visual(novo)
        else:
            novo = nome_conta_fatura_padrao(str(valor_texto))
            antes_txt, depois_txt = atual["conta_origem"] or "não informada", novo
    except (ValueError, TypeError) as exc:
        return "recusa", f"Não foi possível alterar o movimento: {exc}"
    return "previa", _previa_alteracao_texto(
        f"#F{movimento_id} · {atual['tipo_movimento']} · fatura {atual['conta_cartao']} {atual['ano_mes']}",
        [f"{campo.title()}: {antes_txt} → {depois_txt}"])


_RE_VENCIMENTO_FATURA_NOME = (
    r"^(?:vencimento|data de vencimento|data pagamento|data de pagamento)\s+"
    r"(?:da\s+)?(?:fatura|cartao|cartão)\s+(.+?)\s+"
    r"(?:(\d{4}-\d{2})\s+)?(?:para\s+)?(?:dia\s+)?(\d{1,2})$"
)
_RES_DATA_PAGAMENTO_CHECKLIST = (
    r"^(?:data pagamento|data de pagamento|vencimento|alterar vencimento|mudar vencimento|pagar em)\s+([a-zA-Z]?\d+|B_[a-z0-9_]+|b_[a-z0-9_]+|[cCpPtT]\d+)\s+(\d{4}-\d{2})\s+(?:para|em|dia)\s+(.+)$",
    r"^(?:data pagamento|data de pagamento|vencimento|alterar vencimento|mudar vencimento|pagar em)\s+([a-zA-Z]?\d+|B_[a-z0-9_]+|b_[a-z0-9_]+|[cCpPtT]\d+)\s+(?:para|em|dia)\s+(.+?)(?:\s+(\d{4}-\d{2}))?$",
)


def _previa_vencimento_fatura(texto_limpo: str):
    """Mesmo padrão de definir_vencimento_fatura_por_nome_formatado. None = não é este comando."""
    padrao = re.match(_RE_VENCIMENTO_FATURA_NOME, normalizar_texto(texto_limpo))
    if not padrao:
        return None
    nome_cartao = padrao.group(1).strip()
    ano_mes_explicito = validar_ano_mes(padrao.group(2)) if padrao.group(2) else None
    ano_mes = ano_mes_explicito or relogio.hoje(date).strftime("%Y-%m")
    dia = int(padrao.group(3))
    if dia < 1 or dia > 31:
        return "recusa", None
    if ano_mes_explicito:
        _chave, item = resolver_fatura_checklist_por_nome(ano_mes, nome_cartao)
    else:
        _chave, item = resolver_fatura_recorrente_por_nome(ano_mes, nome_cartao)
    if not item:
        return "recusa", None
    atual = formatar_data_visual(item["data"]) if item.get("data") else "não definido"
    if ano_mes_explicito:
        nova = formatar_data_visual(data_por_dia_no_mes(ano_mes, dia))
        linhas = [f"Vencimento de {formatar_ano_mes_visual(ano_mes)}: {atual} → {nova}",
                  "Vale somente para esta fatura."]
    else:
        linhas = [f"Vencimento: {atual} → todo mês dia {dia:02d}",
                  "Vale para esta e para as próximas faturas."]
    return "previa", _previa_alteracao_texto(f"📅 Fatura {item.get('nome')}", linhas)


def _previa_data_pagamento_checklist(texto_limpo: str):
    """Mesmos padrões de definir_data_pagamento_checklist_formatado. None = não é este comando."""
    texto = normalizar_texto(texto_limpo)
    for indice, padrao in enumerate(_RES_DATA_PAGAMENTO_CHECKLIST):
        match = re.match(padrao, texto)
        if not match:
            continue
        if indice == 0:
            ano_mes, data_txt, escopo = validar_ano_mes(match.group(2)), match.group(3), "mes"
        else:
            explicito = validar_ano_mes(match.group(3)) if match.group(3) else None
            ano_mes = explicito or relogio.hoje(date).strftime("%Y-%m")
            data_txt, escopo = match.group(2), ("mes" if explicito else "padrao")
        if not ano_mes:
            return "recusa", None
        data_pagamento = parsear_data_pagamento_usuario(data_txt, ano_mes)
        if not data_pagamento:
            return "recusa", None
        _chave, item = resolver_item_checklist(ano_mes, match.group(1))
        if not item:
            return "recusa", None
        codigo = item.get("codigo") or match.group(1)
        atual = formatar_data_visual(item["data"]) if item.get("data") else "não definida"
        if escopo == "padrao":
            linhas = [f"Vencimento: {atual} → todo mês dia {int(data_pagamento[-2:]):02d}",
                      "Vale para os próximos meses enquanto o item existir."]
        else:
            linhas = [f"Data de pagamento em {formatar_ano_mes_visual(ano_mes)}: {atual} → "
                      f"{formatar_data_visual(data_pagamento)}", "Vale só para este mês."]
        return "previa", _previa_alteracao_texto(f"📅 {codigo} · {item.get('nome')}", linhas)
    return None


def _previa_transferencia_caixa(transferencia: dict):
    return _previa_texto_simples("🔁 Confirme a transferência entre contas", [
        f"Data: {formatar_data_visual(transferencia['data'])}",
        f"Valor: {formatar_moeda(transferencia['valor'])}",
        f"De: {transferencia['conta_origem']} → Para: {transferencia['conta_destino']}",
        "Mexe só no saldo das duas contas; não é receita nem despesa.",
    ])


def _previa_saldo_inicial(ano_mes: str, valor, conta):
    """(tipo, texto). 'recusa' = a própria função responde sem gravar."""
    conta_limpa = (conta or "").strip()
    if not conta_limpa and buscar_saldos_contas_mes(ano_mes):
        return "recusa", None
    if valor is None and not (conta_limpa and _mes_herda_saldo_por_conta(ano_mes)):
        return "recusa", None
    if conta_limpa and not _mes_herda_saldo_por_conta(ano_mes) and _mes_tem_base_inicial_de_outra_origem(ano_mes):
        return "recusa", None
    mes = formatar_ano_mes_visual(ano_mes)
    if valor is None:
        return "previa", _previa_alteracao_texto(f"🏦 Saldo inicial · {conta_limpa} · {mes}", [
            "Saldo definido por você → volta a herdar o valor calculado do mês anterior.",
            "Nada muda nos meses anteriores."])
    if not conta_limpa:
        return "previa", _previa_alteracao_texto(f"🏦 Saldo inicial geral · {mes}", [
            f"Novo saldo inicial: {formatar_moeda(valor)}",
            "O mês passa a usar um saldo inicial geral, sem divisão por conta."])
    alvo = normalizar_texto(formatar_nome_conta_saldo(conta_limpa))
    antes = next((r for r in buscar_saldos_contas_mes(ano_mes)
                  if normalizar_texto(row_get(r, "conta") or "") == alvo), None)
    antes_txt = formatar_moeda(float(row_get(antes, "saldo_inicial") or 0)) if antes else "herdado/não definido"
    linhas = [f"Saldo inicial: {antes_txt} → {formatar_moeda(valor)}"]
    if _mes_herda_saldo_por_conta(ano_mes):
        linhas.append("Os meses seguintes herdam este valor; os anteriores não mudam.")
    return "previa", _previa_alteracao_texto(f"🏦 {formatar_nome_conta_saldo(conta_limpa)} · {mes}", linhas)


def _previa_lancamento(transacao: dict):
    receita = transacao.get("tipo") == "receita"
    linhas = [
        f"{'Entrada' if receita else 'Despesa'}: {formatar_moeda(transacao['valor'])}",
        f"Descrição: {transacao.get('descricao') or 'Sem descrição'}",
        f"Categoria: {transacao.get('categoria') or 'Outros'}",
        f"Data: {formatar_data_visual(transacao['data'])}",
        f"Forma: {transacao.get('forma_pagamento') or 'não informada'} · Conta: {transacao.get('conta') or 'não informada'}",
    ]
    parcelas = int(transacao.get("parcelas_total") or 1)
    if parcelas > 1:
        linhas.append(f"Parcelado em {parcelas}x (cerca de {formatar_moeda(round(transacao['valor'] / parcelas, 2))} por mês).")
    return _previa_texto_simples("✍️ Confirme o lançamento", linhas)


def _sufixo_desfazer_checklist(resposta, ano_mes, chaves, status):
    if not str(resposta).startswith(("✅ Checklist atualizado", "☐ Checklist atualizado")):
        return resposta
    verbo = "desmarcar" if status == "pago" else "paguei"
    codigos = " ".join(str(c).upper() for c in chaves)
    return f"{resposta}\n\nPara desfazer: {verbo} {codigos} {ano_mes}"


def cancelar_alteracao_pendente(sessao=None):
    if not _obter_pendencia(PENDENCIAS_ALTERACAO, sessao):
        return "Não há alteração pendente para cancelar."
    _limpar_pendencia(PENDENCIAS_ALTERACAO, sessao)
    return "Alteração cancelada. Nada foi alterado."


def editar_movimento_fatura_formatado(movimento_id: int, campo: str, valor, sessao=None):
    atual = buscar_fatura_movimento_por_id(movimento_id)
    if not atual:
        return f"Não encontrei o movimento #F{movimento_id}."
    mapa = {"competencia": "ano_mes", "competência": "ano_mes", "valor": "valor", "data": "data_movimento", "origem": "conta_origem", "conta": "conta_origem"}
    campo_db = mapa.get(campo.lower())
    if not campo_db:
        return "Campo inválido. Use valor, competência, data ou conta."
    try:
        if campo_db == "valor":
            valor = converter_valor_texto(str(valor))
        elif campo_db == "ano_mes":
            valor = validar_ano_mes(str(valor))
            if not valor:
                return "Competência inválida. Use AAAA-MM."
        elif campo_db == "data_movimento":
            valor = date.fromisoformat(str(valor)).isoformat()
        else:
            valor = nome_conta_fatura_padrao(str(valor))
        depois = atualizar_fatura_movimento(movimento_id, usuario_sessao=_chave_sessao(sessao), origem="telegram", **{campo_db: valor})
    except (ValueError, TypeError) as exc:
        return f"Não foi possível alterar o movimento: {exc}"
    return "\n".join(["✅ Movimento de fatura atualizado", "", f"ID: #F{movimento_id}", f"Campo: {campo}", f"Novo valor: {valor}", "A alteração foi registrada na trilha de auditoria."])


def remover_termino_fixo(compromisso_id, sessao=None):
    """Remove somente o término de um fixo, com bloqueio e auditoria atômica."""
    from conciliacao import bloquear_alteracao_compromisso
    with get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.row_factory=sqlite3.Row
        antes=conn.execute('SELECT * FROM compromissos WHERE id=?',(compromisso_id,)).fetchone()
        if antes is None:
            return f'Não encontrei o fixo #C{compromisso_id}.'
        if antes['tipo'] != 'fixo':
            return f'O compromisso #C{compromisso_id} não é um fixo. Nada foi alterado.'
        if not antes['data_fim']:
            return f"#C{compromisso_id} · {antes['nome']} já está sem término. Nada foi alterado."
        bloquear_alteracao_compromisso(conn,compromisso_id)
        from fixos_vigencia import garantir_sem_sobreposicao
        garantir_sem_sobreposicao(conn,compromisso_id,dict(antes,data_fim=None))
        conn.execute('UPDATE compromissos SET data_fim=NULL, atualizado_em=? WHERE id=?',
                     (relogio.agora().isoformat(timespec='seconds'),compromisso_id))
        depois=conn.execute('SELECT * FROM compromissos WHERE id=?',(compromisso_id,)).fetchone()
        registrar_auditoria('compromissos',compromisso_id,'remover_termino',
                            dados_antes=dict(antes),dados_depois=dict(depois),
                            origem='telegram',usuario_sessao=_chave_sessao(sessao),conn=conn)
    return '\n'.join(['✅ Vigência do fixo atualizada',
        f"#C{compromisso_id} · {depois['nome']}",
        f"Término anterior: {antes['data_fim']}", 'Novo término: sem término',
        'Valor, início, vencimento, categoria e status preservados.',
        'Os resumos passam a considerar os meses posteriores ao término antigo, se o fixo estiver ativo.'])


def diagnosticar_fixo(compromisso_id, mes):
    from compromissos import compromisso_ocorre_no_mes
    c=buscar_compromisso_por_id(compromisso_id)
    if c is None:
        return f'Não encontrei o compromisso #C{compromisso_id}.'
    previsto=compromisso_ocorre_no_mes(c, mes)
    itens=projetar_pagamentos_mes(mes, incluir_transacoes=True)
    presentes=[i for i in itens if i.get('origem')=='compromisso' and i.get('id')==compromisso_id]
    if not c['ativo']:
        motivo='Pausado: não entra na previsão.'
    elif not previsto:
        motivo='Fora da vigência: confira início e término abaixo.'
    elif presentes:
        motivo='Incluído na previsão mensal.'
    else:
        motivo='Ausente da previsão apesar da vigência. Requer revisão do cálculo.'
    return '\n'.join([
        f"🔎 Diagnóstico #C{compromisso_id} · {c['nome']}",
        f"Mês: {mes}", f"Categoria cadastrada: {c['categoria']}",
        f"Tipo: {c['tipo']} | Ativo: {'sim' if c['ativo'] else 'não'}",
        f"Início: {c['data_inicio']} | Término: {c['data_fim'] or 'sem término'}",
        f"Vencimento: dia {c['dia_vencimento']}", motivo,
        *[f"Categoria no mês: {obter_categoria_item(i)} | Valor: {formatar_moeda(i['valor'])}" for i in presentes],
        'Consulta somente; nenhum dado foi alterado.'
    ])


def _processar_mensagem_core(texto: str, sessao=None):
    texto_alteracao = re.sub(r"\s+", " ", (texto or "").lower().strip())
    if texto_alteracao in {"confirmar alteracao", "confirmar alteração"}:
        return confirmar_alteracao_pendente(sessao)
    if texto_alteracao in {"cancelar alteracao", "cancelar alteração"}:
        return cancelar_alteracao_pendente(sessao)
    # Edições digitadas não gravam direto: prévia antes → depois + confirmação.
    if not _ALTERACAO_CONFIRMADA.get() and not texto_alteracao.startswith("__"):
        previa_alt = previa_alteracao(texto)
        if previa_alt is not None:
            return _preparar_alteracao_sessao(texto, previa_alt, sessao)

    from fixos_edicao import parse as parse_fixo, preparar as preparar_fixo, salvar as salvar_fixo
    edicao_fixo=parse_fixo(texto)
    # Mantém a compatibilidade do complemento de remoção de término.
    if edicao_fixo and not (edicao_fixo[1] in {'termino','fim'} and edicao_fixo[2].strip().lower() in {'sem termino','sem término'} and not edicao_fixo[3]):
        try:
            return salvar_fixo(preparar_fixo(*edicao_fixo),sessao)
        except ValueError as exc:
            return str(exc)

    sem_termino=re.fullmatch(r'alterar\s+t[eé]rmino\s+fixo\s+#?c?(\d+)\s+para\s+sem\s+t[eé]rmino', texto.strip(), re.I)
    if sem_termino:
        return remover_termino_fixo(int(sem_termino.group(1)),sessao)

    diagnostic=re.fullmatch(r'diagn[oó]stico\s+(?:fixo|compromisso)\s+#?[cC]?(\d+)(?:\s+(\d{4}-\d{2}))?', texto.strip(), re.I)
    if diagnostic:
        mes=diagnostic.group(2) or relogio.hoje(date).strftime('%Y-%m')
        if not validar_ano_mes(mes):return 'Mês inválido. Use AAAA-MM.'
        return diagnosticar_fixo(int(diagnostic.group(1)),mes)

    # Um mês explícito inválido nunca deve cair silenciosamente no mês atual.
    for competencia in re.findall(r'(?<!\d)\d{4}-\d{2}(?!\d)', texto or ''):
        if not validar_ano_mes(competencia):
            return 'Mês inválido; competência inválida. Use AAAA-MM com um mês de 01 a 12.'
    texto_limpo = texto.lower().strip()
    exclusao_confirmada = _EXCLUSAO_CONFIRMADA.get()
    if texto_limpo.startswith(_PREFIXO_INTERNO_EXCLUSAO):
        return "Comando interno não permitido. Para apagar, use apagar ... e confirme a prévia."

    if texto_limpo in {"confirmar exclusao", "confirmar exclusão"}:
        return confirmar_exclusao_pendente(sessao)
    if texto_limpo in {"cancelar exclusao", "cancelar exclusão"}:
        return cancelar_exclusao_pendente(sessao)

    m_conf_fatura = re.fullmatch(r"(confirmar|cancelar)\s+(pagamento|estorno|credito|crédito)", texto_limpo)
    if m_conf_fatura:
        rotulo_fatura = "credito" if m_conf_fatura.group(2) == "crédito" else m_conf_fatura.group(2)
        if m_conf_fatura.group(1) == "confirmar":
            return confirmar_movimento_fatura_pendente(rotulo_fatura, sessao)
        return cancelar_movimento_fatura_pendente(rotulo_fatura, sessao)

    m_editar_fatura = re.match(r"^(?:corrigir|editar|alterar)\s+#?f(\d+)\s+(valor|competencia|competência|data|conta|origem)\s+(?:para\s+)?(.+)$", texto_limpo)
    if m_editar_fatura:
        tipo_prev, texto_prev = _previa_editar_fatura(int(m_editar_fatura.group(1)), m_editar_fatura.group(2), m_editar_fatura.group(3))
        if tipo_prev == "recusa":
            return texto_prev
        pedido = _gravacao_pede_confirmacao(texto, texto_prev, sessao)
        if pedido is not None:
            return pedido
        return editar_movimento_fatura_formatado(int(m_editar_fatura.group(1)), m_editar_fatura.group(2), m_editar_fatura.group(3), sessao)

    movimento_fatura_cmd = parsear_comando_movimento_fatura(texto)
    if movimento_fatura_cmd:
        acao = movimento_fatura_cmd[0]
        if acao == "erro":
            return movimento_fatura_cmd[1]
        if acao == "consultar":
            return formatar_resumo_fatura(movimento_fatura_cmd[2], movimento_fatura_cmd[1])
        if acao == "movimentos":
            return listar_movimentos_fatura_formatado(movimento_fatura_cmd[2], movimento_fatura_cmd[1])
        if acao == "apagar":
            if not exclusao_confirmada:
                return _preparar_exclusao_sessao(texto, sessao)
            return apagar_movimento_fatura_formatado(movimento_fatura_cmd[1], sessao=sessao)
        if acao == "registrar":
            _, tipo_mov, valor_mov, conta_mov, mes_mov, origem_mov = movimento_fatura_cmd
            # Texto livre mostra prévia; grava só com "confirmar pagamento/estorno/credito".
            return _preparar_movimento_fatura_sessao(
                tipo_mov, valor_mov, conta_mov, mes_mov,
                conta_origem=origem_mov,
                mensagem_original=texto,
                sessao=sessao,
            )
    texto_limpo = normalizar_comando_sinonimos(texto_limpo)

    match_auditoria_mes = re.match(
        r"^(?:auditar|auditoria|explicar|detalhar)(?:\s+(?:o|do|meu))?\s+(?:mes|mês|resultado|resultado operacional)(?:\s+(\d{4}-\d{2}))?$",
        texto_limpo,
    )
    if match_auditoria_mes:
        ano_mes = match_auditoria_mes.group(1) or relogio.hoje(date).strftime("%Y-%m")
        return gerar_auditoria_resultado_mes_ux(ano_mes)

    match_porque_resultado = re.match(
        r"^por que (?:meu|o) resultado(?: operacional)?(?: esta| está)?(?: errado| estranho)?(?:\s+(\d{4}-\d{2}))?$",
        texto_limpo,
    )
    if match_porque_resultado:
        ano_mes = match_porque_resultado.group(1) or relogio.hoje(date).strftime("%Y-%m")
        return gerar_auditoria_resultado_mes_ux(ano_mes)

    if comando_destrutivo_exclusao(texto_limpo) and not exclusao_confirmada:
        return _preparar_exclusao_sessao(texto_limpo, sessao) or mensagem_exclusao_bloqueada_por_confirmacao(texto_limpo)

    aprender_cmd = parsear_comando_aprender(texto_limpo)
    if aprender_cmd:
        return aprender_cmd


    # Vencimento de fatura e data de pagamento do checklist: prévia + confirmação.
    # As funções de gravação só rodam confirmadas ou para responder a uma recusa
    # (dia/item inválido), caminhos em que elas não gravam.
    for previa_data, gravar_data, rotulo_auditoria in (
        (_previa_vencimento_fatura, definir_vencimento_fatura_por_nome_formatado, "vencimento_fatura"),
        (_previa_data_pagamento_checklist, definir_data_pagamento_checklist_formatado, "data_pagamento"),
    ):
        avaliado = previa_data(texto_limpo)
        if avaliado is None:
            continue
        tipo_prev, texto_prev = avaliado
        if tipo_prev == "previa":
            pedido = _gravacao_pede_confirmacao(texto, texto_prev, sessao)
            if pedido is not None:
                return pedido
        resposta_data = gravar_data(texto_limpo)
        if tipo_prev == "previa":
            _auditar_roteador("checklist_pagamentos", texto_limpo[:80], rotulo_auditoria, sessao,
                              depois={"comando": texto_limpo, "previa": texto_prev})
        if resposta_data:
            return resposta_data

    apagar_data_checklist = apagar_data_pagamento_checklist_formatado(texto_limpo)
    if apagar_data_checklist:
        return apagar_data_checklist

    if texto_limpo in ["vencimentos hoje", "pagamentos hoje", "contas hoje", "lembretes pagamentos hoje", "lembrete pagamentos hoje"]:
        return gerar_lembrete_pagamentos_data(relogio.hoje(date).isoformat())

    match_vencimentos_mes = re.match(r"^(?:vencimentos|datas pagamento|datas de pagamento|agenda pagamentos)(?:\s+(\d{4}-\d{2}))?$", texto_limpo)
    if match_vencimentos_mes:
        ano_mes_venc = validar_ano_mes(match_vencimentos_mes.group(1) or relogio.hoje(date).strftime("%Y-%m"))
        if not ano_mes_venc:
            return "Mês inválido. Use: vencimentos 2026-07"
        return listar_vencimentos_checklist_formatado(ano_mes_venc)


    transferencia_parse = parsear_comando_transferencia_caixa(texto)
    if transferencia_parse:
        if not transferencia_parse.get("erro"):
            pedido = _gravacao_pede_confirmacao(texto, _previa_transferencia_caixa(transferencia_parse), sessao)
            if pedido is not None:
                return pedido
        transferencia_caixa = registrar_transferencia_caixa_formatado(texto)
        m_id_transf = re.search(r"(?m)^#(\d+)$", str(transferencia_caixa or ""))
        if m_id_transf:
            _auditar_roteador("transferencias_caixa", int(m_id_transf.group(1)), "criada", sessao,
                              depois={k: transferencia_parse.get(k) for k in ("data", "valor", "conta_origem", "conta_destino")})
        if transferencia_caixa:
            return transferencia_caixa

    match_transferencias_caixa = re.match(
    r"^(?:"
    r"transferencia|transferência|"
    r"transferencias|transferências|"
    r"transferencias caixa|transferências caixa|"
    r"transferencias de caixa|transferências de caixa"
    r")(?:\s+(\d{4}-\d{2}))?$",
    texto_limpo
)
    if match_transferencias_caixa:
        ano_mes_transf = validar_ano_mes(match_transferencias_caixa.group(1) or relogio.hoje(date).strftime("%Y-%m"))
        if not ano_mes_transf:
            return "Mês inválido. Use: transferências caixa 2026-07"
        return listar_transferencias_caixa_formatado(ano_mes_transf)

    match_apagar_transferencia_caixa = re.match(_RE_APAGAR_TRANSFERENCIA_CAIXA, texto_limpo)
    if match_apagar_transferencia_caixa:
        # Só chega aqui confirmado (o gate de exclusão acima exige prévia + backup).
        from database import buscar_transferencia_caixa_por_id
        transferencia_id = int(match_apagar_transferencia_caixa.group(1))
        antes_transf = buscar_transferencia_caixa_por_id(transferencia_id)
        resposta_transf = apagar_transferencia_caixa_formatado(transferencia_id)
        if antes_transf:
            registrar_auditoria("transferencias_caixa", transferencia_id, "apagada",
                                dados_antes=dict(antes_transf), origem="telegram",
                                usuario_sessao=_chave_sessao(sessao))
        return resposta_transf


    if texto_limpo in ["registrar", "novo lançamento", "novo lancamento", "nova despesa", "nova entrada", "cadastrar"]:
        return gerar_tela_registrar_ux()

    if texto_limpo in ["hoje", "meu dia", "fechamento do dia", "rotina do dia"]:
        return gerar_painel_hoje_ux()

    if texto_limpo in ["ajustes", "configuracoes", "configurações", "opcoes", "opções"]:
        return gerar_tela_ajustes_ux()

    detalhe_checklist_cmd = parsear_comando_detalhar_checklist(texto_limpo)
    if detalhe_checklist_cmd:
        return detalhar_item_checklist_formatado(detalhe_checklist_cmd[0], detalhe_checklist_cmd[1])

    reset_checklist_mes = parsear_comando_resetar_checklist(texto_limpo)
    if reset_checklist_mes:
        marcacoes_antes = {k: dict(v) for k, v in buscar_checklist_status_mes(reset_checklist_mes).items()}
        resposta_reset = resetar_checklist_formatado(reset_checklist_mes)
        if marcacoes_antes:
            registrar_auditoria("checklist_pagamentos", reset_checklist_mes, "resetado",
                                dados_antes=marcacoes_antes, origem="telegram",
                                usuario_sessao=_chave_sessao(sessao))
        return resposta_reset

    # Marcar pago/pendente no checklist: exceção justificada à prévia (é só a
    # marcação visual, sem dinheiro; a baixa de compromisso e a fatura com saldo
    # já são recusadas e mandam para A pagar). Grava direto, com auditoria e a
    # instrução de como desfazer.
    for parser_marcar, marcar, multiplo in (
        (parsear_comando_marcar_checklist_multiplo, marcar_itens_checklist_formatado, True),
        (parsear_comando_marcar_checklist, marcar_item_checklist_formatado, False),
    ):
        marcar_cmd = parser_marcar(texto_limpo)
        if not marcar_cmd:
            continue
        if _COLETANDO_PREVIA.get():
            raise _PreviaColetada(None)  # recálculo de prévia nunca marca nada
        ano_mes_marca, chaves_marca, status_marca = marcar_cmd
        ano_mes_marca = validar_ano_mes(ano_mes_marca) or relogio.hoje(date).strftime("%Y-%m")
        antes_marca = {k: dict(v) for k, v in buscar_checklist_status_mes(ano_mes_marca).items()}
        resposta_marca = marcar(ano_mes_marca, chaves_marca, status_marca)
        depois_marca = {k: dict(v) for k, v in buscar_checklist_status_mes(ano_mes_marca).items()}
        if depois_marca != antes_marca:
            mudou = {k: v for k, v in depois_marca.items() if antes_marca.get(k) != v}
            _auditar_roteador("checklist_pagamentos", ano_mes_marca, f"marcado_{status_marca}", sessao,
                              antes={k: antes_marca.get(k) for k in mudou}, depois=mudou)
        return _sufixo_desfazer_checklist(resposta_marca, ano_mes_marca,
                                          chaves_marca if multiplo else [chaves_marca], status_marca)

    checklist_cmd = parsear_comando_checklist(texto_limpo)
    if checklist_cmd:
        return gerar_checklist_pagamentos(checklist_cmd[0], checklist_cmd[1])

    pendencias_abertas_cmd = parsear_comando_pendencias_abertas(texto_limpo)
    if pendencias_abertas_cmd:
        return gerar_pendencias_abertas_formatado(pendencias_abertas_cmd[0], pendencias_abertas_cmd[1])

    match_heranca = re.match(r"^(?:heranca|herança|saldo herdado|ponte do mes|ponte do mês)(?:\s+(\d{4}-\d{2}))?$", texto_limpo)
    if match_heranca:
        ano_mes_h = validar_ano_mes(match_heranca.group(1)) if match_heranca.group(1) else relogio.hoje(date).strftime("%Y-%m")
        dados_h = obter_metricas_resultado_mes(ano_mes_h)
        return "\n".join([
            f"🔁 Herança / ponte — {formatar_ano_mes_visual(ano_mes_h)}",
            "",
            bloco_heranca_mes_anterior(dados_h),
        ])

    auditoria_despesas_cmd = parsear_comando_auditoria_despesas(texto_limpo)
    if auditoria_despesas_cmd:
        return gerar_auditoria_despesas_mes(auditoria_despesas_cmd[0], auditoria_despesas_cmd[1])

    caixa_por_conta_cmd = parsear_comando_caixa_por_conta(texto_limpo)
    if caixa_por_conta_cmd:
        return gerar_caixa_por_conta_mes(caixa_por_conta_cmd)

    dashboard_categorias_mes = parsear_comando_dashboard_categorias(texto_limpo)
    if dashboard_categorias_mes:
        return gerar_dashboard_categorias_visual_mes(dashboard_categorias_mes)

    dashboard_mes = parsear_comando_dashboard(texto_limpo)
    if dashboard_mes:
        return gerar_dashboard_visual_mes(dashboard_mes)

    saldo_inicial_cmd = parsear_comando_saldo_inicial(texto_limpo)
    if saldo_inicial_cmd:
        tipo_prev, texto_prev = _previa_saldo_inicial(*saldo_inicial_cmd)
        if tipo_prev == "previa":
            pedido = _gravacao_pede_confirmacao(texto, texto_prev, sessao)
            if pedido is not None:
                return pedido
        return definir_saldo_inicial_formatado(saldo_inicial_cmd[0], saldo_inicial_cmd[1], saldo_inicial_cmd[2])

    if texto_limpo in [
        "saldo",
        "saldo do mês",
        "saldo do mes",
        "saldo geral",
        "saldo geral do mês",
        "saldo geral do mes",
        "saldo total",
        "saldo consolidado",
        "saldo acumulado",
        "minha vida financeira",
        "vida financeira",
        "carteira",
        "caixa mensal",
    ]:
        return gerar_saldo_mes_ux(relogio.hoje(date).strftime("%Y-%m"))

    match_saldo_geral_mes = re.match(
        r"^(?:saldo geral|saldo geral do mês|saldo geral do mes|saldo total|saldo consolidado|saldo acumulado|minha vida financeira|vida financeira|caixa geral)\s+(\d{4}-\d{2})$",
        texto_limpo
    )
    if match_saldo_geral_mes:
        ano_mes = validar_ano_mes(match_saldo_geral_mes.group(1))
        if not ano_mes:
            return "Mês inválido. Use o formato: saldo geral 2026-07"
        return gerar_saldo_mes_ux(ano_mes)

    # Aceita a ordem mais natural e já usada na ajuda: saldo Mercado Pago 2026-07.
    # Esse padrão precisa vir antes do saldo da conta atual para que o mês não
    # seja incorporado indevidamente ao nome da conta.
    match_saldo_conta_mes_final = re.match(
        r"^(?:saldo|saldo do mês|saldo do mes|carteira|caixa|caixa mensal)\s+(.+?)\s+(\d{4}-\d{2})$",
        texto_limpo,
    )
    if match_saldo_conta_mes_final:
        conta = match_saldo_conta_mes_final.group(1).strip()
        ano_mes = validar_ano_mes(match_saldo_conta_mes_final.group(2))
        if not ano_mes:
            return "Mês inválido. Use o formato: saldo Mercado Pago 2026-07"
        if eh_alias_saldo_geral(conta):
            return gerar_saldo_mes_ux(ano_mes)
        return gerar_saldo_mes_ux(ano_mes, formatar_nome_conta_saldo(conta))

    match_saldo_mes_conta = re.match(r"^(?:saldo|saldo do mês|saldo do mes|carteira|caixa|caixa mensal)\s+(\d{4}-\d{2})\s+(.+)$", texto_limpo)
    if match_saldo_mes_conta:
        ano_mes = validar_ano_mes(match_saldo_mes_conta.group(1))
        conta = match_saldo_mes_conta.group(2).strip()
        if not ano_mes:
            return "Mês inválido. Use o formato: saldo 2026-07 BTG"
        if eh_alias_saldo_geral(conta):
            return gerar_saldo_mes_ux(ano_mes)
        return gerar_saldo_mes_ux(ano_mes, formatar_nome_conta_saldo(conta))

    match_saldo_mes_novo = re.match(r"^(?:saldo|saldo do mês|saldo do mes|carteira|caixa|caixa mensal)\s+(\d{4}-\d{2})$", texto_limpo)
    if match_saldo_mes_novo:
        ano_mes = validar_ano_mes(match_saldo_mes_novo.group(1))
        if not ano_mes:
            return "Mês inválido. Use o formato: saldo 2026-07"
        return gerar_saldo_mes_ux(ano_mes)

    match_saldo_conta_atual = re.match(r"^(?:saldo|saldo do mês|saldo do mes|carteira|caixa|caixa mensal)\s+(.+)$", texto_limpo)
    # "caixa de som 200" é uma compra, não o saldo de uma conta chamada "De Som 200".
    if (match_saldo_conta_atual and re.match(r"^(?:caixa|carteira)\s", texto_limpo)
            and len(texto_limpo.split()) >= 3
            and re.search(r"(?<!\w)\d+(?:[.,]\d{1,2})?(?!\w)", texto_limpo)):
        match_saldo_conta_atual = None
    if match_saldo_conta_atual:
        conta = match_saldo_conta_atual.group(1).strip()
        if eh_alias_saldo_geral(conta):
            return gerar_saldo_mes_ux(relogio.hoje(date).strftime("%Y-%m"))
        return gerar_saldo_mes_ux(relogio.hoje(date).strftime("%Y-%m"), formatar_nome_conta_saldo(conta))

    movimentacoes_conta_cmd = parsear_comando_movimentacoes_conta_mes(texto_limpo)
    if movimentacoes_conta_cmd:
        return movimentacoes_conta_mes_formatado(
            movimentacoes_conta_cmd[0],
            movimentacoes_conta_cmd[1],
            movimentacoes_conta_cmd[2],
            movimentacoes_conta_cmd[3],
        )

    extrato_conta_cmd = parsear_comando_extrato_conta_mes(texto_limpo)
    if extrato_conta_cmd:
        return extrato_conta_mes_formatado(
            extrato_conta_cmd[0],
            extrato_conta_cmd[1],
            extrato_conta_cmd[2],
            extrato_conta_cmd[3],
        )

    if texto_limpo in ["meu mês", "meu mes", "painel do mês", "painel do mes", "resumo do mês", "resumo do mes"]:
        return gerar_meu_mes_curto_ux(relogio.hoje(date).strftime("%Y-%m"))

    if texto_limpo in ["detalhes meu mês", "detalhes meu mes", "ver detalhes meu mês", "ver detalhes meu mes"]:
        return gerar_meu_mes_ux(relogio.hoje(date).strftime("%Y-%m"))

    match_detalhes_meu_mes = re.match(r"^(detalhes meu mês|detalhes meu mes|ver detalhes meu mês|ver detalhes meu mes)\s+(\d{4}-\d{2})$", texto_limpo)
    if match_detalhes_meu_mes:
        ano_mes = validar_ano_mes(match_detalhes_meu_mes.group(2))
        if not ano_mes:
            return "Mês inválido. Use o formato: detalhes meu mês 2026-07"
        return gerar_meu_mes_ux(ano_mes)

    match_meu_mes = re.match(r"^(meu mês|meu mes|painel do mês|painel do mes|resumo)\s+(\d{4}-\d{2})$", texto_limpo)
    if match_meu_mes:
        ano_mes = validar_ano_mes(match_meu_mes.group(2))
        if not ano_mes:
            return "Mês inválido. Use o formato: meu mês 2026-07"
        return gerar_meu_mes_curto_ux(ano_mes)

    if texto_limpo in ["compromissos", "meus compromissos", "visão compromissos", "visao compromissos"]:
        return gerar_compromissos_ux(relogio.hoje(date).strftime("%Y-%m"))

    match_compromissos = re.match(r"^(compromissos|meus compromissos)\s+(\d{4}-\d{2})$", texto_limpo)
    if match_compromissos:
        ano_mes = validar_ano_mes(match_compromissos.group(2))
        if not ano_mes:
            return "Mês inválido. Use o formato: compromissos 2026-07"
        return gerar_compromissos_ux(ano_mes)

    if texto_limpo in ["revisar", "revisao", "revisão", "revisar base", "revisar dados", "revisar lançamentos", "revisar lancamentos"]:
        return gerar_revisao_inteligente()
    match_detalhar_lancamento = re.match(
        r"^(?:detalhar|abrir|ver|mostrar)\s+(?:lançamento|lancamento|transação|transacao)\s+#?(\d+)$",
        texto_limpo
    )
    if match_detalhar_lancamento:
        return buscar_transacao_detalhada_formatado(int(match_detalhar_lancamento.group(1)))

    match_lancamento_direto = re.match(r"^(?:lançamento|lancamento|transação|transacao)\s+#?(\d+)$", texto_limpo)
    if match_lancamento_direto:
        return buscar_transacao_detalhada_formatado(int(match_lancamento_direto.group(1)))

    if texto_limpo in ["buscar", "procurar", "pesquisar"]:
        return buscar_transacoes_formatado("", 1)

    match_busca_paginada = re.match(r"^buscar\s+(.+?)\s+pagina\s+(\d+)$", texto_limpo)
    if match_busca_paginada:
        return buscar_transacoes_formatado(match_busca_paginada.group(1).strip(), int(match_busca_paginada.group(2)))

    match_busca = re.match(r"^buscar\s+(.+)$", texto_limpo)
    if match_busca:
        return buscar_transacoes_formatado(match_busca.group(1).strip(), 1)

    match_ultimas_pagina = re.match(r"^(?:ultimas|últimas|listar ultimos|listar últimos|listarultimos|ultimos|últimos)\s+pagina\s+(\d+)$", texto_limpo)
    if match_ultimas_pagina:
        return listar_ultimas_paginado(int(match_ultimas_pagina.group(1)))

    match_ultimas_filtro_pagina = re.match(r"^(?:ultimas|últimas|listar ultimos|listar últimos)\s+(.+?)\s+pagina\s+(\d+)$", texto_limpo)
    if match_ultimas_filtro_pagina:
        return listar_ultimas_paginado(int(match_ultimas_filtro_pagina.group(2)), match_ultimas_filtro_pagina.group(1).strip())

    match_ultimas_filtro = re.match(r"^(?:ultimas|últimas|listar ultimos|listar últimos)\s+(.+)$", texto_limpo)
    if match_ultimas_filtro:
        termo = match_ultimas_filtro.group(1).strip()

        if termo.isdigit():
            # Compatibilidade: "últimas 20" mostra página 1, mas limitada visualmente por página.
            return montar_lista_transacoes_paginada(
                list(buscar_ultimas_transacoes(int(termo))),
                f"📌 Últimas {termo} transações",
                1
            )

        return listar_ultimas_paginado(1, termo)

    if texto_limpo in ["listarultimos", "listar ultimos", "listar últimos", "ultimos", "últimos", "ultimas", "últimas"]:
        return listar_ultimas_paginado(1)

    if _obter_pendencia(PENDENCIAS_EXPORTACAO, sessao):
        if texto_limpo in ["cancelar", "cancelar exportacao", "cancelar exportação"]:
            _limpar_pendencia(PENDENCIAS_EXPORTACAO, sessao)
            return "📤 Exportação cancelada."

        periodo_pendente = extrair_periodo_exportacao(texto_limpo)
        if periodo_pendente:
            _limpar_pendencia(PENDENCIAS_EXPORTACAO, sessao)
            return exportar_csv_periodo(periodo_pendente[0], periodo_pendente[1])

        if texto_limpo in ["tudo", "base inteira", "completo", "completa",
                           "exportar csv tudo", "exportar tudo", "exportar csv completo",
                           "exportar csv completa", "exportar csv base inteira"]:
            _limpar_pendencia(PENDENCIAS_EXPORTACAO, sessao)
            return exportar_csv_completo()

        return (
            "📤 Exportação CSV\n\n"
            "Não entendi o período. Envie duas datas no formato:\n"
            "2026-06-01 2030-12-30\n\n"
            "Ou envie: tudo\n"
            "Para cancelar: cancelar"
        )

    if texto_limpo in ["cancelar exportacao", "cancelar exportação"]:
        return "📤 Não há exportação pendente. Nada foi alterado."

    if texto_limpo == "confirmar":
        return confirmar_lancamento_pendente(sessao)

    if texto_limpo == "cancelar":
        return cancelar_lancamento_pendente(sessao)

    if texto_limpo == "confirmar importacao" or texto_limpo == "confirmar importação":
        return confirmar_importacao_csv(sessao)

    if texto_limpo == "cancelar importacao" or texto_limpo == "cancelar importação":
        _limpar_pendencia(PENDENCIAS_IMPORTACAO, sessao)
        return "Importação cancelada. Nada foi gravado."

    if texto_limpo in ["analisar csv", "importar csv", "prever importacao csv", "prever importação csv"]:
        return analisar_csv_importacao(sessao)

    entrada_fixa = parsear_comando_entrada_fixa(texto_limpo)
    if entrada_fixa:
        if entrada_fixa.get("erro"):
            return f"Não consegui cadastrar a entrada fixa. Exemplo: {entrada_fixa['exemplo']}"

        valor = entrada_fixa["valor"]

        if valor is None or valor <= 0:
            return "Valor inválido. Exemplo: nova entrada fixa salário 3800 dia 5"

        return cadastrar_entrada_fixa_formatado(
            entrada_fixa["nome"],
            valor,
            entrada_fixa["dia"],
            entrada_fixa["conta"]
        )

    entrada_avulsa = parsear_comando_entrada_avulsa(texto_limpo)
    if entrada_avulsa:
        if entrada_avulsa.get("erro"):
            return f"Não consegui cadastrar a entrada futura. Exemplo: {entrada_avulsa['exemplo']}"

        valor = entrada_avulsa["valor"]

        if valor is None or valor <= 0:
            return "Valor inválido. Exemplo: entrada décimo terceiro 1900,00 em 2026-12-20"

        return cadastrar_entrada_avulsa_formatado(
            entrada_avulsa["nome"],
            valor,
            entrada_avulsa["data"],
            entrada_avulsa["conta"]
        )

    if texto_limpo in ["entradas", "receitas"]:
        return listar_entradas_mes_formatado(relogio.hoje(date).strftime("%Y-%m"))

    if texto_limpo in ["entradas cadastradas", "receitas cadastradas", "listar entradas", "listar receitas", "entradas fixas", "receitas fixas"]:
        return listar_entradas_formatado()

    match_entradas_mes = re.match(r"^(entradas|receitas)\s+(\d{4}-\d{2})$", texto_limpo)
    if match_entradas_mes:
        ano_mes = validar_ano_mes(match_entradas_mes.group(2))
        if not ano_mes:
            return "Mês inválido. Use o formato: entradas 2026-07"
        return listar_entradas_mes_formatado(ano_mes)

    match_alterar_entrada = re.match(r"^alterar entrada\s+#?e?(\d+)\s+para\s+(.+)$", texto_limpo)
    if match_alterar_entrada:
        entrada_id = int(match_alterar_entrada.group(1))
        valor = converter_valor_texto(match_alterar_entrada.group(2))
        if valor is None or valor <= 0:
            return "Valor inválido. Exemplo: alterar entrada 1 para 3800"
        return alterar_entrada_valor(entrada_id, valor)

    match_pausar_entrada = re.match(r"^(pausar|desativar)\s+entrada\s+#?e?(\d+)$", texto_limpo)
    if match_pausar_entrada:
        return pausar_entrada(int(match_pausar_entrada.group(2)))

    match_reativar_entrada = re.match(r"^(reativar|ativar)\s+entrada\s+#?e?(\d+)$", texto_limpo)
    if match_reativar_entrada:
        return reativar_entrada(int(match_reativar_entrada.group(2)))

    match_apagar_entrada = re.match(r"^(apagar|excluir|deletar|remover)\s+entrada\s+#?e?(\d+)$", texto_limpo)
    if match_apagar_entrada:
        return apagar_entrada_formatado(int(match_apagar_entrada.group(2)))

    novo_fixo = parsear_comando_novo_fixo(texto_limpo)
    if novo_fixo:
        if novo_fixo.get("erro"):
            return f"Não consegui cadastrar o fixo. Exemplo: {novo_fixo['exemplo']}"

        valor = novo_fixo["valor"]

        if valor is None or valor <= 0:
            return "Valor inválido. Exemplo: novo fixo água 150 no pix dia 25"

        return cadastrar_fixo_manual_formatado(
            novo_fixo["nome"],
            valor,
            novo_fixo["dia"],
            novo_fixo["conta"]
        )

    # Consulta consolidada do mês, sem o termo "ainda" e sem exigir banco/conta.
    match_quanto_pagar_mes = re.match(
        r"^quanto vou pagar(?:\s+no\s+m[eê]s(?:\s+de\s+(.+))?|\s+em(?:\s+(.+))?|\s+(n?es[st]e\s+m[eê]s|(?:no\s+)?m[eê]s\s+atual))?$",
        texto_limpo,
    )
    if match_quanto_pagar_mes:
        referencia = (match_quanto_pagar_mes.group(1) or match_quanto_pagar_mes.group(2) or match_quanto_pagar_mes.group(3) or "").strip()
        # "este/esse/neste/nesse mês" e "mês atual" são o mês vigente.
        if not referencia or re.fullmatch(r"(?:no\s+)?(?:n?es[st]e\s+)?m[eê]s(?:\s+atual)?", referencia):
            ano_mes = relogio.hoje(date).strftime("%Y-%m")
        else:
            ano_mes = normalizar_ano_mes_flexivel(referencia)
            if not ano_mes:
                # Nome do mês sem ano usa o ano atual.
                ano_mes = normalizar_ano_mes_flexivel(f"{referencia} {relogio.hoje(date).year}")
        if not ano_mes:
            return "Mês inválido. Exemplos: quanto vou pagar no mês | quanto vou pagar em julho/2026"
        return resumo_pagamento_mes_consolidado(ano_mes)

    match_detalhar_pagamento = re.match(
        r"^(?:detalhar|ver detalhes)(?:\s+quanto vou pagar)?\s+no\s+(.+?)(?:\s+em\s+(\d{4}-\d{2}))?$",
        texto_limpo,
    )
    if match_detalhar_pagamento:
        termo = match_detalhar_pagamento.group(1).strip()
        ano_mes = match_detalhar_pagamento.group(2) or relogio.hoje(date).strftime("%Y-%m")
        ano_mes = validar_ano_mes(ano_mes)
        if not ano_mes:
            return "Mês inválido. Use: detalhar quanto vou pagar no Itaú em 2026-07"
        return detalhar_pagamento_por_conta(ano_mes, termo)

    match_quanto_pagar = re.match(r"^quanto vou pagar no\s+(.+?)(?:\s+em\s+(\d{4}-\d{2}))?$", texto_limpo)
    if match_quanto_pagar:
        termo = match_quanto_pagar.group(1).strip()
        ano_mes = match_quanto_pagar.group(2) or relogio.hoje(date).strftime("%Y-%m")
        ano_mes = validar_ano_mes(ano_mes)
        if not ano_mes:
            return "Mês inválido. Use o formato: quanto vou pagar no nubank em 2026-07"
        return resumo_pagamento_por_conta(ano_mes, termo)

    match_pagar_no = re.match(r"^pagar no\s+(.+?)(?:\s+em\s+(\d{4}-\d{2}))?$", texto_limpo)
    if match_pagar_no:
        termo = match_pagar_no.group(1).strip()
        ano_mes = match_pagar_no.group(2) or relogio.hoje(date).strftime("%Y-%m")
        ano_mes = validar_ano_mes(ano_mes)
        if not ano_mes:
            return "Mês inválido. Use o formato: pagar no nubank em 2026-07"
        return resumo_pagamento_por_conta(ano_mes, termo)

    if texto_limpo in ["contas", "formas de pagamento", "cartoes", "cartões"]:
        return resumo_contas_mes(relogio.hoje(date).strftime("%Y-%m"))

    match_contas_mes = re.match(r"^(contas|formas de pagamento|cartoes|cartões)\s+(\d{4}-\d{2})$", texto_limpo)
    if match_contas_mes:
        ano_mes = validar_ano_mes(match_contas_mes.group(2))
        if not ano_mes:
            return "Mês inválido. Use o formato: contas 2026-07"
        return resumo_contas_mes(ano_mes)

    if texto_limpo in ["formas", "forma", "formas pagamento", "formas de pagamento detalhadas"]:
        return listar_formas_mes(relogio.hoje(date).strftime("%Y-%m"))

    match_formas_mes = re.match(r"^(formas|forma)\s+(\d{4}-\d{2})$", texto_limpo)
    if match_formas_mes:
        ano_mes = validar_ano_mes(match_formas_mes.group(2))
        if not ano_mes:
            return "Mês inválido. Use o formato: formas 2026-07"
        return listar_formas_mes(ano_mes)

    if texto_limpo in ["categorias", "categoria", "categorias detalhadas"]:
        return listar_categorias_mes(relogio.hoje(date).strftime("%Y-%m"))

    match_categorias_mes = re.match(r"^(categorias detalhadas|categorias|categoria)\s+(\d{4}-\d{2})$", texto_limpo)
    if match_categorias_mes:
        ano_mes = validar_ano_mes(match_categorias_mes.group(2))
        if not ano_mes:
            return "Mês inválido. Use o formato: categorias 2026-07"
        return listar_categorias_mes(ano_mes)

    if texto_limpo in ["detalhar mes", "detalhar mês", "detalhar mês atual", "detalhar mes atual", "detalhar tudo"]:
        return detalhar_mes(relogio.hoje(date).strftime("%Y-%m"))

    match_detalhar_mes = re.match(r"^detalhar\s+(\d{4}-\d{2})$", texto_limpo)
    if match_detalhar_mes:
        ano_mes = validar_ano_mes(match_detalhar_mes.group(1))
        if not ano_mes:
            return "Mês inválido. Use o formato: detalhar 2026-07"
        return detalhar_mes(ano_mes)

    match_detalhar_categoria_mes = re.match(
        r"^detalhar\s+(?:categoria\s+)?(.+?)\s+(\d{4}-\d{2})$",
        texto_limpo
    )
    if match_detalhar_categoria_mes:
        categoria = match_detalhar_categoria_mes.group(1).strip()
        ano_mes = validar_ano_mes(match_detalhar_categoria_mes.group(2))
        if not ano_mes:
            return "Mês inválido. Use o formato: detalhar categoria assinaturas 2026-07"
        return detalhar_categoria_mes(categoria, ano_mes)

    match_detalhar_categoria_atual = re.match(
        r"^detalhar\s+(?:categoria\s+)?(.+)$",
        texto_limpo
    )
    if match_detalhar_categoria_atual:
        categoria = match_detalhar_categoria_atual.group(1).strip()

        if categoria not in ["mes", "mês", "tudo"]:
            return detalhar_categoria_mes(categoria, relogio.hoje(date).strftime("%Y-%m"))

    match_categoria_futuro = re.match(
        r"^(?:categoria\s+)?(.+?)\s+(?:futuro|proximos meses|próximos meses)$",
        texto_limpo
    )
    if match_categoria_futuro:
        categoria = match_categoria_futuro.group(1).strip()
        return detalhar_categoria_futuro(categoria)

    match_categoria_direta_mes = re.match(r"^([a-záàâãéêíóôõúç\s]+)\s+(\d{4}-\d{2})$", texto_limpo)
    if match_categoria_direta_mes:
        termo = match_categoria_direta_mes.group(1).strip()
        ano_mes = validar_ano_mes(match_categoria_direta_mes.group(2))

        termos_bloqueados = [
            "agenda", "parcelas", "parcelamento", "contas", "formas", "categorias",
            "resumo", "saldo", "relatorio", "relatório", "fechamento", "exportar csv"
        ]

        if ano_mes and termo not in termos_bloqueados:
            return detalhar_categoria_mes(termo, ano_mes)

    if texto_limpo == "fixos":
        return listar_fixos_formatado()

    match_fixos_filtro = re.match(r"^fixos\s+(.+)$", texto_limpo)
    if match_fixos_filtro:
        return listar_fixos_formatado(match_fixos_filtro.group(1).strip())

    if texto_limpo in ["compromissos fixos"]:
        return listar_compromissos_formatado("fixo")

    if texto_limpo in ["compromissos parcelados", "compromissos parcelas"]:
        return listar_parcelamentos_unificados_formatado()

    match_alterar_fixo = re.match(r"^alterar fixo\s+(\d+)\s+para\s+(.+)$", texto_limpo)
    if match_alterar_fixo:
        compromisso_id = int(match_alterar_fixo.group(1))
        valor = converter_valor_texto(match_alterar_fixo.group(2))
        if valor is None:
            return "Valor inválido. Exemplo: alterar fixo 1 para 250"
        return alterar_fixo_valor(compromisso_id, valor)

    match_vencimento_fixo = re.match(r"^alterar vencimento fixo\s+(\d+)\s+para\s+(?:dia\s+)?(\d{1,2})$", texto_limpo)
    if match_vencimento_fixo:
        compromisso_id = int(match_vencimento_fixo.group(1))
        dia = int(match_vencimento_fixo.group(2))
        return alterar_fixo_vencimento(compromisso_id, dia)

    match_alterar_conta_compromisso = re.match(
        r"^(?:alterar|mudar|trocar)\s+conta\s+(?:do\s+)?(?:fixo|compromisso|parcela|parcelamento)\s+(\d+)\s+(?:para|por)\s+(.+)$",
        texto_limpo
    )
    if match_alterar_conta_compromisso:
        compromisso_id = int(match_alterar_conta_compromisso.group(1))
        nova_conta = match_alterar_conta_compromisso.group(2).strip()
        return alterar_compromisso_conta(compromisso_id, nova_conta)

    match_alterar_forma_compromisso = re.match(
        r"^(?:alterar|mudar|trocar)\s+forma\s+(?:do\s+)?(?:fixo|compromisso|parcela|parcelamento)\s+(\d+)\s+(?:para|por)\s+(.+)$",
        texto_limpo
    )
    if match_alterar_forma_compromisso:
        compromisso_id = int(match_alterar_forma_compromisso.group(1))
        nova_forma = match_alterar_forma_compromisso.group(2).strip()
        return alterar_compromisso_forma(compromisso_id, nova_forma)

    match_alterar_categoria_compromisso = re.match(
        r"^(?:alterar|mudar|trocar)\s+categoria\s+(?:do\s+)?(?:fixo|compromisso|parcela|parcelamento)\s+(\d+)\s+(?:para|por)\s+(.+)$",
        texto_limpo
    )
    if match_alterar_categoria_compromisso:
        compromisso_id = int(match_alterar_categoria_compromisso.group(1))
        nova_categoria = match_alterar_categoria_compromisso.group(2).strip()
        return alterar_compromisso_categoria(compromisso_id, nova_categoria)

    match_pausar_fixo = re.match(r"^(pausar|desativar)\s+(?:fixo|compromisso)\s+(\d+)$", texto_limpo)
    if match_pausar_fixo:
        return pausar_compromisso(int(match_pausar_fixo.group(2)))

    match_reativar_fixo = re.match(r"^(reativar|ativar)\s+(?:fixo|compromisso)\s+(\d+)$", texto_limpo)
    if match_reativar_fixo:
        return reativar_compromisso(int(match_reativar_fixo.group(2)))

    match_apagar_fixo = re.match(r"^(apagar|excluir|deletar|remover)\s+(?:fixo|compromisso)\s+(\d+)$", texto_limpo)
    if match_apagar_fixo:
        return apagar_compromisso_formatado(int(match_apagar_fixo.group(2)))

    if texto_limpo in ["status", "diagnostico", "diagnóstico"]:
        return gerar_status()

    if texto_limpo in ["assessor", "diagnostico financeiro", "diagnóstico financeiro", "modo assessor"]:
        return gerar_diagnostico_assessor()

    if texto_limpo in ["agenda", "agenda financeira"]:
        return gerar_agenda_assessor()

    match_agenda_mes = re.match(r"^agenda\s+(\d{4}-\d{2})$", texto_limpo)
    if match_agenda_mes:
        ano_mes = validar_ano_mes(match_agenda_mes.group(1))
        if not ano_mes:
            return "Mês inválido. Use o formato: agenda 2026-07"
        return resumo_contas_mes(ano_mes)

    if texto_limpo in ["fechamento semanal", "semana"]:
        return gerar_fechamento_semanal_formatado()

    if texto_limpo in ["fechamento do mes", "fechamento do mês", "fechamento mensal"]:
        return gerar_fechamento_mensal_formatado()

    match_fechamento_mes = re.match(r"^fechamento\s+(\d{4}-\d{2})$", texto_limpo)
    if match_fechamento_mes:
        ano_mes = validar_ano_mes(match_fechamento_mes.group(1))
        if not ano_mes:
            return "Mês inválido. Use o formato: fechamento 2026-07"
        return gerar_fechamento_mensal_formatado(ano_mes)

    if texto_limpo.startswith("simular "):
        mensagem = texto.strip()[8:].strip()
        return simular_lancamento(mensagem)

    if texto_limpo.startswith("posso comprar "):
        mensagem = texto.strip()[14:].strip()
        return analisar_compra(mensagem)

    if texto_limpo.startswith("vale a pena comprar "):
        mensagem = texto.strip()[20:].strip()
        return analisar_compra(mensagem)

    if texto_limpo in ["parcelamentos", "listar parcelamentos", "minhas parcelas"]:
        return listar_parcelamentos_unificados_formatado()

    match_apagar_parcelamento = re.match(r"^(apagar|excluir|deletar|remover)\s+parcelamento\s+#?([pc]?\d+)$", texto_limpo)
    if match_apagar_parcelamento:
        return apagar_parcelamento_unificado(match_apagar_parcelamento.group(2))

    if texto_limpo in ["parcelas futuras", "parcelamentos futuros"]:
        return listar_parcelas_futuras_unificadas()

    match_parcelas_mes = re.match(r"^parcelas\s+(\d{4}-\d{2})$", texto_limpo)
    if match_parcelas_mes:
        ano_mes = validar_ano_mes(match_parcelas_mes.group(1))
        if not ano_mes:
            return "Mês inválido. Use o formato: parcelas 2026-07"
        return listar_parcelas_mes_unificadas(ano_mes)

    match_detalhe_parcelamento = re.match(r"^(parcelas|parcelamento)\s+#?([pc]?\d+)$", texto_limpo)
    if match_detalhe_parcelamento:
        return detalhar_parcelamento_unificado(match_detalhe_parcelamento.group(2))

    if texto_limpo in ["relatorio do mes", "relatório do mês", "relatorio mensal", "relatório mensal"]:
        return gerar_relatorio_mes()

    match_relatorio_mes = re.match(r"^relat[oó]rio\s+(\d{4}-\d{2})$", texto_limpo)
    if match_relatorio_mes:
        ano_mes = validar_ano_mes(match_relatorio_mes.group(1))
        if not ano_mes:
            return "Mês inválido. Use o formato: relatório 2026-07"
        return gerar_relatorio_mes(ano_mes)

    if texto_limpo in ["backup", "gerar backup"]:
        return gerar_backup()

    if texto_limpo in ["backup automatico", "backup automático", "gerar backup automatico", "gerar backup automático"]:
        return gerar_backup_automatico()

    if texto_limpo in ["exportar csv", "exportar transacoes", "exportar transações"]:
        return pedir_periodo_exportacao(sessao)

    if texto_limpo in ["exportar csv tudo", "exportar tudo", "exportar csv completo", "exportar csv completa", "exportar csv base inteira"]:
        return exportar_csv_completo()

    match_exportar_csv_periodo = re.match(r"^exportar csv\s+(.+)$", texto_limpo)
    if match_exportar_csv_periodo:
        argumento_exportacao = match_exportar_csv_periodo.group(1).strip()

        periodo = extrair_periodo_exportacao(argumento_exportacao)
        if periodo:
            return exportar_csv_periodo(periodo[0], periodo[1])

        ano_mes = validar_ano_mes(argumento_exportacao)
        if ano_mes:
            return exportar_csv_mes(ano_mes)

        return (
            "📤 Exportação CSV\n\n"
            "Período inválido. Use um dos formatos:\n"
            "exportar csv 2026-06-01 2030-12-30\n"
            "exportar csv 2026-07\n"
            "exportar csv tudo"
        )

    if texto_limpo in [
        "ultimos lançamentos", "últimos lançamentos", "ultimos lancamentos", "últimos lancamentos"
    ]:
        return listar_ultimas()

    match_ultimas_limite = re.match(r"^(últimos|ultimos)\s+(\d+)$", texto_limpo)
    if match_ultimas_limite:
        limite = int(match_ultimas_limite.group(2))
        if limite < 1:
            return "Informe uma quantidade maior que zero. Exemplo: últimas 20"
        if limite > 100:
            return "Para evitar mensagem muito grande, use no máximo: últimas 100"
        return listar_ultimas(limite)

    if texto_limpo in ["metas", "listar metas", "minhas metas"]:
        return listar_metas_formatado()

    match_definir_meta = re.match(r"^meta\s+(.+)\s+(\d+(?:[.,]\d{1,2})?)$", texto_limpo)
    if match_definir_meta:
        categoria = match_definir_meta.group(1).strip().title()
        valor = converter_valor_texto(match_definir_meta.group(2))
        if valor is None or valor <= 0:
            return "Valor de meta inválido. Exemplo: meta mercado 800"
        return definir_meta_formatado(categoria, valor)

    match_apagar_meta = re.match(r"^(?:apagar|excluir|deletar|remover) meta\s+(.+)$", texto_limpo)
    if match_apagar_meta:
        categoria = match_apagar_meta.group(1).strip().title()
        return apagar_meta_formatado(categoria)

    if texto_limpo in ["apagar ultimo", "apagar último", "excluir ultimo", "excluir último", "deletar ultimo", "deletar último", "remover ultimo", "remover último"]:
        return apagar_ultimo()

    match_apagar_faixa = re.match(r"^(?:apagar|excluir|deletar|remover)\s+(\d+)\s*-\s*(\d+)$", texto_limpo)
    if match_apagar_faixa:
        return apagar_por_faixa(int(match_apagar_faixa.group(1)), int(match_apagar_faixa.group(2)))

    match_apagar_id = re.match(r"^(?:apagar|excluir|deletar|remover)\s+(\d+)$", texto_limpo)
    if match_apagar_id:
        return apagar_por_id(int(match_apagar_id.group(1)))

    match_mudar_faixa = re.match(r"^mudar\s+(\d+)\s*-\s*(\d+)\s+para\s+(.+)$", texto_limpo)
    if match_mudar_faixa:
        return mudar_categoria_por_faixa(
            int(match_mudar_faixa.group(1)),
            int(match_mudar_faixa.group(2)),
            match_mudar_faixa.group(3).strip().title()
        )

    match_mudar_id = re.match(r"^mudar\s+(\d+)\s+para\s+(.+)$", texto_limpo)
    if match_mudar_id:
        return mudar_categoria_por_id(int(match_mudar_id.group(1)), match_mudar_id.group(2).strip().title())

    match_corrigir_conta = re.match(r"^(?:corrigir|alterar|mudar|trocar|editar|ajustar)\s+conta\s+(?:do\s+)?(?:lançamento|lancamento|transação|transacao)?\s*#?(\d+)\s+(?:para|por)\s+(.+)$", texto_limpo)
    if match_corrigir_conta:
        bloqueio_parcela = _bloqueio_parcela_isolada(buscar_transacao_por_id(int(match_corrigir_conta.group(1))) or {}, "conta")
        if bloqueio_parcela:
            return bloqueio_parcela
        return corrigir_conta_por_id(int(match_corrigir_conta.group(1)), match_corrigir_conta.group(2).strip())

    match_corrigir_forma = re.match(r"^(?:corrigir|alterar|mudar|trocar|editar|ajustar)\s+forma\s+(?:do\s+)?(?:lançamento|lancamento|transação|transacao)?\s*#?(\d+)\s+(?:para|por)\s+(.+)$", texto_limpo)
    if match_corrigir_forma:
        bloqueio_parcela = _bloqueio_parcela_isolada(buscar_transacao_por_id(int(match_corrigir_forma.group(1))) or {}, "forma")
        if bloqueio_parcela:
            return bloqueio_parcela
        return corrigir_forma_por_id(int(match_corrigir_forma.group(1)), match_corrigir_forma.group(2).strip())

    match_corrigir_valor = re.match(r"^corrigir valor\s+(\d+)\s+para\s+(.+)$", texto_limpo)
    if match_corrigir_valor:
        transacao_id = int(match_corrigir_valor.group(1))
        novo_valor = converter_valor_texto(match_corrigir_valor.group(2))
        if novo_valor is None:
            return "Não consegui entender o novo valor. Exemplo: corrigir valor 1 para 42,90"
        return corrigir_valor_por_id(transacao_id, novo_valor)

    match_corrigir_valor_curto = re.match(r"^corrigir\s+(\d+)\s+para\s+(.+)$", texto_limpo)
    if match_corrigir_valor_curto:
        transacao_id = int(match_corrigir_valor_curto.group(1))
        novo_valor = converter_valor_texto(match_corrigir_valor_curto.group(2))
        if novo_valor is None:
            return "Não consegui entender o novo valor. Exemplo: corrigir 1 para 42,90"
        return corrigir_valor_por_id(transacao_id, novo_valor)

    if texto_limpo == "resumo mensal":
        return gerar_resumo_mes()

    if texto_limpo in ["gastos de hoje", "gastei hoje"]:
        return gerar_gastos_hoje()

    match_categoria_mes = re.match(r"^quanto gastei com\s+(.+)\s+em\s+(\d{4}-\d{2})$", texto_limpo)
    if match_categoria_mes:
        categoria = match_categoria_mes.group(1).strip()
        ano_mes = validar_ano_mes(match_categoria_mes.group(2))
        if not ano_mes:
            return "Mês inválido. Use o formato: quanto gastei com eletrônicos em 2026-07"
        return consultar_categoria(categoria, ano_mes)

    if texto_limpo.startswith("quanto gastei com "):
        categoria = texto_limpo.replace("quanto gastei com ", "").strip()
        return consultar_categoria(categoria)

    if texto_limpo.startswith("mudar último para ") or texto_limpo.startswith("mudar ultimo para "):
        nova_categoria = texto_limpo.replace("mudar último para ", "").replace("mudar ultimo para ", "").strip().title()
        return mudar_categoria_ultimo(nova_categoria)

    comandos_protegidos = [
        # Importação/exportação
        "analisar csv", "importar csv", "prever importacao", "prever importação",
        "confirmar importacao", "confirmar importação", "cancelar importacao", "cancelar importação",
        "exportar", "backup",

        # Consultas/telas
        "status", "metas", "meta", "agenda", "parcelas", "parcelamento",
        "quanto vou pagar", "pagar no", "contas", "formas", "forma",
        "categorias", "categoria", "detalhar", "entradas", "receitas",
        "fixos", "fixo", "compromissos", "resumo", "relatório", "relatorio",
        "saldo", "caixa", "meu caixa", "dinheiro", "meu dinheiro", "aprender", "aula", "treinamento", "manual", "tutorial", "guia", "vencimento", "vencimentos", "data pagamento", "data de pagamento", "pagamentos hoje", "contas hoje", "transferi", "transferir", "transferencia", "transferência", "transferencias", "transferências", "mover", "movimentar", "passei", "assessor", "diagnostico", "diagnóstico", "fechamento",
        "simular", "posso comprar", "revisar", "revisao", "revisão",
        "registrar", "hoje", "meu mês", "meu mes", "ajustes",

        # Ações administrativas que nunca devem virar lançamento financeiro
        "apagar", "excluir", "deletar", "remover", "tirar", "cancelar",
        "alterar", "mudar", "trocar", "editar", "ajustar", "corrigir", "atualizar",
        "pausar", "suspender", "desativar", "parar", "congelar",
        "reativar", "ativar", "retomar", "religar",
        "novo fixo",
    ]

    # Prefixo só vale como comando com fronteira de palavra ("metade" não é "meta"),
    # e substantivos comuns ("guia IPTU 300", "caixa de som 200") com valor e mais de
    # duas palavras são lançamento, desde que não tragam mês (2026-07) de consulta.
    substantivos_ambiguos = {"guia", "caixa", "hoje", "dinheiro", "aula", "manual", "tutorial", "treinamento"}
    parece_lancamento = (
        len(texto_limpo.split()) >= 3
        and re.search(r"\d", texto_limpo)
        and not re.search(r"\d{4}-\d", texto_limpo)
    )

    def _comando_protegido(comando):
        if not re.match(re.escape(comando) + r"(?!\w)", texto_limpo):
            return False
        return not (comando in substantivos_ambiguos and parece_lancamento)

    if any(_comando_protegido(comando) for comando in comandos_protegidos):
        # Sugestões parecidas com o que foi digitado (nunca grava).
        from sugestoes_comando import mensagem_comando_nao_reconhecido
        return mensagem_comando_nao_reconhecido(texto)

    if re.fullmatch(r'[\d\s.,/+\-]+', texto.strip()):
        return 'Valor sem contexto. Informe a despesa ou entrada, por exemplo: gastei 35 no mercado.'
    # Pagamento de fatura só pode entrar pelo comando próprio. Como despesa
    # comum, "paguei a fatura do nubank 100" virava compra dentro da própria
    # fatura (conta Nubank, forma vazia) e somava em dobro. Juros, IOF, anuidade
    # e compras que apenas citam a fatura continuam como antes.
    if (re.search(r'\bfaturas?\b', texto_limpo)
            and re.search(r'\b(?:paguei|pago|paga|pagar|pagamento|quitei|quitada|quitado|quitar)\b', texto_limpo)
            and not re.search(r'\b(?:juros|iof|anuidade|multa|encargos?|tarifa|seguro)\b', texto_limpo)):
        return (
            "💳 Movimento de fatura não reconhecido. Nada foi registrado.\n\n"
            "Para pagar a fatura, use:\n"
            "paguei 500 da fatura Itaú usando Mercado Pago\n"
            "paguei o restante da fatura Itaú usando Mercado Pago\n\n"
            "Para estorno ou crédito:\n"
            "estorno de 50 na fatura Itaú\n\n"
            "Eu mostro uma prévia e só gravo depois que você responder confirmar pagamento (ou confirmar estorno/credito)."
        )
    from roteamento_seguro import comando_operacional
    if comando_operacional(texto):
        from sugestoes_comando import mensagem_comando_nao_reconhecido
        return mensagem_comando_nao_reconhecido(texto)
    transacao = aplicar_correcao_categoria_transacao(parse_mensagem(texto))

    if transacao and transacao.get("erro") == "mensagem_bloqueada":
        if transacao.get('motivo') == 'valor_ou_data_invalida':
            return 'Valor ou data inválidos. Nada foi registrado. Confira o valor positivo e a data informada (DD/MM/AAAA).'
        if transacao.get('motivo') == 'mais_de_um_valor':
            return 'Encontrei mais de um valor na mensagem. Nada foi registrado. Envie um lançamento por vez, com um único valor.'
        if transacao.get('motivo') == 'data_futura':
            return ('Não registro lançamento com data futura ("amanhã"). Nada foi registrado.\n'
                    'Informe a data real da compra (DD/MM/AAAA) ou use agendamento/fixo para contas futuras.')
        if transacao.get('motivo') == 'tipo_ambiguo':
            return ('Não ficou claro se é uma entrada ou uma saída. Nada foi registrado.\n\n'
                    'Comece com o verbo, por exemplo:\ngastei 300 no conserto do celular\nrecebi 500 de salário')
        return (
            "⚠️ Mensagem bloqueada\n\n"
            "Essa mensagem parece código, log ou texto grande.\n"
            "Não registrei como lançamento financeiro.\n\n"
            "Para lançar um gasto, envie algo simples como:\n"
            "gastei 35 no almoço hoje"
        )

    if not transacao:
        from sugestoes_comando import mensagem_sem_valor
        return mensagem_sem_valor(texto)

    # Lançamento por texto que chegou ao núcleo (fluxo guiado legado, botão
    # legado ou frase que a interface nova não reconheceu): prévia + confirmação.
    # As recusas (fatura a escolher, parcelamento com fatura) respondem sem gravar.
    parcelas_total = transacao.get("parcelas_total", 1)
    recusa_lancamento = (
        (eh_credito(transacao) and precisa_escolher(transacao) and not transacao.get("competencia_fatura"))
        or (parcelas_total > 1 and transacao.get("competencia_fatura"))
    )
    if not recusa_lancamento:
        pedido = _gravacao_pede_confirmacao(texto, _previa_lancamento(transacao), sessao)
        if pedido is not None:
            return pedido
    if parcelas_total > 1:
        resposta_lanc = registrar_compra_parcelada(transacao)
        m_id_lanc = re.search(r"#P(\d+)", str(resposta_lanc))
    else:
        resposta_lanc = registrar_transacao_unica(transacao)
        m_id_lanc = re.search(r"#(\d+)", str(resposta_lanc))
    if m_id_lanc and not recusa_lancamento:
        _auditar_roteador("transacoes", int(m_id_lanc.group(1)), "criada_por_texto", sessao,
                          depois={k: transacao.get(k) for k in ("tipo", "valor", "data", "categoria", "descricao",
                                                               "conta", "forma_pagamento", "parcelas_total")})
    return resposta_lanc


def analisar_csv_importacao(sessao=None):
    caminho = buscar_csv_mais_recente()

    if not caminho:
        return (
            "Não encontrei CSV para importar.\n\n"
            "Crie a pasta imports na raiz do projeto e coloque o arquivo CSV lá.\n"
            "Exemplo:\n"
            "imports\\Transactions 1 Jun 2026 - 30 Dec 2030.csv\n\n"
            "Depois envie: analisar csv"
        )

    preview = classificar_csv(caminho)
    _definir_pendencia(PENDENCIAS_IMPORTACAO, sessao, preview)
    return resumir_previa_importacao(preview)


def confirmar_importacao_csv(sessao=None):
    preview = _obter_pendencia(PENDENCIAS_IMPORTACAO, sessao)

    if not preview:
        return "📥 Importação CSV\n\nNão há importação pendente. Primeiro envie: analisar csv"

    resultado = importar_preview(preview)
    _limpar_pendencia(PENDENCIAS_IMPORTACAO, sessao)

    return "\n".join([
        "✅ Importação confirmada",
        "",
        bloco_total("Resumo", [
            f"│ {'Origem':<24} {resultado['origem'][:14]:>14}",
            f"│ {'Removidos antes':<24} {resultado['apagados_anteriores']:>14}",
            f"│ {'Importados':<24} {resultado['importados']:>14}",
        ]),
        "",
        "Próximos testes úteis:",
        "contas 2026-07",
        "quanto vou pagar no nubank em 2026-07",
        "quanto vou pagar no pix em 2026-07",
        "fixos",
        "compromissos parcelados",
    ])


def confirmar_lancamento_pendente(sessao=None):
    transacao = _obter_pendencia(PENDENCIAS_CONFIRMACAO, sessao)
    if not transacao:
        return "Não há lançamento pendente para confirmar."

    _limpar_pendencia(PENDENCIAS_CONFIRMACAO, sessao)
    parcelas_total = transacao.get("parcelas_total", 1)

    if parcelas_total > 1:
        return registrar_compra_parcelada(transacao)

    return registrar_transacao_unica(transacao)


def cancelar_lancamento_pendente(sessao=None):
    transacao = _obter_pendencia(PENDENCIAS_CONFIRMACAO, sessao)
    if not transacao:
        # "cancelar" sozinho também desiste de uma prévia de fatura pendente.
        fatura = _obter_pendencia(PENDENCIAS_PAGAMENTO_FATURA, sessao)
        if fatura and fatura.get("rotulo") in _NOME_ROTULO_FATURA:
            return cancelar_movimento_fatura_pendente(fatura["rotulo"], sessao)
        return "Não há lançamento pendente para cancelar."
    _limpar_pendencia(PENDENCIAS_CONFIRMACAO, sessao)
    return "Lançamento pendente cancelado. Nada foi registrado."


def simular_lancamento(mensagem: str):
    transacao = aplicar_correcao_categoria_transacao(parse_mensagem(mensagem))
    if not transacao:
        return "Não consegui simular porque não identifiquei um valor.\n\nExemplo:\nsimular comprei celular em 12x de 50 reais"
    if transacao.get("erro") == "mensagem_bloqueada":
        return "Mensagem bloqueada. Não simulei esse texto."
    return gerar_simulacao_transacao(transacao)


def analisar_compra(mensagem: str):
    transacao = aplicar_correcao_categoria_transacao(parse_mensagem(mensagem))
    if not transacao:
        return "Não consegui analisar a compra porque não identifiquei um valor.\n\nExemplo:\nposso comprar um drone em 10x de 300 reais"
    if transacao.get("erro") == "mensagem_bloqueada":
        return "Mensagem bloqueada. Não analisei esse texto."
    contexto = montar_contexto_financeiro(relogio.hoje(date).strftime("%Y-%m"))
    return gerar_analise_compra(transacao, contexto)


def montar_contexto_financeiro(ano_mes: str):
    """
    Monta o contexto usado pelo modo assessor e pelo fechamento mensal.

    Receitas:
    - receitas já lançadas como transação;
    - entradas previstas cadastradas como entrada fixa ou entrada avulsa.

    Despesas:
    - fixos e parcelamentos previstos;
    - despesas avulsas já lançadas.
    """
    totais, _categorias_rows = resumo_mes(ano_mes)

    receitas_registradas = 0
    despesas_registradas = 0

    for item in totais:
        if item["tipo"] == "receita":
            receitas_registradas = item["total"] or 0
        elif item["tipo"] == "despesa":
            despesas_registradas = item["total"] or 0

    itens_entradas = projetar_entradas_mes(ano_mes, incluir_transacoes=True)
    itens_entradas_programadas = projetar_entradas_mes(ano_mes, incluir_transacoes=False)
    # Pagamento de fatura não é despesa do mês (B1): sai das despesas, das
    # categorias e das metas, como em "meu mês". Estornos seguem abatendo.
    itens_agenda = remover_liquidacoes_fatura(projetar_pagamentos_mes(ano_mes, incluir_transacoes=True))
    itens_compromissos = remover_liquidacoes_fatura(projetar_pagamentos_mes(ano_mes, incluir_transacoes=False))

    receitas_previstas = sum(item["valor"] for item in itens_entradas)
    receitas_programadas = sum(item["valor"] for item in itens_entradas_programadas)
    despesas_previstas = sum(item["valor"] for item in itens_agenda)
    compromissos_previstos = sum(item["valor"] for item in itens_compromissos)

    categorias_dict = {}
    for item in itens_agenda:
        categoria = item.get("categoria") or "Outros"
        categorias_dict[categoria] = categorias_dict.get(categoria, 0) + item["valor"]

    categorias = [
        {"categoria": categoria, "total": total}
        for categoria, total in sorted(categorias_dict.items(), key=lambda kv: kv[1], reverse=True)
    ]

    metas_status = []
    for meta in listar_metas():
        categoria = meta["categoria"]
        limite = meta["valor"]
        gasto = categorias_dict.get(categoria, 0)
        percentual = (gasto / limite) * 100 if limite > 0 else 0
        restante = limite - gasto

        if restante < 0:
            status = "acima"
        elif percentual >= 80:
            status = "atenção"
        else:
            status = "ok"

        metas_status.append({
            "categoria": categoria,
            "limite": limite,
            "gasto": gasto,
            "percentual": percentual,
            "restante": restante,
            "status": status,
        })

    parcelas_futuras = calcular_parcelas_futuras_por_mes(ano_mes)

    return {
        "ano_mes": ano_mes,
        "receitas": receitas_previstas,
        "receitas_registradas": receitas_registradas,
        "receitas_programadas": receitas_programadas,
        "despesas": despesas_previstas,
        "despesas_registradas": despesas_registradas,
        "compromissos_previstos": compromissos_previstos,
        "categorias": categorias,
        "metas_status": metas_status,
        "parcelas_futuras": parcelas_futuras,
    }

def calcular_parcelas_futuras_por_mes(ano_mes_base: str):
    meses = {}
    grupos = construir_grupos_parcelamentos()

    for grupo in grupos:
        for t in grupo["transacoes"]:
            mes_transacao = competencia_transacao(t)
            if mes_transacao <= ano_mes_base:
                continue
            meses[mes_transacao] = meses.get(mes_transacao, 0) + t["valor"]

    for item in projetar_pagamentos_mes(ano_mes_base, incluir_transacoes=False):
        pass

    ano_base, mes_base = [int(x) for x in ano_mes_base.split("-")]
    base = date(ano_base, mes_base, 1)
    for i in range(1, 13):
        mes = somar_meses(base, i).strftime("%Y-%m")
        total = sum(item["valor"] for item in remover_liquidacoes_fatura(projetar_pagamentos_mes(mes, incluir_transacoes=False)))
        if total:
            meses[mes] = meses.get(mes, 0) + total

    return meses


def gerar_diagnostico_assessor():
    contexto = montar_contexto_financeiro(relogio.hoje(date).strftime("%Y-%m"))
    return gerar_diagnostico_financeiro(contexto)


def gerar_agenda_assessor():
    return gerar_agenda_assessor_ux()


def gerar_fechamento_semanal_formatado():
    hoje = relogio.hoje(date)
    inicio = hoje - timedelta(days=6)
    transacoes = buscar_todas_transacoes()
    transacoes_semana = []
    for t in transacoes:
        data_transacao = date.fromisoformat(t["data"])
        if inicio <= data_transacao <= hoje:
            transacoes_semana.append(t)
    return gerar_fechamento_semanal(transacoes_semana)


def gerar_fechamento_mensal_formatado(ano_mes: str | None = None):
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")
    contexto = montar_contexto_financeiro(ano_mes)
    return gerar_fechamento_mensal(contexto)


def obter_info_parcela(transacao):
    parcela_atual = row_get(transacao, "parcela_atual")
    parcelas_total = row_get(transacao, "parcelas_total")
    if parcela_atual and parcelas_total:
        return int(parcela_atual), int(parcelas_total)

    descricao = transacao["descricao"] or ""
    match = re.search(r"\((\d+)/(\d+)\)\s*$", descricao)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def obter_descricao_base(transacao):
    descricao = transacao["descricao"] or transacao["mensagem_original"] or "Parcelamento"
    return re.sub(r"\s*\(\d+/\d+\)\s*$", "", descricao).strip()


def construir_grupos_parcelamentos():
    transacoes = buscar_todas_transacoes()
    grupos = {}

    for t in transacoes:
        if t["tipo"] != "despesa":
            continue
        parcela_atual, parcelas_total = obter_info_parcela(t)
        if not parcela_atual or not parcelas_total or parcelas_total <= 1:
            continue

        parcelamento_id = row_get(t, "parcelamento_id")
        if parcelamento_id:
            chave = f"novo-{parcelamento_id}"
        else:
            chave = ("legado", t["mensagem_original"] or obter_descricao_base(t), t["categoria"], t["conta"], t["forma_pagamento"], parcelas_total)

        if chave not in grupos:
            grupos[chave] = {
                "parcelamento_id": parcelamento_id,
                "descricao": obter_descricao_base(t),
                "mensagem_original": t["mensagem_original"],
                "categoria": t["categoria"],
                "conta": t["conta"],
                "forma_pagamento": t["forma_pagamento"],
                "parcelas_total": parcelas_total,
                "transacoes": [],
            }
        grupos[chave]["transacoes"].append(t)

    resultado = []
    for grupo in grupos.values():
        transacoes_grupo = sorted(grupo["transacoes"], key=lambda item: item["id"])
        ids = [t["id"] for t in transacoes_grupo]
        datas = [data_competencia(t) for t in transacoes_grupo]
        total_calculado = sum(t["valor"] for t in transacoes_grupo)
        valor_total_metadata = None
        for t in transacoes_grupo:
            valor_total_metadata = row_get(t, "valor_total_parcelamento")
            if valor_total_metadata:
                break

        grupo["transacoes"] = transacoes_grupo
        grupo["id_inicio"] = min(ids)
        grupo["id_fim"] = max(ids)
        grupo["id_exibicao"] = grupo["parcelamento_id"] or grupo["id_inicio"]
        grupo["periodo_inicio"] = min(datas)[:7]
        grupo["periodo_fim"] = max(datas)[:7]
        grupo["parcelas_registradas"] = len(transacoes_grupo)
        grupo["valor_total"] = valor_total_metadata or total_calculado
        grupo["valor_registrado"] = total_calculado
        grupo["valor_parcela_media"] = total_calculado / len(transacoes_grupo) if transacoes_grupo else 0
        resultado.append(grupo)

    return sorted(resultado, key=lambda g: g["id_inicio"])




def parse_identificador_unificado(valor):
    texto = str(valor).strip().lower().replace("#", "")

    if not texto:
        return None, None

    if texto[0] in ["p", "t", "c"]:
        prefixo = texto[0]
        numero = texto[1:]
        if not numero.isdigit():
            return None, None
        return prefixo, int(numero)

    if texto.isdigit():
        return None, int(texto)

    return None, None


def ultimo_dia_mes_local(ano: int, mes: int):
    return calendar.monthrange(ano, mes)[1]


def data_no_mes_local(ano_mes: str, dia: int):
    ano, mes = [int(p) for p in ano_mes.split("-")]
    dia_real = min(dia or 1, ultimo_dia_mes_local(ano, mes))
    return date(ano, mes, dia_real)


def listar_compromissos_parcelados_ativos():
    return [c for c in listar_compromissos(tipo="parcelamento", somente_ativos=True)]


def montar_linhas_parcelamento_importado(compromisso):
    linhas = []

    inicio = date.fromisoformat(compromisso["data_inicio"])
    parcelas_total = compromisso["parcelas_total"] or 1
    dia = compromisso["dia_vencimento"] or inicio.day

    for indice in range(1, parcelas_total + 1):
        mes_ref = somar_meses(date(inicio.year, inicio.month, 1), indice - 1).strftime("%Y-%m")
        data_vencimento = data_no_mes_local(mes_ref, dia)
        linhas.append({
            "id": compromisso["id"],
            "data": data_vencimento.isoformat(),
            "valor": compromisso["valor"],
            "categoria": compromisso["categoria"],
            "nome": compromisso["nome"],
            "conta_pagamento": compromisso["conta_pagamento"] or "Não informada",
            "forma_pagamento": compromisso["forma_pagamento"] or "não informada",
            "parcela_atual": indice,
            "parcelas_total": parcelas_total,
        })

    return linhas


def listar_parcelamentos_unificados_formatado():
    grupos_manuais = construir_grupos_parcelamentos()
    importados = listar_compromissos_parcelados_ativos()

    if not grupos_manuais and not importados:
        return "Não encontrei parcelamentos registrados."

    linhas = ["💳 Parcelamentos", "", "Aqui entram juntos os parcelamentos importados do CSV e os parcelamentos novos registrados pelo bot.", ""]

    itens = []

    for grupo in grupos_manuais:
        itens.append({
            "origem": "manual",
            "ordem": grupo["periodo_inicio"],
            "texto": [
                f"#P{grupo['id_exibicao']} | {grupo['descricao']}",
                f"Conta: {grupo['conta'] or 'Não informada'} | Forma: {grupo['forma_pagamento'] or 'não informada'}",
                f"Categoria: {grupo['categoria']}",
                f"Total: {formatar_moeda(grupo['valor_total'])}",
                f"Parcelas: {grupo['parcelas_total']}x | Registradas: {grupo['parcelas_registradas']}/{grupo['parcelas_total']}",
                f"Período: {grupo['periodo_inicio']} até {grupo['periodo_fim']}",
            ]
        })

    for c in importados:
        valor_total = (c["valor"] or 0) * (c["parcelas_total"] or 1)
        fim = c["data_fim"][:7] if c["data_fim"] else "sem fim"
        itens.append({
            "origem": "importado",
            "ordem": c["data_inicio"][:7],
            "texto": [
                f"#C{c['id']} | {c['nome']}",
                f"Conta: {c['conta_pagamento'] or 'Não informada'} | Forma: {c['forma_pagamento'] or 'não informada'}",
                f"Categoria: {c['categoria']}",
                f"Total: {formatar_moeda(valor_total)}",
                f"Parcelas: {c['parcelas_total']}x de {formatar_moeda(c['valor'])}",
                f"Período: {c['data_inicio'][:7]} até {fim}",
            ]
        })

    for item in sorted(itens, key=lambda x: (x["ordem"], x["origem"])):
        linhas.extend(item["texto"])
        linhas.append("")

    linhas.append("Para detalhar, envie: parcelas ID")
    linhas.append("Exemplos: parcelas P1 ou parcelas C1")

    return "\n".join(linhas)


def detalhar_parcelamento_importado(compromisso_id: int):
    compromisso = buscar_compromisso_por_id(compromisso_id)

    if not compromisso or compromisso["tipo"] != "parcelamento":
        return None

    valor_total = (compromisso["valor"] or 0) * (compromisso["parcelas_total"] or 1)
    fim = compromisso["data_fim"][:7] if compromisso["data_fim"] else "sem fim"

    linhas = [
        f"💳 Parcelamento #C{compromisso['id']}",
        "",
        f"Descrição: {compromisso['nome']}",
        f"Categoria: {compromisso['categoria']}",
        f"Conta: {compromisso['conta_pagamento'] or 'Não informada'}",
        f"Forma: {compromisso['forma_pagamento'] or 'não informada'}",
        f"Total: {formatar_moeda(valor_total)}",
        f"Parcelas: {compromisso['parcelas_total']}x de {formatar_moeda(compromisso['valor'])}",
        f"Período: {compromisso['data_inicio'][:7]} até {fim}",
        "",
        "Parcelas:"
    ]

    for item in montar_linhas_parcelamento_importado(compromisso):
        linhas.append(
            f"#C{item['id']} | {item['data']} | {formatar_moeda(item['valor'])} | "
            f"{item['parcela_atual']}/{item['parcelas_total']}"
        )

    return "\n".join(linhas)


def detalhar_parcelamento_unificado(identificador):
    prefixo, numero = parse_identificador_unificado(identificador)

    if numero is None:
        return "Identificador inválido. Use: parcelas P1 ou parcelas C1"

    respostas = []

    if prefixo in ["p", "t"]:
        resposta = detalhar_parcelamento(numero)
        if not resposta.startswith("Não encontrei"):
            return resposta
        return f"Não encontrei parcelamento manual #P{numero}."

    if prefixo == "c":
        resposta = detalhar_parcelamento_importado(numero)
        if resposta:
            return resposta
        return f"Não encontrei parcelamento importado #C{numero}."

    resposta_manual = detalhar_parcelamento(numero)
    if not resposta_manual.startswith("Não encontrei"):
        respostas.append(resposta_manual)

    resposta_importada = detalhar_parcelamento_importado(numero)
    if resposta_importada:
        respostas.append(resposta_importada)

    if respostas:
        return "\n\n---\n\n".join(respostas)

    return (
        f"Não encontrei parcelamento #{numero}.\n\n"
        "Use o comando:\n"
        "parcelamentos"
    )


def apagar_parcelamento_unificado(identificador):
    prefixo, numero = parse_identificador_unificado(identificador)

    if numero is None:
        return "Identificador inválido. Use: excluir parcelamento P1 ou excluir parcelamento C1"

    if prefixo in ["p", "t", None]:
        if prefixo is None:
            return apagar_parcelamento(numero)
        return apagar_parcelamento(numero)

    if prefixo == "c":
        compromisso = buscar_compromisso_por_id(numero)
        if not compromisso or compromisso["tipo"] != "parcelamento":
            return f"Não encontrei parcelamento importado #C{numero}."
        return apagar_compromisso_formatado(numero)

    return "Identificador inválido. Use: excluir parcelamento P1 ou excluir parcelamento C1"


def listar_parcelas_mes_unificadas(ano_mes: str):
    linhas = [f"💳 Parcelas — {formatar_ano_mes_visual(ano_mes)}", ""]

    itens = projetar_pagamentos_mes(ano_mes)
    itens_parcelas = [
        item for item in itens
        if item.get("tipo") == "parcelamento" or (item.get("parcela_atual") and item.get("parcelas_total"))
    ]

    if not itens_parcelas:
        return f"💳 Parcelas — {formatar_ano_mes_visual(ano_mes)}\n\nNão encontrei parcelas para este mês."

    total_mes = sum(item["valor"] for item in itens_parcelas)

    linhas.append(bloco_total("Resumo", [
        linha_valor("Total em parcelas", total_mes),
        f"│ {'Itens':<24} {len(itens_parcelas):>14}",
    ]))

    for item in itens_parcelas:
        prefixo = "C" if item.get("origem") == "compromisso" else "P"
        extra = ""
        if item.get("parcela_atual") and item.get("parcelas_total"):
            extra = f"Parcela {item['parcela_atual']}/{item['parcelas_total']}"

        linhas.extend([
            "",
            formatar_item_card(
                identificador=f"#{prefixo}{item['id']}",
                data_item=item["data"],
                valor=item["valor"],
                categoria=item["categoria"],
                nome=item["nome"],
                conta=item.get("conta_pagamento"),
                forma=item.get("forma_pagamento"),
                extra=extra,
                tipo_valor="saida",
            )
        ])

    return "\n".join(linhas)


def listar_parcelas_futuras_unificadas():
    hoje_mes = relogio.hoje(date).strftime("%Y-%m")
    ano, mes = [int(p) for p in hoje_mes.split("-")]
    base = date(ano, mes, 1)

    totais = {}

    for i in range(1, 13):
        ano_mes = somar_meses(base, i).strftime("%Y-%m")
        itens = projetar_pagamentos_mes(ano_mes)
        total_mes = sum(
            item["valor"] for item in itens
            if item.get("tipo") == "parcelamento" or (item.get("parcela_atual") and item.get("parcelas_total"))
        )
        if total_mes:
            totais[ano_mes] = total_mes

    if not totais:
        return "Não encontrei parcelas futuras."

    linhas = ["📆 Parcelas futuras", ""]
    for mes_ref, valor in sorted(totais.items()):
        linhas.append(f"- {mes_ref}: {formatar_moeda(valor)}")

    return "\n".join(linhas)




def encontrar_grupo_parcelamento_por_id(id_referencia: int):
    for grupo in construir_grupos_parcelamentos():
        if grupo["id_exibicao"] == id_referencia:
            return grupo
        if grupo["id_inicio"] <= id_referencia <= grupo["id_fim"]:
            ids = [t["id"] for t in grupo["transacoes"]]
            if id_referencia in ids:
                return grupo
    return None


def detalhar_parcelamento(id_referencia: int):
    grupo = encontrar_grupo_parcelamento_por_id(id_referencia)
    if not grupo:
        return f"Não encontrei parcelamento relacionado ao ID #{id_referencia}.\n\nUse o comando:\nparcelamentos"

    linhas = [
        f"💳 Parcelamento #{grupo['id_exibicao']}", "",
        f"Descrição: {grupo['descricao']}",
        f"Categoria: {grupo['categoria']}",
        f"Total: {formatar_moeda(grupo['valor_total'])}",
        f"Parcelas: {grupo['parcelas_total']}x",
        f"Período: {grupo['periodo_inicio']} até {grupo['periodo_fim']}",
        f"Forma: {grupo['forma_pagamento'] or 'não informada'}",
        f"Conta: {grupo['conta'] or 'não informada'}", "", "Parcelas:"
    ]
    for t in grupo["transacoes"]:
        parcela_atual, parcelas_total = obter_info_parcela(t)
        linhas.append(f"#{t['id']} | {data_competencia(t)} | {formatar_moeda(t['valor'])} | {parcela_atual}/{parcelas_total}")
    return "\n".join(linhas)


def apagar_parcelamento(id_referencia: int):
    grupo = encontrar_grupo_parcelamento_por_id(id_referencia)
    if not grupo:
        return f"Não encontrei parcelamento relacionado ao ID #{id_referencia}.\n\nUse o comando:\nparcelamentos"

    ids = [t["id"] for t in grupo["transacoes"]]
    total = sum(t["valor"] for t in grupo["transacoes"])
    # Tudo ou nada: se alguma parcela estiver conciliada, nenhuma é apagada.
    apagadas = list(apagar_transacoes_por_ids(ids))

    if not apagadas:
        return f"Não consegui apagar o parcelamento #{id_referencia}."

    return (
        "🗑️ Parcelamento apagado\n\n"
        f"Parcelamento: #{grupo['id_exibicao']}\n"
        f"Descrição: {grupo['descricao']}\n"
        f"Categoria: {grupo['categoria']}\n"
        f"Parcelas apagadas: {len(apagadas)}/{grupo['parcelas_total']}\n"
        f"IDs apagados: {', '.join(str(i) for i in ids)}\n"
        f"Valor removido: {formatar_moeda(total)}"
    )




def listar_parcelas_mes(ano_mes: str):
    itens = projetar_pagamentos_mes(ano_mes)
    grupos = construir_grupos_parcelamentos()
    linhas = [f"📆 Parcelas e compromissos de {ano_mes}", ""]
    total_mes = 0
    transacoes_exibidas = set()

    for item in itens:
        if item.get("origem") == "transacao":
            transacoes_exibidas.add(item["id"])
        total_mes += item["valor"]
        parcela = ""
        if item.get("parcela_atual") and item.get("parcelas_total"):
            parcela = f" | {item['parcela_atual']}/{item['parcelas_total']}"
        linhas.append(f"#{item['id']} | {item['data']} | {formatar_moeda(item['valor'])} | {item['conta_pagamento']} | {item['categoria']} | {item['nome']}{parcela}")

    for grupo in grupos:
        for t in grupo["transacoes"]:
            if t["id"] in transacoes_exibidas:
                continue
            if competencia_transacao(t) != ano_mes:
                continue
            parcela_atual, parcelas_total = obter_info_parcela(t)
            total_mes += t["valor"]
            linhas.append(f"#{t['id']} | {data_competencia(t)} | {formatar_moeda(t['valor'])} | {grupo['conta'] or 'Não informada'} | {grupo['categoria']} | {grupo['descricao']} | {parcela_atual}/{parcelas_total}")

    if total_mes == 0:
        return f"Não encontrei parcelas/compromissos para {ano_mes}."

    linhas.extend(["", f"Total previsto no mês: {formatar_moeda(total_mes)}"])
    return "\n".join(linhas)


def gerar_status():
    banco_existe = DB_PATH.exists()
    tamanho_banco = DB_PATH.stat().st_size if banco_existe else 0
    total_transacoes = 0
    total_metas = 0
    total_compromissos = 0
    banco_ok = False
    integridade = "não verificada"

    if banco_existe:
        try:
            uri = DB_PATH.resolve().as_uri() + "?mode=ro"
            with closing(sqlite3.connect(uri, uri=True, timeout=10)) as conn:
                conn.execute("PRAGMA query_only=ON")
                integridade = str(conn.execute("PRAGMA quick_check").fetchone()[0])
                total_transacoes = conn.execute("SELECT COUNT(*) FROM transacoes").fetchone()[0]
                total_metas = conn.execute("SELECT COUNT(*) FROM metas").fetchone()[0]
                total_compromissos = conn.execute("SELECT COUNT(*) FROM compromissos").fetchone()[0]
                banco_ok = integridade == "ok"
        except Exception:
            integridade = "falhou"

    backups = []
    if BACKUPS_DIR.exists():
        backups = sorted(BACKUPS_DIR.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    ultimo_backup = backups[0] if backups else None

    from transcricao_audio import diagnosticar_audio
    audio = diagnosticar_audio()
    audio_ok = bool(audio.get("executable_ready") and audio.get("model_ready"))
    ocr_ok = (Path(__file__).with_name("reconhecer_comprovante.ps1").is_file() and bool(shutil.which("powershell.exe"))) or bool(shutil.which("tesseract"))
    ia_configurada = bool(config.ler('ASSESSOR_IA_LOCAL_MODELO','').strip())
    sessoes_ativas = config.ler('ASSESSOR_PERSIST_SESSIONS','true').strip().lower() not in {'0','false','nao','não','off'}
    try:
        from categorias_pessoais import listar_regras
        regras_pessoais = len(listar_regras())
    except Exception:
        regras_pessoais = 0
    uptime = relogio.agora() - PROCESS_STARTED_AT
    uptime_text = f"{uptime.days}d {uptime.seconds//3600:02d}h {(uptime.seconds%3600)//60:02d}min"
    livre = shutil.disk_usage(DB_PATH.parent).free

    linhas = [
        "🩺 Status do assessor", "",
        "Aplicação",
        "- Bot: ativo",
        f"- Versão: {VERSION}",
        f"- Tempo ligado: {uptime_text}",
        f"- Retomada após reinício: {'ativa' if sessoes_ativas else 'desativada'}",
        "",
        "Banco financeiro — somente leitura nesta verificação",
        f"- Encontrado: {'sim' if banco_existe else 'não'}",
        f"- Integridade: {'OK' if banco_ok else integridade}",
        f"- Tamanho: {formatar_tamanho_bytes(tamanho_banco)}",
        f"- Espaço livre: {formatar_tamanho_bytes(livre)}",
        f"- Registros: {total_transacoes} transações · {total_compromissos} compromissos · {total_metas} limites",
        "",
        "Recursos locais",
        f"- Áudio: {'pronto' if audio_ok else 'requer instalação'} · {audio.get('provider','local')} / {audio.get('model','')}",
        f"- OCR de comprovantes: {'disponível' if ocr_ok else 'indisponível'}",
        f"- IA local: {'configurada' if ia_configurada else 'opcional, não configurada'}",
        f"- Categorias aprendidas: {regras_pessoais}",
    ]

    if ultimo_backup:
        data_backup = datetime.fromtimestamp(ultimo_backup.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        linhas.extend(["", "Último backup:", f"Arquivo: {ultimo_backup.name}", f"Data: {data_backup}", f"Tamanho: {formatar_tamanho_bytes(ultimo_backup.stat().st_size)}"])
    else:
        linhas.extend(["", "Último backup: nenhum backup encontrado"])

    return "\n".join(linhas)


def gerar_relatorio_mes(ano_mes: str | None = None):
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")

    totais, categorias = resumo_mes(ano_mes)
    receitas_lancadas = 0
    despesas_lancadas = 0

    for item in totais:
        if item["tipo"] == "receita":
            receitas_lancadas = item["total"] or 0
        elif item["tipo"] == "despesa":
            despesas_lancadas = item["total"] or 0

    entradas_programadas = sum(item["valor"] for item in projetar_entradas_mes(ano_mes, incluir_transacoes=False))
    receitas_totais = sum(item["valor"] for item in projetar_entradas_mes(ano_mes, incluir_transacoes=True))
    # Pagamento de fatura não é despesa do mês (B1), como em fechamento/meu mês;
    # estornos seguem abatendo.
    compromissos_mes = sum(item["valor"] for item in remover_liquidacoes_fatura(projetar_pagamentos_mes(ano_mes, incluir_transacoes=False)))
    despesas_totais = sum(item["valor"] for item in remover_liquidacoes_fatura(projetar_pagamentos_mes(ano_mes, incluir_transacoes=True)))
    saldo = receitas_totais - despesas_totais

    linhas = [
        f"📄 Relatório financeiro de {ano_mes}", "",
        "Resumo geral:",
        f"- Receitas lançadas: {formatar_moeda(receitas_lancadas)}",
        f"- Entradas previstas: {formatar_moeda(entradas_programadas)}",
        f"- Receitas totais previstas/registradas: {formatar_moeda(receitas_totais)}",
        f"- Despesas avulsas/lançadas: {formatar_moeda(despesas_lancadas)}",
        f"- Compromissos previstos: {formatar_moeda(compromissos_mes)}",
        f"- Saídas totais previstas/registradas: {formatar_moeda(despesas_totais)}",
        f"- Saldo projetado: {formatar_moeda(saldo)}", ""
    ]

    if categorias:
        linhas.append("Maiores categorias lançadas:")
        for indice, c in enumerate(categorias[:5], start=1):
            linhas.append(f"{indice}. {c['categoria']}: {formatar_moeda(c['total'])}")
    else:
        linhas.append("Maiores categorias lançadas: nenhuma despesa registrada.")

    linhas.append("")
    metas_texto = gerar_analise_metas_mes(ano_mes)
    if metas_texto:
        linhas.append(metas_texto)
        linhas.append("")

    parcelas_texto = gerar_analise_parcelas_futuras(ano_mes)
    if parcelas_texto:
        linhas.append(parcelas_texto)
        linhas.append("")

    linhas.append("Leitura do assessor:")
    if saldo < 0:
        linhas.append("- O mês fica negativo considerando entradas e compromissos previstos. Revise fixos, parcelas ou receitas esperadas.")
    elif entradas_programadas > 0:
        linhas.append("- O mês está projetado com receitas previstas cadastradas. Confira se elas realmente vão cair.")
    elif compromissos_mes > despesas_lancadas:
        linhas.append("- Seu maior peso está nos compromissos programados, não nos gastos avulsos.")
    else:
        linhas.append("- O mês está controlado, desde que os compromissos e entradas estejam completos no cadastro.")

    return "\n".join(linhas)


def gerar_analise_metas_mes(ano_mes: str):
    metas = listar_metas()
    if not metas:
        return ""
    linhas = ["Metas:"]
    for meta in metas:
        categoria = meta["categoria"]
        limite = meta["valor"]
        gasto = total_por_categoria_mes(ano_mes, categoria)
        percentual = (gasto / limite) * 100 if limite > 0 else 0
        restante = limite - gasto
        if restante < 0:
            status = f"acima da meta em {formatar_moeda(abs(restante))}"
        elif percentual >= 80:
            status = f"atenção, já usou {percentual:.1f}% da meta"
        else:
            status = f"dentro da meta, restam {formatar_moeda(restante)}"
        linhas.append(f"- {categoria}: {formatar_moeda(gasto)} de {formatar_moeda(limite)} — {status}")
    return "\n".join(linhas)


def gerar_analise_parcelas_futuras(ano_mes: str):
    meses_futuros = calcular_parcelas_futuras_por_mes(ano_mes)
    if not meses_futuros:
        return ""
    linhas = ["Parcelas/compromissos futuros já previstos:"]
    for mes in sorted(meses_futuros.keys())[:6]:
        linhas.append(f"- {mes}: {formatar_moeda(meses_futuros[mes])}")
    return "\n".join(linhas)


def exportar_csv_periodo(data_inicio: str, data_fim: str):
    data_inicio = validar_data_iso(data_inicio)
    data_fim = validar_data_iso(data_fim)

    if not data_inicio or not data_fim:
        return (
            "📤 Exportação CSV\n\n"
            "Período inválido.\n\n"
            "Use assim:\n"
            "exportar csv 2026-06-01 2030-12-30"
        )

    if data_inicio > data_fim:
        data_inicio, data_fim = data_fim, data_inicio

    itens = buscar_itens_financeiros_periodo(data_inicio, data_fim)

    if not itens:
        return (
            f"📤 Exportação CSV — {formatar_periodo_visual(data_inicio, data_fim)}\n\n"
            "Não encontrei transações, compromissos ou entradas nesse período."
        )

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    nome_arquivo = f"financeiro_{data_inicio}_a_{data_fim}_{relogio.agora().strftime('%Y%m%d_%H%M%S_%f')}_{uuid.uuid4().hex[:8]}.csv"
    caminho = EXPORTS_DIR / nome_arquivo

    colunas = [
        "origem",
        "id",
        "data",
        "tipo",
        "valor",
        "categoria",
        "nome",
        "conta",
        "forma_pagamento",
        "parcela_atual",
        "parcelas_total",
        "ativo",
        "data_compra",
        "competencia_fatura",
    ]

    with caminho.open("w", newline="", encoding="utf-8-sig") as arquivo:
        writer = csv.writer(arquivo, delimiter=";")
        writer.writerow(colunas)

        for item in itens:
            writer.writerow(montar_linha_exportacao_unificada(item))

    total_entradas = sum(
        item["valor"] for item in itens
        if item.get("origem") == "entrada" or str(item.get("tipo", "")).startswith("receita") or str(item.get("tipo", "")).startswith("entrada")
    )
    total_saidas = sum(
        item["valor"] for item in itens
        if not (item.get("origem") == "entrada" or str(item.get("tipo", "")).startswith("receita") or str(item.get("tipo", "")).startswith("entrada"))
    )
    saldo = total_entradas - total_saidas

    por_origem = {}
    for item in itens:
        origem = item.get("origem") or "desconhecida"
        por_origem[origem] = por_origem.get(origem, 0) + 1

    origem_texto = ", ".join(f"{origem}: {qtd}" for origem, qtd in sorted(por_origem.items()))

    texto = "\n".join([
        f"📤 Exportação gerada — {formatar_periodo_visual(data_inicio, data_fim)}",
        "",
        bloco_total("Arquivo", [
            f"│ {'Itens exportados':<24} {len(itens):>14}",
            linha_valor("Entradas", total_entradas),
            linha_valor("Saídas", total_saidas),
            f"│ {'Saldo':<24} {formatar_status_saldo(saldo):>14}",
            f"│ {'Nome':<24} {nome_arquivo[-14:]:>14}",
        ]),
        "",
        f"Origem dos itens: {origem_texto}",
        "",
        "O arquivo CSV foi anexado nesta conversa.",
    ])

    return {"texto": texto, "arquivo": str(caminho)}


def exportar_csv_completo():
    periodo = descobrir_periodo_base_exportavel()

    if not periodo:
        return "📤 Exportação CSV\n\nNão encontrei transações, compromissos ou entradas na base."

    return exportar_csv_periodo(periodo[0], periodo[1])


def pedir_periodo_exportacao(sessao=None):
    _definir_pendencia(PENDENCIAS_EXPORTACAO, sessao, True)

    return "\n".join([
        "📤 Exportação CSV",
        "",
        "Informe o período que deseja exportar.",
        "",
        "Digite as duas datas no formato:",
        "2026-06-01 2030-12-30",
        "",
        "Também aceito:",
        "exportar csv 2026-06-01 2030-12-30",
        "exportar csv tudo",
    ])


def exportar_csv_mes(ano_mes: str):
    ano_mes = validar_ano_mes(ano_mes)
    if not ano_mes:
        return "📤 Exportação CSV\n\nMês inválido. Use o formato: exportar csv 2026-07"

    ultimo_dia = calendar.monthrange(int(ano_mes[:4]), int(ano_mes[5:7]))[1]
    data_inicio = f"{ano_mes}-01"
    data_fim = f"{ano_mes}-{ultimo_dia:02d}"

    return exportar_csv_periodo(data_inicio, data_fim)


BACKUPS_MANTER = 15


PREFIXO_BACKUP_DIARIO = "financeiro_backup"
# Backups feitos antes de cada exclusão têm rodízio próprio: muitas exclusões no
# mesmo dia não podem empurrar para fora o histórico diário.
PREFIXO_BACKUP_PRE_EXCLUSAO = "financeiro_preexclusao"


def listar_arquivos_backup(prefixo: str = PREFIXO_BACKUP_DIARIO):
    if not BACKUPS_DIR.exists():
        return []

    return sorted(
        BACKUPS_DIR.glob(f"{prefixo}_*.db"),
        key=lambda caminho: caminho.stat().st_mtime,
        reverse=True
    )


def remover_backups_antigos(manter: int = BACKUPS_MANTER, prefixo: str = PREFIXO_BACKUP_DIARIO):
    arquivos = listar_arquivos_backup(prefixo)
    removidos = []

    for caminho in arquivos[manter:]:
        try:
            caminho.unlink()
            removidos.append(caminho.name)
        except Exception:
            # Ex.: arquivo aberto por antivírus/sincronização. Fica para a próxima rodada.
            _LOG_CALCULOS.warning("Backup antigo não pôde ser removido: %s", caminho.name, exc_info=True)

    return removidos


def _validar_backup_sqlite(caminho: Path):
    with closing(sqlite3.connect(caminho)) as conn:
        resultado = conn.execute("PRAGMA quick_check").fetchone()
        if not resultado or resultado[0] != "ok":
            raise sqlite3.DatabaseError(f"backup inválido: {resultado}")
        tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        obrigatorias = {"transacoes", "compromissos", "fatura_movimentos"}
        faltantes = obrigatorias - tabelas
        if faltantes:
            raise sqlite3.DatabaseError(f"backup sem tabelas obrigatórias: {sorted(faltantes)}")


def criar_backup_db(prefixo: str = PREFIXO_BACKUP_DIARIO):
    if not DB_PATH.exists():
        return None, []

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = relogio.agora().strftime("%Y%m%d_%H%M%S_%f")
    nome_arquivo = f"{prefixo}_{timestamp}_{uuid.uuid4().hex[:8]}.db"
    caminho_backup = BACKUPS_DIR / nome_arquivo
    temporario = caminho_backup.with_suffix(".tmp")
    try:
        with closing(sqlite3.connect(DB_PATH)) as origem, closing(sqlite3.connect(temporario)) as destino:
            origem.execute("PRAGMA quick_check").fetchone()
            origem.backup(destino)
        _validar_backup_sqlite(temporario)
        temporario.replace(caminho_backup)
    except Exception:
        temporario.unlink(missing_ok=True)
        caminho_backup.unlink(missing_ok=True)
        raise
    removidos = remover_backups_antigos(BACKUPS_MANTER, prefixo)
    return caminho_backup, removidos


def criar_backup_pre_exclusao():
    """Backup obrigatório antes de apagar: devolve o caminho ou levanta erro.

    Quem chama deve abortar a exclusão se isto falhar (falha fechada).
    """
    caminho, _ = criar_backup_db(PREFIXO_BACKUP_PRE_EXCLUSAO)
    if not caminho:
        raise RuntimeError("banco de dados não encontrado para backup")
    return caminho


def existe_backup_diario_hoje(hoje=None):
    """True se já existe backup diário com data de hoje (relógio local)."""
    hoje = hoje or relogio.hoje(date)
    for caminho in listar_arquivos_backup(PREFIXO_BACKUP_DIARIO):
        if date.fromtimestamp(caminho.stat().st_mtime) == hoje:
            return True
    return False


def horas_desde_ultimo_backup_diario(agora=None):
    """Idade, em horas, do backup diário mais recente (None se não houver)."""
    arquivos = listar_arquivos_backup(PREFIXO_BACKUP_DIARIO)
    if not arquivos:
        return None
    agora = agora if agora is not None else relogio.agora().timestamp()
    return max(0.0, (agora - arquivos[0].stat().st_mtime) / 3600)


def gerar_backup():
    from backup_externo import linha_status as linha_status_externo
    caminho_backup, removidos = criar_backup_db()

    if not caminho_backup:
        return "💾 Backup\n\nBanco de dados ainda não existe. Não há backup para gerar."

    nome_arquivo = caminho_backup.name

    texto = "\n".join([
        "💾 Backup gerado",
        "",
        bloco_total("Arquivo", [
            f"│ {'Nome':<24} {nome_arquivo[-14:]:>14}",
            f"│ {'Tamanho':<24} {formatar_tamanho_bytes(caminho_backup.stat().st_size):>14}",
            f"│ {'Rotação':<24} {('últimos ' + str(BACKUPS_MANTER)):>14}",
        ]),
        "",
        f"Backups antigos removidos: {len(removidos)}",
        linha_status_externo(),
    ])

    return {"texto": texto, "arquivo": str(caminho_backup)}


def gerar_backup_automatico():
    caminho_backup, removidos = criar_backup_db()

    if not caminho_backup:
        return "💾 Backup automático: banco de dados ainda não existe."

    from backup_externo import gerar_se_configurado  # cópia criptografada fora do PC (OneDrive), se configurada
    return (f"💾 Backup automático gerado ({caminho_backup.name}, mantendo últimos {BACKUPS_MANTER}, removidos {len(removidos)})"
            + gerar_se_configurado(caminho_backup))


def gerar_alerta_meta_lancamento(transacao: dict):
    if not transacao or transacao.get("tipo") != "despesa":
        return ""

    categoria = (transacao.get("categoria") or "").strip()

    if not categoria:
        return ""

    meta = buscar_meta_por_categoria(categoria)

    if not meta:
        return ""

    limite = meta["valor"] or 0

    if limite <= 0:
        return ""

    ano_mes = str(transacao.get("data") or relogio.hoje(date).isoformat())[:7]
    gasto_atual = total_por_categoria_mes(ano_mes, categoria)
    valor_lancamento = transacao.get("valor") or 0
    gasto_anterior = max(0, gasto_atual - valor_lancamento)

    if gasto_atual <= limite:
        return ""

    excedente = gasto_atual - limite

    if gasto_anterior <= limite:
        titulo = "⚠️ Meta estourada agora"
    else:
        titulo = "⚠️ Meta continua estourada"

    return "\n".join([
        "",
        titulo,
        "",
        bloco_total(categoria, [
            linha_valor("Meta", limite),
            linha_valor("Gasto atual", gasto_atual),
            linha_valor("Excedente", excedente),
        ]),
    ])



def registrar_transacao_unica(transacao: dict):
    if eh_credito(transacao) and precisa_escolher(transacao) and not transacao.get('competencia_fatura'):
        return ('Esta compra precisa da escolha da fatura. Abra Registrar no Telegram e informe a compra; '
                'o assessor perguntara o mes antes de salvar. Nenhum lancamento foi gravado.')
    transacao_id = inserir_transacao(transacao)
    tipo_valor = "entrada" if transacao["tipo"] == "receita" else "saida"
    titulo = "✅ Receita registrada" if transacao["tipo"] == "receita" else "✅ Despesa registrada"
    alerta_meta = gerar_alerta_meta_lancamento(transacao)

    linhas = [
        titulo,
        "",
        formatar_item_card(
            identificador=f"#{transacao_id}",
            data_item=transacao["data"],
            valor=transacao["valor"],
            categoria=transacao["categoria"],
            nome=transacao.get("descricao") or transacao.get("mensagem_original") or "Lançamento",
            conta=transacao.get("conta") or "Não informada",
            forma=transacao.get("forma_pagamento") or "não informada",
            tipo_valor=tipo_valor,
        ),
    ]

    if alerta_meta:
        linhas.append(alerta_meta)

    linhas.extend([
        "",
        "Ações rápidas:",
        f"corrigir {transacao_id} para 42,90",
        f"mudar {transacao_id} para Nova Categoria",
        f"apagar {transacao_id}",
    ])

    return "\n".join(linhas)


def registrar_compra_parcelada(transacao: dict):
    if transacao.get('competencia_fatura'):
        return 'Use Registrar no Telegram para confirmar o parcelamento com a fatura escolhida. Nenhum lancamento foi gravado.'
    if eh_credito(transacao) and precisa_escolher(transacao) and not transacao.get('competencia_fatura'):
        return ('Esta compra precisa da escolha da fatura. Abra Registrar no Telegram e informe a compra; '
                'o assessor perguntara o mes antes de salvar. Nenhum lancamento foi gravado.')
    parcelas_total = transacao["parcelas_total"]
    valor_total = transacao["valor"]
    valor_parcela = round(valor_total / parcelas_total, 2)
    data_base = date.fromisoformat(transacao["data"])

    # Mesma regra de sempre (n-1 parcelas iguais e a última com o resíduo), mas em
    # centavos inteiros e validada antes de gravar: valores pequenos demais para o
    # número de parcelas geravam parcelas de R$ 0,00 ou negativas.
    try:
        total_centavos = int(parse_money(valor_total) * 100)
        parcela_centavos = int(parse_money(valor_parcela, allow_negative=True) * 100)
    except ValueError:
        return "Valor inválido para parcelamento. Nenhum lançamento foi gravado."
    ultima_centavos = total_centavos - parcela_centavos * (parcelas_total - 1)
    if parcela_centavos < 1 or ultima_centavos < 1:
        return (f"Não dá para dividir {formatar_moeda(valor_total)} em {parcelas_total}x: "
                "cada parcela precisa ter pelo menos R$ 0,01. Nenhum lançamento foi gravado.")

    parcelas = []
    for parcela_atual in range(1, parcelas_total + 1):
        data_parcela = somar_meses(data_base, parcela_atual - 1)
        centavos = ultima_centavos if parcela_atual == parcelas_total else parcela_centavos
        valor_atual = centavos / 100

        descricao_parcela = f"{transacao['descricao']} ({parcela_atual}/{parcelas_total})"
        transacao_parcela = {
            "data": data_parcela.isoformat(), "tipo": "despesa", "valor": valor_atual,
            "categoria": transacao["categoria"], "descricao": descricao_parcela,
            "conta": transacao.get("conta"), "forma_pagamento": transacao.get("forma_pagamento") or "crédito",
            "mensagem_original": transacao.get("mensagem_original"), "parcelamento_id": None,
            "parcela_atual": parcela_atual, "parcelas_total": parcelas_total,
            "valor_total_parcelamento": valor_total
        }
        parcelas.append(transacao_parcela)

    # Tudo numa transação: uma falha no meio não deixa parcelas soltas.
    ids_criados = inserir_parcelamento_atomico(parcelas)
    parcelamento_id = ids_criados[0]

    primeiro_mes = date.fromisoformat(transacao["data"]).strftime("%Y-%m")
    ultimo_mes = somar_meses(data_base, parcelas_total - 1).strftime("%Y-%m")
    ids_resumo = f"{ids_criados[0]} até {ids_criados[-1]}" if len(ids_criados) > 1 else str(ids_criados[0])

    alerta_meta = gerar_alerta_meta_lancamento({
        **transacao,
        "valor": valor_parcela,
        "data": transacao["data"],
        "tipo": "despesa",
    })

    linhas = [
        "💳 Compra parcelada registrada",
        "",
        bloco_total("Parcelamento", [
            f"│ {'ID':<24} {('#P' + str(parcelamento_id)):>14}",
            linha_valor("Valor total", valor_total),
            f"│ {'Parcelas':<24} {(str(parcelas_total) + 'x'):>14}",
            linha_valor("Valor médio", valor_parcela),
            f"│ {'Período':<24} {(formatar_ano_mes_visual(primeiro_mes) + ' a ' + formatar_ano_mes_visual(ultimo_mes)):>14}",
            f"│ {'IDs criados':<24} {ids_resumo:>14}",
        ]),
        "",
        formatar_item_card(
            identificador=f"#P{parcelamento_id}",
            data_item=transacao["data"],
            valor=valor_total,
            categoria=transacao["categoria"],
            nome=transacao.get("descricao") or "Compra parcelada",
            conta=transacao.get("conta") or "Não informada",
            forma=transacao.get("forma_pagamento") or "crédito",
            extra=f"{parcelas_total}x de aproximadamente {formatar_moeda(valor_parcela)}",
            tipo_valor="saida",
        ),
    ]

    if alerta_meta:
        linhas.append(alerta_meta)

    linhas.extend([
        "",
        "Ações rápidas:",
        f"parcelas P{parcelamento_id}",
        f"apagar parcelamento P{parcelamento_id}",
    ])

    return "\n".join(linhas)


def buscar_transacao_detalhada_formatado(transacao_id: int):
    transacao = buscar_transacao_por_id(transacao_id)

    if not transacao:
        return f"🔎 Lançamento\n\nNão encontrei lançamento #{transacao_id}."

    tipo_valor = "entrada" if transacao["tipo"] == "receita" else "saida"
    parcela_atual, parcelas_total = obter_info_parcela(transacao)
    extra = ""

    if parcela_atual and parcelas_total:
        extra = f"Parcela {parcela_atual}/{parcelas_total}"

    return "\n".join([
        "🔎 Lançamento",
        "",
        formatar_item_card(
            identificador=f"#{transacao['id']}",
            data_item=transacao["data"],
            valor=transacao["valor"],
            categoria=transacao["categoria"],
            nome=transacao["descricao"] or "Sem descrição",
            conta=transacao["conta"] or "Não informada",
            forma=transacao["forma_pagamento"] or "não informada",
            extra=extra,
            tipo_valor=tipo_valor,
        ),
        "",
        "Ações disponíveis pelos botões abaixo.",
    ])



TRANSAÇÕES_POR_PAGINA = 5


def normalizar_busca_texto(valor: str):
    texto = (valor or "").lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"\s+", " ", texto)
    return texto


def obter_valor_busca(transacao, campo: str):
    try:
        return transacao[campo]
    except Exception:
        try:
            return transacao.get(campo)
        except Exception:
            return None


def transacao_contem_termo(transacao, termo: str):
    termo_norm = normalizar_busca_texto(termo)

    if not termo_norm:
        return True

    valor_num = converter_valor_texto(termo_norm)

    if valor_num is not None:
        try:
            if round(float(obter_valor_busca(transacao, "valor") or 0), 2) == round(valor_num, 2):
                return True
        except Exception:
            pass

    campos = [
        "descricao",
        "categoria",
        "conta",
        "forma_pagamento",
        "tipo",
        "data",
        "mensagem_original",
    ]

    for campo in campos:
        valor = obter_valor_busca(transacao, campo)
        if termo_norm in normalizar_busca_texto(str(valor or "")):
            return True

    return False


def listar_transacoes_filtradas(termo: str | None = None):
    transacoes = list(buscar_todas_transacoes())
    transacoes.sort(key=lambda t: int(t["id"]), reverse=True)

    termo_limpo = normalizar_busca_texto(termo or "")

    if not termo_limpo:
        return transacoes

    hoje = relogio.hoje(date).isoformat()
    ano_mes_atual = relogio.hoje(date).strftime("%Y-%m")

    aliases = {
        "hoje": lambda t: str(t["data"]) == hoje,
        "dia": lambda t: str(t["data"]) == hoje,
        "mes": lambda t: str(t["data"]).startswith(ano_mes_atual),
        "mês": lambda t: str(t["data"]).startswith(ano_mes_atual),
        "este mes": lambda t: str(t["data"]).startswith(ano_mes_atual),
        "este mês": lambda t: str(t["data"]).startswith(ano_mes_atual),
        "entrada": lambda t: t["tipo"] == "receita",
        "entradas": lambda t: t["tipo"] == "receita",
        "receita": lambda t: t["tipo"] == "receita",
        "receitas": lambda t: t["tipo"] == "receita",
        "despesa": lambda t: t["tipo"] == "despesa",
        "despesas": lambda t: t["tipo"] == "despesa",
        "saida": lambda t: t["tipo"] == "despesa",
        "saída": lambda t: t["tipo"] == "despesa",
        "saidas": lambda t: t["tipo"] == "despesa",
        "saídas": lambda t: t["tipo"] == "despesa",
        "credito": lambda t: "credito" in normalizar_busca_texto(t["forma_pagamento"] or ""),
        "crédito": lambda t: "credito" in normalizar_busca_texto(t["forma_pagamento"] or ""),
        "debito": lambda t: "debito" in normalizar_busca_texto(t["forma_pagamento"] or ""),
        "débito": lambda t: "debito" in normalizar_busca_texto(t["forma_pagamento"] or ""),
        "pix": lambda t: "pix" in normalizar_busca_texto(t["forma_pagamento"] or "") or "pix" in normalizar_busca_texto(t["conta"] or ""),
    }

    if termo_limpo in aliases:
        return [t for t in transacoes if aliases[termo_limpo](t)]

    if re.match(r"^\d{4}-\d{2}$", termo_limpo):
        return [t for t in transacoes if str(t["data"]).startswith(termo_limpo)]

    return [t for t in transacoes if transacao_contem_termo(t, termo_limpo)]


def formatar_linha_transacao_visual(indice_visual: int, transacao):
    descricao = transacao["descricao"] or "Sem descrição"
    categoria = transacao["categoria"] or "Sem categoria"
    conta = transacao["conta"] or "Não informada"
    forma = transacao["forma_pagamento"] or "não informada"
    tipo = "entrada" if transacao["tipo"] == "receita" else "saída"
    sinal = "🟢" if transacao["tipo"] == "receita" else "💸"
    parcela_atual, parcelas_total = obter_info_parcela(transacao)
    extra = f" · {parcela_atual}/{parcelas_total}" if parcela_atual and parcelas_total else ""

    return [
        f"{indice_visual}) {sinal} {descricao}",
        f"   {formatar_moeda(transacao['valor'])} · {categoria}",
        f"   {conta} · {forma}{extra}",
        f"   ID técnico: #{transacao['id']} · {tipo}",
    ]


def montar_lista_transacoes_paginada(
    transacoes,
    titulo: str,
    pagina: int = 1,
    por_pagina: int = TRANSAÇÕES_POR_PAGINA,
):
    total = len(transacoes)

    if total == 0:
        return f"{titulo}\n\nNão encontrei lançamentos para esse filtro."

    total_paginas = max(1, math.ceil(total / por_pagina))
    pagina = max(1, min(int(pagina or 1), total_paginas))

    inicio = (pagina - 1) * por_pagina
    fim = inicio + por_pagina
    pagina_itens = transacoes[inicio:fim]

    linhas = [
        titulo,
        f"Página {pagina} de {total_paginas} · {total} lançamento(s)",
        "",
        "Toque em um número para abrir, corrigir ou apagar.",
    ]

    for indice_visual, transacao in enumerate(pagina_itens, start=1):
        linhas.append("")
        linhas.extend(formatar_linha_transacao_visual(indice_visual, transacao))

    return "\n".join(linhas)


def listar_ultimas_paginado(pagina: int = 1, termo: str | None = None):
    transacoes = listar_transacoes_filtradas(termo)

    if termo:
        titulo = f"📌 Últimas transações — {termo}"
    else:
        titulo = "📌 Últimas transações"

    return montar_lista_transacoes_paginada(transacoes, titulo, pagina)


def buscar_transacoes_formatado(termo: str, pagina: int = 1):
    termo = (termo or "").strip()

    if not termo:
        return (
            "🔎 Buscar lançamentos\n\n"
            "Envie o que quer encontrar.\n\n"
            "Exemplos:\n"
            "buscar uber\n"
            "buscar mercado pago\n"
            "buscar 92,50\n"
            "buscar transporte\n"
            "buscar 2026-06"
        )

    transacoes = listar_transacoes_filtradas(termo)
    titulo = f"🔎 Busca: {termo}"

    return montar_lista_transacoes_paginada(transacoes, titulo, pagina)


def listar_ultimas(limite: int = 10):
    # Mantém compatibilidade com chamadas antigas, mas agora usa paginação.
    return listar_ultimas_paginado(1)


def apagar_ultimo():
    try:
        transacao = apagar_ultima_transacao()
    except ExclusaoParcialParcelamentoError as exc:
        return str(exc)
    if not transacao:
        return "🗑️ Apagar último\n\nNão encontrei nenhuma transação para apagar."

    tipo_valor = "entrada" if transacao["tipo"] == "receita" else "saida"

    return "\n".join([
        "🗑️ Última transação apagada",
        "",
        formatar_item_card(
            identificador=f"#{transacao['id']}",
            data_item=transacao["data"],
            valor=transacao["valor"],
            categoria=transacao["categoria"],
            nome=transacao["descricao"] or "Sem descrição",
            conta=transacao["conta"] or "Não informada",
            forma=transacao["forma_pagamento"] or "não informada",
            tipo_valor=tipo_valor,
        ),
    ])


def gerar_resumo_mes(ano_mes: str | None = None):
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")

    totais, categorias = resumo_mes(ano_mes)
    dados = obter_metricas_resultado_mes(ano_mes)

    receitas_lancadas = 0
    despesas_lancadas = 0

    for item in totais:
        if item["tipo"] == "receita":
            receitas_lancadas = item["total"] or 0
        elif item["tipo"] == "despesa":
            despesas_lancadas = item["total"] or 0

    # Pagamento de fatura não é compromisso de gasto (B1).
    compromissos_mes = sum(item["valor"] for item in remover_liquidacoes_fatura(projetar_pagamentos_mes(ano_mes, incluir_transacoes=False)))

    linhas = [
        f"📊 Resumo — {formatar_ano_mes_visual(ano_mes)}",
        "",
        bloco_heranca_mes_anterior(dados),
        "",
        bloco_resultado_mes(dados),
        "",
        bloco_caixa_acumulado(dados),
        "",
        bloco_total("Referência dos lançamentos", [
            linha_valor("Receitas lançadas", receitas_lancadas),
            linha_valor("Despesas lançadas", despesas_lancadas),
            linha_valor("Compromissos esperados", compromissos_mes),
        ]),
    ]

    if categorias:
        linhas.extend(["", "🏷 Gastos lançados por categoria"])
        total_categorias = sum(c["total"] or 0 for c in categorias)
        for indice, c in enumerate(categorias[:8], start=1):
            valor = c["total"] or 0
            linhas.extend([
                "",
                f"{indice:02d}. {c['categoria']}",
                f"    {formatar_moeda(valor)} · {formatar_percentual(valor, total_categorias)}",
                f"    {formatar_barra_percentual(valor, total_categorias)}",
            ])
    else:
        linhas.extend(["", "🏷 Gastos lançados por categoria", "Nenhuma despesa registrada."])

    metas_texto = gerar_bloco_metas_mes(ano_mes)
    if metas_texto:
        linhas.append("")
        linhas.append(metas_texto)

    return "\n".join(linhas)


def gerar_saldo_mes(ano_mes: str | None = None):
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")

    receitas_lancadas = total_por_tipo_mes(ano_mes, "receita")
    despesas_lancadas = total_por_tipo_mes(ano_mes, "despesa")
    entradas_programadas = sum(item["valor"] for item in projetar_entradas_mes(ano_mes, incluir_transacoes=False))
    receitas_totais = sum(item["valor"] for item in projetar_entradas_mes(ano_mes, incluir_transacoes=True))
    # Pagamento de fatura não é despesa do mês (B1), como em fechamento/meu mês;
    # estornos seguem abatendo.
    compromissos_mes = sum(item["valor"] for item in remover_liquidacoes_fatura(projetar_pagamentos_mes(ano_mes, incluir_transacoes=False)))
    despesas_totais = sum(item["valor"] for item in remover_liquidacoes_fatura(projetar_pagamentos_mes(ano_mes, incluir_transacoes=True)))
    saldo = receitas_totais - despesas_totais

    return "\n".join([
        f"💰 Saldo — {formatar_ano_mes_visual(ano_mes)}",
        "",
        bloco_total("Receitas", [
            linha_valor("Lançadas", receitas_lancadas),
            linha_valor("Previstas", entradas_programadas),
            linha_valor("Total", receitas_totais),
        ]),
        "",
        bloco_total("Saídas", [
            linha_valor("Lançadas", despesas_lancadas),
            linha_valor("Compromissos", compromissos_mes),
            linha_valor("Total", despesas_totais),
        ]),
        "",
        f"Saldo projetado: {formatar_status_saldo(saldo)}",
    ])


def gerar_gastos_hoje():
    return gerar_painel_hoje_ux()


def consultar_categoria(categoria: str, ano_mes: str | None = None):
    if ano_mes is None:
        ano_mes = relogio.hoje(date).strftime("%Y-%m")
    categoria_normalizada = categoria.title()
    total = total_por_categoria_mes(ano_mes, categoria_normalizada)
    meta = buscar_meta_por_categoria(categoria_normalizada)
    resposta = ["🔎 Consulta por categoria", "", f"Mês: {ano_mes}", f"Categoria: {categoria_normalizada}", f"Total gasto: {formatar_moeda(total)}"]
    if meta:
        limite = meta["valor"]
        percentual = (total / limite) * 100 if limite > 0 else 0
        restante = limite - total
        resposta.append(f"Meta: {formatar_moeda(limite)}")
        resposta.append(f"Uso da meta: {percentual:.1f}%")
        if restante >= 0:
            resposta.append(f"Restante: {formatar_moeda(restante)}")
        else:
            resposta.append(f"Acima da meta: {formatar_moeda(abs(restante))}")
    return "\n".join(resposta)


def definir_meta_formatado(categoria: str, valor: float):
    meta = definir_meta(categoria, valor)
    return "\n".join([
        "🎯 Meta definida",
        "",
        bloco_total(meta["categoria"], [
            linha_valor("Limite mensal", meta["valor"]),
        ]),
        "",
        "Para acompanhar:",
        "metas",
    ])


def listar_metas_formatado():
    metas = listar_metas()
    if not metas:
        return "Você ainda não definiu metas.\n\nExemplo:\nmeta mercado 800"
    ano_mes = relogio.hoje(date).strftime("%Y-%m")
    linhas = [f"🎯 Metas cadastradas ({ano_mes})\n"]
    for meta in metas:
        categoria = meta["categoria"]
        limite = meta["valor"]
        gasto = total_por_categoria_mes(ano_mes, categoria)
        percentual = (gasto / limite) * 100 if limite > 0 else 0
        restante = limite - gasto
        status = f"restam {formatar_moeda(restante)}" if restante >= 0 else f"acima em {formatar_moeda(abs(restante))}"
        linhas.append(f"- {categoria}: {formatar_moeda(gasto)} de {formatar_moeda(limite)} ({percentual:.1f}%) — {status}")
    return "\n".join(linhas)


def apagar_meta_formatado(categoria: str):
    meta = apagar_meta_por_categoria(categoria)
    if not meta:
        return f"🗑️ Apagar meta\n\nNão encontrei meta para a categoria: {categoria}"

    return "\n".join([
        "🗑️ Meta apagada",
        "",
        bloco_total(meta["categoria"], [
            linha_valor("Valor removido", meta["valor"]),
        ]),
    ])


def gerar_bloco_metas_mes(ano_mes: str):
    metas = listar_metas()
    if not metas:
        return ""
    linhas = ["🎯 Metas do mês:"]
    for meta in metas:
        categoria = meta["categoria"]
        limite = meta["valor"]
        gasto = total_por_categoria_mes(ano_mes, categoria)
        percentual = (gasto / limite) * 100 if limite > 0 else 0
        restante = limite - gasto
        status = f"restam {formatar_moeda(restante)}" if restante >= 0 else f"acima em {formatar_moeda(abs(restante))}"
        linhas.append(f"- {categoria}: {formatar_moeda(gasto)} de {formatar_moeda(limite)} ({percentual:.1f}%) — {status}")
    return "\n".join(linhas)


def mudar_categoria_ultimo(nova_categoria: str):
    transacao = atualizar_categoria_ultima_transacao(nova_categoria)
    if not transacao:
        return "✏️ Categoria\n\nNão encontrei nenhuma transação para atualizar."

    tipo_valor = "entrada" if transacao["tipo"] == "receita" else "saida"

    return "\n".join([
        "✏️ Categoria atualizada no último lançamento",
        "",
        formatar_item_card(
            identificador=f"#{transacao['id']}",
            data_item=transacao["data"],
            valor=transacao["valor"],
            categoria=transacao["categoria"],
            nome=transacao["descricao"] or "Sem descrição",
            conta=transacao["conta"] or "Não informada",
            forma=transacao["forma_pagamento"] or "não informada",
            tipo_valor=tipo_valor,
        ),
    ])


def apagar_por_id(transacao_id: int):
    try:
        transacao = apagar_transacao_por_id(transacao_id)
    except ExclusaoParcialParcelamentoError as exc:
        return str(exc)
    if not transacao:
        return f"🗑️ Apagar transação\n\nNão encontrei nenhuma transação com ID #{transacao_id}."

    tipo_valor = "entrada" if transacao["tipo"] == "receita" else "saida"

    return "\n".join([
        "🗑️ Transação apagada",
        "",
        formatar_item_card(
            identificador=f"#{transacao['id']}",
            data_item=transacao["data"],
            valor=transacao["valor"],
            categoria=transacao["categoria"],
            nome=transacao["descricao"] or "Sem descrição",
            conta=transacao["conta"] or "Não informada",
            forma=transacao["forma_pagamento"] or "não informada",
            tipo_valor=tipo_valor,
        ),
    ])


def apagar_por_faixa(id_inicio: int, id_fim: int):
    try:
        transacoes = apagar_transacoes_por_intervalo_ids(id_inicio, id_fim)
    except ExclusaoParcialParcelamentoError as exc:
        return str(exc)
    if not transacoes:
        return f"🗑️ Apagar faixa\n\nNão encontrei transações entre #{id_inicio} e #{id_fim}."

    ids = [str(t["id"]) for t in transacoes]
    total = sum(t["valor"] for t in transacoes)

    return "\n".join([
        "🗑️ Transações apagadas em faixa",
        "",
        bloco_total("Resumo", [
            f"│ {'IDs':<24} {(str(id_inicio) + ' a ' + str(id_fim)):>14}",
            f"│ {'Quantidade':<24} {len(transacoes):>14}",
            linha_valor("Valor removido", total),
        ]),
        "",
        f"IDs apagados: {', '.join(ids)}",
    ])


def mudar_categoria_por_id(transacao_id: int, nova_categoria: str):
    transacao = atualizar_categoria_por_id(transacao_id, nova_categoria)
    if not transacao:
        return f"✏️ Categoria\n\nNão encontrei nenhuma transação com ID #{transacao_id}."

    tipo_valor = "entrada" if transacao["tipo"] == "receita" else "saida"

    return "\n".join([
        "✏️ Categoria atualizada",
        "",
        formatar_item_card(
            identificador=f"#{transacao['id']}",
            data_item=transacao["data"],
            valor=transacao["valor"],
            categoria=transacao["categoria"],
            nome=transacao["descricao"] or "Sem descrição",
            conta=transacao["conta"] or "Não informada",
            forma=transacao["forma_pagamento"] or "não informada",
            tipo_valor=tipo_valor,
        ),
    ])


def corrigir_conta_por_id(transacao_id: int, nova_conta: str):
    nova_conta = (nova_conta or "").strip()

    if not nova_conta:
        return "🏦 Conta\n\nInforme a nova conta. Exemplo: corrigir conta 7 para BTG"

    transacao = atualizar_conta_por_id(transacao_id, nova_conta.title())
    if not transacao:
        return f"🏦 Conta\n\nNão encontrei nenhuma transação com ID #{transacao_id}."

    tipo_valor = "entrada" if transacao["tipo"] == "receita" else "saida"

    return "\n".join([
        "🏦 Conta atualizada",
        "",
        formatar_item_card(
            identificador=f"#{transacao['id']}",
            data_item=transacao["data"],
            valor=transacao["valor"],
            categoria=transacao["categoria"],
            nome=transacao["descricao"] or "Sem descrição",
            conta=transacao["conta"] or "Não informada",
            forma=transacao["forma_pagamento"] or "não informada",
            tipo_valor=tipo_valor,
        ),
    ])


def corrigir_forma_por_id(transacao_id: int, nova_forma: str):
    nova_forma = (nova_forma or "").strip()

    if not nova_forma:
        return "💳 Forma\n\nInforme a nova forma. Exemplo: corrigir forma 10 para transferência"

    mapa_formas = {
        "transferencia": "transferência",
        "transferência": "transferência",
        "transf": "transferência",
        "pix": "pix",
        "debito": "débito",
        "débito": "débito",
        "credito": "crédito",
        "crédito": "crédito",
        "cartao": "crédito",
        "cartão": "crédito",
        "dinheiro": "dinheiro",
        "cash": "dinheiro",
    }

    forma_normalizada = normalizar_texto(nova_forma)
    nova_forma_formatada = mapa_formas.get(forma_normalizada, nova_forma.lower())

    transacao = atualizar_forma_por_id(transacao_id, nova_forma_formatada)
    if not transacao:
        return f"💳 Forma\n\nNão encontrei nenhuma transação com ID #{transacao_id}."

    tipo_valor = "entrada" if transacao["tipo"] == "receita" else "saida"

    return "\n".join([
        "💳 Forma atualizada",
        "",
        formatar_item_card(
            identificador=f"#{transacao['id']}",
            data_item=transacao["data"],
            valor=transacao["valor"],
            categoria=transacao["categoria"],
            nome=transacao["descricao"] or "Sem descrição",
            conta=transacao["conta"] or "Não informada",
            forma=transacao["forma_pagamento"] or "não informada",
            tipo_valor=tipo_valor,
        ),
    ])


def mudar_categoria_por_faixa(id_inicio: int, id_fim: int, nova_categoria: str):
    transacoes = atualizar_categoria_por_intervalo_ids(id_inicio, id_fim, nova_categoria)
    if not transacoes:
        return f"✏️ Categoria em faixa\n\nNão encontrei transações entre #{id_inicio} e #{id_fim}."

    return "\n".join([
        "✏️ Categoria atualizada em faixa",
        "",
        bloco_total("Resumo", [
            f"│ {'IDs':<24} {(str(id_inicio) + ' a ' + str(id_fim)):>14}",
            f"│ {'Nova categoria':<24} {nova_categoria[:14]:>14}",
            f"│ {'Atualizadas':<24} {len(transacoes):>14}",
        ]),
    ])


def corrigir_valor_por_id(transacao_id: int, novo_valor: float):
    transacao = atualizar_valor_por_id(transacao_id, novo_valor)
    if not transacao:
        return f"💵 Corrigir valor\n\nNão encontrei nenhuma transação com ID #{transacao_id}."

    tipo_valor = "entrada" if transacao["tipo"] == "receita" else "saida"

    linhas = [
        "💵 Valor atualizado",
        "",
        formatar_item_card(
            identificador=f"#{transacao['id']}",
            data_item=transacao["data"],
            valor=transacao["valor"],
            categoria=transacao["categoria"],
            nome=transacao["descricao"] or "Sem descrição",
            conta=transacao["conta"] or "Não informada",
            forma=transacao["forma_pagamento"] or "não informada",
            tipo_valor=tipo_valor,
        ),
    ]
    if row_get(transacao, "parcelamento_id") is not None and row_get(transacao, "valor_total_parcelamento") is not None:
        linhas += ["", f"Total do parcelamento P{transacao['parcelamento_id']} atualizado para "
                       f"{formatar_moeda(float(transacao['valor_total_parcelamento']))}."]
    return "\n".join(linhas)

# A herança é avaliada em ordem cronológica, sem recursão limitada a 36 meses.
# O memo vive apenas durante uma consulta; gravações seguintes não veem cache velho.
from contextvars import ContextVar as _ContextVarHeranca
_CONTEXTO_HERANCA = _ContextVarHeranca('assessor_heranca', default=None)


def _avaliar_heranca(ano_mes, conta=None, tipo='saldo'):
    ano_mes = validar_ano_mes(ano_mes)
    if not ano_mes:
        raise ValueError('Mês inválido. Use AAAA-MM.')
    contexto = _CONTEXTO_HERANCA.get()
    chave = (tipo, ano_mes, conta if tipo=='saldo' else None)
    if contexto is not None:
        if chave not in contexto['memo']:
            if ano_mes >= contexto['inicio']:
                raise ValueError('Dependência circular na herança do saldo; nenhum valor foi presumido.')
            contexto['memo'][chave] = (_calcular_saldo_mensal_etapa(ano_mes,conta,False)
                                       if tipo=='saldo' else _calcular_caixa_por_conta_etapa(ano_mes,False))
        return contexto['memo'][chave]
    inicio = min(obter_primeiro_mes_relevante(ano_mes), ano_mes)
    # Desempenho (Onda 2): dentro de uma consulta (contexto_consulta), a cadeia
    # já avaliada a partir do mesmo ``inicio`` é reaproveitada pelas chamadas
    # seguintes, em vez de recalcular todos os meses anteriores a cada tela.
    # O memo vive só durante a consulta, como o restante do consulta_cache.
    memos = _namespace_consulta('avaliar_heranca')
    memo = memos.setdefault(inicio, {}) if memos is not None else {}
    contexto = {'inicio':inicio, 'memo':memo}
    token = _CONTEXTO_HERANCA.set(contexto)
    try:
        for mes in gerar_meses_entre(inicio,ano_mes):
            herdar = mes != inicio
            if ('saldo',mes,None) not in memo:
                geral = _calcular_saldo_mensal_etapa(mes,None,herdar)
                if not geral.get('saldo_herdado_auto'):
                    geral['ano_mes_ancora_saldo'] = mes if geral.get('saldo_configurado') else None
                else:
                    anterior = memo.get(('saldo',obter_mes_anterior(mes),None),{})
                    geral['ano_mes_ancora_saldo'] = anterior.get('ano_mes_ancora_saldo')
                memo[('saldo',mes,None)] = geral
            if ('caixa',mes,None) not in memo:
                memo[('caixa',mes,None)] = _calcular_caixa_por_conta_etapa(mes,herdar)
            if conta and ('saldo',mes,conta) not in memo:
                memo[('saldo',mes,conta)] = _calcular_saldo_mensal_etapa(mes,conta,herdar)
        return memo[chave]
    finally:
        _CONTEXTO_HERANCA.reset(token)


@contextmanager
def _leitura_calculo():
    """Ponto de entrada de leitura dos cálculos de saldo (desempenho, Onda 2).

    Fora de uma tela (que já abre ``read_only_mode`` + ``contexto_consulta``),
    cada cálculo de herança abria milhares de conexões e refazia a cadeia de
    meses. Aqui, só durante esta chamada de leitura: uma conexão somente-leitura
    compartilhada e um cache de consulta efêmero. Nada sobrevive à chamada,
    então nenhuma gravação posterior enxerga valor velho. Se já houver modo de
    leitura ou contexto ativos, eles são reaproveitados.
    """
    import database as _database
    from contextlib import ExitStack
    with ExitStack() as pilha:
        if not _database._READ_ONLY.get() and Path(_database.DB_PATH).exists():
            pilha.enter_context(_database.read_only_mode())
        if _CONTEXTO_CONSULTA.get() is None:
            pilha.enter_context(contexto_consulta())
        yield


def calcular_saldo_mensal(ano_mes=None,conta=None,permitir_heranca=True,profundidade_heranca=0):
    ano_mes = ano_mes or relogio.hoje(date).strftime('%Y-%m')
    if not permitir_heranca:
        return _calcular_saldo_mensal_etapa(ano_mes,conta,False)
    with _leitura_calculo():
        return _consulta_cache(
            ('calcular_saldo_mensal', ano_mes, conta),
            lambda: _avaliar_heranca(ano_mes,conta,'saldo'),
        )


def calcular_caixa_por_conta_mes(ano_mes,permitir_heranca=True,profundidade=0):
    if not permitir_heranca:
        return _calcular_caixa_por_conta_etapa(ano_mes,False)
    with _leitura_calculo():
        return _consulta_cache(
            ('calcular_caixa_por_conta_mes', ano_mes),
            lambda: _avaliar_heranca(ano_mes,None,'caixa'),
        )

def processar_mensagem(texto, sessao=None):
    from conciliacao import ConciliacaoError
    try:
        return _processar_mensagem_core(texto,sessao=sessao)
    except ConciliacaoError as exc:
        return '⚠️ ' + str(exc)
