# Conduit speech server: local STT + TTS options

Researched 2026-11-25. Primary sources only (source code, official READMEs and docs). `UNVERIFIED` means not confirmed in a primary source.

Goal: give the Conduit iPhone app a local speech pipeline through the `hermes-conduit-notifier` plugin (in the `hermes-jarvis` container on agatha). The plugin setting `voice.speech_server.url` needs a server that speaks the OpenAI Realtime WebSocket protocol.

Source shorthand:

- `CN` = https://github.com/kaishi00/hermes-conduit-notifier (MIT, last push 2026-11-25)
- `S2S` = https://github.com/huggingface/speech-to-speech (Apache-2.0, `pyproject.toml`; last push 2026-11-25)
- `SP` = https://github.com/speaches-ai/speaches (MIT)

## 1. What the plugin requires of a speech server

### 1.1 Address, auth, test

- Setting: `voice.speech_server.url`. A bare host gets path `/v1/realtime`. `http(s)` is turned into `ws(s)`. Plain `ws://` only works for loopback, private, link-local, Tailscale or LAN-style names. Source: `CN/dashboard/api/speech_server.py`, `speech_server_url()` and the header comment; `CN/README.md` section "Your own speech server".
- Other keys: `api_key`, `api_key_file`, `drive_turns`, `transcription_model`, `model`, `voice`, plus `own_model`. The plugin sends `Authorization: Bearer <key>` only when a key is set. Source: `speech_server.py`, `_speech_server_headers()`.
- The phone never talks to the speech server. The plugin relays Conduit's realtime events from its own host. So the speech server only needs to be reachable from agatha (`hermes-jarvis` container). Source: `speech_server.py` header comment.
- Readiness/test check (`POST /speech-server/test`): the plugin dials the URL and waits `SPEECH_SERVER_TEST_FIRST_EVENT_S = 5.0` s for the first frame.
  - Pass: the first frame is JSON with a string `type`, and `type != "error"`. Normally `session.created`.
  - Fail messages: nothing sent in 5 s; non-Realtime JSON; an `error` event first.
  - `abilities` is read from that first event: `session.model`, `session.audio.output.voice` (or `session.voice`) and `session.audio.input.turn_detection.create_response`. All are optional.
  - Connect timeout is 5 s. The whole call stays under 12 s.
  - Source: `speech_server.py`, `post_speech_server_test()` and `speech_server_abilities()`.
- A socket that sends nothing for 60 s is closed. Client frames over 256 KB are refused. Server frames over 4 MiB are refused. At most 3 relays per profile and 8 per host. Source: `speech_server.py` constants.
- Reply-frame names: the plugin accepts both beta (`response.audio.delta`) and GA (`response.output_audio.delta`) names. If a server sends both, the plugin drops the copy under the name seen second. Pairs: `audio.delta`, `audio.done`, `audio_transcript.delta`, `audio_transcript.done`, `text.delta`, `text.done`. Source: `speech_server.py`, `_SPEECH_SERVER_DIALECT_PAIRS`; `CN/README.md` "Your own speech server".
- `session.update` handling: the plugin rewrites the frame. It adds `session.audio.output.voice` from `voice.speech_server.voice` unless the frame names one. With `drive_turns` it also adds `instructions` ("You are a text-to-speech voice...") and `audio.input.transcription = {model: transcription_model}`. Source: `speech_server.py`, `SpeechServerSetup.update()`, `SpeechServerDrive.update()`.
  - So the server must accept `session.update` carrying `instructions`, `audio.output.voice`, `audio.input.transcription` and `audio.input.turn_detection`.
  - A server that errors on unknown fields would break. S2S deep-merges `session.update`: `S2S/src/speech_to_speech/api/openai_realtime/README.md`, client events table.

### 1.2 Three roles the plugin gives a speech server

