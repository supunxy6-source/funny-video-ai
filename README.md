# AI News Studio 🎬📰

> **Fully Autonomous AI News Video Platform**  
> Discovers, researches, writes, generates, edits, and publishes news videos to YouTube daily with **zero human intervention**.

---

## 🌟 Features & Pipeline Overview

```
Step 1: Discovery  ──►  Step 2: AI Analysis  ──►  Step 3: Script Writer
(RSS & Google News)     (TF-IDF & Verification)   (GPT-4o/Claude/Gemini)
                                                             │
Step 6: Video Editor ◄── Step 5: Voice (TTS) ◄── Step 4: Visual Planner
(FFmpeg / MoviePy)       (ElevenLabs)             (FLUX / SDXL / Charts)
        │
Step 7: Thumbnail    ──► Step 8: SEO          ──► Step 9: YouTube Upload  ──► Step 10: Notification
(FLUX + Pillow CTR)     (Titles & Chapters)       (OAuth2 Resumable)           (Email & Slack)
```

1. **News Discovery**: Scrapes 15+ trusted sources (Reuters, AP, BBC, CNN, Al Jazeera, TechCrunch, Bloomberg, NASA, WHO, Google News).
2. **AI Verification**: Clusters duplicate stories (TF-IDF + Agglomerative Clustering) and enforces **3+ independent trusted sources**.
3. **Script Writer**: LLM-powered script generator (8-12 minutes / 1200-1800 words) with source citations.
4. **Visual Planner**: Generates prompts for FLUX / SDXL AI images, charts, and maps.
5. **Voice Narration**: ElevenLabs natural TTS with emotion adjustment per scene type.
6. **Video Editor**: Assembles scenes, intro/outro, lower thirds, and hardburned subtitles via Whisper.
7. **Thumbnail Generator**: Creates 3-5 thumbnail variants with Pillow text overlays & CTR scoring.
8. **SEO Optimizer**: Generates 100-char titles, 5000-char descriptions, tags, and chapter timestamps.
9. **YouTube Uploader**: Fully automated OAuth2 resumable upload, thumbnail setting, and playlist assignment.
10. **Admin Notification**: Instant email & Slack alerts on success or failure.

---

## 🚀 Quick Start (Docker Compose)

### 1. Environment Setup
```bash
cp .env.example .env
# Open .env and add your API keys (OpenAI, ElevenLabs, Replicate, YouTube OAuth)
```

### 2. Launch Stack
```bash
docker compose up --build -d
```

### 3. Access Services
- **Admin Dashboard**: `http://localhost:3000` (Login: `admin@ainewsstudio.com` / `changeme`)
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
  - TTS: ElevenLabs Multilingual v2
  - Subtitles: OpenAI Whisper / faster-whisper
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
