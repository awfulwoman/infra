import threading
import asyncio
import json
import logging
import os
import re
import time
import wave
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from functools import partial

import torch
from pocket_tts import TTSModel, export_model_state
from stream2sentence import generate_sentences
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver as Observer
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.info import Info, TtsProgram, TtsVoice
from wyoming.server import AsyncEventHandler, AsyncServer
from wyoming.tts import (Synthesize, SynthesizeStart, SynthesizeStop,
                         SynthesizeChunk)
from wyoming.event import Event

# Optimize for inference
torch.set_grad_enabled(False)

def load_config():
    base_data = Path(os.getenv("DATA_DIR", "/share/pocket_tts_streaming"))
    opts_path = Path("/data/options.json")

    config = {
        "hf_token": os.getenv("HF_TOKEN", ""),
        "port": int(os.getenv("WYOMING_PORT", 10222)),
        "voice": os.getenv("DEFAULT_VOICE", "alba"),
        "log_level": os.getenv("LOG_LEVEL", "info").upper(),
        "data_dir": base_data,
        "models_dir": base_data / "models",
        "voices_dir": base_data / "voices",
        "s2s_quick_yield": True,
        "s2s_min_sentence_len": 15,
        "s2s_min_first_frag": 10,
        "enable_phonetic_dict": True,
        "dict_path": base_data / "pronunciations.json",
        "pytorch_threads": 4,
        "speaker_tail_padding": 0.3
    }

    if opts_path.exists():
        try:
            opts = json.loads(opts_path.read_text())
            for k in ["hf_token", "port", "voice", "log_level"]:
                if k in opts: config[k] = opts[k]

            if "s2s_quick_yield_single_sentence_fragment" in opts:
                config["s2s_quick_yield"] = bool(opts["s2s_quick_yield_single_sentence_fragment"])
            if "s2s_minimum_sentence_length" in opts:
                config["s2s_min_sentence_len"] = int(opts["s2s_minimum_sentence_length"])
            if "s2s_minimum_first_fragment_length" in opts:
                config["s2s_min_first_frag"] = int(opts["s2s_minimum_first_fragment_length"])
            if "enable_phonetic_dict" in opts:
                config["enable_phonetic_dict"] = bool(opts["enable_phonetic_dict"])
            if "pytorch_threads" in opts:
                config["pytorch_threads"] = int(opts["pytorch_threads"])
            if "speaker_tail_padding" in opts:
                config["speaker_tail_padding"] = float(opts["speaker_tail_padding"])

        except Exception as e:
            print(f"CRITICAL: Failed to parse options.json: {e}")

    return config

CFG = load_config()

# Configure Logging
LOG_LEVEL = getattr(logging, CFG["log_level"].upper(), logging.INFO)
logging.basicConfig(level=LOG_LEVEL, format='%(levelname)s:%(name)s: %(message)s')
_LOGGER = logging.getLogger("PocketTTSStreaming")
_LOGGER.setLevel(LOG_LEVEL)

# Environment Setup
os.environ["HF_HOME"] = str(CFG["models_dir"])
if CFG["hf_token"]:
    os.environ["HF_TOKEN"] = CFG["hf_token"]

CFG["voices_dir"].mkdir(parents=True, exist_ok=True)
CFG["models_dir"].mkdir(parents=True, exist_ok=True)

# Apply the configured PyTorch threads (Ideal for your CPU-only setup)
torch.set_num_threads(CFG["pytorch_threads"])
_LOGGER.debug(f"PyTorch threads set to: {CFG['pytorch_threads']}")

# Load Pronunciation Dictionary
PRONUNCIATION_DICT = {}
if CFG["enable_phonetic_dict"]:
    if CFG["dict_path"].exists():
        try:
            PRONUNCIATION_DICT = json.loads(CFG["dict_path"].read_text())
            _LOGGER.info(f"Loaded {len(PRONUNCIATION_DICT)} phonetic overrides.")
        except Exception as e:
            _LOGGER.error(f"Failed to load pronunciations.json: {e}")
    else:
        default_dict = {
            "HA": "Home Assistant",
            "HAOS": "Home Assistant O S",
            "Siobhan": "Shiv-awn"
        }
        try:
            CFG["dict_path"].write_text(json.dumps(default_dict, indent=4))
        except Exception as e:
            _LOGGER.error(f"Could not create default pronunciations.json: {e}")

