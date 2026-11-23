import re
from decimal import Decimal
from money import parse_money, parse_money_float
from datetime import date, timedelta
from categorias import canonicalizar_categoria, inferir_categoria


NUMEROS_SIMPLES = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "três": 3,
    "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9,
    "dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14,
    "quinze": 15, "dezesseis": 16, "dezasseis": 16, "dezessete": 17,
    "dezoito": 18, "dezenove": 19, "vinte": 20, "trinta": 30, "quarenta": 40,
    "cinquenta": 50, "sessenta": 60, "setenta": 70, "oitenta": 80, "noventa": 90,
    "cem": 100, "cento": 100, "duzentos": 200, "duzentas": 200, "trezentos": 300,
    "trezentas": 300, "quatrocentos": 400, "quatrocentas": 400, "quinhentos": 500,
    "quinhentas": 500, "seiscentos": 600, "seiscentas": 600, "setecentos": 700,
    "setecentas": 700, "oitocentos": 800, "oitocentas": 800, "novecentos": 900,
    "novecentas": 900
}

MULTIPLICADORES = {
    "mil": 1000,
    "milhão": 1000000,
    "milhao": 1000000,
    "milhões": 1000000,
    "milhoes": 1000000
}

PADRAO_MULTIPLICADOR = r"mil|milh[aã]o|milh[oõ]es"

PADRAO_VALOR = r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:[,.]\d{1,2})?)(?![\d.,])"

# dd/mm/aaaa, dd/mm/aa e dd-mm-aaaa (ISO aaaa-mm-dd é tratado à parte).
PADRAO_DATA_BR = r"(?<![\d/-])(\d{1,2})[/-](\d{1,2})[/-](\d{4}|\d{2})(?![\d/-])"


class MaisDeUmValor(ValueError):
    """Duas quantias na mesma frase: o parser não adivinha qual é a certa."""


class DataFutura(ValueError):
    """Lançamento é de algo realizado; "amanhã" não pode cair em hoje."""


def normalizar_texto(texto: str) -> str:
    return texto.lower().strip()


def parece_codigo_ou_texto_longo(texto: str) -> bool:
    texto_limpo = texto.strip()
    texto_lower = texto_limpo.lower()

    if len(texto_limpo) > 500:
        return True

    if texto_limpo.count("\n") >= 4:
        return True

    indicadores_codigo = [
        "def ", "import ", "from ", "return ", "class ", "async def", "await ",
        "conn.execute", "select ", "insert into", "update ", "delete from", "traceback",
        "file \"", "line ", "keyboardinterrupt", "error:", "exception", "{", "}", "```",
        "python app.py", "notepad ", "ctrl + c", "ctrl+s", "ctrl + s"
    ]

    # Fronteira no início: "line " não pode casar em "online 80" nem "class " em "masterclass 90".
    return any(
        re.search((r"(?<!\w)" if indicador[0].isalnum() else "") + re.escape(indicador), texto_lower)
        for indicador in indicadores_codigo
    )


def texto_numero_para_float(texto: str):
    texto = texto.lower().strip().replace(" reais", "").replace(" real", "").replace(" e ", " ")
    palavras = texto.split()

    if not palavras:
        return None

    total = 0
    grupo = 0
    encontrou_numero = False

    for palavra in palavras:
        if palavra in NUMEROS_SIMPLES:
            grupo += NUMEROS_SIMPLES[palavra]
            encontrou_numero = True
        elif palavra in MULTIPLICADORES:
            multiplicador = MULTIPLICADORES[palavra]
            if grupo == 0:
                grupo = 1
            grupo *= multiplicador
            total += grupo
            grupo = 0
            encontrou_numero = True
        else:
            return None

    total += grupo
    return float(total) if encontrou_numero else None


MESES_NOME = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4, "maio": 5,
    "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}
