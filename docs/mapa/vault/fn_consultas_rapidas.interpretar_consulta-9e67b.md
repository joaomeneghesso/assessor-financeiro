---
tipo: service
arquivo: consultas_rapidas.py
linha: 6
---
# consultas_rapidas.interpretar_consulta

texto -> dict(intent=analytics, period, query_type: expense_total|income_total|category_expense|largest_expenses) ou None. Recusa texto com hoje/ontem/semana/cartão/pix/ano.

`fn:consultas_rapidas.interpretar_consulta`

## Vai para
- (navega) [[fn_telegram_experiencia._ai_query_result-e568b|telegram_experiencia._ai_query_result]] dict estruturado vai a _ai_query_result (3701)

## Vem de
- (chama) [[mod_consultas_rapidas.py-7e976|consultas_rapidas.py]] 
- (chama) [[fn_telegram_experiencia.fast_deterministic_query-635f0|telegram_experiencia.fast_deterministic_query]] 3698
- (chama) [[fn_telegram_experiencia.dispatch_text-ef266|telegram_experiencia.dispatch_text]] 4151
- (chama) [[fn_ux.fast_deterministic_query-fb2df|fast_deterministic_query]] 