def normalize_wav(wav_path):
    """Safely normalizes a 16-bit PCM wav file to 95% peak volume."""
    try:
        with wave.open(str(wav_path), 'rb') as wav:
            params = wav.getparams()
            frames = wav.readframes(params.nframes)

        if params.sampwidth != 2:
            _LOGGER.warning(f"Skipping normalization for {wav_path.name}: not 16-bit PCM.")
            return

        audio = np.frombuffer(frames, dtype=np.int16)
        peak = np.max(np.abs(audio))
        if peak == 0: return

        multiplier = 31128.0 / peak
        if 0.95 < multiplier < 1.05:
            _LOGGER.debug(f"{wav_path.name} is already leveled. Skipping.")
            return

        audio_norm = np.clip(audio * multiplier, -32768, 32767).astype(np.int16)
        with wave.open(str(wav_path), 'wb') as wav:
            wav.setparams(params)
            wav.writeframes(audio_norm.tobytes())

        _LOGGER.info(f"Normalized {wav_path.name} (Volume scaled by {multiplier:.2f}x)")
    except Exception as e:
        _LOGGER.error(f"Failed to normalize {wav_path.name}: {e}")

class VoiceFolderHandler(FileSystemEventHandler):
    def __init__(self, model, voice_states, loop):
        self.model, self.voice_states, self.loop = model, voice_states, loop

    def _check_path(self, path_str):
        path = Path(path_str)
        if path.suffix == ".wav" and not path.name.endswith(".done"):
            _LOGGER.info(f"New voice source detected: {path.name}")
            asyncio.run_coroutine_threadsafe(self._handle_new_wav(path), self.loop)
        elif path.suffix == ".safetensors":
            _LOGGER.info(f"New voice state detected: {path.name}")
            asyncio.run_coroutine_threadsafe(self._handle_new_state(path), self.loop)

    def on_created(self, event):
        if not event.is_directory: self._check_path(event.src_path)

    def on_moved(self, event):
        if not event.is_directory: self._check_path(event.dest_path)

    async def _wait_for_stable_file(self, path, timeout=10):
        last_size = -1
        for _ in range(timeout * 2):
            try:
                if not path.exists(): return False
                current_size = path.stat().st_size
                if current_size == last_size and current_size > 0: return True
                last_size = current_size
            except Exception: pass
            await asyncio.sleep(0.5)
        return False

    async def _handle_new_wav(self, path):
        if await self._wait_for_stable_file(path):
            self.loop.run_in_executor(None, self._process_wav, path)

    async def _handle_new_state(self, path):
        if await self._wait_for_stable_file(path):
            self.loop.run_in_executor(None, self._load_voice, path)

    def _process_wav(self, path):
        try:
            _LOGGER.info(f"Cloning voice: {path.stem}...")
            start_time = time.time()
            normalize_wav(path)
            state = self.model.get_state_for_audio_prompt(str(path))
            safe_path = path.with_suffix(".safetensors")
            export_model_state(state, str(safe_path))
            path.rename(path.with_suffix(".wav.done"))
            _LOGGER.info(f"Successfully cloned {path.stem} in {time.time()-start_time:.2f}s")
        except Exception as e:
            _LOGGER.error(f"Failed to clone {path.name}: {e}", exc_info=(LOG_LEVEL == logging.DEBUG))

    def _load_voice(self, path):
        if path.stem not in self.voice_states:
            try:
                _LOGGER.info(f"Loading custom voice state: {path.stem}")
                self.voice_states[path.stem] = self.model.get_state_for_audio_prompt(str(path))
            except Exception as e:
                _LOGGER.error(f"Failed to load {path.name}: {e}")

