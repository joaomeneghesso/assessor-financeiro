# 07 — Inventário de gravação do caminho legado (Onda 2, 12/11/2026)

Base: commit `afa6933` + frente "fechar o que ainda grava direto no legado".
Escopo: o roteador de texto `services._processar_mensagem_core` e os ramos de `app.py` que chegam a ele (texto livre depois de `ux.dispatch_text`, fluxo guiado legado `guiado:*`, botões `cmd:`/`__legado__`, jobs).

**Prova automatizada:** `tests/test_inventario_gravacao_legado.py`.
- Executa cada comando de escrita num banco temporário (com migrations).
- Afirma que nenhuma tabela muda antes da confirmação e que a confirmação grava.
- Guarda estática: toda função chamada pelo roteador precisa estar classificada como leitura, gravação com prévia, mecânica de pendência ou exceção justificada. Uma função nova sem classificação faz o teste falhar.
- Prova também que o recálculo da prévia nunca grava.

O teste do app é `tests/test_legado_app_onda2.py`.

Legenda: **Prévia** = mostra "antes → depois" e só grava com `confirmar alteracao`, `confirmar exclusao`, `confirmar pagamento|estorno|credito` ou `confirmar importacao`, ou com o botão vinculado à prévia. **PIN** = `acao_exige_pin`/`exportacao_exige_pin` no app.

## Mecanismo (reutilizado da Onda 1)
- Os ramos que gravam chamam `_gravacao_pede_confirmacao(texto, prévia, sessão)`.
  - Sem confirmação, a função cria a pendência em `PENDENCIAS_ALTERACAO` via `_preparar_alteracao_sessao` e devolve a prévia.
  - Confirmado (`_ALTERACAO_CONFIRMADA`), devolve `None` e o ramo grava.
- `confirmar_alteracao_pendente` recalcula a prévia com `recalcular_previa_gravacao`.
  - A função roda o próprio roteador em "modo prévia" (ContextVar `_COLETANDO_PREVIA`).
  - O primeiro gate devolve a prévia por exceção interna, sem criar pendência e sem gravar.
  - Se a prévia mudou, nada é gravado.
  - Uma única regra de recálculo cobre os ramos antigos e os novos.
- Exclusões continuam no mecanismo próprio: prévia, backup prévio, auditoria e TTL de 10 min.

## Tabela

