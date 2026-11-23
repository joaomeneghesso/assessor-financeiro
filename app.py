from telegram_design import message_html
import os
import re
import random
import calendar
import asyncio
import secrets
import sys
import logging
from datetime import date, datetime, timedelta, time, timezone
import relogio
from time import monotonic as _monotonic
from pathlib import Path

import config
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    TypeHandler,
    ApplicationHandlerStop,
    filters
)

from database import init_db, buscar_transacao_por_id
from services import processar_mensagem, preparar_previa_exclusao, executar_exclusao_confirmada, exportacao_exige_pin
from services import parsear_comando_resetar_checklist
from security import AuthAttemptLimiter, chat_is_allowed, hash_secret, verify_secret, verify_pin_pairs, is_hashed_secret
from database import registrar_auditoria
import telegram_experiencia as ux
from telegram_execucao import executar_core
from telegram_recursos import TopicPending,scope_update,thread_id,thread_options


config.carregar_dotenv()


ASSESSOR_PIN = config.ler("ASSESSOR_PIN", "").strip()
ASSESSOR_PIN_HASH = config.ler("ASSESSOR_PIN_HASH", "").strip()
ASSESSOR_PIN_LENGTH = config.ler("ASSESSOR_PIN_LENGTH", "").strip()
ASSESSOR_PIN_RESET_KEY = config.ler("ASSESSOR_PIN_RESET_KEY", "").strip()
ASSESSOR_PIN_RESET_KEY_HASH = config.ler("ASSESSOR_PIN_RESET_KEY_HASH", "").strip()
ASSESSOR_AUTOLOCK_MINUTES = config.ler_int("ASSESSOR_AUTOLOCK_MINUTES", "15")
ASSESSOR_PIN_MAX_ATTEMPTS = config.ler_int("ASSESSOR_PIN_MAX_ATTEMPTS", "5")
ASSESSOR_PIN_LOCK_MINUTES = config.ler_int("ASSESSOR_PIN_LOCK_MINUTES", "15")
ASSESSOR_ALLOW_GROUPS = config.ler_bool("ASSESSOR_ALLOW_GROUPS", "false")
ASSESSOR_ALLOWED_CHAT_ID = config.ler("ASSESSOR_ALLOWED_CHAT_ID", "").strip()

ASSESSOR_ALERTAS_ATIVOS = config.ler_bool("ASSESSOR_ALERTAS_ATIVOS", "true")
ASSESSOR_ALERT_CHAT_ID = config.ler("ASSESSOR_ALERT_CHAT_ID", "").strip()
ASSESSOR_TIMEZONE = config.ler("ASSESSOR_TIMEZONE", "America/Sao_Paulo").strip() or "America/Sao_Paulo"
ASSESSOR_ALERTA_DIARIO_HORA = config.ler("ASSESSOR_ALERTA_DIARIO_HORA", "22:00").strip()
ASSESSOR_LEMBRETE_PAGAMENTOS_HORA = config.ler("ASSESSOR_LEMBRETE_PAGAMENTOS_HORA", "10:00").strip()
ASSESSOR_LEMBRETE_PAGAMENTOS_ATIVO = config.ler_bool("ASSESSOR_LEMBRETE_PAGAMENTOS_ATIVO", "true")
ASSESSOR_RESUMO_DOMINGO_HORA = config.ler("ASSESSOR_RESUMO_DOMINGO_HORA", "20:00").strip()
ASSESSOR_BACKUP_AUTOMATICO = config.ler_bool("ASSESSOR_BACKUP_AUTOMATICO", "true")
ASSESSOR_BACKUP_HORA = config.ler("ASSESSOR_BACKUP_HORA", "03:00").strip()

SESSOES_SEGURANCA = {}
PIN_TECLADO = {}
AUTH_LIMITER = AuthAttemptLimiter(ASSESSOR_PIN_MAX_ATTEMPTS, ASSESSOR_PIN_LOCK_MINUTES)

COMANDOS_PUBLICOS = {
    "/start",
    "/help",
    "/aprender",
    "/limpar",
    "/clear",
    "/seguranca",
    "/segurança",
    "start",
    "help",
    "aprender",
    "aula",
    "treinamento",
    "limpar",
    "clear",
    "bloquear",
    "seguranca",
    "segurança",
    "esqueci pin",
    "esqueci meu pin",
    "/esqueci_pin",
}

PREFIXOS_PUBLICOS = (
    "desbloquear ",
    "/desbloquear ",
    "reset ",
    "resetar ",
    "resetar pin ",
    "redefinir pin ",
    "trocar pin ",
    "/reset ",
    "/resetarpin ",
)


def obter_sessao_seguranca(user_id: int | str | None):
    if user_id is None:
        user_id = "desconhecido"

    if user_id not in SESSOES_SEGURANCA:
        SESSOES_SEGURANCA[user_id] = {
            "desbloqueado": False,
            "ultimo_acesso": None,
        }

    return SESSOES_SEGURANCA[user_id]


def _pin_armazenado():
    return ASSESSOR_PIN_HASH or ASSESSOR_PIN


def _recovery_armazenada():
    return ASSESSOR_PIN_RESET_KEY_HASH or ASSESSOR_PIN_RESET_KEY


def pin_configurado():
    return bool(_pin_armazenado())


def pin_tamanho_configurado():
    if ASSESSOR_PIN_HASH:
        try:
            return int(ASSESSOR_PIN_LENGTH)
        except (TypeError, ValueError):
            return 0
    return len(ASSESSOR_PIN)


def validar_pin_informado(valor: str) -> bool:
    return verify_secret(str(valor or ""), _pin_armazenado())


def validar_chave_recuperacao(valor: str) -> bool:
    return verify_secret(str(valor or ""), _recovery_armazenada())


def assessor_esta_desbloqueado(user_id: int | str | None):
    if not pin_configurado():
        return True

    sessao = obter_sessao_seguranca(user_id)

    if not sessao["desbloqueado"]:
        return False

    ultimo_acesso = sessao.get("ultimo_acesso")

    if not ultimo_acesso:
        sessao["desbloqueado"] = False
        return False

    limite = timedelta(minutes=ASSESSOR_AUTOLOCK_MINUTES)

    # O relógio de parede pode voltar (NTP/CMOS). O tempo monotônico mede a
    # inatividade real; o bloqueio vale quando qualquer um dos dois excede.
    ultimo_mono = sessao.get("ultimo_acesso_mono")
    if ultimo_mono is not None and _monotonic() - ultimo_mono > limite.total_seconds():
        sessao["desbloqueado"] = False
        return False

    if relogio.agora() - ultimo_acesso > limite:
        sessao["desbloqueado"] = False
        return False

    return True


def marcar_acesso_seguro(user_id: int | str | None):
    if not pin_configurado():
        return

    sessao = obter_sessao_seguranca(user_id)
    sessao["ultimo_acesso"] = relogio.agora()
    sessao["ultimo_acesso_mono"] = _monotonic()


def desbloquear_assessor(user_id: int | str | None):
    sessao = obter_sessao_seguranca(user_id)
    sessao["desbloqueado"] = True
    sessao["ultimo_acesso"] = relogio.agora()
    sessao["ultimo_acesso_mono"] = _monotonic()


def bloquear_assessor(user_id: int | str | None):
    sessao = obter_sessao_seguranca(user_id)
    sessao["desbloqueado"] = False
    sessao["ultimo_acesso"] = None
    sessao["ultimo_acesso_mono"] = None
    # Bloquear também descarta a ação sensível que aguardava o PIN (B9).
    descartar_acao_pendente_pin(user_id)


def comando_publico(texto: str | None):
    texto_limpo = (texto or "").lower().strip()

    if texto_limpo in COMANDOS_PUBLICOS:
        return True

    return any(texto_limpo.startswith(prefixo) for prefixo in PREFIXOS_PUBLICOS)


def obter_caminho_env():
    return Path(__file__).resolve().parent / ".env"


def _gravar_env_atomico(caminho_env: Path, conteudo: str):
    """Grava o .env sem janela de arquivo truncado (B5): tmp no mesmo diretório + os.replace."""
    temporario = caminho_env.with_name(caminho_env.name + f".{os.getpid()}.tmp")
    try:
        with open(temporario, "w", encoding="utf-8", newline="") as arquivo:
            arquivo.write(conteudo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho_env)
    finally:
        if temporario.exists():
            try:
                temporario.unlink()
            except OSError:
                pass


def atualizar_valor_env(chave: str, valor: str):
    caminho_env = obter_caminho_env()

    if caminho_env.exists():
        linhas = caminho_env.read_text(encoding="utf-8").splitlines()
    else:
        linhas = []

    nova_linha = f"{chave}={valor}"
    atualizado = False
    novas_linhas = []

    for linha in linhas:
        if linha.strip().startswith(f"{chave}="):
            novas_linhas.append(nova_linha)
            atualizado = True
        else:
            novas_linhas.append(linha)

    if not atualizado:
        if novas_linhas and novas_linhas[-1].strip():
            novas_linhas.append("")
        novas_linhas.append(nova_linha)

    _gravar_env_atomico(caminho_env, "\n".join(novas_linhas) + "\n")
    config.definir(chave, valor)


def remover_valor_env(chave: str):
    caminho_env = obter_caminho_env()
    if not caminho_env.exists():
        config.remover(chave)
        return
    prefixo = f"{chave}="
    linhas = [linha for linha in caminho_env.read_text(encoding="utf-8").splitlines() if not linha.strip().startswith(prefixo)]
    _gravar_env_atomico(caminho_env, "\n".join(linhas).rstrip() + "\n")
    config.remover(chave)


def salvar_pin_protegido(novo_pin: str):
    global ASSESSOR_PIN, ASSESSOR_PIN_HASH, ASSESSOR_PIN_LENGTH
    protegido = hash_secret(novo_pin)
    atualizar_valor_env("ASSESSOR_PIN_HASH", protegido)
    atualizar_valor_env("ASSESSOR_PIN_LENGTH", str(len(novo_pin)))
    remover_valor_env("ASSESSOR_PIN")
    ASSESSOR_PIN = ""
    ASSESSOR_PIN_HASH = protegido
    ASSESSOR_PIN_LENGTH = str(len(novo_pin))


def validar_novo_pin(pin: str):
    pin = (pin or "").strip()

    if not pin.isdigit():
        return False, "O novo PIN deve conter apenas números."

    if len(pin) < 6:
        return False, "O novo PIN precisa ter pelo menos 6 dígitos."

    if len(pin) > 8:
        return False, "O novo PIN deve ter no máximo 8 dígitos."

    return True, ""


def montar_instrucao_reset_pin():
    if not _recovery_armazenada():
        return (
            "🔐 Recuperação de PIN não configurada\n\n"
            "Para habilitar reset seguro, adicione no seu .env:\n\n"
            "ASSESSOR_PIN_RESET_KEY=uma_chave_forte\n\n"
            "Depois reinicie o bot.\n\n"
            "Se você esqueceu o PIN agora, pare o bot e rode no computador:\n"
            "preparar_seguranca_v40.py\n"
            "Ele grava só o hash do novo PIN. Nunca escreva o PIN em texto puro no .env."
        )

    return (
        "🔐 Recuperação de PIN\n\n"
        "Não precisa decorar comando.\n\n"
        "Toque no botão abaixo para começar a recuperação guiada.\n"
        "Eu vou pedir a chave mestre, apagar a mensagem dela, pedir o novo PIN e confirmar."
    )


PENDENCIA_RESET_PIN_TTL = timedelta(minutes=5)
PENDENCIA_EXCLUSAO_TTL = timedelta(minutes=10)
RESET_PIN_EXPIRADOS = set()
EXCLUSAO_EXPIRADAS = set()
MENSAGEM_PENDENCIA_EXPIRADA = "⏳ Pendência expirada.\n\nNada foi apagado. Se ainda quiser, peça a exclusão novamente."
TEXTOS_CONFIRMAR_EXCLUSAO = frozenset({"confirmar exclusao", "confirmar exclusão"})
TEXTOS_ALTERACAO_PENDENTE = frozenset({"confirmar alteracao", "confirmar alteração",
                                       "cancelar alteracao", "cancelar alteração"})


def _pendencia_expirada(pendencia, ttl) -> bool:
    criado = (pendencia or {}).get("criado_em")
    if not isinstance(criado, datetime):
        return True
    return relogio.agora() - criado > ttl


def obter_pendencia_reset_pin(user_id):
    if user_id is None:
        user_id = "desconhecido"
    pendencia = PENDENCIAS_RESET_PIN.get(user_id)
    if pendencia and _pendencia_expirada(pendencia, PENDENCIA_RESET_PIN_TTL):
        PENDENCIAS_RESET_PIN.pop(user_id, None)
        RESET_PIN_EXPIRADOS.add(user_id)
        return None
    return pendencia


def definir_pendencia_reset_pin(user_id, etapa: str, dados: dict | None = None):
    if user_id is None:
        user_id = "desconhecido"

    PENDENCIAS_RESET_PIN[user_id] = {
        "etapa": etapa,
        "dados": dados or {},
        "criado_em": relogio.agora(),
    }


def limpar_pendencia_reset_pin(user_id):
    if user_id is None:
        user_id = "desconhecido"
    PENDENCIAS_RESET_PIN.pop(user_id, None)


def montar_botoes_iniciar_reset_pin():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔑 Resetar PIN", callback_data="pin_resetar"),
        ],
        [
            InlineKeyboardButton("✖️ Cancelar", callback_data="pin_cancelar"),
        ],
    ])


