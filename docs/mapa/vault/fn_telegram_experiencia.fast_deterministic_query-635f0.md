---
tipo: service
arquivo: telegram_experiencia.py
linha: 4593
---
# telegram_experiencia.fast_deterministic_query

Resolve consultas inequívocas sem IA. Ramo 'pay' (3711-3722): mês = _month_from_text(text) ou mês atual; GRAVA s.month e s.pay_month_page=0 (3720-3721).

`fn:telegram_experiencia.fast_deterministic_query`

## Vai para
- (chama) [[fn_telegram_experiencia._month_from_text-076be|telegram_experiencia._month_from_text]] 3713
- (chama) [[fn_telegram_experiencia._pay_month_screen-4681f|telegram_experiencia._pay_month_screen]] indireto via _ai_query_result 3722
- (chama) [[fn_telegram_experiencia._ai_query_result-e568b|telegram_experiencia._ai_query_result]] 3722
- (grava_estado) [[state_Session.month-7f614|Session.month]] 3720: s.month = mês do texto ou mês atual
- (chama) [[fn_consultas_rapidas.interpretar_consulta-9e67b|consultas_rapidas.interpretar_consulta]] 3698

## Vem de
- (chama) [[fn_telegram_experiencia.dispatch_text-ef266|telegram_experiencia.dispatch_text]] 4160 se global_candidate (reconhecer_pergunta -> 'pay')
