# Assessor Financeiro — guia para o Claude

Assessor financeiro **pessoal** (um único titular), em português. Só bot Telegram (o painel web foi removido em 13/11/2026), banco SQLite. Windows 11, PowerShell. Versão atual: ver `version.py` (4.2.0).

## Regras inegociáveis
- **Nunca** abra, leia ou escreva `data/*.db`, `.env`, `.runtime/*.bin`, `backups/`, `dashboards/*.png`, `trash_assessor/`: são dados e segredos reais. Para inspecionar dados use o MCP `assessor-db` (somente leitura) ou uma cópia temporária.
- Testes **nunca** tocam `data/financeiro.db` (o gate aborta se tentarem). Reproduza bugs em banco temporário.
- Não faça commit, push nem aplique migration em banco real sem o usuário pedir. Antes de qualquer migration real: backup (`backup_db.ps1`).
- Nada financeiro grava sem confirmação do titular; exclusão exige prévia + confirmação + backup prévio.
- Dinheiro entra por `money.parse_money` (Decimal, 2 casas, HALF_UP). Não introduza novo `float` em cálculo monetário.
- Correção por texto (`mudar`, `corrigir valor|conta|forma`, `meta`, edições de fixo) e exclusões abrem prévia e só gravam com `confirmar alteracao`/`confirmar exclusao` ou o botão vinculado; "sim" solto não confirma nada.
- Herança de saldo entre meses considera só o realizado; receita prevista não recebida aparece separada (ver `docs/reavaliacao/06_regra_heranca.md`).
- Correção mínima: não refatore junto com bugfix. Todo bug corrigido ganha teste de regressão.

## Comandos
```powershell
# Gate oficial (único caminho aceito; suíte unittest). --workers paraleliza; --timeout em segundos; --data AAAA-MM-DD usa relógio falso
.\.venv\Scripts\python.exe .\validacao\validar_versao_oficial.py --workers 6 --timeout 1200 --saida $env:TEMP\assessor-validacao
# Teste isolado (pytest NÃO está instalado). tests/__init__.py isola banco, backups e .runtime; no discover use sempre -t .
.\.venv\Scripts\python.exe -m unittest tests.test_<modulo> -v
# Iniciar o bot
.\iniciar.ps1        # ou iniciar_assessor_completo.bat
# Migrations (manuais, nunca automáticas)
.\.venv\Scripts\python.exe migrations.py status | validate | dry-run | migrate
```
Não rode `unittest discover` em `validacao/tests` nem `validacao/testes_v39` (dependem do layout temporário do gate; `validacao/tests` é snapshot antigo).

## Arquitetura (arquivo → papel)
- `app.py` (~5300 linhas): entrada do bot, whitelist, PIN, pendências legadas, jobs de backup/alertas, `main()`.
- `telegram_experiencia.py` (~4400): UX 2.0 (`Experience`, `Session`, telas, `dispatch_text/callback`). Outros `telegram_*`: design (HTML/botões), visuais (PNG/PIL), midia (foto/áudio/OCR), recursos, registros (gravação idempotente/desfazer), alertas, aprendizado, streaming, execucao (executor de 1 worker).
- `services.py` (~11000 linhas, 337 funções): camada de negócio e roteador de comandos por regex (`_processar_mensagem_core`, ~1000 linhas). Chamado por app e telegram_*.
- `backup_externo.py` + `backup_externo_cli.py`: cópia diária cifrada (AES-256-GCM, chave scrypt) de banco + `git bundle` + `.env` no OneDrive, conferida a cada geração; chamada por `services.gerar_backup_automatico` e nunca derruba o backup local. A senha é do titular (DPAPI em `.runtime/backup_externo.bin`): nunca a peça, leia ou registre; ele roda `configurar` no próprio terminal.
- `consultas_rapidas.py`: interpreta perguntas de gasto/entrada com categoria e período (últimos N meses, intervalo, mês, ano), sem IA. `busca_lancamentos.py`: "buscar <termo>" em todos os meses e troca de categoria em lote (prévia + confirmação); monta telas com `globals()` do motor, sem importá-lo, para não criar ciclo. Código novo de tela segue esse padrão: `telegram_experiencia.py` não pode crescer (linha de base).
- `parser_financeiro.py` (legado) vs `registro_conversa.py` (fluxo guiado, mais seguro). `assessor_ia_local.py`: Ollama local só para roteamento de intenção, nunca grava.
- `database.py`: conexões (WAL, FK on), CRUD, auditoria, `fatura_write_transaction` (`BEGIN IMMEDIATE`). `migrations.py` + `migrations/0001..0004`.
- Núcleo: `compromissos.py` (projeção, fatura unificada), `conciliacao.py`, `faturas_competencia.py`, `fatura_conferencia.py`, `reservas_faturas.py`, `saldo_resumo.py`, `saldos_edicao.py`, `pagamentos_canonicos.py`, `fixos_*.py`, `categorias*.py`.
- `config.py`: único ponto que lê o ambiente (`config.ler/ler_bool/ler_int`, mesmo padrão e mesmo momento de leitura de antes), `carregar_dotenv()` (só `app.py` e `telegram_experiencia` carregam o `.env`) e caminhos ancorados no projeto (`BACKUPS_DIR`, `EXPORTS_DIR`, `DASHBOARDS_DIR`, `IMPORTS_DIR`, `DB_PATH`). Os nomes antigos (`app.ASSESSOR_*`, `services.*_DIR`, `database.DB_PATH`) seguem como apelidos patcháveis. Variável nova: registrar em `config.VARIAVEIS` e no `.env.example` (`tests/test_config_unica.py`).
- `relogio.py`: relógio único em UTC-3 fixo (`agora()`, `agora_com_fuso()`, `hoje()`, `mes_atual()`). Código novo usa só ele; `hoje(date)`/`hoje(fonte_datahora=datetime)` existem para respeitar `patch.object(modulo,'date'|'datetime')` de testes antigos. Coberto por `tests/relogio_fixo.data_fixa` e pelo `--data` do gate.
- `tests/test_arquitetura_linha_de_base.py`: trava (só pode diminuir) linhas dos 5 maiores módulos, funções >100 linhas, ciclos de import, SQL fora de `database.py`, relógio fora de `relogio.py` e ambiente fora de `config.py`. Ao reduzir, baixe o limite (`python tests/test_arquitetura_linha_de_base.py` mostra os números).
- `security.py`, `estado_runtime.py` (DPAPI), `roteamento_seguro.py`: PIN PBKDF2, limitador, whitelist, estado efêmero.
- `validacao/`: gate oficial. `tests/`: suíte vigente (~71 arquivos, nomes `test_<tema>_<versao|rcNNN|bloco_x>.py`).
- `docs/`: auditorias e decisões. `docs/BUGS_CONHECIDOS.md`: backlog consolidado da análise de 28/10/2026.

