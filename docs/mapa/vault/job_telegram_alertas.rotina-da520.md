---
tipo: job
arquivo: app.py
linha: 5526
---
# telegram_alertas.rotina

Rotina de alertas RC3 (horarios/pausa em Mais > Alertas); unica rotina de alertas agendada, so se obter_chat_id_alertas()

`job:telegram_alertas.rotina`

## Vai para
- (chama) [[fn_telegram_alertas.rotina-a3d59|telegram_alertas.rotina]] 

## Vem de
- (agenda) [[fn_app.inicializar_alertas-42b78|app.inicializar_alertas]] se obter_chat_id_alertas()