async def iniciar_reset_pin_guiado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else None

    if not _recovery_armazenada():
        mensagem = montar_instrucao_reset_pin()
        if update.callback_query:
            await update.callback_query.message.reply_text(message_html(mensagem), parse_mode="HTML")
        else:
            await enviar_resposta(update, mensagem, mostrar_menu=False, comando_executado="/seguranca")
        return True

    definir_pendencia_reset_pin(user_id, "chave")
    limpar_teclado_pin(user_id)
    bloquear_assessor(user_id)

    texto = (
        "🔑 Recuperação guiada de PIN\n\n"
        "Etapa 1 de 3 — envie sua chave mestre de recuperação.\n\n"
        "Por segurança, vou tentar apagar sua mensagem logo depois do envio.\n\n"
        "Para sair, envie: cancelar"
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(
            message_html(texto), parse_mode="HTML", reply_markup=montar_teclado_cancelar_reset_pin())
    else:
        await enviar_resposta(update, texto, mostrar_menu=False, comando_executado="/seguranca")

    return True


def montar_teclado_cancelar_reset_pin():
    return InlineKeyboardMarkup([[InlineKeyboardButton("✖️ Cancelar recuperação", callback_data="pin_reset_cancelar")]])


async def processar_reset_pin_guiado(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str):
    global ASSESSOR_PIN

    user_id = update.effective_user.id if update.effective_user else None
    pendencia = obter_pendencia_reset_pin(user_id)

    if not pendencia:
        return False

    texto_original = (texto or "").strip()
    texto_limpo = texto_original.lower().strip()
    etapa = pendencia.get("etapa")
    dados = pendencia.get("dados", {})

    if texto_limpo in ["cancelar", "sair", "voltar"]:
        await tentar_apagar_mensagem_usuario(update, context)
        limpar_pendencia_reset_pin(user_id)
        bloquear_assessor(user_id)
        await enviar_resposta(
            update,
            "Recuperação de PIN cancelada.\n\nNada foi alterado.",
            mostrar_menu=False,
            comando_executado="/seguranca"
        )
        await enviar_teclado_pin(update, renovar=True)
        return True

    if etapa == "chave":
        await tentar_apagar_mensagem_usuario(update, context)

        chat_id = update.effective_chat.id if update.effective_chat else None
        locked, remaining = AUTH_LIMITER.status(user_id, chat_id, "recovery")
        if locked:
            limpar_pendencia_reset_pin(user_id)
            await enviar_resposta(update, f"🔒 Recuperação bloqueada temporariamente. Aguarde aproximadamente {remaining} minuto(s).", mostrar_menu=False, comando_executado="/seguranca")
            return True

        if not validar_chave_recuperacao(texto_original):
            bloquear_assessor(user_id)
            locked, remaining, failures = AUTH_LIMITER.register_failure(user_id, chat_id, "recovery")
            registrar_auditoria("autenticacao", user_id, "recovery_falha", dados_depois={"falhas": failures, "bloqueado": locked}, origem="telegram", usuario_sessao=f"{user_id}:{chat_id}")
            if locked:
                limpar_pendencia_reset_pin(user_id)
                await enviar_resposta(update, f"🔒 Muitas tentativas de recuperação. Aguarde aproximadamente {remaining} minuto(s).", mostrar_menu=False, comando_executado="/seguranca")
                return True
            definir_pendencia_reset_pin(user_id, "chave")
            await enviar_resposta(
                update,
                "❌ Chave mestre incorreta.\n\n"
                "O assessor continua bloqueado.\n"
                "Envie a chave novamente ou envie: cancelar",
                mostrar_menu=False,
                comando_executado="/seguranca"
            )
            return True

        AUTH_LIMITER.register_success(user_id, chat_id, "recovery")
        registrar_auditoria("autenticacao", user_id, "recovery_sucesso", origem="telegram", usuario_sessao=f"{user_id}:{chat_id}")
        definir_pendencia_reset_pin(user_id, "novo_pin")
        await enviar_resposta(
            update,
            "✅ Chave validada.\n\n"
            "Etapa 2 de 3 — envie o novo PIN.\n\n"
            "Regras:\n"
            "• apenas números\n"
            "• mínimo 6 dígitos\n"
            "• máximo 8 dígitos\n\n"
            "Também vou tentar apagar essa mensagem.",
            mostrar_menu=False,
            comando_executado="/seguranca"
        )
        return True

    if etapa == "novo_pin":
        await tentar_apagar_mensagem_usuario(update, context)

        valido, motivo = validar_novo_pin(texto_original)

        if not valido:
            await enviar_resposta(
                update,
                f"❌ PIN inválido\n\n{motivo}\n\nEnvie outro PIN ou envie: cancelar",
                mostrar_menu=False,
                comando_executado="/seguranca"
            )
            return True

        definir_pendencia_reset_pin(user_id, "confirmar_pin", {"novo_pin": texto_original})
        await enviar_resposta(
            update,
            "Etapa 3 de 3 — confirme o novo PIN.\n\n"
            "Envie o mesmo PIN novamente.\n\n"
            "Também vou tentar apagar essa mensagem.",
            mostrar_menu=False,
            comando_executado="/seguranca"
        )
        return True

    if etapa == "confirmar_pin":
        await tentar_apagar_mensagem_usuario(update, context)

        novo_pin = dados.get("novo_pin", "")

        if not secrets.compare_digest(str(texto_original), str(novo_pin)):
            definir_pendencia_reset_pin(user_id, "novo_pin")
            await enviar_resposta(
                update,
                "❌ Os PINs não conferem.\n\n"
                "Vamos tentar novamente.\n"
                "Envie o novo PIN.",
                mostrar_menu=False,
                comando_executado="/seguranca"
            )
            return True

        salvar_pin_protegido(novo_pin)
        limpar_pendencia_reset_pin(user_id)
        limpar_teclado_pin(user_id)
        bloquear_assessor(user_id)

        await enviar_resposta(
            update,
            "✅ PIN redefinido com sucesso.\n\n"
            "Agora desbloqueie o assessor usando o novo PIN.",
            mostrar_menu=False,
            comando_executado="/seguranca"
        )
        await enviar_teclado_pin(update, renovar=True)
        return True

    limpar_pendencia_reset_pin(user_id)
    return False



async def tentar_apagar_mensagem_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_chat and update.message:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
    except Exception:
        pass


async def processar_reset_pin(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str):
    global ASSESSOR_PIN

    texto_limpo = (texto or "").strip()

    if not _recovery_armazenada():
        await enviar_resposta(
            update,
            montar_instrucao_reset_pin(),
            mostrar_menu=False,
            comando_executado="/seguranca"
        )
        return True

    partes = texto_limpo.split()
    comando = partes[0].lower() if partes else ""
    if len(partes) >= 2:
        # A chave mestra pode estar na mensagem mesmo quando o formato está
        # incompleto: apaga antes de validar os argumentos.
        await tentar_apagar_mensagem_usuario(update, context)

    # Formatos aceitos:
    # reset CHAVE NOVO_PIN
    # resetar CHAVE NOVO_PIN
    # /reset CHAVE NOVO_PIN
    # /resetarpin CHAVE NOVO_PIN
    # resetar pin CHAVE NOVO_PIN
    # redefinir pin CHAVE NOVO_PIN
    # trocar pin CHAVE NOVO_PIN
    chave_informada = None
    novo_pin = None

    if comando in ["reset", "resetar", "/reset", "/resetarpin"]:
        if len(partes) >= 3 and partes[1].lower() != "pin":
            chave_informada = partes[1]
            novo_pin = partes[2]
        elif len(partes) >= 4 and partes[1].lower() == "pin":
            chave_informada = partes[2]
            novo_pin = partes[3]
    elif comando in ["redefinir", "trocar"]:
        if len(partes) >= 4 and partes[1].lower() == "pin":
            chave_informada = partes[2]
            novo_pin = partes[3]

    if not chave_informada or not novo_pin:
        await enviar_resposta(update, montar_instrucao_reset_pin(), mostrar_menu=False, comando_executado="/seguranca")
        return True

    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    locked, remaining = AUTH_LIMITER.status(user_id, chat_id, "recovery")
    if locked:
        await enviar_resposta(update, f"🔒 Recuperação bloqueada temporariamente. Aguarde aproximadamente {remaining} minuto(s).", mostrar_menu=False, comando_executado="/seguranca")
        return True

    if not validar_chave_recuperacao(chave_informada):
        bloquear_assessor(user_id)
        locked, remaining, failures = AUTH_LIMITER.register_failure(user_id, chat_id, "recovery")
        registrar_auditoria("autenticacao", user_id, "recovery_falha", dados_depois={"falhas": failures, "bloqueado": locked}, origem="telegram", usuario_sessao=f"{user_id}:{chat_id}")
        if locked:
            await enviar_resposta(update, f"🔒 Muitas tentativas de recuperação. Aguarde aproximadamente {remaining} minuto(s).", mostrar_menu=False, comando_executado="/seguranca")
            return True
        await enviar_resposta(
            update,
            "❌ Chave de recuperação incorreta.\n\n"
            "O assessor continua bloqueado.",
            mostrar_menu=False,
            comando_executado="/seguranca"
        )
        return True

    AUTH_LIMITER.register_success(user_id, chat_id, "recovery")
    registrar_auditoria("autenticacao", user_id, "recovery_sucesso", origem="telegram", usuario_sessao=f"{user_id}:{chat_id}")

    valido, motivo = validar_novo_pin(novo_pin)

    if not valido:
        await enviar_resposta(
            update,
            f"❌ PIN inválido\n\n{motivo}",
            mostrar_menu=False,
            comando_executado="/seguranca"
        )
        return True

    salvar_pin_protegido(novo_pin)

    limpar_teclado_pin(user_id)
    bloquear_assessor(user_id)

    await enviar_resposta(
        update,
        "✅ PIN redefinido com sucesso\n\n"
        "Agora desbloqueie o assessor usando o novo PIN no teclado seguro.",
        mostrar_menu=False,
        comando_executado="/seguranca"
    )

    await enviar_teclado_pin(update, renovar=True)
    return True


def gerar_pares_teclado_pin():
    numeros = list("0123456789")
    random.shuffle(numeros)

    pares = []
    for indice in range(0, 10, 2):
        par = numeros[indice:indice + 2]
        pares.append(tuple(par))

    return pares


def iniciar_teclado_pin(user_id: int | str | None):
    pares = gerar_pares_teclado_pin()

    PIN_TECLADO[user_id] = {
        "pares": pares,
        "escolhas": [],
        "tentativas": 0,
        "criado_em": relogio.agora(),
    }

    return PIN_TECLADO[user_id]


def obter_estado_teclado_pin(user_id: int | str | None):
    estado = PIN_TECLADO.get(user_id)

    if not estado:
        estado = iniciar_teclado_pin(user_id)

    return estado


def limpar_teclado_pin(user_id: int | str | None):
    PIN_TECLADO.pop(user_id, None)


def montar_teclado_pin(user_id: int | str | None):
    estado = obter_estado_teclado_pin(user_id)
    pares = estado["pares"]

    botoes = []

    # Layout visual:
    # [1-8] [9-3]
    # [0-4] [5-6]
    # [2-7]
    # [Cancelar]
    #
    # O embaralhamento continua acontecendo internamente a cada nova abertura,
    # erro crítico ou cancelamento. Não exibimos isso ao usuário.
    for indice in range(0, len(pares), 2):
        if indice + 1 < len(pares):
            botoes.append([
                InlineKeyboardButton(f"{pares[indice][0]}-{pares[indice][1]}", callback_data=f"pin_pair:{indice}"),
                InlineKeyboardButton(f"{pares[indice + 1][0]}-{pares[indice + 1][1]}", callback_data=f"pin_pair:{indice + 1}"),
            ])
        else:
            botoes.append([
                InlineKeyboardButton(f"{pares[indice][0]}-{pares[indice][1]}", callback_data=f"pin_pair:{indice}"),
            ])

    botoes.append([
        InlineKeyboardButton("⌫ Limpar", callback_data="pin_limpar"),
        InlineKeyboardButton("✖️ Cancelar", callback_data="pin_cancelar"),
    ])

    botoes.append([
        InlineKeyboardButton("🔑 Resetar PIN", callback_data="pin_resetar"),
    ])

    return InlineKeyboardMarkup(botoes)


def obter_mensagem_teclado_pin(user_id: int | str | None):
    estado = obter_estado_teclado_pin(user_id)
    escolhas = estado.get("escolhas", [])
    total = max(pin_tamanho_configurado(), 6) if pin_configurado() else 6
    progresso = "●" * len(escolhas) + "○" * max(total - len(escolhas), 0)

    return (
        "🔒 Assessor bloqueado\n\n"
        "Toque nos botões seguindo a sequência do seu PIN.\n\n"
        f"PIN: {progresso}"
    )


async def enviar_teclado_pin(update: Update, renovar: bool = False):
    user_id = update.effective_user.id if update.effective_user else None

    if renovar or user_id not in PIN_TECLADO:
        iniciar_teclado_pin(user_id)

    texto = obter_mensagem_teclado_pin(user_id)
    teclado = montar_teclado_pin(user_id)

    if update.callback_query:
        mensagem = await update.callback_query.message.reply_text(message_html(texto), reply_markup=teclado, parse_mode="HTML")
        registrar_mensagem_enviada(mensagem)
        return mensagem

    if update.message:
        mensagem = await update.message.reply_text(message_html(texto), reply_markup=teclado, parse_mode="HTML")
        registrar_mensagem_enviada(mensagem)
        return mensagem

    return None


async def processar_callback_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    dados = query.data

    if dados == "pin_reset_cancelar":
        # Mesmo efeito de digitar "cancelar" na recuperação guiada de PIN.
        if not obter_pendencia_reset_pin(user_id):
            await query.message.edit_text("Não há recuperação de PIN em andamento.")
            return True
        limpar_pendencia_reset_pin(user_id)
        bloquear_assessor(user_id)
        await query.message.edit_text("Recuperação de PIN cancelada.\n\nNada foi alterado.")
        await enviar_teclado_pin(update, renovar=True)
        return True

    locked, remaining = AUTH_LIMITER.status(user_id, chat_id, "pin")
    if locked:
        limpar_teclado_pin(user_id)
        await query.message.edit_text(
            f"🔒 Desbloqueio temporariamente bloqueado. Tente novamente em aproximadamente {remaining} minuto(s)."
        )
        return True

    if not pin_configurado():
        await query.message.edit_text(mensagem_bloqueio_seguranca())
        return True

    if dados == "pin_cancelar":
        limpar_teclado_pin(user_id)
        descartar_acao_pendente_pin(user_id)
        await query.message.edit_text("🔒 Desbloqueio cancelado.")
        return True

    if dados == "pin_limpar":
        estado = obter_estado_teclado_pin(user_id)
        estado["escolhas"] = []
        await query.message.edit_text(
            obter_mensagem_teclado_pin(user_id),
            reply_markup=montar_teclado_pin(user_id)
        )
        return True

    if dados == "pin_resetar":
        await iniciar_reset_pin_guiado(update, context)
        return True

    if not dados.startswith("pin_pair:"):
        return False

    estado = obter_estado_teclado_pin(user_id)
    pin_len = pin_tamanho_configurado()

    try:
        indice = int(dados.split(":", 1)[1])
    except ValueError:
        iniciar_teclado_pin(user_id)
        await query.message.edit_text(
            obter_mensagem_teclado_pin(user_id),
            reply_markup=montar_teclado_pin(user_id)
        )
        return True

    pares = estado.get("pares") or []

    if indice < 0 or indice >= len(pares):
        iniciar_teclado_pin(user_id)
        await query.message.edit_text(
            obter_mensagem_teclado_pin(user_id),
            reply_markup=montar_teclado_pin(user_id)
        )
        return True

    # A verificação do PIN roda fora do loop (PBKDF2 x até 2^n candidatos).
    # Enquanto ela não termina, toques extras são ignorados para não contar
    # a mesma tentativa duas vezes no limitador.
    if estado.get("verificando"):
        return True

    escolhas = estado.setdefault("escolhas", [])
    escolhas.append(indice)

    # Segurança: não damos veredito parcial. O usuário escolhe todos os botões
    # e só no final informamos se o PIN está correto ou não.
    if len(escolhas) < pin_len:
        await query.message.edit_text(
            obter_mensagem_teclado_pin(user_id),
            reply_markup=montar_teclado_pin(user_id)
        )
        return True

    pares_escolhidos = [tuple(pares[indice]) for indice in escolhas[:pin_len]]
    # Executa em thread: a verificação leva segundos e, no loop, congelava o bot
    # inteiro (alertas, lembretes e outras mensagens) durante cada tentativa.
    estado["verificando"] = True
    try:
        pin_correto = await asyncio.to_thread(verify_pin_pairs, pares_escolhidos, _pin_armazenado(), pin_len)
    finally:
        estado["verificando"] = False

    if pin_correto:
        AUTH_LIMITER.register_success(user_id, chat_id, "pin")
        registrar_auditoria("autenticacao", user_id, "pin_sucesso", origem="telegram", usuario_sessao=f"{user_id}:{chat_id}")
        desbloquear_assessor(user_id)
        limpar_teclado_pin(user_id)

        await query.message.edit_text(
            "🔓 Assessor desbloqueado\n\n"
            f"Autobloqueio em {ASSESSOR_AUTOLOCK_MINUTES} minuto(s) sem uso.\n"
            "Quando terminar, toque em Bloquear agora (ou envie: bloquear).",
            reply_markup=InlineKeyboardMarkup([[botao_comando("🔒 Bloquear agora", "__bloquear__", "danger")]]),
        )
        if not await reexecutar_acao_pendente_pin(user_id, context):
            await menu_command(update, context)
        return True

    estado["tentativas"] = estado.get("tentativas", 0) + 1
    locked, remaining, failures = AUTH_LIMITER.register_failure(user_id, chat_id, "pin")
    registrar_auditoria(
        "autenticacao", user_id, "pin_falha",
        dados_depois={"falhas": failures, "bloqueado": locked},
        origem="telegram", usuario_sessao=f"{user_id}:{chat_id}"
    )

    if locked:
        limpar_teclado_pin(user_id)
        descartar_acao_pendente_pin(user_id)
        await query.message.edit_text(
            f"🔒 Muitas tentativas incorretas. O desbloqueio foi bloqueado por aproximadamente {remaining} minuto(s)."
        )
        return True

    estado["escolhas"] = []
    await query.message.edit_text(
        "❌ PIN incorreto.\n\n"
        "Tente novamente pelo teclado abaixo.\n"
        "Se tocar errado antes de terminar, use Limpar.\n\n"
        + obter_mensagem_teclado_pin(user_id),
        reply_markup=montar_teclado_pin(user_id)
    )
    return True



def mensagem_bloqueio_seguranca():
    if not pin_configurado():
        return (
            "🔓 Segurança do assessor\n\n"
            "PIN interno ainda não configurado.\n\n"
            "Para ativar, adicione no arquivo .env:\n"
            "ASSESSOR_PIN_HASH=<gerado por preparar_seguranca_v40.py>\n"
            "ASSESSOR_AUTOLOCK_MINUTES=15\n\n"
            "Depois reinicie o bot."
        )

    return (
        "🔐 Proteção reforçada bloqueada\n\n"
        "O uso diário continua liberado para o seu Telegram autorizado. "
        "O PIN será solicitado apenas em ações sensíveis."
    )


def acao_exige_pin(texto: str | None, _canonico: bool = False) -> bool:
    """PIN de segunda camada apenas para ações de alto impacto ou exfiltração.

    Consultas, lançamentos, pagamentos, correções individuais e navegação ficam
    protegidos pela allowlist Telegram e não exigem PIN no uso diário.
    """
    # O núcleo junta espaços e resolve sinônimos antes de executar; o gate precisa enxergar o
    # mesmo texto, senão "gerar  backup" (dois espaços, tab, NBSP) passaria sem PIN.
    clean = re.sub(r'\s+', ' ', texto or '').strip().lower()
    if not clean:
        return False
    if not _canonico:
        try:
            from services import normalizar_comando_sinonimos
            canonico = normalizar_comando_sinonimos(clean) or clean
        except Exception:
            canonico = clean
        if canonico != clean and acao_exige_pin(canonico, _canonico=True):
            return True

    # Segredos / redefinição de credenciais. A recuperação continua usando a
    # chave mestre própria, mas estes comandos nunca devem ser tratados como
    # uso financeiro comum.
    if clean.startswith((
        'reset ', 'resetar ', 'resetar pin ', 'redefinir pin ', 'trocar pin ',
        '/reset ', '/resetarpin '
    )) and not parsear_comando_resetar_checklist(clean):
        return True

    # Cópia integral do banco ou exportação total: alto impacto de exposição.
    if clean in {'backup', 'gerar backup', 'exportar csv tudo', 'exportar tudo',
                 'exportar csv completo', 'exportar csv completa',
                 'exportar csv base inteira'}:
        return True

    # O diagnóstico reúne metadados operacionais do banco, backups e recursos
    # instalados. Mesmo sem expor credenciais, pertence à área administrativa.
    if clean in {'status', '/status', 'saude do assessor', 'saúde do assessor'}:
        return True

    # Importação confirmada grava vários registros de uma só vez.
    if clean in {'confirmar importacao', 'confirmar importação'}:
        return True

    # Exclusão por faixa é destrutiva em massa. Exclusão de um único item continua
    # rápida e já possui confirmação explícita.
    if re.match(r'^(?:apagar|excluir|deletar|remover|tirar)\s+\d+\s*-\s*\d+$', clean):
        return True

    return False


ACAO_PENDENTE_PIN_TTL_SEGUNDOS = 120
ACAO_PENDENTE_PIN = {}


def guardar_acao_pendente_pin(user_id, update):
    """Lembra a ação bloqueada por PIN (apenas o update original, com validade curta)."""
    ACAO_PENDENTE_PIN[user_id] = {
        "update": update,
        "expira_mono": _monotonic() + ACAO_PENDENTE_PIN_TTL_SEGUNDOS,
    }


def descartar_acao_pendente_pin(user_id):
    ACAO_PENDENTE_PIN.pop(user_id, None)


def retirar_acao_pendente_pin(user_id):
    """Devolve o update pendente ainda válido (e o remove); None se não houver/expirou."""
    pendente = ACAO_PENDENTE_PIN.pop(user_id, None)
    if not pendente or _monotonic() > pendente["expira_mono"]:
        return None
    return pendente["update"]


async def reexecutar_acao_pendente_pin(user_id, context) -> bool:
    """Após desbloqueio correto, refaz a ação originalmente bloqueada."""
    original = retirar_acao_pendente_pin(user_id)
    if original is None:
        return False
    try:
        if getattr(original, "callback_query", None) is not None:
            await callback_submenu(original, context)
        else:
            await receber_mensagem(original, context)
    except Exception:
        logging.exception("Falha ao reexecutar a ação pendente após o desbloqueio.")
        return False
    return True


async def bloquear_se_assessor_travado(update: Update, texto: str | None = None):
    sessao = chave_sessao_update(update)
    if not pin_configurado() or (not acao_exige_pin(texto) and not exportacao_exige_pin(texto, sessao)):
        return False

    user_id = update.effective_user.id if update.effective_user else None

    if assessor_esta_desbloqueado(user_id):
        marcar_acesso_seguro(user_id)
        return False

    # Guarda a ação bloqueada (nunca o PIN) para reexecutá-la após o desbloqueio.
    guardar_acao_pendente_pin(user_id, update)
    await enviar_teclado_pin(update, renovar=True)
    return True


def obter_status_seguranca(update: Update):
    user_id = update.effective_user.id if update.effective_user else None
    sessao = obter_sessao_seguranca(user_id)
    desbloqueado = assessor_esta_desbloqueado(user_id)

    linhas = [
        "🛡️ Segurança do assessor",
        "",
        "Acesso diário: Telegram autorizado (Quick Access)",
        f"PIN reforçado configurado: {'sim' if pin_configurado() else 'não'}",
        f"Proteção reforçada: {'desbloqueada' if desbloqueado else 'bloqueada'}",
        f"Sessão sensível: {ASSESSOR_AUTOLOCK_MINUTES} minuto(s)",
        "",
        "Sem PIN: saldo, histórico, faturas, lançamentos, pagamentos e correções individuais.",
        "Com PIN: status técnico, backup, exportação completa, importação confirmada e exclusão em lote.",
        "",
        "Comandos:",
        "desbloquear <PIN> · libera temporariamente ações sensíveis",
        "bloquear · encerra somente a sessão sensível",
        "/seguranca",
    ]

    ultimo_acesso = sessao.get("ultimo_acesso")
    if ultimo_acesso:
        linhas.extend([
            "",
            f"Último acesso seguro: {ultimo_acesso.strftime('%Y-%m-%d %H:%M:%S')}",
        ])

    if not pin_configurado():
        linhas.extend([
            "",
            "Para ativar, adicione no .env:",
            "ASSESSOR_PIN_HASH=<gerado por preparar_seguranca_v40.py>",
            "ASSESSOR_AUTOLOCK_MINUTES=15",
        ])

    return "\n".join(linhas)



MESES_PT = {
    1: "janeiro",
    2: "fevereiro",
    3: "março",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}

MESES_PT_CURTO = {
    1: "jan",
    2: "fev",
    3: "mar",
    4: "abr",
    5: "mai",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "set",
    10: "out",
    11: "nov",
    12: "dez",
}


def formatar_ano_mes_exibicao(ano_mes: str, curto: bool = False):
    match = re.match(r"^(20\d{2})-(\d{2})$", ano_mes or "")
    if not match:
        return ano_mes

    ano = int(match.group(1))
    mes = int(match.group(2))

    if mes < 1 or mes > 12:
        return ano_mes

    nome_mes = MESES_PT_CURTO[mes] if curto else MESES_PT[mes]
    return f"{nome_mes}/{ano}"


def formatar_data_exibicao(data_texto: str):
    match = re.match(r"^(20\d{2})-(\d{2})-(\d{2})$", data_texto or "")
    if not match:
        return data_texto

    ano = int(match.group(1))
    mes = int(match.group(2))
    dia = int(match.group(3))

    if mes < 1 or mes > 12 or dia < 1 or dia > 31:
        return data_texto

    return f"{dia:02d}/{MESES_PT[mes]}/{ano}"


def linha_parece_comando_ou_exemplo(linha: str):
    texto = (linha or "").strip().lower()

    if not texto:
        return False

    prefixos_comando = [
        "/help",
        "/menu",
        "/start",
            "agenda ",
        "categorias ",
        "categoria ",
        "detalhar ",
        "contas ",
        "formas ",
        "parcelas ",
        "parcelamento ",
        "resumo ",
        "saldo ",
        "fechamento ",
        "relatório ",
        "relatorio ",
        "exportar csv ",
        "quanto vou pagar ",
        "quanto gastei ",
        "mudar ",
        "corrigir ",
        "apagar ",
        "excluir ",
        "meta ",
        "novo fixo ",
        "novo ",
        "fixo novo ",
        "cadastrar fixo ",
        "recebi ",
        "gastei ",
        "paguei ",
        "comprei ",
        "simular ",
        "posso comprar ",
        "vale a pena comprar ",
    ]

    if any(texto.startswith(prefixo) for prefixo in prefixos_comando):
        return True

    indicadores_exemplo = [
        "exemplo:",
        "exemplos:",
        "use o formato:",
        "envie:",
        "comando:",
        "comandos:",
    ]

    if any(indicador in texto for indicador in indicadores_exemplo):
        return True

    return False


def formatar_datas_para_exibicao(texto):
    if not isinstance(texto, str):
        return texto

    linhas_formatadas = []

    for linha in texto.splitlines():
        if linha_parece_comando_ou_exemplo(linha):
            linhas_formatadas.append(linha)
            continue

        linha_formatada = re.sub(
            r"\b(20\d{2}-\d{2}-\d{2})\b",
            lambda m: formatar_data_exibicao(m.group(1)),
            linha
        )

        linha_formatada = re.sub(
            r"\b(20\d{2}-\d{2})\b",
            lambda m: formatar_ano_mes_exibicao(m.group(1)),
            linha_formatada
        )

        linhas_formatadas.append(linha_formatada)

    return "\n".join(linhas_formatadas)


ATALHOS_MENU = {
    "🏠 central": "menu",
    "central": "menu",
    "home": "menu",
    "início": "menu",
    "inicio": "menu",
    "❓ ajuda": "__help__",
    "ajuda": "__help__",
    "guia": "__help__",
    "manual": "__help__",
    "🎓 aprender": "aprender",
    "aprender": "aprender",
    "aula": "aprender",
    "treinamento": "aprender",
    "➕ registrar": "registrar",
    "➕ lançar": "registrar",
    "lançar": "registrar",
    "lancar": "registrar",
    "registrar": "registrar",
    "novo lançamento": "registrar",
    "nova despesa": "registrar",
    "nova entrada": "registrar",

    "📆 hoje": "hoje",
    "hoje": "hoje",
    "fechamento do dia": "hoje",

    "📊 meu mês": "meu mês",
    "📊 meu mes": "meu mês",
    "📈 dashboard": "dashboard",
    "dashboard": "dashboard",
    "dash": "dashboard",
    "painel": "dashboard",
    "🏷 dashboard categorias": "dashboard categorias",
    "dashboard categorias": "dashboard categorias",
    "dash categorias": "dashboard categorias",
    "painel categorias": "dashboard categorias",
    "categorias dashboard": "dashboard categorias",
    "meu mês": "meu mês",
    "meu mes": "meu mês",
    "resumo": "meu mês",
    "📊 resumo": "meu mês",
    "resumo do mês": "meu mês",
    "resumo do mes": "meu mês",

    "🧠 diagnóstico": "assessor",
    "🧠 diagnostico": "assessor",
    "diagnóstico": "assessor",
    "diagnostico": "assessor",
    "assessor": "assessor",
    "🧠 assessor": "assessor",

    "💳 compromissos": "compromissos",
    "compromissos": "compromissos",
    "✅ checklist": "checklist",
    "checklist": "checklist",
    "pagamentos": "checklist",
    "lista pagamentos": "checklist",
    "lista de pagamentos": "checklist",
    "agenda": "agenda",
    "📆 agenda": "agenda",

    "🔎 revisar": "revisar",
    "revisar": "revisar",
    "revisão": "revisar",
    "revisao": "revisar",

    "📤 exportar": "exportar csv",
    "exportar": "exportar csv",

    "⚙️ ajustes": "ajustes",
    "ajustes": "ajustes",
    "configurações": "ajustes",
    "configuracoes": "ajustes",
    "mais": "ajustes",

    # Compatibilidade com o menu antigo
    "🏷 categorias": "categorias",
    "categorias": "categorias",
    "💳 parcelas": "parcelamentos",
    "parcelas": "parcelamentos",
    "🧾 fixos": "fixos",
    "fixos": "fixos",
    "💰 entradas": "entradas",
    "entradas": "entradas",
    "receitas": "entradas",
}

from estado_runtime import ProtectedJsonStore

_CALLBACK_STORE = ProtectedJsonStore(Path(__file__).resolve().parent / ".runtime" / "telegram_callbacks.bin")


def _restaurar_callbacks(documento, agora=None):
    """Restaura botões salvos; qualquer formato inesperado é descartado.

    Um arquivo legível mas estranho (versão antiga, tipos trocados) não pode
    impedir o bot de iniciar: nesse caso os botões antigos apenas expiram.
    """
    try:
        agora = relogio.agora_com_fuso().timestamp() if agora is None else agora
        idade = agora - float(documento.get("saved_at") or 0)
        if not 0 <= idade <= 86400:
            return {}, 0
        comandos = {str(key): str(value) for key, value in dict(documento.get("commands") or {}).items()}
        return comandos, int(documento.get("sequence") or 0)
    except Exception:
        logging.warning("Estado de botões em .runtime ignorado (formato inesperado).", exc_info=True)
        return {}, 0


CALLBACK_COMANDOS, CALLBACK_SEQUENCIA = _restaurar_callbacks(_CALLBACK_STORE.load({}))
_CALLBACK_DIRTY = 0
_CALLBACK_LAST_SAVE = 0.0


def persistir_callback_comandos(force=False):
    global _CALLBACK_DIRTY, _CALLBACK_LAST_SAVE
    _CALLBACK_DIRTY += 1
    now = relogio.agora_com_fuso().timestamp()
    if not force and _CALLBACK_DIRTY < 10 and now - _CALLBACK_LAST_SAVE < 2:
        return
    try:
        _CALLBACK_STORE.save({
            "version": 1,
            "saved_at": now,
            "sequence": CALLBACK_SEQUENCIA,
            "commands": CALLBACK_COMANDOS,
        })
        _CALLBACK_DIRTY = 0
        _CALLBACK_LAST_SAVE = now
    except Exception:
        # Falhar fechado: o botão continua válido no processo atual e apenas
        # perde a capacidade de atravessar um reinício.
        pass

PENDENCIAS_GUIADAS = TopicPending()
PENDENCIAS_EXCLUSAO = TopicPending()
PENDENCIAS_RESET_PIN = {}
PENDENCIAS_APRENDIZADO_CATEGORIA = TopicPending()


MENSAGENS_CHAT = {}
MAX_MENSAGENS_RASTREADAS_POR_CHAT = 300


def chave_sessao_update(update: Update):
    if update and update.effective_user and update.effective_chat:return ux.session_key(update)
    user_id = update.effective_user.id if update and update.effective_user else "anon"
    chat_id = obter_chat_id_update(update) if update else "sem_chat"
    return f"{user_id}:{chat_id}"


def registrar_mensagem_chat(chat_id: int | str | None, message_id: int | None):
    if chat_id is None or message_id is None:
        return

    mensagens = MENSAGENS_CHAT.setdefault(chat_id, [])

    if message_id not in mensagens:
        mensagens.append(message_id)

    if len(mensagens) > MAX_MENSAGENS_RASTREADAS_POR_CHAT:
        del mensagens[:-MAX_MENSAGENS_RASTREADAS_POR_CHAT]


def registrar_mensagem_update(update: Update):
    if update.message:
        registrar_mensagem_chat(update.effective_chat.id, update.message.message_id)


def registrar_mensagem_enviada(mensagem):
    if not mensagem:
        return

    try:
        registrar_mensagem_chat(mensagem.chat_id, mensagem.message_id)
    except Exception:
        pass



async def enviar_acao_digitando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_chat:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=ChatAction.TYPING
            )
    except Exception:
        pass


async def enviar_acao_enviando_documento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_chat:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=ChatAction.UPLOAD_DOCUMENT
            )
    except Exception:
        pass


async def enviar_acao_enviando_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_chat:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=ChatAction.UPLOAD_PHOTO
            )
    except Exception:
        pass



def registrar_callback_guiado(acao: str):
    return registrar_callback_comando(f"guiado:{acao}")


def botao_guiado(texto: str, acao: str):
    from telegram_design import button_label, button_style
    texto = button_label(texto, ('guided', acao))
    style = button_style(texto, ('guided', acao))
    try:
        return InlineKeyboardButton(texto, callback_data=registrar_callback_guiado(acao), style=style)
    except TypeError:
        return InlineKeyboardButton(texto, callback_data=registrar_callback_guiado(acao))


def definir_pendencia_exclusao(chat_id, comando: str, previa: str):
    PENDENCIAS_EXCLUSAO[chat_id] = {
        "comando": comando,
        "previa": previa,
        "criado_em": relogio.agora(),
        "id": secrets.token_hex(6),
    }


def limpar_pendencia_exclusao(chat_id):
    PENDENCIAS_EXCLUSAO.pop(chat_id, None)


