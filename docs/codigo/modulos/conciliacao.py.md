---
tipo: modulo
grupo: Núcleo financeiro
linhas: 372
tags: [modulo, nucleo-financeiro]
---
# conciliacao.py

> Vínculos explícitos entre uma ocorrência de compromisso e um lançamento.

**Grupo:** [[Núcleo financeiro]] · **Linhas:** 372 · **Funções:** 26 · **Classes:** 1

## Usa

- [[compromissos.py]] *(importação tardia, dentro de função)*
- [[consulta_cache.py]]
- [[database.py]]
- [[faturas_competencia.py]]
- [[fixos_variaveis.py]] *(importação tardia, dentro de função)*
- [[money.py]]
- [[relogio.py]]

## Usado por

- [[compromissos.py]] — `ajustar_projecao`
- [[consultas_pagar.py]] — `listar_vinculos`
- [[database.py]] — `bloquear_alteracao_compromisso`, `bloquear_alteracao_transacoes`
- [[fixos_edicao.py]] — `ConciliacaoError`, `bloquear_alteracao_compromisso`, `listar_vinculos`
- [[fixos_variaveis_acoes.py]] — `estimativa_fixo_variavel`, `fixos_variaveis_ativos`, `listar_vinculos`
- [[services.py]] — `ConciliacaoError`, `bloquear_alteracao_compromisso`, `centavos`, `fim_mes`, `listar_vinculos`, `normalizar`, `referencia`, `revisoes_pendentes`
- [[telegram_experiencia.py]] — `ConciliacaoError`, `alvo`, `desvincular`, `listar_vinculos`, `marcar_separado`, `vincular_existente`
- [[telegram_registros.py]] — `bloquear_alteracao_transacoes`, `desvincular_conn`, `listar_vinculos`, `marcar_separado_conn`, `vincular_conn`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `listar_vinculos` | 129 | 6 | 4 |  |
| `ConciliacaoError` | 24 | 3 | 6 | Falha de validação do vínculo, exibível ao usuário. |
| `bloquear_alteracao_compromisso` | 325 | 3 | 1 |  |
| `bloquear_alteracao_transacoes` | 319 | 2 | 1 |  |
| `vincular_existente` | 276 | 1 | 4 |  |
| `alvo` | 199 | 1 | 2 |  |
| `desvincular` | 313 | 1 | 2 | Reabre a previsão e preserva o movimento real; não simula devolução bancária. |
| `vincular_conn` | 220 | 1 | 2 | Revalida alvo, saldo e lançamento sob BEGIN IMMEDIATE antes de vincular. |
| `ajustar_projecao` | 166 | 1 | 1 |  |
| `centavos` | 38 | 1 | 0 |  |
| `desvincular_conn` | 302 | 1 | 0 |  |
| `estimativa_fixo_variavel` | 154 | 1 | 0 | (valor, meses usados) da previsão de um fixo variável; baixas lidas dos vínculos se não vierem. |
| `fim_mes` | 47 | 1 | 0 |  |
| `fixos_variaveis_ativos` | 143 | 1 | 0 | {id (str): histórico {mes: centavos}} dos fixos de valor variável (lido 1x por consulta). |
| `marcar_separado` | 370 | 1 | 0 |  |
| `marcar_separado_conn` | 361 | 1 | 0 |  |
| `normalizar` | 42 | 1 | 0 |  |
| `referencia` | 53 | 1 | 0 |  |
| `revisoes_pendentes` | 354 | 1 | 0 |  |
| `_hoje` | 31 | 0 | 3 | Hoje no fuso do titular (UTC-3). Ponto único do relógio da conciliação, |
| `assinatura_alvo` | 78 | 0 | 3 |  |
| `_mesmo_titular` | 289 | 0 | 1 | Mesmo usuário e mesmo chat, ignorando apenas o tópico do Telegram. |

## Tudo que define

- classe `ConciliacaoError` (L24, 2 linhas) — Falha de validação do vínculo, exibível ao usuário.
- `_hoje` (L31, 5 linhas) — Hoje no fuso do titular (UTC-3). Ponto único do relógio da conciliação,
- `centavos` (L38, 2 linhas)
- `normalizar` (L42, 3 linhas)
- `fim_mes` (L47, 3 linhas)
- `referencia` (L53, 7 linhas)
- `_escopo_do_corte` (L62, 14 linhas) — Escopo do cache de consulta para leituras feitas sob este corte.
- `assinatura_alvo` (L78, 5 linhas)
- `_auditar` (L85, 3 linhas)
- `_listar_vinculos_conn` (L90, 37 linhas)
- `listar_vinculos` (L129, 7 linhas)
- `_listar_vinculos_sem_conexao` (L138, 3 linhas)
- `fixos_variaveis_ativos` (L143, 9 linhas) — {id (str): histórico {mes: centavos}} dos fixos de valor variável (lido 1x por consulta).
- `estimativa_fixo_variavel` (L154, 10 linhas) — (valor, meses usados) da previsão de um fixo variável; baixas lidas dos vínculos se não vierem.
- `ajustar_projecao` (L166, 31 linhas)
- `alvo` (L199, 19 linhas)
- `vincular_conn` (L220, 54 linhas) — Revalida alvo, saldo e lançamento sob BEGIN IMMEDIATE antes de vincular.
- `vincular_existente` (L276, 11 linhas)
- `_mesmo_titular` (L289, 11 linhas) — Mesmo usuário e mesmo chat, ignorando apenas o tópico do Telegram.
- `desvincular_conn` (L302, 9 linhas)
- `desvincular` (L313, 4 linhas) — Reabre a previsão e preserva o movimento real; não simula devolução bancária.
- `bloquear_alteracao_transacoes` (L319, 4 linhas)
- `bloquear_alteracao_compromisso` (L325, 3 linhas)
- `_revisoes_pendentes` (L330, 22 linhas) — Sinaliza ambiguidades; não associa nem altera movimentos por semelhança.
- `revisoes_pendentes` (L354, 5 linhas)
- `marcar_separado_conn` (L361, 7 linhas)
- `marcar_separado` (L370, 3 linhas)

## Testes que usam (11)

- `tests/test_baixa_fixo_conta.py`
- `tests/test_bloco_c_ciclo_vida.py`
- `tests/test_bloco_d_usabilidade.py`
- `tests/test_compromissos_correcoes_p0.py`
- `tests/test_contas_gerenciar.py`
- `tests/test_desempenho_heranca_onda2.py`
- `tests/test_equivalencia_calculos_onda2.py`
- `tests/test_heranca_receita_prevista.py`
- `tests/test_mutantes_rede_seguranca.py`
- `tests/test_parcelamento_atomico.py`
- `tests/test_relogio_unico.py`

## No mapa de rotas

- **Funções no mapa (3):** [[fn_conciliacao.desvincular_conn-5bd4b|conciliacao.desvincular_conn]], [[fn_conciliacao.marcar_separado_conn-53f32|conciliacao.marcar_separado_conn]], [[fn_conciliacao.vincular_conn-a192f|conciliacao.vincular_conn]]
- **Chamadas de serviço (5):** [[fn_conciliacao.alvo-7b858|alvo]], [[fn_conciliacao.desvincular-18195|desvincular]], [[fn_conciliacao.listar_vinculos-ca122|listar_vinculos]], [[fn_conciliacao.marcar_separado-c457b|marcar_separado]], [[fn_conciliacao.vincular_existente-f072e|vincular_existente]]

## Documentos que citam

- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
