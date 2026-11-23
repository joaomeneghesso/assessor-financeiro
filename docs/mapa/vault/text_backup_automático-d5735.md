---
tipo: text_trigger
arquivo: services.py
linha: 9244
---
# backup automático

Backup automático (também usado pelo job agendado).

`text:backup automático`

## Vai para
- (chama) [[fn_services.gerar_backup_automatico-a04f0|services.gerar_backup_automatico]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9244
- (chama) [[mod_app.py-57fef|app.py]] job de backup app.py:5368/5377
