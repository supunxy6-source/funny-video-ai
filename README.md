# Stateside Smiles 😄🎬

> **Fully Autonomous AI Entertainment Video Platform**  
> Discovers trending memes, jokes & viral content, writes comedy scripts, generates visuals, edits videos, and publishes to YouTube daily with **zero human intervention**.

---

## 🌟 Features & Pipeline Overview

```
Step 1: Discovery  ──►  Step 2: AI Curation  ──►  Step 3: Comedy Script
(Reddit/Memes/Trends)   (Ranking & Dedup)         (GPT-4o/Claude/Gemini)
                                                           │
Step 6: Video Editor ◄── Step 5: Voice (TTS) ◄── Step 4: Meme Visuals
(FFmpeg / MoviePy)       (ElevenLabs)             (FLUX / Memes / Stock)
        │
Step 7: Thumbnail    ──► Step 8: SEO          ──► Step 9: YouTube Upload  ──► Step 10: Notification
(FLUX + Pillow CTR)     (Titles & Tags)           (OAuth2 Resumable)           (Email & Slack)
```

1. **Content Discovery**: Scrapes Reddit (r/funny, r/memes, r/dankmemes), Google Trends, Imgflip, JokeAPI, and fun facts APIs.
2. **AI Curation**: Ranks content by virality potential, deduplicates, and selects the funniest topics.
3. **Comedy Script Writer**: LLM-powered comedy script generator for meme compilations and voiceover content.
4. **Meme Visual Planner**: Generates meme images with captions, downloads Reddit images, creates caption cards.
5. **Voice Narration**: ElevenLabs / Edge-TTS natural comedy narration with casual tone.
6. **Video Editor**: Assembles meme compilations with transitions, captions, and comedy pacing.
7. **Thumbnail Generator**: Creates eye-catching comedy thumbnails with text overlays & CTR scoring.
8. **SEO Optimizer**: Generates viral comedy titles, descriptions, tags, and hashtags.
9. **YouTube Uploader**: Automated OAuth2 resumable upload for both Shorts (9:16) and regular (16:9) videos.
10. **Notification**: Instant email & Slack alerts on success or failure.

---

## 🚀 Quick Start (Docker Compose)

### 1. Environment Setup
```bash
cp .env.example .env
# Open .env and add your API keys (LLM, ElevenLabs, Replicate, YouTube OAuth)
```

### 2. Launch Stack
```bash
docker compose up --build -d
```

### 3. Access Services
- **Admin Dashboard**: `http://localhost:3000`
- **FastAPI Documentation**: `http://localhost:8000/docs`
- **Flower (Celery Monitor)**: `http://localhost:5555`

---

## 🏗️ Architecture Stack

- **Backend**: FastAPI (Python 3.12), AsyncSQLAlchemy, Alembic
- **Tasks & Schedule**: Celery, Redis 7, Celery Beat
- **Database**: PostgreSQL 16
- **Frontend**: Next.js 15 (App Router), TypeScript, Tailwind CSS
- **AI & ML Models**:
  - LLM: OpenAI GPT-4o / Anthropic Claude / Google Gemini
  - Image: FLUX 1.1 Pro / SDXL (via Replicate)
  - TTS: ElevenLabs Multilingual v2 / Edge-TTS
  - Subtitles: OpenAI Whisper / faster-whisper
- **Content Sources**: Reddit JSON API, Google Trends, Imgflip, JokeAPI
- **DevOps**: Docker Compose, Kubernetes, GitHub Actions CI/CD, Nginx

---

## 🧪 Testing

```bash
# Run pytest test suite inside backend
cd backend
pytest -v
```

---

## 📄 License
MIT License.
