---
tipo: modulo
grupo: Núcleo financeiro
linhas: 163
tags: [modulo, nucleo-financeiro]
---
# faturas_competencia.py

> V39: calendario de faturas separado da data real da compra.

**Grupo:** [[Núcleo financeiro]] · **Linhas:** 163 · **Funções:** 17 · **Classes:** 0

## Usa

- [[config.py]]

## Usado por

- [[compromissos.py]] — `competencia_transacao`, `data_competencia`, `data_real_compra`
- [[conciliacao.py]] — `competencia_transacao`, `eh_credito`
- [[database.py]] — `eh_credito`, `exigir_schema`, `normalizar`, `sql_competencia`, `validar_mes`
- [[efeito_baixa.py]] — `eh_credito`
- [[services.py]] — `competencia_transacao`, `data_competencia`, `eh_credito`, `precisa_escolher`
- [[telegram_experiencia.py]] — `competencia_transacao`, `contexto_escolha`, `data_competencia`, `data_real_compra`, `eh_credito`, `opcoes_fatura`, `precisa_escolher`, `preparar_rascunho`
- [[telegram_registros.py]] — `eh_credito`, `exigir_schema`, `somar_meses`, `validar_escolha`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `eh_credito` | 32 | 6 | 0 |  |
| `competencia_transacao` | 126 | 4 | 0 |  |
| `data_competencia` | 133 | 3 | 0 | Data de referencia mensal; nao substitui a data persistida da compra. |
| `precisa_escolher` | 70 | 2 | 1 |  |
| `data_real_compra` | 141 | 2 | 0 |  |
| `exigir_schema` | 160 | 2 | 0 |  |
| `opcoes_fatura` | 77 | 1 | 1 |  |
| `contexto_escolha` | 82 | 1 | 0 |  |
| `normalizar` | 27 | 1 | 0 |  |
| `preparar_rascunho` | 88 | 1 | 0 | Retorna True quando falta a escolha; invalida escolhas de dados anteriores. |
| `somar_meses` | 43 | 1 | 0 |  |
| `sql_competencia` | 145 | 1 | 0 | Compativel com a v38 sem migration; alias e interno, nunca vem do usuario. |
| `validar_escolha` | 111 | 1 | 0 |  |
| `validar_mes` | 36 | 1 | 0 |  |
| `dia_corte` | 57 | 0 | 1 |  |

## Tudo que define

- `_get` (L19, 6 linhas)
- `normalizar` (L27, 3 linhas)
- `eh_credito` (L32, 2 linhas)
- `validar_mes` (L36, 5 linhas)
- `somar_meses` (L43, 6 linhas)
- `_dia` (L51, 4 linhas)
- `dia_corte` (L57, 11 linhas)
- `precisa_escolher` (L70, 5 linhas)
- `opcoes_fatura` (L77, 3 linhas)
- `contexto_escolha` (L82, 4 linhas)
- `preparar_rascunho` (L88, 21 linhas) — Retorna True quando falta a escolha; invalida escolhas de dados anteriores.
- `validar_escolha` (L111, 13 linhas)
- `competencia_transacao` (L126, 5 linhas)
- `data_competencia` (L133, 6 linhas) — Data de referencia mensal; nao substitui a data persistida da compra.
- `data_real_compra` (L141, 2 linhas)
- `sql_competencia` (L145, 13 linhas) — Compativel com a v38 sem migration; alias e interno, nunca vem do usuario.
- `exigir_schema` (L160, 4 linhas)

## Testes que usam (1)

- `tests/test_mutantes_rede_seguranca.py`

## Documentos que citam

- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
