---
tipo: modulo
grupo: Núcleo financeiro
linhas: 117
tags: [modulo, nucleo-financeiro]
---
# fixos_variaveis.py

> Fixos de valor variável (ex.: conta de luz): regras puras, sem banco.

**Grupo:** [[Núcleo financeiro]] · **Linhas:** 117 · **Funções:** 8 · **Classes:** 1

## Usa

- (nenhum módulo do projeto)

## Usado por

- [[conciliacao.py]] — `elegivel`, `estados_de_eventos`, `estimativa`, `historico_por_mes`
- [[fixos_interface.py]] — `elegivel`, `termos_busca`
- [[fixos_variaveis_acoes.py]] — `FixoVariavelErro`, `candidatos_de`, `elegivel`, `estados_de_eventos`, `estimativa`, `historico_por_mes`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `elegivel` | 57 | 3 | 1 | Motivo de recusa (texto) ou None se o fixo pode ser variável. |
| `estimativa` | 81 | 2 | 1 | Média (2 casas, HALF_UP) dos 3 últimos meses com pagamento ANTES de ``mes``. |
| `estados_de_eventos` | 43 | 2 | 0 | Eventos de auditoria (mais recente primeiro) -> {id (str): estado} só dos variáveis. |
| `historico_por_mes` | 69 | 2 | 0 | Lançamentos de histórico -> {mes: centavos} (só despesas). |
| `termos_busca` | 96 | 1 | 1 | 'Conta de luz' -> ['luz']; palavras de 3+ letras que não são genéricas. |
| `FixoVariavelErro` | 30 | 1 | 0 |  |
| `candidatos_de` | 101 | 1 | 0 | Despesas avulsas dos ``meses`` meses antes de ``ate_mes`` cuja descrição contém um |

## Tudo que define

- classe `FixoVariavelErro` (L30, 2 linhas)
- `centavos` (L34, 2 linhas)
- `_norm` (L38, 3 linhas)
- `estados_de_eventos` (L43, 12 linhas) — Eventos de auditoria (mais recente primeiro) -> {id (str): estado} só dos variáveis.
- `elegivel` (L57, 10 linhas) — Motivo de recusa (texto) ou None se o fixo pode ser variável.
- `historico_por_mes` (L69, 10 linhas) — Lançamentos de histórico -> {mes: centavos} (só despesas).
- `estimativa` (L81, 13 linhas) — Média (2 casas, HALF_UP) dos 3 últimos meses com pagamento ANTES de ``mes``.
- `termos_busca` (L96, 3 linhas) — 'Conta de luz' -> ['luz']; palavras de 3+ letras que não são genéricas.
- `candidatos_de` (L101, 17 linhas) — Despesas avulsas dos ``meses`` meses antes de ``ate_mes`` cuja descrição contém um

## Testes que usam (1)

- `tests/test_fixo_variavel.py`

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
