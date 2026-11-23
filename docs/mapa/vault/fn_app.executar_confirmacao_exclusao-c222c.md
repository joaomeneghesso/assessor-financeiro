---
tipo: handler
arquivo: app.py
linha: 1570
---
# app.executar_confirmacao_exclusao

Revalida previa, backup pre-exclusao obrigatorio, executa services.executar_exclusao_confirmada

`fn:app.executar_confirmacao_exclusao`

## Vai para
- (le_estado) [[state_PENDENCIAS_EXCLUSAO-1f0a4|PENDENCIAS_EXCLUSAO]] 
- (grava_estado) [[state_PENDENCIAS_EXCLUSAO-1f0a4|PENDENCIAS_EXCLUSAO]] limpa
- (chama) [[fn_services.criar_backup_pre_exclusao-6cdc5|services.criar_backup_pre_exclusao]] falha fechada
- (chama) [[fn_services.executar_exclusao_confirmada-c9366|services.executar_exclusao_confirmada]] 

## Vem de
- (chama) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] texto 'confirmar'
- (chama) [[cb___confirmar_exclusao-3fc51|__confirmar_exclusao__]] 