## Modelo de dados — o que não é óbvio
- Sem FK/CHECK; dinheiro em REAL. Não existe tabela de faturas nem de contas: são calculadas, ligadas por texto normalizado.
- **Conta × forma × destino são independentes**: `conta_origem` (banco real, precede `conta_pagamento` legado), `forma_pagamento` (pix/débito/crédito/boleto), `destino_pagamento` (favorecido, nunca entra em cálculo). Pix e crédito nunca são conta.
- Competência de fatura: corte inclusivo (padrão dia 25; `ASSESSOR_FATURA_DIA_CORTE`/`ASSESSOR_FATURA_CORTES`); compra a partir do corte exige o titular escolher o mês. `data_compra` guarda a data real.
- **`auditoria_eventos` guarda estado funcional** (vínculos de conciliação, conferência de fatura, âncoras de saldo, séries de fixos). Nunca purgue/arquive essa tabela.
- Pagamento de fatura nunca é gasto. Parcelamento só se apaga inteiro. Itens conciliados não se alteram. Conciliação falha fechado (um vínculo inconsistente derruba projeções).
- Migrations: `user_version` + `schema_migrations` com checksum; aplicada não se edita; 0002–0004 sem rollback (volta por backup). `init_db` não pode ganhar tabela/coluna fora de migration (quebra o hash do schema).

## Segurança (resumo)
Whitelist de usuário/chat falha fechado; PIN 6–8 dígitos (hash PBKDF2) só para ações sensíveis; autolock 15 min; estado efêmero com DPAPI; callbacks `ux:` (600 s) e `cmd:` (24 h); mídia nunca grava sem revisão. Não há servidor web: o Telegram é a única interface.

## Convenções
- Idioma: português (código de domínio, mensagens e docs).
- Release: bump em `version.py`, bloco no topo do `CHANGELOG.md` (`# x.y.z — Título (dd/mm/aaaa)`), "Gate oficial: N/N testes".
- Fuso: UTC-3 fixo via `relogio.py` (núcleo, `services`, `app`, `database`, telegram); ainda restam ~21 usos diretos de `date.today()`/`datetime.now()` em módulos periféricos (ver `docs/reavaliacao/08_onda3_etapa1.md`). `ASSESSOR_TIMEZONE` é ignorado. Ambiente só via `config.py`.

## Ferramentas do projeto (.claude/)
- Subagentes: `auditor-financeiro`, `auditor-telegram`, `cacador-de-bugs`, `revisor-testes`, `documentador`.
- Skills: `rodar-gate`, `investigar-bug` (depuração em 4 fases: causa raiz antes de corrigir; 3 tentativas falhas = parar), `verificar-antes-de-concluir` (prova vista antes de dizer "pronto"), `nova-migration`, `fechar-versao`.
- MCP `assessor-db` (`.mcp.json`, `tools/mcp_assessor_db.py`): inspeciona o banco só para leitura; use `ASSESSOR_MCP_DB` para apontar a uma cópia.

## Mapa de rotas
`docs/mapa/mapa.html` (grafo interativo) e `docs/mapa/vault/` (Obsidian) mostram tudo que tem ação e para onde vai. Consulte antes de mexer em menu, botão, comando ou estado de sessão (`state:Session.month` tem 113 ligações). Atualize os JSON de `docs/mapa/dados/` e rode `tools/gerar_mapa.py` ao criar rotas novas. Ver `docs/mapa/LEIA-ME.md`.
Vault Obsidian do projeto inteiro: abrir a pasta `docs/` (página `00 Início.md`). As notas de módulo em `docs/codigo/` são geradas por `tools/gerar_vault_codigo.py` (análise estática, sem dados reais): rode-o depois de mudar o código, junto com o gate.

## Pasta trash_assessor/
Arquivos fora de uso (scripts v4.0.2, notas de RCs, validação histórica, bancos/backups manuais antigos, PNG/CSV antigos). **Ignore-a ao analisar o projeto** e não a leia (contém dados reais). Ver `trash_assessor/LEIA-ME.md`.

## Estado conhecido
Reavaliação completa de 09/11/2026 em `docs/reavaliacao/` (comece por `00_veredito.md`): veredito de não recriar, profissionalizar por partes; Ondas 1 e 2 concluídas (rede de testes, gravação com prévia, corretude, jornadas, desempenho, identidade visual, mapa de rotas com verificador). Falta a Onda 3 (estrutura). O gate aceita `--data AAAA-MM-DD` (relógio falso); em testes use `tests/relogio_fixo.data_fixa`, nunca um relógio próprio. Backlog anterior em `docs/BUGS_CONHECIDOS.md`.