DIAS_SEMANA = {
    "segunda": 0, "terca": 1, "terça": 1, "quarta": 2, "quinta": 3, "sexta": 4,
    "sabado": 5, "sábado": 5, "domingo": 6,
}
_RX_MES = "|".join(sorted(MESES_NOME, key=len, reverse=True))
_RX_SEMANA = "|".join(sorted(DIAS_SEMANA, key=len, reverse=True))
# Expressões de data curtas ou naturais ("15/10", "dia 15", "15 de outubro",
# "na segunda"). Cada uma cobre o prefixo "dia"/"na"/"no" para não sobrar na
# descrição. O texto deve estar em minúsculas (acentos opcionais).
PADRAO_EXPRESSAO_DATA = (
    rf"(?:\bdia\s+)?(?<![\d/])\d{{1,2}}\s+de\s+(?:{_RX_MES})\b"
    r"|(?:\bdia\s+)?(?<![\d/])\d{1,2}/\d{1,2}(?:/\d{4}|/\d{2})?(?![\d/])"
    r"|\bdia\s+\d{1,2}\b(?!\s*(?:/|de\b|reais?\b|centavos?\b|,|\.\d))"
    rf"|\b(?:(?:na|no)\s+)?(?:{_RX_SEMANA})(?:-feira)?\b(?!\s+(?:via|parcela|vez|pagina))"
)
PERIODO_DO_DIA = r"(?:\s+(?:[aà]\s+noite|[aà]\s+tarde|de\s+manh[aã]|de\s+madrugada))?"
EXPRESSAO_DATA_VAGA = r"\b(?:semana|mes|mês|ano)\s+passad[oa]\b|\b(?:semana|mes|mês)\s+retrasad[oa]\b"


def interpretar_expressao_data(expressao: str, hoje: date):
    """Converte uma data curta/natural em ``date``; ``None`` se não for uma.

    "15/10" é dia/mês do ano de ``hoje`` e nunca futura; "dia 15" é o dia 15 do
    mês corrente (ou do anterior, se ainda não chegou); "segunda" é a última
    segunda-feira já passada (uma semana atrás se hoje for segunda). Datas
    futuras ou inexistentes levantam ValueError com mensagem acionável.
    """
    texto = re.sub(r"\s+", " ", expressao.strip().lower())
    m = re.fullmatch(rf"(?:dia )?(\d{{1,2}}) de ({_RX_MES})", texto)
    if m:
        return _resolver_dia_mes(int(m[1]), MESES_NOME[m[2]], hoje, m[0])
    m = re.fullmatch(r"(?:dia )?(\d{1,2})/(\d{1,2})(?:/(\d{4}|\d{2}))?", texto)
    if m:
        dia, mes = int(m[1]), int(m[2])
        if m[3]:
            ano = int(m[3]) + (2000 if len(m[3]) == 2 else 0)
            try:
                return date(ano, mes, dia)
            except ValueError:
                raise ValueError("Essa data não existe. Confira o dia e o mês.")
        return _resolver_dia_mes(dia, mes, hoje, f"{dia:02d}/{mes:02d}")
    m = re.fullmatch(r"dia (\d{1,2})", texto)
    if m:
        dia = int(m[1])
        ano, mes = hoje.year, hoje.month
        if dia > hoje.day:
            mes, ano = (12, ano - 1) if mes == 1 else (mes - 1, ano)
        try:
            return date(ano, mes, dia)
        except ValueError:
            raise ValueError(f"O dia {dia} não existe no mês {mes:02d}/{ano}. Informe DD/MM.")
    m = re.fullmatch(rf"(?:(?:na|no) )?({_RX_SEMANA})(?:-feira)?", texto)
    if m:
        atras = (hoje.weekday() - DIAS_SEMANA[m[1]]) % 7 or 7
        return hoje - timedelta(days=atras)
    return None


def _resolver_dia_mes(dia: int, mes: int, hoje: date, rotulo: str):
    try:
        data = date(hoje.year, mes, dia)
    except ValueError:
        raise ValueError("Essa data não existe. Confira o dia e o mês.")
    if data > hoje:
        raise DataFutura(
            f"{rotulo} ainda não chegou neste ano. Se for de outro ano, informe DD/MM/AAAA.")
    return data


def expressoes_de_data(texto: str):
    """Ocorrências de data curta/natural, ignorando "(3/10)" (notação de parcela)."""
    achados = []
    for m in re.finditer(PADRAO_EXPRESSAO_DATA, texto):
        if texto[max(0, m.start() - 1):m.start()] == "(" and texto[m.end():m.end() + 1] == ")":
            continue
        achados.append(m)
    return achados


PALAVRAS_DE_PRODUTO = {
    "iphone", "ipad", "galaxy", "redmi", "poco", "pixel", "moto", "playstation",
    "ps", "xbox", "windows", "macbook", "airpods", "serie", "série", "gen",
}


def numero_e_de_produto(texto: str, inicio: int) -> bool:
    """O número vem colado a um nome de produto ("iphone 15"): não é preço."""
    anterior = re.search(r"([a-zà-ÿ0-9]+)\s+$", texto[:inicio])
    return bool(anterior and anterior.group(1) in PALAVRAS_DE_PRODUTO)


