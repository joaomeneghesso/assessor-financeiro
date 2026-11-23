"""Cópia diária criptografada do assessor FORA do computador (OneDrive por padrão).

Decisão do titular em 13/11/2026: destino OneDrive; o pacote leva banco, código
(repositório git inteiro, em ``git bundle``) e ``.env``, tudo cifrado com a senha
dele. Sem a senha ninguém lê o arquivo, nem a Microsoft.

Formato do arquivo ``assessor_AAAAMMDD_HHMMSS.assessor-bkp``::

    MAGIC (13 bytes) | sal (16) | nonce (12) | AES-256-GCM(zip)

Chave = scrypt(senha, sal, n=2**15, r=8, p=1). O zip contém ``financeiro.db``,
``assessor.bundle`` (quando o git está disponível), ``env.txt`` (quando há
``.env``), ``MANIFESTO.json`` (versão, data, SHA-256) e ``LEIA-ME.txt``.

A senha é escolhida pelo titular em ``backup_externo_cli.py configurar`` (no
terminal dele) e guardada neste computador só protegida pelo DPAPI do Windows
(``.runtime/backup_externo.bin``), para a cópia diária rodar sozinha. Para
restaurar em OUTRO computador, só a senha que o titular guardou no gerenciador
de senhas abre o arquivo.

Este módulo não importa ``services``: ``services.gerar_backup_automatico`` chama
``gerar_se_configurado`` com o backup local que acabou de validar.
"""
import hashlib
import io
import json
import logging
import os
import sqlite3
import subprocess
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path

import config
import relogio
from estado_runtime import ProtectedJsonStore

MAGIC = b'ASSESSOR-BKP1'
EXTENSAO = '.assessor-bkp'
MANTER = 30
SENHA_MINIMA = 12
_SCRYPT = dict(n=2 ** 15, r=8, p=1, maxmem=2 ** 26, dklen=32)
RAIZ = config.BASE_DIR
ARQUIVO_SENHA = config.RUNTIME_DIR / 'backup_externo.bin'
ARQUIVO_STATUS = config.RUNTIME_DIR / 'backup_externo_status.json'

LEIA_ME = """Backup do Assessor Financeiro (criptografado)

Cada arquivo .assessor-bkp é uma cópia completa: banco de dados, código (git) e
configuração (.env). Ele só abre com a senha do backup externo, guardada pelo
titular no gerenciador de senhas.

Para restaurar num computador novo:
1. Instale Python 3.13 e Git; num terminal: python -m pip install cryptography
2. Salve as 6 linhas abaixo como abrir_backup.py e rode:
   python abrir_backup.py <arquivo.assessor-bkp>
   (pede a senha e grava pacote.zip na pasta atual)
3. Descompacte pacote.zip e siga:
   - Código: git clone assessor.bundle assessor-financeiro
   - Banco: copie financeiro.db para assessor-financeiro\\data\\financeiro.db
   - Configuração: copie env.txt para assessor-financeiro\\.env
   - Na pasta assessor-financeiro: .\\instalar.ps1 e depois .\\iniciar.ps1
   - Configure o backup externo de novo: python backup_externo_cli.py configurar

--- abrir_backup.py ---
import hashlib, sys, getpass
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
d = open(sys.argv[1], 'rb').read(); M = b'ASSESSOR-BKP1'; c = d[len(M):]
k = hashlib.scrypt(getpass.getpass('Senha: ').encode(), salt=c[:16], n=2**15, r=8, p=1, maxmem=2**26, dklen=32)
open('pacote.zip', 'wb').write(AESGCM(k).decrypt(c[16:28], c[28:], M))
print('pacote.zip gravado')
--- fim ---

Este LEIA-ME não contém senha nem dados financeiros.
"""


class BackupExternoErro(Exception):
    pass


def destino():
    configurado = config.ler('ASSESSOR_BACKUP_EXTERNO_DIR', '').strip()
    return Path(configurado) if configurado else Path.home() / 'OneDrive' / 'Backups' / 'Assessor'


def _store():
    return ProtectedJsonStore(ARQUIVO_SENHA)


def configurado():
    return bool(_store().load().get('senha'))


def salvar_senha(senha):
    senha = str(senha or '')
    if len(senha) < SENHA_MINIMA:
        raise BackupExternoErro(f'A senha precisa ter pelo menos {SENHA_MINIMA} caracteres.')
    if not _store().save({'senha': senha}):
        raise BackupExternoErro('Não consegui proteger a senha com o DPAPI do Windows.')


def _senha_salva():
    senha = _store().load().get('senha')
    if not senha:
        raise BackupExternoErro('Backup externo não configurado.')
    return senha


# ----------------------------------------------------------------------------- cifra
def _chave(senha, sal):
    return hashlib.scrypt(senha.encode('utf-8'), salt=sal, **_SCRYPT)


