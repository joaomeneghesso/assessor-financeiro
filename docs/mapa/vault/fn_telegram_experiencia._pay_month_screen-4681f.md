---
tipo: service
arquivo: telegram_experiencia.py
linha: 4392
---
# telegram_experiencia._pay_month_screen

Tela 'A pagar' do mês: month = month or s.month; grava s.month (3497) e pay_month_page.

`fn:telegram_experiencia._pay_month_screen`

## Vai para
- (grava_estado) [[state_Session.month-7f614|Session.month]] 3497
- (le_estado) [[state_Session.month-7f614|Session.month]] 3494 month = month or s.month
- (chama) [[fn_compromissos.obter_itens_base_pagamentos_mes-4d0ba|compromissos.obter_itens_base_pagamentos_mes]] 3508

## Vem de
- (chama) [[fn_telegram_experiencia.fast_deterministic_query-635f0|telegram_experiencia.fast_deterministic_query]] indireto via _ai_query_result 3722
- (chama) [[fn_telegram_experiencia._ai_query_result-e568b|telegram_experiencia._ai_query_result]] 3746 (qtype payables)
