---
tipo: service
arquivo: telegram_experiencia.py
linha: 684
---
# telegram_experiencia.render

Renderiza screen_<view>(s) dentro de db.read_only_mode() + contexto_consulta().

`fn:telegram_experiencia.render`

## Vai para
- (le_estado) [[state_Session.month-7f614|Session.month]] screen_<view>(s) usa s.month
- (grava_estado) [[state_CONTEXTO_CONSULTA-83d77|CONTEXTO_CONSULTA]] contexto_consulta(): cache efêmero só durante a renderização
- (chama) [[fn_consulta_cache.contexto_consulta-9f519|consulta_cache.contexto_consulta]] telegram_experiencia.py:601

## Vem de
- (chama) [[fn_telegram_experiencia.act-0d59a|telegram_experiencia.act]] kind=='view' 2814-2822: s.month intocado
