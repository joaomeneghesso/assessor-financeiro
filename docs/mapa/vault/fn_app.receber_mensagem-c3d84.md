---
tipo: handler
arquivo: app.py
linha: 4811
---
# app.receber_mensagem

Roteador de texto livre (ordem documentada nas arestas 'ordem N')

`fn:app.receber_mensagem`

## Vai para
- (chama) [[gate_bloquear_se_nao_autorizado-e070d|bloquear_se_nao_autorizado]] ordem 1: allowlist
- (chama) [[fn_app.processar_reset_pin_guiado-9e198|app.processar_reset_pin_guiado]] ordem 2: se PENDENCIAS_RESET_PIN do user (antes de tudo)
- (chama) [[fn_app.obter_status_seguranca-2b716|app.obter_status_seguranca]] ordem 3: texto 'seguranca'
- (chama) [[text_esqueci_pin-c9d6c|esqueci pin]] ordem 4: 'esqueci pin|esqueci meu pin|/esqueci_pin'
- (chama) [[fn_app.processar_reset_pin-092e9|app.processar_reset_pin]] ordem 5: prefixos reset/resetar/redefinir pin/trocar pin (exceto resetar checklist)
- (chama) [[text_bloquear-31a41|bloquear]] ordem 6: bloqueia PIN (nao descarta registros)
- (chama) [[text_desbloquear_pin-3c305|desbloquear <pin>]] ordem 7: desbloqueio por PIN em texto (limiter+auditoria); apaga a mensagem com o PIN
- (chama) [[fn_ux.dispatch_text-8df9e|ux.dispatch_text]] ordem 10: UX 2.0 ANTES das pendencias legadas e sem gate de PIN de app.py
- (le_estado) [[state_PENDENCIAS_EXCLUSAO-1f0a4|PENDENCIAS_EXCLUSAO]] ordem 11: frase confirmar exclusao -> executar; cancelar/nao -> cancelar; outro texto -> aviso
- (chama) [[gate_comando_exige_confirmacao_exclusao-825e1|comando_exige_confirmacao_exclusao]] ordem 12: apagar/excluir... -> previa (antes, gate de PIN do comando)
- (le_estado) [[state_PENDENCIAS_GUIADAS-21a17|PENDENCIAS_GUIADAS]] ordem 13: fluxo guiado aguardando texto
- (chama) [[fn_app.montar_comando_de_pendencia-10c04|app.montar_comando_de_pendencia]] ordem 13: converte o texto no comando de servico
- (exige_pin) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] ordem 12 (exclusao), 13 (comando guiado montado) e 14 (apos normalizar atalho ATALHOS_MENU)
- (chama) [[fn_app.obter_resposta_comando_especial-bcaa6|app.obter_resposta_comando_especial]] ordem 14: menu/__help__//help/seguranca locais
- (chama) [[fn_services.processar_mensagem-0f752|services.processar_mensagem]] ordem 15: fallback services (executar_core)
- (le_estado) [[state_PENDENCIAS_RESET_PIN-f7ae3|PENDENCIAS_RESET_PIN]] ordem 2
- (chama) [[fn_app.executar_confirmacao_exclusao-c222c|app.executar_confirmacao_exclusao]] texto 'confirmar'
- (chama) [[fn_app.cancelar_confirmacao_exclusao-2489c|app.cancelar_confirmacao_exclusao]] texto 'cancelar'
- (chama) [[fn_app.solicitar_confirmacao_exclusao-1455f|app.solicitar_confirmacao_exclusao]] 
- (chama) [[fn_app.oferecer_aprendizado_categoria-9e4a6|app.oferecer_aprendizado_categoria]] apos corrigir categoria guiado
- (grava_estado) [[state_PENDENCIAS_GUIADAS-21a17|PENDENCIAS_GUIADAS]] limpa ao consumir
- (chama) [[fn_app.iniciar_feedback_visual-746ba|app.iniciar_feedback_visual]] 
- (chama) [[fn_app.enviar_resposta-bb2f6|app.enviar_resposta]] 
- (chama) [[text___atalho_menu-5b206|ATALHOS_MENU]] 
- (le_estado) [[state_ux.session_draft_stage_pending-60605|ux.session(draft/stage/pending)]] ux.dispatch_text
- (le_estado) [[state_RESET_PIN_EXPIRADOS-5c04b|RESET_PIN_EXPIRADOS]] ordem 2b: recuperacao expirada -> apaga a mensagem seguinte e avisa
- (chama) [[fn_app.reexecutar_acao_pendente_pin-28973|reexecutar_acao_pendente_pin]] ordem 7: apos desbloqueio correto refaz a acao bloqueada
- (le_estado) [[state_EXCLUSAO_EXPIRADAS-95cde|EXCLUSAO_EXPIRADAS]] ordem 8: exclusao pendente vencida -> aviso; um sim tardio nao confirma
- (chama) [[text_confirmar_alteracao_cancelar_alteracao-39f74|confirmar alteracao | cancelar alteracao]] ordem 9: TEXTOS_ALTERACAO_PENDENTE -> nucleo direto (sem UX, sem gate de PIN)
- (chama) [[fn_app.descartar_acao_pendente_pin-4ebf5|descartar_acao_pendente_pin]] limitador bloqueado

## Vem de
- (chama) [[handler_MessageHandler.text-d92c9|MessageHandler(TEXT & ~COMMAND)]] 
- (chama) [[fn_app.reexecutar_acao_pendente_pin-28973|reexecutar_acao_pendente_pin]] se a acao era texto