def obter_pendencia_exclusao(chat_id):
    pendencia = PENDENCIAS_EXCLUSAO.get(chat_id)
    if pendencia and _pendencia_expirada(pendencia, PENDENCIA_EXCLUSAO_TTL):
        PENDENCIAS_EXCLUSAO.pop(chat_id, None)
        EXCLUSAO_EXPIRADAS.add(chat_id)
        return None
    return pendencia


def comando_exige_confirmacao_exclusao(comando: str):
    texto = (comando or "").lower().strip()

    if not texto:
        return False

    if texto in ["__confirmar_exclusao__", "__cancelar_exclusao__"]:
        return False

    verbos = r"(?:apagar|excluir|deletar|remover|tirar|cancelar)"

    padroes = [
        rf"^{verbos}\s+(?:ultimo|último)$",
        rf"^{verbos}\s+#?\d+$",
        rf"^{verbos}\s+\d+\s*-\s*\d+$",
        rf"^{verbos}\s+(?:lançamento|lancamento|transação|transacao|movimentação|movimentacao)\s+#?\d+$",
        rf"^{verbos}\s+(?:fixo|compromisso)\s+#?c?\d+$",
        rf"^{verbos}\s+(?:entrada|receita)\s+#?e?\d+$",
        rf"^{verbos}\s+(?:parcelamento|parcela)\s+#?[pc]?\d+$",
        rf"^{verbos}\s+meta\s+.+$",
    ]

    # Mesma lista do núcleo para as exclusões que antes apagavam direto
    # (transferência de caixa, reset de checklist, data de pagamento).
    from services import PADROES_EXCLUSAO_EXTRAS, parsear_comando_resetar_checklist, _parse_apagar_data_pagamento
    return (
        any(re.match(padrao, texto) for padrao in [*padroes, *PADROES_EXCLUSAO_EXTRAS])
        or bool(parsear_comando_resetar_checklist(texto) or _parse_apagar_data_pagamento(texto))
    )


VINCULOS_BOTAO = {}
MENSAGEM_BOTAO_OBSOLETO = (
    "Esse botão é de uma mensagem antiga e não vale mais.\n\n"
    "Nada foi alterado. Use os botões da mensagem mais recente."
)


def botao_comando_vinculado(texto: str, comando: str, token: str | None, estilo: str | None = None):
    """Como botao_comando, mas o botão só vale para a pendência de id `token`."""
    botao = botao_comando(texto, comando, estilo)
    if token:
        VINCULOS_BOTAO[botao.callback_data] = token
        if len(VINCULOS_BOTAO) > 1000:
            for antiga in list(VINCULOS_BOTAO)[:500]:
                VINCULOS_BOTAO.pop(antiga, None)
    return botao


def botao_vinculo_valido(chave, pendencia) -> bool:
    """True só se o botão foi criado para a pendência atual."""
    token = VINCULOS_BOTAO.get(chave)
    return bool(token) and bool(pendencia) and pendencia.get("id") == token


def montar_botoes_confirmacao_exclusao(token: str | None = None):
    return InlineKeyboardMarkup([
        [
            botao_comando_vinculado("🗑 Sim, apagar", "__confirmar_exclusao__", token),
            botao_comando_vinculado("✖️ Não apagar", "__cancelar_exclusao__", token),
        ]
    ])


async def solicitar_confirmacao_exclusao(update: Update, comando: str):
    chat_id = obter_chat_id_update(update)
    if chat_id is None:
        return False

    previa = await executar_core(preparar_previa_exclusao,comando)

    if not previa:
        return False

    from services import previa_exclusao_recusada
    if previa_exclusao_recusada(previa):
        # Recusa: nada a confirmar, nenhuma pendência é criada.
        await enviar_resposta(update, previa, comando_executado=comando)
        return True

    definir_pendencia_exclusao(chat_id, comando, previa)

    mensagem = update.callback_query.message if update.callback_query else update.message

    texto = (
        "⚠️ Confirme a exclusão\n\n"
        f"{previa}\n\n"
        "Nada foi apagado ainda."
    )

    mensagem_enviada = await mensagem.reply_text(
        message_html(texto),
        reply_markup=montar_botoes_confirmacao_exclusao(
            (obter_pendencia_exclusao(chat_id) or {}).get("id")
        ),
        parse_mode="HTML"
    )
    registrar_mensagem_enviada(mensagem_enviada)
    return True


async def executar_confirmacao_exclusao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = obter_chat_id_update(update)
    pendencia = obter_pendencia_exclusao(chat_id)

    if not pendencia:
        expirou = chat_id in EXCLUSAO_EXPIRADAS
        EXCLUSAO_EXPIRADAS.discard(chat_id)
        mensagem = update.callback_query.message if update.callback_query else update.message
        mensagem_enviada = await mensagem.reply_text(
            message_html(MENSAGEM_PENDENCIA_EXPIRADA if expirou else "Não há exclusão pendente para confirmar."),
            reply_markup=montar_menu_principal(),
            parse_mode="HTML"
        )
        registrar_mensagem_enviada(mensagem_enviada)
        return

    comando = pendencia.get("comando")
    limpar_pendencia_exclusao(chat_id)

    # Apaga exatamente o que a prévia mostrou ("apagar último" e faixas são
    # recalculados na execução): se algo mudou, nada é apagado.
    previa_atual = await executar_core(preparar_previa_exclusao, comando)
    if pendencia.get("previa") is not None and previa_atual != pendencia.get("previa"):
        from services import MENSAGEM_PREVIA_EXCLUSAO_MUDOU
        await enviar_resposta(update, MENSAGEM_PREVIA_EXCLUSAO_MUDOU, comando_executado=comando)
        return

    # Backup obrigatório antes de ação destrutiva (falha fechada). Quando a
    # prévia já diz que o alvo não existe, não há o que proteger.
    if not str(previa_atual or "").startswith("Não encontrei"):
        try:
            from services import criar_backup_pre_exclusao
            await executar_core(criar_backup_pre_exclusao)
        except Exception as exc:
            logging.exception("Backup antes da exclusão falhou; exclusão cancelada.")
            await enviar_resposta(
                update,
                "⚠️ Não consegui gerar o backup de segurança antes de apagar. Nada foi apagado.\n\n"
                f"Motivo: {exc}",
                comando_executado=comando,
            )
            return

    await enviar_acao_digitando(update, context)

    # Fail-safe:
    # O services.py agora bloqueia exclusões diretas por padrão.
    # Somente este prefixo interno libera a execução após confirmação explícita.
    resposta = await executar_core(executar_exclusao_confirmada,comando,sessao=chave_sessao_update(update))
    await enviar_resposta(update, resposta, comando_executado=comando)


async def cancelar_confirmacao_exclusao(update: Update):
    chat_id = obter_chat_id_update(update)
    limpar_pendencia_exclusao(chat_id)

    mensagem = update.callback_query.message if update.callback_query else update.message
    mensagem_enviada = await mensagem.reply_text(
        message_html("Exclusão cancelada.\n\nNada foi apagado."),
        reply_markup=montar_menu_principal(),
        parse_mode="HTML"
    )
    registrar_mensagem_enviada(mensagem_enviada)



def obter_chat_id_update(update: Update):
    if update.effective_chat:
        return update.effective_chat.id
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message.chat_id
    return None


def limpar_pendencia_guiada(chat_id):
    if chat_id in PENDENCIAS_GUIADAS:
        PENDENCIAS_GUIADAS.pop(chat_id, None)


PENDENCIA_GUIADA_TTL = timedelta(minutes=10)


def obter_pendencia_guiada(chat_id):
    pendencia = PENDENCIAS_GUIADAS.get(chat_id)
    if pendencia and _pendencia_expirada(pendencia, PENDENCIA_GUIADA_TTL):
        PENDENCIAS_GUIADAS.pop(chat_id, None)
        return None
    return pendencia


def montar_teclado_cancelar_guiado():
    return InlineKeyboardMarkup([[botao_comando("✖️ Cancelar", "__guiado_cancelar__")]])


def definir_pendencia_guiada(chat_id, tipo: str, dados: dict | None = None):
    PENDENCIAS_GUIADAS[chat_id] = {
        "tipo": tipo,
        "dados": dados or {},
        "criado_em": relogio.agora(),
    }


def extrair_id_lancamento_resposta(texto: str):
    if not texto:
        return None

    match = re.search(r"#(\d+)\b", texto)
    if match:
        return match.group(1)

    return None


def extrair_id_compromisso_resposta(texto: str):
    if not texto:
        return None

    match = re.search(r"#C(\d+)\b", texto, flags=re.IGNORECASE)
    if match:
        return match.group(1)

    match = re.search(r"^#(\d+)\s", texto, flags=re.MULTILINE)
    if match:
        return match.group(1)

    return None


async def iniciar_fluxo_guiado(update: Update, context: ContextTypes.DEFAULT_TYPE, acao: str):
    chat_id = obter_chat_id_update(update)
    if chat_id is None:
        return

    mensagem = update.callback_query.message if update.callback_query else update.message
    texto_base = mensagem.text or "" if mensagem else ""

    partes = acao.split(":")
    tipo = partes[0]
    valor = partes[1] if len(partes) > 1 else ""

    # Apagar com ID conhecido: vai direto à prévia com os botões
    # "Sim, apagar / Não apagar" (antes pedia "confirmar" digitado e depois
    # ainda mostrava a prévia). Sem ID, segue o fluxo guiado antigo.
    if tipo in {"apagar_lancamento", "apagar_fixo"}:
        alvo_id = valor or (extrair_id_lancamento_resposta(texto_base) if tipo == "apagar_lancamento"
                            else extrair_id_compromisso_resposta(texto_base))
        if alvo_id and str(alvo_id).isdigit():
            comando_apagar = f"apagar {alvo_id}" if tipo == "apagar_lancamento" else f"apagar fixo {alvo_id}"
            limpar_pendencia_guiada(chat_id)
            if await bloquear_se_assessor_travado(update, comando_apagar):
                return
            if await solicitar_confirmacao_exclusao(update, comando_apagar):
                return

    # Fluxos de registro
    if tipo == "registrar_despesa":
        definir_pendencia_guiada(chat_id, "registrar_despesa")
        texto = (
            "💸 Registrar despesa\n\n"
            "Envie a despesa em uma frase simples.\n\n"
            "Exemplos:\n"
            "gastei 49,90 de Uber no crédito mercado pago\n"
            "paguei 120 no mercado no pix\n\n"
            "Para sair, envie: cancelar"
        )
    elif tipo == "registrar_entrada":
        definir_pendencia_guiada(chat_id, "registrar_entrada")
        texto = (
            "💰 Registrar entrada\n\n"
            "Envie a entrada recebida.\n\n"
            "Exemplos:\n"
            "recebi 3800 de salário\n"
            "entrada bônus 500 hoje\n\n"
            "Para sair, envie: cancelar"
        )
    elif tipo == "registrar_fixo":
        limpar_pendencia_guiada(chat_id)
        screen = await ux.run_experience('act',ux.session_key(update),("new_fixed_start",))
        await ux.send_screen(update, screen, sys.modules[__name__])
        return
    elif tipo == "registrar_parcela":
        definir_pendencia_guiada(chat_id, "registrar_parcela")
        texto = (
            "💳 Compra parcelada\n\n"
            "Envie a compra com quantidade de parcelas.\n\n"
            "Exemplos:\n"
            "celular em 12x de 250 no cartão nubank\n"
            "notebook de 3000 em 10x no cartão btg\n\n"
            "Para sair, envie: cancelar"
        )

    # Fluxos de correção de lançamento
    elif tipo == "corrigir_valor":
        transacao_id = valor or extrair_id_lancamento_resposta(texto_base)
        if not transacao_id:
            texto = "Não encontrei o ID do lançamento. Use: corrigir 7 para 42,90"
        else:
            definir_pendencia_guiada(chat_id, "corrigir_valor", {"id": transacao_id})
            texto = (
                f"💵 Corrigir valor do lançamento #{transacao_id}\n\n"
                "Envie apenas o novo valor.\n"
                "Exemplo: 42,90\n\n"
                "Para sair, envie: cancelar"
            )
    elif tipo == "corrigir_categoria":
        transacao_id = valor or extrair_id_lancamento_resposta(texto_base)
        if not transacao_id:
            texto = "Não encontrei o ID do lançamento. Use: mudar 7 para Transporte"
        else:
            definir_pendencia_guiada(chat_id, "corrigir_categoria", {"id": transacao_id})
            texto = (
                f"🏷 Corrigir categoria do lançamento #{transacao_id}\n\n"
                "Envie a nova categoria.\n"
                "Exemplo: Transporte\n\n"
                "Para sair, envie: cancelar"
            )
    elif tipo == "corrigir_conta":
        transacao_id = valor or extrair_id_lancamento_resposta(texto_base)
        if not transacao_id:
            texto = "Não encontrei o ID do lançamento. Use: corrigir conta 7 para BTG"
        else:
            definir_pendencia_guiada(chat_id, "corrigir_conta", {"id": transacao_id})
            texto = (
                f"🏦 Corrigir banco/conta do lançamento #{transacao_id}\n\n"
                "Envie a nova conta.\n"
                "Exemplo: BTG\n\n"
                "Para sair, envie: cancelar"
            )
    elif tipo == "apagar_lancamento":
        transacao_id = valor or extrair_id_lancamento_resposta(texto_base)
        if not transacao_id:
            texto = "Não encontrei o ID do lançamento. Use: apagar 7"
        else:
            definir_pendencia_guiada(chat_id, "confirmar_apagar_lancamento", {"id": transacao_id})
            texto = (
                f"🗑 Apagar lançamento #{transacao_id}\n\n"
                "Confirme para apagar.\n\n"
                "Envie: confirmar\n"
                "Ou envie: cancelar"
            )

    # Fluxos de compromisso/fixo
    elif tipo == "alterar_conta_fixo":
        compromisso_id = valor or extrair_id_compromisso_resposta(texto_base)
        if compromisso_id:
            definir_pendencia_guiada(chat_id, "alterar_conta_fixo", {"id": compromisso_id})
            texto = (
                f"🏦 Alterar conta do fixo/compromisso #{compromisso_id}\n\n"
                "Envie a nova conta.\n"
                "Exemplo: BTG\n\n"
                "Para sair, envie: cancelar"
            )
        else:
            definir_pendencia_guiada(chat_id, "alterar_conta_fixo_sem_id")
            texto = (
                "🏦 Alterar conta de fixo/compromisso\n\n"
                "Envie o ID e a nova conta.\n"
                "Exemplo: 46 BTG\n\n"
                "Para sair, envie: cancelar"
            )
    elif tipo == "apagar_fixo":
        compromisso_id = valor or extrair_id_compromisso_resposta(texto_base)
        if compromisso_id:
            definir_pendencia_guiada(chat_id, "confirmar_apagar_fixo", {"id": compromisso_id})
            texto = (
                f"🗑 Apagar fixo/compromisso #{compromisso_id}\n\n"
                "Confirme para apagar.\n\n"
                "Envie: confirmar\n"
                "Ou envie: cancelar"
            )
        else:
            definir_pendencia_guiada(chat_id, "apagar_fixo_sem_id")
            texto = (
                "🗑 Apagar fixo/compromisso\n\n"
                "Envie o ID do fixo que deseja apagar.\n"
                "Exemplo: 46\n\n"
                "Para sair, envie: cancelar"
            )

    else:
        texto = "Não reconheci esse fluxo guiado. Envie /menu."

    # Etapa guiada aguardando texto: um botão para sair sem digitar "cancelar".
    teclado = montar_teclado_cancelar_guiado() if obter_pendencia_guiada(chat_id) else montar_menu_principal()
    mensagem_enviada = await mensagem.reply_text(message_html(texto), reply_markup=teclado, parse_mode="HTML")
    registrar_mensagem_enviada(mensagem_enviada)


def montar_comando_de_pendencia(pendencia: dict, texto_usuario: str):
    tipo = pendencia.get("tipo")
    dados = pendencia.get("dados", {})
    texto = (texto_usuario or "").strip()
    texto_limpo = texto.lower().strip()

    if texto_limpo in ["cancelar", "sair", "voltar"]:
        return "__cancelar_guiado__"

    if tipo == "registrar_despesa":
        return texto

    if tipo == "registrar_entrada":
        if texto_limpo.startswith(("recebi ", "entrada ", "ganhei ")):
            return texto
        return f"recebi {texto}"

    if tipo == "registrar_fixo":
        if texto_limpo.startswith(("novo fixo ", "fixo novo ", "cadastrar fixo ")):
            return texto
        return f"novo fixo {texto}"

    if tipo == "registrar_parcela":
        if texto_limpo.startswith(("comprei ", "compra ", "gastei ")):
            return texto
        return f"comprei {texto}"

    if tipo == "corrigir_valor":
        return f"corrigir {dados.get('id')} para {texto}"

    if tipo == "corrigir_categoria":
        return f"mudar {dados.get('id')} para {texto}"

    if tipo == "corrigir_conta":
        return f"corrigir conta {dados.get('id')} para {texto}"

    if tipo == "confirmar_apagar_lancamento":
        if texto_limpo in ["confirmar", "sim", "s", "apagar", "deletar"]:
            return f"apagar {dados.get('id')}"
        return "__cancelar_guiado__"

    if tipo == "alterar_conta_fixo":
        return f"alterar conta fixo {dados.get('id')} para {texto}"

    if tipo == "alterar_conta_fixo_sem_id":
        match = re.match(r"^#?c?(\d+)\s+(.+)$", texto_limpo)
        if match:
            return f"alterar conta fixo {match.group(1)} para {match.group(2)}"
        return "__erro_guiado__:Envie o ID e a nova conta. Exemplo: 46 BTG"

    if tipo == "confirmar_apagar_fixo":
        if texto_limpo in ["confirmar", "sim", "s", "apagar", "deletar"]:
            return f"apagar fixo {dados.get('id')}"
        return "__cancelar_guiado__"

    if tipo == "apagar_fixo_sem_id":
        match = re.match(r"^#?c?(\d+)$", texto_limpo)
        if match:
            return f"apagar fixo {match.group(1)}"
        return "__erro_guiado__:Envie apenas o ID do fixo. Exemplo: 46"

    return texto


async def executar_texto_alteracao_pendente(update: Update, texto: str):
    """confirmar/cancelar alteracao (digitado ou botão vinculado) direto ao núcleo.

    Se a alteração confirmada era a troca de categoria de um lançamento
    ("mudar N para X", inclusive pelo fluxo guiado), oferece aprender a
    preferência depois de gravar, como antes da prévia existir.
    """
    sessao = chave_sessao_update(update)
    categoria_antes = None
    if re.sub(r"\s+", " ", (texto or "").lower().strip()).startswith("confirmar"):
        try:
            from services import PENDENCIAS_ALTERACAO, _obter_pendencia
            pendente = _obter_pendencia(PENDENCIAS_ALTERACAO, sessao) or {}
            alvo = re.match(r"^\s*mudar\s+(\d+)\s+para\s+", str(pendente.get("comando") or ""), re.I)
            if alvo:
                raw = buscar_transacao_por_id(int(alvo.group(1)))
                categoria_antes = dict(raw) if raw else None
        except Exception:
            logging.warning("Não foi possível ler a alteração pendente.", exc_info=True)
    resposta = await executar_core(processar_mensagem, texto, sessao=sessao)
    await enviar_resposta(update, resposta, comando_executado=texto)
    if categoria_antes:
        raw = buscar_transacao_por_id(int(categoria_antes["id"]))
        await oferecer_aprendizado_categoria(update, categoria_antes, dict(raw) if raw else None)


async def oferecer_aprendizado_categoria(update: Update, antes, depois):
    """Oferece uma regra pessoal apenas depois de uma correção confirmada."""
    if not antes or not depois:
        return
    descricao = str(depois.get("descricao") or antes.get("descricao") or "").strip()
    antiga = str(antes.get("categoria") or "Outros").strip()
    nova = str(depois.get("categoria") or "Outros").strip()
    if not descricao or antiga.casefold() == nova.casefold():
        return
    chat_id = obter_chat_id_update(update)
    token_aprendizado = secrets.token_hex(6)
    PENDENCIAS_APRENDIZADO_CATEGORIA[chat_id] = {
        "id": token_aprendizado,
        "descricao": descricao[:160],
        "categoria": nova[:60],
        "transacao_id": int(depois["id"]),
    }
    markup = InlineKeyboardMarkup([[
        botao_comando_vinculado("✅ Aprender", "__aprender_categoria_sim__", token_aprendizado),
        botao_comando_vinculado("Agora não", "__aprender_categoria_nao__", token_aprendizado),
    ]])
    destino = update.message or (update.callback_query.message if update.callback_query else None)
    if destino:
        enviado = await destino.reply_text(
            message_html(
                f"🧠 Aprender esta preferência?\n\n"
                f"Quando aparecer “{descricao}”, sugerir a categoria {nova}.\n\n"
                "A regra só será criada se você confirmar e poderá ser removida em Meus dados."
            ),
            reply_markup=markup,
            parse_mode="HTML",
        )
        registrar_mensagem_enviada(enviado)



def registrar_callback_comando(comando: str):
    global CALLBACK_SEQUENCIA

    CALLBACK_SEQUENCIA += 1
    # Código aleatório: um número sequencial voltava a 1 após um reinício e
    # botões de mensagens antigas passavam a executar comandos novos.
    chave = f"cmd:{secrets.token_urlsafe(9)}"
    while chave in CALLBACK_COMANDOS:
        chave = f"cmd:{secrets.token_urlsafe(9)}"
    CALLBACK_COMANDOS[chave] = comando

    # Evita crescimento infinito se o bot ficar dias rodando.
    if len(CALLBACK_COMANDOS) > 500:
        chaves_antigas = list(CALLBACK_COMANDOS.keys())[:250]
        for chave_antiga in chaves_antigas:
            CALLBACK_COMANDOS.pop(chave_antiga, None)

    persistir_callback_comandos()

    return chave


# Botão que executa um comando de texto direto no assessor (sem passar pelo
# formulário do menu). Ex.: "confirmar pagamento", "cancelar exclusao".
PREFIXO_BOTAO_TEXTO = "__legado__:"
_RE_BOTAO_TEXTO = re.compile(r"^__legado__(?:\[(fatura|exclusao|importacao|alteracao):([0-9a-f]{12})\])?:(.+)$", re.S)


def botao_texto(texto: str, comando: str, estilo: str | None = None, vinculo: tuple | None = None):
    """vinculo=(tipo, assinatura): o botão só vale para aquela prévia."""
    prefixo = PREFIXO_BOTAO_TEXTO
    if vinculo and vinculo[1]:
        prefixo = f"__legado__[{vinculo[0]}:{vinculo[1]}]:"
    return botao_comando(texto, prefixo + comando, estilo)


def _assinatura(tipo: str, sessao):
    if sessao is None:
        return None
    try:
        from services import assinatura_pendencia
        return assinatura_pendencia(tipo, sessao)
    except Exception:
        logging.warning("Assinatura da prévia indisponível.", exc_info=True)
        return None


def _ultimo_dia_mes(ano: int, mes: int) -> date:
    return (date(ano + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1))


def comando_exportacao_periodo(periodo: str, hoje: date | None = None):
    """'exportar csv AAAA-MM-DD AAAA-MM-DD' para um período relativo a hoje."""
    hoje = hoje or relogio.hoje()
    inicio_mes = hoje.replace(day=1)
    if periodo == "mes_atual":
        inicio, fim = inicio_mes, _ultimo_dia_mes(hoje.year, hoje.month)
    elif periodo == "mes_passado":
        fim = inicio_mes - timedelta(days=1)
        inicio = fim.replace(day=1)
    elif periodo == "ano_atual":
        inicio, fim = date(hoje.year, 1, 1), date(hoje.year, 12, 31)
    else:
        return None
    return f"exportar csv {inicio.isoformat()} {fim.isoformat()}"


