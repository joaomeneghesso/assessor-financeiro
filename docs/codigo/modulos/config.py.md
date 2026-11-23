---
tipo: modulo
grupo: Entrada e operação
linhas: 137
tags: [modulo, entrada-e-operacao]
---
# config.py

> Configuração única do assessor: caminhos do projeto e leitura do ambiente.

**Grupo:** [[Entrada e operação]] · **Linhas:** 137 · **Funções:** 8 · **Classes:** 0

## Usa

- (nenhum módulo do projeto)

## Usado por

- [[app.py]] — `carregar_dotenv`, `definir`, `ler`, `ler_bool`, `ler_int`, `remover`
- [[assessor_ia_local.py]] — `ler`
- [[assessor_orientacao.py]] — `ler`
- [[backup_externo.py]] — `ler`
- [[backup_externo_cli.py]] — `carregar_dotenv`
- [[categorias_pessoais.py]] — `ler`
- [[compromissos.py]] — `ler`
- [[database.py]]
- [[faturas_competencia.py]] — `ler`
- [[services.py]] — `ler`
- [[telegram_experiencia.py]] — `carregar_dotenv`, `ler`
- [[telegram_midia.py]] — `ler`
- [[telegram_recursos.py]] — `ler`
- [[telegram_streaming.py]] — `ler`
- [[transcricao_audio.py]] — `ler`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `ler` | 108 | 13 | 1 | Mesmo que ``os.getenv(nome, padrao)``. |
| `carregar_dotenv` | 102 | 3 | 0 | Carrega ``<projeto>/.env`` no ambiente do processo (sem sobrescrever o que já existe). |
| `definir` | 131 | 1 | 1 | Atualiza o ambiente do processo (usado após gravar o ``.env``). |
| `ler_bool` | 113 | 1 | 1 | ``ler(nome, padrao).strip().lower() in verdadeiros`` (padrão em texto, como antes). |
| `ler_int` | 118 | 1 | 1 | ``int(ler(nome, padrao))`` (padrão em texto, como antes; valor inválido levanta). |
| `remover` | 136 | 1 | 1 |  |
| `existe` | 127 | 0 | 1 |  |

## Tudo que define

- `carregar_dotenv` (L102, 4 linhas) — Carrega ``<projeto>/.env`` no ambiente do processo (sem sobrescrever o que já existe).
- `ler` (L108, 3 linhas) — Mesmo que ``os.getenv(nome, padrao)``.
- `ler_bool` (L113, 3 linhas) — ``ler(nome, padrao).strip().lower() in verdadeiros`` (padrão em texto, como antes).
- `ler_int` (L118, 3 linhas) — ``int(ler(nome, padrao))`` (padrão em texto, como antes; valor inválido levanta).
- `ler_float` (L123, 2 linhas)
- `existe` (L127, 2 linhas)
- `definir` (L131, 3 linhas) — Atualiza o ambiente do processo (usado após gravar o ``.env``).
- `remover` (L136, 2 linhas)

## Testes que usam (1)

- `tests/test_config_unica.py`

## Documentos que citam

- [[reavaliacao/01_arquitetura]]
- [[reavaliacao/08_onda3_etapa1]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
