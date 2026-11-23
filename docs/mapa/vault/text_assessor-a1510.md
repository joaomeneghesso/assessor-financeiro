---
tipo: text_trigger
arquivo: app.py
linha: 9172
---
# assessor

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:assessor`

## Vai para
- (navega) [[btn_Detalhar_mês_HOJE-98004|📋 Detalhar mês (HOJE)]] teclado inline
- (navega) [[btn_Categorias_HOJE-551c9|🏷 Categorias (HOJE)]] teclado inline
- (navega) [[btn_Agenda_geral-7b611|📆 Agenda geral]] teclado inline
- (navega) [[btn_Entradas-52446|💰 Entradas]] teclado inline
- (navega) [[btn_Fechamento-d1cce|📄 Fechamento]] teclado inline
- (navega) [[btn_hoje-1-23345|◀️ hoje-1]] teclado inline
- (navega) [[btn_hoje_1-08f6b|hoje+1 ▶️]] teclado inline
- (chama) [[fn_services.gerar_diagnostico_assessor-6a1f3|services.gerar_diagnostico_assessor]] 

## Vem de
- (navega) [[text___atalho_menu-5b206|ATALHOS_MENU]] 
- (navega) [[btn_Diagnóstico-8e4de|🧠 Diagnóstico]] envia 'assessor'
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9172
