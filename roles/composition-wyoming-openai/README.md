# composition-wyoming-openai

Runs [wyoming_openai](https://github.com/roryeckel/wyoming_openai) (Apache-2.0), a
Wyoming-protocol proxy for OpenAI-compatible speech endpoints. It exposes Phonon
(Ollama's text-to-speech models on malcolm) to Home Assistant's Wyoming integration as
the standard TTS backend — see meta#23.

## What it does

- Runs two `ghcr.io/roryeckel/wyoming_openai:0.9.0` containers (Python 3.13-slim), one
  per dedicated Phonon model.
- Proxies Wyoming `synthesize` requests to Ollama's `/v1/audio/speech`
  (`TTS_OPENAI_URL`), TTS only — Phonon is text-to-speech, not STT.
- Publishes a Wyoming TCP port per language; HA adds one Wyoming integration per port.

## Endpoints

Wyoming TCP (not HTTP), no Traefik subdomain, no auth (same as the pocket-tts it
replaces); both are LAN-exposed.

| Service | Host port | Model | Voices |
| --- | --- | --- | --- |
| `wyoming-openai-en` | `homebrain:10300` | `phonon:latest` (English, Apache 2.0) | 12 US + 13 UK + 12 character |
| `wyoming-openai-de` | `homebrain:10301` | `phonon:40m-de` (German, CC BY-NC 4.0) | 13 |

## Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `composition_wyoming_openai_tts_url` | `{{ llm_default_openai_uri }}` | Ollama OpenAI-compatible `/v1` |
| `composition_wyoming_openai_en_port` | `10300` | Host-published Wyoming port (English) |
| `composition_wyoming_openai_en_model` | `phonon:latest` | English TTS model |
| `composition_wyoming_openai_en_voices` | 37 voices, region-prefixed | Voice → HA display name; also drives `--tts-voices` |
| `composition_wyoming_openai_de_port` | `10301` | Host-published Wyoming port (German) |
| `composition_wyoming_openai_de_model` | `phonon:40m-de` | German TTS model |
| `composition_wyoming_openai_de_voices` | 13 voices, region-prefixed | Voice → HA display name; also drives `--tts-voices` |

## Decisions

- **Two dedicated models, not the multilingual one.** The multilingual model normalizes
  numbers/times with the voice's language, so non-English voices read English text's
  numbers natively (meta#23). A dedicated model normalizes correctly for its own
  language, so English voices read English numbers and German voices read German numbers.
- **One shim service per model.** The proxy applies every configured voice to every
  model, so the English and German voice sets (disjoint) cannot share one instance.
  Hence two containers on two ports; HA adds both as Wyoming integrations.
- **No separate US/UK models.** Ollama only ships `phonon:latest` (English, which already
  carries both the US and UK voices) and `phonon:40m-de`; there is no 40M English,
  French, Spanish or Portuguese tag.
- **Voices on the command line.** The 12 character voices have multi-word names and
  `TTS_VOICES` is space-split, so each service passes its voices via `--tts-voices`
  (quoted, so multi-word names survive). `TTS_VOICE_LABELS` sets the region-prefixed
  description HA shows; the underlying voice name is unchanged.
- **Licences:** English `phonon` is Apache 2.0; German `phonon:40m-de` is CC BY-NC 4.0
  (non-commercial, fine for home use).
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
