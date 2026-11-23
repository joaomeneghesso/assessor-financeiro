---
tipo: text_trigger
arquivo: app.py
linha: 4929
---
# confirmar alteracao | cancelar alteracao

Confirmacao/cancelamento de alteracao legada (previa antes->depois); TEXTOS_ALTERACAO_PENDENTE; vai direto ao nucleo, antes do ux.dispatch_text

`text:confirmar alteracao|cancelar alteracao`

## Vai para
- (chama) [[fn_services.processar_mensagem-0f752|services.processar_mensagem]] executar_core com sessao; o nucleo confere a pendencia e recalcula a previa

## Vem de
- (chama) [[fn_app.receber_mensagem-c3d84|app.receber_mensagem]] ordem 9: TEXTOS_ALTERACAO_PENDENTE -> nucleo direto (sem UX, sem gate de PIN)
- (chama) [[btn_Confirmar_alteração-b01aa|✅ Confirmar alteração]] envia 'confirmar alteracao'
- (chama) [[btn_Não_alterar-31213|✖️ Não alterar]] envia 'cancelar alteracao'