1. Classic voice "listen": the plugin streams mic audio via `input_audio_buffer.append`. It needs `conversation.item.input_audio_transcription.completed` back.
2. Classic voice "speak" (`/local-live/socket?mode=speak`, plugin 0.42+): the plugin sends each Hermes reply sentence as a user `conversation.item.create` plus `response.create`. The server reads the text back as audio. Source: `CN/README.md`, text after the Local Live route table ("`/local-live/socket?mode=speak` is Classic voice's reply voice...").
   - README says "Classic then uses one server for listening and speaking. While the reply plays, Classic may open its listening socket too, so start the server with `--num_pipelines 2`" (an S2S flag).
3. Local Live (full live calls) with two sub-modes:
   - Server has an LLM: the server asks the plugin's "model address" (an OpenAI chat-completions route on the dashboard) for each reply.
   - Server is read-back only: the plugin drives turns itself (section 1.3).
   - Source: `CN/README.md` "Local Live: live calls through your own voice server" and "Local Live on a read-back speech server".

### 1.3 Read-back mode (what the plugin sends and expects)

Source for this whole section: `CN/dashboard/api/local_live_read_back.py` (file header and code), `CN/README.md` "Local Live on a read-back speech server".

- A server counts as read-back when it refuses automatic responses. Refusal is `error` with `code == "realtime_live_unavailable"`, or `param` in `session.audio.input.turn_detection.create_response` or `session.turn_detection.create_response` (`_local_live_refuses_live`). The plugin then resends its `session.update` with `turn_detection.create_response=false` and `interrupt_response=false` (`_local_live_read_back_update`).
- With `voice.speech_server.drive_turns: true` the plugin skips the refusal handshake. It sends `create_response: false` from the first `session.update`, tells the server (in `instructions`) to read text aloud verbatim, and cancels any response the server starts on its own.
- Server must emit:
  - `conversation.item.input_audio_transcription.completed` with `transcript`. This starts a Hermes turn.
  - `input_audio_buffer.speech_started`. This is barge-in; the plugin cancels the reply.
  - `conversation.item.input_audio_transcription.failed` is also handled.
- Plugin sends, one per reply sentence:
  `{"type":"response.create","response":{"conversation":"none","input":[{"type":"message","role":"user","content":[{"type":"input_text","text":"<sentence>"}]}]}}`.
  With `drive_turns` it adds `response.instructions` and `response.metadata = {"conduit":"say"}` (`_pump()`). A server that refuses the metadata gets the sentence again without it.
- Server must answer with:
  - `response.created`
  - audio deltas: `response.output_audio.delta` or `response.audio.delta` (matched by substring `"response.output_audio.delta"` / `"response.audio.delta"`)
  - transcript events: `response.output_audio_transcript.delta` and `.done` (or the `audio_transcript` beta names)
  - `response.done`
  - Other events passed through: `response.output_item.added/done`, `response.output_audio.done`, `response.content_part.added/done`.
- Plugin also sends `response.cancel`. A server error saying there was nothing to cancel is swallowed. Watchdogs: 30 s without a response or audio, 2 s after a cancel.
- Sentence rules: first sentence goes as soon as it ends; later ones join to 40 chars; 400 chars max; text waiting 1.2 s goes anyway.
- The "two sentences' transcripts must match" check (`LOCAL_LIVE_READ_BACK_MIN_MATCH = 0.6`, `CHECK_WORDS = 5`, `MISSES = 2`):
  - For a sentence of 5 or more words with no digits, the plugin compares the server's `response.output_audio_transcript.done.transcript` with the sentence. It uses `difflib.SequenceMatcher` on lower-cased words and needs a ratio of at least 0.6.
  - Two misses in a row end the call with "Your speech server doesn't read text back as it's given...". The phone's socket closes 4400.
  - So the server must return a TTS transcript equal to the input text. An LLM-backed server will fail this unless it echoes verbatim.
  - This check only applies to Local Live read-back. It does not apply to plain Classic listen.
- Audio sample rate/format: UNVERIFIED. The relay forwards audio frames untouched. The rate is negotiated between Conduit (iOS) and the server. The Conduit app source is not public in the plugin repo. S2S documents "PCM 24 kHz config" as supported (`S2S/.../openai_realtime/README.md` line 218, compat table).
- `turn_detection`: `create_response: false` must be honoured when sent. `speech_started` / `speech_stopped` must still fire.

