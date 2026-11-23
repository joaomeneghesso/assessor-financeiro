---
tipo: callback
arquivo: app.py
linha: 5088
---
# __legado__[tipo:assinatura]:<cmd>

botao_texto: executa comando de texto direto no assessor, PULA ux.run_experience(handle_text); com vinculo, valida assinatura da previa (fatura/exclusao/importacao)

`cb:__legado__`

## Vai para
- (exige_pin) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] 
- (le_estado) [[state_CALLBACK_COMANDOS-49632|CALLBACK_COMANDOS]] assinatura via services.assinatura_pendencia
- (chama) [[fn_services.processar_mensagem-0f752|services.processar_mensagem]] pula_nativo=True

## Vem de
- (navega) [[cb_cmd-8bcfe|cmd:]] valor em CALLBACK_COMANDOS
- (navega) [[btn_Sim_voltar_a_herdar-cd495|↩️ Sim, voltar a herdar]] saldo inicial AAAA-MM <conta> herdado
- (navega) [[btn_Confirmar_pagamento_estorno_crédito-91173|✅ Confirmar pagamento|estorno|crédito]] prefixo __legado__
- (navega) [[btn_Cancelar_fatura-e1ef8|✖️ Cancelar fatura]] prefixo __legado__
- (navega) [[btn_Sim_apagar_legado-115d9|🗑 Sim, apagar (legado)]] prefixo __legado__
- (navega) [[btn_Não_apagar_legado-375a2|✖️ Não apagar (legado)]] prefixo __legado__
- (navega) [[btn_Importar-df0da|✅ Importar]] prefixo __legado__
- (navega) [[btn_Descartar-7bb90|✖️ Descartar]] prefixo __legado__
- (navega) [[btn_Tudo-b680e|📦 Tudo]] prefixo __legado__
- (navega) [[btn_Cancelar_exportação-70835|✖️ Cancelar exportação]] prefixo __legado__
- (navega) [[btn_Confirmar_alteração-b01aa|✅ Confirmar alteração]] prefixo __legado__ com vinculo alteracao
- (navega) [[btn_Não_alterar-31213|✖️ Não alterar]] prefixo __legado__ com vinculo alteracao