def montar_teclado_confirmacoes_texto(comando: str, resposta: str, sessao=None):
    """Botões para as respostas que hoje pedem uma frase digitada.

    O texto da resposta continua igual (digitar segue funcionando); os botões
    enviam exatamente a mesma frase. Verde confirma, vermelho desiste; em
    exclusões o vermelho é o "apagar" e a desistência fica neutra.
    """
    texto = resposta or ""

    m = re.search(r"(?m)^Responda: confirmar (pagamento|estorno|credito)$", texto)
    if m:
        rotulo = m.group(1)
        nome = {"pagamento": "pagamento", "estorno": "estorno", "credito": "crédito"}[rotulo]
        vinculo = ("fatura", _assinatura("fatura", sessao))
        return InlineKeyboardMarkup([[
            botao_texto(f"✅ Confirmar {nome}", f"confirmar {rotulo}", "success", vinculo),
            botao_texto("✖️ Cancelar", f"cancelar {rotulo}", "danger", vinculo),
        ]])

    if re.search(r"(?m)^Responda: confirmar exclusao$", texto):
        vinculo = ("exclusao", _assinatura("exclusao", sessao))
        return InlineKeyboardMarkup([[
            botao_texto("🗑 Sim, apagar", "confirmar exclusao", "danger", vinculo),
            botao_texto("✖️ Não apagar", "cancelar exclusao", None, vinculo),
        ]])

    if re.search(r"(?m)^Responda: confirmar alteracao$", texto):
        vinculo = ("alteracao", _assinatura("alteracao", sessao))
        return InlineKeyboardMarkup([[
            botao_texto("✅ Confirmar alteração", "confirmar alteracao", "success", vinculo),
            botao_texto("✖️ Não alterar", "cancelar alteracao", "danger", vinculo),
        ]])

    if re.search(r"(?m)^Para gravar no banco, envie:\nconfirmar importacao$", texto):
        vinculo = ("importacao", _assinatura("importacao", sessao))
        return InlineKeyboardMarkup([[
            botao_texto("✅ Importar", "confirmar importacao", "success", vinculo),
            botao_texto("✖️ Descartar", "cancelar importacao", "danger", vinculo),
        ]])

    if texto.startswith("📤 Exportação CSV") and (
        "Informe o período que deseja exportar" in texto or "Não entendi o período" in texto
    ):
        # As datas são calculadas no toque (um botão antigo, perto da virada
        # do mês, ainda exporta o mês certo).
        return InlineKeyboardMarkup([
            [
                botao_comando("📅 Este mês", "__exportar_periodo__:mes_atual"),
                botao_comando("📅 Mês passado", "__exportar_periodo__:mes_passado"),
            ],
            [
                botao_comando("📅 Este ano", "__exportar_periodo__:ano_atual"),
                botao_texto("📦 Tudo", "exportar csv tudo"),
            ],
            [botao_texto("✖️ Cancelar", "cancelar exportacao")],
        ])

    if texto.startswith("🏦 Saldo inicial definido"):
        m = re.search(r"(?m)^(saldo inicial (\d{4}-\d{2}) .+ herdado)$", texto)
        if m:
            return InlineKeyboardMarkup([[
                botao_comando("↩️ Voltar a herdar", "__perguntar_herdar__:" + m.group(1), "danger"),
                botao_comando("🏦 Ver caixa", f"caixa {m.group(2)}", "primary"),
            ]])

    if texto.startswith(("🤔 Não entendi", "🤔 Não encontrei um valor")):
        # Texto não reconhecido: nunca grava; oferece os dois caminhos seguros.
        return InlineKeyboardMarkup([[
            botao_comando("➕ Registrar", "registrar", "primary"),
            botao_comando("☰ Menu", "menu"),
        ]])

    if texto.startswith("💳 Fatura com saldo restante") or texto.startswith("💳 Movimento de fatura não reconhecido"):
        return InlineKeyboardMarkup([[botao_comando("🧾 Abrir A pagar", "a pagar", "primary")]])

    if comando == "/seguranca" and "envie: cancelar" in texto:
        return montar_teclado_cancelar_reset_pin()

    return None


def botao_comando(texto: str, comando: str, estilo: str | None = None):
    from telegram_design import button_label, button_style
    token = registrar_callback_comando(comando)
    texto = button_label(texto, ('legacy', comando))
    style = estilo or button_style(texto, ('legacy', comando))
    try:
        return InlineKeyboardButton(texto, callback_data=token, style=style)
    except TypeError:
        return InlineKeyboardButton(texto, callback_data=token)


def extrair_ano_mes_da_resposta(texto: str):
    match = re.search(r"\b(20\d{2}-\d{2})\b", texto or "")
    if match:
        return match.group(1)
    return None


def extrair_ano_mes_do_comando(comando: str | None):
    match = re.search(r"\b(20\d{2}-\d{2})\b", comando or "")
    if match:
        return match.group(1)
    return None


def somar_meses_app(ano_mes: str, deslocamento: int):
    ano, mes = [int(parte) for parte in ano_mes.split("-")]
    total = ano * 12 + (mes - 1) + deslocamento
    novo_ano = total // 12
    novo_mes = total % 12 + 1
    return f"{novo_ano:04d}-{novo_mes:02d}"


def obter_mes_base(comando: str | None, texto_resposta: str | None):
    return (
        extrair_ano_mes_do_comando(comando)
        or extrair_ano_mes_da_resposta(texto_resposta)
        or relogio.hoje().strftime("%Y-%m")
    )


def botoes_navegacao_mes(mes_base: str, prefixo_comando: str):
    mes_anterior = somar_meses_app(mes_base, -1)
    proximo_mes = somar_meses_app(mes_base, 1)

    return [
        botao_comando(f"◀️ {formatar_ano_mes_exibicao(mes_anterior, curto=True)}", f"{prefixo_comando} {mes_anterior}"),
        botao_comando(f"{formatar_ano_mes_exibicao(proximo_mes, curto=True)} ▶️", f"{prefixo_comando} {proximo_mes}"),
    ]


def botoes_meses_rapidos(prefixo_comando: str, quantidade: int = 4):
    hoje_mes = relogio.hoje().strftime("%Y-%m")
    botoes = []

    for indice in range(quantidade):
        mes = somar_meses_app(hoje_mes, indice)
        botoes.append(botao_comando(formatar_ano_mes_exibicao(mes, curto=True), f"{prefixo_comando} {mes}"))

    linhas = []
    linha = []

    for botao in botoes:
        linha.append(botao)
        if len(linha) == 2:
            linhas.append(linha)
            linha = []

    if linha:
        linhas.append(linha)

    return linhas


def extrair_categorias_da_resposta(texto: str):
    categorias = []

    for linha in (texto or "").splitlines():
        linha = linha.strip()

        # Layout antigo:
        # - Assinaturas: R$ 143,15
        match_antigo = re.match(r"^-\s+(.+?):\s+R\$", linha)
        if match_antigo:
            categoria = match_antigo.group(1).strip()
            if categoria and categoria not in categorias:
                categorias.append(categoria)
            continue

        # Layout visual novo:
        # 01. Assinaturas
        # 02. Moradia
        match_ranking = re.match(r"^\d{1,2}\.\s+(.+?)\s*$", linha)
        if match_ranking:
            categoria = match_ranking.group(1).strip()

            # Evita capturar linhas que não são categorias.
            bloqueadas = {
                "receitas",
                "saídas",
                "saidas",
                "visão geral",
                "visao geral",
                "ranking de categorias",
                "ranking de formas",
            }

            if categoria and categoria.lower() not in bloqueadas and categoria not in categorias:
                categorias.append(categoria)

    # Telegram permite mais botões, mas muitos botões deixam o teclado poluído.
    # 12 categorias = até 6 linhas de 2 botões, ainda fica usável.
    return categorias[:12]