### 1.4 `drive_turns` and `own_model`

- `drive_turns: false` is the plugin's own preset for S2S (`CN/dashboard/speech_server_presets.json`, entry `speech-to-speech`, `url_hint` `ws://192.168.1.20:8765/v1/realtime`, `needs_key: false`). S2S is a documented, first-class target of the plugin.
- `drive_turns: true` makes a server with its own model act only as an STT and voice. Presets for OpenAI Realtime and Qwen use it.
- `own_model: true` lets the server's model answer Local Live calls (`speech_server.py`, `speech_server_own_model()`).

## 2. huggingface/speech-to-speech (S2S)

### 2.1 Backends

Source: `S2S/README.md`, "Supported Components" table; `S2S/src/speech_to_speech/STT/README.md`.

- Pipeline: Silero VAD, then STT, then LLM, then TTS. Each stage is swappable.
- STT backends: Parakeet TDT (default; CUDA/CPU through nano-parakeet, Apple Silicon through MLX), Parakeet Unified, Nemotron streaming, Whisper (Transformers, CUDA/CPU), Faster Whisper (extra `faster-whisper`), Lightning Whisper MLX (extra `whisper-mlx`), MLX Audio Whisper (macOS), Paraformer, Qwen3-ASR, plus remote:
  - OpenAI-compatible `/v1/audio/transcriptions` (`--stt openai`)
  - OpenAI Realtime transcription
  - vLLM Realtime transcription (experimental)
- TTS backends:
  - Qwen3-TTS (default; GGML on Linux, mlx-audio on macOS)
  - Kokoro-82M (extra `kokoro`; on macOS needs Python 3.11 or 3.12)
  - KittenTTS, Pocket TTS, ChatTTS, OmniVoice, Irodori, MMS
  - Phonon, local (extra `phonon`, "CPU (including Apple Silicon)", default checkpoint `gradium/phonon-31m-en`, Apache-2.0; README section "Phonon TTS")
  - Remote OpenAI-compatible `/v1/audio/speech` (`--tts openai`)
- Remote STT details (`S2S/docs/openai-compatible-stt.md`): VAD audio is uploaded as a mono PCM16 16 kHz WAV via `POST /v1/audio/transcriptions`. The response may be JSON `{text}` or plain text. Flags: `--stt openai --openai_stt_base_url <url> --openai_stt_model <model>`. The doc's worked example uses vLLM serving Qwen3-ASR.
- Remote TTS details (`S2S/docs/openai-compatible-tts.md`): `POST /v1/audio/speech` returns PCM16. The handler converts it to 16 kHz.
  - Flags: `--tts openai --openai_tts_base_url ... --openai_tts_model ... --openai_tts_voice ... --openai_tts_response_format pcm --openai_tts_sample_rate 24000`.
  - Servers with their own voice names need `--openai_tts_voice_override`, because clients send Qwen speaker names.
  - Ollama's `/v1/audio/speech` is 24 kHz mono PCM16 with `pcm` as an option (`ollama/docs/api/openai-compatibility.mdx`). That matches. Whether S2S's `openai` TTS handler works against Ollama is UNVERIFIED; no doc says so.
- The S2S docs do not mention Speaches or Ollama by name.

### 2.2 LLM requirement

- An LLM stage is always present. Defaults: MLX LM on Apple Silicon (Qwen3.5-4B 4-bit, "16 GB of unified memory"), Transformers on Linux ("24 GB of VRAM" with NVIDIA; "Slow replies" on CPU). Source: `S2S/README.md` Quickstart table.
- It can be remote: `--llm_backend responses-api` or `--llm_backend chat-completions` with `--responses_api_base_url` and `--responses_api_api_key` (README, "LLM Backends"). Any llama.cpp, vLLM or hosted OpenAI-compatible server works.
  - The Ollama `/v1/chat/completions` endpoint on malcolm is OpenAI-compatible (`ollama/docs/api/openai-compatibility.mdx`). Pairing it with S2S is plausible but UNVERIFIED.
