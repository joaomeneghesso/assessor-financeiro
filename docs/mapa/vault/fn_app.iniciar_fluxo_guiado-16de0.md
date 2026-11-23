---
tipo: handler
arquivo: app.py
linha: 1698
---
# app.iniciar_fluxo_guiado

Inicia fluxos guiados (guiado:<tipo>:<id>); define PENDENCIAS_GUIADAS

`fn:app.iniciar_fluxo_guiado`

## Vai para
- (grava_estado) [[state_PENDENCIAS_GUIADAS-21a17|PENDENCIAS_GUIADAS]] 
- (navega) [[btn_Cancelar___guiado_cancelar-3c583|✖️ Cancelar [__guiado_cancelar__]]] montar_teclado_cancelar_guiado

## Vem de
- (chama) [[cb_guiado-020e0|guiado:<tipo>[:<id>]]] 
- (chama) [[cb_guiado_registrar_despesa-9a43c|guiado:registrar_despesa]] 
- (chama) [[cb_guiado_registrar_entrada-a97f6|guiado:registrar_entrada]] 
- (chama) [[cb_guiado_registrar_fixo-9b449|guiado:registrar_fixo]] 
- (chama) [[cb_guiado_registrar_parcela-4d4fa|guiado:registrar_parcela]] 
- (chama) [[cb_guiado_corrigir_valor-9ce4e|guiado:corrigir_valor]] 
- (chama) [[cb_guiado_corrigir_categoria-8f04b|guiado:corrigir_categoria]] 
- (chama) [[cb_guiado_corrigir_conta-74439|guiado:corrigir_conta]] 
- (chama) [[cb_guiado_apagar_lancamento-0d61d|guiado:apagar_lancamento]] 
- (chama) [[cb_guiado_alterar_conta_fixo-0885d|guiado:alterar_conta_fixo]] 
- (chama) [[cb_guiado_apagar_fixo-6811a|guiado:apagar_fixo]] 
