---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 298
tags: [modulo, telegram-telas-e-conversa]
---
# fixos_interface.py

> Telas e formulário de edição de fixos. Gravação somente após a prévia.

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 298 · **Funções:** 19 · **Classes:** 0

## Usa

- [[compromissos.py]]
- [[database.py]]
- [[fixos_edicao.py]]
- [[fixos_variaveis.py]] *(importação tardia, dentro de função)*
- [[fixos_variaveis_acoes.py]] *(importação tardia, dentro de função)*
- [[telegram_experiencia.py]] *(importação tardia, dentro de função)*

## Usado por

- [[telegram_experiencia.py]] — `acao`, `interpretar_mes`, `retomar`, `texto`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `acao` | 239 | 1 | 3 |  |
| `texto` | 272 | 1 | 3 |  |
| `interpretar_mes` | 15 | 1 | 1 | Converte texto livre de mês em 'AAAA-MM'; None se não for um mês válido. |
| `retomar` | 220 | 1 | 1 |  |
| `listar` | 169 | 0 | 3 |  |
| `campos` | 144 | 0 | 2 |  |
| `detalhe` | 73 | 0 | 2 |  |

## Tudo que define

- `_sem_acento` (L12, 2 linhas)
- `interpretar_mes` (L15, 22 linhas) — Converte texto livre de mês em 'AAAA-MM'; None se não for um mês válido.
- `_rotulo_mes` (L38, 2 linhas)
- `_nav` (L43, 3 linhas)
- `_dica_codigo` (L47, 2 linhas)
- `_rotulo_forma` (L50, 3 linhas)
- `_exibir` (L54, 3 linhas)
- `_mes_prox` (L58, 4 linhas)
- `_tela_mes` (L63, 4 linhas)
- `screen` (L69, 3 linhas)
- `detalhe` (L73, 14 linhas)
- `_variavel` (L89, 54 linhas) — Telas de "valor variável": escolher o histórico, prévia, ativar/desligar (grava só ao confirmar).
- `campos` (L144, 13 linhas)
- `_resumo_categorias` (L158, 10 linhas) — {categoria: [total do mês, qtd, qtd no cartão]} dos fixos vigentes no mês (variável = estimativa).
- `listar` (L169, 41 linhas)
- `previa` (L211, 8 linhas)
- `retomar` (L220, 17 linhas)
- `acao` (L239, 32 linhas)
- `texto` (L272, 27 linhas)

## Testes que usam (3)

- `tests/test_fixos_identidade_visual.py`
- `tests/test_fixos_mes_botoes_onda1.py`
- `tests/test_fixos_vigencia_integridade.py`

## No mapa de rotas

- **Ações (4):** [[act_fixed_var-bfa5a|fixed_var]], [[act_fixed_var_off-6a57c|fixed_var_off]], [[act_fixed_var_off_ok-d823e|fixed_var_off_ok]], [[act_fixed_var_ok-89822|fixed_var_ok]]
- **Chamadas de serviço (3):** [[fn_fixos_interface.acao-b7cd3|acao]], [[fn_fixos_interface.retomar-ea2c7|fixos_interface.retomar]], [[fn_fixos_interface.texto-9739b|texto]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
