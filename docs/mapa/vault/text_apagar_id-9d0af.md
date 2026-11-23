---
tipo: text_trigger
arquivo: app.py
linha: 1895
---
# apagar <id>

Comando de servico montado a partir da pendencia guiada

`text:apagar <id>`

## Vai para
- (grava_estado) [[state_PENDENCIAS_EXCLUSAO-1f0a4|PENDENCIAS_EXCLUSAO]] ATENCAO: via pendencia guiada vai direto a processar_mensagem (4751) sem solicitar_confirmacao_exclusao
- (chama) [[fn_services.apagar_por_id-de484|services.apagar_por_id]] 

## Vem de
- (navega) [[fn_app.montar_comando_de_pendencia-10c04|app.montar_comando_de_pendencia]] 
- (alias_de) [[alias_deletar_lançamento_transação_id_deletar_id-65ad1|deletar lançamento|transação|movimentação <id> ou <id> -> apagar <id>]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9310