- `--stt none` exists, but it sends VAD audio to an audio-capable LLM, so it is not "no STT" (`S2S/docs/configuration.md`: "To bypass STT, use `backend: none`... The LLM backend and remote model must support audio input").
- Whether the LLM stage can be skipped entirely: UNVERIFIED, and no flag is documented.
- The plugin's way of supplying the LLM: point S2S at the plugin's Local Live model address, so Hermes answers.

  ```
  speech-to-speech serve --llm_backend chat-completions \
    --responses_api_base_url https://<dashboard>/api/plugins/conduit_push/local-live/v1 \
    --responses_api_api_key <key> --model_name conduit --stream_batch_sentences 1
  ```

  Source: `CN/README.md`, "Local Live" step 3.
- Does S2S honour read-back (`response.create` with `conversation:"none"` and inline `input`) without calling its LLM? UNVERIFIED. The plugin's `mode=speak` route gets read-back by serving a fake LLM that echoes the text.
- Does S2S honour `create_response: false`? Yes. `runtime_config.py` has `create_response_enabled`, used in `service.py` to gate automatic generation. Source: `S2S/src/speech_to_speech/api/openai_realtime/runtime_config.py` lines ~121-130.

### 2.3 Docker, CPU/GPU, Apple Silicon

- Official files: `S2S/Dockerfile` and `S2S/Dockerfile.arm64`. Both use base `nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04` (the arm64 one only pins `--platform linux/arm64`). Both install via `uv sync`. Neither has a `USER` line, so they run as root. That conflicts with Charlie's non-root rule.
- `S2S/docker-compose.yml`: a `llama` service (`ghcr.io/ggml-org/llama.cpp:server-cuda`) plus a `pipeline` service, both reserving an NVIDIA GPU. The pipeline listens on `8765`, and the compose file exposes `8080` and `8765`. README, "Docker": "Install the NVIDIA Container Toolkit".
- There is no CPU-only image or Dockerfile, and no published image in the repo. The `publish.yml` workflow only publishes to PyPI. A ghcr image: UNVERIFIED (I could not list packages). Only `demo/Dockerfile` is built in CI, and that is the browser demo.
- GPU: NVIDIA only. No NVIDIA GPU exists on agatha. Whether storage has one: UNVERIFIED (check `hosts.md`).
- CPU Linux: supported through `pip install speech-to-speech`. Default STT Parakeet uses nano-parakeet on CPU. Default TTS Qwen3-TTS has a CPU-only GGML wheel (`qwentts-cpp-python==0.3.1+cpu`, README near line 184). A CPU-only container would have to be written by hand.
- Apple Silicon (MLX): `pip install` or `speech-to-speech serve` natively. README "Quickstart": Python 3.11-3.14 on Apple Silicon macOS, "16 GB of unified memory" suggested. `speech-to-speech local -f example_configs/mac.yaml` runs Parakeet (MLX), mlx-lm and Qwen3-TTS locally (`S2S/docs/configuration.md`). Docker on macOS cannot reach MLX or Metal, so on malcolm it must run as a native process, not a container.
- Resource numbers (README): 16 GB unified memory for the Mac default (STT + 4B LLM + TTS); 24 GB VRAM for the NVIDIA default. With remote LLM, STT and TTS, local needs are lower (VAD only), but S2S does not document figures. UNVERIFIED.

### 2.4 Auth, ports, config

