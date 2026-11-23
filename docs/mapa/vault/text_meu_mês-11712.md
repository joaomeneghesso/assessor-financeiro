---
tipo: text_trigger
arquivo: app.py
linha: 8766
---
# meu mês

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:meu mês`

## Vai para
- (navega) [[btn_mês_anterior-fe874|◀️ mês anterior]] teclado inline
- (navega) [[btn_mês_seguinte-1149f|mês seguinte ▶️]] teclado inline
- (navega) [[btn_Ver_detalhes-c2fc0|🔎 Ver detalhes]] teclado inline
- (navega) [[btn_Categorias_categorias_mes-a79dd|🏷 Categorias]] teclado inline
- (navega) [[btn_Compromissos_compromissos-aa678|💳 Compromissos]] teclado inline
- (navega) [[btn_Diagnóstico-8e4de|🧠 Diagnóstico]] teclado inline
- (chama) [[fn_services.gerar_meu_mes_curto_ux-1614a|services.gerar_meu_mes_curto_ux]] 

## Vem de
- (navega) [[text___atalho_menu-5b206|ATALHOS_MENU]] 
- (navega) [[btn_Meu_mês_meu_mês-d5345|📊 Meu mês]] envia 'meu mês'
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8766
