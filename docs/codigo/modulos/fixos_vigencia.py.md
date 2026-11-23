---
tipo: modulo
grupo: Núcleo financeiro
linhas: 50
tags: [modulo, nucleo-financeiro]
---
# fixos_vigencia.py

> Identidade de versões pela auditoria existente; nenhuma inferência por nome.

**Grupo:** [[Núcleo financeiro]] · **Linhas:** 50 · **Funções:** 3 · **Classes:** 0

## Usa

- (nenhum módulo do projeto)

## Usado por

- [[database.py]] — `garantir_sem_sobreposicao`, `ids_da_serie`
- [[fixos_edicao.py]] — `garantir_sem_sobreposicao`
- [[services.py]] — `garantir_sem_sobreposicao`, `periodos_sobrepostos`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `garantir_sem_sobreposicao` | 39 | 3 | 0 |  |
| `periodos_sobrepostos` | 6 | 1 | 1 |  |
| `ids_da_serie` | 18 | 1 | 0 |  |

## Tudo que define

- `periodos_sobrepostos` (L6, 10 linhas)
- `ids_da_serie` (L18, 19 linhas)
- `garantir_sem_sobreposicao` (L39, 12 linhas)

## Testes que usam (1)

- `tests/test_mutantes_rede_seguranca.py`

## Documentos que citam

- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
