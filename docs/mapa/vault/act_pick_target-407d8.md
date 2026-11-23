---
tipo: action
arquivo: telegram_experiencia.py
linha: 3303
---
# pick_target

Relacionar a previsão: grava Session.month=competência do rascunho.

`act:pick_target`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.2787 s.month=competência do rascunho
- (chama) [[fn_ux.target_picker-0a39c|target_picker]] 
- (grava_estado) [[state_Session.target_page-6e2a0|Session.target_page]] 
- (le_estado) [[state_Session.draft-81d88|Session.draft]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[fn_ux.preview-35809|preview]] 🔗 Relacionar a uma previsão
