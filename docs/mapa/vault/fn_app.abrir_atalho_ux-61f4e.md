---
tipo: handler
arquivo: app.py
linha: 4669
---
# app.abrir_atalho_ux

Atalhos /mes /registrar /pagar /historico /saldos /fechamento /atencao: abre a tela UX apos gate de PIN

`fn:app.abrir_atalho_ux`

## Vai para
- (grava_estado) [[state_session.month-91610|session.month]] month = hoje (reseta competencia escolhida)
- (le_estado) [[state_session.month-91610|session.month]] cash_accounts usa s.month
- (chama) [[fn_ux.run_experience-c1322|ux.run_experience]] act view/cash_accounts
- (exige_pin) [[gate_bloquear_se_assessor_travado-323dc|bloquear_se_assessor_travado]] 'saldo geral' (nao e acao sensivel)

## Vem de
- (chama) [[fn_app.mes_command-26e50|mes_command]] home
- (chama) [[fn_app.registrar_command-868b6|registrar_command]] register
- (chama) [[fn_app.pagar_command-dd25a|pagar_command]] pay
- (chama) [[fn_app.historico_command-1af15|historico_command]] history
- (chama) [[fn_app.saldos_command-20ef1|saldos_command]] cash_accounts
- (chama) [[fn_app.fechamento_command-07cdf|fechamento_command]] closing
- (chama) [[fn_app.atencao_command-b3322|atencao_command]] attention
