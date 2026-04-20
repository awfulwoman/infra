# Piper (Wyoming)

[Piper](https://github.com/rhasspy/piper) is a fast, local neural text-to-speech (TTS) system. This role deploys the Wyoming-protocol wrapper (`rhasspy/wyoming-piper`), which exposes Piper as a network service compatible with Home Assistant's Wyoming integration.

The default voice is `en_US-lessac-medium`. Additional voices can be downloaded and placed in `{{ composition_config }}/voices` to make them available without rebuilding.

## Ports

`10200` — Wyoming protocol TCP (also registered with Traefik, though this port is not typically accessed via browser).

## Key configuration

The voice is set via the container `command` argument: `--voice en_US-lessac-medium`. Change this in the template to use a different default voice.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/piper` | Piper runtime data |
| `{{ composition_config }}/voices` | Voice model files |

## Integration

Home Assistant's Wyoming integration connects to `<host>:10200` to use Piper as the TTS provider for voice assistants and TTS services.
