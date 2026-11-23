---
tipo: modulo
grupo: Entrada e operação
linhas: 141
tags: [modulo, entrada-e-operacao]
---
# operacao_bot.py

> Operação do bot: trava de instância única, tratador global de erro e tarefas monitoradas.

**Grupo:** [[Entrada e operação]] · **Linhas:** 141 · **Funções:** 7 · **Classes:** 2

## Usa

- (nenhum módulo do projeto)

## Usado por

- [[app.py]] — `InstanciaJaEmExecucao`, `adquirir_trava_instancia`, `criar_tarefa_monitorada`, `criar_tratador_erro`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `InstanciaJaEmExecucao` | 21 | 1 | 1 | Outra instância do assessor já segura a trava. |
| `adquirir_trava_instancia` | 82 | 1 | 1 |  |
| `criar_tarefa_monitorada` | 128 | 1 | 1 |  |
| `criar_tratador_erro` | 109 | 1 | 1 |  |
| `aviso_padrao` | 105 | 0 | 1 |  |

## Tudo que define

- classe `InstanciaJaEmExecucao` (L21, 2 linhas) — Outra instância do assessor já segura a trava.
- `_travar` (L25, 10 linhas)
- `_destravar` (L37, 10 linhas)
- `_ler_pid` (L49, 6 linhas)
- classe `TravaInstancia` (L57, 23 linhas)
- `adquirir_trava_instancia` (L82, 21 linhas)
- `aviso_padrao` (L105, 2 linhas)
- `criar_tratador_erro` (L109, 17 linhas)
- `criar_tarefa_monitorada` (L128, 14 linhas)

## Testes que usam (1)

- `tests/test_operacao_bot.py`

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
