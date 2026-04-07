# 🕯️ CreepyPasta Video Maker Bot

Automatically turns horror stories from [Creepypasta.com](https://www.creepypasta.com)
into narrated short-form videos ready to upload to TikTok, YouTube Shorts, or Instagram Reels.

No video editing. No manual writing. Just `python main.py`.

---

## How It Works

```
Creepypasta.com  →  Scraper  →  TTS Narrator  →  Video Assembler  →  MP4
```

1. **Scraper** — Pulls a story from horror categories on Creepypasta.com
2. **Narrator** — Converts it to speech (Google TTS free, or ElevenLabs premium)
3. **Video Maker** — Overlays text on a dark background + bakes in narration audio
4. **Output** — Vertical 1080×1920 MP4 ready for short-form platforms

---

## Requirements

- Python 3.10+
- `ffmpeg` installed on your system ([ffmpeg.org](https://ffmpeg.org/download.html))

---

## Installation

```bash
git clone https://github.com/yourname/CreepyPastaVideoBot.git
cd CreepyPastaVideoBot

python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

---

## Run

```bash
python main.py
```

On first run it creates `config.toml`. Edit it to your liking, then run again.

---

## Configuration (`config.toml`)

| Key | Default | Description |
|---|---|---|
| `tts_engine` | `"gtts"` | `"gtts"` (free) or `"elevenlabs"` (premium) |
| `tts_language` | `"en"` | Language code |
| `tts_slow` | `false` | Slower, more dramatic narration pace |
| `min_words` | `150` | Skip stories shorter than this |
| `max_words` | `800` | Trim stories longer than this |
| `words_per_chunk` | `10` | Words displayed at once (subtitle style) |
| `resolution` | `[1080, 1920]` | Output resolution (portrait for Reels/Shorts) |
| `bg_color` | `[10, 5, 15]` | Background RGB if no video supplied |
| `text_color` | `[220, 210, 200]` | Story text color |
| `title_color` | `[180, 30, 30]` | Title text color (blood red default) |

---

## Premium Voice (ElevenLabs)

For a much scarier, realistic voice:

1. Sign up at [elevenlabs.io](https://elevenlabs.io)
2. Get your API key
3. Set environment variable:
   ```bash
   export ELEVENLABS_API_KEY="your_key_here"
   ```
4. In `config.toml`, set `tts_engine = "elevenlabs"`

---

## Optional: Custom Background Video

Place a looping dark video (forest, fog, static, etc.) at:
```
assets/background.mp4
```

The bot will automatically darken and loop it behind the text.
Good sources: [Pexels](https://www.pexels.com/videos/) (free, no attribution required)

---

## Output

Videos are saved to `assets/output/`. Upload manually to:
- TikTok
- YouTube Shorts
- Instagram Reels

> **Note:** This bot does not auto-upload. You upload manually to avoid
> platform Terms of Service issues.

---

## Folder Structure

```
CreepyPastaVideoBot/
├── main.py                    # Entry point
├── config.toml                # Generated on first run
├── requirements.txt
├── scraper/
│   └── story_scraper.py       # Fetches stories from creepypasta.com
├── tts/
│   └── narrator.py            # Text-to-speech engine
├── video_creation/
│   └── video_maker.py         # Assembles the final video
├── utils/
│   ├── config.py              # Config loader
│   └── logger.py              # Console logging
└── assets/
    ├── audio/                 # Generated MP3 narrations
    ├── output/                # Final MP4 videos
    ├── fonts/                 # Optional: drop CreepsterCaps.ttf here
    ├── background.mp4         # Optional: your background footage
    └── used_stories.txt       # Tracks used stories to avoid repeats
```

---

## Disclaimer

- Stories on Creepypasta.com are community-submitted. Check individual story
  licenses before monetizing your videos.
- This bot does not upload content — you are responsible for what you post.
- Respect platform community guidelines.

---

## License

MIT