def texto_com_varios_lancamentos(texto: str):
    """Quantidade de lançamentos em texto multilinha (0 se for uma só frase)."""
    linhas = [l for l in re.split(r"[\r\n]+", texto) if l.strip()]
    if len(linhas) < 2:
        return 0
    sinais = [l for l in linhas if re.search(r"\d", l)]
    return len(sinais) if len(sinais) >= 2 else 0


def mensagem_varios_lancamentos(quantidade: int) -> str:
    return (f"Encontrei {quantidade} lançamentos nesta mensagem. Nada foi registrado. "
            "Envie um por vez para eu conferir cada um antes de salvar.")


def converter_valor_numerico(valor_texto: str):
    return parse_money_float(valor_texto)


def encontrar_numeros(texto: str):
    padrao = rf"(?:r\$\s*)?{PADRAO_VALOR}"
    encontrados = []

    for match in re.finditer(padrao, texto):
        valor_texto = match.group(1)
        encontrados.append({
            "valor": converter_valor_numerico(valor_texto),
            "inicio": match.start(),
            "fim": match.end(),
            "texto": valor_texto
        })

    return encontrados


def detectar_valor_total_por_parcela(texto: str):
    padroes = [
        rf"(?:em\s+)?(\d{{1,2}})x\s+de\s+(?:r\$\s*)?{PADRAO_VALOR}",
        rf"(?:em\s+)?(\d{{1,2}})\s+parcelas\s+de\s+(?:r\$\s*)?{PADRAO_VALOR}",
        rf"(?:em\s+)?(\d{{1,2}})\s+vezes\s+de\s+(?:r\$\s*)?{PADRAO_VALOR}",
        rf"parcelado\s+em\s+(\d{{1,2}})\s+parcelas\s+de\s+(?:r\$\s*)?{PADRAO_VALOR}",
        rf"parcelado\s+em\s+(\d{{1,2}})\s+vezes\s+de\s+(?:r\$\s*)?{PADRAO_VALOR}",
        rf"dividido\s+em\s+(\d{{1,2}})\s+parcelas\s+de\s+(?:r\$\s*)?{PADRAO_VALOR}",
        rf"dividido\s+em\s+(\d{{1,2}})\s+vezes\s+de\s+(?:r\$\s*)?{PADRAO_VALOR}",
    ]

    for padrao in padroes:
        match = re.search(padrao, texto)
        if match:
            parcelas = int(match.group(1))
            valor_parcela = converter_valor_numerico(match.group(2))
            if parcelas > 1:
                return round(parcelas * valor_parcela, 2)

    return None


def numero_esta_em_contexto_de_data(texto: str, numero: dict):
    """Evita que partes de datas ISO sejam interpretadas como valor monetário."""
    for match in re.finditer(r"\b20\d{2}-\d{2}-\d{2}\b", texto):
        if numero["inicio"] < match.end() and numero["fim"] > match.start():
            return True
    # "(3/10)" é notação de parcela, não valores.
    for match in re.finditer(r"\(\s*\d{1,2}\s*/\s*\d{1,2}\s*\)", texto):
        if numero["inicio"] < match.end() and numero["fim"] > match.start():
            return True
    return False


def numero_esta_em_contexto_de_parcela(texto: str, numero: dict):
    """Marca somente o numero que representa a quantidade de parcelas.

    A versao anterior procurava qualquer padrao de parcelamento em uma janela de
    dezenas de caracteres ao redor do numero. Em frases como "1200 em 12x", isso
    fazia o valor 1200 ser descartado apenas porque 12x aparecia perto dele.
    """
    inicio=numero["inicio"]
    fim=numero["fim"]
    depois=texto[fim:fim+20]
    antes=texto[max(0,inicio-20):inicio]
    # O proprio token e seguido por x, "parcelas" ou "vezes".
    if re.match(r"\s*(?:x\b|parcelas\b|vezes\b)",depois):
        return True
    # Formas como "parcelado em 12" sem sufixo tambem indicam quantidade.
    return bool(re.search(r"(?:feito em|parcelado em|dividido em)\s*$",antes))


def aplicar_escala(texto: str, fim: int, valor: float):
    """"1,5 mil", "R$ 2 mil": só escala o número que já seria escolhido como valor.

    Números de outras partes da frase ("revisão dos 10 mil km R$ 450") não
    passam na frente do valor monetário.
    """
    escala = re.match(rf"\s+({PADRAO_MULTIPLICADOR})\b", texto[fim:])
    if not escala:
        return valor
    return float(parse_money(valor) * MULTIPLICADORES[escala.group(1)])


