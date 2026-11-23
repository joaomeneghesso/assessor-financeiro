---
tipo: grupo
tags: [grupo, midia-e-voz]
---
# Mídia e voz

Transcrição local de áudio (Whisper) em processo isolado.

[[00 Início|← Início]]

| Módulo | Linhas | Usado por | Papel |
|---|---|---|---|
| [[transcricao_audio.py]] | 328 | 3 | Transcrição local de voz com worker Whisper isolado. |
| [[transcricao_audio_worker.py]] | 126 | 0 | Worker isolado para transcrição local com OpenAI Whisper/PyTorch. |

---
*Gerado por `tools/gerar_vault_codigo.py`.*
