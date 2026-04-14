# vid2text

Turn short videos (for example Instagram reels) into:

- transcript files
- individual blog-style notes
- one categorized table of contents (`blog.md`)

This project runs fully local for AI processing:

- Whisper for speech-to-text
- Ollama for title generation, blog writing, and category grouping

## What It Does

Given one or more URLs, the pipeline in `main.py` does this for each URL:

1. Downloads audio from the video URL.
2. Transcribes audio with Whisper.
3. Generates a clean title using Ollama.
4. Saves transcript as `output/<generated-title-slug>.txt`.
5. Generates a blog note and saves it as `output/<generated-title-slug>.md`.

After all URLs are processed:

6. Generates `output/blog.md` as a categorized table of contents.
7. `blog.md` only contains category sections and links to the individual `.md` files.

Note: downloaded media is temporary and deleted automatically after transcription.

## Project Structure

```
.
├── main.py
├── requirements.txt
├── output/
│   ├── blog.md
│   ├── <title-1>.txt
│   ├── <title-1>.md
│   ├── <title-2>.txt
│   └── <title-2>.md
└── README.md
```

## Requirements

- Python 3.10+
- `ffmpeg` installed on system
- Ollama installed and running locally
- An available Ollama model (default used here: `gemma4`)

Install system dependency:

```bash
sudo apt install ffmpeg
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Ollama Setup

Make sure Ollama service is running and model exists:

```bash
ollama list
ollama run gemma4
```

If needed, start server:

```bash
ollama serve
```

## Usage

Basic:

```bash
python main.py <url1> <url2> <url3>
```

Examples:

```bash
python main.py \
	"https://www.instagram.com/reel/DUEPQsyD8B1/?igsh=b3dmY3k4a2k4OHR2" \
	"https://www.instagram.com/reel/DWhc4UJj1Fe/?igsh=MW9rMzJmNWhma3E2Yg==" \
	"https://www.instagram.com/reel/DXEsl6BkZ8Z/?igsh=M3BsemdlN3hhMDdu"
```

Optional flags:

```bash
python main.py -m small <url1>
python main.py --ollama-model gemma4 <url1>
```

- `-m, --whisper-model`: `tiny | base | small | medium | large`
- `--ollama-model`: local Ollama model name

## Outputs

- `output/*.txt`: raw transcripts
- `output/*.md`: blog entries per video
- `output/blog.md`: categorized table of contents linking to per-video `.md`

## Notes

- Title/file names are generated from transcript content using Ollama.
- File names are normalized to safe slugs.
- If title generation fails, the script uses a fallback name.
- If a URL fails to download, the script skips it and continues.