---
tipo: handler
arquivo: telegram_experiencia.py
linha: 3755
---
# Experience.handle_text

Roteador de texto livre: aulas, fixos, atalhos, cancelar, dashboard, resposta de etapa, comandos de fatura, consultas, ajuda, perguntas naturais, registro por frase.

`fn:ux.handle_text`

## Vai para
- (chama) [[fn_orientacao.reconhecer_pergunta-2077d|reconhecer_pergunta]] 
- (chama) [[act_view-1d8b8|view]] shortcuts/consulta fixa/pergunta natural
- (chama) [[act_cancel-c6497|cancel]] 
- (chama) [[act_chart-efa97|chart]] dashboard_route
- (chama) [[act_topic-518da|topic]] /help <tema>
- (chama) [[fn_ux.answer-a52eb|answer]] stage ativo
- (chama) [[fn_ux.parse_draft-0ebfb|parse_draft]] 
- (chama) [[fn_ux.begin_settlement-f6619|begin_settlement]] 
- (chama) [[fn_ux.begin_invoice_payment_from_command-5d84f|begin_invoice_payment_from_command]] 
- (chama) [[fn_ux.open_learning-405a2|open_learning]] 
- (chama) [[fn_ux._new_fixed_text-81b47|_new_fixed_text]] 
- (chama) [[fn_fixos_interface.texto-9739b|texto]] 
- (chama) [[fn_ux._flow_help_screen-a5285|_flow_help_screen]] 
- (chama) [[fn_services.parsear_comando_movimento_fatura-5c9cb|services.parsear_comando_movimento_fatura]] 
- (chama) [[fn_services.parsear_comando_marcar_checklist-260c9|services.parsear_comando_marcar_checklist]] 
- (chama) [[fn_services.normalizar_ano_mes_flexivel-68b03|services.normalizar_ano_mes_flexivel]] 
- (chama) [[fn_services.validar_ano_mes-a072d|services.validar_ano_mes]] 
- (chama) [[fn_services.resolver_item_checklist-a2267|services.resolver_item_checklist]] 
- (chama) [[fn_ux.session-8e514|Experience.session]] 
- (chama) [[fn_telegram_aprendizado.route-d257a|telegram_aprendizado.route]] 
- (chama) [[fn_ux._rota_frase_natural-c0a82|ux._rota_frase_natural]] 
- (chama) [[fn_orientacao.eh_pergunta_compra-461c2|orientacao.eh_pergunta_compra]] 
- (chama) [[fn_ux._fechar_caminho_legado-7ec16|ux._fechar_caminho_legado]] 
- (chama) [[fn_ux.begin_can_buy-202cd|ux.begin_can_buy]] 
- (chama) [[fn_ux.question_result-77118|question_result]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (chama) [[fn_services.parsear_comando_marcar_checklist_multiplo-7597a|services.parsear_comando_marcar_checklist_multiplo]] 
- (le_estado) [[state_Session.draft-81d88|Session.draft]] 
- (chama) [[fn_ux.act-20779|Experience.act]] 

## Vem de
- (chama) [[text_menu-03529|menu]] 
- (chama) [[text_atalhos_tela-c62ab|registrar/a pagar/historico/analises/mais/ajuda]] 
- (chama) [[text_cancelar-f5cad|cancelar]] 
- (chama) [[text_dashboard-5acd2|dashboard]] 
- (chama) [[text_consulta_fixa-855da|meu mes|fechamento|atencao|resumo|quanto vou pagar|saldo geral|agenda|alertas|a receber|conciliacoes|assinaturas|meu plano|assessor [AAAA-MM]]] 
- (chama) [[text_help_tema-5c74b|/help <tema>]] 
- (chama) [[text_pergunta_natural-eb99e|pergunta em linguagem natural]] 
- (chama) [[text_gastei-ed06b|gastei/recebi/comprei/paguei/entrada <frase>]] 
- (chama) [[text_simular-39cec|simular <frase>]] 
- (chama) [[text_fatura_pagamento-24641|pagamento/reembolso de fatura]] 
- (chama) [[text_baixa_checklist-e8d4f|marcar <item> pago]] 
- (chama) [[text_aula-951df|aprender / aula <tema>]] 
- (chama) [[text_resposta_etapa-954bb|texto durante um fluxo (stage ativo)]] 
- (chama) [[text_valor_solto-d6872|número sem contexto]] 
- (chama) [[text_ajuda_em_fluxo-39618|ajuda durante registro]] 
- (chama) [[fn_ux.dispatch_text-8df9e|ux.dispatch_text]] demais textos (via run_experience)
- (chama) [[fn_ux.run_experience-c1322|ux.run_experience]] 
- (chama) [[act_legacy-00431|legacy]] handle_text(cmd) primeiro
- (chama) [[act_conflict_start-3417b|conflict_start]] 
