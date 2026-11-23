# Reavaliação 01 — Arquitetura e manutenibilidade (09/11/2026)

Escopo: código da raiz em v4.1.3, commit `c427341`, árvore limpa. Fontes: 4 varreduras somente leitura (subagentes Sonnet) mais um script AST meu (`scratchpad/arq/met.py`), com conferência por amostragem no código. **[verificado]** significa que eu mesmo conferi a linha citada ou que o script AST mediu o valor. **[suspeita]** é um relato de subagente que não reconferi linha por linha. Não abri banco, `.env`, backups nem dados.

---

## A) Retrato com métricas

### Tamanho [verificado]
| Medida | Valor |
|---|---|
| `.py` na raiz | 50 arquivos, 34.537 linhas |
| Top 5 | `services.py` 10.944 · `app.py` 5.470 · `telegram_experiencia.py` 5.048 · `compromissos.py` 2.166 · `database.py` 1.863 (= 25.491, **74 % do código**) |
| Funções/métodos | 1.329. 117 têm mais de 50 linhas e 35 têm mais de 100 |
| Maior classe | `Experience` (`telegram_experiencia.py:398-4532`): 4.135 linhas, 150 métodos, 82 % do arquivo |
| Testes | 90 arquivos `tests/test_*.py`, 802 métodos em `tests/`. Com `validacao/testes_v39` e `test_rc307`, o gate soma 1.032 |

### Top 20 funções por linhas [verificado, AST]
| # | Linhas | Função |
|---|---|---|
| 1 | 1.012 | `services._processar_mensagem_core` (`services.py:7962`) |
| 2 | 611 | `Experience.act` (`telegram_experiencia.py:2764`) |
| 3 | 461 | `app.montar_teclado_inline_para_resposta` (`app.py:2647`) |
| 4 | 353 | `services._calcular_saldo_mensal_etapa` (`services.py:2354`) |
| 5 | 252 | `registro_conversa.extrair_campos` (`:97`) |
| 6 | 241 | `app.montar_teclado_acao_produtiva` (`app.py:2404`) |
| 7 | 222 | `app.receber_mensagem` (`app.py:4715`) |
| 8 | 203 | `services.normalizar_comando_sinonimos` (`:6320`) |
| 9 | 202 | `app.callback_submenu` (`app.py:4939`) |
| 10 | 197 | `services.gerar_auditoria_resultado_mes_ux` (`:4604`) |
| 11 | 178 | `services.montar_itens_checklist_mes` (`:5266`) |
| 12 | 176 | `app.montar_help_por_tema` (`:4109`) |
| 13 | 171 | `Experience.dispatch_text` (`:4746`) |
| 14 | 169 | `database.init_db` (`:244`) |
| 15 | 158 | `app.iniciar_fluxo_guiado` (`:1669`) |
| 16 | 157 | `services.preparar_previa_exclusao` (`:6560`) |
| 17 | 152 | `services.gerar_revisao_inteligente` (`:1726`) |
| 18 | 148 | `services.gerar_dashboard_categorias_visual_mes` (`:3124`) |
| 19 | 146 | `services.gerar_compromissos_ux` (`:4879`) |
| 20 | 144 | `app.processar_callback_pin` (`:740`) |

### Acoplamento (grafo de imports entre módulos da raiz) [verificado, AST]
O grafo conta também os imports tardios, feitos dentro de função.
- **Fan-out:** `telegram_experiencia` importa 31 dos 50 módulos, `services` importa 16 e `app` importa 12.
- **Fan-in:** `database` é importado por 18 módulos, `money` por 13 e `services` por 11.
- **Dois ciclos grandes (componentes fortemente conexos):**
  1. **Núcleo:** `database ↔ conciliacao ↔ compromissos ↔ fatura_conferencia ↔ services ↔ reservas_faturas ↔ fixos_edicao`. A camada de dados importa regra de domínio: `database.py:821, 951, 1059, 1093, 1119, 1182, 1207, 1242, 1424` fazem `from conciliacao import bloquear_alteracao_*`.
  2. **UI:** `telegram_experiencia ↔ telegram_midia ↔ telegram_recursos ↔ telegram_alertas ↔ fixos_interface ↔ dashboard_metricas ↔ telegram_streaming`.
