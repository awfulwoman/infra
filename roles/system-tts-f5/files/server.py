#!/usr/bin/env python3
"""Wyoming TTS server backed by F5-TTS with zero-shot voice cloning."""

import argparse
import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path

import numpy as np

_LOGGER = logging.getLogger(__name__)

FFMPEG = "/opt/homebrew/bin/ffmpeg"
SAMPLE_RATE = 24000
SAMPLE_WIDTH = 2  # 16-bit PCM
CHANNELS = 1
CHUNK_FRAMES = 4096
MAX_REF_SECONDS = 15  # F5-TTS works best with 5-15s reference clips


def prepare_ref_audio(voice_path: str) -> str:
    """Convert to 24kHz mono WAV, trimmed to MAX_REF_SECONDS."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    _LOGGER.info("Preparing reference audio: %s → %s", voice_path, tmp.name)
    subprocess.run(
        [
            FFMPEG, "-y", "-i", voice_path,
            "-ar", str(SAMPLE_RATE), "-ac", "1",
            "-t", str(MAX_REF_SECONDS),
            tmp.name,
        ],
        check=True,
        capture_output=True,
    )
    return tmp.name


async def handle_connection(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    wyoming_info,
    tts,
    ref_wav: str,
    speed: float,
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

            def generate():
                wav, sr, _ = tts.infer(
                    ref_file=ref_wav,
                    ref_text="",  # auto-transcribe from the reference clip
                    gen_text=text,
                    speed=speed,
                )
                return np.asarray(wav, dtype=np.float32)

            samples = await loop.run_in_executor(None, generate)
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
    parser = argparse.ArgumentParser(description="Wyoming TTS server backed by F5-TTS")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=10202)
    parser.add_argument("--voice", required=True, help="Path to reference audio file for voice cloning")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    import torch
    from f5_tts.api import F5TTS
    from wyoming.info import Attribution, Info, TtsProgram, TtsVoice, TtsVoiceSpeaker

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    _LOGGER.info("Loading F5-TTS on %s…", device)
    tts = F5TTS(device=device)

    ref_wav = prepare_ref_audio(args.voice)

    _LOGGER.info("Warming up (this also transcribes the reference clip)…")
    tts.infer(ref_file=ref_wav, ref_text="", gen_text="Hello.", speed=args.speed)
    _LOGGER.info("Model ready")

    _attribution = Attribution(name="SWivid", url="https://github.com/SWivid/F5-TTS")
    wyoming_info = Info(
        tts=[
            TtsProgram(
                name="f5-tts",
                attribution=_attribution,
                installed=True,
                description="F5-TTS zero-shot voice cloning",
                version=None,
                voices=[
                    TtsVoice(
                        name="cloned",
                        attribution=_attribution,
                        installed=True,
                        description="Cloned voice from reference audio",
                        version=None,
                        languages=["en-us"],
                        speakers=[TtsVoiceSpeaker(name="cloned")],
                    )
                ],
            )
        ]
    )

    handler = lambda r, w: handle_connection(r, w, wyoming_info, tts, ref_wav, args.speed)
    server = await asyncio.start_server(handler, args.host, args.port)
    _LOGGER.info("Listening on %s:%d", args.host, args.port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
