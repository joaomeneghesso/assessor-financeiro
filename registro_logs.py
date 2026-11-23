"""Log em arquivo para avisos e erros, sem mudar o que aparece no console.

- Grava apenas WARNING ou acima (o mesmo nível que já aparecia no console).
- Arquivo rotativo em ``logs/`` (1 MB x 5), um por processo, para o bot e o
  painel não disputarem o mesmo arquivo no Windows.
- ``httpx``/``httpcore`` ficam em WARNING: em INFO eles registrariam a URL da
  API do Telegram, que contém o token do bot.
- Falhar ao criar o log nunca impede o assessor de iniciar.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
_MARCA = "_assessor_registro_logs"


def configurar_logs(nome_arquivo: str, pasta: Path | None = None) -> Path | None:
    raiz = logging.getLogger()
    for nome in ("httpx", "httpcore"):
        logging.getLogger(nome).setLevel(logging.WARNING)

    if any(getattr(h, _MARCA, False) for h in raiz.handlers):
        return None  # já configurado neste processo

    # Sem handlers, o Python usa um "last resort" que imprime WARNING+ no
    # console. Ao incluir o arquivo, mantemos esse console explicitamente.
    if not raiz.handlers:
        console = logging.StreamHandler(sys.stderr)
        console.setLevel(logging.WARNING)
        console.setFormatter(logging.Formatter("%(message)s"))
        setattr(console, _MARCA, True)
        raiz.addHandler(console)
    if raiz.level == logging.NOTSET or raiz.level > logging.WARNING:
        raiz.setLevel(logging.WARNING)

    destino = Path(pasta or LOG_DIR) / nome_arquivo
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        arquivo = RotatingFileHandler(destino, maxBytes=1_000_000, backupCount=5, encoding="utf-8", delay=True)
    except OSError as exc:
        print(f"Aviso: log em arquivo indisponível ({exc}). O assessor continua normalmente.", file=sys.stderr)
        return None
    arquivo.setLevel(logging.WARNING)
    arquivo.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    setattr(arquivo, _MARCA, True)
    raiz.addHandler(arquivo)
    return destino


def avisar_se_fuso_divergente(agora=None) -> bool:
    """Avisa (sem alterar nada) se o relógio do PC não está em UTC-3.

    Boa parte do assessor usa a data local do Windows (``date.today()``),
    enquanto a conciliação e a tela do Telegram usam UTC-3 fixo. No seu PC em
    São Paulo as duas coincidem; se o fuso do Windows mudar, lançamentos perto
    da meia-noite podem cair em dias diferentes. Retorna True se divergiu.
    """
    from datetime import datetime, timedelta
    agora = agora or datetime.now().astimezone()
    if agora.utcoffset() == timedelta(hours=-3):
        return False
    logging.getLogger("assessor.relogio").warning(
        "O fuso do Windows está em %s, mas o assessor considera São Paulo (UTC-03:00). "
        "Ajuste o fuso do sistema para evitar datas trocadas perto da meia-noite.",
        agora.strftime("UTC%z"),
    )
    return True
