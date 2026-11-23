---
tipo: action
arquivo: telegram_experiencia.py
linha: 3144
---
# pref

Salva preferência de alerta/visual/ia.

`act:pref`

## Vai para
- (chama) [[fn_orientacao.salvar_preferencia-50ee3|salvar_preferencia]] 
- (navega) [[screen_alerts-313c9|alerts]] 
- (navega) [[screen_local_ai-599c7|local_ai]] ia_local
- (navega) [[screen_more-4f9f6|more]] visual
- (chama) [[fn_ux.render-b3471|Experience.render]] 
- (chama) [[fn_orientacao.em_silencio-adc37|orientacao.em_silencio]] 
- (chama) [[fn_orientacao.preferencias-f52ab|preferencias]] 

## Vem de
- (chama) [[fn_ux.act-20779|Experience.act]] 
- (navega) [[screen_alerts-313c9|alerts]] Pausar/Retomar
- (navega) [[screen_alert_settings-a6f83|alert_settings]] Pausar/Retomar alertas
