"""
Stateside Smiles — Voice Narrator

Generates natural narration audio using ElevenLabs TTS API.
Supports multiple voices, emotion adjustment, and scene-level generation.
"""

import asyncio
import logging
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.scene import Scene

logger = logging.getLogger(__name__)


class VoiceNarrator:
    """Generates narration audio using ElevenLabs, Edge-TTS, gTTS, and Windows Speech."""

    def __init__(self):
        self._client = None
        self.output_dir = Path(settings.generated_dir) / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.voice_id = settings.elevenlabs_voice_id
        self.model = settings.elevenlabs_model

    @property
    def client(self):
        if self._client is None and settings.elevenlabs_api_key:
            try:
                from elevenlabs.client import ElevenLabs
                self._client = ElevenLabs(api_key=settings.elevenlabs_api_key)
            except Exception as e:
                logger.warning(f"Could not initialize ElevenLabs client: {e}")
        return self._client

    def generate_scene_audio(
        self,
        text: str,
        scene_type: str = "narration",
        voice_id: str = None,
    ) -> Optional[str]:
        """
        Generate narration audio for a single scene using a tiered TTS engine fallback:
        1. ElevenLabs (if configured and active)
        2. Edge-TTS (Microsoft Neural Voice)
        3. gTTS (Google Translate TTS)
        4. Windows SAPI / System Speech
        """
        if not text or not text.strip():
            return None

        # Clean text for speech (remove markdown, stage directions in brackets, etc.)
        clean_text = self._clean_narration_text(text)
        if not clean_text:
            return None

        # 1. Try ElevenLabs TTS
        if settings.elevenlabs_api_key and settings.elevenlabs_api_key.strip():
            audio_path = self._generate_elevenlabs_audio(clean_text, scene_type, voice_id)
            if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
                return audio_path

        # 2. Try Edge-TTS (Microsoft Neural Voices)
        audio_path = self._generate_edge_tts_audio(clean_text)
        if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
            return audio_path

        # 3. Try Google TTS (gTTS)
        audio_path = self._generate_gtts_audio(clean_text)
        if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
            return audio_path

        # 4. Try Windows Speech Synthesizer / SAPI
        audio_path = self._generate_system_speech_audio(clean_text)
        if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
            return audio_path

        logger.error(f"❌ All TTS providers failed for text: {clean_text[:60]}...")
        return None

    def _clean_narration_text(self, text: str) -> str:
        """Strip brackets, JSON fragments, and formatting while preserving natural speech cadence."""
        import re
        # Remove bracketed directions like [Scene 1], [Visual: ...], (laughs), etc.
        cleaned = re.sub(r'\[.*?\]', '', text)
        cleaned = re.sub(r'\(.*?\)', '', cleaned)
        cleaned = re.sub(r'[*_#>`]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        # Normalize multiple ellipses down to a natural 3-dot pause
        cleaned = re.sub(r'\.{4,}', '...', cleaned)
        # Ensure clean spacing after punctuation
        cleaned = re.sub(r'([.,!?;:])(?=[A-Za-z])', r'\1 ', cleaned)
        return cleaned

    def _generate_elevenlabs_audio(
        self, text: str, scene_type: str, voice_id: str = None
    ) -> Optional[str]:
        """Generate audio using ElevenLabs API."""
        try:
            voice_id = voice_id or self.voice_id
            voice_settings = self._get_voice_settings(scene_type)

            logger.info(
                f"🎙️ [ElevenLabs] Generating audio for {scene_type} "
                f"({len(text.split())} words)..."
            )

            audio_generator = self.client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=self.model,
                voice_settings=voice_settings,
            )

            audio_bytes = b"".join(chunk for chunk in audio_generator)
            if not audio_bytes:
                return None

            file_name = f"narration_eleven_{uuid.uuid4().hex}.mp3"
            file_path = self.output_dir / file_name
            file_path.write_bytes(audio_bytes)
            logger.info(f"✅ ElevenLabs audio saved: {file_path} ({len(audio_bytes)} bytes)")
            return str(file_path)
        except Exception as e:
            logger.warning(f"⚠️ ElevenLabs TTS failed ({e}), falling back to next engine.")
            return None

    def _generate_edge_tts_audio(self, text: str) -> Optional[str]:
        """Generate high quality audio using Microsoft Edge Neural TTS with female voice."""
        try:
            import asyncio
            import edge_tts

            file_name = f"narration_edge_{uuid.uuid4().hex}.mp3"
            file_path = self.output_dir / file_name

            # Premium female news anchor voice (Jenny Neural)
            voice = getattr(settings, "edge_tts_voice", "en-US-JennyNeural") or "en-US-JennyNeural"

            async def _run_edge():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(str(file_path))

            # Run in event loop or thread
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create new loop in thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        pool.submit(lambda: asyncio.run(_run_edge())).result()
                else:
                    loop.run_until_complete(_run_edge())
            except RuntimeError:
                asyncio.run(_run_edge())

            if file_path.exists() and file_path.stat().st_size > 500:
                logger.info(f"✅ Edge-TTS audio saved: {file_path} ({file_path.stat().st_size} bytes, voice={voice})")
                return str(file_path)
            return None
        except Exception as e:
            logger.warning(f"⚠️ Edge-TTS failed ({e}), trying Google TTS...")
            return None

    def _generate_gtts_audio(self, text: str) -> Optional[str]:
        """Generate audio using Google Translate TTS (gTTS) with standard female voice."""
        try:
            from gtts import gTTS

            logger.info(f"🎙️ [Google TTS] Generating audio ({len(text.split())} words)...")
            file_name = f"narration_gtts_{uuid.uuid4().hex}.mp3"
            file_path = self.output_dir / file_name

            tts = gTTS(text=text, lang="en", tld="com", slow=False)
            tts.save(str(file_path))

            if file_path.exists() and file_path.stat().st_size > 500:
                logger.info(f"✅ Google TTS saved: {file_path} ({file_path.stat().st_size} bytes)")
                return str(file_path)
            return None
        except Exception as e:
            logger.warning(f"⚠️ gTTS failed: {e}")
            return None

    def _generate_system_speech_audio(self, text: str) -> Optional[str]:
        """Generate audio using Windows PowerShell System.Speech / SAPI with female voice."""
        import os
        import subprocess

        if os.name != "nt":
            return None

        try:
            logger.info("🎙️ [System Speech] Generating audio via Windows SAPI (Female voice)...")
            file_name = f"narration_sys_{uuid.uuid4().hex}.wav"
            file_path = self.output_dir / file_name

            # Escape text for powershell
            ps_text = text.replace('"', '""').replace("'", "''")
            ps_script = (
                f"Add-Type -AssemblyName System.Speech; "
                f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"try {{ $synth.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female) }} catch {{}}; "
                f"$synth.Rate = 0; "
                f"$synth.SetOutputToWaveFile('{file_path}'); "
                f"$synth.Speak('{ps_text}'); "
                f"$synth.Dispose()"
            )

            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                timeout=30,
                check=True,
            )

            if file_path.exists() and file_path.stat().st_size > 1000:
                logger.info(f"✅ System speech audio saved: {file_path}")
                return str(file_path)
            return None
        except Exception as e:
            logger.warning(f"⚠️ System Speech failed: {e}")
            return None

    def _get_voice_settings(self, scene_type: str) -> dict:
        """Get voice settings tuned for the scene type and content mode."""
        mode = getattr(settings, "content_mode", "entertainment")
        if mode == "entertainment":
            # Expressive, dynamic comedy delivery (allows laughter and sarcastic inflection)
            base = {
                "stability": 0.45,
                "similarity_boost": 0.80,
                "style": 0.45,
                "use_speaker_boost": True,
            }
            overrides = {
                # General comedy types
                "hook": {"stability": 0.35, "style": 0.55},
                "comedy_body": {"stability": 0.42, "style": 0.45},
                "punchline": {"stability": 0.38, "style": 0.50},
                "loop_bridge": {"stability": 0.40, "style": 0.50},
                "intro": {"stability": 0.45, "style": 0.40},
                "cta": {"stability": 0.40, "style": 0.45},
                # Storytelling narrative types
                "story_hook": {"stability": 0.38, "style": 0.52},
                "story_setup": {"stability": 0.46, "style": 0.40},
                "story_escalation": {"stability": 0.40, "style": 0.48},
                "story_payoff": {"stability": 0.36, "style": 0.52},
                "story_payoff_loop": {"stability": 0.36, "style": 0.52},
                "story_transition": {"stability": 0.44, "style": 0.42},
            }
        else:
            base = {
                "stability": 0.71,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
            }
            overrides = {
                "hook": {"stability": 0.50, "style": 0.50},
                "intro": {"stability": 0.70, "style": 0.1},
                "facts": {"stability": 0.80, "style": 0.0},
                "context": {"stability": 0.75, "style": 0.1},
                "impact": {"stability": 0.60, "style": 0.40},
                "conclusion": {"stability": 0.72, "style": 0.15},
                "cta": {"stability": 0.65, "style": 0.25},
            }

        if scene_type in overrides:
            base.update(overrides[scene_type])

        return base

    def get_audio_duration(self, file_path: str, fallback_word_count: int = 0) -> float:
        """Get the duration of an audio file in seconds using ffprobe, or estimate from file/words."""
        import subprocess

        try:
            result = subprocess.run(
                [
                    "ffprobe", "-i", file_path,
                    "-show_entries", "format=duration",
                    "-v", "quiet", "-of", "csv=p=0",
                ],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception:
            pass

        # Python MP3/WAV file header estimation fallback
        try:
            if file_path.endswith(".wav"):
                import wave
                with wave.open(file_path, "r") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    return frames / float(rate)
            elif file_path.endswith(".mp3"):
                # Approximate MP3 duration from file size (assuming ~128kbps / 16KB/s)
                size_bytes = os.path.getsize(file_path)
                return max(2.5, size_bytes / 16000.0)
        except Exception:
            pass

        if fallback_word_count > 0:
            return max(3.0, fallback_word_count / 2.5)

        return 5.0


async def generate_narration(script_id: int) -> list[str]:
    """
    Main narration entry point called by Celery task.
    Generates audio for all scenes in a script.

    Returns list of generated audio file paths.
    """
    import asyncio

    narrator = VoiceNarrator()
    audio_paths = []

    async with async_session_factory() as db:
        result = await db.execute(
            select(Scene)
            .where(Scene.script_id == script_id)
            .order_by(Scene.order)
        )
        scenes = result.scalars().all()

        for scene in scenes:
            if not scene.text or not scene.text.strip():
                continue

            # Run the sync ElevenLabs call in a thread to avoid blocking the event loop
            audio_path = await asyncio.to_thread(
                narrator.generate_scene_audio,
                text=scene.text,
                scene_type=scene.scene_type,
            )

            if audio_path:
                # Update scene with audio path and duration
                scene.audio_url = audio_path
                duration = narrator.get_audio_duration(audio_path)
                if duration > 0:
                    scene.duration = duration
                audio_paths.append(audio_path)
            else:
                logger.warning(f"⚠️ Failed to generate audio for scene {scene.id}")

        await db.commit()
        logger.info(
            f"🎙️ Generated {len(audio_paths)}/{len(scenes)} scene narrations "
            f"for script {script_id}"
        )

    return audio_paths
