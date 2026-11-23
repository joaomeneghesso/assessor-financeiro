---
tipo: service
arquivo: telegram_registros.py
linha: 184
---
# telegram_registros.desfazer_registro

Remove só as linhas inalteradas do evento; recusa se há dependência posterior (fatura/saldo ajustado).

`fn:telegram_registros.desfazer_registro`

## Vai para
- (chama) [[fn_telegram_registros._dependencia_posterior-d179c|telegram_registros._dependencia_posterior]] 
- (chama) [[fn_conciliacao.desvincular_conn-5bd4b|conciliacao.desvincular_conn]] 
- (grava_estado) [[state_db_transacoes-fbd85|db:transacoes]] DELETE das linhas
- (grava_estado) [[state_db_auditoria_eventos-e3dd2|db:auditoria_eventos]] telegram_registro/desfeito

## Vem de
- (chama) [[mod_telegram_registros.py-6b0ea|telegram_registros.py]] 
- (chama) [[act_undo-07bdc|undo]] 
