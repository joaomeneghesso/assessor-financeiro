---
tipo: service
arquivo: telegram_registros.py
linha: 89
---
# telegram_registros.confirmar_registro

Grava a(s) linha(s) em transacoes (parcelas) numa fatura_write_transaction; idempotente pela chave em auditoria_eventos; vincula/separa conciliação.

`fn:telegram_registros.confirmar_registro`

## Vai para
- (chama) [[fn_telegram_registros.validar_transacao-8ba78|telegram_registros.validar_transacao]] 
- (chama) [[fn_database.fatura_write_transaction-95ff7|database.fatura_write_transaction]] 
- (grava_estado) [[state_db_transacoes-fbd85|db:transacoes]] 
- (grava_estado) [[state_db_auditoria_eventos-e3dd2|db:auditoria_eventos]] telegram_registro/confirmado
- (chama) [[fn_conciliacao.vincular_conn-a192f|conciliacao.vincular_conn]] 
- (chama) [[fn_conciliacao.marcar_separado_conn-53f32|conciliacao.marcar_separado_conn]] 

## Vem de
- (chama) [[mod_telegram_registros.py-6b0ea|telegram_registros.py]] 
- (navega) [[fn_telegram_experiencia._advance_registration-7c204|telegram_experiencia._advance_registration]] confirmação final -> telegram_registros.confirmar_registro
- (chama) [[act_commit-ada76|commit]] 