def extrair_conta_de_comando_detalhar_quanto_vou_pagar(comando: str | None):
    comando = (comando or "").strip()

    match = re.match(
        r"^detalhar\s+quanto\s+vou\s+pagar\s+no\s+(.+?)\s+em\s+(20\d{2}-\d{2})$",
        comando,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    conta = match.group(1).strip()
    mes = match.group(2)
    if not conta:
        return None

    return conta, mes


def extrair_categoria_de_comando_detalhar(comando: str | None):
    comando = (comando or "").strip()

    # O detalhamento de "quanto vou pagar" possui navegacao propria por conta.
    # Sem esta protecao, o comando inteiro era interpretado como uma categoria.
    if extrair_conta_de_comando_detalhar_quanto_vou_pagar(comando):
        return None

    match = re.match(
        r"^detalhar\s+(?:categoria\s+)?(.+?)\s+20\d{2}-\d{2}$",
        comando,
        flags=re.IGNORECASE
    )
    if match:
        categoria = match.group(1).strip()
        if categoria.lower() not in ["mes", "mês", "tudo"]:
            return categoria

    return None




def extrair_primeiro_id(texto: str, prefixos: str = ""):
    if prefixos:
        padrao = rf"#([{prefixos}]?\d+)"
    else:
        padrao = r"#([A-Za-z]?\d+)"

    match = re.search(padrao, texto or "", flags=re.IGNORECASE)
    if not match:
        return None

    return match.group(1)


def extrair_ids_lista_visual_transacoes(texto: str, limite: int = 10):
    if not texto:
        return []

    ids = []
    linhas = (texto or "").splitlines()
    visual_atual = None

    # Parser simples, sem regex multiline complexa:
    # 1) 💸 Gasolina
    #    ...
    #    ID técnico: #9 · saída
    for linha in linhas:
        linha_limpa = linha.strip()

        match_visual = re.match(r"^(\d+)\)", linha_limpa)
        if match_visual:
            visual_atual = match_visual.group(1)
            continue

        match_id = re.search(r"ID técnico:\s*#(\d+)\b", linha_limpa)
        if match_id and visual_atual:
            ids.append((visual_atual, match_id.group(1)))
            visual_atual = None

            if len(ids) >= limite:
                break

    # Fallback: se o texto vier no formato antigo, pega #ids em ordem.
    if not ids:
        encontrados = re.findall(r"#(\d+)\b", texto)
        vistos = set()

        for transacao_id in encontrados:
            if transacao_id in vistos:
                continue

            vistos.add(transacao_id)
            ids.append((str(len(ids) + 1), transacao_id))

            if len(ids) >= limite:
                break

    return ids


def extrair_pagina_lista_visual(texto: str):
    match = re.search(r"Página\s+(\d+)\s+de\s+(\d+)", texto or "", flags=re.IGNORECASE)
    if not match:
        return None, None

    return int(match.group(1)), int(match.group(2))


def normalizar_comando_base_lista(comando: str | None):
    texto = (comando or "").lower().strip()

    if not texto:
        return "ultimas"

    # Remove sufixo de paginação.
    texto = re.sub(r"\s+pagina\s+\d+\s*$", "", texto).strip()

    aliases_inicio = ["listarultimos", "listar ultimos", "listar últimos", "ultimos", "últimos", "ultimas", "últimas"]

    if any(texto == alias for alias in aliases_inicio):
        return "ultimas"

    if any(texto.startswith(alias + " ") for alias in aliases_inicio):
        # Preserva filtro: "ultimas credito" -> "ultimas credito"
        for alias in aliases_inicio:
            if texto.startswith(alias + " "):
                filtro = texto[len(alias):].strip()
                return f"ultimas {filtro}" if filtro else "ultimas"

    if texto.startswith("buscar "):
        return texto

    return "ultimas"


def montar_botoes_paginacao_lista(comando: str | None, texto_resposta: str):
    pagina_atual, total_paginas = extrair_pagina_lista_visual(texto_resposta)

    if not pagina_atual or not total_paginas or total_paginas <= 1:
        return []

    base = normalizar_comando_base_lista(comando)
    botoes = []

    if pagina_atual > 1:
        botoes.append(botao_texto("◀️ Anterior", f"{base} pagina {pagina_atual - 1}"))

    if pagina_atual < total_paginas:
        botoes.append(botao_texto("Próxima ▶️", f"{base} pagina {pagina_atual + 1}"))

    return [botoes] if botoes else []


def comando_sem_pagina_final(comando: str | None):
    return re.sub(r"\s+pagina\s+\d+\s*$", "", comando or "", flags=re.IGNORECASE).strip()


def montar_botoes_paginacao_conta(comando: str | None, texto_resposta: str):
    pagina_atual, total_paginas = extrair_pagina_lista_visual(texto_resposta)

    if not pagina_atual or not total_paginas or total_paginas <= 1:
        return []

    base = comando_sem_pagina_final(comando)
    if not base:
        return []

    botoes = []

    if pagina_atual > 1:
        botoes.append(botao_texto("◀️ Anterior", f"{base} pagina {pagina_atual - 1}"))

    if pagina_atual < total_paginas:
        botoes.append(botao_texto("Próxima ▶️", f"{base} pagina {pagina_atual + 1}"))

    return [botoes] if botoes else []


def resposta_eh_lista_conta_paginavel(resposta: str):
    texto = resposta or ""

    if texto.startswith("💸 Despesas —"):
        return True

    if texto.startswith("📒 Movimentações —"):
        return True

    if texto.startswith("📒 Lançamentos —"):
        return True

    if texto.startswith("🟢 Receitas —"):
        return True

    return False



def montar_teclado_acao_produtiva(comando: str, texto_resposta: str, mes_base: str):
    resposta = texto_resposta or ""

    if resposta.startswith("🎓 Aprender") or resposta.startswith("🎓 Aula:"):
        return InlineKeyboardMarkup([
            [botao_comando("🚀 Primeiros passos", "aprender primeiros passos"), botao_comando("💸 Lançamentos", "aprender lançamentos")],
            [botao_comando("💳 Faturas", "aprender faturas"), botao_comando("🏦 Caixa", "aprender caixa")],
            [botao_comando("🧾 Fixos/previsões", "aprender previsões"), botao_comando("🔁 Transferências", "aprender transferências")],
            [botao_comando("✅ Checklist", "aprender checklist"), botao_comando("🔗 Conciliação", "aprender conciliação")],
            [botao_comando("🎯 Planejamento", "aprender planejamento"), botao_comando("🧪 Auditoria", "aprender auditoria")],
            [botao_comando("🔐 Dados/backup", "aprender dados"), botao_comando("🗓 Rotina", "aprender rotina")],
            [botao_comando("📚 Aula completa", "aprender tudo")],
        ])

    if resposta.startswith("❓ Ajuda rápida") or resposta.startswith("🏦 /help saldo") or resposta.startswith("🥗 /help caju") or resposta.startswith("🏦 /help caixa") or resposta.startswith("💳 /help pagar"):
        return InlineKeyboardMarkup([
            [
                botao_comando("💸 Lançar", "/help lancamentos"),
                botao_comando("🥗 Caju/VR", "/help caju"),
            ],
            [
                botao_comando("🏦 Caixa", "/help caixa"),
                botao_comando("💳 A pagar", "/help pagar"),
            ],
            [
                botao_comando("✅ Checklist", "/help checklist"),
                botao_comando("✏️ Corrigir", "/help corrigir"),
            ],
            [
                botao_comando("📊 Saldo/mês", "/help saldo"),
                botao_comando("🔎 Consultas", "/help consultas"),
            ],
        ])

    if resposta.startswith("🏦 Saldo do mês"):
        return InlineKeyboardMarkup([
            [
                botao_comando("📊 Meu mês", f"meu mês {mes_base}"),
                botao_comando("📈 Dashboard", f"dashboard {mes_base}"),
            ],
            [
                botao_comando("🏦 Contas", f"contas {mes_base}"),
                botao_comando("💳 Compromissos", f"compromissos {mes_base}"),
            ],
            [
                botao_comando("📌 Últimos", "listarultimos"),
                botao_comando("➕ Lançar", "registrar"),
            ],
            [
                botao_comando("❓ Ajuda", "__help__"),
            ],
        ])

    if resposta_eh_lista_conta_paginavel(resposta):
        linhas = []
        linhas.extend(montar_botoes_paginacao_conta(comando, resposta))

        linhas.append([
            botao_comando("📊 Saldo geral", f"saldo geral {mes_base}"),
            botao_comando("🏦 Contas", f"contas {mes_base}"),
        ])

        linhas.append([
            botao_comando("💳 Compromissos", f"compromissos {mes_base}"),
            botao_comando("📌 Últimos", "listarultimos"),
        ])

        return InlineKeyboardMarkup(linhas)

    if resposta.startswith("📌 Últimas") or resposta.startswith("🔎 Busca:"):
        ids = extrair_ids_lista_visual_transacoes(resposta, limite=5)
        linhas = []
        linha = []

        for visual, transacao_id in ids:
            linha.append(botao_comando(visual, f"lançamento {transacao_id}"))

            if len(linha) == 5:
                linhas.append(linha)
                linha = []

        if linha:
            linhas.append(linha)

        linhas.extend(montar_botoes_paginacao_lista(comando, resposta))

        linhas.append([
            botao_comando("🔎 Buscar", "buscar"),
            botao_comando("📅 Hoje", "ultimas hoje"),
        ])

        linhas.append([
            botao_comando("💳 Crédito", "ultimas credito"),
            botao_comando("📊 Meu mês", "meu mês"),
        ])

        return InlineKeyboardMarkup(linhas)

    if resposta.startswith("🔎 Lançamento"):
        transacao_id = extrair_id_lancamento_resposta(resposta) or ""
        return InlineKeyboardMarkup([
            [
                botao_guiado("💵 Valor", f"corrigir_valor:{transacao_id}"),
                botao_guiado("🏷 Categoria", f"corrigir_categoria:{transacao_id}"),
            ],
            [
                botao_guiado("🏦 Banco/conta", f"corrigir_conta:{transacao_id}"),
                botao_guiado("🗑 Apagar", f"apagar_lancamento:{transacao_id}"),
            ],
            [
                botao_comando("📌 Voltar às últimas", "últimas 10"),
                botao_comando("📊 Meu mês", f"meu mês {mes_base}"),
            ],
            [
                botao_comando("📆 Hoje", "hoje"),
            ],
        ])

    if resposta.startswith("✅ Despesa registrada") or resposta.startswith("✅ Receita registrada"):
        transacao_id = extrair_id_lancamento_resposta(resposta) or ""
        return InlineKeyboardMarkup([
            [
                botao_guiado("💵 Valor", f"corrigir_valor:{transacao_id}"),
                botao_guiado("🏷 Categoria", f"corrigir_categoria:{transacao_id}"),
            ],
            [
                botao_guiado("🏦 Banco/conta", f"corrigir_conta:{transacao_id}"),
                botao_guiado("🗑 Apagar", f"apagar_lancamento:{transacao_id}"),
            ],
            [
                botao_comando("📌 Últimas", "últimas 10"),
                botao_comando("📊 Meu mês", f"meu mês {mes_base}"),
            ],
            [
                botao_comando("📆 Hoje", "hoje"),
            ],
        ])

    if resposta.startswith("🏦 Conta atualizada"):
        transacao_id = extrair_id_lancamento_resposta(resposta) or ""
        return InlineKeyboardMarkup([
            [
                botao_guiado("💵 Valor", f"corrigir_valor:{transacao_id}"),
                botao_guiado("🏷 Categoria", f"corrigir_categoria:{transacao_id}"),
            ],
            [
                botao_guiado("🏦 Banco/conta", f"corrigir_conta:{transacao_id}"),
                botao_guiado("🗑 Apagar", f"apagar_lancamento:{transacao_id}"),
            ],
            [
                botao_comando("📌 Últimas", "últimas 10"),
                botao_comando("📊 Meu mês", f"meu mês {mes_base}"),
            ],
        ])

    if resposta.startswith("💳 Compra parcelada registrada"):
        parcelamento_id = extrair_primeiro_id(resposta, "P")
        comando_parcelas = f"parcelas {parcelamento_id}" if parcelamento_id else "parcelamentos"

        return InlineKeyboardMarkup([
            [
                botao_comando("💳 Ver parcelas", comando_parcelas),
                botao_comando("📆 Agenda geral", "agenda"),
            ],
            [
                botao_comando("📊 Meu mês", f"meu mês {mes_base}"),
                botao_comando("🏷 Categorias", f"categorias {mes_base}"),
            ],
        ])

    if (
        resposta.startswith("🔁 Fixo cadastrado")
        or resposta.startswith("🔁 Fixo atualizado")
        or resposta.startswith("📅 Vencimento do fixo")
        or resposta.startswith("🏦 Conta do compromisso atualizada")
        or resposta.startswith("💳 Forma de pagamento atualizada")
        or resposta.startswith("🏷 Categoria do compromisso atualizada")
    ):
        return InlineKeyboardMarkup([
            [
                botao_comando("🧾 Ver fixos", "fixos"),
                botao_comando("💳 Compromissos", "compromissos"),
            ],
            [
                botao_guiado("🏦 Alterar conta", "alterar_conta_fixo"),
                botao_guiado("🗑 Apagar fixo", "apagar_fixo"),
            ],
            [
                botao_comando("📊 Meu mês", f"meu mês {mes_base}"),
                botao_comando("🏦 Contas", f"contas {mes_base}"),
            ],
        ])

    if resposta.startswith("💰 Entrada fixa cadastrada") or resposta.startswith("💰 Entrada futura cadastrada") or resposta.startswith("💰 Entrada atualizada"):
        return InlineKeyboardMarkup([
            [
                botao_comando("💰 Ver entradas", f"entradas {mes_base}"),
                botao_comando("📆 Agenda geral", "agenda"),
            ],
            [
                botao_comando("📊 Meu mês", f"meu mês {mes_base}"),
                botao_comando("🧠 Diagnóstico", "assessor"),
            ],
        ])

    if resposta.startswith("🗑️") or resposta.startswith("✏️") or resposta.startswith("💵 Valor atualizado"):
        return InlineKeyboardMarkup([
            [
                botao_comando("📌 Últimas", "últimas 10"),
                botao_comando("📊 Meu mês", f"meu mês {mes_base}"),
            ],
            [
                botao_comando("📋 Detalhar mês", f"detalhar {mes_base}"),
                botao_comando("🏷 Categorias", f"categorias {mes_base}"),
            ],
        ])

    if resposta.startswith("📤 Exportação gerada") or resposta.startswith("💾 Backup gerado"):
        return InlineKeyboardMarkup([
            [
                botao_comando("📊 Meu mês", f"meu mês {mes_base}"),
                botao_comando("📆 Agenda geral", "agenda"),
            ],
            [
                botao_comando("🧹 Limpar conversa", "/limpar"),
            ],
        ])

    if resposta.startswith("🔓 Assessor desbloqueado"):
        return InlineKeyboardMarkup([
            [
                botao_comando("🧠 Diagnóstico", "assessor"),
                botao_comando("📆 Agenda geral", "agenda"),
            ],
            [
                botao_comando("📊 Meu mês", f"meu mês {mes_base}"),
                botao_comando("🏷 Categorias", f"categorias {mes_base}"),
            ],
        ])

    return None


def montar_teclado_inline_para_resposta(comando_executado: str | None, resposta, sessao=None):
    if not isinstance(resposta, str):
        return None

    comando = (comando_executado or "").lower().strip()
    texto_resposta = resposta or ""
    mes_base = obter_mes_base(comando, texto_resposta)
    categoria_filtrada = extrair_categoria_de_comando_detalhar(comando_executado)

    teclado_confirmacao = montar_teclado_confirmacoes_texto(comando, texto_resposta, sessao)
    if teclado_confirmacao:
        return teclado_confirmacao

    teclado_acao = montar_teclado_acao_produtiva(comando, texto_resposta, mes_base)
    if teclado_acao:
        return teclado_acao

    if comando in ["__help__", "menu", "central"] or comando.startswith("/help"):
        if comando == "__help__" or comando.startswith("/help"):
            return InlineKeyboardMarkup([
                [
                    botao_comando("🏦 Saldo/contas", "/help saldo"),
                    botao_comando("✅ Checklist", "/help checklist"),
                ],
                [
                    botao_comando("🔎 Consultas", "/help consultas"),
                    botao_comando("🟢 Lançar", "/help lancamentos"),
                ],
                [
                    botao_comando("🧾 Fixos", "/help fixos"),
                    botao_comando("💳 Parcelas", "/help parcelas"),
                ],
                [
                    botao_comando("✏️ Corrigir", "/help corrigir"),
                    botao_comando("📤 Exportar", "/help exportar"),
                ],
                [
                    botao_comando("🔐 Segurança", "/help seguranca"),
                    botao_comando("🏠 Central", "menu"),
                ],
            ])

        return InlineKeyboardMarkup([
            [
                botao_comando("➕ Lançar", "registrar"),
                botao_comando("📆 Hoje", "hoje"),
            ],
            [
                botao_comando("📊 Meu mês", "meu mês"),
                botao_comando("📈 Dashboard", "dashboard"),
            ],
            [
                botao_comando("🏷 Categorias", "dashboard categorias"),
                botao_comando("🧠 Diagnóstico", "assessor"),
            ],
            [
                botao_comando("🔎 Revisar", "revisar"),
                botao_comando("💳 Compromissos", "compromissos"),
            ],
            [
                botao_comando("✅ Checklist", "checklist"),
                botao_comando("🏦 Saldo", "saldo do mês"),
            ],
            [
                botao_comando("📌 Últimos", "listarultimos"),
                botao_comando("📤 Exportar", "exportar csv"),
            ],
            [
                botao_comando("⚙️ Ajustes", "ajustes"),
                botao_comando("❓ Ajuda", "__help__"),
            ],
        ])

    if comando.startswith("registrar"):
        return InlineKeyboardMarkup([
            [
                botao_guiado("💸 Despesa", "registrar_despesa"),
                botao_guiado("💰 Entrada", "registrar_entrada"),
            ],
            [
                botao_guiado("🧾 Fixo mensal", "registrar_fixo"),
                botao_guiado("💳 Compra parcelada", "registrar_parcela"),
            ],
            [
                botao_comando("📊 Meu mês", "meu mês"),
                botao_comando("🔎 Revisar", "revisar"),
            ],
        ])

    if comando.startswith("hoje"):
        return InlineKeyboardMarkup([
            [
                botao_comando("📌 Gastos de hoje", "gastos de hoje"),
                botao_comando("➕ Registrar", "registrar"),
            ],
            [
                botao_comando("📊 Meu mês", "meu mês"),
                botao_comando("🔎 Revisar", "revisar"),
            ],
        ])

    if comando in ["meu mês", "meu mes", "painel do mês", "painel do mes"] or comando.startswith("meu mês ") or comando.startswith("meu mes "):
        return InlineKeyboardMarkup([
            botoes_navegacao_mes(mes_base, "meu mês"),
            [
                botao_comando("🔎 Ver detalhes", f"detalhes meu mês {mes_base}"),
                botao_comando("🏷 Categorias", f"categorias {mes_base}"),
            ],
            [
                botao_comando("💳 Compromissos", "compromissos"),
                botao_comando("🧠 Diagnóstico", "assessor"),
            ],
        ])

    if comando.startswith("detalhes meu mês") or comando.startswith("detalhes meu mes"):
        return InlineKeyboardMarkup([
            botoes_navegacao_mes(mes_base, "detalhes meu mês"),
            [
                botao_comando("📊 Resumo curto", f"meu mês {mes_base}"),
                botao_comando("🏷 Categorias", f"categorias {mes_base}"),
            ],
            [
                botao_comando("💳 Compromissos", "compromissos"),
                botao_comando("🧠 Diagnóstico", "assessor"),
            ],
        ])

    if comando.startswith("checklist"):
        return InlineKeyboardMarkup([
            [
                botao_comando("⏳ Pendentes", f"checklist pendentes {mes_base}"),
                botao_comando("✅ Pagos", f"checklist pagos {mes_base}"),
            ],
            [
                botao_comando("🧾 Fixos", f"checklist fixos {mes_base}"),
                botao_comando("💳 Bancos/parcelas", f"checklist bancos {mes_base}"),
            ],
            [
                botao_comando("💳 Compromissos", f"compromissos {mes_base}"),
                botao_comando("🏠 Central", "menu"),
            ],
        ])

    if comando.startswith("compromissos"):
        return InlineKeyboardMarkup([
            [
                botao_comando("✅ Checklist", f"checklist {mes_base}"),
                botao_comando("🧾 Fixos", "fixos"),
            ],
            [
                botao_comando("💳 Parcelas", "parcelamentos"),
                botao_comando("💰 Entradas", "entradas"),
            ],
            [
                botao_guiado("🏦 Alterar conta", "alterar_conta_fixo"),
            ],
            [
                botao_comando("📆 Agenda geral", "agenda"),
                botao_comando("📊 Meu mês", "meu mês"),
            ],
        ])

    if comando.startswith("revisar") or comando.startswith("revisao") or comando.startswith("revisão"):
        return InlineKeyboardMarkup([
            [
                botao_comando("📊 Meu mês", "meu mês"),
                botao_comando("📋 Detalhar", f"detalhar {mes_base}"),
            ],
            [
                botao_comando("🏷 Categorias", f"categorias {mes_base}"),
                botao_comando("💳 Compromissos", "compromissos"),
            ],
        ])

    if comando.startswith("ajustes"):
        return InlineKeyboardMarkup([
            [
                botao_comando("🔐 Segurança", "/seguranca"),
                botao_comando("📤 Exportar", "exportar csv"),
            ],
            [
                botao_comando("💾 Backup", "backup"),
                botao_comando("📘 Ajuda", "__help__"),
            ],
        ])

    if comando == "agenda" or comando == "agenda financeira":
        linhas = []
        linhas.extend(botoes_meses_rapidos("detalhar", 4))
        linhas.extend([
            [
                botao_comando("🏷 Categorias mês atual", f"categorias {mes_base}"),
                botao_comando("💰 Contas mês atual", f"contas {mes_base}"),
            ],
            [
                botao_comando("💳 Parcelas mês atual", f"parcelas {mes_base}"),
                botao_comando("💰 Entradas mês atual", f"entradas {mes_base}"),
            ],
            [
                botao_comando("🧠 Diagnóstico", "assessor"),
            ],
        ])
        return InlineKeyboardMarkup(linhas)

    if comando.startswith("agenda "):
        linhas = [
            botoes_navegacao_mes(mes_base, "agenda"),
            [
                botao_comando("📋 Detalhar mês", f"detalhar {mes_base}"),
                botao_comando("🏷 Categorias", f"categorias {mes_base}"),
            ],
            [
                botao_comando("💳 Parcelas", f"parcelas {mes_base}"),
                botao_comando("💰 Contas", f"contas {mes_base}"),
            ],
            [
                botao_comando("🧠 Diagnóstico", "assessor"),
            ],
        ]
        return InlineKeyboardMarkup(linhas)

    if comando.startswith("categorias") or comando.startswith("categoria "):
        categorias = extrair_categorias_da_resposta(texto_resposta)

        linhas = [
            botoes_navegacao_mes(mes_base, "categorias")
        ]

        linha_atual = []
        for categoria in categorias:
            linha_atual.append(botao_comando(categoria[:24], f"detalhar categoria {categoria} {mes_base}"))
            if len(linha_atual) == 2:
                linhas.append(linha_atual)
                linha_atual = []

        if linha_atual:
            linhas.append(linha_atual)

        linhas.extend([
            [
                botao_comando("📋 Detalhar mês", f"detalhar {mes_base}"),
                botao_comando("📆 Agenda geral", "agenda"),
            ],
            [
                botao_comando("💰 Contas", f"contas {mes_base}"),
                botao_comando("💳 Parcelas", f"parcelas {mes_base}"),
            ],
        ])

        return InlineKeyboardMarkup(linhas)

    if comando.startswith("quanto vou pagar"):
        match_conta = re.match(
            r"^quanto vou pagar no\s+(.+?)(?:\s+em\s+(\d{4}-\d{2}))?$",
            comando,
        )
        if match_conta and not re.match(r"^m[eê]s(?:\s+de\s+.+)?$", match_conta.group(1).strip()):
            conta = match_conta.group(1).strip()
            mes_conta = match_conta.group(2) or mes_base
            return InlineKeyboardMarkup([
                [
                    botao_comando(
                        "🔎 Ver detalhes",
                        f"detalhar quanto vou pagar no {conta} em {mes_conta}",
                    ),
                    botao_comando("🏦 Ver contas", f"contas {mes_conta}"),
                ],
                [
                    botao_comando("📊 Meu mês", f"meu mês {mes_conta}"),
                    botao_comando("💳 Compromissos", f"compromissos {mes_conta}"),
                ],
            ])

        return InlineKeyboardMarkup([
            [
                botao_comando("📋 Detalhar mês", f"detalhar {mes_base}"),
                botao_comando("🏦 Ver contas", f"contas {mes_base}"),
            ],
            [
                botao_comando("📊 Meu mês", f"meu mês {mes_base}"),
                botao_comando("💳 Compromissos", f"compromissos {mes_base}"),
            ],
        ])

    if comando.startswith("detalhar quanto vou pagar no"):
        conta_mes = extrair_conta_de_comando_detalhar_quanto_vou_pagar(comando_executado)
        if conta_mes:
            conta, mes_conta = conta_mes
            mes_anterior = somar_meses_app(mes_conta, -1)
            proximo_mes = somar_meses_app(mes_conta, 1)

            return InlineKeyboardMarkup([
                [
                    botao_comando(
                        f"◀️ {formatar_ano_mes_exibicao(mes_anterior, curto=True)}",
                        f"detalhar quanto vou pagar no {conta} em {mes_anterior}",
                    ),
                    botao_comando(
                        f"{formatar_ano_mes_exibicao(proximo_mes, curto=True)} ▶️",
                        f"detalhar quanto vou pagar no {conta} em {proximo_mes}",
                    ),
                ],
                [
                    botao_comando("🏷 Ver categorias do mês", f"categorias {mes_conta}"),
                    botao_comando("📋 Ver mês completo", f"detalhar {mes_conta}"),
                ],
                [
                    botao_comando("📆 Agenda geral", "agenda"),
                    botao_comando("🧠 Diagnóstico", "assessor"),
                ],
            ])

    if comando.startswith("detalhar"):
        if categoria_filtrada:
            mes_anterior = somar_meses_app(mes_base, -1)
            proximo_mes = somar_meses_app(mes_base, 1)

            linhas = [
                [
                    botao_comando(
                        f"◀️ {formatar_ano_mes_exibicao(mes_anterior, curto=True)}",
                        f"detalhar categoria {categoria_filtrada} {mes_anterior}"
                    ),
                    botao_comando(
                        f"{formatar_ano_mes_exibicao(proximo_mes, curto=True)} ▶️",
                        f"detalhar categoria {categoria_filtrada} {proximo_mes}"
                    ),
                ],
                [
                    botao_comando("🏷 Ver categorias do mês", f"categorias {mes_base}"),
                    botao_comando("📋 Ver mês completo", f"detalhar {mes_base}"),
                ],
                [
                    botao_comando("📆 Agenda geral", "agenda"),
                    botao_comando("🧠 Diagnóstico", "assessor"),
                ],
            ]
            return InlineKeyboardMarkup(linhas)

        linhas = [
            botoes_navegacao_mes(mes_base, "detalhar"),
            [
                botao_comando("🏷 Categorias", f"categorias {mes_base}"),
                botao_comando("💰 Contas", f"contas {mes_base}"),
            ],
            [
                botao_comando("💳 Parcelas", f"parcelas {mes_base}"),
                botao_comando("📆 Agenda geral", "agenda"),
            ],
            [
                botao_comando("🧠 Diagnóstico", "assessor"),
            ],
        ]
        return InlineKeyboardMarkup(linhas)

    if comando in ["resumo do mês", "resumo do mes"] or comando.startswith("resumo"):
        linhas = [
            botoes_navegacao_mes(mes_base, "resumo"),
            [
                botao_comando("📋 Detalhar mês", f"detalhar {mes_base}"),
                botao_comando("🏷 Categorias", f"categorias {mes_base}"),
            ],
            [
                botao_comando("📆 Agenda geral", "agenda"),
                botao_comando("🧠 Diagnóstico", "assessor"),
            ],
        ]
        return InlineKeyboardMarkup(linhas)

    if comando.startswith("contas") or comando.startswith("formas"):
        prefixo = "contas" if comando.startswith("contas") else "formas"
        linhas = [
            botoes_navegacao_mes(mes_base, prefixo),
            [
                botao_comando("📋 Detalhar mês", f"detalhar {mes_base}"),
                botao_comando("🏷 Categorias", f"categorias {mes_base}"),
            ],
            [
                botao_comando("📆 Agenda geral", "agenda"),
                botao_comando("🧠 Diagnóstico", "assessor"),
            ],
        ]
        return InlineKeyboardMarkup(linhas)

    if comando.startswith("parcelamentos") or comando.startswith("parcelas"):
        linhas = [
            botoes_navegacao_mes(mes_base, "parcelas"),
            [
                botao_comando("📆 Parcelas do mês", f"parcelas {mes_base}"),
                botao_comando("🔮 Futuras", "parcelas futuras"),
            ],
            [
                botao_comando("📋 Detalhar mês", f"detalhar {mes_base}"),
                botao_comando("📆 Agenda geral", "agenda"),
            ],
        ]
        return InlineKeyboardMarkup(linhas)


    if comando.startswith("entradas") or comando.startswith("receitas"):
        linhas = [
            botoes_navegacao_mes(mes_base, "entradas"),
            [
                botao_comando("📋 Detalhar mês", f"detalhar {mes_base}"),
                botao_comando("📆 Agenda geral", "agenda"),
            ],
            [
                botao_comando("🧠 Diagnóstico", "assessor"),
                botao_comando("⚙️ Ajuda entradas", "__help__"),
            ],
        ]
        return InlineKeyboardMarkup(linhas)

    if comando.startswith("fixos"):
        return InlineKeyboardMarkup([
            [botao_comando("✏️ Editar fixos", "editar fixos")],
            [
                botao_comando("📆 Agenda geral", "agenda"),
                botao_comando("🏷 Categorias", "categorias"),
            ],
            [
                botao_comando("💰 Contas", "contas"),
                botao_comando("🧠 Diagnóstico", "assessor"),
            ],
        ])

    if comando.startswith("assessor") or comando.startswith("diagnostico") or comando.startswith("diagnóstico"):
        hoje = relogio.hoje().strftime("%Y-%m")
        return InlineKeyboardMarkup([
            [
                botao_comando("📋 Detalhar mês", f"detalhar {hoje}"),
                botao_comando("🏷 Categorias", f"categorias {hoje}"),
            ],
            [
                botao_comando("📆 Agenda geral", "agenda"),
                botao_comando("💰 Entradas", "entradas"),
            ],
            [
                botao_comando("📄 Fechamento", "fechamento do mês"),
            ],
            [
                botao_comando(f"◀️ {formatar_ano_mes_exibicao(somar_meses_app(hoje, -1), curto=True)}", f"detalhar {somar_meses_app(hoje, -1)}"),
                botao_comando(f"{formatar_ano_mes_exibicao(somar_meses_app(hoje, 1), curto=True)} ▶️", f"detalhar {somar_meses_app(hoje, 1)}"),
            ],
        ])

    if comando.startswith("fechamento") or comando.startswith("relatorio") or comando.startswith("relatório"):
        linhas = [
            botoes_navegacao_mes(mes_base, "fechamento"),
            [
                botao_comando("📋 Detalhar mês", f"detalhar {mes_base}"),
                botao_comando("🏷 Categorias", f"categorias {mes_base}"),
            ],
            [
                botao_comando("📆 Agenda geral", "agenda"),
                botao_comando("🧠 Diagnóstico", "assessor"),
            ],
        ]
        return InlineKeyboardMarkup(linhas)

    return None


def _menu_button(texto: str, style: str | None = None):
    """Usa estilo nativo quando disponível sem tornar a UI dependente dele."""
    if style:
        try:
            return KeyboardButton(texto, style=style)
        except TypeError:
            # Compatibilidade defensiva com ambientes Telegram anteriores ao
            # suporte de estilos. O rótulo continua suficiente para a ação.
            pass
    return KeyboardButton(texto)


def montar_menu_principal(abrir=False):
    if not abrir:
        # Omitir markup preserva o teclado e seu estado no cliente.
        # Nunca remover ou reenviar nas respostas comuns.
        return None
    # Cores reforçam intenção, mas os rótulos continuam completos para
    # acessibilidade e a função segue utilizável caso o cliente ignore estilos.
    keyboard = [
        [_menu_button('🏠 Início', 'primary'), _menu_button('➕ Registrar', 'primary')],
        [_menu_button('🧾 A pagar', 'primary'), _menu_button('🔎 Histórico')],
        [_menu_button('📊 Análises'), _menu_button('⚙️ Mais')],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=False,
        input_field_placeholder="Registre um gasto ou faça uma pergunta."
    )


def normalizar_atalho_menu(texto: str):
    texto_limpo = (texto or "").lower().strip()
    return ATALHOS_MENU.get(texto_limpo)



def obter_allowed_chat_id():
    if not ASSESSOR_ALLOWED_CHAT_ID:
        return None
    try:
        return int(ASSESSOR_ALLOWED_CHAT_ID)
    except ValueError as exc:
        raise RuntimeError("ASSESSOR_ALLOWED_CHAT_ID precisa ser um número.") from exc


def contexto_chat_autorizado(update: Update):
    allowed_user_id = obter_allowed_user_id()
    allowed_chat_id = obter_allowed_chat_id()
    if allowed_chat_id is None and not ASSESSOR_ALLOW_GROUPS:
        # Em conversa privada do Telegram, o chat pessoal usa o mesmo identificador do usuário.
        allowed_chat_id = allowed_user_id
    return chat_is_allowed(
        update,
        allow_groups=ASSESSOR_ALLOW_GROUPS,
        allowed_chat_id=allowed_chat_id,
    )


def obter_allowed_user_id():
    valor = config.ler("TELEGRAM_ALLOWED_USER_ID")

    if not valor:
        return None

    try:
        return int(valor)
    except ValueError:
        raise RuntimeError(
            "TELEGRAM_ALLOWED_USER_ID inválido no arquivo .env. "
            "Ele precisa ser um número."
        )


def usuario_autorizado(update: Update):
    if not contexto_chat_autorizado(update):
        return False

    allowed_user_id = obter_allowed_user_id()

    if allowed_user_id is None:
        return False

    if not update.effective_user:
        return False

    return update.effective_user.id == allowed_user_id


def obter_dados_usuario(update: Update):
    usuario = update.effective_user

    if not usuario:
        return "Usuário não identificado."

    username = f"@{usuario.username}" if usuario.username else "não informado"

    return (
        "👤 Dados do seu Telegram\n\n"
        f"ID: {usuario.id}\n"
        f"Nome: {usuario.full_name}\n"
        f"Username: {username}"
    )


async def bloquear_se_nao_autorizado(update: Update):
    scope_update(update)
    if usuario_autorizado(update):
        return False
    # Fail-silent: não confirma a existência, configuração ou proprietário do bot.
    return True


def politica_protecao_conteudo() -> bool:
    """Mesma chave de ambiente de telegram_recursos.protect_financial_content."""
    return config.ler("ASSESSOR_PROTECT_FINANCIAL_CONTENT", "1").strip().lower() in {"1", "true", "sim", "s", "yes", "on"}


def modo_ocultar_ativo(update) -> bool:
    """True quando a sessão da interface nova está com Ocultar ligado."""
    try:
        sessao = ux.EXPERIENCE.sessions.get(chave_sessao_update(update))
        return bool(sessao is not None and getattr(sessao, "privacy", False))
    except Exception:
        return False


MENSAGEM_IMAGEM_OCULTA = (
    "🙈 Modo Ocultar ligado: a imagem com valores não foi enviada.\n\n"
    "Desligue Ocultar no Início para ver o gráfico."
)


async def enviar_resposta(update: Update, resposta, mostrar_menu: bool = True, comando_executado: str | None = None):
    from telegram_design import legacy_pages, mask_money
    reply_markup_menu = montar_menu_principal() if mostrar_menu else None
    # Privacidade do caminho legado: Ocultar mascara valores; arquivos, imagens e
    # textos com valores saem com protect_content (sem encaminhar nem salvar).
    ocultar = modo_ocultar_ativo(update)
    proteger = politica_protecao_conteudo()
    if ocultar:
        if isinstance(resposta, dict):
            resposta = dict(resposta)
            if resposta.get("texto"):
                resposta["texto"] = mask_money(resposta["texto"])
            if resposta.get("imagem"):
                resposta.pop("imagem", None)
                resposta["texto"] = "\n\n".join(p for p in (MENSAGEM_IMAGEM_OCULTA, resposta.get("texto")) if p)
        else:
            resposta = mask_money(str(resposta))

    def _protecao_texto(parte):
        return {"protect_content": True} if proteger and "R$" in str(parte) else {}

    protecao_midia = {"protect_content": True} if proteger else {}
    try:
        sessao_resposta = chave_sessao_update(update)
    except Exception:
        sessao_resposta = None
    inline_markup = montar_teclado_inline_para_resposta(comando_executado, resposta, sessao_resposta)
    if inline_markup:
        persistir_callback_comandos(force=True)

    comando_normalizado = (comando_executado or "").lower().strip()
    deve_formatar_datas = not (
        comando_normalizado == "__help__"
        or comando_normalizado.startswith("/help")
        or comando_normalizado.startswith("help")
    )

    mensagem_destino = update.message
    if mensagem_destino is None and update.callback_query:
        mensagem_destino = update.callback_query.message

    if mensagem_destino is None:
        return

    if isinstance(resposta, dict):
        texto = resposta.get("texto", "")
        if deve_formatar_datas:
            texto = formatar_datas_para_exibicao(texto)
        arquivo = resposta.get("arquivo")
        imagem = resposta.get("imagem")

        # Quando houver imagem, o texto vai apenas como legenda da foto.
        # Assim evitamos enviar primeiro uma mensagem de texto e depois repetir
        # a mesma legenda junto com o dashboard.
        if imagem:
            caminho_imagem = Path(imagem)

            if caminho_imagem.exists():
                # Legendas também seguem o tema. Uma legenda longa continua em
                # texto, sem descartar os detalhes depois do limite da foto.
                legendas = legacy_pages(texto, limit=950) if texto else []
                with caminho_imagem.open("rb") as f:
                    mensagem_enviada = await mensagem_destino.reply_photo(
                        photo=f,
                        caption=legendas[0] if legendas else None,
                        parse_mode="HTML",
                        reply_markup=(inline_markup or reply_markup_menu) if len(legendas)<=1 else None,
                        **protecao_midia
                    )
                    registrar_mensagem_enviada(mensagem_enviada)
                for indice, parte in enumerate(legendas[1:], 1):
                    mensagem_enviada = await mensagem_destino.reply_text(
                        parte, parse_mode="HTML",
                        reply_markup=(inline_markup or reply_markup_menu) if indice==len(legendas)-1 else None,
                        **protecao_midia
                    )
                    registrar_mensagem_enviada(mensagem_enviada)
            else:
                mensagem_enviada = await mensagem_destino.reply_text(
                    message_html(f"Imagem não encontrada: {imagem}"),
                    reply_markup=reply_markup_menu,
                    parse_mode="HTML"
                )
                registrar_mensagem_enviada(mensagem_enviada)

            return

        if texto:
            partes = legacy_pages(texto)
            for indice, parte in enumerate(partes):
                mensagem_enviada = await mensagem_destino.reply_text(
                    parte, parse_mode="HTML",
                    reply_markup=inline_markup if indice == len(partes) - 1 and inline_markup else reply_markup_menu,
                    **(protecao_midia if arquivo else _protecao_texto(parte))
                )
                registrar_mensagem_enviada(mensagem_enviada)

        if arquivo:
            caminho = Path(arquivo)
            user_id_arquivo = update.effective_user.id if update.effective_user else None

            if caminho.exists() and not assessor_esta_desbloqueado(user_id_arquivo):
                # Backup (.db) e CSV nunca vão ao chat sem PIN válido: o arquivo
                # fica no computador e a entrega é refeita após o desbloqueio.
                guardar_acao_pendente_pin(user_id_arquivo, update)
                mensagem_enviada = await mensagem_destino.reply_text(
                    message_html("🔐 O arquivo foi gerado no computador, mas só é enviado ao chat "
                                 "com o PIN. Digite o PIN para recebê-lo."),
                    parse_mode="HTML",
                )
                registrar_mensagem_enviada(mensagem_enviada)
                await enviar_teclado_pin(update, renovar=True)
            elif caminho.exists():
                with caminho.open("rb") as f:
                    mensagem_enviada = await mensagem_destino.reply_document(
                        document=f,
                        filename=caminho.name,
                        **protecao_midia
                    )
                    registrar_mensagem_enviada(mensagem_enviada)
            else:
                mensagem_enviada = await mensagem_destino.reply_text(
                    message_html(f"Arquivo não encontrado: {arquivo}"),
                    reply_markup=reply_markup_menu,
                    parse_mode="HTML"
                )
                registrar_mensagem_enviada(mensagem_enviada)

        return

    texto_resposta = str(resposta)
    if deve_formatar_datas:
        texto_resposta = formatar_datas_para_exibicao(texto_resposta)

    partes = legacy_pages(texto_resposta)

    for indice, parte in enumerate(partes):
        mensagem_enviada = await mensagem_destino.reply_text(
            parte, parse_mode="HTML",
            reply_markup=inline_markup if indice == len(partes) - 1 and inline_markup else reply_markup_menu,
            **_protecao_texto(parte)
        )
        registrar_mensagem_enviada(mensagem_enviada)



def montar_help_principal():
    return (
        "❓ Ajuda rápida do Assessor\n\n"
        "Escolha o que você quer fazer. Envie o comando exatamente como no exemplo.\n\n"

        "💸 Lançar gastos e entradas\n"
        "gastei 35 almoço pix mercado pago\n"
        "gastei 19,89 almoço iFood pix caju\n"
        "recebi 600,00 VR conta Caju\n"
        "recebi 3800 salário\n\n"

        "📊 Entender o mês\n"
        "meu mês\n"
        "saldo geral\n"
        "herança\n"
        "pendências abertas\n\n"

        "🏦 Ver dinheiro em caixa\n"
        "caixa\n"
        "caixa 2026-07\n"
        "saldo 2026-07 Caju\n"
        "Ajustar saldos: Contas e saldos → Ajustar saldos atuais\n"
        "transferi 100 do Itaú para Caju\n\n"

        "💳 Ver o que ainda vou pagar\n"
        "compromissos 2026-07\n"
        "quanto vou pagar no mercado pago em 2026-07\n"
        "quanto vou pagar no nubank em 2026-07\n"
        "checklist pendentes 2026-07\n\n"

        "✅ Dar baixa e configurar vencimentos\n"
        "checklist 2026-07\n"
        "vencimentos 2026-07\n"
        "vencimento B2 para dia 10\n"
        "vencimento B2 2026-07 para dia 10\n"
        "paguei C7 B1 B3 2026-07\n"
        "marcar pendente C7 2026-07\n\n"

        "🔎 Auditar e detalhar\n"
        "auditar despesas 2026-07\n"
        "de onde vem as despesas 2026-07\n"
        "movimentações mercado pago 2026-07\n"
        "extrato caju 2026-07\n\n"

        "✏️ Corrigir lançamento\n"
        "corrigir valor 48 para 42,90\n"
        "mudar 48 para Alimentação\n"
        "corrigir conta 48 para Caju\n"
        "corrigir forma 48 para pix\n\n"

        "📚 Ajuda e treinamento\n"
        "/aprender · /aprender caixa · /aprender checklist\n"
        "/help lancamentos · /help caju · /help caixa\n"
        "/help saldo · /help pagar · /help checklist\n"
        "/help consultas · /help corrigir · /help fixos\n"
        "/help parcelas · /help entradas · /help backup"
    )



def montar_help_lancamentos():
    return (
        "💸 /help lancamentos\n\n"
        "Use frases naturais. O bot tenta identificar valor, descrição, categoria, conta e forma.\n\n"

        "Despesa avulsa:\n"
        "gastei 35 almoço pix mercado pago\n"
        "gastei 19,89 almoço iFood pix caju\n"
        "gastei 80 gasolina pix\n"
        "comprei 45 remédio crédito mercado pago\n\n"

        "Entrada recebida:\n"
        "recebi 3800 salário\n"
        "recebi 600,00 VR conta Caju\n"
        "recebi 120 ajuda home office\n\n"

        "Compra parcelada:\n"
        "comprei celular em 12x de 50 no cartão nubank\n"
        "comprei drone em 16 parcelas de 500 no mercado pago\n\n"

        "Regra importante:\n"
        "Entrada só deve ser lançada quando caiu de verdade.\n"
        "Salário, VR/Caju e bônus não entram automaticamente no saldo real.\n\n"

        "Depois de lançar:\n"
        "últimas 10\n"
        "extrato caju 2026-07\n"
        "meu mês 2026-07"
    )


def montar_help_fixos():
    return (
        "🔁 /help fixos\n\n"
        "Use para contas que repetem todo mês:\n"
        "água, luz, condomínio, internet, IPTU, academia, assinaturas etc.\n\n"

        "Criar fixo:\n"
        "novo fixo agua 150 pix dia 25\n"
        "novo fixo água 150 no pix dia 25\n"
        "novo agua 150 pix dia 25\n"
        "fixo novo internet 120 pix dia 10\n"
        "cadastrar fixo academia 99 no cartão nubank dia 5\n\n"

        "Listar fixos:\n"
        "fixos\n\n"

        "Alterar banco/conta:\n"
        "alterar conta fixo 7 para Pix\n"
        "alterar conta fixo 7 para BTG\n\n"

        "Alterar forma:\n"
        "alterar forma fixo 7 para pix\n"
        "alterar forma fixo 7 para crédito\n\n"

        "Alterar valor:\n"
        "alterar fixo 10 para 250\n\n"

        "Alterar vencimento:\n"
        "alterar vencimento fixo 10 para dia 5\n\n"

        "Pausar, reativar ou apagar:\n"
        "pausar fixo 10\n"
        "reativar fixo 10\n"
        "apagar fixo 10\n\n"

        "Depois de mexer em fixos, confira:\n"
        "agenda\n"
        "quanto vou pagar no pix\n"
        "contas"
    )


def montar_help_parcelas():
    return (
        "💳 /help parcelas\n\n"
        "Use para compras que acabam em algum momento.\n\n"

        "Criar compra parcelada:\n"
        "comprei celular em 12x de 50 no cartão nubank\n"
        "comprei drone em 16 parcelas de 500 no mercado pago\n"
        "comprei notebook de 3000 em 10x no cartão btg\n\n"

        "Listar todos os parcelamentos:\n"
        "parcelamentos\n\n"

        "Ver parcelas de um mês:\n"
        "parcelas 2026-07\n"
        "parcelas 2026-08\n\n"

        "Ver parcelas futuras:\n"
        "parcelas futuras\n\n"

        "Detalhar um parcelamento:\n"
        "parcelas 10\n"
        "parcelamento 10\n\n"

        "Apagar parcelamento inteiro:\n"
        "apagar parcelamento 10\n"
        "excluir parcelamento 10\n\n"

        "Atenção:\n"
        "apagar 10 remove só o lançamento #10.\n"
        "apagar parcelamento 10 remove todas as parcelas daquele parcelamento."
    )



def montar_help_consultas():
    return (
        "🔎 /help consultas\n\n"
        "Existem duas visões diferentes:\n\n"

        "🏦 Caixa = dinheiro disponível por banco/conta\n"
        "caixa\n"
        "caixa 2026-07\n"
        "saldo 2026-07 Itaú\n"
        "saldo 2026-07 Mercado Pago\n"
        "saldo 2026-07 Caju\n\n"

        "💳 Contas = obrigações/gastos do mês\n"
        "contas 2026-07\n"
        "quanto vou pagar no mercado pago em 2026-07\n"
        "quanto vou pagar no nubank em 2026-07\n\n"

        "📒 Movimentações e extrato\n"
        "movimentações mercado pago 2026-07\n"
        "movimentações caju 2026-07\n"
        "extrato mercado pago 2026-07\n"
        "extrato caju 2026-07\n\n"

        "🏷 Categoria e forma\n"
        "categorias 2026-07\n"
        "formas 2026-07\n"
        "quanto gastei com alimentação em 2026-07\nquanto gastei de viagem nos últimos 3 meses\nquanto gastei com alimentação de julho a novembro\nquanto gastei com mercado em 2025\n\n"

        "🔎 Auditoria\n"
        "auditar despesas 2026-07\n"
        "de onde vem as despesas 2026-07\n"
        "pendências abertas 2026-07"
    )



def montar_help_saldo():
    return (
        "🏦 /help saldo\n\n"
        "Use para entender saldo geral, herança do mês anterior e dinheiro por conta.\n\n"

        "Resumo do mês:\n"
        "meu mês\n"
        "meu mês 2026-07\n"
        "saldo geral 2026-07\n\n"

        "Herança do mês anterior:\n"
        "herança\n"
        "herança 2026-07\n"
        "saldo herdado 2026-07\n\n"

        "Dinheiro em caixa por banco/conta:\n"
        "caixa\n"
        "caixa 2026-07\n"
        "saldos das contas 2026-07\n"
        "dinheiro em caixa 2026-07\n\n"

        "Saldo de uma conta específica:\n"
        "saldo 2026-07 Itaú\n"
        "saldo 2026-07 Mercado Pago\n"
        "saldo 2026-07 Caju\n\n"

        "Ajustar saldo de uma conta (mês atual):\n"
        "Contas e saldos → Ajustar saldos atuais\n"
        "informe o valor que aparece agora no app do banco.\n\n"

        "Saldo inicial de uma conta por comando:\n"
        "ajustar saldo 2026-07 Itaú para 1000\n"
        "ajustar saldo 2026-07 Caju para 580,11\n"
        "Em mês que herda o saldo do anterior, só essa conta muda;\n"
        "as outras seguem herdadas. Os meses seguintes herdam o novo\n"
        "valor e os anteriores não mudam. Para a conta voltar a herdar:\n"
        "saldo inicial 2026-07 Itaú herdado\n"
        "Não vale em mês com saldo inicial geral (sem divisão por conta).\n\n"

        "Diferença importante:\n"
        "caixa = dinheiro disponível.\n"
        "contas = obrigações/gastos do mês."
    )



def montar_help_checklist():
    return (
        "✅ /help checklist\n\n"
        "Use para controlar o que foi pago e o que ainda falta dar baixa.\n\n"

        "Abrir checklist:\n"
        "checklist\n"
        "checklist 2026-07\n"
        "checklist pendentes 2026-07\n"
        "checklist pagos 2026-07\n\n"

        "Marcar como pago:\n"
        "paguei C7\n"
        "paguei B3\n"
        "paguei C7 B1 B3 2026-07\n\n"

        "Voltar para pendente:\n"
        "marcar pendente C7\n"
        "marcar pendente B3 2026-07\n\n"

        "Detalhar item:\n"
        "detalhar C7\n"
        "detalhar B3 2026-07\n\n"

        "Datas de pagamento e lembrete:\n"
        "vencimentos 2026-07\n"
        "vencimento B2 para dia 10\n"
        "vencimento B2 2026-07 para dia 10\n"
        "apagar vencimento fixo B2\n"
        "vencimentos hoje\n\n"

        "Pendências antigas:\n"
        "pendências abertas\n"
        "pendências abertas 2026-07\n\n"

        "Legenda:\n"
        "C/P = fixo, compromisso ou parcela individual.\n"
        "B = fatura/cartão agrupado por banco.\n"
        "T = lançamento avulso já realizado.\n\n"

        "Regra de mês:\n"
        "Se estiver pagando junho em julho, informe o mês de origem:\n"
        "paguei B3 2026-06"
    )


def montar_help_agenda():
    return (
        "📆 /help agenda\n\n"
        "A agenda é a visão consolidada da sua vida financeira.\n"
        "Ela junta avulsos, fixos, parcelas, receitas e lançamentos importados.\n\n"

        "Ver mês atual + próximos meses:\n"
        "agenda\n\n"

        "Ver mês específico:\n"
        "agenda 2026-06\n"
        "agenda 2026-07\n"
        "agenda 2026-08\n\n"

        "Detalhar mês específico:\n"
        "detalhar 2026-07\n"
        "detalhar categoria assinaturas 2026-07\n\n"

        "Ver agrupamentos do mês:\n"
        "contas 2026-07\n"
        "formas 2026-07\n"
        "categorias 2026-07\n"
        "parcelas 2026-07\n\n"

        "Ver por conta específica:\n"
        "quanto vou pagar no pix em 2026-07\n"
        "quanto vou pagar no nubank em 2026-07\n"
        "quanto vou pagar no mercado pago em 2026-07\n\n"

        "Para análise financeira:\n"
        "assessor\n"
        "fechamento do mês\n"
        "fechamento 2026-07"
    )


def montar_help_detalhar():
    return (
        "📋 /help detalhar\n\n"
        "Use para abrir os números do mês e entender o que existe dentro de cada categoria.\n\n"

        "Detalhar mês atual:\n"
        "detalhar mês\n"
        "detalhar mes\n\n"

        "Detalhar mês específico:\n"
        "detalhar 2026-07\n"
        "detalhar 2026-08\n\n"

        "Ver categorias do mês:\n"
        "categorias\n"
        "categorias 2026-07\n\n"

        "Detalhar uma categoria:\n"
        "detalhar categoria assinaturas\n"
        "detalhar categoria assinaturas 2026-07\n"
        "detalhar assinaturas\n"
        "assinaturas 2026-07\n\n"

        "Ver categoria nos próximos meses:\n"
        "categoria assinaturas futuro\n"
        "categoria moradia futuro\n"
        "categoria eletrônicos futuro\n\n"

        "Exemplo prático:\n"
        "Se categorias 2026-07 mostrar Assinaturas, envie:\n"
        "detalhar categoria assinaturas 2026-07"
    )



def montar_help_corrigir():
    return (
        "✏️ /help corrigir\n\n"
        "Use quando um lançamento foi salvo com valor, categoria, conta ou forma errada.\n\n"

        "Corrigir valor:\n"
        "corrigir valor 48 para 42,90\n"
        "corrigir 48 para 42,90\n\n"

        "Corrigir categoria:\n"
        "mudar 48 para Alimentação\n"
        "mudar 10-18 para Eletrônicos\n\n"

        "Corrigir banco/conta:\n"
        "corrigir conta 48 para Caju\n"
        "corrigir conta 48 para Mercado Pago\n"
        "corrigir conta 48 para Itaú\n\n"

        "Corrigir forma:\n"
        "corrigir forma 48 para pix\n"
        "corrigir forma 48 para crédito\n\n"

        "Corrigir fixo/compromisso:\n"
        "alterar conta fixo 7 para Pix\n"
        "alterar forma fixo 7 para pix\n"
        "alterar fixo 10 para 250\n\n"

        "Conferir depois:\n"
        "lançamento 48\n"
        "últimas 10\n"
        "caixa 2026-07\n"
        "meu mês 2026-07"
    )


def montar_help_excluir():
    return (
        "🗑️ /help excluir\n\n"
        "Use com cuidado. Exclusão remove dados da base.\n\n"

        "Apagar um lançamento específico:\n"
        "apagar 10\n\n"

        "Apagar uma faixa de lançamentos:\n"
        "apagar 10-18\n\n"

        "Apagar o último lançamento:\n"
        "apagar último\n"
        "apagar ultimo\n\n"

        "Apagar fixo:\n"
        "apagar fixo 10\n\n"

        "Apagar parcelamento inteiro:\n"
        "apagar parcelamento 10\n"
        "excluir parcelamento 10\n\n"

        "Atenção:\n"
        "Se uma parcela tem ID #10, apagar 10 remove só essa parcela.\n"
        "Para remover o conjunto inteiro, use apagar parcelamento 10.\n\n"

        "Depois de excluir, confira:\n"
        "últimas 20\n"
        "agenda\n"
        "parcelamentos\n"
        "fixos"
    )


def montar_help_metas():
    return (
        "🎯 /help metas\n\n"
        "Use metas para controlar limites mensais por categoria.\n\n"

        "Criar ou alterar meta:\n"
        "meta mercado 800\n"
        "meta alimentação 600\n"
        "meta eletrônicos 300\n"
        "meta moradia 1500\n\n"

        "Listar metas:\n"
        "metas\n"
        "listar metas\n"
        "minhas metas\n\n"

        "Apagar meta:\n"
        "apagar meta mercado\n"
        "apagar meta eletrônicos\n\n"

        "Ver impacto das metas:\n"
        "assessor\n"
        "relatório do mês\n"
        "fechamento do mês\n"
        "categorias"
    )


def montar_help_importacao():
    return (
        "📥 /help importacao\n\n"
        "Use para importar seu CSV e equalizar sua vida financeira atual com o bot.\n\n"

        "Fluxo recomendado:\n"
        "1. Coloque o CSV na pasta imports\n"
        "2. Envie: analisar csv\n"
        "3. Confira a prévia\n"
        "4. Se estiver correto, envie: confirmar importacao\n"
        "5. Se estiver errado, envie: cancelar importacao\n\n"

        "Comandos:\n"
        "analisar csv\n"
        "confirmar importacao\n"
        "cancelar importacao\n\n"

        "Depois de importar, confira:\n"
        "status\n"
        "agenda\n"
        "contas\n"
        "fixos\n"
        "parcelamentos\n"
        "quanto vou pagar no pix\n"
        "quanto vou pagar no nubank"
    )



def montar_help_backup():
    return (
        "💾 /help backup\n\n"
        "Use para backup, exportação, status técnico e segurança.\n\n"

        "Backup do banco:\n"
        "backup\n\n"

        "Exportar CSV:\n"
        "exportar csv\n"
        "exportar csv 2026-07\n"
        "exportar csv tudo\n\n"

        "Status técnico:\n"
        "status\n\n"

        "Segurança:\n"
        "/seguranca\n"
        "bloquear\n"
        "esqueci pin\n\n"

        "Telegram ID:\n"
        "/meuid\n\n"

        "Limpar conversa rastreada pelo bot:\n"
        "/limpar"
    )


def montar_help_entradas():
    return (
        "💰 /help entradas\n\n"
        "Regra do projeto:\n"
        "entrada só deve ser lançada quando o dinheiro caiu de verdade.\n"
        "Mesmo salário, VR/Caju e bônus não entram automaticamente no saldo real.\n\n"

        "Lançar entrada recebida:\n"
        "recebi 3800 salário\n"
        "recebi 600,00 VR conta Caju\n"
        "recebi 120 ajuda home office\n"
        "recebi 500 bônus\n\n"

        "Consultar entradas:\n"
        "entradas\n"
        "entradas 2026-07\n"
        "últimas 10\n\n"

        "Corrigir entrada lançada:\n"
        "corrigir valor 42 para 600,00\n"
        "corrigir conta 42 para Caju\n"
        "mudar 42 para Benefícios\n\n"

        "Atenção:\n"
        "Use entrada fixa prevista só se você realmente quiser simular futuro.\n"
        "Para saldo real/conservador, lance apenas quando receber."
    )


def montar_help_assessor():
    return (
        "🧠 /help assessor\n\n"
        "Use para receber leitura financeira, diagnóstico e recomendação.\n\n"

        "Diagnóstico financeiro:\n"
        "assessor\n"
        "diagnóstico financeiro\n"
        "diagnostico financeiro\n\n"

        "Fechamento semanal:\n"
        "fechamento semanal\n"
        "semana\n\n"

        "Fechamento mensal:\n"
        "fechamento do mês\n"
        "fechamento mensal\n"
        "fechamento 2026-07\n\n"

        "Relatório mensal:\n"
        "relatório do mês\n"
        "relatorio do mes\n"
        "relatório 2026-07\n"
        "relatorio 2026-07\n\n"

        "Simular sem registrar:\n"
        "simular comprei celular em 12x de 50 no cartão nubank\n\n"

        "Pedir opinião antes de comprar:\n"
        "posso comprar um drone em 10x de 300?\n"
        "vale a pena comprar um celular em 12x de 100?"
    )



def montar_help_caixa():
    return (
        "🏦 /help caixa\n\n"
        "Use para ver dinheiro disponível por banco/conta.\n\n"

        "Ver caixa geral por conta:\n"
        "caixa\n"
        "caixa 2026-07\n"
        "saldos das contas 2026-07\n"
        "dinheiro em caixa 2026-07\n\n"

        "Ver uma conta específica:\n"
        "saldo 2026-07 Itaú\n"
        "saldo 2026-07 Mercado Pago\n"
        "saldo 2026-07 Caju\n\n"

        "Ajustar saldo real (mês atual):\n"
        "Contas e saldos → Ajustar saldos atuais\n"
        "informe o valor que aparece agora no app do banco.\n\n"

        "Saldo inicial de uma conta por comando:\n"
        "ajustar saldo 2026-07 Itaú para 1000\n"
        "ajustar saldo 2026-07 Caju para 580,11\n"
        "Em mês que herda o saldo do anterior, só essa conta muda;\n"
        "as outras seguem herdadas. Os meses seguintes herdam o novo\n"
        "valor e os anteriores não mudam. Para a conta voltar a herdar:\n"
        "saldo inicial 2026-07 Itaú herdado\n"
        "Não vale em mês com saldo inicial geral (sem divisão por conta).\n\n"

        "Transferir entre contas sem afetar Meu mês:\n"
        "transferi 100 do Itaú para Caju\n"
        "transferi 250 do Mercado Pago para Itaú\n"
        "transferências caixa 2026-07\n\n"

        "Fórmula do caixa:\n"
        "saldo inicial + entradas realizadas - saídas imediatas.\n\n"

        "Crédito, faturas e parcelamentos não reduzem o caixa aqui."
    )


def montar_help_pagar():
    return (
        "💳 /help pagar\n\n"
        "Use para ver o que ainda representa obrigação/fatura do mês.\n\n"

        "Visão geral do mês:\n"
        "compromissos 2026-07\n\n"

        "Quanto vou pagar por banco/conta:\n"
        "quanto vou pagar no mercado pago em 2026-07\n"
        "quanto vou pagar no nubank em 2026-07\n"
        "pagar no mercado pago em 2026-07\n\n"

        "Regra atual:\n"
        "inclui crédito, fixos, parcelamentos e compromissos não imediatos.\n"
        "não inclui Pix, débito, dinheiro ou transferência já consolidados no caixa.\n\n"

        "Ver tudo, inclusive Pix realizado:\n"
        "movimentações mercado pago 2026-07\n"
        "extrato mercado pago 2026-07\n\n"

        "Ver pendentes operacionais:\n"
        "checklist pendentes 2026-07"
    )


def montar_help_faturas():
    return "\n".join([
        "💳 /help faturas", "",
        "Compra no crédito mantém a data real e pode ter uma competência de fatura diferente.",
        "Na v39, a partir do dia 25, o fluxo pergunta fatura atual ou próxima.", "",
        "Exemplo: compra 25/09 escolhendo outubro → data 25/09, fatura outubro.",
        "Parcelado 3x → outubro, novembro e dezembro.", "",
        "Para pagar a fatura, use A pagar. Não registre o pagamento como nova compra.",
        "Pagar uma fatura não apaga parcelas futuras.",
    ])


def montar_help_transferencias():
    return "\n".join([
        "🔁 /help transferencias", "",
        "Transferência entre contas próprias não é receita nem despesa.",
        "Exemplo: transferi 100 do Itaú para Caju", "",
        "Consultar: transferências caixa 2026-09",
        "Apagar: apagar transferencia caixa 3", "",
        "Pix é forma de pagamento; origem e destino devem ser contas reais.",
    ])


def montar_help_auditoria():
    return "\n".join([
        "🧪 /help auditoria", "",
        "Use quando um número parecer estranho antes de editar dados.",
        "auditar mês 2026-09",
        "auditar despesas 2026-09",
        "de onde vem as despesas 2026-09", "",
        "Depois localize o lançamento no Histórico e só então corrija ou exclua.",
    ])


def montar_help_planejamento():
    return "\n".join([
        "🎯 /help planejamento", "",
        "Planejamento não grava hipótese como movimento realizado.",
        "Use Limites, Meu plano, Simular e Recorrências para decidir sem alterar seu histórico.", "",
        "Exemplos: meta alimentação 600 | simular comprei celular em 10x de 100 no crédito Itaú",
    ])


def montar_help_caju():
    return (
        "🥗 /help caju\n\n"
        "Caju/VR é tratado como conta de saldo própria.\n\n"

        "Lançar crédito recebido no Caju:\n"
        "recebi 600,00 VR conta Caju\n"
        "recebi 600,00 vale refeição Caju\n\n"

        "Lançar gasto no Caju:\n"
        "gastei 19,89 almoço iFood pix caju\n"
        "gastei 32 mercado pix caju\n"
        "gastei 15 padaria pix caju\n\n"

        "Ver saldo e extrato:\n"
        "saldo 2026-07 Caju\n"
        "caixa 2026-07\n"
        "extrato caju 2026-07\n"
        "movimentações caju 2026-07\n\n"

        "Ajustar saldo real do Caju (mês atual):\n"
        "Contas e saldos → Ajustar saldos atuais\n"
        "informe o valor que aparece agora no app do Caju.\n\n"

        "Saldo inicial do Caju por comando:\n"
        "ajustar saldo 2026-07 Caju para 580,11\n"
        "em mês que herda o saldo, só o Caju muda e os meses seguintes\n"
        "herdam o novo valor; os anteriores não mudam.\n"
        "Não vale em mês com saldo inicial geral (sem divisão por conta).\n\n"

        "Regra:\n"
        "o crédito do VR deve ser lançado só quando cair.\n"
        "os gastos no Caju mantêm forma pix para reduzir saldo imediatamente."
    )


def montar_help_heranca():
    return (
        "🔁 /help heranca\n\n"
        "Use para entender o saldo que veio do mês anterior.\n\n"

        "Ver herança atual:\n"
        "herança\n"
        "herança 2026-07\n"
        "saldo herdado 2026-07\n\n"

        "Ver pendências antigas abertas:\n"
        "pendências abertas\n"
        "pendências abertas 2026-07\n"
        "dívidas abertas 2026-07\n\n"

        "Regra:\n"
        "o mês atual herda o saldo livre provável do mês anterior.\n"
        "não herda o caixa bruto.\n"
        "não soma meses futuros.\n\n"

        "Se uma fatura de junho ficou aberta, quite pelo mês de origem:\n"
        "paguei B3 2026-06"
    )


def montar_help_por_tema(tema: str):
    tema = tema.lower().strip()

    aliases = {
        "lancamento": "lancamentos",
        "lançamento": "lancamentos",
        "lançamentos": "lancamentos",
        "gastos": "lancamentos",
        "receitas": "lancamentos",

        "fixo": "fixos",
        "recorrentes": "fixos",
        "recorrente": "fixos",

        "parcela": "parcelas",
        "parcelamento": "parcelas",
        "parcelamentos": "parcelas",

        "consulta": "consultas",
        "consultas": "consultas",
        "conta": "consultas",
        "contas": "consultas",

        "pagar": "pagar",
        "pagamento": "pagar",
        "pagamentos": "pagar",
        "fatura": "faturas",
        "faturas": "faturas",
        "credito": "faturas",
        "crédito": "faturas",
        "cartao": "faturas",
        "cartão": "faturas",


        "transferencia": "transferencias",
        "transferência": "transferencias",
        "transferencias": "transferencias",
        "transferências": "transferencias",
        "auditoria": "auditoria",
        "auditar": "auditoria",
        "planejamento": "planejamento",
        "planejar": "planejamento",
        "caixa": "caixa",
        "dinheiro": "caixa",
        "banco": "caixa",
        "bancos": "caixa",
        "saldos bancos": "caixa",
        "dinheiro em caixa": "caixa",

        "caju": "caju",
        "vr": "caju",
        "vale refeicao": "caju",
        "vale refeição": "caju",
        "vale alimentacao": "caju",
        "vale alimentação": "caju",

        "pix": "consultas",
        "nubank": "pagar",
        "mercado": "pagar",
        "mercado pago": "pagar",
        "btg": "caixa",

        "saldo": "saldo",
        "saldos": "saldo",
        "saldo conta": "saldo",
        "saldo banco": "saldo",
        "heranca": "heranca",
        "herança": "heranca",
        "pendencias": "heranca",
        "pendências": "heranca",

        "checklist": "checklist",
        "check": "checklist",
        "pendentes": "checklist",
        "pago": "checklist",
        "pagos": "checklist",

        "mes": "agenda",
        "mês": "agenda",

        "detalhe": "detalhar",
        "detalhes": "detalhar",
        "detalhar": "detalhar",
        "categoria": "detalhar",
        "categorias": "detalhar",
        "assinaturas": "detalhar",

        "correcao": "corrigir",
        "correção": "corrigir",
        "editar": "corrigir",
        "alterar": "corrigir",

        "exclusao": "excluir",
        "exclusão": "excluir",
        "apagar": "excluir",
        "deletar": "excluir",

        "meta": "metas",

        "entrada": "entradas",
        "entradas": "entradas",
        "receita": "entradas",
        "receitas": "entradas",
        "salario": "entradas",
        "salário": "entradas",

        "importar": "importacao",
        "importação": "importacao",
        "importacao": "importacao",
        "exportacao": "backup",
        "exportar": "backup",
        "exportação": "backup",
        "csv": "importacao",

        "exportar": "backup",
        "status": "backup",
        "seguranca": "backup",
        "segurança": "backup",

        "diagnostico": "assessor",
        "diagnóstico": "assessor",
        "relatorio": "assessor",
        "relatório": "assessor",
        "fechamento": "assessor",
        "simular": "assessor",
        "comprar": "assessor"
    }

    tema_normalizado = aliases.get(tema, tema)

    helps = {
        "lancamentos": montar_help_lancamentos,
        "fixos": montar_help_fixos,
        "parcelas": montar_help_parcelas,
        "consultas": montar_help_consultas,
        "saldo": montar_help_saldo,
        "caixa": montar_help_caixa,
        "pagar": montar_help_pagar,
        "faturas": montar_help_faturas,
        "transferencias": montar_help_transferencias,
        "auditoria": montar_help_auditoria,
        "planejamento": montar_help_planejamento,
        "caju": montar_help_caju,
        "heranca": montar_help_heranca,
        "checklist": montar_help_checklist,
        "agenda": montar_help_agenda,
        "detalhar": montar_help_detalhar,
        "corrigir": montar_help_corrigir,
        "excluir": montar_help_excluir,
        "metas": montar_help_metas,
        "entradas": montar_help_entradas,
        "importacao": montar_help_importacao,
        "backup": montar_help_backup,
        "assessor": montar_help_assessor
    }

    if tema_normalizado in helps:
        return helps[tema_normalizado]()

    return (
        f"Não encontrei ajuda para o tema: {tema}\n\n"
        "Temas disponíveis:\n"
        "/help lancamentos\n"
        "/help caju\n"
        "/help caixa\n"
        "/help saldo\n"
        "/help pagar\n"
        "/help checklist\n"
        "/help consultas\n"
        "/help corrigir\n"
        "/help fixos\n"
        "/help parcelas\n"
        "/help entradas\n"
        "/help backup\n"
        "/help heranca"
    )


def montar_texto_central():
    return (
        "🏠 Central do Assessor\n\n"
        "Escolha uma ação nos botões da mensagem.\n\n"
        "Menu inferior fixo:\n"
        "🏠 Central · volta para esta tela\n"
        "➕ Lançar · registra despesa, entrada, fixo ou parcela\n"
        "❓ Ajuda · abre o guia completo\n\n"
        "Você também pode digitar normalmente. Exemplo:\n"
        "gastei 35 no almoço no pix"
    )


def obter_resposta_comando_especial(update: Update, comando: str | None):
    texto = (comando or "").lower().strip()

    if texto in ["menu", "central", "/menu"]:
        return montar_texto_central()

    if texto == "__help__":
        return montar_help_principal()

    if texto.startswith("/help"):
        tema = texto.replace("/help", "", 1).strip()
        if tema:
            return montar_help_por_tema(tema)
        return montar_help_principal()

    if texto in ["/seguranca", "/segurança", "seguranca", "segurança"]:
        return obter_status_seguranca(update)

    return None


async def seguranca_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):
        return

    registrar_mensagem_update(update)
    resposta = obter_status_seguranca(update)
    await enviar_resposta(update, resposta, comando_executado="/seguranca")


