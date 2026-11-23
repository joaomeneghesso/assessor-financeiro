---
tipo: state
arquivo: telegram_experiencia.py
linha: 389
---
# Session.pay_account_filter

Filtro de conta de A pagar; persiste entre telas até clear_pay_filters.

`state:Session.pay_account_filter`

## Vem de
- (le_estado) [[screen_pay-ee2a3|pay]] 
- (grava_estado) [[act_clear_pay_filters-3757f|clear_pay_filters]] 
- (grava_estado) [[act_account_filter-0f866|account_filter]] filter_view=pay
- (grava_estado) [[act_pay_account_filter-642f0|pay_account_filter]] 
- (grava_estado) [[fn_ux.answer-a52eb|answer]] stage=account_search
- (le_estado) [[fn_ux._pay_tools_screen-7fc89|_pay_tools_screen]] 