- **Outras dependências invertidas:**
  - `reservas_faturas.py:8` importa `services`.
  - `services.py:9668` importa `transcricao_audio`.
  - `dashboard_metricas` importa `telegram_experiencia`.

### Estilo, tipagem, erros e logging
- **`;` como separador de statements:** 358 linhas, 192 delas em `telegram_experiencia.py` [verificado].
- **Lambdas com mais de 120 caracteres:** 6, por exemplo `services.py:4727` (274 caracteres) e `services.py:770` [verificado].
- **Anotações de tipo:** 732 de 1.529 funções (48 %). `telegram_experiencia.py` tem **0 de 176**. Não há mypy, ruff, black, cobertura nem pyproject [suspeita, contagem do subagente].
- **`except Exception`:** 101 em produção [suspeita]. Desses, 47 não têm log, `raise` nem `print`, e 20 têm corpo vazio ou constante. Por arquivo: `app.py` 24 [verificado], `services.py` 23 [verificado], `telegram_experiencia.py` 19 [verificado].
- **Logging:** central em `registro_logs.py`, nível WARNING. `services.py` (10,9 mil linhas) tem só 2 usos de logger. Há 65 `print(` em produção, 29 deles em `migrations.py`, o que é aceitável numa CLI [suspeita].

### Modelo de dados [suspeita, relatório conferido em amostras]
- **Tabelas:** 11 funcionais mais `schema_migrations`.
- **Dinheiro:** 8 colunas `REAL`; não existe coluna monetária em INTEGER.
- **Integridade:** 0 FOREIGN KEY e 0 CHECK nas tabelas funcionais.
- **Índices:** só 2, nenhum em `transacoes(data)` ou `transacoes(conta)`.
- **Entidades calculadas:** não há tabela de contas nem de faturas.
- **Dicionário em auditoria:** ~12 entidades distintas de `auditoria_eventos` são lidas para reconstruir estado. Detalhe no item B4.

---

## B) Os 10 problemas estruturais que mais custam

### B1. Dois motores de conversa em produção, com ordem de despacho frágil — [verificado]
- **Ordem de despacho em `app.receber_mensagem`** (`app.py:4715-4936`):
  1. Reset de PIN e comandos de segurança.
  2. `ux.dispatch_text` (`app.py:4832`).
  3. Pendências legadas `PENDENCIAS_EXCLUSAO` e `PENDENCIAS_GUIADAS`.
  4. `obter_resposta_comando_especial`.
  5. `processar_mensagem` → `_processar_mensagem_core` (`services.py:7962`, 1.012 linhas de `if/regex`).
- **A UX 2.0 devolve o controle ao legado** em vários pontos:
  - `dispatch_text` retorna False se houver pendência legada (`telegram_experiencia.py:4756-4767`) ou comando operacional (`:4812`).
  - Há 31 ações `('legacy', …)` e 5 `legacy_raw`, que chamam `svc.processar_mensagem` (`:5018`).
- **Só no legado:** backup, exportar e importar CSV, herança do mês, auditoria do mês, metas, apagar e mudar faixas, corrigir valor, conta e forma, vencimento e conta de fixo, relatório, busca e status (`services.py:8031-8840`).
- **Custo:**
  - Todo comando novo exige decidir em qual motor ele vive e testar os dois caminhos.
  - "Digitado" e "clicado" podem cair em rotas diferentes (`docs/mapa/LEIA-ME.md`).
  - O mapa já registrou gatilhos mortos causados por ordem de regex.

### B2. Módulos-deus e funções-roteador gigantes — [verificado]
- **Os três maiores arquivos** concentram 21,5 mil linhas, 62 % do código:
  - `services.py` (344 funções) mistura regra, SQL (33 `execute`), PIL e geração de PNG (`services.py:2923+`), exportação CSV, backup e roteamento por regex.
  - `Experience` tem 150 métodos.
  - `act` tem 611 linhas.
- **Custo:**
  - Qualquer mudança toca arquivos de mais de 5 mil linhas.
  - A revisão é lenta.
  - Conflito de contexto (para humano e para IA) é constante.

