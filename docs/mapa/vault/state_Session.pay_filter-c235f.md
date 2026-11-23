---
tipo: state
arquivo: telegram_experiencia.py
linha: 385
---
# Session.pay_filter

Filtro de A pagar (all/overdue/soon/review). NÃO é zerado ao reabrir A pagar via view/atalho de texto.

`state:Session.pay_filter`

## Vem de
- (le_estado) [[screen_pay-ee2a3|pay]] 
- (grava_estado) [[act_filter-91736|filter]] pay
- (grava_estado) [[act_clear_pay_filters-3757f|clear_pay_filters]] 
- (grava_estado) [[act_pay_account_filter-642f0|pay_account_filter]] 
- (le_estado) [[fn_ux._pay_tools_screen-7fc89|_pay_tools_screen]] 