| # | Comando (exemplo) | Caminho | Prévia + confirmação | Auditoria | PIN |
|---|---|---|---|---|---|
| 1 | `mudar 7 para X`, `mudar 1-5 para X`, `mudar último para X` | `previa_alteracao` → `mudar_categoria_*` | Sim (Onda 1) | Sim | Não |
| 2 | `corrigir valor 7 para 9`, `corrigir 7 para 9` | `previa_alteracao` → `corrigir_valor_por_id` | Sim (Onda 1) | Sim | Não |
| 3 | `corrigir conta/forma 7 para X` | `previa_alteracao` → `corrigir_*_por_id` | Sim (Onda 1; parcela isolada recusada) | Sim | Não |
| 4 | `meta lazer 300` | `previa_alteracao` → `definir_meta_formatado` | Sim (Onda 1) | Sim | Não |
| 5 | `alterar valor/conta/forma/categoria/vencimento fixo N …`, `alterar fixo N para X`, `alterar término … sem término` | `previa_alteracao` → `fixos_edicao.salvar` / `alterar_*` / `remover_termino_fixo` | Sim (Onda 1) | Sim | Não |
| 6 | `pausar/reativar fixo N`, `pausar/reativar entrada N`, `alterar entrada N para X` | `previa_alteracao` → `pausar_*`/`reativar_*`/`alterar_entrada_valor` | Sim (Onda 1) | Sim | Não |
| 7 | `novo fixo …`, `nova entrada fixa …`, `entrada … em AAAA-MM-DD` | `previa_alteracao` → `cadastrar_*` | Sim (Onda 1) | Sim | Não |
| 8 | **`corrigir #F12 valor para 25,50`** (valor, competência, data, conta) | `_previa_editar_fatura` → `editar_movimento_fatura_formatado` | **Sim (Onda 2)**; antes gravava direto | Sim | Não |
| 9 | **`vencimento fatura nubank dia 15`** (recorrente ou `AAAA-MM`) | `_previa_vencimento_fatura` → `definir_vencimento_fatura_por_nome_formatado` | **Sim (Onda 2)** | **Sim (Onda 2)** | Não |
| 10 | **`vencimento C7 para dia 12`**, `data pagamento B2 2026-07 para dia 10` | `_previa_data_pagamento_checklist` → `definir_data_pagamento_checklist_formatado` | **Sim (Onda 2)** | **Sim (Onda 2)** | Não |
| 11 | **`transferi 100 do Itaú para Caju`**, `mover/passei …` (quando chega ao núcleo) | `_previa_transferencia_caixa` → `registrar_transferencia_caixa_formatado` | **Sim (Onda 2)**; pelo app normal a UX já abria prévia | **Sim (Onda 2)** | Não |
| 12 | **`saldo inicial [AAAA-MM] [conta] valor`**, `ajustar/corrigir saldo … para X`, `saldo inicial … herdado` | `_previa_saldo_inicial` → `definir_saldo_inicial_formatado` | **Sim (Onda 2)**; as recusas continuam respondendo sem pendência. O botão "Voltar a herdar" abre esta mesma prévia, com confirmação única | Sim (`_gravar_*_auditado`) | Não |
| 13 | **Texto livre de lançamento** (`gastei 35 no mercado`, `recebi 500`, `celular 1200 em 10x`) que chega ao núcleo | `parse_mensagem` → `_previa_lancamento` → `registrar_transacao_unica`/`registrar_compra_parcelada` | **Sim (Onda 2)**; antes gravava direto pelo fluxo guiado, por botões legados e por frases que a UX não reconhecia | **Sim (Onda 2)** | Não |
| 14 | `apagar 7`, `apagar 1-5`, `apagar último`, `apagar fixo/entrada/parcelamento/meta …` | `comando_destrutivo_exclusao` → `_preparar_exclusao_sessao` | Sim, com backup prévio | Sim | Sim (fixo, parcelamento, faixa) |
| 15 | `apagar transferencia caixa N`, `resetar checklist`, `apagar data pagamento X` | `PADROES_EXCLUSAO_EXTRAS` → exclusão | Sim (Onda 1), com backup | Sim | Não |
| 16 | `apagar #F12` | movimento de fatura → exclusão | Sim, com backup | Sim | Não |
| 17 | `paguei 500 da fatura X usando Y`, `estorno de 50 na fatura X` | `_preparar_movimento_fatura_sessao` | Sim (`confirmar pagamento/estorno/credito`) | Sim | Não |
| 18 | `analisar csv` → `confirmar importacao` | `PENDENCIAS_IMPORTACAO` → `importar_preview` | Sim (resíduo M8: substitui por origem sem backup) | Não por item | Sim |
| 19 | `confirmar` (lançamento pendente) | `PENDENCIAS_CONFIRMACAO` | Só grava pendência criada antes. Hoje nenhum ramo cria essa pendência (código morto) | Sim (via #13) | Não |
| 20 | **`paguei C5`**, `marcar pago/pendente C5`, `desmarcar C5 C7` | `marcar_item(s)_checklist_formatado` | **Não: exceção justificada** | **Sim (Onda 2)** | Não |
| 21 | `backup`, `backup automatico` | `gerar_backup*` | Não (só gera arquivo, não altera dados) | Não | Sim |
| 22 | `exportar csv …` | `exportar_csv_*` | Não (só gera arquivo) | Não | Sim (base inteira/período grande) |
| 23 | `dashboard …` | `gerar_dashboard_*` | Não (só gera PNG) | Não | Não |
| 24 | `aprender`, `aula …` (legado) | `parsear_comando_aprender` | Só leitura (aulas). Não grava | — | — |

### Ramos de `app.py` que chegam ao núcleo

| Ponto | O que chega | Situação agora |
|---|---|---|
| Fluxo guiado `registrar_despesa/entrada/parcela` (`montar_comando_de_pendencia`) | Texto livre (#13) | Prévia + botões vinculados. Antes gravava direto |
| Fluxo guiado `corrigir_valor/categoria/conta`, `alterar_conta_fixo*` | `corrigir …`/`mudar …`/`alterar conta fixo …` | Prévia (Onda 1). O aprendizado de categoria agora é oferecido depois do `confirmar alteracao` |
| Fluxo guiado `confirmar_apagar_*`, `apagar_fixo_sem_id` | `apagar …` | Prévia de exclusão + backup |
| Botões `__legado__[alteracao:…]` / `confirmar alteracao` digitado | `confirmar/cancelar alteracao` | `executar_texto_alteracao_pendente` (assinatura da prévia conferida) |
| `__perguntar_herdar__:` ("Voltar a herdar") | `saldo inicial … herdado` | Abre a prévia padrão (#12). Antes era uma pergunta própria seguida de gravação direta |
| Callback `aprender_categoria_sim` | `salvar_regra` | Botão vinculado + auditoria (sem mudança) |
| `af:` (alertas) | adiar lembrete | Estado de alerta, não financeiro |
| Recuperação/troca de PIN | `.env` (hash) | Auditado. A escrita agora é atômica (B5) |
| Jobs (`rotina_backup_diario`, alertas, resumo) | Backup em arquivo; leitura | Sem gravação financeira |

## Contagem
- **Comandos de escrita financeira no roteador: 24 famílias** (linhas 1–20 da tabela, mais o `confirmar` de importação e de fatura).
- **Com prévia + confirmação: 23.** Sete delas foram fechadas nesta onda: #8–#13 e o fluxo guiado de lançamento.
- **Exceção justificada: 1** (#20, marcar pago/pendente no checklist).
- **Sem gravação financeira (arquivo/leitura): 4** (#21–#24).

## Exceção justificada: marcar pago/pendente no checklist
- **O que é:** só a marcação visual do item. A baixa financeira de compromisso e a fatura com saldo já são recusadas e levam para A pagar, com valor, conta e data.
- **Por que não pede prévia:** é usada várias vezes por dia. Uma prévia em cada toque dobraria o atrito sem proteger dinheiro.
- **O que mudou:** a marcação agora gera um evento em `auditoria_eventos` (antes → depois) e a resposta termina com "Para desfazer: desmarcar C5 2026-11" (ou "paguei …").
- **Recálculo de prévia:** nunca marca nada.

## Fora desta frente (abertos)
- **M8:** reimportação de CSV sem backup e sem "N serão substituídos".
- **B7:** stderr do ffmpeg/whisper no chat (`transcricao_audio.py`, `telegram_midia.py`).
- **B14:** texto do OCR/áudio em `mensagem_original` (`telegram_midia.py:166`).
- **B3 parcial:** `resetar <qualquer coisa>` ainda cai no reset de PIN.

Os três últimos estão em arquivos fora do escopo desta frente.