### B3. Ciclos de import e dependências invertidas — [verificado]
- Os dois ciclos estão no item A.
- **O caso mais caro:** `database.py` (camada de dados) chama `conciliacao` (regra) em 9 pontos para bloquear alteração de itens conciliados.
- **Consequências:**
  - Não dá para testar o DAL sem a regra.
  - Não dá para extrair `services` em pacotes sem antes quebrar os ciclos.
  - Os imports tardios escondem a dependência.

### B4. Estado funcional dentro de `auditoria_eventos` — [verificado em parte]
- **Quem lê estado do log:**
  - Vínculos de conciliação: `conciliacao.py:65`, com varredura por entidade e "último evento vence".
  - Revisão: `conciliacao.py:270`.
  - Conferência de fatura: `fatura_conferencia.py:25`, com N+1 em `:36-39`.
  - Âncoras de saldo: `fatura_conferencia.py:94`.
  - Séries de fixos: `fixos_vigencia.py:20`.
  - Contas inativas: `contas_inativas.py:22`.
  - Herança de saldo inicial: `services.py:3660`.
  - Preferências e soneca: `assessor_orientacao.py:22`, `telegram_alertas.py:40`.
- **Custo:**
  - Um log de auditoria é tratado como tabela de estado, sem schema, sem índice próprio e sem cache além da renderização (`consulta_cache.py`).
  - Purga ou arquivamento destrói dados.
  - Cada nova "configuração" tende a ir para lá porque "não exige migration", como já ocorreu com contas inativas. É dívida que cresce sozinha.

### B5. Dinheiro em float/REAL fora da fronteira de entrada — [verificado em parte]
- **Entrada correta:** `money.parse_money` (Decimal, HALF_UP).
- **O problema:** `parse_money_float` (`money.py:36`) devolve float logo em seguida.
- **Contagem de `float(`:** `services.py` 160, `telegram_experiencia.py` 84, `compromissos.py` 36.
- **Somas em float:** `services.py:2211, 2522, 2592-2594, 2616-2628, 2770-2772`.
- **Comparações com tolerância:** `abs(a-b) < 0.005` (`services.py:202, 350`).
- **No JSON da auditoria:** valores entram em hashes de conciliação (`conciliacao.py:55-56`).
- **Custo:** risco latente de centavo divergente entre telas, testes que precisam de tolerância e migração cara (ver C e D).

### B6. Regra de negócio dentro da UI — [verificado em amostra]
- **SQL direto em `telegram_experiencia.py`:**
  - O UNION de contas em `:1928-1939` é, na prática, a "tabela de contas".
  - Outros pontos em `:2323` e `:3397`.
- **Totais, parcelamento e saldo calculados na tela:** `telegram_experiencia.py:738-882, 1259-1275, 2205, 2360, 2460-2475, 1806, 3044`.
- **Teclados que reinterpretam a resposta:** em `app.py`, os teclados interpretam o **texto da resposta** para descobrir mês e ids (`extrair_*`, `app.py:2074-2310`). A UI depende do formato textual da regra.
- **Custo:** a mesma regra existe em duas formas, uma no serviço e outra na tela. O roteiro de design já registrou "fonte de verdade dupla".

### B7. Duplicação de primitivas — [suspeita, subagente; amostras conferidas]
- **Normalizadores:** 17 ou mais normalizadores de texto e conta, em 3 famílias que divergem. Alguns tiram acento e outros não:
  - `compromissos.py:204` (não tira acento) × `services.py:712` (tira).
  - `parser_financeiro.py:46` é homônimo de `services.normalizar_texto`, com outra semântica.
- **Datas:**
  - 5 versões de "último dia do mês" e 5 de "somar meses" (`faturas_competencia.somar_meses` tem assinatura diferente da homônima em `services`).
- **Relógio:**
  - ~114 `date.today()` e ~66 `datetime.now()`, só 5 com fuso.
  - `obter_timezone_alertas` ignora `ASSESSOR_TIMEZONE` nos dois ramos (`app.py:5143-5152`, [verificado]).
- **Backup:** 3 implementações (`services.criar_backup_db:9982`, `sqlite_backup.py:8`, `migrations.create_schema_backup:526`).
- **Extração de valor:** duas (`parser_financeiro.extrair_valor` × `registro_conversa.extrair_campos`).
- **Formatador de R$:** 6 cópias.
- **Custo:** bug de conta "Itaú" ≠ "itau" conforme o caminho, e correções que precisam ser feitas N vezes.