async def bloquear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):
        return

    registrar_mensagem_update(update)

    user_id = update.effective_user.id if update.effective_user else None
    bloquear_assessor(user_id)
    ux.EXPERIENCE.invalidate(ux.session_key(update))

    await enviar_resposta(
        update,
        "🔒 Assessor bloqueado\n\n"
        "Dados financeiros protegidos. Para liberar novamente, digite seu PIN.",
        comando_executado="/menu"
    )


async def desbloquear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):
        return

    registrar_mensagem_update(update)

    if getattr(context, "args", None):
        # "/desbloquear 123456": o PIN digitado não pode ficar visível no chat.
        await tentar_apagar_mensagem_usuario(update, context)

    if not pin_configurado():
        await enviar_resposta(
            update,
            mensagem_bloqueio_seguranca(),
            comando_executado="/seguranca"
        )
        return

    await enviar_teclado_pin(update, renovar=True)


async def esqueci_pin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):
        return

    registrar_mensagem_update(update)
    await enviar_resposta(update, montar_instrucao_reset_pin(), mostrar_menu=False, comando_executado="/seguranca")


async def resetarpin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):
        return

    registrar_mensagem_update(update)
    texto = update.message.text or ""
    await processar_reset_pin(update, context, texto)



async def limpar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):
        return

    registrar_mensagem_update(update)

    chat_id = update.effective_chat.id
    mensagens = list(dict.fromkeys(MENSAGENS_CHAT.get(chat_id, [])))

    apagadas = 0
    falhas = 0

    for message_id in sorted(mensagens, reverse=True):
        try:
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=message_id
            )
            apagadas += 1
        except Exception:
            falhas += 1

    MENSAGENS_CHAT[chat_id] = []

    resposta = (
        "🧹 Conversa limpa\n\n"
        f"Mensagens removidas nesta sessão: {apagadas}\n"
    )

    if falhas:
        resposta += (
            f"Mensagens que não consegui remover: {falhas}\n\n"
            "Observação: o Telegram limita a exclusão de mensagens por bots. "
            "Mensagens antigas ou não rastreadas pelo bot podem continuar aparecendo."
        )
    else:
        resposta += (
            "Observação: isso limpa as mensagens que o bot conseguiu rastrear nesta sessão. "
            "Para histórico antigo, use a opção nativa do Telegram de limpar conversa."
        )

    mensagem_enviada = await update.effective_chat.send_message(
        message_html(resposta),
        reply_markup=montar_menu_principal(),
        parse_mode="HTML", **thread_options(update)
    )
    registrar_mensagem_enviada(mensagem_enviada)



