---
tipo: action
arquivo: telegram_experiencia.py
linha: 3359
---
# edit

Edita um campo da prévia.

`act:edit`

## Vai para
- (grava_estado) [[state_Session.stage-ad71b|Session.stage]] 
- (chama) [[fn_ux.prompt-41177|prompt]] 
- (grava_estado) [[state_Session.account_choice_page-45779|Session.account_choice_page]] 
- (grava_estado) [[state_Session.draft-81d88|Session.draft]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_edit_menu-328c2|edit_menu]] Valor/Descrição/Conta/Data/Categoria/Forma/Parcelamento/Fatura
- (chama) [[fn_ux.preview-35809|preview]] 
- (chama) [[fn_ux._edit_menu_screen-ff416|_edit_menu_screen]] 