### B8. Estado global em memória e configuração espalhada — [verificado em parte]
- **Estado em dicts de módulo:**
  - `app.py`: `SESSOES_SEGURANCA`, `PIN_TECLADO`, `PENDENCIAS_*`, `VINCULOS_BOTAO`, `MENSAGENS_CHAT` (`:62-65, 298, 948, 1337-1343, 1478`).
  - `services.py`: 5 `PENDENCIAS_*` (`:299-303`).
  - O singleton `EXPERIENCE` (`telegram_experiencia.py:4546`).
  - `PENDENCIAS_GUIADAS` não verifica TTL [suspeita].
- **Configuração:**
  - Não há módulo central. `app.py:41-60` lê 20 variáveis com `int()` no import.
  - `load_dotenv` é chamado em 2 lugares.
  - `web_app.py` não carrega `.env`.
  - 15 variáveis lidas pelo código não estão no `.env.example`.
- **Pastas relativas ao CWD:** `services.py:292-295` [verificado] e `compromissos.py:42`.
- **Custo:**
  - Testes precisam fazer patch de módulos (274 `patch.object`, 86 sobre `app`).
  - Reinício perde pendências.
  - O comportamento depende do diretório de execução.

### B9. Schema com duas fontes (init_db × migrations) e sem integridade declarada — [verificado em parte]
- **DDL fora de migration:** `init_db` ainda faz `ALTER TABLE ADD COLUMN` (`database.py:261-264`, [verificado]) e normaliza categorias a cada boot.
- **Divergência possível:** o CREATE de `compromissos` já tem as colunas da 0002, mas `data_compra` e `competencia_fatura` só vêm pela 0004. Banco novo e banco migrado podem divergir.
- **Sem integridade declarada:** não há FK, CHECK nem índice em `transacoes`, e "conta" é texto livre em 7 colunas de 5 tabelas.
- **O que já é bom:** `migrations.py` tem `user_version`, checksum e hash funcional de schema.

### B10. Testabilidade cara: relógio, globais e I/O Telegram misturados — [suspeita, coerente com amostras]
- **Isolamento do banco:**
  - É feito por monkeypatch de `DB_PATH` arquivo a arquivo; 60 de 93 arquivos repetem o padrão.
  - Não há fixture compartilhada nem relógio injetável (12 arquivos fazem patch de data).
  - Os testes de `app` dependem de `SimpleNamespace`/`AsyncMock` e de muitos patches (`test_app_pin_pendencias_bloco_p1.py`: 52).
  - Patches por nome interno (`telegram_experiencia.svc.*`, `compromissos.calcular_fatura_unificada`) tornam a refatoração de nomes cara: mover uma função quebra testes que não testam aquilo.
- **Gate:**
  - O timeout fixo de 300 s já estourou.
  - `web_contracts` é fixo em 12 (`validar_versao_oficial.py:83`).
- **Custo:** a rede de 1.032 testes é forte em comportamento, mas está acoplada à estrutura atual. Isso precisa ser considerado na ordem das etapas.

**Menção honrosa (higiene):**
- `openai==2.42.0` e `pydantic` estão pinados sem uso, e o `requirements.txt` é um lockfile transitivo copiado.
- `iniciar_site_assessor.bat:9` diz 4.1.2.
- Há 27 símbolos sem uso algum, entre eles `app.py:5266, 5283, 5313` (rotinas legadas nunca agendadas), `comando_publico` (`:199`) e `web_app._serie_historica` (`:272`).
- `services.py:93-101` importa de `assessor.py` 3 funções que nunca chama.
- `ajustar_fatura_itau.py` e `sqlite_backup.py` são relíquias de ajuste pontual.

---

## C) Veredito

**Refatorar por estrangulamento (strangler), começando pelo núcleo de dados e pelas primitivas, e não recriar do zero.** Manter como está também não serve, porque a dívida cresce a cada feature (B1, B4, B7).

