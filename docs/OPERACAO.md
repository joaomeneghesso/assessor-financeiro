# Assessor Financeiro

Assessor financeiro **pessoal** (um único titular), em português. É composto por:

- um **bot Telegram** para registrar e consultar gastos, fixos, faturas e saldos;
- um banco **SQLite** local (`data/financeiro.db`).

Nada financeiro é gravado sem confirmação do titular. A versão atual está em `version.py`.

## Requisitos

- Windows 10/11 com PowerShell.
- Python 3 (o `instalar.ps1` cria o ambiente `.venv` com o `python` do PATH; use uma versão 3.13 ou compatível com as dependências fixadas em `requirements.txt`).
- Um bot do Telegram (token) e o ID numérico do titular.

## Instalação

```powershell
.\instalar.ps1
```

O script cria o `.venv`, instala `requirements-tooling.txt` e `requirements.txt` e, se não existir `.env`, copia `.env.example` para `.env`. Depois:

1. Edite `.env`: preencha `TELEGRAM_BOT_TOKEN` e `TELEGRAM_ALLOWED_USER_ID`.
2. Rode `python preparar_seguranca_v40.py` (do `.venv`) para gerar os hashes do PIN e da chave de recuperação.
3. Opcional, voz local: `.\instalar_audio.ps1` (whisper.cpp + FFmpeg portátil).

O `.env` contém segredos: nunca o versione nem o compartilhe.

## Iniciar e parar

| Script | O que faz |
|---|---|
| `.\iniciar.ps1` | Inicia o bot Telegram |
| `iniciar_assessor_completo.bat` | Inicia o bot Telegram numa janela própria (atalho de duplo clique) |

Para parar, feche a janela ou pressione `Ctrl+C`. Só pode haver **uma instância do bot**: uma segunda é recusada por uma trava em `.runtime/bot.lock`.

## Backup e restauração

- Backup automático diário às 03:00 (`ASSESSOR_BACKUP_HORA` / `ASSESSOR_BACKUP_AUTOMATICO` no `.env`).
- O comando `backup` no bot exige PIN.
- Manual: `.\backup_db.ps1`. Os arquivos ficam em `backups/`.
- **Cópia fora do computador (OneDrive), criptografada:** depois de cada backup diário, o bot grava em `%USERPROFILE%\OneDrive\Backups\Assessor` um pacote `.assessor-bkp` com banco, código (git) e `.env`, cifrado com a sua senha (AES-256-GCM). Cada cópia é conferida ao ser gravada; ficam as 30 mais recentes.
  - Ativar (uma vez, no seu terminal): `.\.venv\Scripts\python.exe backup_externo_cli.py configurar`. **Guarde a senha no seu gerenciador de senhas**: sem ela nenhum pacote abre.
  - Conferir: `backup_externo_cli.py status` e `backup_externo_cli.py verificar` (testa a restauração sem gravar nada).
  - Restaurar: `backup_externo_cli.py restaurar <arquivo> <pasta-nova>`; num computador novo, siga o `LEIA-ME.txt` da pasta do OneDrive.

Restauração (manual e segura; não há script de restauração):

1. Pare o bot.
2. Guarde uma cópia do banco atual (`data/financeiro.db`, e `-wal`/`-shm` se existirem).
3. Copie o backup escolhido sobre `data/financeiro.db`.
4. Rode `.\.venv\Scripts\python.exe migrations.py status` para conferir a versão do esquema.
5. Inicie o bot e confira os saldos.

## Migrations

Manuais, nunca automáticas:

```powershell
.\.venv\Scripts\python.exe migrations.py status | validate | dry-run | migrate
```

Faça sempre um backup (`backup_db.ps1`) antes de `migrate`. Migrations aplicadas não se editam e as mais recentes não têm rollback: a volta é por backup.

## Testes

Gate oficial (suíte unittest em banco temporário; `--workers` paraleliza, `--data AAAA-MM-DD` usa relógio falso):

```powershell
.\.venv\Scripts\python.exe .\validacao\validar_versao_oficial.py --workers 4 --timeout 1500 --saida $env:TEMP\assessor-validacao
```

Teste isolado (pytest não é usado):

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_<modulo> -v
```

Os testes nunca devem tocar o banco real; reproduza problemas em banco temporário.

## Logs

Pasta `logs/`, arquivos rotativos (1 MB x 5), `assessor.log` (bot). Logs podem conter dados pessoais: não os compartilhe.

## Segurança em resumo

- Whitelist de usuário/chat do Telegram; falha fechado. Por padrão só conversa privada.
- PIN (6–8 dígitos, hash PBKDF2) para ações sensíveis; bloqueio automático após inatividade (15 min) e limite de tentativas.
- Estado efêmero protegido pelo DPAPI do Windows.
- O limite de tentativas de PIN fica salvo em `.runtime/` e continua valendo após reiniciar o bot.
- Edições digitadas (`mudar`, `corrigir`, `meta`, fixos, entradas) mostram a prévia antes → depois e só gravam com o botão ou `confirmar alteracao`.
- Exclusões exigem prévia, confirmação explícita (botão ou `confirmar exclusao`) e backup prévio.
- Backup e CSV só são enviados ao chat com PIN válido e com proteção contra encaminhamento.

## Documentação

- `CHANGELOG.md`: histórico de versões.
- `docs/`: auditorias e decisões.
- `docs/BUGS_CONHECIDOS.md`: backlog priorizado.
- `docs/mapa/`: mapa interativo de rotas, menus e botões.
- `CLAUDE.md`: guia de arquitetura e regras do projeto.
