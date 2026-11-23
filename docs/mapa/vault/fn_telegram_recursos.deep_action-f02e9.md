---
tipo: service
arquivo: telegram_recursos.py
linha: 47
---
# telegram_recursos.deep_action

Mapeia payload de /start (inicio, ajuda, aprender, dashboard, pagar, historico, contas, aula_*, fatura_<x>_<aaaa-mm>) -> ação.

`fn:telegram_recursos.deep_action`

## Vai para
- (navega) [[fn_telegram_experiencia.act-0d59a|telegram_experiencia.act]] app.start: run_experience('render'|'act') (4365)

## Vem de
- (chama) [[mod_telegram_recursos.py-a9bf3|telegram_recursos.py]] 
- (chama) [[mod_app.py-57fef|app.py]] app.py:4357 /start <payload>
