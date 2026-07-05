#!/usr/bin/env python3
"""Wyoming TTS server backed by Chatterbox with multi-voice support."""

import argparse
import asyncio
import logging
import subprocess
import tempfile
import threading
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

FFMPEG = "/opt/homebrew/bin/ffmpeg"
SAMPLE_RATE = 24000
SAMPLE_WIDTH = 2  # 16-bit PCM
CHANNELS = 1
CHUNK_FRAMES = 4096
VOICE_EXTENSIONS = {".wav", ".m4a", ".mp3", ".flac", ".ogg"}


def ensure_wav(voice_path: str) -> str:
    if Path(voice_path).suffix.lower() == ".wav":
        return voice_path
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    _LOGGER.info("Converting %s → %s", voice_path, tmp.name)
    subprocess.run(
        [FFMPEG, "-y", "-i", voice_path, "-ar", "44100", "-ac", "1", tmp.name],
        check=True,
        capture_output=True,
    )
    return tmp.name


async def handle_connection(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    wyoming_info,
    model,
    voice_conds: dict,
    default_voice: str,
    cfg_weight: float,
    lock: threading.Lock,
) -> None:
    from wyoming.audio import AudioChunk, AudioStart, AudioStop
    from wyoming.event import async_read_event, async_write_event
    from wyoming.info import Describe
    from wyoming.tts import Synthesize

    addr = writer.get_extra_info("peername")
    _LOGGER.debug("Connection from %s", addr)
    try:
        while True:
            event = await async_read_event(reader)
            if event is None:
                break

            if Describe.is_type(event.type):
                await async_write_event(wyoming_info.event(), writer)
                continue

            if not Synthesize.is_type(event.type):
                continue

            synthesize = Synthesize.from_event(event)
            text = synthesize.text or ""
            voice_name = (synthesize.voice.name if synthesize.voice else None) or default_voice
            if voice_name not in voice_conds:
                _LOGGER.warning("Unknown voice %r, falling back to %s", voice_name, default_voice)
                voice_name = default_voice

            if not text.strip():
                await async_write_event(AudioStop().event(), writer)
                continue

            _LOGGER.info("Synthesizing [%s]: %.60s…", voice_name, text)

            conds = voice_conds[voice_name]
            loop = asyncio.get_event_loop()

            def generate():
                with lock:
                    model.conds = conds
                    return model.generate(text, cfg_weight=cfg_weight)

            wav = await loop.run_in_executor(None, generate)

            import numpy as np
            samples = wav.squeeze(0).cpu().numpy()
            pcm = (samples * 32767).clip(-32768, 32767).astype(np.int16).tobytes()

            await async_write_event(
                AudioStart(rate=SAMPLE_RATE, width=SAMPLE_WIDTH, channels=CHANNELS).event(),
                writer,
            )
            chunk_bytes = CHUNK_FRAMES * SAMPLE_WIDTH
            timestamp = 0
            for i in range(0, len(pcm), chunk_bytes):
                chunk = pcm[i : i + chunk_bytes]
                await async_write_event(
                    AudioChunk(
                        rate=SAMPLE_RATE,
                        width=SAMPLE_WIDTH,
                        channels=CHANNELS,
                        audio=chunk,
                        timestamp=timestamp,
                    ).event(),
                    writer,
                )
                timestamp += len(chunk) // SAMPLE_WIDTH
            await async_write_event(AudioStop().event(), writer)
            _LOGGER.info("Finished (%d samples)", len(pcm) // SAMPLE_WIDTH)

    except Exception:
        _LOGGER.exception("Error handling connection from %s", addr)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def main() -> None:
    parser = argparse.ArgumentParser(description="Wyoming TTS server backed by Chatterbox")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=10200)
    parser.add_argument("--voices-dir", required=True, help="Directory of reference audio files")
    parser.add_argument("--default-voice", default="", help="Default voice name (file stem); uses first alphabetically if unset")
    parser.add_argument("--exaggeration", type=float, default=0.5)
    parser.add_argument("--cfg-weight", type=float, default=0.5)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    import perth
    import torch
    from wyoming.info import Attribution, Info, TtsProgram, TtsVoice, TtsVoiceSpeaker

    if not callable(getattr(perth, "PerthImplicitWatermarker", None)):
        class _NoOpWatermarker:
            def apply_watermark(self, audio, *args, **kwargs):
                return audio
        perth.PerthImplicitWatermarker = _NoOpWatermarker

    from chatterbox.tts import ChatterboxTTS

    voices_dir = Path(args.voices_dir)
    voice_files = sorted(
        f for f in voices_dir.iterdir()
        if f.is_file() and f.suffix.lower() in VOICE_EXTENSIONS
    )
    if not voice_files:
        raise SystemExit(f"No voice files found in {voices_dir}")

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    _LOGGER.info("Loading Chatterbox on %s…", device)
    model = ChatterboxTTS.from_pretrained(device=device)

    _LOGGER.info("Pre-computing conditionals for %d voice(s)…", len(voice_files))
    voice_conds = {}
    for voice_file in voice_files:
        name = voice_file.stem
        wav_path = ensure_wav(str(voice_file))
        _LOGGER.info("  → %s", name)
        model.prepare_conditionals(wav_path, exaggeration=args.exaggeration)
        voice_conds[name] = model.conds

    default_voice = args.default_voice if args.default_voice in voice_conds else next(iter(voice_conds))
    _LOGGER.info("Default voice: %s", default_voice)

    _LOGGER.info("Warming up MPS graph…")
    model.conds = voice_conds[default_voice]
    model.generate("Warm up.", cfg_weight=args.cfg_weight)
    _LOGGER.info("Model ready")

    _attribution = Attribution(name="Resemble AI", url="https://github.com/resemble-ai/chatterbox")
    wyoming_info = Info(
        tts=[
            TtsProgram(
                name="chatterbox",
                attribution=_attribution,
                installed=True,
                description="Chatterbox TTS by Resemble AI",
                version=None,
                voices=[
                    TtsVoice(
                        name=name,
                        attribution=_attribution,
                        installed=True,
                        description=f"Cloned voice: {name}",
                        version=None,
                        languages=["en-us"],
                        speakers=[TtsVoiceSpeaker(name=name)],
                    )
                    for name in voice_conds
                ],
            )
        ]
    )

    lock = threading.Lock()
    handler = lambda r, w: handle_connection(
        r, w, wyoming_info, model, voice_conds, default_voice, args.cfg_weight, lock
    )
    server = await asyncio.start_server(handler, args.host, args.port)
    _LOGGER.info("Listening on %s:%d", args.host, args.port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
