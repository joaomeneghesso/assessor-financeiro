"""V39: calendario de faturas separado da data real da compra.

Este modulo nao abre conexoes, nao grava no banco e nao altera o historico.
O dia de corte e inclusivo. Configuracao opcional via ambiente:
ASSESSOR_FATURA_DIA_CORTE=25
ASSESSOR_FATURA_CORTES={"Itau":25,"Nubank":20}
"""
from __future__ import annotations

import calendar
import json
import os
import config
import re
import unicodedata
from datetime import date


def _get(row, key, default=None):
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        return default
    return default if value is None else value


def normalizar(value) -> str:
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', str(value or '').casefold())
                           if not unicodedata.combining(c)).split())


def eh_credito(row) -> bool:
    return _get(row, 'tipo') == 'despesa' and normalizar(_get(row, 'forma_pagamento')) in {'credito', 'cartao', 'cartao de credito'}


def validar_mes(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}', value):
        raise ValueError('Fatura invalida. Use AAAA-MM.')
    date.fromisoformat(value + '-01')
    return value


def somar_meses(mes: str, quantidade: int) -> str:
    validar_mes(mes)
    year, month = map(int, mes.split('-'))
    year, month0 = divmod(year * 12 + month - 1 + quantidade, 12)
    date(year, month0 + 1, 1)
    return f'{year:04d}-{month0+1:02d}'


def _dia(value) -> int:
    if isinstance(value, bool) or not re.fullmatch(r'\d{1,2}', str(value)) or not 1 <= int(value) <= 31:
        raise ValueError('Dia de corte invalido: use um inteiro de 1 a 31.')
    return int(value)


def dia_corte(conta: str, compra: str) -> int:
    day = date.fromisoformat(compra)
    padrao = _dia(config.ler('ASSESSOR_FATURA_DIA_CORTE', '25'))
    try:
        configuracao = json.loads(config.ler('ASSESSOR_FATURA_CORTES', '{}'))
    except (ValueError, TypeError) as exc:
        raise ValueError('ASSESSOR_FATURA_CORTES deve conter um objeto JSON valido.') from exc
    if not isinstance(configuracao, dict):
        raise ValueError('ASSESSOR_FATURA_CORTES deve conter um objeto JSON.')
    cortes = {normalizar(name): _dia(value) for name, value in configuracao.items()}
    return min(cortes.get(normalizar(conta), padrao), calendar.monthrange(day.year, day.month)[1])


def precisa_escolher(row) -> bool:
    if not eh_credito(row):
        return False
    compra = _get(row, 'data')
    return date.fromisoformat(compra).day >= dia_corte(_get(row, 'conta', ''), compra)


def opcoes_fatura(row) -> tuple[str, ...]:
    mes = date.fromisoformat(_get(row, 'data')).strftime('%Y-%m')
    return (mes, somar_meses(mes, 1)) if precisa_escolher(row) else (mes,)


def contexto_escolha(row) -> tuple:
    return (_get(row, 'data'), normalizar(_get(row, 'conta')),
            normalizar(_get(row, 'forma_pagamento')), int(_get(row, 'parcelas_total', 1)),
            dia_corte(_get(row, 'conta', ''), _get(row, 'data')))


def preparar_rascunho(draft: dict) -> bool:
    """Retorna True quando falta a escolha; invalida escolhas de dados anteriores."""
    if draft.get('existing_id'):
        return False  # Vincular nao altera a competencia de um movimento existente.
    if not eh_credito(draft):
        for key in ('competencia_fatura', 'data_compra', '_fatura_contexto'):
            draft.pop(key, None)
        return False
    contexto = contexto_escolha(draft)
    if draft.get('_fatura_contexto') != contexto:
        draft.pop('competencia_fatura', None)
    draft['_fatura_contexto'] = contexto
    draft['data_compra'] = draft['data']
    opcoes = opcoes_fatura(draft)
    if len(opcoes) == 1:
        draft['competencia_fatura'] = opcoes[0]
        return False
    if draft.get('competencia_fatura') not in opcoes:
        draft.pop('competencia_fatura', None)
        return True
    return False


def validar_escolha(row, obrigatoria=False) -> None:
    mes = _get(row, 'competencia_fatura')
    compra = _get(row, 'data_compra')
    if not eh_credito(row):
        if mes or compra:
            raise ValueError('Competencia de fatura e data de compra sao exclusivas de despesas no credito.')
        return
    if compra is not None and compra != _get(row, 'data'):
        raise ValueError('A data real da compra precisa corresponder a data informada no registro.')
    if mes is not None and validar_mes(mes) not in opcoes_fatura(row):
        raise ValueError('Escolha a fatura do mes da compra ou do mes seguinte, conforme o dia de corte.')
    if obrigatoria and precisa_escolher(row) and mes is None:
        raise ValueError('Escolha o mes da fatura antes de confirmar. Abra Registrar e revise a compra.')


def competencia_transacao(row) -> str:
    mes = _get(row, 'competencia_fatura')
    if eh_credito(row) and mes:
        return validar_mes(mes)
    return str(_get(row, 'data', ''))[:7]


def data_competencia(row) -> str:
    """Data de referencia mensal; nao substitui a data persistida da compra."""
    original = date.fromisoformat(_get(row, 'data_compra') or _get(row, 'data'))
    year, month = map(int, competencia_transacao(row).split('-'))
    day = min(original.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


def data_real_compra(row) -> str:
    return _get(row, 'data_compra') or _get(row, 'data')


def sql_competencia(conn, alias='') -> str:
    """Compativel com a v38 sem migration; alias e interno, nunca vem do usuario."""
    if alias and not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', alias):
        raise ValueError('Alias SQL invalido.')
    prefix = alias + '.' if alias else ''
    columns = {row[1] for row in conn.execute('PRAGMA table_info(transacoes)')}
    legacy = f'substr({prefix}data, 1, 7)'
    if 'competencia_fatura' not in columns:
        return legacy
    return (f"CASE WHEN {prefix}tipo = 'despesa' AND "
            f"lower(replace(replace(replace(replace(trim(coalesce({prefix}forma_pagamento,'')), 'é', 'e'), 'É', 'e'), 'ã', 'a'), 'Ã', 'a')) "
            f"IN ('credito','cartao','cartao de credito') "
            f"THEN coalesce(nullif({prefix}competencia_fatura,''), {legacy}) ELSE {legacy} END")


def exigir_schema(conn) -> None:
    columns = {row[1] for row in conn.execute('PRAGMA table_info(transacoes)')}
    if not {'data_compra', 'competencia_fatura'} <= columns:
        raise ValueError('A v39 precisa da migration 0004. Pare o bot e execute: python migrations.py migrate')
