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
| `composition_wyoming_openai_tts_models` | `phonon phonon:40m-de` | TTS models |
| `composition_wyoming_openai_tts_voices` | `default` | Voices advertised |
| `composition_wyoming_openai_languages` | `en de` | Languages advertised |

## Decisions

- **Voices: `default` only.** The proxy applies every configured voice to every model.
  phonon's ~38 English voices and phonon:40m-de's ~14 German voices are disjoint, so
  listing them all would advertise invalid `voice × model` pairs. `default` is the one
  name both models share. Revisit when per-model voices are needed (one shim instance
  per model, or voice labels).
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
