---
tipo: service
arquivo: telegram_experiencia.py
linha: 5002
---
# telegram_experiencia.dispatch_text

Primeiro filtro de texto do Telegram (app.py:4691): decide UX2 vs legado.

`fn:telegram_experiencia.dispatch_text`

## Vai para
- (chama) [[fn_telegram_experiencia.fast_deterministic_query-635f0|telegram_experiencia.fast_deterministic_query]] 4160 se global_candidate (reconhecer_pergunta -> 'pay')
- (chama) [[fn_telegram_experiencia.handle_text-7faea|telegram_experiencia.handle_text]] 4193 caso contrário
- (chama) [[fn_assessor_orientacao.reconhecer_pergunta-5191e|assessor_orientacao.reconhecer_pergunta]] 4144
- (chama) [[fn_consultas_rapidas.interpretar_consulta-9e67b|consultas_rapidas.interpretar_consulta]] 4151
- (chama) [[fn_telegram_aprendizado.route-d257a|telegram_aprendizado.route]] 4152

## Vem de
- (chama) [[mod_app.py-57fef|app.py]] app.py:4691
