"""Comandos operacionais nunca são interpretados como novos gastos."""
import re
import unicodedata

def comando_operacional(texto):
    text = ''.join(c for c in unicodedata.normalize('NFKD', str(texto or '').lower()) if not unicodedata.combining(c)).strip()
    return bool(re.match(r'^(?:alterar|mudar|trocar|corrigir|editar|ajustar|apagar|excluir|deletar|remover|pausar|suspender|desativar|reativar|ativar|retomar|resetar|conciliar|desvincular|vincular|confirmar|cancelar|diagnostico fixo|diagnostico compromisso)\b', text))

def campo_ia_valido(valor):
    text = str(valor or '').strip()
    return bool(text and not re.fullmatch(r'[\d\s.,+\-]+', text) and not re.search(r'\b(?:register_expense|register_income|query_type|payment_method)\b', text, re.I))
