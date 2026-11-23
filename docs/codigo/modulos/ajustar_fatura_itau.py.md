---
tipo: modulo
grupo: Núcleo financeiro
linhas: 241
tags: [modulo, nucleo-financeiro]
---
# ajustar_fatura_itau.py

**Grupo:** [[Núcleo financeiro]] · **Linhas:** 241 · **Funções:** 9 · **Classes:** 0

## Usa

- [[sqlite_backup.py]]

## Usado por

- (ninguém no código de produção; ponto de entrada ou script)

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `aplicar` | 134 | 0 | 2 |  |

## Tudo que define

- `add_month_iso` (L17, 6 linhas)
- `add_month_ym` (L25, 5 linhas)
- `norm_sql` (L32, 2 linhas)
- `selecionar_alvos` (L36, 55 linhas)
- `ja_aplicado` (L93, 6 linhas)
- `banco_usa_competencia_fatura` (L101, 13 linhas) — True quando há lançamentos com competência de fatura explícita.
- `montar_resumo` (L116, 16 linhas)
- `aplicar` (L134, 92 linhas)
- `main` (L228, 10 linhas)

## Testes que usam (2)

- `tests/test_bloco_c_auditoria.py`
- `tests/test_rc1514_ajuste_fatura_itau.py`

## Documentos que citam

- [[reavaliacao/01_arquitetura]]
- [[reavaliacao/08_onda3_etapa1]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
