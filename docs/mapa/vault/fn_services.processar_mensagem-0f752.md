---
tipo: handler
arquivo: services.py
linha: 11448
---
# services.processar_mensagem

services: roteador de comandos por regex (executar_core)

`fn:services.processar_mensagem`

## Vai para
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] 

## Vem de
- (chama) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] ordem 15: fallback services (executar_core)
- (chama) [[cb___legado-f60eb|__legado__[tipo:assinatura]:<cmd>]] pula_nativo=True
- (chama) [[cb_cmd-8bcfe|cmd:]] fallback
- (chama) [[text_confirmar_alteracao_cancelar_alteracao-39f74|confirmar alteracao | cancelar alteracao]] executar_core com sessao; o nucleo confere a pendencia e recalcula a previa
- (chama) [[mod_app.py-57fef|app.py]] executar_core(processar_mensagem) app.py:4969, só se UX2 não devolver tela
- (chama) [[fn_services.executar_exclusao_confirmada-c9366|services.executar_exclusao_confirmada]] reentra no roteador com flag
- (chama) [[fn_services.executar_alteracao_confirmada-b88d8|services.executar_alteracao_confirmada]] reentra no roteador com flag
- (chama) [[mod_app.py-57fef|app.py]] executar_core(processar_mensagem) app.py:4930 texto livre; 5002/5031/5249 comandos guiados e confirmados
- (chama) [[mod_telegram_experiencia.py-c6fa1|telegram_experiencia.py]] dispatch_callback (legacy/legacy_raw) telegram_experiencia.py:5315
- (chama) [[act_legacy-00431|legacy]] fallback sem tela nativa
- (chama) [[act_legacy_raw-2e265|legacy_raw]] 
