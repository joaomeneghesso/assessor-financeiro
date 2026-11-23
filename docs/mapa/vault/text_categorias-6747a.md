---
tipo: text_trigger
arquivo: app.py
linha: 9041
---
# categorias

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:categorias`

## Vai para
- (navega) [[btn_mês_anterior_categorias-4abb4|◀️ mês anterior (categorias)]] teclado inline
- (navega) [[btn_mês_seguinte_categorias-1b24f|mês seguinte ▶️ (categorias)]] teclado inline
- (navega) [[btn_categoria_ate_12-fc69f|<categoria> (ate 12)]] teclado inline
- (navega) [[btn_Detalhar_mês-7cb84|📋 Detalhar mês]] teclado inline
- (navega) [[btn_Agenda_geral-7b611|📆 Agenda geral]] teclado inline
- (navega) [[btn_Contas_contas_mes-7af3f|💰 Contas]] teclado inline
- (navega) [[btn_Parcelas_parcelas_mes-a4056|💳 Parcelas]] teclado inline
- (chama) [[fn_services.listar_categorias_mes-dcee4|services.listar_categorias_mes]] 

## Vem de
- (navega) [[text___atalho_menu-5b206|ATALHOS_MENU]] 
- (navega) [[btn_Categorias_categorias-7f8d8|🏷 Categorias]] envia 'categorias'
- (alias_de) [[alias_ver_categoria_s-9a983|ver categoria(s) -> categorias]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9041
