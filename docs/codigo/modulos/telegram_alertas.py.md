---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 203
tags: [modulo, telegram-telas-e-conversa]
---
# telegram_alertas.py

> Agenda discreta com preferências persistentes e deduplicação por janela de envio.

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 203 · **Funções:** 15 · **Classes:** 0

## Usa

- [[assessor_orientacao.py]] *(importação tardia, dentro de função)*
- [[database.py]]
- [[telegram_design.py]]
- [[telegram_execucao.py]]
- [[telegram_experiencia.py]] *(importação tardia, dentro de função)*
- [[telegram_recursos.py]] *(importação tardia, dentro de função)*

## Usado por

- [[app.py]] — `callback`, `rotina`
- [[telegram_experiencia.py]] — `contagens`, `montar_aviso`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `callback` | 55 | 1 | 1 |  |
| `montar_aviso` | 131 | 1 | 1 | Avisos sem nomes, contas ou descrições. Valores só com a preferência alerta_valores (padrão desligada). |
| `contagens` | 103 | 1 | 0 | Conta (sem nomes) as obrigações em aberto: vencidas, de hoje, de amanhã e dos demais dias da janela. |
| `rotina` | 196 | 1 | 0 |  |
| `controles` | 15 | 0 | 2 | Callbacks de alerta independentes dos tokens do formulário em andamento. |
| `adiar` | 36 | 0 | 1 |  |
| `executar_janela` | 160 | 0 | 1 |  |
| `reservar` | 87 | 0 | 1 |  |
| `sonecas` | 45 | 0 | 1 |  |

## Tudo que define

- `controles` (L15, 20 linhas) — Callbacks de alerta independentes dos tokens do formulário em andamento.
- `adiar` (L36, 8 linhas)
- `sonecas` (L45, 9 linhas)
- `callback` (L55, 22 linhas)
- `elegiveis` (L78, 8 linhas)
- `reservar` (L87, 8 linhas)
- `_valor` (L96, 3 linhas)
- `_brl` (L100, 2 linhas)
- `contagens` (L103, 14 linhas) — Conta (sem nomes) as obrigações em aberto: vencidas, de hoje, de amanhã e dos demais dias da janela.
- `_n` (L118, 1 linhas)
- `_habito_sem_registro_hoje` (L120, 10 linhas) — Critério determinístico: o titular tem o hábito se registrou em >=3 dias distintos dos 7 dias
- `montar_aviso` (L131, 28 linhas) — Avisos sem nomes, contas ou descrições. Valores só com a preferência alerta_valores (padrão desligada).
- `executar_janela` (L160, 28 linhas)
- `_snapshot_alerta` (L190, 5 linhas)
- `rotina` (L196, 8 linhas)

## Testes que usam (2)

- `tests/test_alertas_fase1.py`
- `tests/test_inovacoes_410.py`

## No mapa de rotas

- **Módulo (1):** [[mod_telegram_alertas.py-deb44|telegram_alertas.py]]
- **Estado da sessão (1):** [[state_ALERT_ACTIONS-d9136|ALERT_ACTIONS]]
- **Funções no mapa (8):** [[fn_telegram_alertas._snapshot_alerta-02723|telegram_alertas._snapshot_alerta]], [[fn_telegram_alertas.adiar-a92a0|telegram_alertas.adiar]], [[fn_telegram_alertas.controles-5e527|telegram_alertas.controles]], [[fn_telegram_alertas.elegiveis-53461|telegram_alertas.elegiveis]], [[fn_telegram_alertas.executar_janela-a11fc|telegram_alertas.executar_janela]], [[fn_telegram_alertas.montar_aviso-23d00|telegram_alertas.montar_aviso]], [[fn_telegram_alertas.reservar-1a6f7|telegram_alertas.reservar]], [[fn_telegram_alertas.sonecas-d0a3f|telegram_alertas.sonecas]]
- **Tratadores (2):** [[fn_telegram_alertas.callback-80f31|telegram_alertas.callback]], [[fn_telegram_alertas.rotina-a3d59|telegram_alertas.rotina]]

## Documentos que citam

- [[reavaliacao/01_arquitetura]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
