# composition-wyoming-openai

Runs [wyoming_openai](https://github.com/roryeckel/wyoming_openai) (Apache-2.0), a
Wyoming-protocol proxy for OpenAI-compatible speech endpoints. It exposes Phonon
(Ollama's text-to-speech model on malcolm) to Home Assistant's Wyoming integration as
the standard TTS backend — see meta#23.

## What it does

- Runs the `ghcr.io/roryeckel/wyoming_openai:0.9.0` container (Python 3.13-slim).
- Proxies Wyoming `synthesize` requests to Ollama's `/v1/audio/speech`
  (`TTS_OPENAI_URL`), TTS only — Phonon is text-to-speech, not STT.
- Publishes the Wyoming TCP port on the host; HA's Wyoming integration connects to
  `homebrain:{{ composition_wyoming_openai_port }}`.

## Endpoint

Wyoming TCP (not HTTP): `homebrain:10300`. No Traefik subdomain — Wyoming is a binary
TCP protocol. No auth (same as the pocket-tts it replaces); it is LAN-exposed.

## Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `composition_wyoming_openai_port` | `10300` | Host-published Wyoming port |
| `composition_wyoming_openai_tts_url` | `{{ llm_default_openai_uri }}` | Ollama OpenAI-compatible `/v1` |
| `composition_wyoming_openai_tts_models` | `phonon:40m-multilingual` | TTS model |
| `composition_wyoming_openai_tts_voices` | 38 US/UK/DE voices | Voices advertised |
| `composition_wyoming_openai_languages` | `en de` | Languages advertised |

## Decisions

- **One model, `phonon:40m-multilingual`.** The proxy applies every configured voice to
  every model, so disjoint per-model voice sets (base `phonon` = English, `phonon:40m-de`
  = German) can't be combined. The multilingual model carries all 102 voices in one
  model, so a single shim instance exposes the 38 US + UK + German catalogue voices.
- **Voices: US + UK + German catalogue voices only.** The 12 English "character" voices
  (Captain Silas Blackwater, Fairy Godmother, …) are excluded — 11 of them have
  multi-word names and the shim parses `TTS_VOICES` with `.split()`, so they can't pass
  through the env var. Exposing them would need a `command:` override with `--tts-voices`.
- **Licence:** `phonon:40m-multilingual` is CC BY-NC 4.0 (non-commercial) — fine for
  home use, unlike the Apache-2.0 base `phonon` (English-only) it replaces.
- **TTS-only.** Ollama's speech models are TTS; STT would need a separate backend.
- **`TTS_BACKEND: OPENAI`** explicit, so autodetection never probes for the historical
  Kokoro/Speaches/LocalAI health endpoints.

## Data / ZFS

Stateless — no volumes, just environment config in the compose file. ZFS policy `none`.

## Deploy

```bash
ansible-playbook playbooks/hosts/minipc-8gb-homebrain/core.yaml \
  --tags composition -e target_composition=wyoming-openai
```
