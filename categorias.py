"""Taxonomia e categorização canônica compartilhada pelo assessor.

Texto e áudio devem produzir o mesmo resultado sem depender da IA local.
Categoria explicitamente escolhida pelo usuário sempre prevalece.
"""
from __future__ import annotations

import re
import unicodedata


CATEGORIAS_CANONICAS = (
    "Alimentação", "Assinaturas", "Beleza", "Dívidas", "Educação",
    "Eletrônicos", "Lazer", "Mercado", "Moradia", "Pet", "Saúde",
    "Transporte", "Vestuário", "Viagem", "Receita", "Outros",
)


def _chave_categoria(valor: str | None) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "").strip())
    texto = "".join(c for c in texto if not unicodedata.combining(c)).casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+]+", " ", texto)).strip()


_ALIASES = {_chave_categoria(categoria): categoria for categoria in CATEGORIAS_CANONICAS}
_ALIASES.update({
    "assinatura": "Assinaturas", "alimentacao": "Alimentação", "divida": "Dívidas",
    "eletronico": "Eletrônicos", "eletronicos": "Eletrônicos", "educacao": "Educação",
    "saude": "Saúde", "roupas": "Vestuário", "pets": "Pet",
})


# Expressões maiores vencem termos genéricos. A ordem resolve somente empates.
REGRAS_CATEGORIA = {
    "Pet": (
        "pet shop", "petshop", "veterinario", "clinica veterinaria", "racao",
        "banho e tosa", "banho tosa", "agropecuaria", "petz", "cobasi", "cachorro", "gato",
    ),
    "Saúde": (
        "plano de saude", "seguro saude", "oculos de grau", "personal trainer",
        "farmacia", "remedio", "medicamento", "consulta", "medico", "dentista",
        "nutricionista", "nutri", "psicologo", "terapia", "exame", "hospital",
        "laboratorio", "academia", "wellhub", "gympass", "oculos", "lente de grau",
    ),
    "Educação": (
        "mensalidade escolar", "material escolar", "faculdade", "universidade", "escola",
        "curso", "livro", "papelaria", "certificacao", "treinamento",
    ),
    "Beleza": (
        "corte de cabelo", "salao de beleza", "cabeleireiro", "cabeleireira", "barbearia",
        "manicure", "pedicure", "cosmetico", "maquiagem", "perfume", "chapinha", "depilacao",
    ),
    "Dívidas": ("emprestimo", "financiamento", "divida", "juros", "cheque especial"),
    "Viagem": (
        "passagem aerea", "seguro viagem", "agencia de viagem", "hotel", "pousada",
        "hospedagem", "airbnb", "aeroporto", "viagem", "turismo", "praia", "resort",
        "mala de viagem",
    ),
    "Transporte": (
        "transporte publico", "passagem de trem", "passagem de metro", "bilhete unico",
        "aplicativo de transporte", "uber", "99pop", "cabify", "taxi", "gasolina", "etanol",
        "combustivel", "posto", "estacionamento", "pedagio", "onibus", "metro", "trem",
        "passagem", "patinete",
    ),
    "Moradia": (
        "conta de luz", "conta de agua", "energia eletrica", "banda larga", "condominio",
        "aluguel", "iptu", "internet", "energia", "luz", "agua", "gas encanado",
        "manutencao residencial", "moveis", "travesseiro",
    ),
    "Assinaturas": (
        "youtube premium", "amazon prime", "plano de celular", "assinatura", "netflix",
        "spotify", "icloud", "paramount+", "paramount plus", "disney+", "disney plus",
        "meli+", "meli plus", "capcut", "iptv", "streaming", "licenca windows",
    ),
    "Eletrônicos": (
        "fone de ouvido", "email corporativo", "e mail corporativo", "seguro drone",
        "acessorios drone", "celular", "smartphone", "iphone", "android", "notebook",
        "computador", "monitor", "airpods", "headphone", "carregador", "teclado", "camera",
        "tablet", "eletronico", "drone", "dji", "goggles", "firestick", "transceiver",
        "pelicula celular", "cabo usb", "mouse",
    ),
    "Vestuário": (
        "ajuste de roupa", "corte e costura", "camiseta", "camisa", "calca", "tenis",
        "jaqueta", "bermuda", "vestido", "blusa", "roupa", "costureira", "sapato",
        "chinelo", "shein",
    ),
    "Mercado": (
        "pao de acucar", "cesta basica", "supermercado", "mercadinho", "atacadao", "atacado",
        "hortifruti", "acougue", "mercearia", "feira", "mercado", "carrefour", "conveniencia",
    ),
    "Alimentação": (
        "cafe da manha", "cachorro quente", "rodizio japones", "rodizio japa", "vale refeicao",
        "delivery", "restaurante", "almoco", "jantar", "janta", "lanche", "ifood", "keeta",
        "pizza", "hamburguer", "mcdonalds", "subway", "outback", "padaria", "cafe", "comida",
        "bebida", "cerveja", "sorvete", "acai", "churrasco", "gorjeta",
    ),
    "Lazer": (
        "parque de diversoes", "ingresso", "cinema", "teatro", "show", "festa", "role",
        "jogo", "evento", "clube", "passeio",
    ),
}


_IGNORAR_NO_TEXTO = ("mercado pago", "mercado livre", "cartao de credito", "cartao de debito")


def canonicalizar_categoria(valor: str | None, padrao: str | None = None) -> str | None:
    """Normaliza categorias conhecidas sem destruir uma escolha personalizada."""
    texto = str(valor or "").strip()
    if not texto:
        return padrao
    return _ALIASES.get(_chave_categoria(texto), texto)


def sugerir_categoria(texto: str | None, tipo: str = "despesa") -> str | None:
    """Sugere uma categoria canônica ou ``None`` sem evidência suficiente."""
    if _chave_categoria(tipo) in {"receita", "entrada"}:
        return "Receita"
    # Preferências confirmadas pelo titular vencem o dicionário geral. A
    # importação tardia mantém este módulo puro quando o recurso não é usado.
    from categorias_pessoais import sugerir_categoria_pessoal
    pessoal = sugerir_categoria_pessoal(texto, tipo)
    if pessoal:
        return canonicalizar_categoria(pessoal, pessoal)
    chave = _chave_categoria(texto)
    if not chave:
        return None
    for trecho in _IGNORAR_NO_TEXTO:
        chave = re.sub(rf"(?<![a-z0-9]){re.escape(trecho)}(?![a-z0-9])", " ", chave)
    chave = re.sub(r"\s+", " ", chave).strip()
    candidatos = []
    for prioridade, (categoria, termos) in enumerate(REGRAS_CATEGORIA.items()):
        for termo in termos:
            termo_chave = _chave_categoria(termo)
            if re.search(rf"(?<![a-z0-9]){re.escape(termo_chave)}(?![a-z0-9])", chave):
                candidatos.append((len(termo_chave.split()), len(termo_chave), -prioridade, categoria))
    return max(candidatos)[3] if candidatos else None


def inferir_categoria(texto: str | None, tipo: str = "despesa", padrao: str = "Outros") -> str:
    return sugerir_categoria(texto, tipo) or padrao


def categoria_permitida_ia(valor: str | None) -> str | None:
    """Aceita da IA somente nomes pertencentes à taxonomia conhecida."""
    canonica = canonicalizar_categoria(valor)
    return canonica if canonica in CATEGORIAS_CANONICAS and canonica != "Outros" else None

