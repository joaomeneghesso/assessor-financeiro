---
tipo: modulo
grupo: Camada de negócio e interpretação
linhas: 328
tags: [modulo, camada-de-negocio-e-interpretacao]
---
# assessor_orientacao.py

> Orientação local explicável. Não consulta APIs, não decide pagamentos e não grava finanças.

**Grupo:** [[Camada de negócio e interpretação]] · **Linhas:** 328 · **Funções:** 18 · **Classes:** 0

## Usa

- [[config.py]]
- [[database.py]]
- [[money.py]]
- [[saldo_resumo.py]] *(importação tardia, dentro de função)*
- [[services.py]] *(importação tardia, dentro de função)*
- [[telegram_design.py]]

## Usado por

- [[dashboard_metricas.py]] — `mes_anterior`, `normalizar`
- [[telegram_alertas.py]] — `coletar`, `em_silencio`, `preferencias`
- [[telegram_experiencia.py]] — `barra`, `coletar`, `configurar_saldo`, `eh_pergunta_compra`, `em_silencio`, `extrair_pergunta_compra`, `normalizar`, `preferencias` +6

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `coletar` | 80 | 2 | 1 | Um retrato por renderização, obtido do motor RC2 sem fórmulas de saldo paralelas. |
| `preferencias` | 21 | 2 | 1 |  |
| `em_silencio` | 70 | 2 | 0 |  |
| `normalizar` | 18 | 2 | 0 |  |
| `barra` | 212 | 1 | 1 | Barra de progresso ▰▱. Passar de 100% enche a barra; >0% mostra ao menos 1 bloco. |
| `configurar_saldo` | 51 | 1 | 1 | Mesmo saldo inicial do motor, com prévia otimista e auditoria na mesma transação. |
| `eh_pergunta_compra` | 255 | 1 | 1 |  |
| `extrair_pergunta_compra` | 258 | 1 | 1 | 'posso comprar um celular de 3000 em 10x' -> dict(total_centavos, parcelas, descricao, credito); None sem val… |
| `salvar_preferencia` | 31 | 1 | 1 |  |
| `situacao_limites` | 218 | 1 | 1 | B5: gasto, ritmo e margem diária por limite. Não consulta nem grava nada. |
| `mes_anterior` | 75 | 1 | 0 |  |
| `reconhecer_pergunta` | 183 | 1 | 0 |  |
| `salvar_preferencias` | 41 | 1 | 0 |  |
| `simular_compra` | 288 | 1 | 0 | B7: 'Deve sobrar' antes e depois da compra, com o motor canônico (resumir_saldo). |
| `veredito_compra` | 317 | 1 | 0 | Leitura descritiva (nunca recomendação): dict(tom, emoji, mes, valor, pct). |
| `validar_preferencia` | 34 | 0 | 1 |  |

## Tudo que define

- `normalizar` (L18, 2 linhas)
- `preferencias` (L21, 9 linhas)
- `salvar_preferencia` (L31, 2 linhas)
- `validar_preferencia` (L34, 6 linhas)
- `salvar_preferencias` (L41, 9 linhas)
- `configurar_saldo` (L51, 18 linhas) — Mesmo saldo inicial do motor, com prévia otimista e auditoria na mesma transação.
- `em_silencio` (L70, 4 linhas)
- `mes_anterior` (L75, 4 linhas)
- `coletar` (L80, 77 linhas) — Um retrato por renderização, obtido do motor RC2 sem fórmulas de saldo paralelas.
- `reconhecer_pergunta` (L183, 15 linhas)
- `_dec` (L209, 2 linhas)
- `barra` (L212, 5 linhas) — Barra de progresso ▰▱. Passar de 100% enche a barra; >0% mostra ao menos 1 bloco.
- `situacao_limites` (L218, 34 linhas) — B5: gasto, ritmo e margem diária por limite. Não consulta nem grava nada.
- `eh_pergunta_compra` (L255, 2 linhas)
- `extrair_pergunta_compra` (L258, 26 linhas) — 'posso comprar um celular de 3000 em 10x' -> dict(total_centavos, parcelas, descricao, credito); None sem val…
- `_somar_mes` (L285, 2 linhas)
- `simular_compra` (L288, 28 linhas) — B7: 'Deve sobrar' antes e depois da compra, com o motor canônico (resumir_saldo).
- `veredito_compra` (L317, 12 linhas) — Leitura descritiva (nunca recomendação): dict(tom, emoji, mes, valor, pct).

## Testes que usam (5)

- `tests/test_alertas_fase1.py`
- `tests/test_bloco_b_datas_comandos.py`
- `tests/test_experiencia_identidade_onda2c.py`
- `tests/test_limites_comprar_fase2.py`
- `tests/test_revisao_saldo_integridade.py`

## No mapa de rotas

- **Módulo (1):** [[mod_assessor_orientacao.py-e9925|assessor_orientacao.py]]
- **Funções no mapa (5):** [[fn_assessor_orientacao.coletar-df8f0|assessor_orientacao.coletar]], [[fn_assessor_orientacao.configurar_saldo-1ec8e|assessor_orientacao.configurar_saldo]], [[fn_assessor_orientacao.preferencias-719d2|assessor_orientacao.preferencias]], [[fn_assessor_orientacao.reconhecer_pergunta-5191e|assessor_orientacao.reconhecer_pergunta]], [[fn_assessor_orientacao.salvar_preferencias-c89c1|assessor_orientacao.salvar_preferencias]]
- **Chamadas de serviço (12):** [[fn_orientacao.barra-bfa5b|orientacao.barra]], [[fn_orientacao.coletar-ba856|coletar]], [[fn_orientacao.configurar_saldo-11f0c|configurar_saldo]], [[fn_orientacao.eh_pergunta_compra-461c2|orientacao.eh_pergunta_compra]], [[fn_orientacao.em_silencio-adc37|orientacao.em_silencio]], [[fn_orientacao.extrair_pergunta_compra-851a2|orientacao.extrair_pergunta_compra]], [[fn_orientacao.preferencias-f52ab|preferencias]], [[fn_orientacao.reconhecer_pergunta-2077d|reconhecer_pergunta]], [[fn_orientacao.salvar_preferencia-50ee3|salvar_preferencia]], [[fn_orientacao.salvar_preferencias-f9905|salvar_preferencias]], [[fn_orientacao.simular_compra-78064|orientacao.simular_compra]], [[fn_orientacao.situacao_limites-eb39b|orientacao.situacao_limites]]

## Documentos que citam

- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
