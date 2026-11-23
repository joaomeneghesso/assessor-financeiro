---
tipo: handler
arquivo: telegram_alertas.py
linha: 196
---
# telegram_alertas.rotina

telegram_alertas: rotina de alertas RC3 (horarios/pausa)

`fn:telegram_alertas.rotina`

## Vai para
- (chama) [[fn_telegram_alertas.executar_janela-a11fc|telegram_alertas.executar_janela]] 

## Vem de
- (chama) [[job_telegram_alertas.rotina-da520|telegram_alertas.rotina]] 
- (chama) [[mod_telegram_alertas.py-deb44|telegram_alertas.py]] 
- (chama) [[mod_app.py-57fef|app.py]] app.py:4806 / 5243 (job de alertas)