class PocketTTSHandler(AsyncEventHandler):
    def __init__(self, model, voice_states, executor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model, self.voice_states, self.executor = model, voice_states, executor
        self.text_queue = asyncio.Queue()
        self.is_streaming = False

    async def run(self) -> None:
        try:
            await super().run()
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, asyncio.IncompleteReadError):
            _LOGGER.debug("Client disconnected normally after receiving audio.")
        except Exception as e:
            _LOGGER.error(f"Unexpected connection error: {e}", exc_info=True)

    async def handle_event(self, event) -> bool:
        if event.type == "describe":
            await self.write_event(self._get_info().event())
            return True

        if SynthesizeStart.is_type(event.type):
            synth = SynthesizeStart.from_event(event)
            self.is_streaming = True
            asyncio.create_task(self.start_synthesis(synth.voice))
            return True

        if Synthesize.is_type(event.type):
            if self.is_streaming: return True
            synth = Synthesize.from_event(event)
            asyncio.create_task(self.start_synthesis(synth.voice, synth.text))
            return True

        if SynthesizeChunk.is_type(event.type):
            synth = SynthesizeChunk.from_event(event)
            await self.text_queue.put(synth.text)
            return True

        if SynthesizeStop.is_type(event.type):
            await self.text_queue.put(None)
            return True

        return True

    async def start_synthesis(self, voice_data, initial_text=None):
        voice_name = getattr(voice_data, "name", CFG["voice"]) if voice_data else CFG["voice"]
        v_state = self.voice_states.get(voice_name, self.voice_states.get(CFG["voice"]))

        await self.write_event(AudioStart(rate=24000, width=2, channels=1).event())

        if initial_text:
            await self.text_queue.put(initial_text)
            await self.text_queue.put(None)

        audio_queue = asyncio.Queue(maxsize=15)
        loop = asyncio.get_running_loop()
        abort_event = threading.Event()

        def text_iterator():
            while True:
                future = asyncio.run_coroutine_threadsafe(self.text_queue.get(), loop)
                val = future.result()
                if val is None or abort_event.is_set(): break
                yield val

        loop.run_in_executor(self.executor, self._run_generator, text_iterator, voice_name, v_state, audio_queue, loop, abort_event)

        try:
            while True:
                chunk = await audio_queue.get()
                if chunk is None: break
                await self.write_event(AudioChunk(audio=chunk, rate=24000, width=2, channels=1).event())
                await self.writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            abort_event.set()
            await self.text_queue.put(None)
            return
        except Exception as e:
            _LOGGER.error(f"Stream Error: {e}", exc_info=True)
            abort_event.set()
            await self.text_queue.put(None)
        finally:
            abort_event.set()
            try:
                if not self.writer.is_closing():
                    if CFG["speaker_tail_padding"] > 0:
                        padding_bytes = int(24000 * 2 * CFG["speaker_tail_padding"])
                        if padding_bytes % 2 != 0: padding_bytes += 1
                        silence = bytes(padding_bytes)
                        await self.write_event(AudioChunk(audio=silence, rate=24000, width=2, channels=1).event())
                        _LOGGER.debug(f"Added {CFG['speaker_tail_padding']}s of silence padding.")

                    await self.write_event(AudioStop().event())
                if not self.writer.is_closing():
                    await self.write_event(Event(type="synthesize-stopped", data={}))
                    await self.write_event(SynthesizeStop().event())
                    await self.writer.drain()
                    self.writer.close()
            except Exception:
                pass

    def _get_info(self):
        voices = [TtsVoice(name=n, languages=["en"], installed=True, version="1.0",
                           attribution={"name": "Kyutai", "url": "https://kyutai.org"},
                           description=f"Pocket TTS: {n}") for n in self.voice_states]
        return Info(tts=[TtsProgram(name="Pocket TTS Streaming", installed=True, voices=voices,
                                    version="1.0.0", supports_synthesize_streaming=True,
                                    attribution={"name": "Kyutai", "url": "https://kyutai.org"},
                                    description="Ultra-low latency streaming TTS")])

    def _run_generator(self, text_iterator, base_voice_name, initial_v_state, audio_queue, loop, abort_event):
        tag_pattern = re.compile(r'\[([^\]]+)\]')
        current_v_state = initial_v_state
        current_voice_name = base_voice_name

        try:
            generator = generate_sentences(
                text_iterator(),
                quick_yield_single_sentence_fragment=CFG["s2s_quick_yield"],
                minimum_sentence_length=CFG["s2s_min_sentence_len"],
                minimum_first_fragment_length=CFG["s2s_min_first_frag"],
                force_first_fragment_after_words=7,
                cleanup_text_links=True,
                cleanup_text_emojis=True
            )

            for sentence in generator:
                if abort_event.is_set(): break

                # Extract tags to determine the voice for this sentence
                tags = tag_pattern.findall(sentence)
                if tags:
                    # Grab the first tag found in the sentence to set the emotion
                    tag = tags[0].strip().lower()
                    emotion_voice = f"{base_voice_name}_{tag}"

                    if tag in ["normal", "default", "reset"]:
                        current_v_state = initial_v_state
                        current_voice_name = base_voice_name
                    elif emotion_voice in self.voice_states:
                        current_v_state = self.voice_states[emotion_voice]
                        current_voice_name = emotion_voice
                    elif tag in self.voice_states:
                        current_v_state = self.voice_states[tag]
                        current_voice_name = tag

                # Strip ALL tags from the text so they aren't spoken
                clean_sentence = tag_pattern.sub('', sentence).strip()
                if not clean_sentence: continue

                # Apply Phonetic Override
                if CFG["enable_phonetic_dict"] and PRONUNCIATION_DICT:
                    for target_word, phonetic_spelling in PRONUNCIATION_DICT.items():
                        clean_sentence = re.sub(
                            rf'\b{re.escape(target_word)}\b',
                            phonetic_spelling,
                            clean_sentence,
                            flags=re.IGNORECASE
                        )

                _LOGGER.debug(f"Phraser yielded clean sentence: '{clean_sentence}' using voice: {current_voice_name}")

                # Generate the audio straem..
                for chunk in self.model.generate_audio_stream(current_v_state, clean_sentence):
                    if abort_event.is_set(): break
                    audio_data = (chunk.clamp(-1.0, 1.0) * 32767).to(torch.int16).cpu().numpy().tobytes()
                    future = asyncio.run_coroutine_threadsafe(audio_queue.put(audio_data), loop)
                    future.result()

        except Exception as e:
            _LOGGER.error(f"Generator Error: {e}")
        finally:
            if not abort_event.is_set():
                asyncio.run_coroutine_threadsafe(audio_queue.put(None), loop)

