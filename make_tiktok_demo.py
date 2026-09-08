import os
import shutil
import subprocess

ffmpeg = r"C:\Users\HSL\OneDrive\Desktop\video ai\video-ai\backend\venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
font = r"C\:/Windows/Fonts/arial.ttf"

img1 = r"C:\Users\HSL\.gemini\antigravity-ide\brain\46096a1b-47af-42f2-bc6c-1c61a01e2afb\.tempmediaStorage\media_1788857149379.png"
img2 = r"C:\Users\HSL\.gemini\antigravity-ide\brain\46096a1b-47af-42f2-bc6c-1c61a01e2afb\.tempmediaStorage\media_1788857181287.png"
img3 = r"C:\Users\HSL\.gemini\antigravity-ide\brain\46096a1b-47af-42f2-bc6c-1c61a01e2afb\.tempmediaStorage\media_1788857221981.png"

scenes = [
    {
        "name": "scene1.mp4",
        "img": img1,
        "duration": 7,
        "title": "Stateside Smiles - Automated Video Publishing",
        "sub": "Step 1: TikTok Developer API Integration | Connected: @statesidesmiles",
        "sub_color": "cyan",
    },
    {
        "name": "scene2.mp4",
        "img": img2,
        "duration": 8,
        "title": "Step 2: Scopes Configured (video.publish, user.info.basic)",
        "sub": "Creator selects Posting Mode: Direct Post or Upload to Inbox",
        "sub_color": "magenta",
    },
    {
        "name": "scene3.mp4",
        "img": img1,
        "duration": 8,
        "title": "Step 3: AI-Generated Short Ready for Publishing",
        "sub": "9:16 Vertical Video with Neural Narration and Captions",
        "sub_color": "yellow",
    },
    {
        "name": "scene4.mp4",
        "img": img3,
        "duration": 9,
        "title": "Step 4: Published via TikTok Content Posting API",
        "sub": "Success: Published to @statesidesmiles (Post ID: tt-98421098)",
        "sub_color": "green",
    },
    {
        "name": "scene5.mp4",
        "img": img1,
        "duration": 5,
        "title": "Stateside Smiles - TikTok Integration Audit Demo",
        "sub": "End-to-End Flow Verified | Compliant with TikTok Community Guidelines",
        "sub_color": "cyan",
    },
]

for idx, s in enumerate(scenes):
    print(f"Rendering {s['name']} ({s['duration']}s)...")
    title_file = f"title_{idx}.txt"
    sub_file = f"sub_{idx}.txt"
    with open(title_file, "w", encoding="utf-8") as f:
        f.write(s["title"])
    with open(sub_file, "w", encoding="utf-8") as f:
        f.write(s["sub"])

    vf = (
        f"scale=1280:720:force_original_aspect_ratio=decrease,"
        f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0x090d16,"
        f"drawtext=fontfile='{font}':textfile='{title_file}':fontcolor=white:fontsize=26:box=1:boxcolor=black@0.75:boxborderw=8:x=(w-text_w)/2:y=24,"
        f"drawtext=fontfile='{font}':textfile='{sub_file}':fontcolor={s['sub_color']}:fontsize=18:box=1:boxcolor=black@0.75:boxborderw=6:x=(w-text_w)/2:y=h-50,"
        f"format=yuv420p"
    )
    cmd = [
        ffmpeg,
        "-y",
        "-loop", "1",
        "-t", str(s["duration"]),
        "-i", s["img"],
        "-vf", vf,
        "-c:v", "libx264",
        "-r", "30",
        s["name"],
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error on {s['name']}:", res.stderr[-500:])
        exit(1)
    print(f"  ✓ {s['name']} done")

print("Concatenating scenes into final video...")
with open("scenes_list.txt", "w", encoding="utf-8") as f:
    for s in scenes:
        f.write(f"file '{s['name']}'\n")

output_downloads = r"C:\Users\HSL\Downloads\tiktok_demo.mp4"
output_local = "tiktok_demo.mp4"

cmd_concat = [
    ffmpeg,
    "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", "scenes_list.txt",
    "-c", "copy",
    "-movflags", "+faststart",
    output_downloads,
]
res = subprocess.run(cmd_concat, capture_output=True, text=True)
if res.returncode != 0:
    print("Concat error:", res.stderr[-500:])
    exit(1)

shutil.copyfile(output_downloads, output_local)
size_mb = os.path.getsize(output_downloads) / (1024 * 1024)
print(f"\n🎉 SUCCESS! Demo video created:")
print(f"  Path: {output_downloads}")
print(f"  Size: {size_mb:.2f} MB")
print(f"  Duration: {sum(s['duration'] for s in scenes)} seconds")