def cifrar(dados, senha):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    sal, nonce = os.urandom(16), os.urandom(12)
    return MAGIC + sal + nonce + AESGCM(_chave(senha, sal)).encrypt(nonce, dados, MAGIC)


def decifrar(conteudo, senha):
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if not conteudo.startswith(MAGIC) or len(conteudo) < len(MAGIC) + 28 + 16:
        raise BackupExternoErro('Arquivo não é um backup do assessor.')
    corpo = conteudo[len(MAGIC):]
    sal, nonce, cifrado = corpo[:16], corpo[16:28], corpo[28:]
    try:
        return AESGCM(_chave(senha, sal)).decrypt(nonce, cifrado, MAGIC)
    except InvalidTag as exc:
        raise BackupExternoErro('Senha errada ou arquivo corrompido.') from exc


# ----------------------------------------------------------------------------- pacote
def _git_bundle(pasta_tmp):
    """Repositório inteiro num arquivo; None se o git não estiver disponível (o resto segue)."""
    if not (RAIZ / '.git').exists():
        return None
    alvo = Path(pasta_tmp) / 'assessor.bundle'
    try:
        r = subprocess.run(['git', 'bundle', 'create', str(alvo), '--all'], cwd=RAIZ,
                           capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        logging.warning('Backup externo: git indisponível; pacote segue sem o código.', exc_info=True)
        return None
    return alvo if r.returncode == 0 and alvo.exists() else None


def montar_pacote(banco):
    """Zip em memória com banco, código, .env, manifesto e leia-me."""
    from version import VERSION
    banco = Path(banco)
    manifesto = {'versao': VERSION, 'criado_em': relogio.agora().isoformat(timespec='seconds'), 'arquivos': {}}
    memoria = io.BytesIO()
    with tempfile.TemporaryDirectory(prefix='assessor_bkp_') as tmp, \
            zipfile.ZipFile(memoria, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        itens = [('financeiro.db', banco), ('assessor.bundle', _git_bundle(tmp)), ('env.txt', config.ENV_PATH)]
        for nome, origem in itens:
            if origem is None or not Path(origem).is_file():
                continue
            dados = Path(origem).read_bytes()
            manifesto['arquivos'][nome] = hashlib.sha256(dados).hexdigest()
            z.writestr(nome, dados)
        if 'financeiro.db' not in manifesto['arquivos']:
            raise BackupExternoErro('Backup local não encontrado para empacotar.')
        z.writestr('MANIFESTO.json', json.dumps(manifesto, ensure_ascii=False, indent=2))
        z.writestr('LEIA-ME.txt', LEIA_ME)
    return memoria.getvalue(), manifesto


def conferir_pacote(conteudo, senha):
    """Decifra, confere os SHA-256 do manifesto e roda quick_check no banco (sem gravar nada fora do temp)."""
    zip_bytes = decifrar(conteudo, senha)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        manifesto = json.loads(z.read('MANIFESTO.json'))
        for nome, sha in manifesto['arquivos'].items():
            if hashlib.sha256(z.read(nome)).hexdigest() != sha:
                raise BackupExternoErro(f'{nome} não confere com o manifesto.')
        with tempfile.TemporaryDirectory(prefix='assessor_bkp_chk_') as tmp:
            db = Path(tmp) / 'financeiro.db'
            db.write_bytes(z.read('financeiro.db'))
            with closing(sqlite3.connect(db)) as conn:
                if conn.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                    raise BackupExternoErro('Banco dentro do pacote não passou no quick_check.')
    return manifesto


def _rotacionar(pasta):
    arquivos = sorted(pasta.glob('assessor_*' + EXTENSAO), key=lambda p: p.name, reverse=True)
    for antigo in arquivos[MANTER:]:
        try:
            antigo.unlink()
        except OSError:
            logging.warning('Backup externo antigo não pôde ser removido: %s', antigo.name, exc_info=True)


def remoto_rclone():
    """Servidor sem OneDrive instalado: destino rclone (ex.: 'onedrive:Backups/Assessor'); '' = não enviar."""
    return config.ler('ASSESSOR_BACKUP_EXTERNO_RCLONE', '').strip()


def _enviar_rclone(*arquivos):
    """Envia os arquivos (já cifrados) ao remoto rclone e apaga lá os pacotes com mais de 45 dias."""
    remoto = remoto_rclone()
    if not remoto:
        return
    try:
        for arquivo in arquivos:
            r = subprocess.run(['rclone', 'copy', str(arquivo), remoto], capture_output=True, text=True, timeout=600)
            if r.returncode:
                raise BackupExternoErro(f'rclone não enviou {Path(arquivo).name}: {r.stderr.strip()[-150:]}')
        subprocess.run(['rclone', 'delete', remoto, '--min-age', '45d', '--include', 'assessor_*' + EXTENSAO],
                       capture_output=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BackupExternoErro(f'rclone indisponível: {exc}') from exc


def gerar(banco, senha=None):
    """Grava o pacote cifrado no destino, relê e confere; devolve o caminho."""
    senha = senha or _senha_salva()
    pasta = destino()
    pasta.mkdir(parents=True, exist_ok=True)
    pacote, manifesto = montar_pacote(banco)
    conteudo = cifrar(pacote, senha)
    nome = 'assessor_' + relogio.agora().strftime('%Y%m%d_%H%M%S') + EXTENSAO
    final, temporario = pasta / nome, pasta / (nome + '.tmp')
    try:
        temporario.write_bytes(conteudo)
        conferir_pacote(temporario.read_bytes(), senha)  # restauração testada a cada cópia
        temporario.replace(final)
    finally:
        temporario.unlink(missing_ok=True)
    (pasta / 'LEIA-ME.txt').write_text(LEIA_ME, encoding='utf-8')
    _rotacionar(pasta)
    _enviar_rclone(final, pasta / 'LEIA-ME.txt')
    _gravar_status({'ultimo_ok': manifesto['criado_em'], 'arquivo': nome,
                    'com_codigo': 'assessor.bundle' in manifesto['arquivos'],
                    'com_env': 'env.txt' in manifesto['arquivos']})
    return final


def _gravar_status(dados):
    try:
        atual = json.loads(ARQUIVO_STATUS.read_text(encoding='utf-8')) if ARQUIVO_STATUS.is_file() else {}
        atual.update(dados)
        ARQUIVO_STATUS.parent.mkdir(parents=True, exist_ok=True)
        ARQUIVO_STATUS.write_text(json.dumps(atual, ensure_ascii=False), encoding='utf-8')
    except (OSError, ValueError):
        logging.warning('Backup externo: status não gravado.', exc_info=True)


def status():
    try:
        return json.loads(ARQUIVO_STATUS.read_text(encoding='utf-8')) if ARQUIVO_STATUS.is_file() else {}
    except (OSError, ValueError):
        return {}


def gerar_se_configurado(banco):
    """Gancho do backup diário: nunca levanta erro; devolve uma linha de status (ou '' se não configurado)."""
    if not configurado():
        return ''
    try:
        caminho = gerar(banco)
        return f'\n☁️ Cópia criptografada no OneDrive: {caminho.name}'
    except Exception as exc:
        logging.exception('Backup externo falhou')
        _gravar_status({'ultima_falha': relogio.agora().isoformat(timespec='seconds'), 'erro': str(exc)[:200]})
        return f'\n⚠️ Cópia externa falhou: {str(exc)[:120]}'


def linha_status():
    """Uma linha para a resposta do comando backup (sem dados sensíveis)."""
    if not configurado():
        return 'Cópia externa: não configurada (rode backup_externo_cli.py configurar).'
    s = status()
    if s.get('ultima_falha') and s.get('ultima_falha', '') > s.get('ultimo_ok', ''):
        return f'⚠️ Cópia externa: última tentativa falhou em {s["ultima_falha"][:16].replace("T", " ")}.'
    if s.get('ultimo_ok'):
        return f'Cópia externa (OneDrive): {s["ultimo_ok"][:16].replace("T", " ")}.'
    return 'Cópia externa: configurada; a primeira sai no próximo backup automático.'


def restaurar(arquivo, pasta_nova, senha):
    """Extrai o pacote numa pasta NOVA (nunca sobrescreve) e escreve RESTAURAR.txt."""
    pasta_nova = Path(pasta_nova)
    if pasta_nova.exists() and any(pasta_nova.iterdir()):
        raise BackupExternoErro('A pasta de destino precisa ser nova ou vazia. Nada foi extraído.')
    manifesto = conferir_pacote(Path(arquivo).read_bytes(), senha)
    pasta_nova.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(decifrar(Path(arquivo).read_bytes(), senha))) as z:
        z.extractall(pasta_nova)
    (pasta_nova / 'RESTAURAR.txt').write_text(
        'Restauração do Assessor Financeiro\n\n'
        f'Pacote da versão {manifesto["versao"]}, criado em {manifesto["criado_em"]}.\n\n'
        '1. Código: git clone assessor.bundle assessor-financeiro\n'
        '2. Banco: copie financeiro.db para assessor-financeiro\\data\\financeiro.db\n'
        '3. Configuração: copie env.txt para assessor-financeiro\\.env\n'
        '4. Na pasta assessor-financeiro: .\\instalar.ps1 e depois .\\iniciar.ps1\n'
        '5. Rode backup_externo_cli.py configurar de novo neste computador.\n'
        '\nNunca rode dois bots ao mesmo tempo com o mesmo token.\n', encoding='utf-8')
    return manifesto
