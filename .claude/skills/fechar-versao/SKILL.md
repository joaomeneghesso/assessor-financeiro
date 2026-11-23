---
name: fechar-versao
description: Fecha uma versão do assessor: atualiza version.py, CHANGELOG.md e docs, após gate aprovado. Use ao concluir um conjunto de correções.
disable-model-invocation: true
---
# Fechar versão

1. Confirme gate aprovado (`rodar-gate`) e anote o total de testes.
2. Atualize `version.py` (`VERSION = "x.y.z"`; patch para correções, minor para recursos).
3. Adicione no topo de `CHANGELOG.md`: `# x.y.z — Título (dd/mm/aaaa)` + bullets curtos + linha "Gate oficial: N/N testes." Mantenha a observação sobre o que ficou inalterado (banco, migrations, cálculos) quando for verdade.
4. Decisão arquitetural → `docs/` (padrão `IMPLEMENTACAO_*.md`).
5. Atualize `CLAUDE.md` só se mudou algo estrutural.
6. Commit só se o usuário pedir.