- Command: `speech-to-speech serve`. Default bind `127.0.0.1`, default port 8765, path `/v1/realtime`. Use `--host 0.0.0.0` for network exposure. README "CLI reference": "`serve` binds to `127.0.0.1` by default; pass `--host 0.0.0.0` explicitly".
- Auth: none. README, Realtime API section: "The server performs no authentication and no throttling of its own." The code agrees. `rg` for `Authorization|bearer` under `api/openai_realtime` only matches the LLM proxy upstream key and the client. Put it behind a reverse proxy if needed. The plugin can add a Bearer key. It also states: "speech-to-speech has no authentication of its own, so keep it on your network" (`CN/README.md`).
- Config is by CLI flags, or a YAML file with `-f` (`S2S/docs/configuration.md`). The YAML uses `schema_version: 1`, `blocks` (kinds vad/stt/llm/tts) and `pipelines`. Values can come from `{env: NAME}`. There is no `.env` or string interpolation.
- Multiple concurrent pipelines: `--num_pipelines N` (YAML `num_pipelines`). Needed for the plugin's speak plus listen sockets.
- Protocol support, `S2S/.../openai_realtime/README.md`:
  - Server to client: `session.created` (sent on connection, WebSocket), `conversation.item.input_audio_transcription.delta/.completed`, `response.created`, `response.output_audio.delta/.done`, `response.output_audio_transcript.delta/.done`, `response.done`, `input_audio_buffer.speech_started`.
  - Client to server: `input_audio_buffer.append`, `session.update`, `conversation.item.create`, `conversation.item.truncate`, `response.create`, `response.cancel`.
  - Caveat in the README: "a tested core subset, not a claim of full OpenAI Realtime API equivalence".
  - These event names are the GA names. The beta names are not emitted. The plugin accepts both.

### 2.5 Fit against the plugin

- Matches: GA event names, `session.created` first, `create_response` honoured, `speech_started`, transcription `.completed`, PCM 24 kHz config. It is the named preset in the plugin.
- Gaps and risks:
  - S2S is an LLM pipeline. The plugin's own speak route uses a fake LLM to get read-back, so the documented recipe needs the plugin's model address reachable from the S2S host.
  - No container image for CPU or Apple Silicon.
  - The default STT, TTS and LLM are heavy for agatha (8 GB).
  - Pairing S2S with remote STT (`--stt openai`) and TTS (`--tts openai`) is documented in S2S but untested against Ollama and Speaches here.

## 3. STT servers that speak OpenAI `/v1/audio/transcriptions`

| Server | Endpoint | Docker / arm64 | Notes |
|---|---|---|---|
| Speaches (`SP`, MIT) | `POST /v1/audio/transcriptions` with `-F file=@... -F model=...` (`SP/docs/usage/speech-to-text.md`). Also `/v1/audio/speech` and `/v1/realtime`. | `compose.cpu.yaml` uses `ghcr.io/speaches-ai/speaches:latest-cpu`. The image runs as non-root `ubuntu` (UID 1000; Dockerfile). The CI matrix builds `-cuda` and `-cpu` tags. arm64 in the published image: UNVERIFIED (docs only show `docker buildx build --platform linux/amd64,linux/arm64`, `SP/docs/installation.md`). | Models are downloaded by id, e.g. `Systran/faster-distil-whisper-small.en` (faster-whisper). TTS: Kokoro-82M ONNX and Piper. RAM figures: UNVERIFIED. |
| whisper.cpp server | README documents `/inference` (multipart `file`, `response_format`, `temperature`) and `/load`. Flags `--inference-path`, `--port` (default 8080), `--host` (default 127.0.0.1), `--convert` (needs ffmpeg). Source: https://github.com/ggml-org/whisper.cpp/blob/master/examples/server/README.md | The server README has no Docker info. Whether the upstream repo ships a server image: UNVERIFIED. | Not natively OpenAI-shaped. The `--inference-path /v1/audio/transcriptions` flag may allow it, but response-format compatibility is UNVERIFIED. The README warns to run it sandboxed and unprivileged. |
| Ollama | Yes. `POST /v1/audio/transcriptions`, also `/v1/audio/translations`. Fields: `file` (WAV), `model`, `language`, `prompt`, `response_format` (json/text/verbose_json), `temperature`, `stream`. Audio over 30 s is split at pauses. Source: https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx | It is the same Ollama already on malcolm. | Needs "models that accept audio input" (capability `audio`; `integration/audio_test.go`). Ollama's own docs do not list which models. The ollama.com library shows an `audio` tag on `lfm3-audio` ("LFM3-Audio-2B ... compact"), `gemma4` and `nemotron-3.5-bolt`. No Whisper model was found there. Which Ollama release added transcriptions: UNVERIFIED (latest release is v0.40.18, 2026-11-24). Whether the installed malcolm version has it: UNVERIFIED. |
| vLLM | `vllm serve Qwen/Qwen3-ASR-1.7B` serves `/v1/audio/transcriptions` (`S2S/docs/openai-compatible-stt.md`). | CUDA-oriented. Not assessed. | |
| kcosr/openai-speech-server | HTTP STT/TTS (Parakeet, Kokoro workers) plus `/v1/realtime?intent=transcription` only. Source: https://github.com/kcosr/openai-speech-server (MIT, 2 stars) | Not assessed. | It "rejects conversational Realtime, `response.*`". It cannot read replies back, so it is unusable for TTS through the plugin. Tiny project. |

