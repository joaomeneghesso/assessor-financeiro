---
tipo: modulo
grupo: Camada de negócio e interpretação
linhas: 348
tags: [modulo, camada-de-negocio-e-interpretacao]
---
# registro_conversa.py

> Extrai apenas os dados informados em um registro, sem banco, rede ou IA.

**Grupo:** [[Camada de negócio e interpretação]] · **Linhas:** 348 · **Funções:** 6 · **Classes:** 0

## Usa

- [[categorias.py]]
- [[money.py]]
- [[parser_financeiro.py]]

## Usado por

- [[telegram_experiencia.py]] — `categoria_da_descricao`, `data_informada`, `descricao_valida`, `extrair_campos`, `valor_informado`
- [[telegram_midia.py]] — `data_informada`, `extrair_campos`, `normalizar`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `extrair_campos` | 97 | 2 | 4 | Reconhece campos explícitos; rejeita valores/contas/formas conflitantes. |
| `data_informada` | 53 | 2 | 1 | Data completa, relativa ou curta ("15/10", "dia 15", "segunda"). |
| `normalizar` | 22 | 1 | 1 |  |
| `categoria_da_descricao` | 93 | 1 | 0 |  |
| `descricao_valida` | 78 | 1 | 0 |  |
| `valor_informado` | 84 | 1 | 0 |  |

## Tudo que define

- `normalizar` (L22, 3 linhas)
- `data_informada` (L53, 23 linhas) — Data completa, relativa ou curta ("15/10", "dia 15", "segunda").
- `descricao_valida` (L78, 4 linhas)
- `valor_informado` (L84, 7 linhas)
- `categoria_da_descricao` (L93, 2 linhas)
- `extrair_campos` (L97, 252 linhas) — Reconhece campos explícitos; rejeita valores/contas/formas conflitantes.

## Testes que usam (4)

- `tests/test_categorizacao_unificada.py`
- `tests/test_parser_legado_seguro.py`
- `tests/test_parser_tolerante_fase2.py`
- `tests/test_registro_valor_por_voz.py`

## No mapa de rotas

- **Módulo (1):** [[mod_registro_conversa.py-b630c|registro_conversa.py]]
- **Funções no mapa (4):** [[fn_registro_conversa.categoria_da_descricao-56c15|registro_conversa.categoria_da_descricao]], [[fn_registro_conversa.data_informada-7335b|registro_conversa.data_informada]], [[fn_registro_conversa.extrair_campos-776ac|registro_conversa.extrair_campos]], [[fn_registro_conversa.valor_informado-4b17a|registro_conversa.valor_informado]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
