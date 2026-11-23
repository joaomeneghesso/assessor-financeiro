---
tipo: service
arquivo: telegram_alertas.py
linha: 87
---
# telegram_alertas.reservar

Reserva (idempotência) o envio gravando experiencia_alerta/reservado.

`fn:telegram_alertas.reservar`

## Vai para
- (grava_estado) [[state_db_auditoria_eventos-e3dd2|db:auditoria_eventos]] experiencia_alerta/reservado

## Vem de
- (chama) [[fn_telegram_alertas.executar_janela-a11fc|telegram_alertas.executar_janela]] 