Small-model RAM figures for faster-whisper, whisper.cpp and the Ollama audio models: UNVERIFIED; none were found in the official READMEs read here.

Ollama TTS (already deployed): `/v1/audio/speech`, WAV default or `pcm`, 16-bit mono 24 kHz, `input` up to 4,096 chars, `stream_format=audio` only (`ollama/docs/api/openai-compatibility.mdx`). See also `roles/composition-wyoming-openai/README.md` ("TTS-only. Ollama's speech models are TTS; STT would need a separate backend.").

## 4. Existing Realtime servers over OpenAI-style STT/TTS

A search (primary pages checked) found no project whose job is "Realtime WebSocket front over any OpenAI `/v1/audio/*` endpoints with read-back". Closest candidates:

| Project | What it is | Fit |
|---|---|---|
| S2S (`--stt openai --tts openai`) | Realtime server that calls remote `/v1/audio/transcriptions` and `/v1/audio/speech` | Closest match. It is the adapter, with a mandatory LLM stage. The plugin preset exists. |
| Speaches `/v1/realtime` | Realtime front over its own STT/TTS. Doc: https://speaches.ai/usage/realtime-api/, `SP/docs/usage/realtime-api.md` | Not read-back-safe. `response.create` with `input`, `conversation` or `metadata` publishes an "unsupported field" error (`SP/src/speaches/realtime/response_event_router.py`, `handle_response_create_event`). `response.cancel` is not implemented (`handle_response_cancel_event` returns an error). Conversation mode calls an external LLM. `intent=transcription` mode (listen only) may work for the Classic listen socket (doc statement, plugin interaction UNVERIFIED). Auth: Bearer, `X-API-Key` or `api_key` query. Own TTS only (Kokoro ONNX default), not Phonon. |
| LocalAI | Go server. `/v1/realtime` as a VAD, STT, LLM, TTS pipeline from a model YAML (`pipeline: {vad, transcription, llm, tts}`). Doc: https://github.com/mudler/LocalAI/blob/master/docs/content/api/openai-realtime.md (MIT) | Stages are LocalAI-managed backends, not arbitrary remote OpenAI URLs (UNVERIFIED: no doc says a stage can name an external URL). Read-back and `create_response` handling: UNVERIFIED. Heavy to adopt only for this. |
| lfm3-realtime (MhaWay) | Single-model LFM3-Audio server (search listing only; repo not read) | One model, no separate STT/TTS, so cannot reuse Phonon. Not assessed further. |

## 5. What a custom adapter would have to implement

An adapter exposing `ws://host:port/v1/realtime`, backed by a Whisper-style HTTP server (`/v1/audio/transcriptions`) plus Ollama `/v1/audio/speech`. Derived from section 1 and `CN/dashboard/api/local_live_read_back.py`:

