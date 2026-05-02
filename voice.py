from __future__ import annotations

import os
import threading

from dotenv import load_dotenv
from elevenlabs import ElevenLabs
from elevenlabs.play import play


_speech_gate = threading.Semaphore(1)

load_dotenv()


def speak(text: str) -> None:
    """Synthesize and play speech, falling back to console output on failure."""
    with _speech_gate:
        try:
            api_key = os.getenv("ELEVENLABS_API_KEY")
            voice_id = os.getenv("ELEVENLABS_VOICE_ID")
            if not api_key or not voice_id:
                raise RuntimeError("missing ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID")

            client = ElevenLabs(api_key=api_key)
            audio = client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
            )
            play(audio)
        except Exception:
            print(f"[voice] FALLBACK: {text}")
