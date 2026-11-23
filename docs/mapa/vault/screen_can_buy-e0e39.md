---
tipo: screen
arquivo: telegram_experiencia.py
linha: 2592
---
# can_buy

Simulação 'Posso comprar?': parcelas e fatura (só leitura).

`screen:can_buy`

## Vai para
- (chama) [[fn_ux._compra_primeiro_mes-b32d0|ux._compra_primeiro_mes]] 
- (chama) [[fn_orientacao.simular_compra-78064|orientacao.simular_compra]] 
- (chama) [[fn_ux._compra_resultado_linhas-ee753|ux._compra_resultado_linhas]] 
- (chama) [[fn_ux.nav-29bea|Experience.nav]] 
- (le_estado) [[state_Session.compra-c6ee7|Session.compra]] 
- (navega) [[act_buy_sim-7508a|buy_sim]] 
- (navega) [[act_start-ebd45|start]] 
- (navega) [[act_buy_fatura-a5396|buy_fatura]] 
- (navega) [[act_view-1d8b8|view]] 
- (navega) [[screen_home-111fe|home]] 

## Vem de
- (navega) [[act_buy_sim-7508a|buy_sim]] 
- (navega) [[act_buy_fatura-a5396|buy_fatura]] 
- (navega) [[fn_ux.begin_can_buy-202cd|ux.begin_can_buy]] 
