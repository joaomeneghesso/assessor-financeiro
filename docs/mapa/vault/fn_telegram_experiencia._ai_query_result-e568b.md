---
tipo: service
arquivo: telegram_experiencia.py
linha: 4628
---
# telegram_experiencia._ai_query_result

Executa consulta estruturada; 3737-3741 recalcula mês (explícito ou período) e GRAVA s.month; qtype payables -> _pay_month_screen.

`fn:telegram_experiencia._ai_query_result`

## Vai para
- (chama) [[fn_telegram_experiencia._month_from_text-076be|telegram_experiencia._month_from_text]] 3737
- (grava_estado) [[state_Session.month-7f614|Session.month]] 3741: s.month = months[-1]
- (chama) [[fn_telegram_experiencia._pay_month_screen-4681f|telegram_experiencia._pay_month_screen]] 3746 (qtype payables)

## Vem de
- (chama) [[fn_telegram_experiencia.fast_deterministic_query-635f0|telegram_experiencia.fast_deterministic_query]] 3722
- (navega) [[fn_consultas_rapidas.interpretar_consulta-9e67b|consultas_rapidas.interpretar_consulta]] dict estruturado vai a _ai_query_result (3701)
