#!/usr/bin/env bash
# Instala o Assessor Financeiro num servidor Ubuntu 24.04 (Google Cloud e2-micro gratuito,
# ou qualquer VPS Ubuntu). Rodar como o seu usuário (não root), dentro da pasta do projeto:
#     bash deploy/instalar_servidor.sh            # bot + OCR + áudio
#     bash deploy/instalar_servidor.sh --sem-audio
# Não mexe no banco nem no .env: a migração é um passo separado (deploy/LEIA-ME.md).
set -euo pipefail

PROJETO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHISPER_VERSAO="1.8.3"
MODELO_VOZ="${ASSESSOR_AUDIO_MODELO:-base}"
COM_AUDIO=1
[[ "${1:-}" == "--sem-audio" ]] && COM_AUDIO=0
cd "$PROJETO"

echo "== 0/6 Memória de troca (máquinas de 1 GB precisam para compilar e rodar com folga)"
MEM_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
if [[ $MEM_MB -lt 3000 ]] && ! swapon --show | grep -q .; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile >/dev/null
    sudo swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
    echo "   swap de 2 GB criado (memória: ${MEM_MB} MB)"
fi

echo "== 1/6 Pacotes do sistema"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    git curl sqlite3 ffmpeg tesseract-ocr tesseract-ocr-por rclone \
    build-essential cmake unattended-upgrades
sudo timedatectl set-timezone America/Sao_Paulo || true   # só para logs; o assessor usa UTC-3 fixo

echo "== 2/6 Python 3.13 (uv) e dependências"
if ! command -v uv >/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
uv python install 3.13
[[ -d .venv ]] || uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements-tooling.txt -r requirements.txt -r requirements-audio.txt
.venv/bin/python -m pip check

echo "== 3/6 Pastas privadas"
mkdir -p data backups exports dashboards imports logs .runtime
chmod 700 data backups .runtime

if [[ $COM_AUDIO == 1 ]]; then
    echo "== 4/6 Voz local (whisper.cpp $WHISPER_VERSAO, modelo $MODELO_VOZ)"
    RT="$PROJETO/.runtime/whispercpp"
    if [[ ! -x "$RT/bin/whisper-cli" ]]; then
        TMP="$(mktemp -d)"
        git clone -q --depth 1 --branch "v$WHISPER_VERSAO" https://github.com/ggml-org/whisper.cpp "$TMP/w"
        cmake -S "$TMP/w" -B "$TMP/w/build" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF >/dev/null
        cmake --build "$TMP/w/build" -j1 --target whisper-cli >/dev/null   # -j1: cabe em 1 GB + swap
        mkdir -p "$RT/bin" "$RT/models"
        cp "$TMP/w/build/bin/whisper-cli" "$RT/bin/whisper-cli"
        rm -rf "$TMP"
    fi
    [[ -f "$RT/models/ggml-$MODELO_VOZ.bin" ]] || \
        curl -fL -o "$RT/models/ggml-$MODELO_VOZ.bin" \
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$MODELO_VOZ.bin"
else
    echo "== 4/6 Voz local: pulada (--sem-audio)"
fi

echo "== 5/6 Serviço systemd (sobe com o servidor e reinicia se cair)"
sed -e "s#__PROJETO__#$PROJETO#g" -e "s#__USUARIO__#$(whoami)#g" deploy/assessor.service \
    | sudo tee /etc/systemd/system/assessor.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable assessor.service >/dev/null
echo "   Serviço instalado e habilitado (ainda NÃO iniciado)."

echo "== 6/6 Conferência"
.venv/bin/python -c "import cryptography, telegram, PIL; print('Python OK:', __import__('sys').version.split()[0])"
tesseract --list-langs 2>/dev/null | grep -q '^por$' && echo "OCR português OK"
command -v rclone >/dev/null && echo "rclone OK"
cat <<'FIM'

Pronto. Próximos passos (deploy/LEIA-ME.md):
  1. Rodar o gate oficial aqui:  .venv/bin/python validacao/validar_versao_oficial.py --workers 1 --timeout 5400 --saida ~/gate
  2. Migrar banco e .env do PC (com o bot do PC PARADO).
  3. sudo systemctl start assessor && journalctl -u assessor -f
FIM
