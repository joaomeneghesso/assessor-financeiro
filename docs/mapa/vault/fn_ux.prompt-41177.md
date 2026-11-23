---
tipo: handler
arquivo: telegram_experiencia.py
linha: 2011
---
# prompt

Tela da etapa de registro (valor, descrição, forma, conta, data, parcelas, fatura, categoria).

`fn:ux.prompt`

## Vai para
- (le_estado) [[state_Session.draft-81d88|Session.draft]] 
- (le_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (navega) [[act_answer-596e5|answer]] Sim/Não, formas, contas, Hoje/Ontem, meses de fatura
- (navega) [[act_back_step-afc43|back_step]] ‹ Etapa anterior
- (navega) [[act_cancel-c6497|cancel]] Cancelar
- (navega) [[act_account_choice_page-f85b1|account_choice_page]] Página de contas
- (chama) [[fn_sugestoes_lancamento.ordenar_contas-5c6a8|sugestoes_lancamento.ordenar_contas]] 
- (grava_estado) [[state_Session.account_choice_page-45779|Session.account_choice_page]] 
- (chama) [[fn_ux.accounts-08856|accounts]] 

## Vem de
- (chama) [[act_search-165fd|search]] 
- (chama) [[act_edit-7bceb|edit]] 
- (chama) [[act_back_step-afc43|back_step]] 
- (chama) [[act_account_choice_page-f85b1|account_choice_page]] 
- (chama) [[act_flow_resume-b920b|flow_resume]] 
- (navega) [[fn_ux.begin-7f489|begin]] 
- (navega) [[fn_ux.answer-a52eb|answer]] 
- (navega) [[fn_ux.parse_draft-0ebfb|parse_draft]] 
- (chama) [[act_conflict_keep-95a36|conflict_keep]] 
- (chama) [[fn_ux.preview-35809|preview]] 
