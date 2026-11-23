---
tipo: state
arquivo: app.py
linha: 4669
---
# session.month

ux.EXPERIENCE.session(key).month: mes/competencia selecionado na UX 2.0 (string AAAA-MM), chave user:chat

`state:session.month`

## Vem de
- (grava_estado) [[fn_app.abrir_atalho_ux-61f4e|app.abrir_atalho_ux]] month = hoje (reseta competencia escolhida)
- (le_estado) [[fn_app.abrir_atalho_ux-61f4e|app.abrir_atalho_ux]] cash_accounts usa s.month
- (grava_estado) [[fn_app.dashboard_command-1e8d5|dashboard_command]] /dashboard AAAA-MM
- (le_estado) [[state_mes_base-b9f3b|mes_base]] NAO se comunicam: mes_base ignora session.month; session.month so e usado pelo UX 2.0
