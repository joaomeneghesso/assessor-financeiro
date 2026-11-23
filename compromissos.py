from faturas_competencia import data_competencia, data_real_compra, competencia_transacao
import csv
import calendar
import logging
import os
import config
import re
import unicodedata
from money import parse_money_float
from categorias import inferir_categoria as inferir_categoria_canonica
from pagamentos_canonicos import (
    obter_conta_pagamento_efetiva,
    obter_destino_pagamento_efetivo,
)
from collections import defaultdict
from copy import deepcopy
from functools import lru_cache
from datetime import date, datetime
import relogio
from decimal import Decimal
from pathlib import Path
from consulta_cache import (
    cache_atual,
    chave_no_escopo,
    copia_defensiva,
    copia_rapida,
    namespace,
    obter_ou_calcular as _consulta_cache,
)

from database import (
    inserir_compromisso,
    listar_compromissos,
    buscar_compromisso_por_id,
    atualizar_valor_compromisso,
    atualizar_vencimento_compromisso,
    atualizar_campo_compromisso,
    definir_status_compromisso,
    apagar_compromisso_por_id,
    apagar_compromissos_por_origem,
    substituir_compromissos_por_origem,
    buscar_transacoes_por_mes,
    buscar_transacoes_por_competencia,
    listar_fatura_movimentos,
    obter_primeira_competencia_financeira,
)


IMPORTS_DIR = config.IMPORTS_DIR  # ancorada no projeto (config.py)

_LOG = logging.getLogger(__name__)

# RC3.0.14: contas fora da lista de bancos conhecidos só passam a ser tratadas
# como fatura de cartão a partir desta data (ISO). Padrão preservado; pode ser
# ajustada por ASSESSOR_CARTAO_NOVO_INICIO (AAAA-MM-DD).
def _data_inicio_cartoes_novos() -> str:
    padrao = "2026-09-01"
    valor = config.ler("ASSESSOR_CARTAO_NOVO_INICIO", "").strip()
    if not valor:
        return padrao
    try:
        return date.fromisoformat(valor).isoformat()
    except ValueError:
        _LOG.warning("ASSESSOR_CARTAO_NOVO_INICIO inválida (%r); usando %s", valor, padrao)
        return padrao


DATA_INICIO_CARTOES_NOVOS = _data_inicio_cartoes_novos()

CONTAS_PAGAMENTO = {
    "nubank": "Nubank",
    "mercado pago": "Mercado Pago",
    "btg": "BTG",
    "itaú": "Itaú",
    "itau": "Itaú",
    "lia": "Lia",
    "compras": "Compras",
    "inter": "Inter",
    "picpay": "PicPay",
    "c6": "C6",
    "xp": "XP",
}

FIXOS_KEYWORDS = [
    "icloud",
    "youtube",
    "premium",
    "internet",
    "banda larga",
    "condominio",
    "condomínio",
    "iptu",
    "iptv",
    "cnpj",
    "plano de celular",
    "celular plano",
    "wellhub",
    "academia",
    "aluguel",
    "luz",
    "energia",
    "água",
    "agua",
]

ELETRONICOS_KEYWORDS = ["dji", "drone", "iphone", "tablet", "headphone", "logitech", "airpods", "hub", "bateria", "lentes", "transceiver", "celular", "firestick"]


def formatar_moeda(valor: float):
    # Mesma regra de services.formatar_moeda (Decimal HALF_UP, sem -0,00).
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
    sinal = "+" if valor >= 0 else "-"
    return f"{sinal}{formatar_moeda(abs(valor))}"


def formatar_status_saldo(valor: float):
    if valor < 0:
        return f"🔴 {formatar_sinal_moeda(valor)}"
    if valor == 0:
        return f"🟡 {formatar_moeda(valor)}"
    return f"🟢 {formatar_sinal_moeda(valor)}"


def linha_valor(rotulo: str, valor: float, largura: int = 24):
    return f"│ {rotulo:<{largura}} {formatar_moeda(valor):>14}"


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



def normalizar(texto: str):
    return re.sub(r"\s+", " ", (texto or "").strip())


def texto_chave(texto: str):
    return normalizar(texto).lower()


