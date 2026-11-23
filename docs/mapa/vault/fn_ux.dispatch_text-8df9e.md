---
tipo: handler
arquivo: telegram_experiencia.py
linha: 5002
---
# ux.dispatch_text

telegram_experiencia: roteia texto para UX 2.0 (chamado em receber_mensagem, depois da confirmacao de alteracao e antes das pendencias legadas)

`fn:ux.dispatch_text`

## Vai para
- (chama) [[fn_ux.fast_deterministic_query-fb2df|fast_deterministic_query]] global_candidate (pergunta/consulta)
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] demais textos (via run_experience)
- (chama) [[fn_ux.send_screen-6d6ac|send_screen]] 
- (chama) [[fn_ux.run_experience-c1322|ux.run_experience]] 
- (chama) [[fn_ux.session_key-714ba|session_key]] 
- (chama) [[fn_assessor_ia_local.interpretar_contexto-e0413|interpretar_contexto]] 2ª camada Ollama (só roteia)
- (chama) [[fn_ux.question_result-77118|question_result]] LocalUnavailable + "?"
- (chama) [[act_view-1d8b8|view]] deterministic_view sem enrich (act view) - NÃO toca no mês
- (chama) [[fn_ux._invalidar_preservando_pausa-1a027|_invalidar_preservando_pausa]] comando operacional
- (le_estado) [[state_Session.stage-ad71b|Session.stage]] native_active
- (chama) [[fn_ux._ai_query_result-20fe1|_ai_query_result]] 
- (chama) [[fn_ux._suspend_flow-76c4a|_suspend_flow]] 
- (chama) [[fn_ux.clear_service_pending-6ba11|clear_service_pending]] 
- (chama) [[fn_ux._tela_fluxo_expirado-10505|ux._tela_fluxo_expirado]] 
- (chama) [[fn_ux.parece_outro_lancamento-da2d5|ux.parece_outro_lancamento]] 
- (chama) [[fn_ux._parece_resposta_de_etapa-afb2b|ux._parece_resposta_de_etapa]] 
- (chama) [[fn_ux._draft_summary-b5886|ux._draft_summary]] 

## Vem de
- (chama) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] ordem 10: UX 2.0 ANTES das pendencias legadas e sem gate de PIN de app.py
- (navega) [[state_menu_inferior_novo-5257a|montar_menu_principal (ReplyKeyboard)]] texto dos botoes
- (chama) [[text_quanto_vou_pagar_mes-cf5ca|quanto vou pagar em novembro]] 
- (chama) [[text_pergunta_compra-86d79|pergunta_compra]] 
- (chama) [[text_fluxo_expirado-6dadf|fluxo_expirado]] 
- (chama) [[text_conflito_lancamento-7d630|conflito_lancamento]] 
- (chama) [[text_pagamento_fatura_pausa-fdd8c|pagamento_fatura_pausa]] 
- (chama) [[text_fixos_edicao-7f755|fixos_edicao]] 
- (chama) [[text_entrada_prevista_sem_data-8770a|entrada_prevista_sem_data]] 
- (chama) [[text_comando_operacional-ca373|comando_operacional]] 
