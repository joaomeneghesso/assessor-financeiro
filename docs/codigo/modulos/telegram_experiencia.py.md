---
tipo: modulo
grupo: Telegram (telas e conversa)
linhas: 5543
tags: [modulo, telegram-telas-e-conversa]
---
# telegram_experiencia.py

> Interface Telegram 2.0: apresentação curta, navegação e registros revisáveis.

**Grupo:** [[Telegram (telas e conversa)]] · **Linhas:** 5543 · **Funções:** 26 · **Classes:** 3

> [!warning] Linha de base
> Limite de 5546 linhas (hoje 5543). Este arquivo não pode crescer: código novo vai em módulo próprio.

## Usa

- [[assessor_ia_local.py]] *(importação tardia, dentro de função)*
- [[assessor_orientacao.py]]
- [[busca_lancamentos.py]] *(importação tardia, dentro de função)*
- [[categorias.py]] *(importação tardia, dentro de função)*
- [[categorias_pessoais.py]] *(importação tardia, dentro de função)*
- [[compromissos.py]] *(importação tardia, dentro de função)*
- [[conciliacao.py]]
- [[config.py]]
- [[consultas_pagar.py]] *(importação tardia, dentro de função)*
- [[consultas_rapidas.py]] *(importação tardia, dentro de função)*
- [[contas_inativas.py]]
- [[dashboard_metricas.py]] *(importação tardia, dentro de função)*
- [[database.py]]
- [[efeito_baixa.py]]
- [[estado_runtime.py]] *(importação tardia, dentro de função)*
- [[faturas_competencia.py]]
- [[fixos_interface.py]] *(importação tardia, dentro de função)*
- [[money.py]]
- [[parser_financeiro.py]]
- [[registro_conversa.py]] *(importação tardia, dentro de função)*
- [[relogio.py]]
- [[roteamento_seguro.py]] *(importação tardia, dentro de função)*
- [[saldo_resumo.py]]
- [[saldos_edicao.py]] *(importação tardia, dentro de função)*
- [[services.py]]
- [[sugestoes_lancamento.py]]
- [[telegram_alertas.py]] *(importação tardia, dentro de função)*
- [[telegram_aprendizado.py]]
- [[telegram_design.py]]
- [[telegram_execucao.py]]
- [[telegram_midia.py]] *(importação tardia, dentro de função)*
- [[telegram_recursos.py]] *(importação tardia, dentro de função)*
- [[telegram_registros.py]]
- [[telegram_streaming.py]] *(importação tardia, dentro de função)*
- [[telegram_visuais.py]] *(importação tardia, dentro de função)*
- [[version.py]]

## Usado por

- [[app.py]] — `Screen`, `clear_service_pending`, `dashboard_route`, `dispatch_callback`, `dispatch_text`, `norm`, `run_experience`, `safe` +2
- [[dashboard_metricas.py]] — `money`, `month_label`
- [[fixos_interface.py]] — `Screen`, `money`
- [[telegram_alertas.py]] — `Experience`, `Screen`, `run_experience`, `send_screen`, `session_key`
- [[telegram_midia.py]] — `Screen`, `money`, `safe`, `send_screen`, `session_key`
- [[telegram_recursos.py]] — `Screen`, `money`, `month_label`, `safe`
- [[tools__medir_desempenho.py|tools/medir_desempenho.py]] — `Experience`
- [[tools__medir_rotina.py|tools/medir_rotina.py]] — `Experience`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `Screen` | 360 | 5 | 5 |  |
| `money` | 270 | 4 | 7 |  |
| `Experience` | 421 | 3 | 47 |  |
| `send_screen` | 4991 | 3 | 2 |  |
| `session_key` | 4984 | 3 | 1 |  |
| `safe` | 254 | 3 | 0 |  |
| `month_label` | 308 | 2 | 0 |  |
| `run_experience` | 4976 | 2 | 0 | Executa uma operação completa da experiência fora do event loop. |
| `dispatch_text` | 5200 | 1 | 6 |  |
| `clear_service_pending` | 5539 | 1 | 2 |  |
| `dispatch_callback` | 5448 | 1 | 1 |  |
| `dashboard_route` | 242 | 1 | 0 | Comandos de gráfico têm prioridade sobre a intenção natural de resumo. |
| `norm` | 237 | 1 | 0 |  |
| `cortar` | 259 | 0 | 1 | Rótulo curto sem cortar no meio da palavra: espaços colapsados e "…" quando encurta. |
| `data_br` | 302 | 0 | 1 | '2026-11-10' → '10/11/2026' (só exibição); outro texto volta como veio. |
| `today` | 289 | 0 | 1 |  |