def parse_data_csv(valor: str):
    valor = normalizar(valor)
    for formato in ["%d/%m/%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            pass
    raise ValueError(f"Data inválida no CSV: {valor}")


def parse_valor_csv(valor: str):
    # Extratos exportam despesas como valores negativos ("-100"); o sinal é
    # descartado depois com abs(). Sem allow_negative, todo o CSV era recusado.
    return parse_money_float(normalizar(valor), allow_negative=True)


def obter_coluna(row: dict, nome: str):
    for chave, valor in row.items():
        if chave.strip().lower() == nome.lower():
            return valor
    return ""


def termo_aparece(texto: str, termo: str):
    termo = re.escape(termo.strip())
    return re.search(rf"(?<![a-z0-9]){termo}(?![a-z0-9])", texto) is not None


def inferir_conta_pagamento(category: str, note: str):
    texto = texto_chave(f"{category} {note}")
    categoria_limpa = texto_chave(category)

    for termo, conta in CONTAS_PAGAMENTO.items():
        if termo == categoria_limpa:
            return conta

    for termo, conta in CONTAS_PAGAMENTO.items():
        if termo_aparece(texto, termo):
            return conta

    return "Pix"


def inferir_forma_pagamento(conta_pagamento: str, category: str, note: str):
    texto = texto_chave(f"{conta_pagamento} {category} {note}")

    if "pix" in texto:
        return "pix"

    if conta_pagamento in ["Nubank", "Mercado Pago", "BTG", "Itaú", "Inter", "PicPay", "C6", "XP", "Compras", "Lia"]:
        return "crédito"

    if conta_pagamento == "Boleto":
        return "boleto"

    return "pix"


def inferir_categoria(category: str, note: str):
    return inferir_categoria_canonica(f"{category} {note}", "despesa")


def inferir_nome(category: str, note: str):
    note = normalizar(note)
    category = normalizar(category)

    if note:
        return note

    return category or "Compromisso"


def eh_fixo(category: str, note: str, quantidade: int):
    texto = texto_chave(f"{category} {note}")

    if "empréstimo" in texto or "emprestimo" in texto:
        return False

    if any(k in texto for k in FIXOS_KEYWORDS):
        return True

    return quantidade >= 18 and not any(k in texto for k in ELETRONICOS_KEYWORDS)


def meses_entre(data_inicio: date, data_fim: date):
    return (data_fim.year - data_inicio.year) * 12 + (data_fim.month - data_inicio.month) + 1


def buscar_csv_mais_recente():
    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    arquivos = sorted(IMPORTS_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    return arquivos[0] if arquivos else None


def ler_csv_transacoes(caminho: Path):
    linhas = []

    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        reader = csv.DictReader(arquivo)

        for row in reader:
            data = parse_data_csv(obter_coluna(row, "Date"))
            category = normalizar(obter_coluna(row, "Category"))
            amount = parse_valor_csv(obter_coluna(row, "Amount"))
            note = normalizar(obter_coluna(row, "Note"))

            if amount == 0:
                continue

            linhas.append({
                "data": data,
                "category": category,
                "amount": amount,
                "valor": abs(amount),
                "note": note,
            })

    return linhas


def _data_fim_importada(tipo, ultima: date, quantidade: int, periodo_meses: int):
    """Término de um compromisso importado.

    Quando há exatamente uma ocorrência por mês do primeiro ao último mês, o
    término vai para o fim do mês da última ocorrência (mesma convenção do
    cadastro manual, _mes_para_fim_fixo). Assim uma última parcela paga antes
    do dia de vencimento não some da projeção.

    Em qualquer outro caso (meses pulados, duas no mesmo mês, pagamento que
    atrasou e caiu no mês seguinte) mantém a data exata, como sempre foi: não dá
    para saber a qual vencimento a última ocorrência pertence, e o fim do mês
    criaria um mês a mais.
    """
    if tipo != "avulso" and quantidade == periodo_meses:
        return ultima.replace(day=ultimo_dia_mes(ultima.year, ultima.month)).isoformat()
    return ultima.isoformat()


def classificar_csv(caminho: Path):
    linhas = ler_csv_transacoes(caminho)
    linhas_lidas = len(linhas)
    # Extratos trazem despesas negativas. Se o arquivo tem negativos, os valores
    # positivos são entradas/estornos e não podem virar compromisso de despesa.
    ignorados_positivos = 0
    if any(linha["amount"] < 0 for linha in linhas):
        ignorados_positivos = sum(1 for linha in linhas if linha["amount"] > 0)
        linhas = [linha for linha in linhas if linha["amount"] < 0]

    grupos = defaultdict(list)
    data_maxima_csv = max((linha["data"] for linha in linhas), default=None)

    for linha in linhas:
        chave = (
            texto_chave(linha["category"]),
            texto_chave(linha["note"]),
            round(linha["valor"], 2),
        )
        grupos[chave].append(linha)

    compromissos = []
    avulsos = []

    for _, itens in grupos.items():
        itens = sorted(itens, key=lambda item: item["data"])
        primeiro = itens[0]
        ultimo = itens[-1]
        quantidade = len(itens)

        nome = inferir_nome(primeiro["category"], primeiro["note"])
        categoria = inferir_categoria(primeiro["category"], primeiro["note"])
        conta = inferir_conta_pagamento(primeiro["category"], primeiro["note"])
        forma = inferir_forma_pagamento(conta, primeiro["category"], primeiro["note"])
        valor = primeiro["valor"]
        dia = primeiro["data"].day
        periodo_meses = meses_entre(primeiro["data"], ultimo["data"])

        if quantidade == 1:
            tipo = "avulso"
        elif eh_fixo(primeiro["category"], primeiro["note"], quantidade):
            tipo = "fixo"
        else:
            tipo = "parcelamento"

        compromisso = {
            "tipo": tipo,
            "nome": nome,
            "categoria": categoria,
            "conta_pagamento": conta,
            "forma_pagamento": forma,
            "valor": valor,
            "dia_vencimento": dia,
            "data_inicio": primeiro["data"].isoformat(),
            "data_fim": _data_fim_importada(tipo, ultimo["data"], quantidade, periodo_meses),
            "parcelas_total": quantidade if tipo == "parcelamento" else None,
            "ativo": True,
            "origem": f"csv:{caminho.name}",
            "observacao": (
                f"Importado do CSV. Category original: {primeiro['category']}. "
                f"Note original: {primeiro['note']}. Ocorrências: {quantidade}. "
                f"Período observado: {primeiro['data'].isoformat()} até {ultimo['data'].isoformat()}."
            )
        }

        if tipo == "avulso":
            avulsos.append(compromisso)
        else:
            compromissos.append(compromisso)

    compromissos = sorted(compromissos, key=lambda c: (c["tipo"], c["conta_pagamento"] or "", c["nome"], c["data_inicio"]))
    avulsos = sorted(avulsos, key=lambda c: c["data_inicio"])

    return {
        "arquivo": caminho.name,
        "linhas": linhas_lidas,
        "ignorados_positivos": ignorados_positivos,
        "compromissos": compromissos,
        "avulsos": avulsos,
    }


def resumir_previa_importacao(preview: dict):
    compromissos = preview["compromissos"]
    avulsos = preview["avulsos"]

    total_fixos = sum(1 for c in compromissos if c["tipo"] == "fixo")
    total_parcelamentos = sum(1 for c in compromissos if c["tipo"] == "parcelamento")
    total_avulsos = len(avulsos)

    linhas = [
        "📥 Prévia da importação CSV",
        "",
        f"Arquivo: {preview['arquivo']}",
        f"Linhas lidas: {preview['linhas']}",
        *([f"Entradas/estornos ignorados (valores positivos): {preview['ignorados_positivos']}"]
          if preview.get("ignorados_positivos") else []),
        "",
        "Classificação sugerida:",
        f"- Fixos: {total_fixos}",
        f"- Parcelamentos: {total_parcelamentos}",
        f"- Avulsos: {total_avulsos}",
        "",
    ]

    fixos = [c for c in compromissos if c["tipo"] == "fixo"]
    parcelamentos = [c for c in compromissos if c["tipo"] == "parcelamento"]

    if fixos:
        linhas.append("Exemplos de fixos:")
        for c in fixos[:8]:
            fim = c["data_fim"] or "sem fim definido"
            linhas.append(
                f"- {c['nome']} | {formatar_moeda(c['valor'])} | {c['conta_pagamento']} | dia {c['dia_vencimento']} | {fim}"
            )
        linhas.append("")

    if parcelamentos:
        linhas.append("Exemplos de parcelamentos:")
        for c in parcelamentos[:8]:
            linhas.append(
                f"- {c['nome']} | {c['parcelas_total']}x de {formatar_moeda(c['valor'])} | "
                f"{c['conta_pagamento']} | {c['data_inicio'][:7]} até {c['data_fim'][:7]}"
            )
        linhas.append("")

    linhas.extend([
        "Para gravar no banco, envie:",
        "confirmar importacao",
        "",
        "Para descartar a prévia, envie:",
        "cancelar importacao",
    ])

    return "\n".join(linhas)


def importar_preview(preview: dict):
    origem = f"csv:{preview['arquivo']}"
    lote = preview["compromissos"] + preview["avulsos"]
    resultado = substituir_compromissos_por_origem(origem, lote)
    return {
        "origem": origem,
        "apagados_anteriores": resultado["apagados"],
        "importados": len(resultado["ids"]),
        "ids": resultado["ids"],
    }


def ultimo_dia_mes(ano: int, mes: int):
    return calendar.monthrange(ano, mes)[1]


def data_no_mes(ano_mes: str, dia: int):
    ano, mes = [int(p) for p in ano_mes.split("-")]
    dia_real = min(dia or 1, ultimo_dia_mes(ano, mes))
    return date(ano, mes, dia_real)


def compromisso_ocorre_no_mes(compromisso, ano_mes: str):
    inicio = date.fromisoformat(compromisso["data_inicio"])
    fim = date.fromisoformat(compromisso["data_fim"]) if compromisso["data_fim"] else None
    data_ref = data_no_mes(ano_mes, compromisso["dia_vencimento"] or inicio.day)

    if data_ref < inicio.replace(day=1):
        return False

    if fim and data_ref > fim:
        return False

    if compromisso["tipo"] in ["avulso", "entrada_avulsa"]:
        return compromisso["data_inicio"][:7] == ano_mes

    return True


def _projetar_compromissos_mes(ano_mes: str, somente_ativos: bool = True):
    resultado = []

    for c in listar_compromissos(somente_ativos=somente_ativos):
        if somente_ativos and not c["ativo"]:
            continue

        if c["tipo"] in ["entrada_fixa", "entrada_avulsa"]:
            continue

        if not compromisso_ocorre_no_mes(c, ano_mes):
            continue

        vencimento = data_no_mes(ano_mes, c["dia_vencimento"] or date.fromisoformat(c["data_inicio"]).day)

        parcela_atual = None
        if c["tipo"] == "parcelamento":
            inicio = date.fromisoformat(c["data_inicio"])
            parcela_atual = (vencimento.year - inicio.year) * 12 + (vencimento.month - inicio.month) + 1

        conta_efetiva = obter_conta_pagamento_efetiva(c) or "Não informada"
        destino_efetivo = obter_destino_pagamento_efetivo(c)
        resultado.append({
            "origem": "compromisso",
            "id": c["id"],
            "tipo": c["tipo"],
            "nome": c["nome"],
            "categoria": c["categoria"],
            "conta_pagamento": conta_efetiva,
            "conta_pagamento_legado": c["conta_pagamento"],
            "conta_origem": (c["conta_origem"] if "conta_origem" in c.keys() else None),
            "destino_pagamento": destino_efetivo,
            "forma_pagamento": c["forma_pagamento"] or "não informada",
            "valor": c["valor"],
            "data": vencimento.isoformat(),
            "parcela_atual": parcela_atual,
            "parcelas_total": c["parcelas_total"],
            "ativo": bool(c["ativo"]),
        })

    from conciliacao import ajustar_projecao
    return sorted(ajustar_projecao(resultado, ano_mes), key=lambda item: (item["data"], item["conta_pagamento"], item["nome"]))


def projetar_compromissos_mes(ano_mes: str, somente_ativos: bool = True):
    return _consulta_cache(
        ("projetar_compromissos_mes", str(ano_mes), bool(somente_ativos)),
        lambda: _projetar_compromissos_mes(ano_mes, somente_ativos),
    )


def _incluir_transacoes_mes_na_projecao(ano_mes: str):
    resultado = []

    for t in buscar_transacoes_por_competencia(ano_mes):
        if t["tipo"] != "despesa":
            continue

        resultado.append({
            "origem": "transacao",
            "id": t["id"],
            "tipo": "transacao",
            "nome": t["descricao"] or "Lançamento",
            "categoria": t["categoria"],
            "conta_pagamento": t["conta"] or t["forma_pagamento"] or "Não informada",
            "forma_pagamento": t["forma_pagamento"] or "não informada",
            "valor": t["valor"],
            "data": data_competencia(t),
            "data_compra": data_real_compra(t),
            "competencia_fatura": competencia_transacao(t),
            "parcela_atual": t["parcela_atual"] if "parcela_atual" in t.keys() else None,
            "parcelas_total": t["parcelas_total"] if "parcelas_total" in t.keys() else None,
            "ativo": True,
        })

    return resultado


def incluir_transacoes_mes_na_projecao(ano_mes: str):
    return _consulta_cache(
        ("incluir_transacoes_mes_na_projecao", str(ano_mes)),
        lambda: _incluir_transacoes_mes_na_projecao(ano_mes),
    )



def normalizar_conta_fatura(valor: str | None):
    if valor is None or type(valor) is str:
        return _normalizar_conta_fatura_texto(valor or "")
    return _normalizar_conta_fatura_sem_cache(valor)


@lru_cache(maxsize=4096)
def _normalizar_conta_fatura_texto(valor: str):
    # Função pura de texto: memoizada (chamada dezenas de milhares de vezes por tela).
    return _normalizar_conta_fatura_sem_cache(valor)


def _normalizar_conta_fatura_sem_cache(valor):
    texto = normalizar(valor or "").lower()
    aliases = {
        "itau": "itau", "itaú": "itau",
        "mercado pago": "mercado pago",
        "nubank": "nubank", "nu bank": "nubank",
        "btg": "btg", "inter": "inter", "c6": "c6",
        "bradesco": "bradesco", "santander": "santander",
        "banco do brasil": "banco do brasil", "bb": "banco do brasil",
        "caixa": "caixa", "picpay": "picpay", "xp": "xp",
    }
    return aliases.get(texto, texto)


def _texto_classificacao_pagamento(valor) -> str:
    return _texto_classificacao_texto(str(valor or ""))


@lru_cache(maxsize=8192)
def _texto_classificacao_texto(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", valor.strip().lower())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", texto)


def item_eh_fatura_cartao(item: dict) -> bool:
    """Classifica faturas sem depender apenas de uma whitelist fechada.

    Contas historicamente conhecidas preservam o comportamento legado. Para
    contas novas (InfinitePay, Neon, Will etc.), uma forma explicitamente de
    credito passa a bastar a partir da competencia de implantacao desta regra.
    Isso evita ressuscitar compras antigas que nunca foram acompanhadas como
    fatura/pendencia pelo assessor.
    """
    if not isinstance(item, dict):
        return False

    origem = _texto_classificacao_pagamento(item.get("origem"))
    tipo = _texto_classificacao_pagamento(item.get("tipo"))
    nome = _texto_classificacao_pagamento(item.get("nome") or item.get("descricao"))
    categoria = _texto_classificacao_pagamento(item.get("categoria"))
    conta = _texto_classificacao_pagamento(
        item.get("conta_pagamento") or item.get("conta")
    )
    forma = _texto_classificacao_pagamento(
        item.get("forma_pagamento") or item.get("forma")
    )

    if origem == "fatura_movimento" or tipo == "fatura_movimento":
        return False
    if "emprest" in f"{nome} {categoria} {tipo}":
        return False

    formas_imediatas = {
        "pix", "debito", "dinheiro", "transferencia", "boleto",
    }
    if forma in formas_imediatas:
        return False

    bancos_conhecidos = {
        "itau", "nubank", "mercado pago", "btg", "inter", "c6",
        "santander", "bradesco", "caixa", "banco do brasil",
        "bb", "sicredi", "sicoob", "picpay", "xp",
    }
    conta_eh_fatura_legada = (
        conta in bancos_conhecidos
        or "cartao" in conta
        or "card" in conta
    )

    forma_credito = any(
        termo in forma for termo in ("credito", "cartao", "fatura")
    )
    forma_legada = forma in {
        "", "nao informada", "nao informado", "outro", "outros",
        "desconhecida", "desconhecido",
    }

    if conta_eh_fatura_legada:
        return forma_credito or forma_legada

    # RC3.0.14 - onboarding dinamico de novos cartoes.
    # Antes de setembro/2026, contas fora da whitelist nunca foram acompanhadas
    # como fatura pelo assessor. Nao inferimos retroativamente que essas compras
    # antigas seguem em aberto. A partir daqui, qualquer conta nomeada usada em
    # credito entra automaticamente no fluxo mensal e passa a ser carregada para
    # o mes seguinte se realmente permanecer sem baixa.
    data_item = str(item.get("data") or "")[:10]
    conta_informada = conta not in {
        "", "nao informada", "nao informado", "desconhecida", "desconhecido",
    }
    return bool(
        forma_credito
        and conta_informada
        and data_item >= DATA_INICIO_CARTOES_NOVOS
    )


def classificar_natureza_pagamento(item: dict) -> str:
    """Retorna uma natureza visual sem alterar valor ou elegibilidade."""
    if not isinstance(item, dict):
        return "compromissos"

    origem = _texto_classificacao_pagamento(item.get("origem"))
    tipo = _texto_classificacao_pagamento(item.get("tipo"))
    nome = _texto_classificacao_pagamento(item.get("nome") or item.get("descricao"))
    categoria = _texto_classificacao_pagamento(item.get("categoria"))
    forma = _texto_classificacao_pagamento(
        item.get("forma_pagamento") or item.get("forma")
    )

    if origem == "fatura_movimento" or tipo == "fatura_movimento":
        return "movimentos_fatura"
    if "emprest" in f"{nome} {categoria} {tipo}":
        return "emprestimos"
    if tipo == "fixo":
        return "fixos"
    if origem == "transacao" and forma in {
        "pix", "debito", "dinheiro", "transferencia",
    }:
        return "transacoes_imediatas"
    if item_eh_fatura_cartao(item):
        return "faturas"
    if (
        tipo == "parcelamento"
        or item.get("parcela_atual")
        or item.get("parcelas_total")
    ):
        return "parcelas"
    return "compromissos"


def total_movimentos_fatura(ano_mes: str, conta_cartao: str):
    conta_norm = normalizar_conta_fatura(conta_cartao)
    creditos = pagamentos = ajustes_debito = 0.0
    for mov in _listar_fatura_movimentos_consulta(ano_mes):
        if normalizar_conta_fatura(mov["conta_cartao"]) != conta_norm:
            continue
        valor = float(mov["valor"] or 0)
        tipo = mov["tipo_movimento"]
        if tipo in {"estorno", "credito", "ajuste_credito"}:
            creditos += valor
        elif tipo in {"pagamento_parcial", "pagamento_total"}:
            pagamentos += valor
        elif tipo == "ajuste_debito":
            ajustes_debito += valor
    return {
        "creditos": creditos,
        "pagamentos": pagamentos,
        "ajustes_debito": ajustes_debito,
        "liquido": ajustes_debito - creditos - pagamentos,
    }



def _obter_itens_base_pagamentos_mes(ano_mes: str, incluir_transacoes: bool = True):
    itens = projetar_compromissos_mes(ano_mes)
    if incluir_transacoes:
        itens.extend(incluir_transacoes_mes_na_projecao(ano_mes))
    return sorted(
        itens,
        key=lambda item: (
            item.get("data") or "",
            item.get("conta_pagamento") or "",
            item.get("nome") or "",
        ),
    )


def obter_itens_base_pagamentos_mes(ano_mes: str, incluir_transacoes: bool = True):
    return _consulta_cache(
        ("obter_itens_base_pagamentos_mes", str(ano_mes), bool(incluir_transacoes)),
        lambda: _obter_itens_base_pagamentos_mes(ano_mes, incluir_transacoes),
    )


def _listar_fatura_movimentos_consulta(ano_mes=None, conta_cartao=None):
    return _consulta_cache(
        ("listar_fatura_movimentos", ano_mes, conta_cartao),
        lambda: listar_fatura_movimentos(ano_mes, conta_cartao),
    )


def _obter_primeira_competencia_consulta():
    return _consulta_cache(
        ("obter_primeira_competencia_financeira",),
        obter_primeira_competencia_financeira,
    )


def _mes_anterior(ano_mes: str):
    ano, mes = map(int, ano_mes.split("-"))
    mes -= 1
    if mes == 0:
        ano -= 1
        mes = 12
    return f"{ano:04d}-{mes:02d}"


def _nome_base_item_cartao(item: dict) -> str:
    """Normaliza nome e remove sufixos de parcela para comparação segura."""
    nome = _texto_classificacao_pagamento(item.get("nome") or item.get("descricao"))
    nome = re.sub(r"\s*\(\s*\d+\s*/\s*\d+\s*\)\s*$", "", nome).strip()
    return nome


def _previsto_corresponde_realizado(previsto: dict, realizado: dict) -> bool:
    """Detecta apenas duplicidade do MESMO item, nunca do cartão inteiro.

    A RC3.0.6 eliminava todas as previsões de um cartão assim que existia
    qualquer lançamento real naquele mês. Isso removia obrigações diferentes
    (ex.: Monitor Magalu fazia sumir Drone DJI). Aqui a substituição só ocorre
    quando há evidência forte de que previsto e realizado representam a mesma
    cobrança: mesma conta, mesmo valor e mesmo nome normalizado.
    """
    if not isinstance(previsto, dict) or not isinstance(realizado, dict):
        return False
    if normalizar_conta_fatura(previsto.get("conta_pagamento") or "") != normalizar_conta_fatura(realizado.get("conta_pagamento") or ""):
        return False
    try:
        if abs(float(previsto.get("valor") or 0) - float(realizado.get("valor") or 0)) > 0.01:
            return False
    except (TypeError, ValueError):
        return False

    nome_prev = _nome_base_item_cartao(previsto)
    nome_real = _nome_base_item_cartao(realizado)
    if not nome_prev or not nome_real:
        return False
    return nome_prev == nome_real


def _separar_fonte_cartao(candidatos: list[dict]):
    """Mantém previsões independentes e remove somente duplicidades reais."""
    realizados = [
        item for item in candidatos
        if texto_chave(item.get("origem") or "") == "transacao"
        or (
            texto_chave(item.get("tipo") or "") in {"transacao", "despesa", "receita"}
            and texto_chave(item.get("origem") or "") != "compromisso"
        )
    ]
    previstos = [item for item in candidatos if item not in realizados]
    previstos_ignorados = []
    previstos_mantidos = []
    for previsto in previstos:
        if any(_previsto_corresponde_realizado(previsto, real) for real in realizados):
            previstos_ignorados.append(previsto)
        else:
            previstos_mantidos.append(previsto)
    return realizados, previstos_mantidos, previstos_ignorados


def _copia_rapida(valor, _memo=None):
    """Equivale a ``deepcopy`` para estruturas de leitura (dict/list/tuple/set).

    Escalares imutaveis sao reaproveitados; conteineres sao recriados e a
    identidade compartilhada dentro de um mesmo resultado e preservada (como no
    deepcopy). Qualquer outro tipo cai no ``deepcopy`` original.
    """
    # Mesma cópia do consulta_cache (com atalho para escalares simples).
    return copia_rapida(valor, _memo)


def _itens_base_da_conta(ano_mes: str, conta_norm: str):
    """Itens-base do mes que pertencem a ``conta_norm``, ja copiados.

    Equivale a filtrar ``obter_itens_base_pagamentos_mes`` (que devolve uma copia
    profunda de TODOS os itens do mes a cada leitura em cache), mas filtra sobre
    a entrada do cache sem copiar e so copia os itens da conta pedida.
    """
    def da_conta(item):
        return isinstance(item, dict) and normalizar_conta_fatura(item.get("conta_pagamento") or "") == conta_norm

    cache = cache_atual()
    chave = chave_no_escopo(("obter_itens_base_pagamentos_mes", str(ano_mes), True))
    base = cache.get(chave) if cache is not None else None
    if base is None:
        # Sem cache (ou ainda nao calculado): a leitura normal ja devolve copia propria.
        return [item for item in obter_itens_base_pagamentos_mes(ano_mes, incluir_transacoes=True) if da_conta(item)]
    memo = {}
    return [_copia_rapida(item, memo) for item in base if da_conta(item)]


def calcular_fatura_unificada(ano_mes: str, conta_cartao: str, _memo=None, somente_cartao: bool = False):
    """Consolida a fatura sem duplicar o mesmo item previsto e realizado.

    Lançamentos reais NÃO substituem todas as previsões do cartão. Uma previsão
    só é removida quando corresponde ao mesmo item real (conta + valor + nome).
    """
    conta_norm = normalizar_conta_fatura(conta_cartao)
    memo_contexto = namespace("calcular_fatura_unificada") if _memo is None else None
    _memo = _memo if _memo is not None else (memo_contexto if memo_contexto is not None else {})
    chave = (ano_mes, conta_norm, bool(somente_cartao))
    if chave in _memo:
        return _copia_rapida(_memo[chave])

    itens_todos = _itens_base_da_conta(ano_mes, conta_norm)

    itens_previstos_ignorados = []
    if somente_cartao:
        candidatos = [item for item in itens_todos if item_eh_fatura_cartao(item)]
        realizados, previstos, itens_previstos_ignorados = _separar_fonte_cartao(candidatos)
        itens_fatura = previstos + realizados
    else:
        elegiveis = [item for item in itens_todos if item_entra_no_quanto_vou_pagar(item)]
        cartao = [item for item in elegiveis if item_eh_fatura_cartao(item)]
        outros = [item for item in elegiveis if item not in cartao]
        realizados, previstos, itens_previstos_ignorados = _separar_fonte_cartao(cartao)
        itens_fatura = outros + previstos + realizados

    if itens_previstos_ignorados:
        fonte_fatura = "mista_deduplicada"
    elif any(texto_chave(item.get("origem") or "") == "transacao" for item in itens_fatura):
        fonte_fatura = "mista" if any(texto_chave(item.get("origem") or "") == "compromisso" for item in itens_fatura) else "real"
    else:
        fonte_fatura = "prevista" if itens_fatura else "sem_dados"

    itens_imediatos = [item for item in itens_todos if forma_pagamento_imediata(item)]
    movimentos = [
        mov for mov in _listar_fatura_movimentos_consulta(ano_mes)
        if normalizar_conta_fatura(mov["conta_cartao"]) == conta_norm
    ]

    valor_bruto = sum(float(item.get("valor") or 0) for item in itens_fatura)
    creditos = sum(float(m["valor"] or 0) for m in movimentos if m["tipo_movimento"] in {"estorno", "credito", "ajuste_credito"})
    pagamentos = sum(float(m["valor"] or 0) for m in movimentos if m["tipo_movimento"] in {"pagamento_parcial", "pagamento_total"})
    ajustes_debito = sum(float(m["valor"] or 0) for m in movimentos if m["tipo_movimento"] == "ajuste_debito")

    credito_herdado = 0.0
    primeira = _obter_primeira_competencia_consulta()
    anterior = _mes_anterior(ano_mes)
    if primeira and anterior >= primeira:
        resumo_anterior = calcular_fatura_unificada(anterior, conta_cartao, _memo, somente_cartao=somente_cartao)
        credito_herdado = max(0.0, -float(resumo_anterior["saldo_restante"] or 0))

    from fatura_conferencia import obter as obter_conferencia
    conferencia = _consulta_cache(
        ("fatura_conferencia.obter", ano_mes, conta_norm),
        lambda: obter_conferencia(ano_mes, conta_cartao),
    )
    ajuste_conferencia = float(conferencia['ajuste_composicao']) if conferencia else 0.0
    saldo_restante = valor_bruto - credito_herdado - creditos - pagamentos + ajustes_debito + ajuste_conferencia
    possui_movimento = bool(itens_fatura or movimentos)
    if saldo_restante > 0.005:
        status = "parcialmente paga" if pagamentos > 0 else ("parcialmente abatida" if creditos > 0 or credito_herdado > 0 else "pendente")
    elif saldo_restante < -0.005:
        status = "saldo credor transportado" if not possui_movimento and credito_herdado > 0 else "saldo credor"
    else:
        status = "paga" if possui_movimento or credito_herdado > 0 else "sem movimentação"

    resultado = {
        "ano_mes": ano_mes,
        "conta_cartao": conta_cartao,
        "valor_bruto": valor_bruto,
        "credito_herdado": credito_herdado,
        "creditos": creditos,
        "pagamentos": pagamentos,
        "ajustes_debito": ajustes_debito,
        "ajuste_conferencia": ajuste_conferencia,
        "conferencia": conferencia,
        "saldo_restante": saldo_restante,
        "status": status,
        "itens": itens_fatura,
        "itens_imediatos_ignorados": itens_imediatos,
        "itens_previstos_ignorados": itens_previstos_ignorados,
        "fonte_fatura": fonte_fatura,
        "movimentos": movimentos,
    }
    _memo[chave] = copia_defensiva(resultado)
    return _copia_rapida(_memo[chave])


def aplicar_movimentos_fatura_na_projecao(ano_mes: str, itens: list):
    resultado = list(itens)
    from fatura_conferencia import ajustes_mes, item_projecao
    resultado.extend(item_projecao(evento) for evento in ajustes_mes(ano_mes))
    for mov in _listar_fatura_movimentos_consulta(ano_mes):
        tipo = mov["tipo_movimento"]
        valor = float(mov["valor"] or 0)
        if tipo in {"estorno", "credito", "pagamento_parcial", "pagamento_total", "ajuste_credito"}:
            valor_item = -valor
        elif tipo == "ajuste_debito":
            valor_item = valor
        else:
            continue
        resultado.append({
            "origem": "fatura_movimento",
            "id": mov["id"],
            "tipo": "fatura_movimento",
            "nome": mov["descricao"] or tipo.replace("_", " ").title(),
            "categoria": "Ajuste de fatura",
            "conta_pagamento": mov["conta_cartao"],
            "forma_pagamento": "fatura",
            "valor": valor_item,
            "data": mov["data_movimento"],
            "parcela_atual": None,
            "parcelas_total": None,
            "ativo": True,
            "tipo_movimento": tipo,
        })
    return resultado


def _projetar_pagamentos_mes(ano_mes: str, incluir_transacoes: bool = True):
    itens = obter_itens_base_pagamentos_mes(
        ano_mes,
        incluir_transacoes=incluir_transacoes,
    )
    itens = aplicar_movimentos_fatura_na_projecao(ano_mes, itens)
    return sorted(
        itens,
        key=lambda item: (
            item.get("data") or "",
            item.get("conta_pagamento") or "",
            item.get("nome") or "",
        ),
    )


def projetar_pagamentos_mes(ano_mes: str, incluir_transacoes: bool = True):
    return _consulta_cache(
        ("projetar_pagamentos_mes", str(ano_mes), bool(incluir_transacoes)),
        lambda: _projetar_pagamentos_mes(ano_mes, incluir_transacoes),
    )


TIPOS_LIQUIDACAO_FATURA = frozenset({"pagamento_parcial", "pagamento_total"})


def item_eh_liquidacao_fatura(item) -> bool:
    """Pagamento de fatura projetado como item negativo (``fatura_movimento``).

    Mesmo critério de ``liquidacoes_fatura`` em ``_calcular_saldo_mensal_etapa``:
    liquidar a fatura não é estorno nem despesa; só a ponte de caixa o usa.
    """
    return (
        isinstance(item, dict)
        and item.get("origem") == "fatura_movimento"
        and item.get("tipo_movimento") in TIPOS_LIQUIDACAO_FATURA
    )


def remover_liquidacoes_fatura(itens) -> list:
    """Remove pagamentos de fatura de visões de gasto (categorias/fechamento).

    Estornos, créditos e ajustes de débito continuam, como em "meu mês", onde
    reduzem/aumentam as despesas esperadas do mês.
    """
    return [item for item in (itens or []) if not item_eh_liquidacao_fatura(item)]


def item_eh_realizado(item: dict):
    return item.get("origem") == "transacao"


def resumo_contas_mes_quebrado(ano_mes: str):
    # Pagamento de fatura não é gasto do mês (B1): a compra já entrou como
    # crédito/esperado. Mantê-lo aqui deixava o "Esperado" negativo.
    itens = remover_liquidacoes_fatura(projetar_pagamentos_mes(ano_mes, incluir_transacoes=True))

    if not itens:
        return f"Não encontrei pagamentos previstos ou realizados para {ano_mes}."

    totais = defaultdict(lambda: {"realizado": 0.0, "esperado": 0.0})

    for item in itens:
        chave = item.get("conta_pagamento") or item.get("forma_pagamento") or "Não informada"

        if item_eh_realizado(item):
            totais[chave]["realizado"] += item["valor"]
        else:
            totais[chave]["esperado"] += item["valor"]

    total_realizado = sum(v["realizado"] for v in totais.values())
    total_esperado = sum(v["esperado"] for v in totais.values())
    total_geral = total_realizado + total_esperado

    linhas = [f"🏦 Contas de pagamento em {formatar_ano_mes_visual(ano_mes)}", ""]
    linhas.append(f"Total do mês: {formatar_moeda(total_geral)}")
    linhas.append(f"Realizado: {formatar_moeda(total_realizado)}")
    linhas.append(f"Esperado: {formatar_moeda(total_esperado)}")
    linhas.append("")

    for conta, valores in sorted(totais.items(), key=lambda kv: kv[1]["realizado"] + kv[1]["esperado"], reverse=True):
        total_conta = valores["realizado"] + valores["esperado"]
        linhas.append(
            f"- {conta}: {formatar_moeda(total_conta)} "
            f"(realizado {formatar_moeda(valores['realizado'])} | esperado {formatar_moeda(valores['esperado'])})"
        )

    linhas.extend([
        "",
        "Critério:",
        "Realizado = lançamentos já registrados.",
        "Esperado = fixos, compromissos e parcelas do mês.",
        "",
        "Para detalhar, envie:",
        "quanto vou pagar no nubank",
        "quanto vou pagar no pix em 2026-07",
    ])

    return "\n".join(linhas)


def incluir_receitas_mes_na_projecao(ano_mes: str):
    resultado = []

    for t in buscar_transacoes_por_mes(ano_mes):
        if t["tipo"] != "receita":
            continue

        resultado.append({
            "origem": "transacao",
            "id": t["id"],
            "tipo": "receita_lancada",
            "nome": t["descricao"] or "Receita",
            "categoria": t["categoria"] or "Receita",
            "conta_pagamento": t["conta"] or t["forma_pagamento"] or "Não informada",
            "forma_pagamento": t["forma_pagamento"] or "não informada",
            "valor": t["valor"],
            "data": t["data"],
            "parcela_atual": None,
            "parcelas_total": None,
            "ativo": True,
        })

    return resultado


def projetar_entradas_programadas_mes(ano_mes: str, somente_ativos: bool = True):
    resultado = []

    for c in listar_compromissos(somente_ativos=somente_ativos):
        if somente_ativos and not c["ativo"]:
            continue

        if c["tipo"] not in ["entrada_fixa", "entrada_avulsa"]:
            continue

        if not compromisso_ocorre_no_mes(c, ano_mes):
            continue

        data_referencia = date.fromisoformat(c["data_inicio"])
        data_entrada = data_no_mes(ano_mes, c["dia_vencimento"] or data_referencia.day)

        resultado.append({
            "origem": "entrada",
            "id": c["id"],
            "tipo": c["tipo"],
            "nome": c["nome"],
            "categoria": c["categoria"] or "Receita",
            "conta_pagamento": c["conta_pagamento"] or "Não informada",
            "forma_pagamento": c["forma_pagamento"] or "entrada",
            "valor": c["valor"],
            "data": data_entrada.isoformat(),
            "parcela_atual": None,
            "parcelas_total": None,
            "ativo": bool(c["ativo"]),
        })

    from conciliacao import ajustar_projecao
    return sorted(ajustar_projecao(resultado, ano_mes), key=lambda item: (item["data"], item["nome"], item["id"]))


def projetar_entradas_mes(ano_mes: str, incluir_transacoes: bool = True):
    itens = projetar_entradas_programadas_mes(ano_mes)

    if incluir_transacoes:
        itens.extend(incluir_receitas_mes_na_projecao(ano_mes))

    return sorted(itens, key=lambda item: (item["data"], item["nome"], item["id"]))


def criar_entrada_fixa_manual(nome: str, valor: float, dia_recebimento: int | None = None, conta_recebimento: str | None = None):
    nome = normalizar(nome).title()

    if not nome:
        nome = "Entrada Fixa"

    if dia_recebimento is None:
        dia_recebimento = relogio.hoje(date).day

    if dia_recebimento < 1 or dia_recebimento > 31:
        return None

    conta = normalizar(conta_recebimento or "Conta principal").title()
    hoje = relogio.hoje(date)
    data_inicio = data_no_mes(hoje.strftime("%Y-%m"), dia_recebimento)

    compromisso = {
        "tipo": "entrada_fixa",
        "nome": nome,
        "categoria": "Receita",
        "conta_pagamento": conta,
        "forma_pagamento": "entrada",
        "valor": valor,
        "dia_vencimento": dia_recebimento,
        "data_inicio": data_inicio.isoformat(),
        "data_fim": None,
        "parcelas_total": None,
        "ativo": True,
        "origem": "telegram:entrada_fixa",
        "observacao": "Entrada fixa cadastrada manualmente pelo Telegram.",
    }

    compromisso_id = inserir_compromisso(compromisso)
    compromisso["id"] = compromisso_id

    return compromisso


def criar_entrada_avulsa_manual(nome: str, valor: float, data_entrada: str, conta_recebimento: str | None = None):
    nome = normalizar(nome).title()

    if not nome:
        nome = "Entrada Avulsa"

    data_ref = date.fromisoformat(data_entrada)
    conta = normalizar(conta_recebimento or "Conta principal").title()

    compromisso = {
        "tipo": "entrada_avulsa",
        "nome": nome,
        "categoria": "Receita",
        "conta_pagamento": conta,
        "forma_pagamento": "entrada",
        "valor": valor,
        "dia_vencimento": data_ref.day,
        "data_inicio": data_ref.isoformat(),
        "data_fim": data_ref.isoformat(),
        "parcelas_total": None,
        "ativo": True,
        "origem": "telegram:entrada_avulsa",
        "observacao": "Entrada avulsa/futura cadastrada manualmente pelo Telegram.",
    }

    compromisso_id = inserir_compromisso(compromisso)
    compromisso["id"] = compromisso_id

    return compromisso


def cadastrar_entrada_fixa_formatado(nome: str, valor: float, dia_recebimento: int | None = None, conta_recebimento: str | None = None):
    entrada = criar_entrada_fixa_manual(nome, valor, dia_recebimento, conta_recebimento)

    if not entrada:
        return "💰 Entrada fixa\n\nNão consegui cadastrar a entrada fixa. Verifique o dia de recebimento."

    return "\n".join([
        "💰 Entrada fixa cadastrada",
        "",
        f"┌ #E{entrada['id']} · {entrada['nome']}",
        f"│ 💰 +{formatar_moeda(entrada['valor'])}",
        f"│ 📅 dia {entrada['dia_vencimento']}",
        f"│ 🏦 {entrada['conta_pagamento']}",
        "└",
        "",
        "Ela entrará na previsão do mês atual e dos próximos meses enquanto estiver ativa.",
    ])


def cadastrar_entrada_avulsa_formatado(nome: str, valor: float, data_entrada: str, conta_recebimento: str | None = None):
    try:
        entrada = criar_entrada_avulsa_manual(nome, valor, data_entrada, conta_recebimento)
    except ValueError:
        return "💰 Entrada futura\n\nData inválida. Use o formato: entrada décimo terceiro 1900,00 em 2026-12-20"

    return "\n".join([
        "💰 Entrada futura cadastrada",
        "",
        formatar_item_card(
            identificador=f"#E{entrada['id']}",
            data_item=entrada["data_inicio"],
            valor=entrada["valor"],
            categoria="Receita",
            nome=entrada["nome"],
            conta=entrada["conta_pagamento"],
            forma="entrada",
            extra="avulsa",
            tipo_valor="entrada",
        ),
        "",
        "Ela entrará na previsão desse mês.",
    ])


def listar_entradas_formatado():
    entradas = [
        c for c in listar_compromissos()
        if c["tipo"] in ["entrada_fixa", "entrada_avulsa"]
    ]

    if not entradas:
        return (
            "Não encontrei entradas previstas cadastradas.\n\n"
            "Exemplos:\n"
            "nova entrada fixa salário 3800 dia 5\n"
            "entrada décimo terceiro 1900,00 em 2026-12-20"
        )

    linhas = ["💰 Entradas previstas cadastradas", ""]

    for e in entradas:
        status = "ativa" if e["ativo"] else "pausada"
        tipo = "fixa" if e["tipo"] == "entrada_fixa" else "avulsa"
        data = e["data_inicio"] if e["tipo"] == "entrada_avulsa" else f"dia {e['dia_vencimento']}"
        linhas.append(
            f"#E{e['id']} | {status} | {tipo} | {e['nome']} | "
            f"{formatar_moeda(e['valor'])} | {data} | {e['conta_pagamento'] or 'Não informada'}"
        )

    linhas.extend([
        "",
        "Comandos úteis:",
        "entradas 2026-07",
        "alterar entrada 1 para 3800",
        "pausar entrada 1",
        "reativar entrada 1",
        "apagar entrada 1",
    ])

    return "\n".join(linhas)


def listar_entradas_mes_formatado(ano_mes: str):
    itens = projetar_entradas_mes(ano_mes, incluir_transacoes=True)

    if not itens:
        return (
            f"💰 Entradas — {formatar_ano_mes_visual(ano_mes)}\n\n"
            "Não encontrei entradas previstas ou registradas para este mês.\n\n"
            "Exemplos:\n"
            "nova entrada fixa salário 3800 dia 5\n"
            "entrada décimo terceiro 1900,00 em 2026-12-20"
        )

    total = sum(item["valor"] for item in itens)
    linhas = [
        f"💰 Entradas — {formatar_ano_mes_visual(ano_mes)}",
        "",
        bloco_total("Resumo", [
            linha_valor("Total", total),
            f"│ {'Itens':<24} {len(itens):>14}",
        ]),
        "",
        "Itens:"
    ]

    for item in itens:
        prefixo = "E" if item["origem"] == "entrada" else ""
        identificador = f"#{prefixo}{item['id']}"
        tipo = "fixa" if item["tipo"] == "entrada_fixa" else "avulsa" if item["tipo"] == "entrada_avulsa" else "lançada"

        linhas.extend([
            "",
            formatar_item_card(
                identificador=identificador,
                data_item=item["data"],
                valor=item["valor"],
                categoria="Receita",
                nome=item["nome"],
                conta=item["conta_pagamento"],
                forma=item["forma_pagamento"],
                extra=tipo,
                tipo_valor="entrada",
            )
        ])

    return "\n".join(linhas)


def alterar_entrada_valor(entrada_id: int, novo_valor: float):
    antes = buscar_compromisso_por_id(entrada_id)

    if not antes:
        return f"💰 Entrada\n\nNão encontrei entrada #E{entrada_id}."

    if antes["tipo"] not in ["entrada_fixa", "entrada_avulsa"]:
        return f"💰 Entrada\n\nO item #E{entrada_id} não é uma entrada. Tipo atual: {antes['tipo']}."

    depois = atualizar_valor_compromisso(entrada_id, novo_valor)

    return "\n".join([
        "💰 Entrada atualizada",
        "",
        bloco_total(f"#E{depois['id']} · {depois['nome']}", [
            linha_valor("Valor antigo", antes["valor"]),
            linha_valor("Novo valor", depois["valor"]),
        ]),
    ])


def pausar_entrada(entrada_id: int):
    entrada = buscar_compromisso_por_id(entrada_id)

    if not entrada or entrada["tipo"] not in ["entrada_fixa", "entrada_avulsa"]:
        return f"⏸️ Entrada\n\nNão encontrei entrada #E{entrada_id}."

    entrada = definir_status_compromisso(entrada_id, False)
    return f"⏸️ Entrada pausada\n\n#E{entrada['id']} · {entrada['nome']}\n{formatar_moeda(entrada['valor'])}"


def reativar_entrada(entrada_id: int):
    entrada = buscar_compromisso_por_id(entrada_id)

    if not entrada or entrada["tipo"] not in ["entrada_fixa", "entrada_avulsa"]:
        return f"▶️ Entrada\n\nNão encontrei entrada #E{entrada_id}."

    entrada = definir_status_compromisso(entrada_id, True)
    return f"▶️ Entrada reativada\n\n#E{entrada['id']} · {entrada['nome']}\n{formatar_moeda(entrada['valor'])}"


def apagar_entrada_formatado(entrada_id: int):
    entrada = buscar_compromisso_por_id(entrada_id)

    if not entrada or entrada["tipo"] not in ["entrada_fixa", "entrada_avulsa"]:
        return f"🗑️ Entrada\n\nNão encontrei entrada #E{entrada_id}."

    apagada = apagar_compromisso_por_id(entrada_id)
    return "\n".join([
        "🗑️ Entrada apagada",
        "",
        bloco_total(f"#E{apagada['id']} · {apagada['nome']}", [
            linha_valor("Valor removido", apagada["valor"]),
        ]),
    ])


def criar_fixo_manual(nome: str, valor: float, dia_vencimento: int | None = None, conta_pagamento: str | None = None):
    nome = normalizar(nome).title()

    if not nome:
        nome = "Fixo"

    if dia_vencimento is None:
        dia_vencimento = relogio.hoje(date).day

    if dia_vencimento < 1 or dia_vencimento > 31:
        return None

    conta = conta_pagamento or inferir_conta_pagamento(nome, nome)
    conta = normalizar(conta).title()

    mapa_contas = {
        "Pix": "Pix",
        "Nubank": "Nubank",
        "Mercado Pago": "Mercado Pago",
        "Btg": "BTG",
        "BtG": "BTG",
        "Itaú": "Itaú",
        "Itau": "Itaú",
        "Inter": "Inter",
        "Picpay": "PicPay",
        "PicPay": "PicPay",
        "C6": "C6",
        "Xp": "XP",
        "XP": "XP",
        "Lia": "Lia",
        "Compras": "Compras",
        "Boleto": "Boleto",
    }

    conta = mapa_contas.get(conta, conta)
    categoria = inferir_categoria(nome, nome)
    forma = inferir_forma_pagamento(conta, nome, nome)

    hoje = relogio.hoje(date)
    data_inicio = data_no_mes(hoje.strftime("%Y-%m"), dia_vencimento)

    compromisso = {
        "tipo": "fixo",
        "nome": nome,
        "categoria": categoria,
        "conta_pagamento": conta,
        "forma_pagamento": forma,
        "valor": valor,
        "dia_vencimento": dia_vencimento,
        "data_inicio": data_inicio.isoformat(),
        "data_fim": None,
        "parcelas_total": None,
        "ativo": True,
        "origem": "telegram:fixo",
        "observacao": "Fixo cadastrado manualmente pelo Telegram.",
    }

    compromisso_id = inserir_compromisso(compromisso)
    compromisso["id"] = compromisso_id

    return compromisso


def cadastrar_fixo_manual_formatado(nome: str, valor: float, dia_vencimento: int | None = None, conta_pagamento: str | None = None):
    compromisso = criar_fixo_manual(nome, valor, dia_vencimento, conta_pagamento)

    if not compromisso:
        return "🔁 Fixo\n\nNão consegui cadastrar o fixo. Verifique o dia de vencimento."

    return "\n".join([
        "🔁 Fixo cadastrado",
        "",
        f"┌ #C{compromisso['id']} · {compromisso['nome']}",
        f"│ 💸 {formatar_moeda(compromisso['valor'])}",
        f"│ 📅 dia {compromisso['dia_vencimento']}",
        f"│ 🏦 {compromisso['conta_pagamento']}",
        f"│ 💳 {compromisso['forma_pagamento']}",
        f"│ 🏷 {compromisso['categoria']}",
        "└",
        "",
        "Ele entrará na agenda do mês atual e dos próximos meses enquanto estiver ativo.",
    ])



def forma_pagamento_imediata(item: dict):
    """
    Itens de pagamento imediato já foram consolidados no caixa quando lançados.
    Portanto não devem entrar no comando "quanto vou pagar no X".
    """
    forma = texto_chave(item.get("forma_pagamento") or "")
    return forma in ["pix", "debito", "débito", "dinheiro", "transferencia", "transferência"]


def item_entra_no_quanto_vou_pagar(item: dict):
    """
    Para "quanto vou pagar no banco/conta", considerar tudo o que ainda
    representa obrigação futura do mês.

    Regras:
    - compromissos projetados (fixos, parcelamentos e avulsos) entram mesmo
      quando a forma cadastrada é Pix/débito/transferência, pois ainda não
      foram realizados;
    - transações já lançadas como Pix/débito/dinheiro/transferência ficam de
      fora, pois já movimentaram o caixa;
    - compras e lançamentos de crédito continuam entrando na fatura.
    """
    origem = texto_chave(item.get("origem") or "")
    tipo = texto_chave(item.get("tipo") or "")

    if origem == "compromisso" or tipo in {"fixo", "parcelamento", "avulso"}:
        return True

    return not forma_pagamento_imediata(item)



def calcular_resumo_pagamento_conta(ano_mes: str, termo: str):
    """Calcula os componentes pendentes sem deixar crédito de cartão abater Pix/fixos."""
    # Usa a projeção ampla porque ela contém também compromissos não-cartão.
    # ``calcular_fatura_unificada`` já remove previsões de cartão quando existe
    # fonte real na competência.
    fatura = calcular_fatura_unificada(ano_mes, termo)
    itens = list(fatura.get("itens") or [])

    total_fixos = 0.0
    total_emprestimos = 0.0
    total_compromissos = 0.0
    total_fatura_bruta = 0.0
    # Fixos/compromissos lançados no crédito fazem parte da fatura do cartão
    # (como em ``calcular_fatura_unificada`` e no checklist). Continuam
    # exibidos em linhas próprias, mas o pagamento/crédito da fatura que
    # exceder as compras também os cobre.
    fixos_cartao = 0.0
    compromissos_cartao = 0.0

    for item in itens:
        if not isinstance(item, dict):
            continue
        tipo = texto_chave(item.get("tipo") or "")
        origem = texto_chave(item.get("origem") or "")
        valor = float(item.get("valor") or 0)
        natureza = classificar_natureza_pagamento(item)

        if natureza == "emprestimos":
            total_emprestimos += valor
        elif tipo == "fixo":
            total_fixos += valor
            if item_eh_fatura_cartao(item):
                fixos_cartao += valor
        elif tipo == "avulso" or (origem == "compromisso" and tipo not in {"parcelamento"}):
            total_compromissos += valor
            if item_eh_fatura_cartao(item):
                compromissos_cartao += valor
        else:
            total_fatura_bruta += valor

    abatimentos_fatura = (
        float(fatura.get("credito_herdado") or 0)
        + float(fatura.get("creditos") or 0)
        + float(fatura.get("pagamentos") or 0)
    )
    ajustes_fatura = (
        float(fatura.get("ajustes_debito") or 0)
        + float(fatura.get("ajuste_conferencia") or 0)
    )
    saldo_fatura = total_fatura_bruta - abatimentos_fatura + ajustes_fatura
    # Excesso de pagamento/crédito da fatura abate primeiro os fixos e depois
    # os compromissos lançados no MESMO cartão. Pix/débito/empréstimos nunca
    # são abatidos. Só o que sobrar continua como crédito disponível.
    fixos_cobertos_fatura = 0.0
    compromissos_cobertos_fatura = 0.0
    if saldo_fatura < 0:
        fixos_cobertos_fatura = min(-saldo_fatura, max(0.0, fixos_cartao))
        saldo_fatura += fixos_cobertos_fatura
        total_fixos -= fixos_cobertos_fatura
    if saldo_fatura < 0:
        compromissos_cobertos_fatura = min(-saldo_fatura, max(0.0, compromissos_cartao))
        saldo_fatura += compromissos_cobertos_fatura
        total_compromissos -= compromissos_cobertos_fatura
    if fixos_cobertos_fatura or compromissos_cobertos_fatura:
        # Evita resíduo de ponto flutuante (ex.: 2e-14) virando linha "R$ 0,00".
        if abs(total_fixos) < 0.005:
            total_fixos = 0.0
        if abs(total_compromissos) < 0.005:
            total_compromissos = 0.0
        if abs(saldo_fatura) < 0.005:
            saldo_fatura = 0.0
    fatura_a_pagar = max(0.0, saldo_fatura)
    total_a_pagar = fatura_a_pagar + total_fixos + total_emprestimos + total_compromissos
    credito_disponivel = max(0.0, -saldo_fatura)
    possui_fatura = bool(
        total_fatura_bruta
        or fatura.get("movimentos")
        or fatura.get("conferencia")
        or fatura.get("credito_herdado")
    )

    return {
        "fatura": fatura_a_pagar,
        "fatura_bruta": total_fatura_bruta,
        "fixos": total_fixos,
        "emprestimos": total_emprestimos,
        "compromissos": total_compromissos,
        "total": total_a_pagar,
        "saldo_fatura": saldo_fatura,
        "credito_disponivel": credito_disponivel,
        "fixos_cobertos_fatura": fixos_cobertos_fatura,
        "compromissos_cobertos_fatura": compromissos_cobertos_fatura,
        "credito_herdado": float(fatura.get("credito_herdado") or 0),
        "creditos": float(fatura.get("creditos") or 0),
        "pagamentos": float(fatura.get("pagamentos") or 0),
        "ajustes_debito": float(fatura.get("ajustes_debito") or 0),
        "ajuste_conferencia": float(fatura.get("ajuste_conferencia") or 0),
        "fonte_fatura": fatura.get("fonte_fatura"),
        "possui_dados": bool(itens or fatura.get("movimentos") or possui_fatura),
        "possui_fatura": possui_fatura,
    }

def detalhar_pagamento_por_conta(ano_mes: str, termo: str):
    """Detalha exatamente os valores usados no resumo de pagamento da conta."""
    fatura = calcular_fatura_unificada(ano_mes, termo)
    resumo = calcular_resumo_pagamento_conta(ano_mes, termo)
    titulo = normalizar(termo).title()

    if not resumo["possui_dados"]:
        return f"Não encontrei pagamentos pendentes para {titulo} em {formatar_ano_mes_visual(ano_mes)}."

    grupos = {"fatura": [], "fixos": [], "emprestimos": [], "compromissos": []}
    for item in fatura.get("itens") or []:
        try:
            tipo = texto_chave(item.get("tipo") or "")
            origem = texto_chave(item.get("origem") or "")
            valor = float(item.get("valor") or 0)
        except (AttributeError, TypeError, ValueError):
            continue

        nome = str(item.get("nome") or item.get("descricao") or "Lançamento").strip()
        identificador = item.get("id")
        prefixo = ""
        if origem == "compromisso" and identificador:
            prefixo = f"#C{identificador} · "
        elif origem == "transacao" and identificador:
            prefixo = f"#{identificador} · "
        linha = f"• {prefixo}{nome}: {formatar_moeda(valor)}"

        if classificar_natureza_pagamento(item) == "emprestimos":
            grupos["emprestimos"].append(linha)
        elif tipo == "fixo":
            grupos["fixos"].append(linha)
        elif tipo == "avulso" or (origem == "compromisso" and tipo not in {"parcelamento"}):
            grupos["compromissos"].append(linha)
        else:
            grupos["fatura"].append(linha)

    linhas = [f"🏦 {titulo} — {formatar_ano_mes_visual(ano_mes)}", ""]

    if resumo["possui_fatura"]:
        linhas.append(f"💳 Fatura/cartão — {formatar_moeda(resumo['fatura'])}")
        linhas.extend(grupos["fatura"] or ["• Nenhum lançamento bruto pendente."])

        credito_herdado = float(fatura.get("credito_herdado") or 0)
        creditos = float(fatura.get("creditos") or 0)
        pagamentos = float(fatura.get("pagamentos") or 0)
        ajustes = float(fatura.get("ajustes_debito") or 0)
        if credito_herdado:
            linhas.append(f"• Crédito anterior: -{formatar_moeda(credito_herdado)}")
        if creditos:
            linhas.append(f"• Créditos/estornos: -{formatar_moeda(creditos)}")
        if pagamentos:
            linhas.append(f"• Pagamentos registrados: -{formatar_moeda(pagamentos)}")
        if ajustes:
            linhas.append(f"• Ajustes de débito: +{formatar_moeda(ajustes)}")
        linhas.append("")

    fixos_cobertos = float(resumo.get("fixos_cobertos_fatura") or 0)
    if resumo["fixos"] or fixos_cobertos > 0.005:
        linhas.append(f"🔁 Fixos — {formatar_moeda(resumo['fixos'])}")
        linhas.extend(grupos["fixos"])
        if fixos_cobertos > 0.005:
            linhas.append(f"• Coberto pelo pagamento/crédito da fatura: -{formatar_moeda(fixos_cobertos)}")
        linhas.append("")

    if resumo.get("emprestimos"):
        linhas.append(f"🤝 Empréstimos — {formatar_moeda(resumo['emprestimos'])}")
        linhas.extend(grupos["emprestimos"])
        linhas.append("")

    compromissos_cobertos = float(resumo.get("compromissos_cobertos_fatura") or 0)
    if resumo["compromissos"] or compromissos_cobertos > 0.005:
        linhas.append(f"📝 Compromissos — {formatar_moeda(resumo['compromissos'])}")
        linhas.extend(grupos["compromissos"])
        if compromissos_cobertos > 0.005:
            linhas.append(f"• Coberto pelo pagamento/crédito da fatura: -{formatar_moeda(compromissos_cobertos)}")
        linhas.append("")

    linhas.extend([
        "────────────────────",
        f"TOTAL A PAGAR: {formatar_moeda(resumo['total'])}",
    ])
    return "\n".join(linhas)


def resumo_pagamento_por_conta(ano_mes: str, termo: str):
    """Retorna um resumo objetivo do valor necessário por conta."""
    resumo = calcular_resumo_pagamento_conta(ano_mes, termo)
    titulo = normalizar(termo).title()

    if not resumo["possui_dados"]:
        return f"Não encontrei pagamentos pendentes para {titulo} em {formatar_ano_mes_visual(ano_mes)}."

    linhas = [
        f"🏦 {titulo} — {formatar_ano_mes_visual(ano_mes)}",
        "",
    ]

    if resumo["possui_fatura"]:
        linhas.append(f"💳 Fatura/cartão: {formatar_moeda(resumo['fatura'])}")
    if resumo["fixos"]:
        linhas.append(f"🔁 Fixos: {formatar_moeda(resumo['fixos'])}")
    if resumo.get("emprestimos"):
        linhas.append(f"🤝 Empréstimos: {formatar_moeda(resumo['emprestimos'])}")
    if resumo["compromissos"]:
        linhas.append(f"📝 Compromissos: {formatar_moeda(resumo['compromissos'])}")

    linhas.extend([
        "",
        "────────────────────",
        f"TOTAL A PAGAR: {formatar_moeda(resumo['total'])}",
    ])

    if resumo["saldo_fatura"] < -0.005:
        linhas.extend(["", f"Crédito disponível na fatura: {formatar_moeda(abs(resumo['saldo_fatura']))}"])

    return "\n".join(linhas)


def resumo_pagamento_mes_consolidado(ano_mes: str):
    """Consolida as obrigações pendentes do mês em todas as contas.

    Transações já realizadas por Pix, débito, dinheiro e transferência não
    entram. Fixos, parcelas, compromissos e saldos de fatura pendentes entram.
    """
    itens = obter_itens_base_pagamentos_mes(ano_mes, incluir_transacoes=True)
    movimentos = _listar_fatura_movimentos_consulta(ano_mes)

    def nome_conta_seguro(valor):
        texto = str(valor or "").strip()
        return texto or "Não informada"

    contas = set()
    for item in itens:
        try:
            if item_entra_no_quanto_vou_pagar(item):
                contas.add(nome_conta_seguro(item.get("conta_pagamento")))
        except (AttributeError, TypeError, ValueError):
            # Um registro legado ou malformado não pode derrubar a consulta inteira.
            continue

    for movimento in movimentos:
        try:
            contas.add(nome_conta_seguro(movimento.get("conta_cartao")))
        except (AttributeError, TypeError, ValueError):
            continue

    resultados = []
    avisos = []
    for conta in sorted(contas, key=texto_chave):
        try:
            resumo = calcular_resumo_pagamento_conta(ano_mes, conta)
        except Exception as exc:  # inclui ConciliacaoError
            # Isola a conta com problema, preserva as demais e AVISA o titular:
            # o total fica calculável, mas nunca em silêncio.
            _LOG.error(
                "Falha ao calcular resumo da conta %r em %s: %s",
                conta, ano_mes, exc, exc_info=True,
            )
            motivo = str(exc).strip() or type(exc).__name__
            avisos.append(
                f"⚠️ Não foi possível calcular a conta {conta}: {motivo}; "
                "o total pode estar incompleto."
            )
            continue
        if resumo.get("possui_dados") and float(resumo.get("total") or 0) > 0.005:
            resultados.append((normalizar(conta).title(), resumo))

    if not resultados:
        if avisos:
            return "\n".join([
                f"📅 {formatar_ano_mes_visual(ano_mes)}", "", *avisos,
            ])
        return f"Não encontrei pagamentos pendentes para {formatar_ano_mes_visual(ano_mes)}."

    total_faturas = sum(float(r.get("fatura") or 0) for _, r in resultados)
    total_fixos = sum(float(r.get("fixos") or 0) for _, r in resultados)
    total_emprestimos = sum(float(r.get("emprestimos") or 0) for _, r in resultados)
    total_compromissos = sum(float(r.get("compromissos") or 0) for _, r in resultados)
    total_geral = sum(float(r.get("total") or 0) for _, r in resultados)

    linhas = [f"📅 {formatar_ano_mes_visual(ano_mes)}", ""]
    if total_faturas:
        linhas.append(f"💳 Faturas: {formatar_moeda(total_faturas)}")
    if total_fixos:
        linhas.append(f"🔁 Fixos: {formatar_moeda(total_fixos)}")
    if total_emprestimos:
        linhas.append(f"🤝 Empréstimos: {formatar_moeda(total_emprestimos)}")
    if total_compromissos:
        linhas.append(f"📝 Compromissos: {formatar_moeda(total_compromissos)}")

    linhas.extend(["", "Por conta:"])
    for conta, resumo in sorted(resultados, key=lambda x: float(x[1].get("total") or 0), reverse=True):
        linhas.append(f"🏦 {conta}: {formatar_moeda(float(resumo.get('total') or 0))}")

    linhas.extend([
        "",
        "────────────────────",
        f"TOTAL A PAGAR: {formatar_moeda(total_geral)}",
    ])
    if avisos:
        linhas.extend(["", *avisos])
    return "\n".join(linhas)


def resumo_contas_mes(ano_mes: str):
    return resumo_contas_mes_quebrado(ano_mes)


def listar_fixos_formatado(filtro: str | None = None):
    # Condições encerradas permanecem ativas para preservar a projeção histórica.
    # A listagem atual usa a mesma regra de vigência do motor financeiro.
    ano_mes_atual = relogio.hoje(date).strftime("%Y-%m")
    fixos = [
        c for c in listar_compromissos(tipo="fixo")
        if c["ativo"] and compromisso_ocorre_no_mes(c, ano_mes_atual)
    ]

    if filtro:
        filtro_normalizado = texto_chave(filtro)
        fixos = [
            c for c in fixos
            if filtro_normalizado in texto_chave(c["nome"])
            or filtro_normalizado in texto_chave(c["categoria"])
            or filtro_normalizado in texto_chave(obter_conta_pagamento_efetiva(c))
            or filtro_normalizado in texto_chave(c["forma_pagamento"])
            or filtro_normalizado in texto_chave(obter_destino_pagamento_efetivo(c))
        ]

    if not fixos:
        return "🔁 Fixos ativos\n\nNão encontrei fixos ativos."

    total = sum(c["valor"] or 0 for c in fixos)
    linhas = [
        "🔁 Fixos ativos",
        "",
        bloco_total("Resumo", [
            linha_valor("Total mensal", total),
            f"│ {'Itens':<24} {len(fixos):>14}",
        ]),
    ]

    for c in fixos:
        conta = obter_conta_pagamento_efetiva(c) or "Não informada"
        forma = c["forma_pagamento"] or "não informada"
        destino = obter_destino_pagamento_efetivo(c)
        linhas.extend([
            "",
            f"┌ #C{c['id']} · {c['nome']}",
            f"│ 💸 {formatar_moeda(c['valor'])}",
            f"│ 📅 dia {c['dia_vencimento']}",
            f"│ 🏦 Conta: {conta}",
            f"│ 💳 Forma: {forma}",
        ])
        if destino:
            linhas.append(f"│ 👤 Destino: {destino}")
        linhas.extend([
            f"│ 🏷 {c['categoria']}",
            "└",
        ])

    linhas.extend([
        "",
        "Comandos úteis:",
        "alterar fixo 1 para 250",
        "alterar vencimento fixo 1 para dia 10",
        "pausar fixo 1",
    ])
    return "\n".join(linhas)


def listar_compromissos_formatado(tipo: str | None = None):
    compromissos = listar_compromissos(tipo=tipo)

    if not compromissos:
        return "Não encontrei compromissos cadastrados."

    titulo = "📋 Compromissos" if not tipo else f"📋 Compromissos: {tipo}"
    linhas = [titulo, ""]

    for c in compromissos:
        status = "ativo" if c["ativo"] else "pausado"
        fim = c["data_fim"][:7] if c["data_fim"] else "sem fim"
        parcelas = f" | {c['parcelas_total']}x" if c["parcelas_total"] else ""
        conta = obter_conta_pagamento_efetiva(c) or "Não informada"
        forma = c["forma_pagamento"] or "não informada"
        destino = obter_destino_pagamento_efetivo(c)
        pagamento = f"Conta: {conta} | Forma: {forma}"
        if destino:
            pagamento += f" | Destino: {destino}"
        linhas.append(
            f"#{c['id']} | {status} | {c['tipo']} | {c['nome']} | {formatar_moeda(c['valor'])} | "
            f"{pagamento} | {c['data_inicio'][:7]} até {fim}{parcelas}"
        )

    return "\n".join(linhas)


def alterar_fixo_valor(compromisso_id: int, novo_valor: float):
    antes = buscar_compromisso_por_id(compromisso_id)

    if not antes:
        return f"🔁 Fixo\n\nNão encontrei fixo/compromisso #{compromisso_id}."

    if antes["tipo"] != "fixo":
        return f"🔁 Fixo\n\nO compromisso #{compromisso_id} não é fixo. Tipo atual: {antes['tipo']}."

    depois = atualizar_valor_compromisso(compromisso_id, novo_valor)

    return "\n".join([
        "🔁 Fixo atualizado",
        "",
        bloco_total(f"#C{depois['id']} · {depois['nome']}", [
            linha_valor("Valor antigo", antes["valor"]),
            linha_valor("Novo valor", depois["valor"]),
        ]),
    ])


def alterar_fixo_vencimento(compromisso_id: int, novo_dia: int):
    if novo_dia < 1 or novo_dia > 31:
        return "📅 Vencimento\n\nDia inválido. Use um dia entre 1 e 31."

    antes = buscar_compromisso_por_id(compromisso_id)

    if not antes:
        return f"📅 Vencimento\n\nNão encontrei fixo/compromisso #{compromisso_id}."

    if antes["tipo"] != "fixo":
        return f"📅 Vencimento\n\nO compromisso #{compromisso_id} não é fixo. Tipo atual: {antes['tipo']}."

    depois = atualizar_vencimento_compromisso(compromisso_id, novo_dia)

    return "\n".join([
        "📅 Vencimento do fixo atualizado",
        "",
        f"┌ #C{depois['id']} · {depois['nome']}",
        f"│ Antes: dia {antes['dia_vencimento']}",
        f"│ Agora: dia {depois['dia_vencimento']}",
        "└",
    ])


def normalizar_conta_pagamento_usuario(conta: str):
    texto = (conta or "").strip().lower()

    if not texto:
        return ""

    texto = re.sub(r"\s+", " ", texto)

    if texto in CONTAS_PAGAMENTO:
        return CONTAS_PAGAMENTO[texto]

    aliases = {
        "mercadopago": "Mercado Pago",
        "mp": "Mercado Pago",
        "itaú": "Itaú",
        "itau": "Itaú",
        "banco inter": "Inter",
        "banco btg": "BTG",
        "btg pactual": "BTG",
    }

    if texto in aliases:
        return aliases[texto]

    return conta.strip().title()


def normalizar_forma_pagamento_usuario(forma: str):
    texto = (forma or "").strip().lower()
    texto = re.sub(r"\s+", " ", texto)

    aliases = {
        "pix": "Pix",
        "credito": "Crédito",
        "crédito": "Crédito",
        "cartao credito": "Crédito",
        "cartão crédito": "Crédito",
        "cartao de credito": "Crédito",
        "cartão de crédito": "Crédito",
        "debito": "Débito",
        "débito": "Débito",
        "cartao debito": "Débito",
        "cartão débito": "Débito",
        "cartao de debito": "Débito",
        "cartão de débito": "Débito",
        "dinheiro": "Dinheiro",
        "boleto": "Boleto",
    }

    return aliases.get(texto, forma.strip().title())


def alterar_compromisso_conta(compromisso_id: int, nova_conta: str):
    antes = buscar_compromisso_por_id(compromisso_id)

    if not antes:
        return f"Não encontrei fixo/compromisso #{compromisso_id}."

    nova_conta_normalizada = normalizar_conta_pagamento_usuario(nova_conta)

    if not nova_conta_normalizada:
        return "Conta inválida. Exemplo: alterar conta fixo 1 para BTG"

    # Modelo canônico: Pix/crédito/débito/boleto são forma, nunca conta. Quando o
    # registro já usa conta_origem, não aceitamos uma forma no lugar da conta.
    if (
        "conta_origem" in antes.keys()
        and antes["conta_origem"]
        and texto_chave(nova_conta_normalizada) in {"pix", "credito", "debito", "boleto", "cartao"}
    ):
        return (
            f"'{nova_conta_normalizada}' é forma de pagamento, não conta. "
            "Use alterar forma para mudar a forma ou informe um banco real."
        )

    depois = atualizar_campo_compromisso(compromisso_id, "conta_pagamento", nova_conta_normalizada)

    return (
        "🏦 Conta do compromisso atualizada\n\n"
        f"#{depois['id']} · {depois['nome']}\n"
        f"Conta anterior: {obter_conta_pagamento_efetiva(antes) or 'Não informada'}\n"
        f"Nova conta: {obter_conta_pagamento_efetiva(depois) or 'Não informada'}\n\n"
        "Essa alteração afeta a projeção dos próximos meses e os resumos por conta."
    )


def alterar_compromisso_forma(compromisso_id: int, nova_forma: str):
    antes = buscar_compromisso_por_id(compromisso_id)

    if not antes:
        return f"Não encontrei fixo/compromisso #{compromisso_id}."

    nova_forma_normalizada = normalizar_forma_pagamento_usuario(nova_forma)

    if not nova_forma_normalizada:
        return "Forma inválida. Exemplo: alterar forma fixo 1 para Crédito"

    depois = atualizar_campo_compromisso(compromisso_id, "forma_pagamento", nova_forma_normalizada)

    return (
        "💳 Forma de pagamento atualizada\n\n"
        f"#{depois['id']} · {depois['nome']}\n"
        f"Forma anterior: {antes['forma_pagamento'] or 'Não informada'}\n"
        f"Nova forma: {depois['forma_pagamento'] or 'Não informada'}"
    )


def alterar_compromisso_categoria(compromisso_id: int, nova_categoria: str):
    antes = buscar_compromisso_por_id(compromisso_id)

    if not antes:
        return f"Não encontrei fixo/compromisso #{compromisso_id}."

    nova_categoria = (nova_categoria or "").strip().title()

    if not nova_categoria:
        return "Categoria inválida. Exemplo: alterar categoria fixo 1 para Telefonia"

    depois = atualizar_campo_compromisso(compromisso_id, "categoria", nova_categoria)

    return (
        "🏷 Categoria do compromisso atualizada\n\n"
        f"#{depois['id']} · {depois['nome']}\n"
        f"Categoria anterior: {antes['categoria'] or 'Não informada'}\n"
        f"Nova categoria: {depois['categoria'] or 'Não informada'}"
    )


def pausar_compromisso(compromisso_id: int):
    compromisso = definir_status_compromisso(compromisso_id, False)
    if not compromisso:
        return f"⏸️ Compromisso\n\nNão encontrei compromisso #{compromisso_id}."
    return f"⏸️ Compromisso pausado\n\n#C{compromisso['id']} · {compromisso['nome']}\n{formatar_moeda(compromisso['valor'])}"


def reativar_compromisso(compromisso_id: int):
    compromisso = definir_status_compromisso(compromisso_id, True)
    if not compromisso:
        return f"▶️ Compromisso\n\nNão encontrei compromisso #{compromisso_id}."
    return f"▶️ Compromisso reativado\n\n#C{compromisso['id']} · {compromisso['nome']}\n{formatar_moeda(compromisso['valor'])}"


def apagar_compromisso_formatado(compromisso_id: int):
    from database import ExclusaoCompromissoBloqueadaError
    try:
        compromisso = apagar_compromisso_por_id(compromisso_id)
    except ExclusaoCompromissoBloqueadaError as exc:
        return str(exc)
    if not compromisso:
        return f"🗑️ Compromisso\n\nNão encontrei compromisso #{compromisso_id}."
    return "\n".join([
        "🗑️ Compromisso apagado",
        "",
        bloco_total(f"#C{compromisso['id']} · {compromisso['nome']}", [
            linha_valor("Valor removido", compromisso["valor"]),
        ]),
    ])
