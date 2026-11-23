---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 494
tags: [modulo, telegram-telas-e-conversa]
---
# telegram_registros.py

> Gravação confirmada, atômica e auditada usando o schema já existente.

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 494 · **Funções:** 16 · **Classes:** 0

## Usa

- [[categorias.py]]
- [[compromissos.py]] *(importação tardia, dentro de função)*
- [[conciliacao.py]] *(importação tardia, dentro de função)*
- [[database.py]]
- [[faturas_competencia.py]]
- [[money.py]]
- [[relogio.py]]
- [[services.py]] *(importação tardia, dentro de função)*

## Usado por

- [[telegram_experiencia.py]] — `buscar_duplicata`, `confirmar_pagamento_fatura`, `confirmar_registro`, `corrigir_categoria_registro`, `corrigir_data_registro`, `desfazer_registro`, `evento_registro_recente`, `motivo_bloqueio_data` +2

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `confirmar_pagamento_fatura` | 221 | 1 | 3 | Confirma um pagamento de fatura de forma idempotente e revalidada. |
| `buscar_duplicata` | 329 | 1 | 1 | Somente leitura. Lançamento existente que parece o mesmo que `t`, ou None. |
| `confirmar_registro` | 90 | 1 | 1 | Uma confirmação repetida não insere novamente, mesmo entre processos. |
| `corrigir_categoria_registro` | 464 | 1 | 1 | Troca só a categoria, uma vez por `chave`, com auditoria antes/depois. |
| `desfazer_registro` | 185 | 1 | 1 | Remove só as linhas inalteradas do evento, em uma única transação. |
| `evento_registro_recente` | 380 | 1 | 1 | Chave do evento `telegram_registro` que criou a linha, se ainda dá para desfazer pela barra. |
| `validar_transacao` | 37 | 1 | 1 |  |
| `corrigir_data_registro` | 426 | 1 | 0 | Troca só a data, uma vez por `chave`, com auditoria antes/depois na mesma transação. |
| `motivo_bloqueio_data` | 412 | 1 | 0 | Por que a data deste lançamento não pode ser corrigida aqui (None = pode). |
| `validar_campo_textual` | 21 | 1 | 0 |  |

## Tudo que define

- `validar_campo_textual` (L21, 14 linhas)
- `validar_transacao` (L37, 28 linhas)
- `_auditar` (L67, 8 linhas)
- `_inserir` (L77, 11 linhas)
- `confirmar_registro` (L90, 55 linhas) — Uma confirmação repetida não insere novamente, mesmo entre processos.
- `_dependencia_posterior` (L147, 36 linhas) — Mensagem de recusa quando algo gravado DEPOIS do registro depende dele.
- `desfazer_registro` (L185, 34 linhas) — Remove só as linhas inalteradas do evento, em uma única transação.
- `confirmar_pagamento_fatura` (L221, 91 linhas) — Confirma um pagamento de fatura de forma idempotente e revalidada.
- `_norm_texto` (L320, 3 linhas)
- `_centavos` (L325, 2 linhas)
- `buscar_duplicata` (L329, 36 linhas) — Somente leitura. Lançamento existente que parece o mesmo que `t`, ou None.
- `_linhas_inalteradas` (L367, 11 linhas)
- `evento_registro_recente` (L380, 30 linhas) — Chave do evento `telegram_registro` que criou a linha, se ainda dá para desfazer pela barra.
- `motivo_bloqueio_data` (L412, 12 linhas) — Por que a data deste lançamento não pode ser corrigida aqui (None = pode).
- `corrigir_data_registro` (L426, 36 linhas) — Troca só a data, uma vez por `chave`, com auditoria antes/depois na mesma transação.
- `corrigir_categoria_registro` (L464, 31 linhas) — Troca só a categoria, uma vez por `chave`, com auditoria antes/depois.

## Testes que usam (5)

- `tests/test_bloco_c_ciclo_vida.py`
- `tests/test_equivalencia_calculos_onda2.py`
- `tests/test_fatura_paga_mes_posterior.py`
- `tests/test_mutantes_rede_seguranca.py`
- `tests/test_pos_salvar_fase2.py`

## No mapa de rotas

- **Módulo (1):** [[mod_telegram_registros.py-6b0ea|telegram_registros.py]]
- **Funções no mapa (5):** [[fn_telegram_registros._dependencia_posterior-d179c|telegram_registros._dependencia_posterior]], [[fn_telegram_registros.confirmar_pagamento_fatura-ded85|telegram_registros.confirmar_pagamento_fatura]], [[fn_telegram_registros.confirmar_registro-9a9b2|telegram_registros.confirmar_registro]], [[fn_telegram_registros.desfazer_registro-d77a5|telegram_registros.desfazer_registro]], [[fn_telegram_registros.validar_transacao-8ba78|telegram_registros.validar_transacao]]
- **Chamadas de serviço (5):** [[fn_telegram_registros.buscar_duplicata-f51a5|telegram_registros.buscar_duplicata]], [[fn_telegram_registros.corrigir_categoria_registro-0464d|telegram_registros.corrigir_categoria_registro]], [[fn_telegram_registros.corrigir_data_registro-55931|telegram_registros.corrigir_data_registro]], [[fn_telegram_registros.evento_registro_recente-3aace|telegram_registros.evento_registro_recente]], [[fn_telegram_registros.validar_campo_textual-c5180|telegram_registros.validar_campo_textual]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