def _numero_tem_marca_de_dinheiro(texto: str, numero: dict):
    """R$ antes, "reais" depois ou casas decimais/milhar: é uma quantia, não um código."""
    if texto[numero["inicio"]:numero["inicio"] + 2] == "r$":
        return True
    if re.match(r"\s+(?:reais|real)\b", texto[numero["fim"]:]):
        return True
    return bool(re.search(r"[.,]", numero["texto"]))


_ANTES_DE_PRECO = r"(?:\bpor|\bcustou|\bvalor de)\s+(?:r\$\s*)?$"
_ANTES_DE_VERBO = r"(?:gastei|paguei|comprei|recebi|ganhei|de|no|na|em|com|por|custou|r\$)\s*$"
_UNIDADE_DEPOIS = r"\s*(?:dias?|mes(?:es)?|semanas?|horas?|anos?|pessoas?|km|itens?|unidades?)\b"


def _escolher_candidato(texto: str, candidatos: list):
    """Primeiro candidato, exceto quando ele é número do nome do item.

    "comprei iphone 15 por 5000": 15 vem colado a uma palavra do item e o preço
    vem depois de por/custou/valor de.
    """
    primeiro = candidatos[0]
    if len(candidatos) == 1 or re.search(_ANTES_DE_VERBO, texto[:primeiro["inicio"]]):
        return primeiro
    for numero in candidatos[1:]:
        if (re.search(_ANTES_DE_PRECO, texto[max(0, numero["inicio"] - 14):numero["inicio"]])
                and not re.match(_UNIDADE_DEPOIS, texto[numero["fim"]:])):
            return numero
    return primeiro


def extrair_valor_numerico(texto: str):
    valor_total_por_parcela = detectar_valor_total_por_parcela(texto)
    if valor_total_por_parcela is not None:
        return valor_total_por_parcela

    # "1,5k", "2k": mil, sem espaço (kg/km não casam por causa do \b).
    valores_k = re.findall(r"(?<![\w.,])(\d+(?:[.,]\d{1,2})?)k\b", texto)
    if len(valores_k) > 1:
        raise MaisDeUmValor("mais de um valor")
    if valores_k:
        return float(parse_money(valores_k[0]) * 1000)

    # "3 mil e 500 reais" / "1 mil e 500": o "e" soma centenas ao milhar.
    match_mil_e = re.search(
        r"(?:r\$\s*)?(?<![\d.,])(\d{1,3})\s+mil\s+e\s+(\d{1,3})(?![\d.,])(?:\s+(?:reais|real)\b)?", texto)
    if match_mil_e:
        return float(parse_money(match_mil_e.group(1)) * 1000 + parse_money(match_mil_e.group(2)))

    valores_rs = {converter_valor_numerico(m.group(1)) for m in re.finditer(rf"r\$\s*{PADRAO_VALOR}", texto)}
    if len(valores_rs) > 1:
        raise MaisDeUmValor("mais de um valor")
    match_rs = re.search(rf"r\$\s*{PADRAO_VALOR}", texto)
    if match_rs:
        return aplicar_escala(texto, match_rs.end(1), converter_valor_numerico(match_rs.group(1)))

    match_reais = re.search(rf"{PADRAO_VALOR}\s+(?:reais|real)\b(?:\s+e\s+(\d{{1,2}})\s+centavos?\b)?", texto)
    if match_reais:
        valor = parse_money(match_reais.group(1))
        if match_reais.group(2):
            # Voz costuma transcrever R$ 10,50 como "10 reais e 50 centavos".
            valor += Decimal(int(match_reais.group(2))) / 100
        return float(valor)

    numeros = encontrar_numeros(texto)
    if not numeros:
        return None

    candidatos = [
        numero for numero in numeros
        if not numero_esta_em_contexto_de_parcela(texto, numero)
        and not numero_esta_em_contexto_de_data(texto, numero)
    ]
    quantias = {n["valor"] for n in candidatos if _numero_tem_marca_de_dinheiro(texto, n)}
    if len(quantias) > 1:
        raise MaisDeUmValor("mais de um valor")
    # "iphone 15" não tem preço: o número do modelo nunca vira valor.
    candidatos = [n for n in candidatos
                  if _numero_tem_marca_de_dinheiro(texto, n) or not numero_e_de_produto(texto, n["inicio"])]
    if not candidatos:
        return None
    if len(candidatos) > 1 and not quantias:
        primeiro = candidatos[0]
        tem_preco = any(
            re.search(_ANTES_DE_PRECO, texto[max(0, n["inicio"] - 14):n["inicio"]])
            and not re.match(_UNIDADE_DEPOIS, texto[n["fim"]:]) for n in candidatos[1:])
        if not re.search(_ANTES_DE_VERBO, texto[:primeiro["inicio"]]) and not tem_preco:
            # Dois números soltos sem verbo/por/R$ antes: não adivinha qual é o valor.
            livres = [n for n in candidatos if not re.match(_UNIDADE_DEPOIS, texto[n["fim"]:])]
            if len(livres) > 1:
                raise MaisDeUmValor("mais de um valor")
            if len(livres) == 1:
                candidatos = livres
    if candidatos:
        # Em linguagem natural, o primeiro número monetário fora de parcelas/data
        # é mais seguro que escolher o maior número da frase.
        escolhido = _escolher_candidato(texto, candidatos)
        return aplicar_escala(texto, escolhido["fim"], escolhido["valor"])

    return None


