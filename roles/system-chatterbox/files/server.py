#!/usr/bin/env python3
"""Wyoming TTS server backed by Chatterbox."""

import argparse
import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

_LOGGER = logging.getLogger(__name__)

FFMPEG = "/opt/homebrew/bin/ffmpeg"
SAMPLE_RATE = 24000
SAMPLE_WIDTH = 2  # 16-bit PCM
CHANNELS = 1
CHUNK_FRAMES = 4096


def ensure_wav(voice_path: str) -> str:
    """Convert voice file to WAV if needed; return path to a WAV file."""
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
    voice_path: Optional[str],
    exaggeration: float,
    cfg_weight: float,
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
            if not text.strip():
                await async_write_event(AudioStop().event(), writer)
                continue

            _LOGGER.info("Synthesizing: %.60s…", text)

            loop = asyncio.get_event_loop()
            wav = await loop.run_in_executor(
                None,
                lambda: model.generate(
                    text,
                    audio_prompt_path=voice_path,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight,
                ),
            )

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
    parser.add_argument("--voice", help="Path to reference WAV for voice cloning", default=None)
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

    # resemble-perth ships a Linux-only native extension; on macOS the class is None.
    # Patch it with a no-op before ChatterboxTTS initialises.
    if not callable(getattr(perth, "PerthImplicitWatermarker", None)):
        class _NoOpWatermarker:
            def apply_watermark(self, audio, *args, **kwargs):
                return audio
        perth.PerthImplicitWatermarker = _NoOpWatermarker

    from chatterbox.tts import ChatterboxTTS

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
                        name="default",
                        attribution=_attribution,
                        installed=True,
                        description="Default voice",
                        version=None,
                        languages=["en-us"],
                        speakers=[TtsVoiceSpeaker(name="default")],
                    )
                ],
            )
        ]
    )

    if args.voice:
        args.voice = ensure_wav(args.voice)

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    _LOGGER.info("Loading Chatterbox on %s…", device)
    model = ChatterboxTTS.from_pretrained(device=device)
    _LOGGER.info("Model ready")

    handler = lambda r, w: handle_connection(
        r, w, wyoming_info, model, args.voice, args.exaggeration, args.cfg_weight
    )
    server = await asyncio.start_server(handler, args.host, args.port)
    _LOGGER.info("Listening on %s:%d", args.host, args.port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
