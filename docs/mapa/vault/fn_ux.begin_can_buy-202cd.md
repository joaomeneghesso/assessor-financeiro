---
tipo: handler
arquivo: telegram_experiencia.py
linha: 2575
---
# ux.begin_can_buy

Inicia a simulação Posso comprar? a partir do texto.

`fn:ux.begin_can_buy`

## Vai para
- (chama) [[fn_orientacao.extrair_pergunta_compra-851a2|orientacao.extrair_pergunta_compra]] 
- (grava_estado) [[state_Session.compra-c6ee7|Session.compra]] 
- (grava_estado) [[state_Session.month-7f614|Session.month]] 
- (grava_estado) [[state_Session.page-3e7eb|Session.page]] 
- (chama) [[act_view-1d8b8|view]] 
- (chama) [[act_start-ebd45|start]] 
- (navega) [[screen_can_buy-e0e39|can_buy]] 

## Vem de
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] 
- (chama) [[text_pergunta_compra-86d79|pergunta_compra]] 
