---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 242
tags: [modulo, telegram-telas-e-conversa]
---
# sugestoes_comando.py

> Sugestões de comando quando o texto digitado não é reconhecido.

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 242 · **Funções:** 10 · **Classes:** 0

## Usa

- (nenhum módulo do projeto)

## Usado por

- [[services.py]] — `mensagem_comando_nao_reconhecido`, `mensagem_sem_valor`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `mensagem_comando_nao_reconhecido` | 214 | 1 | 1 |  |
| `mensagem_sem_valor` | 232 | 1 | 1 |  |
| `sugerir_comandos` | 171 | 0 | 1 | Até `limite` comandos do catálogo parecidos com `texto` (mais parecido primeiro). |

## Tudo que define

- `_norm` (L122, 6 linhas)
- `_palavras` (L130, 2 linhas)
- `_sim_palavra` (L134, 6 linhas)
- `_melhor` (L142, 2 linhas)
- `_pontuar` (L154, 15 linhas)
- `sugerir_comandos` (L171, 29 linhas) — Até `limite` comandos do catálogo parecidos com `texto` (mais parecido primeiro).
- `_truncar` (L202, 3 linhas)
- `_acao_pedida` (L207, 5 linhas)
- `mensagem_comando_nao_reconhecido` (L214, 16 linhas)
- `mensagem_sem_valor` (L232, 11 linhas)

## Testes que usam (1)

- `tests/test_sugestoes_comando.py`

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