async def main():
    _LOGGER.info(f"Starting Pocket TTS Streaming on port {CFG['port']}...")

    try:
        _LOGGER.info("Loading Pocket TTS model weights...")
        model = TTSModel.load_model()

        # Process pending .wav files on startup
        for wav_path in CFG["voices_dir"].glob("*.wav"):
            if not wav_path.name.endswith(".done"):
                _LOGGER.info(f"Found unprocessed wav on startup: {wav_path.name}")
                try:
                    normalize_wav(wav_path)
                    state = model.get_state_for_audio_prompt(str(wav_path))
                    safe_path = wav_path.with_suffix(".safetensors")
                    export_model_state(state, str(safe_path))
                    wav_path.rename(wav_path.with_suffix(".wav.done"))
                except Exception as e:
                    _LOGGER.error(f"Failed to process {wav_path.name} on startup: {e}")

        # Load Initial Base Voices and Safetensors
        builtin_voices = [
            "alba", "marius", "javert", "jean",
            "fantine", "cosette", "eponine", "azelma"
        ]
        voice_states = {v: model.get_state_for_audio_prompt(v) for v in builtin_voices}

        for p in CFG["voices_dir"].glob("*.safetensors"):
            voice_states[p.stem] = model.get_state_for_audio_prompt(str(p))

        # Group voices for clean logging
        all_names = set(voice_states.keys())
        voice_tree = {}
        for name in sorted(all_names):
            if '_' in name and name.split('_', 1)[0] in all_names:
                base, emote = name.split('_', 1)
                voice_tree.setdefault(base, []).append(emote)
            else:
                voice_tree.setdefault(name, [])

        log_entries = [f"{b} [{', '.join(e)}]" if e else b for b, e in voice_tree.items()]
        _LOGGER.info(f"Ready! Loaded {len(voice_states)} total states: {' | '.join(log_entries)}")

        # Start threads and handlers
        executor, loop = ThreadPoolExecutor(max_workers=4), asyncio.get_running_loop()
        observer = Observer()
        observer.schedule(VoiceFolderHandler(model, voice_states, loop), str(CFG["voices_dir"]))
        observer.start()

        server = AsyncServer.from_uri(f"tcp://0.0.0.0:{CFG['port']}")
        await server.run(partial(PocketTTSHandler, model, voice_states, executor))

    finally:
        _LOGGER.warning("Service shutting down...")
        observer.stop()
        observer.join()
        executor.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
