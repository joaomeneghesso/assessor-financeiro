---
tipo: modulo
grupo: Camada de negócio e interpretação
linhas: 745
tags: [modulo, camada-de-negocio-e-interpretacao]
---
# parser_financeiro.py

**Grupo:** [[Camada de negócio e interpretação]] · **Linhas:** 745 · **Funções:** 30 · **Classes:** 2

## Usa

- [[categorias.py]]
- [[money.py]]

## Usado por

- [[registro_conversa.py]] — `detectar_categoria`, `interpretar_expressao_data`, `mensagem_varios_lancamentos`, `numero_e_de_produto`, `parece_codigo_ou_texto_longo`, `texto_com_varios_lancamentos`, `texto_numero_para_float`
- [[services.py]] — `detectar_categoria_explicita`, `parse_mensagem`
- [[telegram_experiencia.py]] — `parse_mensagem`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `parse_mensagem` | 681 | 2 | 4 |  |
| `detectar_categoria` | 508 | 1 | 1 |  |
| `detectar_categoria_explicita` | 423 | 1 | 0 |  |
| `interpretar_expressao_data` | 128 | 1 | 0 | Converte uma data curta/natural em ``date``; ``None`` se não for uma. |
| `mensagem_varios_lancamentos` | 209 | 1 | 0 |  |
| `numero_e_de_produto` | 194 | 1 | 0 | O número vem colado a um nome de produto ("iphone 15"): não é preço. |
| `parece_codigo_ou_texto_longo` | 50 | 1 | 0 |  |
| `texto_com_varios_lancamentos` | 200 | 1 | 0 | Quantidade de lançamentos em texto multilinha (0 se for uma só frase). |
| `texto_numero_para_float` | 74 | 1 | 0 |  |

## Tudo que define

- classe `MaisDeUmValor` (L38, 2 linhas) — Duas quantias na mesma frase: o parser não adivinha qual é a certa.
- classe `DataFutura` (L42, 2 linhas) — Lançamento é de algo realizado; "amanhã" não pode cair em hoje.
- `normalizar_texto` (L46, 2 linhas)
- `parece_codigo_ou_texto_longo` (L50, 22 linhas)
- `texto_numero_para_float` (L74, 28 linhas)
- `interpretar_expressao_data` (L128, 37 linhas) — Converte uma data curta/natural em ``date``; ``None`` se não for uma.
- `_resolver_dia_mes` (L167, 9 linhas)
- `expressoes_de_data` (L178, 8 linhas) — Ocorrências de data curta/natural, ignorando "(3/10)" (notação de parcela).
- `numero_e_de_produto` (L194, 4 linhas) — O número vem colado a um nome de produto ("iphone 15"): não é preço.
- `texto_com_varios_lancamentos` (L200, 7 linhas) — Quantidade de lançamentos em texto multilinha (0 se for uma só frase).
- `mensagem_varios_lancamentos` (L209, 3 linhas)
- `converter_valor_numerico` (L214, 2 linhas)
- `encontrar_numeros` (L218, 14 linhas)
- `detectar_valor_total_por_parcela` (L234, 20 linhas)
- `numero_esta_em_contexto_de_data` (L256, 10 linhas) — Evita que partes de datas ISO sejam interpretadas como valor monetário.
- `numero_esta_em_contexto_de_parcela` (L268, 16 linhas) — Marca somente o numero que representa a quantidade de parcelas.
- `aplicar_escala` (L286, 10 linhas) — "1,5 mil", "R$ 2 mil": só escala o número que já seria escolhido como valor.
- `_numero_tem_marca_de_dinheiro` (L298, 7 linhas) — R$ antes, "reais" depois ou casas decimais/milhar: é uma quantia, não um código.
- `_escolher_candidato` (L312, 14 linhas) — Primeiro candidato, exceto quando ele é número do nome do item.
- `extrair_valor_numerico` (L328, 69 linhas)
- `extrair_valor_por_extenso` (L399, 15 linhas)
- `extrair_valor` (L416, 5 linhas)
- `detectar_categoria_explicita` (L423, 6 linhas)
- `limpar_categoria_explicita` (L431, 2 linhas)
- `detectar_parcelas` (L435, 16 linhas)
- `detectar_data` (L453, 32 linhas)
- `detectar_tipo` (L487, 19 linhas)
- `detectar_categoria` (L508, 5 linhas)
- `detectar_forma_pagamento` (L515, 23 linhas)
- `detectar_conta` (L540, 38 linhas)
- `limpar_descricao` (L580, 99 linhas)
- `parse_mensagem` (L681, 65 linhas)

## Testes que usam (4)

- `tests/test_categorizacao_unificada.py`
- `tests/test_parser_legado_seguro.py`
- `tests/test_parser_legado_valor_data_cmd.py`
- `tests/test_parser_tolerante_fase2.py`

## No mapa de rotas

- **Funções no mapa (2):** [[fn_parser_financeiro.detectar_categoria-b7ce6|parser_financeiro.detectar_categoria]], [[fn_parser_financeiro.parse_mensagem-7c39b|parser_financeiro.parse_mensagem]]

## Documentos que citam

- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
