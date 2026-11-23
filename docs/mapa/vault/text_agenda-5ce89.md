---
tipo: text_trigger
arquivo: app.py
linha: 9175
---
# agenda

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:agenda`

## Vai para
- (navega) [[btn_meses_rapidos_4_mês_atual_3-29ff1|meses rapidos (4) mês atual+3]] teclado inline
- (navega) [[btn_Categorias_mês_atual-bbfa0|🏷 Categorias mês atual]] teclado inline
- (navega) [[btn_Contas_mês_atual-58e1b|💰 Contas mês atual]] teclado inline
- (navega) [[btn_Parcelas_mês_atual-a9ded|💳 Parcelas mês atual]] teclado inline
- (navega) [[btn_Entradas_mês_atual-698e9|💰 Entradas mês atual]] teclado inline
- (navega) [[btn_Diagnóstico-8e4de|🧠 Diagnóstico]] teclado inline
- (chama) [[fn_services.gerar_agenda_assessor-b5367|services.gerar_agenda_assessor]] 

## Vem de
- (navega) [[text___atalho_menu-5b206|ATALHOS_MENU]] 
- (navega) [[btn_Agenda_geral-7b611|📆 Agenda geral]] envia 'agenda'
- (alias_de) [[alias_ver_agenda-a1e70|ver agenda -> agenda]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:9175
