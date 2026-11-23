---
tipo: text_trigger
arquivo: app.py
linha: 9210
---
# parcelamentos

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:parcelamentos`

## Vai para
- (navega) [[btn_mês_anterior_parcelas-27bc7|◀️ mês anterior (parcelas)]] teclado inline
- (navega) [[btn_mês_seguinte_parcelas-26ca3|mês seguinte ▶️ (parcelas)]] teclado inline
- (navega) [[btn_Parcelas_do_mês-9f263|📆 Parcelas do mês]] teclado inline
- (navega) [[btn_Futuras-85bf0|🔮 Futuras]] teclado inline
- (navega) [[btn_Detalhar_mês-7cb84|📋 Detalhar mês]] teclado inline
- (navega) [[btn_Agenda_geral-7b611|📆 Agenda geral]] teclado inline
- (chama) [[fn_services.listar_parcelamentos_unificados_formatado-855dd|services.listar_parcelamentos_unificados_formatado]] 

## Vem de
- (navega) [[text___atalho_menu-5b206|ATALHOS_MENU]] 
- (navega) [[btn_Parcelas_parcelamentos-f1540|💳 Parcelas]] envia 'parcelamentos'
- (alias_de) [[alias_ver_parcela_s_parcelamento_s-534eb|ver parcela(s)/parcelamento(s) -> parcelamentos]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9210
