"""Sugestões de comando quando o texto digitado não é reconhecido.

Módulo puro: sem I/O, sem banco, só stdlib. Nunca interpreta nem executa o
texto do usuário; apenas o compara com um catálogo de comandos reais do
roteador (services._processar_mensagem_core) e devolve exemplos parecidos.
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

# (comando de exemplo, palavras-chave extras para casar com o que o titular digita)
CATALOGO_COMANDOS: list[tuple[str, str]] = [
    # Consultas gerais
    ("saldo", "saldo carteira caixa quanto tenho dinheiro"),
    ("saldo 2026-07", "saldo mes carteira caixa mensal"),
    ("saldo itaú", "saldo conta banco itau"),
    ("caixa 2026-07", "caixa mensal carteira mes"),
    ("meu mês", "meu mes painel resumo mensal"),
    ("resumo mensal", "resumo mes mensal painel"),
    ("hoje", "hoje meu dia rotina fechamento do dia"),
    ("gastos de hoje", "gastei hoje gastos dia"),
    ("a pagar", "pagar pagamentos contas pendentes vencimentos"),
    ("quanto vou pagar no mês", "quanto pagar mes total contas"),
    ("quanto vou pagar no nubank", "quanto pagar cartao fatura banco nubank"),
    ("vencimentos", "vencimentos datas pagamento agenda contas"),
    ("vencimentos hoje", "vencimentos pagamentos hoje lembretes"),
    ("agenda", "agenda financeira compromissos datas"),
    ("checklist", "checklist lista pagamentos pagos pendentes"),
    ("compromissos", "compromissos fixos parcelas faturas"),
    ("fixos", "fixos fixo compromissos fixos mensais contas fixas"),
    ("parcelamentos", "parcelamentos parcelas parceladas minhas parcelas"),
    ("parcelas futuras", "parcelas futuras parcelamentos futuros"),
    ("entradas", "entradas receitas salario recebimentos"),
    ("entradas fixas", "entradas fixas receitas fixas salario"),
    ("metas", "metas limites orcamento categorias"),
    ("categorias", "categorias categoria gastos por categoria"),
    ("contas", "contas formas pagamento cartoes bancos"),
    ("formas de pagamento", "formas forma pagamento pix debito credito"),
    ("faturas", "faturas fatura cartao credito"),
    ("fatura nubank", "fatura cartao nubank credito"),
    ("heranca", "heranca saldo herdado ponte do mes"),
    # Relatórios e fechamentos
    ("fechamento do mês", "fechamento mensal mes resumo"),
    ("fechamento semanal", "fechamento semana semanal"),
    ("relatório do mês", "relatorio mensal mes resumo"),
    ("detalhar mês", "detalhar detalhe mes atual tudo"),
    ("dashboard", "dashboard painel grafico visual"),
    ("diagnóstico", "status diagnostico saude sistema"),
    ("assessor", "assessor diagnostico financeiro modo assessor"),
    ("revisar", "revisar revisao base dados lancamentos"),
    # Buscas e listas
    ("últimas 10", "ultimas ultimos lancamentos transacoes listar recentes"),
    ("últimos lançamentos", "ultimos ultimas lancamentos transacoes recentes"),
    ("buscar mercado", "buscar procurar pesquisar achar lancamento"),
    ("extrato itaú", "extrato conta banco itau movimentos"),
    ("transferências caixa", "transferencias transferencia caixa entre contas"),
    ("quanto gastei com mercado", "quanto gastei categoria mercado total"),
    ("detalhar lançamento 7", "detalhar detalhe lancamento transacao abrir"),
    # Registro
    ("gastei 35 no almoço", "gastei gasto despesa paguei comprei registrar almoco"),
    ("recebi 500 de salário", "recebi receita entrada salario ganhei"),
    ("registrar", "registrar novo lancamento nova despesa cadastrar"),
    ("transferi 100 do Itaú para Caju", "transferi transferencia mover dinheiro entre contas itau caju"),
    ("saldo inicial Itaú 1000", "saldo inicial conta banco itau abertura"),
    ("ajustar saldo Itaú para 1000", "ajustar saldo conta banco itau corrigir"),
    # Alterações de lançamentos
    ("mudar 7 para Transporte", "mudar trocar categoria lancamento"),
    ("corrigir valor 7 para 42,90", "corrigir alterar valor lancamento preco"),
    ("corrigir conta 7 para BTG", "corrigir alterar mudar conta banco lancamento"),
    ("corrigir forma 7 para pix", "corrigir alterar mudar forma pagamento pix debito credito"),
    ("mudar último para Mercado", "mudar ultimo categoria lancamento"),
    ("apagar 7", "apagar excluir deletar remover lancamento"),
    ("apagar último", "apagar excluir deletar remover ultimo lancamento"),
    # Fixos e entradas
    ("novo fixo água 150 no pix dia 25", "novo fixo cadastrar adicionar criar conta fixa agua"),
    ("nova entrada fixa salário 3800 dia 5", "nova entrada fixa cadastrar receita salario"),
    ("alterar fixo 1 para 250", "alterar fixo valor mudar compromisso"),
    ("alterar vencimento fixo 1 para dia 10", "alterar vencimento fixo dia mudar data"),
    ("alterar conta do fixo 1 para Itaú", "alterar conta fixo compromisso banco"),
    ("alterar categoria do fixo 1 para Moradia", "alterar categoria fixo compromisso"),
    ("alterar entrada 2 para 5000", "alterar entrada receita valor mudar"),
    ("pausar fixo 3", "pausar suspender desativar fixo parar"),
    ("reativar fixo 3", "reativar ativar retomar fixo"),
    ("pausar entrada 2", "pausar desativar entrada receita"),
    ("apagar fixo 46", "apagar excluir remover cancelar fixo compromisso"),
    ("apagar parcelamento 3", "apagar excluir remover cancelar parcelamento parcelas"),
    ("apagar entrada 2", "apagar excluir remover entrada receita"),
    ("apagar meta mercado", "apagar excluir remover meta"),
    ("meta mercado 800", "meta definir limite mercado orcamento"),
    ("paguei C5", "paguei pago quitar quitei marcar pago compromisso fixo fatura"),
    ("desmarcar C5", "desmarcar pendente marcar pendente desfazer pagamento"),
    ("diagnóstico fixo 5", "diagnostico fixo compromisso"),
    # Simulações e ferramentas
    ("simular compra 1200 em 6x", "simular compra parcelar parcelado simulacao"),
    ("posso comprar notebook 3000", "posso comprar comprar vale a pena"),
    ("vale a pena comprar celular 2000", "vale a pena comprar compra"),
    ("exportar csv", "exportar csv planilha transacoes baixar"),
    ("exportar csv tudo", "exportar csv tudo completo base inteira"),
    ("analisar csv", "importar csv analisar prever importacao"),
    ("backup", "backup copia seguranca gerar backup"),
    ("ajustes", "ajustes configuracoes opcoes"),
]

_STOP = {
    "o", "a", "os", "as", "um", "uma", "de", "do", "da", "dos", "das", "no", "na",
    "nos", "nas", "em", "para", "pra", "por", "com", "que", "e", "ao", "meu", "minha",
}

_VERBOS_ACAO = {
    "apagar": "apagar", "excluir": "apagar", "deletar": "apagar", "remover": "apagar",
    "alterar": "alterar", "mudar": "alterar", "trocar": "alterar", "editar": "alterar",
    "corrigir": "corrigir", "ajustar": "ajustar", "pausar": "pausar",
    "reativar": "reativar", "cancelar": "cancelar",
}

_LIMIAR_PALAVRA = 0.75
_LIMIAR_SCORE = 0.42


def _norm(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or "").lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\d+(?:[-/.,]\d+)*", " N ", texto)
    texto = re.sub(r"[^a-z# ]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _palavras(texto: str) -> list[str]:
    return [p for p in _norm(texto).split() if p != "N" and p not in _STOP]


def _sim_palavra(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if len(a) < 3 or len(b) < 3:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _melhor(p: str, candidatas: list[str]) -> float:
    return max((_sim_palavra(p, c) for c in candidatas), default=0.0)


# Pré-cálculo (determinístico): palavras de cada entrada do catálogo.
_INDICE = []
for _cmd, _kw in CATALOGO_COMANDOS:
    _pc = _palavras(_cmd)
    _pk = list(dict.fromkeys(_pc + _palavras(_kw)))
    _INDICE.append((_cmd, _norm(_cmd), _pc, _pk))


def _pontuar(entrada_norm: str, palavras: list[str], item) -> float:
    cmd, cmd_norm, p_cmd, p_kw = item
    if not palavras:
        return 0.0
    sims = [_melhor(p, p_kw) for p in palavras]
    acertos = [s for s in sims if s >= _LIMIAR_PALAVRA]
    if not acertos:
        return 0.0
    cob_entrada = sum(acertos) / len(palavras)
    cob_cmd = sum(1 for c in p_cmd if _melhor(c, palavras) >= _LIMIAR_PALAVRA) / max(len(p_cmd), 1)
    frase = SequenceMatcher(None, entrada_norm, cmd_norm).ratio()
    primeira = 0.0
    if p_cmd and _sim_palavra(palavras[0], p_cmd[0]) >= _LIMIAR_PALAVRA:
        primeira = 1.0
    return 0.40 * cob_entrada + 0.20 * cob_cmd + 0.25 * frase + 0.15 * primeira


def sugerir_comandos(texto: str, limite: int = 3) -> list[str]:
    """Até `limite` comandos do catálogo parecidos com `texto` (mais parecido primeiro)."""
    try:
        limite = int(limite)
    except (TypeError, ValueError):
        return []
    if limite <= 0:
        return []
    entrada_norm = _norm(texto)
    palavras = _palavras(texto)
    if not palavras:
        return []
    pontuados = []
    for ordem, item in enumerate(_INDICE):
        score = _pontuar(entrada_norm, palavras, item)
        if score >= _LIMIAR_SCORE:
            pontuados.append((-score, ordem, item[0]))
    pontuados.sort()
    saida: list[str] = []
    vistos: set[str] = set()
    for _, _, cmd in pontuados:
        chave = _norm(cmd)
        if chave in vistos:
            continue
        vistos.add(chave)
        saida.append(cmd)
        if len(saida) >= limite:
            break
    return saida


def _truncar(texto: str, tamanho: int = 60) -> str:
    texto = re.sub(r"\s+", " ", str(texto or "")).strip()
    return texto if len(texto) <= tamanho else texto[: tamanho - 1].rstrip() + "…"


def _acao_pedida(texto: str) -> str | None:
    for p in _norm(texto).split():
        if p in _VERBOS_ACAO:
            return _VERBOS_ACAO[p]
    return None


def mensagem_comando_nao_reconhecido(texto: str) -> str:
    linhas = [
        "🤔 Não entendi esse comando",
        f"Você escreveu: “{_truncar(texto)}”",
    ]
    acao = _acao_pedida(texto)
    if acao:
        linhas.append(f"Parece um pedido para {acao}, mas faltou o alvo ou o formato.")
    linhas.append("Nada foi registrado.")
    sugestoes = sugerir_comandos(texto)
    if sugestoes:
        linhas.append("Talvez você quis dizer:")
        linhas.extend(f"• {s}" for s in sugestoes)
    else:
        linhas.append("Toque em Registrar para lançar um gasto ou em Menu para ver tudo.")
    return "\n".join(linhas)


def mensagem_sem_valor(texto: str) -> str:
    linhas = ["🤔 Não encontrei um valor nessa mensagem."]
    sugestoes = sugerir_comandos(texto)
    if sugestoes:
        linhas.append("Talvez você quis dizer:")
        linhas.extend(f"• {s}" for s in sugestoes)
    palavras = [p for p in _norm(texto).split() if p != "N"]
    if 1 <= len(palavras) <= 2 and not _acao_pedida(texto):
        linhas.append(f"Para registrar um gasto, inclua o valor: gastei 35 no {_truncar(texto, 30)}")
    linhas.append("Nada foi registrado.")
    return "\n".join(linhas)
