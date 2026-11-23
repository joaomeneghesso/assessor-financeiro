---
tipo: text_trigger
arquivo: app.py
linha: 8602
---
# hoje

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:hoje`

## Vai para
- (navega) [[btn_Gastos_de_hoje-8d66c|📌 Gastos de hoje]] teclado inline
- (navega) [[btn_Registrar-19bf7|➕ Registrar]] teclado inline
- (navega) [[btn_Meu_mês_meu_mês-d5345|📊 Meu mês]] teclado inline
- (navega) [[btn_Revisar-ffeba|🔎 Revisar]] teclado inline
- (chama) [[fn_services.gerar_painel_hoje_ux-d5e23|services.gerar_painel_hoje_ux]] 

## Vem de
- (navega) [[text___atalho_menu-5b206|ATALHOS_MENU]] 
- (navega) [[btn_Hoje-ab454|📆 Hoje]] envia 'hoje'
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8602
