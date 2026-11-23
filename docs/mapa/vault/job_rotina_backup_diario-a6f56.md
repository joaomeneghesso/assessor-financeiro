---
tipo: job
arquivo: app.py
linha: 5355
---
# rotina_backup_diario

Backup automatico diario (ASSESSOR_BACKUP_HORA 03:00) + recuperacao no start se nao ha backup de hoje; chama processar_mensagem('backup automatico') sem PIN

`job:rotina_backup_diario`

## Vai para
- (chama) [[text_backup_automatico-24458|backup automatico]] 
- (exige_pin) [[gate_acao_exige_pin-e6d76|acao_exige_pin]] NAO passa por PIN (executa processar_mensagem direto)

## Vem de
- (agenda) [[fn_app.inicializar_alertas-42b78|app.inicializar_alertas]] criar_tarefa_monitorada (tarefa de fundo)
