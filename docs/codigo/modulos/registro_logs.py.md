---
tipo: modulo
grupo: Entrada e operação
linhas: 69
tags: [modulo, entrada-e-operacao]
---
# registro_logs.py

> Log em arquivo para avisos e erros, sem mudar o que aparece no console.

**Grupo:** [[Entrada e operação]] · **Linhas:** 69 · **Funções:** 2 · **Classes:** 0

## Usa

- (nenhum módulo do projeto)

## Usado por

- [[app.py]] — `avisar_se_fuso_divergente`, `configurar_logs`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `avisar_se_fuso_divergente` | 52 | 1 | 1 | Avisa (sem alterar nada) se o relógio do PC não está em UTC-3. |
| `configurar_logs` | 19 | 1 | 1 |  |

## Tudo que define

- `configurar_logs` (L19, 31 linhas)
- `avisar_se_fuso_divergente` (L52, 18 linhas) — Avisa (sem alterar nada) se o relógio do PC não está em UTC-3.

## Testes que usam (1)

- `tests/test_confiabilidade_bloco2.py`

## Documentos que citam

- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
