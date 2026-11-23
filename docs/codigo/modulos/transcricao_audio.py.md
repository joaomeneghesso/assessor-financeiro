---
tipo: modulo
grupo: Mídia e voz
linhas: 328
tags: [modulo, midia-e-voz]
---
# transcricao_audio.py

> Transcrição local de voz com worker Whisper isolado.

**Grupo:** [[Mídia e voz]] · **Linhas:** 328 · **Funções:** 16 · **Classes:** 2

## Usa

- [[config.py]]

## Usado por

- [[services.py]] — `diagnosticar_audio`
- [[telegram_midia.py]] — `AudioDependencyMissing`, `AudioTranscriptionError`, `transcrever_audio`
- [[tools__medir_desempenho.py|tools/medir_desempenho.py]] — `_kill_worker`, `transcrever_audio`

## Funções mais usadas por fora

| Função | Linha | Módulos | Testes | O que faz |
|---|---|---|---|---|
| `transcrever_audio` | 289 | 2 | 1 |  |
| `AudioDependencyMissing` | 29 | 1 | 1 | Dependência local de áudio ainda não instalada. |
| `diagnosticar_audio` | 274 | 1 | 1 | Diagnóstico sem carregar modelo, abrir rede ou revelar credenciais. |
| `AudioTranscriptionError` | 25 | 1 | 0 | Falha recuperável de transcrição. |
| `_kill_worker` | 91 | 1 | 0 |  |
| `audio_config` | 44 | 0 | 2 |  |
| `_read_transcript` | 215 | 0 | 1 |  |

## Tudo que define

- classe `AudioTranscriptionError` (L25, 2 linhas) — Falha recuperável de transcrição.
- classe `AudioDependencyMissing` (L29, 2 linhas) — Dependência local de áudio ainda não instalada.
- `_env` (L40, 2 linhas)
- `audio_config` (L44, 13 linhas)
- `_worker_script` (L59, 2 linhas)
- `_start_worker` (L63, 19 linhas)
- `_ensure_worker` (L84, 5 linhas)
- `_kill_worker` (L91, 14 linhas)
- `_readline_with_timeout` (L107, 18 linhas)
- `_request_worker` (L127, 35 linhas)
- `normalizar_transcricao` (L164, 5 linhas)
- `_creation_flags` (L171, 2 linhas)
- `_decode_to_wav` (L175, 20 linhas)
- `_wav_has_voice_level` (L197, 16 linhas) — Recusa silêncio/ruído ínfimo antes que o modelo possa alucinar texto.
- `_read_transcript` (L215, 8 linhas)
- `_transcribe_whisper_cpp` (L225, 47 linhas)
- `diagnosticar_audio` (L274, 13 linhas) — Diagnóstico sem carregar modelo, abrir rede ou revelar credenciais.
- `transcrever_audio` (L289, 39 linhas)

## Testes que usam (2)

- `tests/test_audio_whisper_cpp.py`
- `tests/test_portabilidade_linux.py`

## No mapa de rotas

- **Funções no mapa (1):** [[fn_transcricao_audio.transcrever_audio-a44a2|transcricao_audio.transcrever_audio]]

## Documentos que citam

- [[reavaliacao/03_seguranca_privacidade]]
- [[reavaliacao/07_inventario_gravacao_legado]]

---
*Gerado por `tools/gerar_vault_codigo.py`. Não edite à mão: rode o gerador de novo.*
