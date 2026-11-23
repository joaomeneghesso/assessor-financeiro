"""Configuração única do assessor: caminhos do projeto e leitura do ambiente.

Regras (Onda 3, etapa 1):

- Este é o ÚNICO módulo que lê ``os.environ``/``os.getenv`` (o teste
  ``tests/test_arquitetura_linha_de_base.py`` trava isso). Os módulos chamam
  ``ler``/``ler_bool``/``ler_int``/``ler_float`` no MESMO ponto em que antes
  liam o ambiente, com o MESMO padrão: o que era lido no import continua no
  import; o que era lido a cada chamada continua a cada chamada (testes usam
  ``patch.dict(os.environ, ...)``).
- O ``.env`` só é carregado por quem já carregava antes (``app.py`` na subida
  e ``telegram_experiencia._runtime_store``), via ``carregar_dotenv()``.
  Importar este módulo NÃO carrega o ``.env``. (O painel web, que lia
  ``ASSESSOR_WEB_*``, foi removido em 13/11/2026.)
- Os nomes antigos continuam existindo nos módulos de origem como apelidos
  (``app.ASSESSOR_AUTOLOCK_MINUTES``, ``services.BACKUPS_DIR``,
  ``database.DB_PATH``...) e continuam patcháveis.
- ``ASSESSOR_TIMEZONE`` é lida, mas IGNORADA: o fuso é UTC-3 fixo (ver
  ``relogio.py``).
- Toda variável lida tem de estar em ``VARIAVEIS`` e no ``.env.example``
  (``tests/test_config_unica.py``).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "financeiro.db"
RUNTIME_DIR = BASE_DIR / ".runtime"
# Antes eram relativas ao diretório de execução (Path("backups")...). Ancoradas
# na pasta do projeto: mesmo destino quando o bot é iniciado pela raiz (uso normal).
BACKUPS_DIR = BASE_DIR / "backups"
EXPORTS_DIR = BASE_DIR / "exports"
DASHBOARDS_DIR = BASE_DIR / "dashboards"
IMPORTS_DIR = BASE_DIR / "imports"

VALORES_VERDADEIROS = ("1", "true", "sim", "s", "yes", "on")

# Variáveis lidas pelo código (nome -> onde/como). O padrão de cada uma fica no
# ponto de leitura, idêntico ao de antes da centralização.
VARIAVEIS = {
    # Telegram
    "TELEGRAM_BOT_TOKEN": "app.main: token do bot",
    "TELEGRAM_ALLOWED_USER_ID": "app.obter_allowed_user_id: whitelist do titular",
    # Segurança (app.py, na subida)
    "ASSESSOR_PIN": "app: PIN em texto (legado; prefira o hash)",
    "ASSESSOR_PIN_HASH": "app: hash PBKDF2 do PIN",
    "ASSESSOR_PIN_LENGTH": "app: tamanho do PIN",
    "ASSESSOR_PIN_RESET_KEY": "app: chave de recuperação (texto)",
    "ASSESSOR_PIN_RESET_KEY_HASH": "app: hash da chave de recuperação",
    "ASSESSOR_AUTOLOCK_MINUTES": "app: autolock (padrão 15)",
    "ASSESSOR_PIN_MAX_ATTEMPTS": "app: tentativas de PIN (padrão 5)",
    "ASSESSOR_PIN_LOCK_MINUTES": "app: bloqueio após tentativas (padrão 15)",
    "ASSESSOR_ALLOW_GROUPS": "app: permite grupo (padrão false)",
    "ASSESSOR_ALLOWED_CHAT_ID": "app: chat de grupo permitido",
    "ASSESSOR_PROTECT_FINANCIAL_CONTENT": "app/telegram_recursos: protect_content (padrão 1)",
    # Alertas
    "ASSESSOR_ALERTAS_ATIVOS": "app: alertas (padrão true)",
    "ASSESSOR_ALERT_CHAT_ID": "app: chat que recebe alertas",
    "ASSESSOR_TIMEZONE": "app: IGNORADA (fuso fixo UTC-3)",
    "ASSESSOR_ALERTA_DIARIO_HORA": "app/assessor_orientacao: hora do alerta da noite",
    "ASSESSOR_LEMBRETE_PAGAMENTOS_HORA": "app/assessor_orientacao: hora do lembrete da manhã",
    "ASSESSOR_LEMBRETE_PAGAMENTOS_ATIVO": "app/telegram_alertas: lembrete de pagamentos",
    "ASSESSOR_RESUMO_DOMINGO_HORA": "app/assessor_orientacao: hora do resumo semanal",
    # Backup
    "ASSESSOR_BACKUP_AUTOMATICO": "app: backup diário (padrão true)",
    "ASSESSOR_BACKUP_HORA": "app: hora do backup (padrão 03:00)",
    "ASSESSOR_BACKUP_EXTERNO_DIR": "backup_externo: pasta da cópia criptografada (padrão ~/OneDrive/Backups/Assessor)",
    "ASSESSOR_BACKUP_EXTERNO_RCLONE": "backup_externo: remoto rclone para enviar a cópia (servidor; ex.: onedrive:Backups/Assessor)",
    # Regras de fatura e cartões (lidas a cada cálculo)
    "ASSESSOR_FATURA_DIA_CORTE": "faturas_competencia: dia de corte padrão (25)",
    "ASSESSOR_FATURA_CORTES": "faturas_competencia: cortes por cartão (JSON)",
    "ASSESSOR_CARTAO_NOVO_INICIO": "compromissos: início de cartões novos (AAAA-MM-DD)",
    "ASSESSOR_CATEGORY_RULES_PATH": "categorias_pessoais: arquivo de regras de categoria",
    # Telegram (recursos)
    "ASSESSOR_RICH_MESSAGES": "telegram_recursos (padrão 1)",
    "ASSESSOR_STREAMING_PROGRESS": "telegram_streaming (padrão 1)",
    "ASSESSOR_STREAMING_DELAY": "telegram_streaming (padrão 0.35)",
    "ASSESSOR_STREAMING_MIN_INTERVAL": "telegram_streaming (padrão 0.75)",
    "ASSESSOR_PERSIST_SESSIONS": "telegram_experiencia/services (padrão true)",
    "ASSESSOR_OCR_TIMEOUT": "telegram_midia (padrão 30)",
    # IA local
    "ASSESSOR_IA_LOCAL_MODELO": "assessor_ia_local/services: modelo Ollama",
    "ASSESSOR_IA_CONNECT_TIMEOUT": "assessor_ia_local (padrão 0.5)",
    "ASSESSOR_IA_RESPONSE_TIMEOUT": "assessor_ia_local (padrão 6)",
    "ASSESSOR_IA_CIRCUIT_FAILURES": "assessor_ia_local (padrão 1)",
    "ASSESSOR_IA_CIRCUIT_SECONDS": "assessor_ia_local (padrão 30)",
    "ASSESSOR_IA_MODEL_CACHE_SECONDS": "assessor_ia_local (padrão 60)",
    # Áudio
    "ASSESSOR_AUDIO_PROVIDER": "transcricao_audio (padrão whisper_cpp)",
    "ASSESSOR_AUDIO_MODELO": "transcricao_audio (padrão base)",
    "ASSESSOR_AUDIO_IDIOMA": "transcricao_audio (padrão pt)",
    "ASSESSOR_AUDIO_THREADS": "transcricao_audio (padrão 4)",
    "ASSESSOR_AUDIO_TIMEOUT": "transcricao_audio (padrão 120)",
    "ASSESSOR_AUDIO_CPP_EXE": "transcricao_audio (padrão .runtime/whispercpp)",
    "ASSESSOR_AUDIO_CPP_MODEL": "transcricao_audio (padrão .runtime/whispercpp)",
    "ASSESSOR_AUDIO_PROMPT": "transcricao_audio: prompt inicial do whisper",
}


def carregar_dotenv():
    """Carrega ``<projeto>/.env`` no ambiente do processo (sem sobrescrever o que já existe)."""
    from dotenv import load_dotenv
    return load_dotenv(ENV_PATH)


def ler(nome, padrao=None):
    """Mesmo que ``os.getenv(nome, padrao)``."""
    return os.getenv(nome, padrao)


def ler_bool(nome, padrao, verdadeiros=VALORES_VERDADEIROS):
    """``ler(nome, padrao).strip().lower() in verdadeiros`` (padrão em texto, como antes)."""
    return ler(nome, padrao).strip().lower() in verdadeiros


def ler_int(nome, padrao):
    """``int(ler(nome, padrao))`` (padrão em texto, como antes; valor inválido levanta)."""
    return int(ler(nome, padrao))


def ler_float(nome, padrao):
    return float(ler(nome, padrao))


def existe(nome):
    return nome in os.environ


def definir(nome, valor):
    """Atualiza o ambiente do processo (usado após gravar o ``.env``)."""
    os.environ[nome] = valor


def remover(nome):
    os.environ.pop(nome, None)
