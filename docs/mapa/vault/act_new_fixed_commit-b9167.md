---
tipo: action
arquivo: telegram_experiencia.py
linha: 2872
---
# new_fixed_commit

GRAVA fixo (svc.cadastrar_fixo_guiado).

`act:new_fixed_commit`

## Vai para
- (chama) [[fn_services.cadastrar_fixo_guiado-6e117|cadastrar_fixo_guiado]] 
- (grava_estado) [[state_Session.new_fixed-b5c04|Session.new_fixed]] 
- (navega) [[screen_pay-ee2a3|pay]] 
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (navega) [[act_view-1d8b8|view]] botão da resposta

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_new_fixed_preview-94294|new_fixed_preview]] ✅ Salvar fixo
- (chama) [[fn_ux._new_fixed_preview-90ab6|_new_fixed_preview]] 
