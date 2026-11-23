"""Relógio único do assessor (Onda 3, etapa 1): "agora" e "hoje" no fuso do titular.

Fuso: UTC-3 FIXO (Brasília, sem horário de verão desde 2019), o mesmo que a
conciliação e as telas do Telegram já usavam. ``ASSESSOR_TIMEZONE`` continua
IGNORADA (é lida por ``app.py`` só por compatibilidade).

Antes havia três critérios de "hoje": ``date.today()`` ingênuo (relógio local
do PC) em ``services``/``database``/..., UTC-3 fixo em
``telegram_experiencia.today()``/``app.py`` e ``conciliacao._hoje()``. Numa
máquina em UTC-3 (a do titular) todos dão o mesmo resultado; em máquina fora
de UTC-3, os pontos convertidos para este módulo passam a usar UTC-3.

Testes: ``tests/relogio_fixo.data_fixa`` e o modo ``--data`` do gate
(``validacao/relogio_falso.py``) trocam ``date``/``datetime`` em todos os
módulos do projeto, inclusive neste; por isso aqui só se usa
``datetime.now()`` pelo nome do módulo (nunca guardar referência ao método),
convertido para UTC-3 com ``astimezone`` (o ``now()`` ingênuo é a hora local
do PC; relógios falsos de teste que só sabem o ``now()`` ingênuo continuam
valendo). ``hoje(fonte_data)``/``hoje(fonte_datahora=...)`` respeitam um
``patch.object(modulo, 'date'|'datetime', Substituto)`` feito por testes
antigos no módulo que chama (compatibilidade; não use em código novo).
"""
import datetime as _modulo_datetime
from datetime import datetime, timedelta, timezone

FUSO = timezone(timedelta(hours=-3))


def agora_com_fuso():
    """Instante atual com ``tzinfo`` UTC-3."""
    return datetime.now().astimezone(FUSO)


def agora():
    """Data e hora atuais em UTC-3, ingênuas (sem ``tzinfo``), como o ``datetime.now()`` de antes."""
    return agora_com_fuso().replace(tzinfo=None)


def hoje(fonte_data=None, fonte_datahora=None):
    """Data de hoje em UTC-3.

    ``fonte_data``/``fonte_datahora``: a classe ``date``/``datetime`` do módulo
    chamador. Se não é a classe real (um teste a substituiu com
    ``patch.object`` ou o relógio falso está ativo), vale o substituto, como
    antes; com a classe real, vale o relógio único.
    """
    if fonte_data is not None and fonte_data is not _classe_real("date"):
        return fonte_data.today()
    if fonte_datahora is not None and fonte_datahora is not _classe_real("datetime"):
        return fonte_datahora.now(FUSO).date()
    return agora().date()


def _classe_real(nome):
    atual = getattr(_modulo_datetime, nome)
    return getattr(atual, "_classe_real", atual)  # relógio falso guarda a real em _classe_real


def mes_atual():
    """Mês corrente ``AAAA-MM`` em UTC-3."""
    return hoje().strftime("%Y-%m")
