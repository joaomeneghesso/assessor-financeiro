---
tipo: state
arquivo: telegram_experiencia.py
linha: 418
---
# Experience.sessions

Dict key->Session em memória (máx 100, TTL 600 s, expurgo em session()).

`state:Experience.sessions`

## Vem de
- (grava_estado) [[fn_ux._invalidar_preservando_pausa-1a027|_invalidar_preservando_pausa]] apaga Session (mês volta ao corrente)
- (grava_estado) [[act_lock-5ad19|lock]] invalidate
- (le_estado) [[fn_ux.session-8e514|Experience.session]] 
