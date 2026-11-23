---
tipo: text_trigger
arquivo: app.py
linha: 2797
---
# detalhes meu mês

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:detalhes meu mês`

## Vai para
- (navega) [[btn_mês_anterior_detalhes-9b73e|◀️ mês anterior (detalhes)]] teclado inline
- (navega) [[btn_mês_seguinte_detalhes-e2f5b|mês seguinte ▶️ (detalhes)]] teclado inline
- (navega) [[btn_Resumo_curto-c62a8|📊 Resumo curto]] teclado inline
- (navega) [[btn_Categorias_categorias_mes-a79dd|🏷 Categorias]] teclado inline
- (navega) [[btn_Compromissos_compromissos-aa678|💳 Compromissos]] teclado inline
- (navega) [[btn_Diagnóstico-8e4de|🧠 Diagnóstico]] teclado inline
- (chama) [[fn_services.gerar_meu_mes_ux-f2a95|services.gerar_meu_mes_ux]] 

## Vem de
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8769
