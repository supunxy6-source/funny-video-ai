import asyncio
import os
import subprocess
import sys

# Enable UTF-8 encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

output_dir = "backend/test_output_images"
os.makedirs(output_dir, exist_ok=True)

test_text = "This is a breaking news update for YouTube Shorts. Verified reports confirm the voice has been updated to a professional female news anchor."

# 1. Test Edge-TTS (AriaNeural)
async def test_edge_tts():
    try:
        import edge_tts
        voice = "en-US-JennyNeural"
        file_path = os.path.join(output_dir, "edge_female_voice.mp3")
        comm = edge_tts.Communicate(test_text, voice)
        await comm.save(file_path)
        print(f"✅ Edge-TTS Female voice generated: {file_path} ({os.path.getsize(file_path)} bytes)")
    except Exception as e:
        print(f"⚠️ Edge-TTS failed: {e}")

# 2. Test Windows Speech SAPI (Female hint)
def test_sapi():
    try:
        file_path = os.path.join(output_dir, "sapi_female_voice.wav")
        ps_text = test_text.replace('"', '""').replace("'", "''")
        ps_script = (
            f"Add-Type -AssemblyName System.Speech; "
            f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"try {{ $synth.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female) }} catch {{}}; "
            f"$synth.Rate = 0; "
            f"$synth.SetOutputToWaveFile('{file_path}'); "
            f"$synth.Speak('{ps_text}'); "
            f"$synth.Dispose()"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, check=True)
        if os.path.exists(file_path):
            print(f"✅ Windows SAPI Female voice generated: {file_path} ({os.path.getsize(file_path)} bytes)")
    except Exception as e:
        print(f"⚠️ SAPI failed: {e}")

# 3. Test gTTS
def test_gtts():
    try:
        from gtts import gTTS
        file_path = os.path.join(output_dir, "gtts_female_voice.mp3")
        tts = gTTS(text=test_text, lang="en", tld="com", slow=False)
        tts.save(file_path)
        print(f"✅ gTTS Female voice generated: {file_path} ({os.path.getsize(file_path)} bytes)")
    except Exception as e:
        print(f"⚠️ gTTS failed: {e}")

async def main():
    print("=== TESTING FEMALE AUDIO GENERATION ===")
    await test_edge_tts()
    test_sapi()
    test_gtts()
    print("=== TTS TESTS COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
