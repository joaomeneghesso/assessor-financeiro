# Assessor na nuvem (Google Cloud, máquina e2-micro gratuita)

Objetivo: o bot roda num servidor que nunca desliga, sobe sozinho e reinicia se
cair. O projeto do PC (`C:\Projetos\assessor-financeiro`) fica intacto como
reserva: se algo der errado, para o servidor e liga o PC de novo.

> Só um bot pode ler o Telegram por vez. Depois da migração, **não** inicie o
> assessor no PC enquanto o servidor estiver ligado.

(A Oracle "Always Free" foi descartada em 14/11/2026: no Brasil passou a aceitar
só cadastro de empresa, com CNPJ ativo.)

## Parte 1 — Conta e servidor (você)

1. <https://console.cloud.google.com/> com a sua conta Google → aceite os termos →
   **Activate / Começar a avaliação gratuita**: país Brasil, tipo **Individual**,
   cartão para verificação.
2. **Ative a conta completa** (botão "Activate full account" / "Ativar conta
   completa" no topo). Sem isso, a máquina para quando acabar a avaliação de
   90 dias. Dentro do limite gratuito o custo continua R$ 0.
3. **Billing → Budgets & alerts → Create budget**: US$ 1, alertas em 50% e 100%.
4. **Compute Engine → VM instances → Create instance** (ative a API se pedir):
   - Name: `assessor`
   - **Region: us-central1 (Iowa)** (ou us-west1 / us-east1). Outra região é cobrada.
   - Machine: **E2 → e2-micro**
   - Boot disk → **Change**: **Ubuntu 24.04 LTS (x86/64)**,
     **Disk type: Standard persistent disk** (não "Balanced": é cobrado), **30 GB**.
   - Firewall: deixe **desmarcados** HTTP e HTTPS (o bot não recebe conexões).
   - **Advanced → Security → Manage access → Add item (SSH key)**: cole a chave
     pública que o Claude gerou, que termina em ` assessor`
     (o usuário do servidor será `assessor`).
   - Observability / Data protection: **desligue** snapshots e backups agendados
     (são cobrados; o assessor já faz backup cifrado próprio).
   - Networking: IP externo **Ephemeral** (padrão). **Não** reserve IP estático.
5. **Create**. Quando aparecer o **External IP**, mande para o Claude.

## Parte 2 — Instalação (Claude, com sua aprovação em cada comando)

1. Envia o código (branch `nuvem`) por `git bundle` + `scp` e clona em
   `~/assessor-financeiro`.
2. `bash deploy/instalar_servidor.sh` — swap de 2 GB, pacotes, Python 3.13, OCR
   (Tesseract português), voz (whisper.cpp), serviço systemd (habilitado, ainda parado).
3. Gate oficial no próprio servidor (Linux de verdade; demora, 1 worker):
   `.venv/bin/python validacao/validar_versao_oficial.py --workers 1 --timeout 5400 --saida ~/gate`

## Parte 3 — Migração (você roda os comandos com dados reais)

1. **Pare o bot no PC** (feche a janela).
2. No PC, gere um backup consistente: `.\backup_db.ps1` (mostra o arquivo criado em `backups\`).
3. Envie banco e configuração (PowerShell do PC, na pasta do projeto):

   ```powershell
   scp -i $HOME\.ssh\assessor_nuvem backups\<arquivo-mostrado>.db assessor@IP:assessor-financeiro/data/financeiro.db
   scp -i $HOME\.ssh\assessor_nuvem .env assessor@IP:assessor-financeiro/.env
   ```
4. No servidor, no `.env`: deixe `ASSESSOR_IA_LOCAL_MODELO=` **vazio** (não há
   Ollama em 1 GB). Depois:
   `chmod 600 ~/assessor-financeiro/.env ~/assessor-financeiro/data/financeiro.db`
   e `sudo systemctl enable --now assessor` (liga agora e a cada reinício do
   servidor; até a migração o serviço fica desabilitado de propósito, para não
   ficar reiniciando sem token). Mande `/menu` no Telegram.
5. Acompanhar: `journalctl -u assessor -f` (Ctrl+C sai sem parar o bot).

## Parte 4 — Backup cifrado do servidor para o OneDrive

1. No servidor, no `.env`:
   ```
   ASSESSOR_BACKUP_EXTERNO_DIR=/home/assessor/assessor-backups-cifrados
   ASSESSOR_BACKUP_EXTERNO_RCLONE=onedrive:Backups/Assessor
   ```
2. Autorize o OneDrive para o rclone: baixe o rclone para Windows
   (<https://rclone.org/downloads/>), rode `rclone authorize "onedrive"` no PC
   (abre o navegador para você entrar na Microsoft) e cole o token no
   `rclone config` do servidor (remote chamado `onedrive`).
3. `.venv/bin/python backup_externo_cli.py configurar` no servidor (pode usar a
   mesma senha do PC). A cópia fica no servidor e vai para o OneDrive.
   Tráfego: ~6 MB/dia, dentro de 1 GB/mês gratuito.

## Voltar para o PC (plano B)

`sudo systemctl stop assessor` no servidor → copie o banco do servidor para o
PC (`scp -i $HOME\.ssh\assessor_nuvem assessor@IP:assessor-financeiro/data/financeiro.db ...`)
→ inicie o bot no PC.

## Segurança do servidor

- Acesso só por chave SSH (sem login por senha); usuário `assessor`.
- Nenhuma porta aberta além da 22 (SSH): o bot só faz conexões de saída.
- Opcional: na regra de firewall `default-allow-ssh`, limitar a origem ao seu IP.
- Atualizações de segurança automáticas (`unattended-upgrades`).
- `.env`, banco e `.runtime` com permissão só do dono; serviço com `UMask=0077`.
- Disco do Google é cifrado em repouso; o backup externo é cifrado com a sua senha.
