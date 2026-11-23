---
tipo: action
arquivo: telegram_experiencia.py
linha: 3350
---
# privacy

Alterna ocultar valores e vai para Início.

`act:privacy`

## Vai para
- (grava_estado) [[state_Session.privacy-8341f|Session.privacy]] alterna
- (navega) [[screen_home-111fe|home]] 
- (chama) [[fn_ux._save_privacy_preference-c9a2f|ux._save_privacy_preference]] 
- (chama) [[fn_ux.render-b3471|Experience.render]] 
- (le_estado) [[state_Session.owner-41459|Session.owner]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_home-111fe|home]] 👁 Mostrar/◉ Ocultar
- (navega) [[screen_month_actions-bedf6|month_actions]] Mostrar/Ocultar
- (navega) [[screen_balance_details-02072|balance_details]] Mostrar valores