def extrair_valor_por_extenso(texto: str):
    match = re.search(r"\b([a-záéíóúâêôãõç\s]+?)\s+(?:reais|real)\b", texto, re.IGNORECASE)
    if not match:
        return None

    trecho = match.group(1).strip()
    palavras_trecho = trecho.split()

    for i in range(len(palavras_trecho)):
        tentativa = " ".join(palavras_trecho[i:])
        valor = texto_numero_para_float(tentativa)
        if valor is not None:
            return valor

    return None


def extrair_valor(texto: str):
    valor_numerico = extrair_valor_numerico(texto)
    if valor_numerico is not None:
        return valor_numerico
    return extrair_valor_por_extenso(texto)


def detectar_categoria_explicita(texto_original: str):
    match = re.search(r"\bcategoria\s+(.+)$", texto_original, re.IGNORECASE)
    if not match:
        return None
    categoria = match.group(1).strip()
    return canonicalizar_categoria(categoria.title()) if categoria else None


def limpar_categoria_explicita(texto_original: str):
    return re.sub(r"\bcategoria\s+(.+)$", "", texto_original, flags=re.IGNORECASE).strip()


def detectar_parcelas(texto: str):
    padroes = [
        r"(?:em\s+)?(\d{1,2})x\b",
        r"(?:em|feito em|parcelado em|dividido em)\s+(\d{1,2})\s+vezes\b",
        r"(?:em|feito em|parcelado em|dividido em)\s+(\d{1,2})\s+parcelas\b",
        r"(\d{1,2})\s+vezes\b",
        r"(\d{1,2})\s+parcelas\b"
    ]

    for padrao in padroes:
        match = re.search(padrao, texto)
        if match:
            parcelas = int(match.group(1))
            return parcelas if parcelas >= 1 else 1

    return 1


def detectar_data(texto: str, hoje=None):
    match_iso = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", texto)
    if match_iso:
        return date.fromisoformat(match_iso.group(1))

    if re.search(r"\bamanh[aã]\b", texto):
        raise DataFutura("data futura")

    match_br = re.search(PADRAO_DATA_BR, texto)
    if match_br:
        dia, mes, ano = map(int, match_br.groups())
        if ano < 100:
            ano += 2000
        return date(ano, mes, dia)

    hoje = hoje or date.today()
    # "15/10", "dia 15", "15 de outubro", "segunda": resolvidas contra ``hoje``
    # (ano corrente, nunca futuras). "(3/10)" é notação de parcela, não data.
    if re.search(EXPRESSAO_DATA_VAGA, texto):
        raise ValueError("data vaga")
    datas = {interpretar_expressao_data(m.group(0), hoje) for m in expressoes_de_data(texto)}
    datas.discard(None)
    if len(datas) > 1:
        raise ValueError("mais de uma data")
    if datas:
        return datas.pop()

    if "anteontem" in texto:
        return hoje - timedelta(days=2)
    if "ontem" in texto:
        return hoje - timedelta(days=1)
    return hoje


