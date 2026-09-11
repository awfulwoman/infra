# Pocket TTS Streaming (Wyoming)

[Pocket TTS](https://github.com/kyutai-labs/pocket-tts) is Kyutai's ultra-low-latency,
CPU-only local TTS model. This role deploys
[pocket-tts-streaming](https://github.com/MisterEcks/pocket-tts-streaming), a Wyoming-protocol
wrapper adding streaming, emotion tags, and voice cloning — normally distributed as a Home
Assistant Supervisor add-on, but built here as a plain Docker container since this host runs
HA Core (no Supervisor/add-on store).

The upstream project has no published image, so the compose file builds directly from the
add-on's Dockerfile via a git build context. `wyoming_server.py` falls back to plain env vars
when `/data/options.json` (the Supervisor-injected config) is absent, so it runs standalone
without modification.

## Ports

`10222` — Wyoming protocol TCP.

## Key configuration

Set in `.environment_vars`:

- `WYOMING_PORT` — defaults to `10222`.
- `DEFAULT_VOICE` — defaults to `alba`.
- `LOG_LEVEL` — defaults to `info`.
- `HF_TOKEN` — leave blank unless you want voice cloning against gated Hugging Face models.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/data` | Models, voices, pronunciation dict (`DATA_DIR`) |

## Integration

Home Assistant's Wyoming integration connects to `<host>:10222` to use Pocket TTS as a TTS
provider for voice assistants and TTS services — same pattern as `composition-piper`.

## Hardware note

Upstream recommends an Intel i5/N100-class CPU or better; inference is CPU-bound (no GPU
support). Watch this host for contention with its other compositions (Home Assistant, MQTT,
Zigbee2MQTT, etc.) since it's an 8GB mini-PC, not the storage server that runs Piper.
