---
tipo: text_trigger
arquivo: app.py
linha: 8786
---
# compromissos

Comando de texto enviado a processar_mensagem/ux (rota exata decidida fora de app.py)

`text:compromissos`

## Vai para
- (navega) [[btn_Checklist_checklist_mes-f7d68|✅ Checklist]] teclado inline
- (navega) [[btn_Fixos_fixos-5a228|🧾 Fixos]] teclado inline
- (navega) [[btn_Parcelas_parcelamentos-f1540|💳 Parcelas]] teclado inline
- (navega) [[btn_Entradas-52446|💰 Entradas]] teclado inline
- (navega) [[btn_Alterar_conta-9a995|🏦 Alterar conta]] teclado inline
- (navega) [[btn_Agenda_geral-7b611|📆 Agenda geral]] teclado inline
- (navega) [[btn_Meu_mês_meu_mês-d5345|📊 Meu mês]] teclado inline
- (chama) [[fn_services.gerar_compromissos_ux-ba5d7|services.gerar_compromissos_ux]] 

## Vem de
- (navega) [[text___atalho_menu-5b206|ATALHOS_MENU]] 
- (navega) [[btn_Compromissos_compromissos-aa678|💳 Compromissos]] envia 'compromissos'
- (alias_de) [[alias_ver_compromisso_s-6a78f|ver compromisso(s)/compromissos gerais -> compromissos]] 
- (chama) [[fn_services._processar_mensagem_core-9355a|_processar_mensagem_core]] services.py:8786