def detectar_tipo(texto: str):
    # A descrição pode conter "salário" ou "pix recebido" sem mudar uma despesa.
    if re.match(r'^(gastei|paguei|comprei)\b', texto.strip()):
        return 'despesa'
    if re.match(r'^(recebi|ganhei)\b', texto.strip()):
        return 'receita'
    termos_receita = [
        "recebi", "caiu", "salário", "salario", "pix recebido", "pagamento recebido",
        "ganhei", "entrada de dinheiro"
    ]

    if any(termo in texto for termo in termos_receita):
        # "o celular caiu e gastei 300" tem sinal de entrada e de saída ao mesmo
        # tempo. Antes virava receita; agora fica para o usuário esclarecer.
        if re.search(r"\b(gastei|paguei|comprei)\b", texto):
            return "ambiguo"
        return "receita"

    return "despesa"


def detectar_categoria(texto: str, tipo: str, categoria_explicita=None):
    if categoria_explicita:
        return canonicalizar_categoria(categoria_explicita)

    return inferir_categoria(texto, tipo)


def detectar_forma_pagamento(texto: str, parcelas: int = 1):
    if "pix" in texto:
        return "pix"

    if "boleto" in texto:
        return "boleto"

    if "débito" in texto or "debito" in texto:
        return "débito"

    if "crédito" in texto or "credito" in texto:
        return "crédito"

    if "cartão" in texto or "cartao" in texto:
        return "crédito"

    if "dinheiro" in texto:
        return "dinheiro"

    if parcelas > 1:
        return "crédito"

    return None


def detectar_conta(texto: str):
    contas = {
        "mercado pago": "Mercado Pago",
        "mp ": "Mercado Pago",
        "nubank": "Nubank",
        "nu bank": "Nubank",
        "nu": "Nubank",
        "it": "Itaú",
        "btg": "BTG",
        "inter": "Inter",
        "itaú": "Itaú",
        "itau": "Itaú",
        "bradesco": "Bradesco",
        "santander": "Santander",
        "caixa": "Caixa",
        "banco do brasil": "Banco do Brasil",
        "bb": "Banco do Brasil",
        "picpay": "PicPay",
        "c6": "C6",
        "c6bank": "C6",
        "mercadopago": "Mercado Pago",
        "willbank": "Will",
        "neon": "Neon",
        "will": "Will",
        "xp": "XP",
    }

    for termo, conta in contas.items():
        if re.search(rf"(?<!\w){re.escape(termo.strip())}(?!\w)", texto):
            return conta

    forma = detectar_forma_pagamento(texto)
    if forma == "pix":
        return "Pix"
    if forma == "boleto":
        return "Boleto"

    return None