async def atalhos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):
        return
    if await bloquear_se_assessor_travado(update, 'saldo geral'):
        return
    mensagem = await update.effective_chat.send_message(
        message_html('Escolha um atalho. Use o ícone ao lado da digitação para abrir ou recolher o teclado.'),
        reply_markup=montar_menu_principal(abrir=True), parse_mode="HTML", **thread_options(update))
    registrar_mensagem_enviada(mensagem)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):
        return

    registrar_mensagem_update(update)

    if await bloquear_se_assessor_travado(update, 'saldo geral'):
        return
    limpar_pendencia_guiada(obter_chat_id_update(update))
    limpar_pendencia_exclusao(obter_chat_id_update(update))
    key = ux.session_key(update)
    ux.clear_service_pending(key)
    screen = await ux.run_experience('act',key,('view','home'))
    mensagem = await update.effective_chat.send_message(
        message_html('Escolha uma ação abaixo. Use /cancelar para abandonar um registro.'),
        reply_markup=montar_menu_principal(), parse_mode="HTML", **thread_options(update))
    registrar_mensagem_enviada(mensagem)
    await ux.send_screen(update, screen, sys.modules[__name__])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):
        return

    registrar_mensagem_update(update)
    if context.args:
        from telegram_recursos import deep_action
        try:action=deep_action(context.args[0])
        except ValueError:action=None
        if action:
            public=action[0]=='lesson' or action in {('view','help'),('view','learn')}
            if not public and await bloquear_se_assessor_travado(update,'dashboard'):return
            key=ux.session_key(update)
            ux.EXPERIENCE.pause_for_guidance(ux.EXPERIENCE.session(key))
            screen=(await ux.run_experience('render',key,action[1]) if action[0]=='view'
                    else await ux.run_experience('act',key,action))
            from telegram_recursos import _resume
            if not any(a[0] in {'resume_suspended','learning_resume'} for row in screen.rows for _,a in row):_resume(ux.EXPERIENCE,ux.EXPERIENCE.session(key),screen)
            await ux.send_screen(update,screen,sys.modules[__name__]);return
    await menu_command(update, context)


async def recursos_command(update: Update,context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):return
    if await bloquear_se_assessor_travado(update,'dashboard'):return
    screen=await ux.run_experience('act',ux.session_key(update),('innovations',))
    await ux.send_screen(update,screen,sys.modules[__name__])


async def topics_command(update: Update,context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):return
    await ux.send_screen(update,ux.Screen('A criação de tópicos foi retirada da versão sem cobranças. Use /menu para acessar as ferramentas.',[[('🏠 Início',('view','home'))]]),sys.modules[__name__])


async def receber_midia(update: Update,context: ContextTypes.DEFAULT_TYPE):
    from telegram_midia import receive
    await receive(update,context,sys.modules[__name__])


async def meuid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):
        return
    if await bloquear_se_assessor_travado(update, "/meuid"):
        return
    registrar_mensagem_update(update)
    resposta = obter_dados_usuario(update)
    await enviar_resposta(update, resposta)



async def aprender_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):
        return

    registrar_mensagem_update(update)

    if context.args:
        comando = "aprender " + " ".join(context.args).strip()
    else:
        comando = "aprender"

    screen = await ux.run_experience('open_learning',ux.session_key(update),ux.learning.route(comando) or '')
    await ux.send_screen(update,screen,sys.modules[__name__])


async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):return
    if await bloquear_se_assessor_travado(update,'dashboard'):return
    registrar_mensagem_update(update)
    key=ux.session_key(update)
    route=ux.dashboard_route('dashboard '+' '.join(context.args or []))
    try:
        if route is None:raise ValueError('Use /dashboard, /dashboard categorias ou /dashboard AAAA-MM.')
        view,period=route
        if period:
            month=ux.svc.normalizar_ano_mes_flexivel(period)
            if not month or not ux.svc.validar_ano_mes(month):raise ValueError('Informe o mês como AAAA-MM, por exemplo /dashboard 2026-10.')
            ux.EXPERIENCE.session(key).month=month
        screen=await ux.run_experience('act',key,('chart',view))
    except ValueError as exc:
        screen=ux.Screen('<b>📊 Não consegui montar este painel</b>\n\n'+ux.safe(exc,400),[[('📊 Painel atual',('chart','home')),('💡 Ajuda',('topic','dashboard'))]])
    await ux.send_screen(update,screen,sys.modules[__name__])


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):
        return
    registrar_mensagem_update(update)
    key=ux.session_key(update);topic=ux.norm(' '.join(context.args or []))
    session=ux.EXPERIENCE.sessions.get(key)
    if session and session.stage and (session.fixed_edit or session.new_fixed):
        ux.EXPERIENCE.pause_for_guidance(session)
    # Ajuda é consulta, não cancelamento. Preserve um registro nativo em andamento
    # e ofereça retorno explícito para a etapa anterior.
    if session and session.stage and session.draft:
        if not topic:
            screen=ux.EXPERIENCE._flow_help_screen(session)
            await ux.send_screen(update,screen,sys.modules[__name__])
            return
        ux.EXPERIENCE._suspend_flow(session)
    aliases={'lancamentos':'registrar','caixa':'saldo','heranca':'saldo','checklist':'pagar','entradas':'receber','metas':'limites','assessor':'ia','seguranca':'privacidade','primeiros passos':'primeiros','comecar':'primeiros','cartao':'faturas','credito':'faturas','previsoes':'compromissos','analises':'analisar','painel':'dashboard','dash':'dashboard','aprender':'primeiros'}
    topic=aliases.get(topic,topic)
    if not topic:screen=await ux.run_experience('act',key,('view','help'))
    elif topic in ux.HELP_TOPICS or topic in ux.orient.TOPICS:screen=await ux.run_experience('act',key,('topic',topic))
    else:
        screen=await ux.run_experience('advanced_help',key,topic,montar_help_por_tema(' '.join(context.args)))
    await ux.send_screen(update,screen,sys.modules[__name__])


async def abrir_atalho_ux(update: Update, context: ContextTypes.DEFAULT_TYPE, destino: str):
    if await bloquear_se_nao_autorizado(update):
        return
    registrar_mensagem_update(update)
    if await bloquear_se_assessor_travado(update, 'saldo geral'):
        return
    key=ux.session_key(update)
    s=ux.EXPERIENCE.session(key)
    s.month=ux.EXPERIENCE.date_provider().strftime('%Y-%m')
    if destino=='cash_accounts':
        # Consultar saldos também pausa, em vez de apagar, um registro em andamento.
        if s.stage and s.draft:ux.EXPERIENCE._suspend_flow(s)
        screen=await ux.run_experience('act',key,('cash_accounts',s.month))
    else:
        screen=await ux.run_experience('act',key,('view',destino))
    await ux.send_screen(update,screen,sys.modules[__name__])


async def mes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await abrir_atalho_ux(update,context,'home')


async def registrar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await abrir_atalho_ux(update,context,'register')


async def pagar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await abrir_atalho_ux(update,context,'pay')


async def historico_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await abrir_atalho_ux(update,context,'history')


async def saldos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await abrir_atalho_ux(update,context,'cash_accounts')


async def fechamento_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await abrir_atalho_ux(update,context,'closing')


async def atencao_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await abrir_atalho_ux(update,context,'attention')


def obter_etapas_feedback_visual(comando: str | None):
    texto = (comando or "").lower().strip()

    if not texto:
        return []

    if texto.startswith("dashboard categorias") or texto.startswith("dash categorias") or texto.startswith("painel categorias") or texto.startswith("categorias dashboard"):
        return [
            "⏳ Preparando dashboard de categorias...",
            "🏷 Agrupando categorias do mês...",
            "🥧 Montando gráfico de pizza...",
            "🎨 Finalizando imagem...",
        ]

    if texto.startswith("dashboard") or texto.startswith("dash") or texto.startswith("painel"):
        return [
            "⏳ Preparando dashboard...",
            "📊 Calculando entradas e despesas...",
            "🎨 Montando imagem...",
            "✅ Quase pronto...",
        ]

    if texto.startswith("backup"):
        return [
            "⏳ Preparando backup...",
            "🗂 Conferindo arquivos do projeto...",
            "📦 Compactando dados...",
        ]

    if texto.startswith("exportar"):
        return [
            "⏳ Preparando exportação...",
            "📄 Consultando lançamentos...",
            "📦 Gerando arquivo...",
        ]

    if texto.startswith("importar"):
        return [
            "⏳ Preparando importação...",
            "📄 Lendo arquivo...",
            "🔎 Conferindo dados...",
        ]

    if texto.startswith("fechar mês") or texto.startswith("fechamento") or texto.startswith("fechar mes"):
        return [
            "📘 Iniciando fechamento mensal...",
            "📊 Conferindo entradas e despesas...",
            "🏷 Analisando categorias...",
            "🧾 Montando fechamento...",
        ]

    return []


async def iniciar_feedback_visual(update: Update, etapas: list[str]):
    if not etapas:
        return None

    mensagem_destino = update.message
    if mensagem_destino is None and update.callback_query:
        mensagem_destino = update.callback_query.message

    if mensagem_destino is None:
        return None

    try:
        mensagem = await mensagem_destino.reply_text(message_html(etapas[0]), parse_mode="HTML")
        registrar_mensagem_enviada(mensagem)
        return mensagem
    except Exception:
        return None


async def atualizar_feedback_visual(mensagem, texto: str):
    if mensagem is None:
        return

    try:
        await mensagem.edit_text(texto)
    except Exception:
        pass


async def finalizar_feedback_visual(mensagem):
    if mensagem is None:
        return

    try:
        await mensagem.delete()
    except Exception:
        try:
            await mensagem.edit_text("✅ Pronto.")
        except Exception:
            pass


async def receber_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):
        return

    registrar_mensagem_update(update)

    texto = update.message.text or ""
    texto_limpo = texto.lower().strip()
    user_id = update.effective_user.id if update.effective_user else None

    if obter_pendencia_reset_pin(user_id):
        await processar_reset_pin_guiado(update, context, texto)
        return

    if user_id in RESET_PIN_EXPIRADOS:
        # A mensagem seguinte seria tratada como "chave": apaga e avisa.
        RESET_PIN_EXPIRADOS.discard(user_id)
        await tentar_apagar_mensagem_usuario(update, context)
        await enviar_resposta(
            update,
            "⏳ Pendência expirada.\n\nA recuperação de PIN foi encerrada. Nada foi alterado. "
            "Toque em Resetar PIN para recomeçar.",
            mostrar_menu=False,
            comando_executado="/seguranca"
        )
        return

    if texto_limpo in ["seguranca", "segurança"]:
        resposta = obter_status_seguranca(update)
        await enviar_resposta(update, resposta, comando_executado="/seguranca")
        return

    if texto_limpo in ["esqueci pin", "esqueci meu pin", "/esqueci_pin"]:
        if ASSESSOR_PIN_RESET_KEY:
            await update.message.reply_text(
                message_html(montar_instrucao_reset_pin()),
                reply_markup=montar_botoes_iniciar_reset_pin(),
                parse_mode="HTML"
            )
        else:
            await enviar_resposta(update, montar_instrucao_reset_pin(), mostrar_menu=False, comando_executado="/seguranca")
        return

    if (
        texto_limpo.startswith("reset ")
        or (texto_limpo.startswith("resetar ") and not parsear_comando_resetar_checklist(texto_limpo))
        or texto_limpo.startswith("resetar pin ")
        or texto_limpo.startswith("redefinir pin ")
        or texto_limpo.startswith("trocar pin ")
        or texto_limpo.startswith("/reset ")
        or texto_limpo.startswith("/resetarpin ")
    ):
        await processar_reset_pin(update, context, texto)
        return

    if texto_limpo == "bloquear":
        bloquear_assessor(user_id)
        await enviar_resposta(
            update,
            "🔐 Proteção reforçada bloqueada\n\n"
            "Seu uso diário continua liberado. O PIN será pedido apenas em ações sensíveis.",
            comando_executado="/menu"
        )
        return

    if texto_limpo.startswith("desbloquear "):
        # O PIN digitado não deve ficar visível no chat (sucesso ou falha).
        await tentar_apagar_mensagem_usuario(update, context)
        if not pin_configurado():
            await enviar_resposta(update, mensagem_bloqueio_seguranca(), comando_executado="/seguranca")
            return

        pin_informado = texto_limpo.replace("desbloquear ", "", 1).strip()

        chat_id = update.effective_chat.id if update.effective_chat else None
        locked, remaining = AUTH_LIMITER.status(user_id, chat_id, "pin")
        if locked:
            await enviar_resposta(update, f"🔒 Tentativas bloqueadas. Aguarde aproximadamente {remaining} minuto(s).", comando_executado="/seguranca")
            return

        if not validar_pin_informado(pin_informado):
            bloquear_assessor(user_id)
            locked, remaining, failures = AUTH_LIMITER.register_failure(user_id, chat_id, "pin")
            registrar_auditoria("autenticacao", user_id, "pin_falha", dados_depois={"falhas": failures, "bloqueado": locked}, origem="telegram", usuario_sessao=f"{user_id}:{chat_id}")
            if locked:
                descartar_acao_pendente_pin(user_id)
            mensagem = f"🔒 Muitas tentativas incorretas. Aguarde aproximadamente {remaining} minuto(s)." if locked else "❌ PIN incorreto\n\nAssessor continua bloqueado."
            await enviar_resposta(update, mensagem, comando_executado="/seguranca")
            return

        AUTH_LIMITER.register_success(user_id, chat_id, "pin")
        registrar_auditoria("autenticacao", user_id, "pin_sucesso", origem="telegram", usuario_sessao=f"{user_id}:{chat_id}")
        desbloquear_assessor(user_id)
        await enviar_resposta(
            update,
            "🔓 Proteção reforçada desbloqueada\n\n"
            f"Ações sensíveis ficam liberadas por {ASSESSOR_AUTOLOCK_MINUTES} minuto(s) sem uso.\n"
            "Consultas e lançamentos comuns nunca dependem desta sessão.",
            comando_executado="/menu"
        )
        await reexecutar_acao_pendente_pin(user_id, context)
        return

    # Quick Access: identidade Telegram é a barreira diária. O PIN é segunda
    # camada apenas para ações classificadas como sensíveis.

    # Exclusão pendente vencida: nunca deixa um "sim" tardio confirmar.
    chat_id_exclusao = obter_chat_id_update(update)
    obter_pendencia_exclusao(chat_id_exclusao)
    if chat_id_exclusao in EXCLUSAO_EXPIRADAS:
        EXCLUSAO_EXPIRADAS.discard(chat_id_exclusao)
        await enviar_resposta(update, MENSAGEM_PENDENCIA_EXPIRADA, comando_executado="/menu")
        if texto_limpo in ["confirmar", "sim", "s", "apagar", "deletar", "excluir",
                           "cancelar", "nao", "não", "n"] or texto_limpo in TEXTOS_CONFIRMAR_EXCLUSAO:
            return

    # Confirmação/cancelamento de uma alteração legada (prévia antes → depois):
    # vai direto ao núcleo, que confere a pendência da sessão e recalcula a prévia.
    if re.sub(r"\s+", " ", texto_limpo) in TEXTOS_ALTERACAO_PENDENTE:
        await executar_texto_alteracao_pendente(update, texto_limpo)
        return

    # Nova interface: sempre depois da autorização, antes de gravar.
    if await ux.dispatch_text(update, context, sys.modules[__name__]):
        return

    chat_id = obter_chat_id_update(update)
    pendencia_exclusao = obter_pendencia_exclusao(chat_id)

    if pendencia_exclusao:
        # Só a frase explícita (ou o botão vinculado) confirma: um "sim" solto,
        # digitado para outra pergunta, nunca apaga nada.
        if re.sub(r"\s+", " ", texto_limpo) in TEXTOS_CONFIRMAR_EXCLUSAO:
            await executar_confirmacao_exclusao(update, context)
            return

        if texto_limpo in ["cancelar", "nao", "não", "n", "cancelar exclusao", "cancelar exclusão"]:
            await cancelar_confirmacao_exclusao(update)
            return

        await enviar_resposta(
            update,
            "Há uma exclusão aguardando confirmação. Nada foi apagado.\n\n"
            "Toque em 🗑 Sim, apagar na prévia ou envie: confirmar exclusao\nPara desistir, envie: cancelar",
            comando_executado="/menu"
        )
        return

    if comando_exige_confirmacao_exclusao(texto_limpo):
        if await bloquear_se_assessor_travado(update, texto_limpo):
            return
        confirmou = await solicitar_confirmacao_exclusao(update, texto)
        if confirmou:
            return

    chat_id = obter_chat_id_update(update)
    pendencia_guiada = obter_pendencia_guiada(chat_id)

    if pendencia_guiada:
        comando_guiado = montar_comando_de_pendencia(pendencia_guiada, texto)

        if comando_guiado == "__cancelar_guiado__":
            limpar_pendencia_guiada(chat_id)
            await enviar_resposta(
                update,
                "Fluxo cancelado.\n\nNada foi alterado.",
                comando_executado="/menu"
            )
            return

        if comando_guiado.startswith("__erro_guiado__:"):
            await enviar_resposta(
                update,
                comando_guiado.replace("__erro_guiado__:", "", 1),
                comando_executado="/menu"
            )
            return

        categoria_antes = None
        if pendencia_guiada.get("tipo") == "corrigir_categoria":
            transacao_id = int(pendencia_guiada.get("dados", {}).get("id") or 0)
            raw = buscar_transacao_por_id(transacao_id) if transacao_id else None
            categoria_antes = dict(raw) if raw else None

        # O comando montado pelo fluxo guiado passa pelo mesmo gate de PIN do texto livre
        # (antes de consumir a pendência, para a ação ser refeita após o desbloqueio).
        if await bloquear_se_assessor_travado(update, comando_guiado):
            return
        limpar_pendencia_guiada(chat_id)
        await enviar_acao_digitando(update, context)
        resposta = await executar_core(processar_mensagem,comando_guiado,sessao=chave_sessao_update(update))

        if isinstance(resposta, dict) and resposta.get("arquivo"):
            await enviar_acao_enviando_documento(update, context)

        await enviar_resposta(update, resposta, comando_executado=comando_guiado)
        if categoria_antes:
            raw = buscar_transacao_por_id(int(categoria_antes["id"]))
            await oferecer_aprendizado_categoria(update, categoria_antes, dict(raw) if raw else None)
        return

    atalho = normalizar_atalho_menu(texto)
    comando_executado = atalho or texto

    if await bloquear_se_assessor_travado(update, comando_executado):
        return

    await enviar_acao_digitando(update, context)

    etapas_feedback = obter_etapas_feedback_visual(comando_executado)
    mensagem_feedback = await iniciar_feedback_visual(update, etapas_feedback)

    if len(etapas_feedback) > 1:
        await atualizar_feedback_visual(mensagem_feedback, etapas_feedback[1])

    resposta_especial = obter_resposta_comando_especial(update, comando_executado)
    if resposta_especial is not None:
        resposta = resposta_especial
    else:
        resposta = await executar_core(processar_mensagem,comando_executado,sessao=chave_sessao_update(update))

    if len(etapas_feedback) > 2:
        await atualizar_feedback_visual(mensagem_feedback, etapas_feedback[2])

    marcar_acesso_seguro(user_id)

    if isinstance(resposta, dict) and resposta.get("imagem"):
        await enviar_acao_enviando_foto(update, context)
        if len(etapas_feedback) > 3:
            await atualizar_feedback_visual(mensagem_feedback, etapas_feedback[3])
    elif isinstance(resposta, dict) and resposta.get("arquivo"):
        await enviar_acao_enviando_documento(update, context)

    await finalizar_feedback_visual(mensagem_feedback)
    await enviar_resposta(update, resposta, comando_executado=comando_executado)


