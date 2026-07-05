#!/usr/bin/env python3
"""Wyoming TTS server backed by Kokoro-82M."""

import argparse
import asyncio
import logging

import numpy as np

_LOGGER = logging.getLogger(__name__)

SAMPLE_RATE = 24000
SAMPLE_WIDTH = 2  # 16-bit PCM
CHANNELS = 1
CHUNK_FRAMES = 4096

# (wyoming language tag, human description, pipeline lang_code)
VOICES = {
    "af_heart":    ("en-us", "American English - Heart (female)",     "a"),
    "af_bella":    ("en-us", "American English - Bella (female)",     "a"),
    "af_sarah":    ("en-us", "American English - Sarah (female)",     "a"),
    "af_sky":      ("en-us", "American English - Sky (female)",       "a"),
    "am_adam":     ("en-us", "American English - Adam (male)",        "a"),
    "am_michael":  ("en-us", "American English - Michael (male)",     "a"),
    "bf_emma":     ("en-gb", "British English - Emma (female)",       "b"),
    "bf_isabella": ("en-gb", "British English - Isabella (female)",   "b"),
    "bm_george":   ("en-gb", "British English - George (male)",       "b"),
    "bm_lewis":    ("en-gb", "British English - Lewis (male)",        "b"),
}


async def handle_connection(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    wyoming_info,
    pipelines: dict,
    default_voice: str,
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
            voice = (synthesize.voice.name if synthesize.voice else None) or default_voice
            if voice not in VOICES:
                voice = default_voice

            if not text.strip():
                await async_write_event(AudioStop().event(), writer)
                continue

            _LOGGER.info("Synthesizing [%s]: %.60s…", voice, text)

            lang_code = VOICES[voice][2]
            pipeline = pipelines[lang_code]

            loop = asyncio.get_event_loop()

            def generate():
                segments = []
                for _, _, audio in pipeline(text, voice=voice, speed=speed):
                    segments.append(audio)
                return np.concatenate(segments) if segments else np.array([], dtype=np.float32)

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
    parser = argparse.ArgumentParser(description="Wyoming TTS server backed by Kokoro-82M")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=10201)
    parser.add_argument("--voice", default="af_heart", choices=list(VOICES))
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from kokoro import KPipeline
    from wyoming.info import Attribution, Info, TtsProgram, TtsVoice, TtsVoiceSpeaker

    _attribution = Attribution(name="hexgrad", url="https://github.com/hexgrad/kokoro")

    _LOGGER.info("Loading Kokoro pipelines…")
    pipelines = {
        "a": KPipeline(lang_code="a"),
        "b": KPipeline(lang_code="b"),
    }

    _LOGGER.info("Warming up…")
    list(pipelines["a"]("Hello.", voice="af_heart", speed=args.speed))
    _LOGGER.info("Model ready, default voice: %s", args.voice)

    wyoming_info = Info(
        tts=[
            TtsProgram(
                name="kokoro",
                attribution=_attribution,
                installed=True,
                description="Kokoro-82M TTS",
                version=None,
                voices=[
                    TtsVoice(
                        name=name,
                        attribution=_attribution,
                        installed=True,
                        description=desc,
                        version=None,
                        languages=[lang],
                        speakers=[TtsVoiceSpeaker(name=name)],
                    )
                    for name, (lang, desc, _) in VOICES.items()
                ],
            )
        ]
    )

    handler = lambda r, w: handle_connection(
        r, w, wyoming_info, pipelines, args.voice, args.speed
    )
    server = await asyncio.start_server(handler, args.host, args.port)
    _LOGGER.info("Listening on %s:%d", args.host, args.port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