| Opção | Custo | Risco para ESTE projeto | Avaliação |
|---|---|---|---|
| **Recriar do zero** | Alto: ~34 mil linhas, centenas de regras de domínio implícitas (competência inclusiva, conciliação que falha fechado, fixos com séries, parcelamentos, dedupe previsto×real), mais a migração dos dados reais, inclusive o estado guardado em `auditoria_eventos` | **Muito alto.** É uma pessoa com dados reais em uso diário. As regras estão espalhadas e só os 1.032 testes as documentam, mas esses testes são acoplados aos nomes atuais e não migram para outra base. Haveria meses de dois sistemas ou de congelamento de features, e quase certamente regressões silenciosas em saldo e fatura | Não recomendado |
| **Strangler (recomendado)** | Médio, diluído em etapas pequenas. Cada etapa é reversível por `git revert` e roda contra a mesma suíte | **Baixo a médio.** A suíte protege o comportamento enquanto a estrutura muda. As migrations de dados (contas, centavos, estado fora da auditoria) entram só depois de o código estar em camadas, sempre com backup e dry-run | Recomendado |
| **Manter** | Zero agora; custo crescente depois | Médio: cada feature aumenta os dois motores e a auditoria-como-estado. Quem mantém (o titular ou uma IA) precisa ler arquivos de 5 a 11 mil linhas | Só aceitável se o produto congelar |

**Por que o strangler funciona aqui:**
1. O domínio já está parcialmente extraído em módulos pequenos e bons (`faturas_competencia`, `conciliacao`, `saldos_edicao`, `pagamentos_canonicos`, `money`).
2. A UX 2.0 já é o motor que se quer manter. O legado pode ser drenado comando a comando.
3. O framework de migrations com hash de schema é sólido e permite mudar o modelo com segurança.
4. Existe suíte comportamental grande, com percurso de botões (173 telas e 749 botões).

---

## D) Arquitetura-alvo e plano em etapas

### Pacotes-alvo (Python puro, sem framework novo)
```
assessor/
  config.py            ← todas as variáveis de ambiente (app.py:41-60, web_app, faturas_competencia…), Settings imutável; caminhos ancorados em BASE_DIR
  relogio.py           ← hoje()/agora() com fuso único (substitui date.today/UTC-3 fixo); injetável em teste
  dominio/
    texto.py           ← UM normalizador (+ chave de conta) — substitui as 17 variantes
    datas.py           ← ultimo_dia_mes, somar_meses, competência (de faturas_competencia)
    money.py           ← atual + tipo Centavos/Decimal e formatação R$ única
    contas.py          ← resolução/aliases de conta (compromissos.normalizar_conta_fatura, services.texto_chave_saldo, contas_inativas)
    faturas.py, conciliacao.py, compromissos.py, saldos.py, fixos.py, parcelamentos.py, categorias.py
  dados/
    conexao.py         ← get_connection, transações (de database.py)
    repos/*.py         ← SQL por agregado (transacoes, compromissos, faturas, auditoria, estado)
    migrations/        ← já existe
  servicos/            ← casos de uso (registrar, pagar fatura, conciliar, exportar, backup, relatórios); sem Telegram, sem regex
  interface/
    telegram/          ← app.py (bootstrap+handlers finos), experiencia/ (telas por área), roteamento de texto
    web/               ← web_app.py
    cli/               ← migrations, backup_db, tools
  legado/              ← parser_financeiro, _processar_mensagem_core enquanto drena
```
**Regras de dependência:**
- `interface → servicos → dominio`.
- `servicos → dados → dominio`.
- `dominio` não importa nada do projeto.
- Um teste de arquitetura (AST, como `met.py`) reprova ciclos novos.

**Onde vão os módulos atuais:**

| Hoje | Destino |
|---|---|
| `services.py` (por fatias) | `servicos/` (casos de uso), `dominio/` (cálculo), `dados/repos` (SQL) e `interface/telegram/textos` (formatação) |
| `telegram_experiencia.Experience` | `interface/telegram/experiencia/{inicio,apagar,registrar,fatura,saldos,ajuda}.py`, com `act` virando tabela de despacho |
| `app.py` | `interface/telegram/{bootstrap,seguranca_pin,handlers}.py` |
| `database.py` | `dados/conexao.py` mais repos. O bloqueio por conciliação sai do DAL e sobe para `servicos` |

