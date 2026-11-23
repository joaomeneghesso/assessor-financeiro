---
tipo: inicio
tags: [inicio]
---
# Assessor financeiro — Início

Mapa do projeto para navegar no Obsidian. Só estrutura de código e documentos: **nenhum dado financeiro real entra neste vault** (banco, `.env`, backups e `.runtime` ficam fora da pasta `docs/`).

## Como navegar

1. Escolha uma área abaixo e clique no módulo.
2. Em cada módulo: **Usa** (o que ele chama), **Usado por** (quem depende dele), funções mais usadas, testes e as telas/ações do mapa de rotas.
3. Visão de grafo (Ctrl+G): cores por área. Para ver só o código, filtre por `path:codigo`.
4. Para ver as rotas (botões, telas, ações) abra [[mapa/LEIA-ME]] ou qualquer tela pelo módulo.

## Áreas do código (68 módulos, 39.178 linhas)

- [[Entrada e operação]] — 8 módulos · Onde o bot começa: inicialização, configuração única, relógio, trava de instância e logs.
- [[Telegram (telas e conversa)]] — 17 módulos · Tudo que o titular vê e toca: telas, botões, registros revisáveis, alertas, consultas e mídia.
- [[Camada de negócio e interpretação]] — 7 módulos · Roteador de comandos por texto, interpretação de registros e orientação local (sem gravar sozinho).
- [[Núcleo financeiro]] — 17 módulos · As regras que mexem em dinheiro: compromissos e fixos, conciliação, faturas e competência, saldos e categorias.
- [[Dados, backup e segurança]] — 9 módulos · Banco SQLite, migrations, backups (local e externo cifrado), PIN, estado protegido e limitador.
- [[Mídia e voz]] — 2 módulos · Transcrição local de áudio (Whisper) em processo isolado.
- [[Ferramentas e validação]] — 8 módulos · Scripts de apoio: gate oficial, mapa de rotas, medições, MCP somente leitura e este gerador.

## Documentos-chave

- [[reavaliacao/00_veredito|Veredito da reavaliação (comece por aqui)]]
- [[mapa/LEIA-ME|Mapa de rotas: como ler e manter]]
- [[DECISAO_ARQUITETURAL_MIGRATIONS|Decisão sobre migrations]]

## Manter atualizado

- Notas de código: `python tools/gerar_vault_codigo.py` (rode depois de mudar o código).
- Mapa de rotas: `python tools/gerar_mapa.py` e `tools/verificar_mapa.py` (ver [[mapa/LEIA-ME]]).
- Módulo novo sem área: entra em *Outros*; ajuste `GRUPOS` no gerador.

---
*Gerado por `tools/gerar_vault_codigo.py`.*
