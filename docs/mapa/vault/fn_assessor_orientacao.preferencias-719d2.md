---
tipo: service
arquivo: assessor_orientacao.py
linha: 20
---
# assessor_orientacao.preferencias

Lê preferências do último evento 'experiencia_preferencia' em auditoria_eventos.

`fn:assessor_orientacao.preferencias`

## Vai para
- (le_estado) [[state_db_auditoria_eventos-e3dd2|db:auditoria_eventos]] 

## Vem de
- (chama) [[mod_assessor_orientacao.py-e9925|assessor_orientacao.py]] 
- (chama) [[fn_telegram_alertas.executar_janela-a11fc|telegram_alertas.executar_janela]] 