## Tudo que define

- `norm` (L237, 3 linhas)
- `dashboard_route` (L242, 10 linhas) — Comandos de gráfico têm prioridade sobre a intenção natural de resumo.
- `safe` (L254, 3 linhas)
- `cortar` (L259, 9 linhas) — Rótulo curto sem cortar no meio da palavra: espaços colapsados e "…" quando encurta.
- `money` (L270, 3 linhas)
- `_private_key_screen` (L281, 6 linhas) — Aplica o modo Ocultar a telas que recebem (key, ...) e não passam por render().
- `today` (L289, 2 linhas)
- `month_shift` (L293, 7 linhas)
- `data_br` (L302, 4 linhas) — '2026-11-10' → '10/11/2026' (só exibição); outro texto volta como veio.
- `month_label` (L308, 4 linhas)
- `installment_plan` (L314, 20 linhas) — Retorna o cronograma exato usado por confirmar_registro, em centavos.
- `installment_distribution_text` (L336, 13 linhas) — Resume valores distintos sem sugerir que todas as parcelas são idênticas.
- `copy_text_value` (L351, 6 linhas) — Texto simples seguro para CopyTextButton (limite nativo: 256 chars).
- classe `Screen` (L360, 13 linhas)
- classe `Session` (L376, 43 linhas)
- classe `Experience` (L421, 4541 linhas)
- `_runtime_store` (L4964, 7 linhas)
- `run_experience` (L4976, 6 linhas) — Executa uma operação completa da experiência fora do event loop.
- `session_key` (L4984, 5 linhas)
- `send_screen` (L4991, 141 linhas)
- `_invalidar_preservando_pausa` (L5134, 14 linhas) — Como EXPERIENCE.invalidate, mas um registro pausado continua guardado
- `_draft_summary` (L5150, 11 linhas) — Uma linha com o que já foi preenchido no rascunho (ex.: Uber · R$ 13,32).
- `_parece_resposta_de_etapa` (L5170, 5 linhas) — Resposta curta típica de uma etapa (valor, data, forma, sim/não), sem sentido fora do fluxo.
- `_tela_fluxo_expirado` (L5177, 4 linhas)
- `parece_outro_lancamento` (L5183, 4 linhas) — Frase que claramente é um lançamento novo: verbo de registro + valor (ex.: "gastei 15 no café").
- `dispatch_text` (L5200, 212 linhas)
- `expired_callback_screen` (L5414, 32 linhas) — Retoma um clique sem token válido sem presumir o estado financeiro anterior.
- `dispatch_callback` (L5448, 89 linhas)
- `clear_service_pending` (L5539, 5 linhas)

## Testes que usam (52)

- `tests/test_ajustar_saldo_seletor.py`
- `tests/test_baixa_fixo_conta.py`
- `tests/test_bloco_a_protecao_dados.py`
- `tests/test_bloco_b_datas_comandos.py`
- `tests/test_bloco_b_saldos_pagamentos.py`
- `tests/test_bloco_d_usabilidade.py`
- `tests/test_botoes_confirmacao.py`
- `tests/test_botoes_finais_regressao.py`
- `tests/test_busca_lancamentos.py`
- `tests/test_categorizacao_unificada.py`
- `tests/test_confiabilidade_413.py`
- `tests/test_confiabilidade_bloco2.py`
- `tests/test_consultas_periodo.py`
- `tests/test_contas_gerenciar.py`
- `tests/test_dashboard_metricas_412.py`
- `tests/test_dashboard_rota_entrega.py`
- `tests/test_experiencia_identidade_onda2c.py`
- `tests/test_fatura_conferencia.py`
- `tests/test_fixos_identidade_visual.py`
- `tests/test_fixos_mes_botoes_onda1.py`
- … +32

## No mapa de rotas

