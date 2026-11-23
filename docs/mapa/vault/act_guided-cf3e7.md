---
tipo: action
arquivo: telegram_experiencia.py
linha: 4318
---
# guided

dispatch_callback: zera stage/draft e inicia fluxo guiado do app (registrar_fixo ou host.iniciar_fluxo_guiado).

`act:guided`

## Vai para
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] zera
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] zera
- (chama) [[fn_ux.clear_service_pending-6ba11|clear_service_pending]] 
- (chama) [[act_new_fixed_start-3bf76|new_fixed_start]] registrar_fixo

## Vem de
- (chama) [[fn_ux.dispatch_callback-a9f29|ux.dispatch_callback]] 
- (navega) [[screen_setup-2cfa0|setup]] Novo compromisso
- (navega) [[screen_transaction-cd364|transaction]] Corrigir categoria/valor
- (navega) [[screen_advanced_help-617c1|advanced_help]] 
