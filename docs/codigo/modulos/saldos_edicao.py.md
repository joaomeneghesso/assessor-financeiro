---
tipo: modulo
grupo: Núcleo financeiro
linhas: 69
tags: [modulo, nucleo-financeiro]
---
# saldos_edicao.py

> Confirmação atômica do saldo atual de uma conta e da base geral do mês.

**Grupo:** [[Núcleo financeiro]] · **Linhas:** 69 · **Funções:** 2 · **Classes:** 0

## Usa

- [[database.py]]
- [[money.py]]
- [[relogio.py]]
- [[services.py]]

## Usado por

- [[telegram_experiencia.py]] — `capturar`, `confirmar`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `capturar` | 11 | 1 | 4 | Foto para validação otimista. Não guarda dados em cache entre ações. |
| `confirmar` | 20 | 1 | 4 |  |

## Tudo que define

- `capturar` (L11, 7 linhas) — Foto para validação otimista. Não guarda dados em cache entre ações.
- `confirmar` (L20, 50 linhas)

## Testes que usam (4)

- `tests/test_bloco_c_ciclo_vida.py`
- `tests/test_fatura_conferencia.py`
- `tests/test_matriz_release_oficial.py`
- `tests/test_revisao_saldo_integridade.py`

## No mapa de rotas

- **Chamadas de serviço (2):** [[fn_saldos_edicao.capturar-a2e33|capturar]], [[fn_saldos_edicao.confirmar-dd457|confirmar]]

## Documentos que citam

- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