### Etapas (cada uma: PR pequeno, reversível por `git revert`, gate verde)

**Etapa 0. Higiene e rede de segurança (1–2 dias)**
- **O que fazer:**
  - Fazer o commit de segurança pendente (sem `dashboards/*.png` e sem dados), conforme o CLAUDE.md.
  - Remover `openai`/`pydantic` do requirements e separar `requirements.in` de `requirements.lock`.
  - Corrigir a versão no `.bat`.
  - Remover os 27 símbolos mortos e as relíquias (`ajustar_fatura_itau.py` vai para `trash_assessor`).
  - Adicionar `ruff` só com regras de erro (F, E9), sem reformatar.
  - Adicionar o teste de arquitetura que mede ciclos e tamanho (só registra a linha de base, sem reprovar).
- **Pronto quando:** o gate fica verde com a mesma contagem menos os testes das funções removidas, e `ruff` passa.
- **O que a suíte garante:** comportamento inalterado, porque só sai código sem referência.

**Etapa 1. `config.py` e `relogio.py` (2–3 dias)**
- **O que fazer:**
  - Centralizar a leitura de ambiente e manter os nomes antigos como alias (`app.ASSESSOR_X = config.X`) para não quebrar os `patch.object`.
  - Criar `relogio.hoje()` com o fuso único `ASSESSOR_TIMEZONE`, usando `zoneinfo` com fallback −3.
  - Substituir `date.today()` arquivo por arquivo, começando pelos de menor volume.
  - Ancorar `exports/`, `backups/`, `dashboards/` e `imports/` em `BASE_DIR`.
- **Pronto quando:**
  - Zero `os.getenv` fora de `config.py`.
  - Zero `date.today()` fora de `relogio.py`.
  - O `.env.example` cobre todas as variáveis.
- **O que a suíte garante:** os testes com patch de data continuam valendo. Um teste novo cobre a virada de dia às 21h–24h.

**Etapa 2. Primitivas únicas: texto, datas, R$ e backup (3–5 dias)**
- **O que fazer:**
  - Criar `dominio/texto.py` e `dominio/datas.py`.
  - Trocar os corpos duplicados por delegação, mantendo os nomes antigos como wrappers finos.
  - Usar um único backup (`services.criar_backup_db`), com `migrations` passando a chamá-lo.
  - Antes de unificar, escrever um **teste de caracterização** que roda os 17 normalizadores sobre ~200 nomes reais de conta (anonimizados) e documenta as divergências.
  - Quando a divergência for intencional, como os aliases de cartão, ela vira parâmetro explícito.
- **Pronto quando:** existem 1 normalizador base, 1 `ultimo_dia_mes`, 1 `somar_meses` e 1 formatador de R$, e os wrappers ficam marcados como `# legado`.
- **O que a suíte garante:** os testes de conta, fatura e saldo existentes, mais o teste de caracterização.

**Etapa 3. Quebrar os ciclos do núcleo (3–5 dias)**
- **O que fazer:**
  - Tirar `from conciliacao import bloquear_*` de `database.py`. As guardas passam para as funções de serviço que chamam o DAL, ou para um hook injetado na conexão.
  - Quebrar `reservas_faturas → services` e `dashboard_metricas → telegram_experiencia`.
- **Pronto quando:** o teste de arquitetura reprova ciclos no SCC do núcleo, e `database` não importa nenhum módulo de domínio além de `categorias` e `faturas_competencia`.
- **O que a suíte garante:** o teste "itens conciliados não se alteram" (já existente) prova que as guardas continuam no caminho.

**Etapa 4. Fatiar `services.py` por estrangulamento (2–4 semanas, em ~10 PRs)**
- **Ordem das fatias:** exportação/importação CSV, backup, imagens/PIL, checklist, saldos, faturas, fixos, transferências, relatórios e auditoria do mês.
- **Como cada fatia é feita:**
  1. Mover o código para `servicos/<tema>.py`.
  2. Deixar em `services.py` `from servicos.<tema> import *` (reexport) para os patches e chamadores antigos continuarem funcionando.
  3. Ajustar os patches dos testes da fatia para o novo caminho.
