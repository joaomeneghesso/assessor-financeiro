---
tipo: action
arquivo: telegram_experiencia.py
linha: 4325
---
# legacy_raw

dispatch_callback: comando bruto -> services.processar_mensagem (sem handle_text).

`act:legacy_raw`

## Vai para
- (chama) [[fn_services.processar_mensagem-0f752|services.processar_mensagem]] 

## Vem de
- (chama) [[fn_ux.dispatch_callback-a9f29|ux.dispatch_callback]] 
- (navega) [[screen_cash_account_detail-b41d6|cash_account_detail]] 📋 Ver movimentos
- (navega) [[screen_balance_account-fac81|balance_account]] Ver extrato
- (navega) [[screen_balance_details-02072|balance_details]] 
- (navega) [[screen_transaction-cd364|transaction]] 
- (chama) [[fn_ux._cash_account_detail_screen-2f392|_cash_account_detail_screen]] 
- (chama) [[fn_ux._balance_account_screen-85ed8|_balance_account_screen]] 
