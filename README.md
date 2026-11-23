# Assessor Financeiro

Assistente financeiro pessoal que funciona inteiramente pelo **Telegram**: registra gastos, entradas, contas fixas, faturas de cartão e parcelamentos, e responde perguntas como "quanto gastei com alimentação nos últimos 3 meses?" ou "quanto vou pagar de cartão em dezembro?". Uso real e diário desde 2026, rodando 24 h num servidor gratuito do Google Cloud.

> Projeto pessoal, escrito em Python e em português. Este repositório é uma cópia pública **sem nenhum dado real**: banco, segredos, backups e valores pessoais foram removidos, e os exemplos dos testes são fictícios.

## Destaques

- **~37 mil linhas de Python** em 61 módulos, com **~1.390 testes automatizados** (unittest) que rodam num gate oficial antes de qualquer publicação.
- **Nada financeiro grava sem prévia e confirmação.** Toda correção ou exclusão mostra o "antes → depois" e só grava com confirmação explícita; "sim" solto não confirma nada. Exclusões fazem backup antes.
- **Dinheiro em `Decimal`** (2 casas, arredondamento HALF_UP) em um ponto único de entrada (`money.py`).
- **Regras de negócio reais de cartão de crédito:** competência de fatura com dia de corte, compras no dia do corte, parcelamentos, estornos, pagamento de fatura que nunca conta como gasto, conciliação de lançamentos com contas fixas.
- **Saldo honesto entre meses:** só o realizado é herdado; receita prevista e não recebida aparece separada (ver [regra de herança](docs/reavaliacao/06_regra_heranca.md)).
- **Interpretação de linguagem natural sem IA** para consultas por período e categoria (`consultas_rapidas.py`). Uma IA local (Ollama) é usada só para roteamento de intenção e nunca grava nada.
- **Mídia:** leitura de comprovantes por OCR (Tesseract) e mensagens de voz transcritas localmente (whisper.cpp). Nada vindo de mídia grava sem revisão.

## Segurança

- Whitelist de usuário e chat que **falha fechado**.
- PIN de 6 a 8 dígitos (hash PBKDF2) para ações sensíveis, com bloqueio automático após 15 minutos e limitador de tentativas persistente.
- Callbacks de botão com validade (10 min para telas, 24 h para comandos) e estado efêmero cifrado.
- Backup diário local e **cópia externa cifrada** (AES-256-GCM, chave derivada com scrypt), conferida a cada geração.
- Testes isolados: o gate aborta se algum teste tentar tocar o banco real.

## Arquitetura

```
Telegram ──► app.py (entrada, whitelist, PIN, jobs)
               │
               ├─► telegram_experiencia.py   telas, sessão, botões (UX)
               ├─► telegram_*.py             design, mídia, alertas, gravação idempotente
               │
               ▼
           services.py  ── roteador de comandos e camada de negócio
               │
               ├─► núcleo: compromissos, conciliação, faturas_competencia,
               │           saldo_resumo, pagamentos_canonicos, fixos_*
               ├─► consultas_rapidas, busca_lancamentos
               ▼
           database.py ── SQLite (WAL), auditoria, transações BEGIN IMMEDIATE
           migrations/ ── migrations versionadas com checksum
```

- **Relógio único** (`relogio.py`, UTC-3 fixo) e **configuração única** (`config.py`): nenhum outro módulo lê o ambiente ou a hora diretamente. Um teste de arquitetura garante isso.
- **Linha de base de arquitetura** (`tests/test_arquitetura_linha_de_base.py`): trava o tamanho dos maiores módulos, funções longas, ciclos de import, SQL fora de `database.py` e relógio fora de `relogio.py`. Os limites só podem diminuir.
- **Mapa de rotas** gerado do código: todo comando, botão, tela e estado de sessão e para onde leva ([`docs/mapa/`](docs/mapa/LEIA-ME.md)).
- **Documentação navegável em Obsidian:** abra a pasta `docs/` como cofre e comece por `00 Início.md`. As notas de cada módulo (`docs/codigo/`) são geradas por análise estática (`tools/gerar_vault_codigo.py`).

## Qualidade e processo

- **Gate oficial** (`validacao/validar_versao_oficial.py`): roda toda a suíte em paralelo, em banco temporário, inclusive com **relógio falso** (`--data AAAA-MM-DD`) para testar viradas de mês e de ano.
- Todo bug corrigido ganha um teste de regressão. A correção é sempre mínima, sem refatoração no mesmo passo.
- **Migrations manuais** (`migrations.py status | validate | dry-run | migrate`) com backup antes.
- **Deploy com volta automática:** `deploy/publicar.ps1` roda o gate, faz backup do banco no servidor, envia, reinicia e confere. Se o bot não subir, volta à versão anterior sozinho.
- Uma reavaliação técnica completa do projeto está em [`docs/reavaliacao/`](docs/reavaliacao/00_veredito.md), com o veredito de profissionalizar por etapas em vez de reescrever.
- Desenvolvido com apoio do **Claude Code**: instruções do projeto em `CLAUDE.md`, subagentes de auditoria e skills de processo em `.claude/`.

## Stack

Python 3.13 · python-telegram-bot 22 · SQLite · Pillow · cryptography · Tesseract (OCR) · whisper.cpp (voz) · Ollama (opcional) · Google Cloud e2-micro (Debian, systemd)

## Como rodar

Instruções completas em [`docs/OPERACAO.md`](docs/OPERACAO.md) (Windows) e [`deploy/LEIA-ME.md`](deploy/LEIA-ME.md) (servidor Linux). Resumo:

```powershell
.\instalar.ps1                     # cria o .venv e copia .env.example para .env
# preencha TELEGRAM_BOT_TOKEN e TELEGRAM_ALLOWED_USER_ID no .env
.\.venv\Scripts\python.exe preparar_seguranca_v40.py
.\iniciar.ps1
```

Para rodar os testes:

```powershell
.\.venv\Scripts\python.exe .\validacao\validar_versao_oficial.py --workers 4 --saida $env:TEMP\assessor-validacao
```

## Autor

João Meneghesso · [github.com/joaomeneghesso](https://github.com/joaomeneghesso)
