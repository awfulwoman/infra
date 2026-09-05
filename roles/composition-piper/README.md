# Piper (Wyoming)

[Piper](https://github.com/rhasspy/piper) is a fast, local neural text-to-speech (TTS) system. This role deploys the Wyoming-protocol wrapper (`rhasspy/wyoming-piper`), which exposes Piper as a network service compatible with Home Assistant's Wyoming integration.

The default voice is `en_US-lessac-medium`. You can download additional voices and place them in `{{ composition_config }}/voices` to make them available without a rebuild.

## Ports

`10200` — Wyoming protocol TCP. Traefik also registers this port, though browsers do not typically use it.

## Key configuration

The container `command` argument sets the voice: `--voice en_US-lessac-medium`. Change this in the template to use a different default voice.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/piper` | Piper runtime data |
| `{{ composition_config }}/voices` | Voice model files |

## Integration

Home Assistant's Wyoming integration connects to `<host>:10200` to use Piper as the TTS provider for voice assistants and TTS services.
