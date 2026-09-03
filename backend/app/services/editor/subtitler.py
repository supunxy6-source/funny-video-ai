"""
Stateside Smiles — Subtitle Generator

Uses faster-whisper to transcribe narration audio and generate
SRT subtitle files with word-level timestamps.
"""

import logging
import uuid
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class SubtitleGenerator:
    """Generates subtitles from audio using faster-whisper."""

    def __init__(self):
        self.model_size = settings.whisper_model
        self.device = settings.whisper_device
        self.output_dir = Path(settings.generated_dir) / "subtitles"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._model = None

    @property
    def model(self):
        """Lazy-load the Whisper model."""
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type="int8" if self.device == "cpu" else "float16",
            )
        return self._model

    def transcribe_to_srt(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio and generate an SRT subtitle file.

        Returns the SRT file path, or None on failure.
        """
        try:
            logger.info(f"📝 Transcribing audio: {audio_path}")
            # Try faster-whisper model
            segments, info = self.model.transcribe(
                audio_path,
                beam_size=5,
                word_timestamps=True,
                vad_filter=True,
            )

            srt_lines = []
            index = 1

            for segment in segments:
                start = self._format_timestamp(segment.start)
                end = self._format_timestamp(segment.end)
                text = segment.text.strip()

                if text:
                    srt_lines.append(f"{index}")
                    srt_lines.append(f"{start} --> {end}")
                    srt_lines.append(text)
                    srt_lines.append("")
                    index += 1

            if not srt_lines:
                logger.warning("No subtitle segments generated")
                return None

            # Save SRT file
            file_name = f"subtitles_{uuid.uuid4().hex}.srt"
            file_path = self.output_dir / file_name
            file_path.write_text("\n".join(srt_lines), encoding="utf-8")

            logger.info(f"✅ SRT saved: {file_path} ({index - 1} segments)")
            return str(file_path)

        except Exception as e:
            logger.warning(f"Whisper transcription unavailable: {e}")
            return None

    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_subtitles(audio_path: str) -> Optional[str]:
    """
    Entry point for subtitle generation.
    Transcribes audio and returns the SRT file path.
    """
    generator = SubtitleGenerator()
    return generator.transcribe_to_srt(audio_path)