def limpar_descricao(texto_original: str, valor=None):
    texto = texto_original.strip()
    texto_lower = texto.lower().strip()

    # Remove padrões completos de parcelamento antes de limpar números soltos.
    padroes_parcelamento = [
        rf"\bem\s+\d{{1,2}}x\s+de\s+(?:r\$\s*)?{PADRAO_VALOR}\s*(?:reais|real)?\b",
        rf"\b\d{{1,2}}x\s+de\s+(?:r\$\s*)?{PADRAO_VALOR}\s*(?:reais|real)?\b",
        rf"\bem\s+\d{{1,2}}\s+parcelas\s+de\s+(?:r\$\s*)?{PADRAO_VALOR}\s*(?:reais|real)?\b",
        rf"\b\d{{1,2}}\s+parcelas\s+de\s+(?:r\$\s*)?{PADRAO_VALOR}\s*(?:reais|real)?\b",
        rf"\bem\s+\d{{1,2}}\s+vezes\s+de\s+(?:r\$\s*)?{PADRAO_VALOR}\s*(?:reais|real)?\b",
        rf"\b\d{{1,2}}\s+vezes\s+de\s+(?:r\$\s*)?{PADRAO_VALOR}\s*(?:reais|real)?\b",
        r"\bem\s+\d{1,2}x\b",
        r"\b\d{1,2}x\b",
        r"\bem\s+\d{1,2}\s+parcelas\b",
        r"\bem\s+\d{1,2}\s+vezes\b",
    ]

    for padrao in padroes_parcelamento:
        texto_lower = re.sub(padrao, " ", texto_lower, flags=re.IGNORECASE)

    # Remove forma/conta de pagamento para a descrição ficar curta e útil.
    contas = [
        "mercado pago", "mercadopago", "mp", "nubank", "nu bank", "nu", "it", "btg", "inter", "itaú", "itau",
        "bradesco", "santander", "caixa", "banco do brasil", "picpay", "c6",
        "neon", "will", "xp", "pix", "boleto"
    ]

    contas_regex = "|".join(re.escape(c) for c in contas)

    padroes_pagamento = [
        rf"\b(com|no|na|pelo|pela|por|via)\s+(o\s+|a\s+)?cart[aã]o\s+(de\s+)?(cr[eé]dito|credito|d[eé]bito|debito)?\s*(do|da|de)?\s*({contas_regex})\b",
        rf"\b(com|no|na|pelo|pela|por|via)\s+(o\s+|a\s+)?(cr[eé]dito|credito|d[eé]bito|debito|pix|boleto|dinheiro)\s*(do|da|de)?\s*({contas_regex})?\b",
        rf"\b(com|no|na|pelo|pela|por|via)\s+(o\s+|a\s+)?({contas_regex})\b",
        r"\bcart[aã]o\s+(de\s+)?(cr[eé]dito|credito|d[eé]bito|debito)\b",
        r"\b(cr[eé]dito|credito|d[eé]bito|debito|pix|boleto|dinheiro)\b",
    ]

    for padrao in padroes_pagamento:
        texto_lower = re.sub(padrao, " ", texto_lower, flags=re.IGNORECASE)

    # Remove valores explícitos, preservando números que fazem parte do nome do item
    # como "iPhone 15 Pro Max". Só removemos número quando ele aparece como dinheiro
    # ou precedido por conectores típicos de valor.
    # Valor com "mil" só sai da descrição quando é claramente dinheiro (R$, reais
    # ou fim da frase); "revisão dos 10 mil km" mantém a quilometragem.
    texto_lower = re.sub(r"(?:r\$\s*)?(?<![\d.,])\d{1,3}\s+mil\s+e\s+\d{1,3}(?![\d.,])(?:\s+(?:reais|real)\b)?", " ", texto_lower, flags=re.IGNORECASE)
    texto_lower = re.sub(rf"r\$\s*{PADRAO_VALOR}\s+(?:{PADRAO_MULTIPLICADOR})\b", " ", texto_lower, flags=re.IGNORECASE)
    texto_lower = re.sub(rf"\b{PADRAO_VALOR}\s+(?:{PADRAO_MULTIPLICADOR})\s+(?:reais|real)\b", " ", texto_lower, flags=re.IGNORECASE)
    texto_lower = re.sub(rf"\b{PADRAO_VALOR}\s+(?:{PADRAO_MULTIPLICADOR})\s*$", " ", texto_lower, flags=re.IGNORECASE)
    texto_lower = re.sub(rf"r\$\s*{PADRAO_VALOR}", " ", texto_lower, flags=re.IGNORECASE)
    texto_lower = re.sub(rf"\b{PADRAO_VALOR}\s+(reais|real)\s+e\s+\d{{1,2}}\s+centavos?\b", " ", texto_lower, flags=re.IGNORECASE)
    texto_lower = re.sub(rf"\b{PADRAO_VALOR}\s+(reais|real)\b", " ", texto_lower, flags=re.IGNORECASE)
    texto_lower = re.sub(rf"\b(de|por|valor de|custou)\s+{PADRAO_VALOR}\b", " ", texto_lower, flags=re.IGNORECASE)

    # Remove verbos e palavras operacionais que não ajudam na descrição.
    texto_lower = re.sub(
        r"\b(gastei|paguei|comprei|compra|recebi|ganhei|caiu|lancei|lancar|lançar|novo|fixo|cadastrar|cadastro)\b",
        " ",
        texto_lower,
        flags=re.IGNORECASE
    )

    texto_lower = re.sub(r"\b20\d{2}-\d{2}-\d{2}\b", " ", texto_lower, flags=re.IGNORECASE)
    texto_lower = re.sub(PADRAO_DATA_BR, " ", texto_lower)
    texto_lower = re.sub(rf"\b(hoje|ontem|anteontem){PERIODO_DO_DIA}", " ", texto_lower, flags=re.IGNORECASE)
    for achado in reversed(expressoes_de_data(texto_lower)):
        texto_lower = texto_lower[:achado.start()] + " " + texto_lower[achado.end():]
    texto_lower = re.sub(r"(?<![\w.,])\d+(?:[.,]\d{1,2})?k\b", " ", texto_lower)
    texto_lower = re.sub(r"\s+", " ", texto_lower).strip()

    # Remove valor que sobrou no início, comum em frases como
    # "paguei 120 no mercado" depois da remoção do verbo.
    texto_lower = re.sub(rf"^{PADRAO_VALOR}(?:\s+(?:{PADRAO_MULTIPLICADOR})\b)?\s+", "", texto_lower).strip()

    # Valor solto no meio/fim ("mercado 45", "tv 3000"): sai da descrição.
    if valor is not None:
        for numero in encontrar_numeros(texto_lower):
            if numero_e_de_produto(texto_lower, numero["inicio"]) or re.match(_UNIDADE_DEPOIS, texto_lower[numero["fim"]:]):
                continue
            escalado = aplicar_escala(texto_lower, numero["fim"], numero["valor"])
            if abs(escalado - valor) < 0.005:
                fim = numero["fim"]
                escala = re.match(rf"\s+(?:{PADRAO_MULTIPLICADOR})\b", texto_lower[fim:])
                if escala and escalado != numero["valor"]:
                    fim += escala.end()
                texto_lower = (texto_lower[:numero["inicio"]] + " " + texto_lower[fim:]).strip()
                break

    # Limpa conectores sobrando no começo/fim. Repete para casos como
    # "120 no mercado" -> "no mercado" -> "mercado".
    for _ in range(3):
        texto_lower = re.sub(r"^(no|na|de|do|da|em|com|para|pra|um|uma|o|a)\s+", "", texto_lower).strip()
        texto_lower = re.sub(r"\s+(no|na|de|do|da|em|com|para|pra|um|uma|o|a)$", "", texto_lower).strip()

    if not texto_lower:
        return re.sub(r"\s+", " ", texto_original.strip())

    return texto_lower.capitalize()