1. Accept the WebSocket upgrade at `/v1/realtime`, optional `?model=`. Optionally check `Authorization: Bearer`.
2. Send `session.created` at once (first frame, within 5 s). Include `session.model`, `session.audio.output.voice` and `session.audio.input.turn_detection.create_response=false`, or leave them out.
3. `session.update`: merge, tolerate unknown fields (`instructions`, `audio.output.voice`, `audio.input.transcription`, `tools`), and reply `session.updated`. If a client asks for `create_response=true`, either honour it or answer `error` code `realtime_live_unavailable` (the plugin's read-back signal).
4. `input_audio_buffer.append`: base64 PCM. Needs server-side VAD (Silero or webrtcvad) to find turns, because the plugin relays and never commits (`CN/README.md`, drive/relay design; the exact client commit behaviour is UNVERIFIED). Emit `input_audio_buffer.speech_started` and `speech_stopped`, optionally `committed` and `conversation.item.created`. Resample to 16 kHz mono WAV, POST it to `/v1/audio/transcriptions`, then emit `conversation.item.input_audio_transcription.completed` with `item_id` and `transcript`. Also emit `.failed` on error.
5. `conversation.item.create` (`input_text`): store it, or ack with `conversation.item.created`.
6. `response.create` with `response.input[].content[].text`: call `/v1/audio/speech` with `response_format=pcm` and `stream_format=audio`, then emit in order:
   - `response.created`
   - one or more `response.output_audio.delta` (base64 PCM, in the format Conduit negotiated; rate UNVERIFIED)
   - `response.output_audio.done`
   - `response.output_audio_transcript.delta` and `.done`, where the transcript must equal the input text so the 0.6 match check passes
   - `response.done` with `status: completed`
7. `response.cancel`: abort the in-flight HTTP stream and emit `response.done` with `status: cancelled`. Never leave a response hanging past 30 s.
8. Ignore or accept `response.metadata` (`{"conduit":"say"}`) and `response.conversation = "none"`. Never auto-generate a response.
9. Concurrency: at least 2 sessions (listen plus speak).
10. Strip markdown or normalise numbers? Not required. The check skips sentences with digits.

Needs only httpx, a WebSocket library, a VAD and a PCM resampler. All of them exist on PyPI. The same-named plugin README admits only S2S, Hermes Live Voice's local mode, and hosted OpenAI/Qwen as known servers.

## 6. Recommendation

| Option | Pros | Cons |
|---|---|---|
| A. Run S2S | Named preset in the plugin. Maintained (Apache-2.0, ~13.8k stars, active). Honours `create_response=false`. Has remote STT and TTS backends. | Mandatory LLM stage. No CPU or Apple Silicon container; official Dockerfiles are NVIDIA-CUDA and run as root. No auth. Read-back is not native, so you need the plugin's model-address recipe, and that makes Hermes the LLM, with latency and one-call-per-profile limits. Heavy defaults (16 to 24 GB). |
| B. Custom adapter | Smallest footprint; reuses Phonon on malcolm; exact fit to the plugin's read-back contract; can run on agatha. | Violates "don't build if suitable exists" unless A and C fail. Must be written and tested against the iOS client. Audio format is unverified. |
| C. Existing third-party adapter (Speaches or LocalAI realtime) | Speaches ships a CPU image, non-root, and serves STT+TTS+Realtime in one container. | Speaches rejects the read-back request fields and has no `response.cancel`. LocalAI pipelines are internal backends. Neither reuses Phonon. Neither is a plugin preset. |

Recommended path:

1. First try A as a native process on malcolm, not a container. Use `--stt whisper-mlx` or the default Parakeet MLX for STT, the local Phonon TTS (`--tts phonon`, same model family as the Ollama Phonon already in use), and `--llm_backend chat-completions` pointed at the plugin's model address. This exercises the exact configuration the plugin documents, using the one host (Apple Silicon) where S2S is fully supported. Set `voice.speech_server.url: ws://malcolm:8765/v1/realtime`, `drive_turns: false`, and `--num_pipelines 2`. Add a reverse proxy or firewall rule, since S2S has no auth.
2. If STT must stay remote or a container is required, run Speaches `latest-cpu` as the STT endpoint. Check first that its image is published for arm64 if the host is arm64. Point S2S's `--stt openai` at it. Validate S2S's `--tts openai` against Ollama `/v1/audio/speech` before relying on it (UNVERIFIED).
3. Only if A fails the read-back test (the plugin "doesn't read text back" error), write the thin adapter (B) from section 5. Do a test run first with the plugin's `POST /speech-server/test` to confirm `session.created`.

Open items before deciding:

- Which Ollama version on malcolm, and whether it serves `/v1/audio/transcriptions` with a usable audio model (Whisper-quality STT is not documented there).
- Conduit's audio format and rate (sample rate and encoding on the wire).
- Whether Hermes as the S2S LLM adds unacceptable latency for Classic speak.
