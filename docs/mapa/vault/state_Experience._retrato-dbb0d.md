---
tipo: state
arquivo: telegram_experiencia.py
linha: 689
---
# Experience._retrato

Cache do snapshot orient.coletar válido só durante um render() (limpo no finally l.611). Não vaza entre telas.

`state:Experience._retrato`

## Vem de
- (grava_estado) [[fn_ux.render-b3471|Experience.render]] limpa no finally
- (le_estado) [[fn_orientacao.coletar-ba856|coletar]] cache só dentro de um render