async def callback_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):
        return

    if update.callback_query and str(update.callback_query.data or "").startswith("pin_"):
        await processar_callback_pin(update, context)
        return
    if str(update.callback_query.data or '').startswith('af:'):
        import telegram_alertas
        if await telegram_alertas.callback(update,context,sys.modules[__name__]):return

    if str(update.callback_query.data or "").startswith("ux:"):
        # Navegar pela interface nova abandona a exclusão pendente do legado:
        # a resposta seguinte pertence a outra pergunta e não pode confirmá-la.
        limpar_pendencia_exclusao(obter_chat_id_update(update))

    if await ux.dispatch_callback(update, context, sys.modules[__name__]):
        return

    query = update.callback_query
    await query.answer()

    chave = query.data
    comando = CALLBACK_COMANDOS.get(chave)

    if not comando:
        mensagem_enviada = await query.message.reply_text(
            message_html("Esse botão expirou. Envie /menu para abrir o menu novamente."),
            reply_markup=montar_menu_principal(),
            parse_mode="HTML"
        )
        registrar_mensagem_enviada(mensagem_enviada)
        return

    # Botão que repete um comando de texto (confirmar/cancelar uma prévia,
    # exportar, voltar a herdar). Vai direto ao assessor: não pode cair num
    # registro aberto no menu, como aconteceria se o texto fosse digitado
    # durante um formulário.
    pular_nativo = False
    botao_texto_match = _RE_BOTAO_TEXTO.match(comando)
    if botao_texto_match:
        tipo_vinculo, assinatura, comando = botao_texto_match.groups()
        pular_nativo = True
        if tipo_vinculo:
            atual = _assinatura(tipo_vinculo, chave_sessao_update(update))
            if atual is None:
                # Falha fechada: prévia já usada, cancelada ou expirada.
                await enviar_resposta(
                    update,
                    "⏳ Esta prévia não está mais pendente (já foi usada, cancelada ou expirou).\n\n"
                    "Nada foi feito. Envie o comando de novo para ver uma prévia atualizada.",
                    comando_executado="/menu",
                )
                return
            if atual != assinatura:
                await enviar_resposta(
                    update,
                    "⚠️ Este botão é de uma prévia antiga, que já foi substituída por outra.\n\n"
                    "Nada foi feito. Use os botões da prévia mais recente.",
                    comando_executado="/menu",
                )
                return

    if comando.startswith("__exportar_periodo__:"):
        comando_exportar = comando_exportacao_periodo(comando.split(":", 1)[1])
        if comando_exportar:
            comando = comando_exportar
            pular_nativo = True

    if await bloquear_se_assessor_travado(update, comando):
        return

    if re.sub(r"\s+", " ", comando.lower().strip()) in TEXTOS_ALTERACAO_PENDENTE:
        await executar_texto_alteracao_pendente(update, comando)
        return

    if comando == "__guiado_cancelar__":
        limpar_pendencia_guiada(obter_chat_id_update(update))
        await enviar_resposta(update, "Fluxo cancelado.\n\nNada foi alterado.", comando_executado="/menu")
        return

    if comando.startswith("__perguntar_herdar__:"):
        # Um toque só mostra a prévia padrão (antes → depois) com botões
        # vinculados; quem desfaz é o "Confirmar alteração" dessa prévia.
        comando_herdar = comando.split(":", 1)[1]
        resposta = await executar_core(processar_mensagem, comando_herdar, sessao=chave_sessao_update(update))
        await enviar_resposta(update, resposta, comando_executado=comando_herdar)
        return

    if comando == "__nada_alterado__":
        await enviar_resposta(update, "Tudo certo. Nada foi alterado.", comando_executado="/menu")
        return

    if comando == "__bloquear__":
        # Igual a digitar "bloquear": só fecha a proteção reforçada; não
        # descarta registros em andamento (o /bloquear descarta).
        bloquear_assessor(update.effective_user.id if update.effective_user else None)
        await enviar_resposta(
            update,
            "🔐 Proteção reforçada bloqueada\n\n"
            "Seu uso diário continua liberado. O PIN será pedido apenas em ações sensíveis.",
            comando_executado="/menu"
        )
        return

    if comando in {"__confirmar_exclusao__", "__cancelar_exclusao__"}:
        # O botão pertence a uma pendência específica: botão de mensagem
        # antiga nunca confirma (nem cancela) a pendência mais recente.
        chat_id = obter_chat_id_update(update)
        if not botao_vinculo_valido(chave, obter_pendencia_exclusao(chat_id)):
            if chat_id in EXCLUSAO_EXPIRADAS:
                EXCLUSAO_EXPIRADAS.discard(chat_id)
                aviso = MENSAGEM_PENDENCIA_EXPIRADA
            else:
                aviso = MENSAGEM_BOTAO_OBSOLETO
            await query.message.reply_text(message_html(aviso), parse_mode="HTML")
            return
        if comando == "__confirmar_exclusao__":
            await executar_confirmacao_exclusao(update, context)
        else:
            await cancelar_confirmacao_exclusao(update)
        return

    if comando in {"__aprender_categoria_sim__", "__aprender_categoria_nao__"}:
        chat_id = obter_chat_id_update(update)
        if PENDENCIAS_APRENDIZADO_CATEGORIA.get(chat_id) and not botao_vinculo_valido(
            chave, PENDENCIAS_APRENDIZADO_CATEGORIA.get(chat_id)
        ):
            await query.message.reply_text(message_html(MENSAGEM_BOTAO_OBSOLETO), parse_mode="HTML")
            return
        pending = PENDENCIAS_APRENDIZADO_CATEGORIA.pop(chat_id, None)
        if not pending:
            await query.message.reply_text(
                message_html("Essa sugestão de aprendizado expirou. Nenhuma regra foi criada."),
                parse_mode="HTML",
            )
            return
        if comando == "__aprender_categoria_nao__":
            await query.message.reply_text(
                message_html("Tudo bem. A categoria foi corrigida, mas nenhuma preferência foi aprendida."),
                parse_mode="HTML",
            )
            return
        from categorias_pessoais import salvar_regra
        try:
            regra = salvar_regra(pending["descricao"], pending["categoria"])
            registrar_auditoria(
                "regra_categoria_pessoal", pending.get("transacao_id"), "salvar",
                dados_depois={"expressao": regra["phrase"], "categoria": regra["category"]},
                origem="telegram", usuario_sessao=chave_sessao_update(update),
            )
        except ValueError as exc:
            await query.message.reply_text(message_html(str(exc)), parse_mode="HTML")
            return
        await query.message.reply_text(
            message_html(
                f"✅ Preferência aprendida\n\n“{regra['phrase']}” → {regra['category']}\n\n"
                "Ela será usada em texto e áudio. Você continua podendo corrigir qualquer sugestão."
            ),
            parse_mode="HTML",
        )
        return

    if comando.startswith("guiado:"):
        await iniciar_fluxo_guiado(update, context, comando.replace("guiado:", "", 1))
        return

    if comando in ["/limpar", "/clear"]:
        await limpar_command(update, context)
        return

    if comando_exige_confirmacao_exclusao(comando):
        confirmou = await solicitar_confirmacao_exclusao(update, comando)
        if confirmou:
            return

    screen = None if pular_nativo else await ux.run_experience('handle_text',ux.session_key(update),comando)
    if screen is not None:
        await ux.send_screen(update, screen, sys.modules[__name__], edit=True)
        return

    await enviar_acao_digitando(update, context)

    etapas_feedback = obter_etapas_feedback_visual(comando)
    mensagem_feedback = await iniciar_feedback_visual(update, etapas_feedback)

    if len(etapas_feedback) > 1:
        await atualizar_feedback_visual(mensagem_feedback, etapas_feedback[1])

    resposta_especial = obter_resposta_comando_especial(update, comando)
    if resposta_especial is not None:
        resposta = resposta_especial
    else:
        resposta = await executar_core(processar_mensagem,comando,sessao=chave_sessao_update(update))

    if len(etapas_feedback) > 2:
        await atualizar_feedback_visual(mensagem_feedback, etapas_feedback[2])

    marcar_acesso_seguro(update.effective_user.id if update.effective_user else None)

    if isinstance(resposta, dict) and resposta.get("imagem"):
        await enviar_acao_enviando_foto(update, context)
        if len(etapas_feedback) > 3:
            await atualizar_feedback_visual(mensagem_feedback, etapas_feedback[3])
    elif isinstance(resposta, dict) and resposta.get("arquivo"):
        await enviar_acao_enviando_documento(update, context)

    await finalizar_feedback_visual(mensagem_feedback)
    await enviar_resposta(update, resposta, comando_executado=comando)


def obter_timezone_alertas():
    # Evita dependência do pacote tzdata no Windows.
    # Para o Brasil/São Paulo, UTC-3 é suficiente para os alertas diários,
    # já que não há horário de verão vigente.
    if ASSESSOR_TIMEZONE in ["America/Sao_Paulo", "America/São_Paulo", "BRT", "UTC-3", "UTC-03:00"]:
        return timezone(timedelta(hours=-3), name="America/Sao_Paulo")

    # Fallback conservador: mantém UTC-3 para não quebrar os alertas.
    return timezone(timedelta(hours=-3), name="America/Sao_Paulo")


def interpretar_hora_alerta(valor: str, padrao: str):
    texto = (valor or padrao).strip()

    try:
        hora, minuto = texto.split(":", 1)
        return time(hour=int(hora), minute=int(minuto))
    except Exception:
        hora, minuto = padrao.split(":", 1)
        return time(hour=int(hora), minute=int(minuto))


def obter_chat_id_alertas():
    if ASSESSOR_ALERT_CHAT_ID:
        try:
            return int(ASSESSOR_ALERT_CHAT_ID)
        except ValueError:
            raise RuntimeError("ASSESSOR_ALERT_CHAT_ID precisa ser um número.")

    allowed_user_id = obter_allowed_user_id()

    if allowed_user_id is not None:
        return allowed_user_id

    return None


def segundos_ate_proximo_horario(horario: time, dia_semana: int | None = None):
    tz = obter_timezone_alertas()
    agora = datetime.now(tz)

    alvo = agora.replace(
        hour=horario.hour,
        minute=horario.minute,
        second=0,
        microsecond=0,
    )

    if dia_semana is None:
        if alvo <= agora:
            alvo = alvo + timedelta(days=1)
    else:
        dias_ate = (dia_semana - agora.weekday()) % 7
        alvo = alvo + timedelta(days=dias_ate)

        if alvo <= agora:
            alvo = alvo + timedelta(days=7)

    return max((alvo - agora).total_seconds(), 1)


async def rotina_backup_diario():
    if not ASSESSOR_BACKUP_AUTOMATICO:
        print("Backup automático desativado por ASSESSOR_BACKUP_AUTOMATICO.")
        return

    horario = interpretar_hora_alerta(ASSESSOR_BACKUP_HORA, "03:00")

    # Se o PC estava desligado no horário, o backup diário nunca acontecia.
    # Ao iniciar, recupera: se ainda não existe backup diário com a data de hoje.
    try:
        from services import existe_backup_diario_hoje
        if not await executar_core(existe_backup_diario_hoje):
            await asyncio.sleep(60)
            await executar_core(processar_mensagem, "backup automatico")
            print("Backup automático de recuperação gerado (ainda não havia backup de hoje).")
    except Exception:
        logging.exception("Falha no backup automático de recuperação")

    while True:
        await asyncio.sleep(segundos_ate_proximo_horario(horario))

        try:
            resultado = await executar_core(processar_mensagem,"backup automatico")
            if isinstance(resultado, dict):
                texto = resultado.get("texto", "Backup automático executado.")
            else:
                texto = str(resultado)
            print(texto.splitlines()[0] if texto else "Backup automático executado.")
        except Exception as exc:
            logging.exception("Erro ao gerar backup automático")
            print(f"Erro ao gerar backup automático: {exc}")


async def cancelar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await bloquear_se_nao_autorizado(update):
        return
    key = ux.session_key(update)
    ux.EXPERIENCE.invalidate(key)
    ux.clear_service_pending(key)
    limpar_pendencia_guiada(obter_chat_id_update(update))
    limpar_pendencia_exclusao(obter_chat_id_update(update))
    await update.effective_chat.send_message(message_html('Cancelado. Use /menu para voltar ao início.'), reply_markup=montar_menu_principal(), parse_mode="HTML", **thread_options(update))


async def inicializar_alertas(application):
    from telegram import BotCommand
    try:
        await application.bot.set_my_commands([
            BotCommand('menu', 'Painel e próximos passos'),
            BotCommand('atalhos', 'Abrir teclado de atalhos'),
            BotCommand('mes', 'Resumo do mês atual'),
            BotCommand('registrar', 'Registrar entrada ou despesa'),
            BotCommand('pagar', 'Ver o que falta pagar'),
            BotCommand('historico', 'Consultar lançamentos'),
            BotCommand('saldos', 'Ver saldos por conta'),
            BotCommand('fechamento', 'Resumo e conferência do mês'),
            BotCommand('atencao', 'Ver o que precisa de atenção'),
            BotCommand('help', 'Ajuda por objetivo'),
            BotCommand('aprender', 'Aulas e primeiros passos'),
            BotCommand('dashboard', 'Painel visual do mês'),
            BotCommand('recursos', 'Facilidades, exercícios e comprovantes'),
            BotCommand('cancelar', 'Cancelar a etapa atual'),
            BotCommand('bloquear', 'Bloquear o assessor'),
        ])
    except Exception as exc:
        print('Não foi possível atualizar o menu de comandos:', type(exc).__name__)
    try:
        await application.bot.set_my_description('Controle seu dinheiro com clareza: saldo disponível, contas e faturas, fixos, histórico e previsão do mês. Use /help para encontrar o caminho ou /aprender para começar. Áudio e comprovantes passam por revisão antes de salvar.')
        await application.bot.set_my_short_description('Saldo, faturas e previsão do mês. Registre, confira e aprenda pelo Telegram.')
        from telegram import MenuButtonCommands
        await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except Exception as exc:
        print('Configuração visual do bot não atualizada:',type(exc).__name__)
    # Referência guardada (sem ela o asyncio pode coletar a tarefa) e falha logada.
    from operacao_bot import criar_tarefa_monitorada
    criar_tarefa_monitorada(rotina_backup_diario(), "backup_diario", TAREFAS_FUNDO)
    if obter_chat_id_alertas() is None:
        print('Alertas não iniciados: configure o usuário autorizado e o destino.')
        return
    import telegram_alertas
    criar_tarefa_monitorada(telegram_alertas.rotina(application, sys.modules[__name__]), "alertas", TAREFAS_FUNDO)
    print('Alertas RC3: horários e pausa disponíveis em Mais > Alertas; sem valores nas notificações.')


TAREFAS_FUNDO = set()
UPDATES_PERMITIDOS = ["message", "callback_query"]
# Editar uma mensagem antiga (ex.: /limpar, foto, "apagar 7") não reexecuta nada.
SO_MENSAGEM_NOVA = filters.UpdateType.MESSAGE
UPDATES_VISTOS = {}
MAX_UPDATES_VISTOS = 500


async def descartar_update_repetido(update, context):
    """Dedupe por update_id (B12): reentrega do mesmo update não grava de novo."""
    update_id = getattr(update, "update_id", None)
    if update_id is None:
        return
    if update_id in UPDATES_VISTOS:
        logging.warning("Update %s repetido descartado.", update_id)
        raise ApplicationHandlerStop
    UPDATES_VISTOS[update_id] = True
    if len(UPDATES_VISTOS) > MAX_UPDATES_VISTOS:
        for antigo in list(UPDATES_VISTOS)[: MAX_UPDATES_VISTOS // 2]:
            UPDATES_VISTOS.pop(antigo, None)


CAMINHO_TRAVA_INSTANCIA = Path(__file__).resolve().parent / ".runtime" / "bot.lock"
CAMINHO_LIMITADOR_PIN = Path(__file__).resolve().parent / ".runtime" / "auth_limiter.bin"


async def avisar_erro_ao_titular(update, texto):
    """Aviso curto do tratador global; nunca responde fora da allowlist."""
    if not (usuario_autorizado(update) and contexto_chat_autorizado(update)):
        return
    from telegram_recursos import thread_options
    await update.effective_chat.send_message(message_html(texto), parse_mode="HTML", **thread_options(update))


def ativar_limitador_persistente(caminho=None):
    """Troca o limitador em memória pelo persistido em .runtime (DPAPI).

    Só na subida real do bot: testes que importam app continuam com o
    limitador em memória e não deixam bloqueios gravados em disco.
    """
    global AUTH_LIMITER
    from limitador_persistente import LimitadorPersistente
    AUTH_LIMITER = LimitadorPersistente(
        ASSESSOR_PIN_MAX_ATTEMPTS, ASSESSOR_PIN_LOCK_MINUTES,
        ProtectedJsonStore(Path(caminho or CAMINHO_LIMITADOR_PIN)),
    )
    return AUTH_LIMITER


def validar_configuracao_seguranca():
    token = config.ler("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN não encontrado no arquivo .env")
    allowed_user_id = obter_allowed_user_id()
    if allowed_user_id is None:
        raise RuntimeError("SEGURANÇA V40: TELEGRAM_ALLOWED_USER_ID é obrigatório. O bot não inicia sem allowlist.")
    if ASSESSOR_ALLOW_GROUPS and obter_allowed_chat_id() is None:
        raise RuntimeError("SEGURANÇA V40: grupos exigem ASSESSOR_ALLOWED_CHAT_ID explícito.")
    if not is_hashed_secret(ASSESSOR_PIN_HASH):
        raise RuntimeError("SEGURANÇA V40: PIN protegido é obrigatório. Execute preparar_seguranca_v40.py.")
    pin_len = pin_tamanho_configurado()
    if pin_len < 6 or pin_len > 8:
        raise RuntimeError("SEGURANÇA V40: o PIN deve ter de 6 a 8 dígitos. Execute preparar_seguranca_v40.py.")
    if not is_hashed_secret(ASSESSOR_PIN_RESET_KEY_HASH):
        raise RuntimeError("SEGURANÇA V40: recovery key protegida é obrigatória. Execute preparar_seguranca_v40.py.")
    return token


def main():
    from registro_logs import configurar_logs, avisar_se_fuso_divergente
    configurar_logs("assessor.log")
    avisar_se_fuso_divergente()
    token = validar_configuracao_seguranca()
    from database import verificar_banco_para_iniciar
    motivo = verificar_banco_para_iniciar()
    if motivo:
        raise RuntimeError("BANCO: " + motivo)
    init_db()
    # Instância única: uma segunda janela daria 409 Conflict e estado duplicado.
    from operacao_bot import adquirir_trava_instancia, criar_tratador_erro, InstanciaJaEmExecucao
    try:
        trava = adquirir_trava_instancia(CAMINHO_TRAVA_INSTANCIA)
    except InstanciaJaEmExecucao as exc:
        print(str(exc))
        raise SystemExit(2)
    ativar_limitador_persistente()
    app = ApplicationBuilder().token(token).post_init(inicializar_alertas).build()
    app.add_error_handler(criar_tratador_erro(avisar_erro_ao_titular))
    # Antes de tudo (grupo -1): um update reentregue nunca é processado duas vezes.
    app.add_handler(TypeHandler(Update, descartar_update_repetido), group=-1)

    app.add_handler(CommandHandler("start", start, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("help", help_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("mes", mes_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("registrar", registrar_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("pagar", pagar_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("historico", historico_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("saldos", saldos_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("fechamento", fechamento_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("atencao", atencao_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("aprender", aprender_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("dashboard", dashboard_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("recursos", recursos_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("topicos", topics_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("menu", menu_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("atalhos", atalhos_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("cancelar", cancelar_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("limpar", limpar_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("clear", limpar_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("seguranca", seguranca_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("bloquear", bloquear_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("desbloquear", desbloquear_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("esqueci_pin", esqueci_pin_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("reset", resetarpin_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("resetarpin", resetarpin_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CommandHandler("meuid", meuid_command, filters=SO_MENSAGEM_NOVA))
    app.add_handler(CallbackQueryHandler(callback_submenu))
    app.add_handler(MessageHandler(SO_MENSAGEM_NOVA & filters.TEXT & ~filters.COMMAND, receber_mensagem))
    app.add_handler(MessageHandler(SO_MENSAGEM_NOVA & (filters.VOICE | filters.AUDIO | filters.PHOTO), receber_midia))

    print("Bot iniciado em modo V40 fail-closed com allowlist de usuário/chat e segredos protegidos.")

    try:
        # Só mensagens novas e toques em botões: edited_message, canais, enquetes etc.
        # nem chegam ao bot (B1).
        app.run_polling(allowed_updates=UPDATES_PERMITIDOS)
    finally:
        trava.liberar()


if __name__ == "__main__":
    main()