def parse_mensagem(texto_original: str, data_referencia=None):
    # Várias linhas com lançamentos: recusa tudo (não grava o primeiro e perde o resto).
    quantidade = texto_com_varios_lancamentos(texto_original)
    if quantidade and not parece_codigo_ou_texto_longo(" ".join(texto_original.splitlines())):
        return {
            "erro": "mensagem_bloqueada",
            "motivo": "mais_de_um_valor",
            "detalhe": "varios_lancamentos",
            "mensagem": mensagem_varios_lancamentos(quantidade),
        }
    if parece_codigo_ou_texto_longo(texto_original):
        return {
            "erro": "mensagem_bloqueada",
            "motivo": "codigo_ou_texto_longo"
        }

    categoria_explicita = detectar_categoria_explicita(texto_original)
    texto_sem_categoria = limpar_categoria_explicita(texto_original)
    texto = normalizar_texto(texto_sem_categoria)

    try:
        data = detectar_data(texto, hoje=data_referencia)
        if re.search(r'(?<![\w\d])-\s*\d', texto):
            raise ValueError('valor negativo')
        texto_valor = re.sub(PADRAO_DATA_BR, ' ', texto)
        for achado in reversed(expressoes_de_data(texto_valor)):
            texto_valor = texto_valor[:achado.start()] + ' ' + texto_valor[achado.end():]
        # "mercado 45, padaria 30": a vírgula de pontuação não é casa decimal.
        texto_valor = re.sub(r"(\d)[,.](?=\s+\D)", r"\1", texto_valor)
        if (len(re.findall(r"\b(?:gastei|paguei|comprei|recebi|ganhei)\b", texto)) > 1
                and len(re.findall(r"\d+", texto_valor)) > 1):
            raise MaisDeUmValor("mais de um lançamento")
        valor = extrair_valor(texto_valor)
    except MaisDeUmValor:
        return {'erro': 'mensagem_bloqueada', 'motivo': 'mais_de_um_valor'}
    except DataFutura:
        return {'erro': 'mensagem_bloqueada', 'motivo': 'data_futura'}
    except (ValueError, OverflowError):
        return {'erro': 'mensagem_bloqueada', 'motivo': 'valor_ou_data_invalida'}
    if valor is None:
        return None

    tipo = detectar_tipo(texto)
    if tipo == "ambiguo":
        return {'erro': 'mensagem_bloqueada', 'motivo': 'tipo_ambiguo'}
    parcelas = detectar_parcelas(texto)

    if tipo == "receita":
        parcelas = 1

    categoria = detectar_categoria(texto, tipo, categoria_explicita)
    forma_pagamento = detectar_forma_pagamento(texto, parcelas)
    conta = detectar_conta(texto)

    return {
        "data": data.isoformat(),
        "tipo": tipo,
        "valor": valor,
        "categoria": categoria,
        "descricao": limpar_descricao(texto_sem_categoria, valor),
        "forma_pagamento": forma_pagamento,
        "conta": conta,
        "mensagem_original": texto_original,
        "parcelas_total": parcelas
    }
