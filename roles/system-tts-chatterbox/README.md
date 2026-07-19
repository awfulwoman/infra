# system-tts-chatterbox

Installs a [Chatterbox](https://github.com/resemble-ai/chatterbox) text-to-speech server exposed over the [Wyoming protocol](https://github.com/OHF-Voice/wyoming), with multi-voice cloning support. Intended for use as a Home Assistant/voice assistant TTS backend.

## What it does

- Installs `uv` via Homebrew and uses it to create a dedicated Python 3.11 venv.
- Installs `chatterbox-tts`, `wyoming`, and `numpy` into that venv.
- Deploys `server.py`, a Wyoming TTS server that wraps Chatterbox and supports per-request voice selection.
- Syncs reference voice clips from `files/voices/` to the target host (deletes any removed locally).
- Deploys and loads a per-user `launchd` LaunchAgent (`com.awfulwoman.chatterbox`) that runs the server with `RunAtLoad`/`KeepAlive`, restarting it whenever the server script, voices, or plist change.

## Voices

Reference clips live in `files/voices/` (`.wav`, `.m4a`, `.mp3`, `.flac`, `.ogg` all accepted — non-WAV files are converted via `ffmpeg` at synth time). The file stem is the voice name a client selects. Currently shipped:

- jeff-goldblum
- ken-jeong
- nick-offerman
- phoebe-waller-bridge
- rick-sanchez
- tom-scott

If `system_chatterbox_default_voice` is unset, the server falls back to the first voice alphabetically.

## Variables

See `defaults/main.yaml`:

- `system_chatterbox_base_dir`: install directory. Defaults to `{{ awfulwoman_opt_dir }}/chatterbox`.
- `system_chatterbox_host` / `system_chatterbox_port`: bind address for the Wyoming server. Defaults to `0.0.0.0:10200`.
- `system_chatterbox_default_voice`: file stem in `voices/` to use when a request doesn't specify one. Empty = first alphabetically.
- `system_chatterbox_exaggeration`: emotion exaggeration, `0.25`–`2.0` (lower = more neutral). Default `0.5`.
- `system_chatterbox_cfg_weight`: pacing control, `0.0`–`1.0` (lower = slower/more expressive). Default `0.5`.
- `system_chatterbox_stream_sentences`: split text into sentences and stream each independently. Default `true`.
- `system_chatterbox_turbo`: use ChatterboxTurbo (~2x faster, voice cloning, no CFG/exaggeration). Default `true`.

## Requirements

- `vault_huggingface_token`: Hugging Face token, injected into the LaunchAgent environment (`HF_TOKEN`) for model downloads.
- `ffmpeg` available at `/opt/homebrew/bin/ffmpeg` (used to convert non-WAV voice references).

## Platforms

- macOS only (launchd). No Linux/systemd implementation exists — `tasks/main.yaml` only includes `install-macos.yaml` when `ansible_facts['os_family'] == 'Darwin'`.
