from __future__ import annotations

import re
from decimal import Decimal, DecimalException, ROUND_HALF_UP


def parse_money(value: str | int | float | Decimal, *, allow_negative: bool = False) -> Decimal:
    """Aceita decimal simples e agrupamento pt-BR, sem corrigir separadores por conta própria."""
    try:
        if isinstance(value, bool):
            raise ValueError('valor monetário inválido')
        if isinstance(value, (Decimal, int, float)):
            result = Decimal(str(value))
        else:
            text = re.sub(r'^r\$\s*', '', str(value or '').strip(), flags=re.I).strip()
            # Espaços internos e agrupamentos incompletos podem mudar a ordem de
            # grandeza. Só removemos pontos após validar toda a estrutura.
            plain = r'[+-]?\d+(?:[,.]\d{1,2})?'
            grouped = r'[+-]?\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?'
            if re.fullmatch(plain, text):
                normalized = text.replace(',', '.')
            elif re.fullmatch(grouped, text):
                normalized = text.replace('.', '').replace(',', '.')
            else:
                raise ValueError('formato monetário inválido; use 1.234,56 ou 1234.56')
            result = Decimal(normalized)
        if not result.is_finite():
            raise ValueError('o valor deve ser um número finito')
        result = result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except DecimalException as exc:
        raise ValueError('valor monetário inválido ou grande demais') from exc
    if not allow_negative and result <= 0:
        raise ValueError('o valor deve ser maior que zero')
    return result


def parse_money_float(value, *, allow_negative: bool = False) -> float:
    return float(parse_money(value, allow_negative=allow_negative))


def formatar_brl(value) -> str:
    """Regra única de exibição: 2 casas HALF_UP em Decimal, sem "R$ -0,00".

    2.675 → "R$ 2,68"; 1.005 → "R$ 1,01"; −0.004 → "R$ 0,00";
    −50 → "R$ -50,00" (a camada de UX troca por "−R$ 50,00").
    O float entra pela representação curta (str), como em parse_money.
    """
    try:
        number = value if isinstance(value, Decimal) else Decimal(str(float(value or 0)))
    except (TypeError, ValueError, DecimalException):
        number = Decimal('NaN')
    if not number.is_finite():
        return 'R$ —'
    number = number.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if number == 0:
        number = Decimal('0.00')  # -0,00 vira 0,00
    return 'R$ ' + f'{number:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
