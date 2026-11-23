---
tipo: text_trigger
arquivo: app.py
linha: 8599
---
# registrar

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:registrar`

## Vai para
- (navega) [[btn_Despesa-bd09d|💸 Despesa]] teclado inline
- (navega) [[btn_Entrada-e59ba|💰 Entrada]] teclado inline
- (navega) [[btn_Fixo_mensal-da0f8|🧾 Fixo mensal]] teclado inline
- (navega) [[btn_Compra_parcelada-960ec|💳 Compra parcelada]] teclado inline
- (navega) [[btn_Meu_mês_meu_mês-d5345|📊 Meu mês]] teclado inline
- (navega) [[btn_Revisar-ffeba|🔎 Revisar]] teclado inline
- (chama) [[fn_services.gerar_tela_registrar_ux-8214b|services.gerar_tela_registrar_ux]] 

## Vem de
- (navega) [[text___atalho_menu-5b206|ATALHOS_MENU]] 
- (navega) [[btn_Lançar-e6c87|➕ Lançar]] envia 'registrar'
- (navega) [[btn_Registrar-19bf7|➕ Registrar]] envia 'registrar'
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8599