- **Pronto quando:** `services.py` fica abaixo de ~3 mil linhas (roteador legado mais reexports), com cada fatia testada em isolamento.
- **O que a suíte garante:** tudo, já que é movimento puro de código. Revisar o diff com `git diff --color-moved`.

**Etapa 5. Drenar o motor legado (contínuo, 1 comando por PR)**
- **O que fazer:** para cada gatilho só-legado da tabela de B1, criar ação ou tela na UX, apontar o gatilho de texto para ela, apagar o ramo em `_processar_mensagem_core` e apagar a ação `('legacy', …)` correspondente.
- **Ordem:** começar pelos sensíveis (exclusão, faixa, corrigir valor), que ganham prévia e confirmação uniformes.
- **Pronto quando:** `legacy`/`legacy_raw` chegam a 0, os `PENDENCIAS_*` de `services` e `app` deixam de existir e `_processar_mensagem_core` é removido.
- **O que a suíte garante:** o percurso de botões e os testes de comandos digitados. Cada PR acrescenta "digitado == clicado" para o comando migrado.

**Etapa 6. Fatiar `Experience` (2–3 semanas)**
- **O que fazer:**
  - Separar as telas por área.
  - Trocar `act` (611 linhas) por um dicionário `acao → handler`.
  - Mover os cálculos de B6 para `servicos`, para que as telas só formatem.
  - Anotar tipos à medida que mover e rodar `mypy` só nos arquivos novos.
- **Pronto quando:** nenhum arquivo de UI passa de ~800 linhas, há zero SQL em `interface/` e não restam `;` como separador nos arquivos novos.

**Etapa 7. Modelo de dados (só depois das etapas 3 a 6, cada uma com backup, dry-run e ensaio em cópia)**
- **7a. Migration 0005, estado fora da auditoria:**
  - Criar tabelas `conciliacao_vinculos`, `fatura_conferencias`, `saldo_ancoras`, `fixo_series`, `contas` (com `ativa` e aliases) e `preferencias`, populadas a partir do último evento por chave.
  - A auditoria continua sendo escrita, mas deixa de ser lida.
  - **Pronto quando:** a projeção de saldo e fatura no banco copiado fica idêntica antes e depois (script de comparação).
- **7b. Migration 0006, centavos:**
  - Criar colunas `*_centavos INTEGER`, preencher com `ROUND(valor*100)` e fazer leitura dupla com asserção de igualdade por um período.
  - Depois, remover o REAL. As ~73 instruções SQL e ~290 `float(` só ficam tratáveis depois das etapas 4 e 6, porque o SQL estará concentrado em `dados/repos`.
  - Adicionar índices em `transacoes(data)` e `transacoes(conta)`.
- **7c.** Mover o `ALTER` restante de `init_db` para migration, para que `init_db` = cadeia de migrations em banco novo.

---

## E) O que NÃO vale a pena mexer
- **Trocar de stack:** não migrar para FastAPI, ORM, Postgres, Docker ou outro framework de bot. SQLite em WAL, `python-telegram-bot` e `http.server` em loopback servem bem a um titular. Um ORM só aumentaria a superfície de mudança.
- **Framework de migrations:** `migrations.py` funciona, tem checksum e hash funcional de schema. Não reescrever, só usar.
- **Segurança já endurecida:** PIN PBKDF2, DPAPI (`estado_runtime`), whitelist e callbacks com TTL ficam como estão, salvo bugs pontuais.
- **Módulos de domínio pequenos e coesos:** `faturas_competencia.py`, `pagamentos_canonicos.py`, `saldos_edicao.py`, `money.parse_money`, `registro_conversa` (fluxo guiado), `telegram_design` e `telegram_execucao` só mudam de pasta.
- **Painel web:** é somente leitura, pequeno e tem 12 contratos JS.
- **Converter a suíte:** não migrar de `unittest` para pytest agora. Adicionar pytest não paga o custo, e o gate depende de `unittest`.
- **Tipagem retroativa:** não anotar em massa. Tipar só o que for movido.
- **Formatação em massa:** não rodar black ou ruff-format no repositório inteiro. O diff gigante destruiria `git blame` e a revisão das etapas de movimento.
- **`auditoria_eventos`:** não purgar, nem depois da 7a. Ela continua sendo trilha de auditoria.
