---
tipo: handler
arquivo: telegram_experiencia.py
linha: 2660
---
# _new_fixed_prompt

Etapas 1-8 do novo fixo.

`fn:ux._new_fixed_prompt`

## Vai para
- (le_estado) [[state_Session.new_fixed-b5c04|Session.new_fixed]] 
- (navega) [[act_new_fixed_answer-6a6aa|new_fixed_answer]] sugestão/botões
- (navega) [[act_new_fixed_no_end-54ad7|new_fixed_no_end]] Sem término
- (navega) [[act_new_fixed_define_end-b9e31|new_fixed_define_end]] Definir término
- (navega) [[act_new_fixed_back-a5d76|new_fixed_back]] ‹ Etapa anterior
- (navega) [[act_new_fixed_cancel-e16bb|new_fixed_cancel]] Cancelar
- (chama) [[fn_ux._new_fixed_preview-90ab6|_new_fixed_preview]] 
- (chama) [[fn_ux._registration_category-c8854|ux._registration_category]] 
- (chama) [[fn_ux.accounts-08856|accounts]] 
- (le_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (le_estado) [[state_Session.owner-41459|Session.owner]] 

## Vem de
- (navega) [[act_learning_resume-96135|learning_resume]] 
- (chama) [[act_new_fixed_start-3bf76|new_fixed_start]] 
- (navega) [[act_new_fixed_define_end-b9e31|new_fixed_define_end]] 
- (navega) [[act_new_fixed_back-a5d76|new_fixed_back]] 
- (navega) [[act_new_fixed_edit-fc7ba|new_fixed_edit]] 
- (navega) [[fn_ux._new_fixed_text-81b47|_new_fixed_text]] 
- (chama) [[act_conflict_keep-95a36|conflict_keep]] 
- (chama) [[fn_ux._new_fixed_preview-90ab6|_new_fixed_preview]] 
