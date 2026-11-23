---
tipo: action
arquivo: telegram_experiencia.py
linha: 4325
---
# legacy

dispatch_callback: comando antigo -> handle_text(cmd) ou services.processar_mensagem.

`act:legacy`

## Vai para
- (chama) [[fn_ux.handle_text-89ee1|Experience.handle_text]] handle_text(cmd) primeiro
- (chama) [[fn_services.processar_mensagem-0f752|services.processar_mensagem]] fallback sem tela nativa

## Vem de
- (chama) [[fn_ux.dispatch_callback-a9f29|ux.dispatch_callback]] 
- (navega) [[screen_balance_details-02072|balance_details]] Memória completa
- (navega) [[screen_pay_tools-19539|pay_tools]] Checklist completo
- (navega) [[screen_budgets-b41b9|budgets]] Lista completa
- (navega) [[screen_data_tools-d1767|data_tools]] 💾 Criar backup
- (navega) [[screen_setup-2cfa0|setup]] Contas e saldos
- (navega) [[screen_command_help-4b0d8|command_help]] Fixos/Parcelamentos/Faturas/... (legacy /help)
- (navega) [[screen_transaction-cd364|transaction]] Outros ajustes
- (navega) [[screen_obligation-113ca|obligation]] Memória completa
- (chama) [[fn_ux._pay_tools_screen-7fc89|_pay_tools_screen]] 
