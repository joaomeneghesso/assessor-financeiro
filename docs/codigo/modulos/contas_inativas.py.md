---
tipo: modulo
grupo: Núcleo financeiro
linhas: 66
tags: [modulo, nucleo-financeiro]
---
# contas_inativas.py

> Contas desativadas: saem das listas de escolha, mas o histórico, os relatórios e o backup seguem intactos.

**Grupo:** [[Núcleo financeiro]] · **Linhas:** 66 · **Funções:** 7 · **Classes:** 0

## Usa

- [[database.py]]

## Usado por

- [[telegram_experiencia.py]] — `desativar`, `esta_inativa`, `listar`, `reativar`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `desativar` | 61 | 1 | 2 |  |
| `reativar` | 65 | 1 | 1 |  |
| `esta_inativa` | 37 | 1 | 0 |  |
| `listar` | 30 | 1 | 0 |  |

## Tudo que define

- `normalizar` (L15, 3 linhas)
- `_ler` (L20, 8 linhas)
- `listar` (L30, 5 linhas)
- `esta_inativa` (L37, 3 linhas)
- `_alterar` (L42, 17 linhas)
- `desativar` (L61, 2 linhas)
- `reativar` (L65, 2 linhas)

## Testes que usam (2)

- `tests/test_ajustar_saldo_seletor.py`
- `tests/test_contas_gerenciar.py`

## No mapa de rotas

- **Chamadas de serviço (1):** [[fn_contas_inativas.esta_inativa-72d78|contas_inativas.esta_inativa]]

## Documentos que citam

- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
