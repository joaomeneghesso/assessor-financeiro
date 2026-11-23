---
tipo: action
arquivo: telegram_experiencia.py
linha: 3306
---
# target_month

Mês anterior/próximo do seletor de previsões: grava Session.month±1.

`act:target_month`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] l.2788 s.month±1
- (chama) [[fn_ux.target_picker-0a39c|target_picker]] 
- (grava_estado) [[state_Session.target_page-6e2a0|Session.target_page]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[fn_ux.target_picker-0a39c|target_picker]] ‹ Mês anterior / Próximo mês ›