- **Módulo (1):** [[mod_telegram_experiencia.py-c6fa1|telegram_experiencia.py]]
- **Telas (61):** [[screen_accounts-cc0c6|accounts]], [[screen_accounts_manage-5980c|accounts_manage]], [[screen_advanced_help-617c1|advanced_help]], [[screen_agenda-a82fc|agenda]], [[screen_alert_settings-a6f83|alert_settings]], [[screen_alerts-313c9|alerts]], [[screen_analytics-4bd00|analytics]], [[screen_assistant-c05b6|assistant]], [[screen_attention-ebc03|attention]], [[screen_balance-64c54|balance]], [[screen_balance_account-fac81|balance_account]], [[screen_balance_details-02072|balance_details]], [[screen_budgets-b41b9|budgets]], [[screen_can_buy-e0e39|can_buy]], [[screen_cash_account_detail-b41d6|cash_account_detail]], [[screen_cash_accounts-cc984|cash_accounts]], [[screen_categories-bcdb1|categories]], [[screen_category_rules-91f55|category_rules]], [[screen_closing-a1da9|closing]], [[screen_closing_details-60038|closing_details]], [[screen_command_help-4b0d8|command_help]], [[screen_dashboard-6ba51|dashboard]], [[screen_data_tools-d1767|data_tools]], [[screen_edit_menu-328c2|edit_menu]], [[screen_feature_guide-3fc8e|feature_guide]], [[screen_fixos-1e200|fixos]], [[screen_help-8e6e8|help]], [[screen_help_topic-07999|help_topic]], [[screen_history-d40e7|history]], [[screen_history_tools-cc0f8|history_tools]] …
- **Ações (164):** [[act_account_choice_page-f85b1|account_choice_page]], [[act_account_filter-0f866|account_filter]], [[act_account_page-23d57|account_page]], [[act_account_search-82984|account_search]], [[act_accounts_for-fd5a1|accounts_for]], [[act_acct_off-1b680|acct_off]], [[act_acct_off_ok-f0e88|acct_off_ok]], [[act_acct_on-baf20|acct_on]], [[act_ai_route-0c6a9|ai_route]], [[act_ai_status-127b5|ai_status]], [[act_alert_hours-a41d6|alert_hours]], [[act_alert_preview-31dab|alert_preview]], [[act_answer-596e5|answer]], [[act_ask-dbbdf|ask]], [[act_back-bca78|back]], [[act_back_step-afc43|back_step]], [[act_balance_account-4ec4f|balance_account]], [[act_balance_initial-82e49|balance_initial]], [[act_balance_start-167b7|balance_start]], [[act_budget_cat-77d03|budget_cat]], [[act_budget_start-ded37|budget_start]], [[act_busca-82b5b|busca]], [[act_busca_cat-d2a2f|busca_cat]], [[act_busca_cat_ok-7f8e8|busca_cat_ok]], [[act_busca_cat_ver-2ee97|busca_cat_ver]], [[act_busca_regra-c2b09|busca_regra]], [[act_buscar_texto-3e167|buscar_texto]], [[act_buy_fatura-a5396|buy_fatura]], [[act_buy_sim-7508a|buy_sim]], [[act_cancel-c6497|cancel]] …
- **Estado da sessão (47):** [[bug_menu_mes_novembro-e8fd4|BUG mês vaza para o Menu]], [[state_Experience._retrato-dbb0d|Experience._retrato]], [[state_Experience.sessions-934fe|Experience.sessions]], [[state_Session.account_choice_page-45779|Session.account_choice_page]], [[state_Session.account_filter-56b02|Session.account_filter]], [[state_Session.ai_question-7def3|Session.ai_question]], [[state_Session.cash_page-7ddbf|Session.cash_page]], [[state_Session.compra-c6ee7|Session.compra]], [[state_Session.draft-81d88|Session.draft]], [[state_Session.filter_view-6b228|Session.filter_view]], [[state_Session.fixed_edit-92b26|Session.fixed_edit]], [[state_Session.help_page-c97c0|Session.help_page]], [[state_Session.help_pages-88e29|Session.help_pages]], [[state_Session.help_title-3db7d|Session.help_title]], [[state_Session.history_account_filter-0cdca|Session.history_account_filter]], [[state_Session.history_basis-93b47|Session.history_basis]], [[state_Session.history_category_filter-6f763|Session.history_category_filter]], [[state_Session.history_filter-db2cb|Session.history_filter]], [[state_Session.last_event-a12b9|Session.last_event]], [[state_Session.learning_stage-1e8f0|Session.learning_stage]], [[state_Session.lesson-d22b3|Session.lesson]], [[state_Session.lesson_page-2a0cb|Session.lesson_page]], [[state_Session.month-7f614|Session.month]], [[state_Session.new_fixed-b5c04|Session.new_fixed]], [[state_Session.owner-41459|Session.owner]], [[state_Session.page-3e7eb|Session.page]], [[state_Session.pay_account_filter-280ee|Session.pay_account_filter]], [[state_Session.pay_filter-c235f|Session.pay_filter]], [[state_Session.pay_month_page-6ad4e|Session.pay_month_page]], [[state_Session.persist-7ac83|Session.persist]] …
- **Funções no mapa (23):** [[fn_telegram_experiencia._advance_registration-7c204|telegram_experiencia._advance_registration]], [[fn_telegram_experiencia._ai_query_result-e568b|telegram_experiencia._ai_query_result]], [[fn_telegram_experiencia._month_from_text-076be|telegram_experiencia._month_from_text]], [[fn_telegram_experiencia._pay_month_screen-4681f|telegram_experiencia._pay_month_screen]], [[fn_telegram_experiencia.act-0d59a|telegram_experiencia.act]], [[fn_telegram_experiencia.dispatch_text-ef266|telegram_experiencia.dispatch_text]], [[fn_telegram_experiencia.fast_deterministic_query-635f0|telegram_experiencia.fast_deterministic_query]], [[fn_telegram_experiencia.handle_text-7faea|telegram_experiencia.handle_text]], [[fn_telegram_experiencia.parse_draft-28bf2|telegram_experiencia.parse_draft]], [[fn_telegram_experiencia.render-aa635|telegram_experiencia.render]], [[fn_telegram_experiencia.screen_agenda-da330|telegram_experiencia.screen_agenda]], [[fn_telegram_experiencia.screen_alerts-edeeb|telegram_experiencia.screen_alerts]], [[fn_telegram_experiencia.screen_analytics-3aa02|telegram_experiencia.screen_analytics]], [[fn_telegram_experiencia.screen_attention-cfc78|telegram_experiencia.screen_attention]], [[fn_telegram_experiencia.screen_balance-df783|telegram_experiencia.screen_balance]], [[fn_telegram_experiencia.screen_budgets-740e9|telegram_experiencia.screen_budgets]], [[fn_telegram_experiencia.screen_closing-785b7|telegram_experiencia.screen_closing]], [[fn_telegram_experiencia.screen_help-94df3|telegram_experiencia.screen_help]], [[fn_telegram_experiencia.screen_home-2d196|telegram_experiencia.screen_home]], [[fn_telegram_experiencia.screen_pay-c88c4|telegram_experiencia.screen_pay]], [[fn_telegram_experiencia.screen_receivables-7fe08|telegram_experiencia.screen_receivables]], [[fn_telegram_experiencia.screen_recurring-4c0ce|telegram_experiencia.screen_recurring]], [[fn_telegram_experiencia.screen_review-6556a|telegram_experiencia.screen_review]]
- **Tratadores (113):** [[fn_ux._accounts_manage_notice-4b796|ux._accounts_manage_notice]], [[fn_ux._acct_off_apply-c3b72|ux._acct_off_apply]], [[fn_ux._acct_off_confirm-18a50|ux._acct_off_confirm]], [[fn_ux._acct_on-a9298|ux._acct_on]], [[fn_ux._advance_registration-9403a|ux._advance_registration]], [[fn_ux._ai_months-95d1a|_ai_months]], [[fn_ux._ai_query_result-20fe1|_ai_query_result]], [[fn_ux._ai_registration_preview-cdfb6|_ai_registration_preview]], [[fn_ux._apply_privacy-1d25f|ux._apply_privacy]], [[fn_ux._attention_signals-e5362|_attention_signals]], [[fn_ux._aviso_limite-3eb5c|ux._aviso_limite]], [[fn_ux._aviso_saldo_negativo-0fdcc|ux._aviso_saldo_negativo]], [[fn_ux._balance_account_screen-85ed8|_balance_account_screen]], [[fn_ux._cash_account_detail_screen-2f392|_cash_account_detail_screen]], [[fn_ux._cash_accounts_screen-0bdea|_cash_accounts_screen]], [[fn_ux._cash_setup_account-e2e3c|_cash_setup_account]], [[fn_ux._cash_setup_accounts-636f3|ux._cash_setup_accounts]], [[fn_ux._cash_setup_advance-a7700|ux._cash_setup_advance]], [[fn_ux._cash_setup_all-403de|ux._cash_setup_all]], [[fn_ux._cash_setup_commit-e0b60|_cash_setup_commit]], [[fn_ux._cash_setup_prompt-fbe95|_cash_setup_prompt]], [[fn_ux._cash_setup_start-b8255|_cash_setup_start]], [[fn_ux._categoria_menu-09adc|ux._categoria_menu]], [[fn_ux._categorias_limite-7ed40|ux._categorias_limite]], [[fn_ux._categorias_provaveis-37ee3|ux._categorias_provaveis]], [[fn_ux._compra_primeiro_mes-b32d0|ux._compra_primeiro_mes]], [[fn_ux._compra_resultado_linhas-ee753|ux._compra_resultado_linhas]], [[fn_ux._cresceu_linhas-16d90|ux._cresceu_linhas]], [[fn_ux._data_bloqueio-db47b|ux._data_bloqueio]], [[fn_ux._data_menu-cf2f5|ux._data_menu]] …
- **Gatilhos de texto (23):** [[text_ajuda_em_fluxo-39618|ajuda durante registro]], [[text_atalhos_tela-c62ab|registrar/a pagar/historico/analises/mais/ajuda]], [[text_aula-951df|aprender / aula <tema>]], [[text_baixa_checklist-e8d4f|marcar <item> pago]], [[text_botões_view_X_Início-cb16d|botões ('view', X)]], [[text_comando_operacional-ca373|comando_operacional]], [[text_conflito_lancamento-7d630|conflito_lancamento]], [[text_consulta_fixa-855da|meu mes|fechamento|atencao|resumo|quanto vou pagar|saldo geral|agenda|alertas|a receber|conciliacoes|assinaturas|meu plano|assessor [AAAA-MM]]], [[text_entrada_prevista_sem_data-8770a|entrada_prevista_sem_data]], [[text_fatura_pagamento-24641|pagamento/reembolso de fatura]], [[text_fixos_edicao-7f755|fixos_edicao]], [[text_fluxo_expirado-6dadf|fluxo_expirado]], [[text_gastei-ed06b|gastei/recebi/comprei/paguei/entrada <frase>]], [[text_help_tema-5c74b|/help <tema>]], [[text_menu_início_a_pagar_atalhos_UX2-88d1a|menu|inicio|central|a pagar|histórico|análises (texto)]], [[text_pagamento_fatura_pausa-fdd8c|pagamento_fatura_pausa]], [[text_pergunta_compra-86d79|pergunta_compra]], [[text_pergunta_natural-eb99e|pergunta em linguagem natural]], [[text_quanto_vou_pagar_mes-cf5ca|quanto vou pagar em novembro]], [[text_quanto_vou_pagar_ux2_aaaa-mm-714dc|quanto vou pagar [aaaa-mm] (UX2)]], [[text_resposta_etapa-954bb|texto durante um fluxo (stage ativo)]], [[text_simular-39cec|simular <frase>]], [[text_valor_solto-d6872|número sem contexto]]
- **Botões (8):** [[btn_Histórico_teclado-15934|Teclado fixo: 🏠 Início ➕ Registrar 🧾 A pagar 🔎 Histórico 📊 Análises ⚙️ Mais]], [[btn_Início-1bd0b|🏠 Início]], [[btn_Menu-04e55|☰ Menu]], [[btn_Mês_anterior-c7670|‹ Mês anterior]], [[btn_Mês_atual-9f60a|Mês atual / ↩ Mês atual]], [[btn_Período-15d50|📅 Período]], [[btn_Próximo_mês-62aa3|Próximo mês ›]], [[btn_Voltar-c2fc6|↩ Voltar]]

## Documentos que citam

- [[mapa/LEIA-ME]]
- [[reavaliacao/01_arquitetura]]
- [[reavaliacao/03_seguranca_privacidade]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
