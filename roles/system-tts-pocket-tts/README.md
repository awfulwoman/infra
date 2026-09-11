# system-tts-pocket-tts

Installs [Pocket TTS](https://github.com/kyutai-labs/pocket-tts) (Kyutai's ultra-low-latency
local TTS model) wrapped with the [Wyoming protocol](https://github.com/OHF-Voice/wyoming) via
[pocket-tts-streaming](https://github.com/MisterEcks/pocket-tts-streaming), running natively on
macOS instead of in Docker. Runs on Apple Silicon's native PyTorch build (MPS-accelerated),
which is significantly faster than the CPU-only build used in a Linux container — this is why
it lives on `apple-macmini-m4-16gb-malcolm` rather than a mini-PC composition host.

Same pattern as the sibling role [[system-tts-chatterbox]] — see that role's README for more
detail on the general approach (uv venv + launchd LaunchAgent).

## What it does

- Installs `uv` via Homebrew and uses it to create a dedicated Python 3.12 venv.
- Installs `pocket-tts`, `wyoming`, and the streaming script's other dependencies
  (`watchdog`, `zeroconf`, `stream2sentence`, `safetensors`, `numpy`) into that venv.
- Deploys `wyoming_server.py` verbatim from the upstream `pocket-tts-streaming` add-on — it's
  designed to fall back to plain environment variables when `/data/options.json` (the Home
  Assistant Supervisor's injected config) is absent, so it runs unmodified outside of Supervisor.
- Deploys and loads a per-user `launchd` LaunchAgent (`com.awfulwoman.pocket-tts`). Runs with
  `RunAtLoad`/`KeepAlive`, restarts on script or plist changes.

## Voices

The model ships 8 built-in voices (Les Misérables character names, not "real" names like Piper's
or Chatterbox's voice packs): `alba`, `azelma`, `cosette`, `eponine`, `fantine`, `javert`,
`jean`, `marius`. Drop a `.wav` reference clip or `.safetensors` embedding into
`{{ system_pocket_tts_base_dir }}/data/voices` to add a custom cloned voice — the server watches
that folder and loads new files automatically, no restart needed.

## Variables

See `defaults/main.yaml`:

- `system_pocket_tts_base_dir`: install directory. Defaults to `{{ awfulwoman_opt_dir }}/pocket-tts`.
- `system_pocket_tts_port`: Wyoming protocol TCP port. Defaults to `10222`.
- `system_pocket_tts_voice`: default voice, must be one of the 8 built-ins above. Defaults to `alba`.
- `system_pocket_tts_log_level`: defaults to `info`.
- `system_pocket_tts_hf_token`: Hugging Face token for gated model downloads (voice cloning).
  Defaults to `vault_huggingface_token` — the same secret [[system-tts-chatterbox]] already uses.

## Integration

Home Assistant's Wyoming integration connects to `malcolm:10222`.

## CLI / ad-hoc testing

`pocket-tts` is also available as a standalone Homebrew formula (`brew install pocket-tts`) for
quick CLI generation (`pocket-tts generate`) or its own one-off HTTP server, independent of this
role's Wyoming service and venv.

## Platforms

- macOS only (launchd). No Linux/systemd implementation exists — `tasks/main.yaml` only includes
  `install-macos.yaml` when `ansible_facts['os_family'] == 'Darwin'`.
