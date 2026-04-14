#!/usr/bin/env python3
"""Download videos, transcribe them, and generate categorized blog references.

Usage:
    python main.py <url1> <url2> ...
    python main.py -m small <url1>          # use a larger Whisper model
    python main.py --ollama-model gemma4 <url1>  # specify Ollama model
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

import whisper

OUTPUT_DIR = "output"


def slugify(text):
    """Convert a string to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:80].strip('-')


def download_audio(url, output_path):
    """Download video and extract audio using yt-dlp."""
    print(f"  Downloading audio from: {url}")
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "-o", output_path,
        "--no-playlist",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Error downloading: {result.stderr}", file=sys.stderr)
        return False
    return True


def transcribe_audio(audio_path, model):
    """Transcribe audio file using a preloaded Whisper model."""
    print("  Transcribing...")
    result = model.transcribe(audio_path)
    return result["text"].strip()


def query_ollama(prompt, model="gemma4"):
    """Send a prompt to the local Ollama API and return the response."""
    url = "http://localhost:11434/api/generate"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "")
    except urllib.error.URLError as e:
        print(f"  Error connecting to Ollama: {e}", file=sys.stderr)
        print("  Make sure Ollama is running (ollama serve).", file=sys.stderr)
        return None


def generate_title(transcript, ollama_model):
    """Ask Ollama to generate a short descriptive title from the transcript."""
    prompt = f"""Given the following transcript from a short video, generate a short, descriptive title (5-10 words max). Return ONLY the title text, nothing else. No quotes, no markdown, no explanation.

Transcript:
{transcript}

Title:"""
    result = query_ollama(prompt, model=ollama_model)
    if result:
        # Clean up: remove quotes, markdown, newlines
        title = result.strip().strip('"').strip("'").strip('#').strip()
        title = title.split('\n')[0].strip()
        return title
    return None


def generate_individual_blog(title, transcript, source_url, ollama_model):
    """Generate a blog-style markdown entry for a single transcript."""
    prompt = f"""You are a helpful assistant that turns video transcripts into clean, reusable blog-style reference notes.

Given the following transcript from a short video titled "{title}", generate a clean Markdown blog entry with:

1. A descriptive **title** (as an H1 heading)
2. The **category/genre** (e.g., Life Improvements, Coding, Graphic Design, Productivity, Mindset, Health, Finance, etc.)
3. **Source URL**: {source_url}
4. A **summary** (2-3 sentences of what the video teaches)
5. **Key takeaways** (bullet points of actionable items)

Use clean Markdown formatting. Be concise and practical.

Transcript:
{transcript}

Generate the blog entry now:"""

    return query_ollama(prompt, model=ollama_model)


def generate_toc(individual_md_files, ollama_model):
    """Generate a table of contents (blog.md) with categories linking to individual .md files."""
    entries = ""
    filenames = []
    for md_file in individual_md_files:
        with open(md_file, "r") as f:
            content = f.read().strip()
        basename = os.path.basename(md_file)
        filenames.append(basename)
        entries += f"\n--- File: {basename} ---\n{content}\n"

    file_list = ", ".join(filenames)
    prompt = f"""You are a helpful assistant that creates a table of contents from blog entries.

Below are individual blog entries from video transcripts. Each has a filename, title, and category.

Your task:
1. Group entries by their category/genre.
2. Create a Markdown table of contents with:
   - Main title: "# Video Knowledge Base"
   - Category sections as H2 headings (e.g., ## Life Improvements, ## Coding)
   - Under each category, list only the entry title as a Markdown link to the file. Use relative links like [Title](./{basename}).
3. Do NOT include summaries, key takeaways, or full content — only category headings and linked titles.
4. Use clean Markdown formatting.

The available filenames are: {file_list}

Here are the entries:
{entries}

Generate the table of contents now:"""

    return query_ollama(prompt, model=ollama_model)


def process_url(url, whisper_model, ollama_model):
    """Process a single URL: download, transcribe, generate blog entry."""
    print(f"\n{'='*60}")
    print(f"Processing: {url}")
    print('='*60)

    # Download and transcribe
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "audio.mp3")
        if not download_audio(url, audio_path):
            print(f"  SKIPPING: Failed to download {url}", file=sys.stderr)
            return None

        transcript = transcribe_audio(audio_path, whisper_model)
        # Audio/video files are automatically cleaned up when tmpdir exits

    # Generate title using Ollama
    print("  Generating title via Ollama...")
    title = generate_title(transcript, ollama_model)
    if not title:
        print("  Warning: Could not generate title, using fallback.", file=sys.stderr)
        title = f"video-{hash(url) % 10000}"

    slug = slugify(title)
    print(f"  Title: {title}")
    print(f"  Slug: {slug}")

    transcript_path = os.path.join(OUTPUT_DIR, f"{slug}.txt")
    blog_path = os.path.join(OUTPUT_DIR, f"{slug}.md")

    # Save transcript
    with open(transcript_path, "w") as f:
        f.write(transcript)
    print(f"  Transcript saved: {transcript_path}")

    # Generate individual blog entry
    print(f"  Generating blog entry via Ollama...")
    blog_content = generate_individual_blog(title, transcript, url, ollama_model)
    if not blog_content:
        print(f"  Warning: Failed to generate blog for {title}", file=sys.stderr)
        return None

    with open(blog_path, "w") as f:
        f.write(blog_content)
    print(f"  Blog entry saved: {blog_path}")

    return blog_path


def main():
    parser = argparse.ArgumentParser(
        description="Download videos, transcribe, and generate categorized blog references.",
        usage="python main.py [options] <url> [url ...]"
    )
    parser.add_argument("urls", nargs="+", help="Video URLs to process")
    parser.add_argument("-m", "--whisper-model", default="base",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size (default: base)")
    parser.add_argument("--ollama-model", default="gemma4",
                        help="Ollama model to use (default: gemma4)")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load Whisper model once
    print(f"Loading Whisper model '{args.whisper_model}'...")
    whisper_model = whisper.load_model(args.whisper_model)

    # Process each URL
    new_blog_files = []
    for url in args.urls:
        result = process_url(url, whisper_model, args.ollama_model)
        if result:
            new_blog_files.append(result)

    if not new_blog_files:
        print("\nNo blog entries were generated.", file=sys.stderr)
        sys.exit(1)

    # Collect ALL .md files in output/ (except blog.md) for the combined blog
    all_md_files = sorted([
        os.path.join(OUTPUT_DIR, f)
        for f in os.listdir(OUTPUT_DIR)
        if f.endswith(".md") and f != "blog.md"
    ])

    # Generate table of contents blog.md
    print(f"\n{'='*60}")
    print(f"Generating blog.md (table of contents) from {len(all_md_files)} entries...")
    print('='*60)

    toc = generate_toc(all_md_files, args.ollama_model)
    if toc:
        blog_path = os.path.join(OUTPUT_DIR, "blog.md")
        with open(blog_path, "w") as f:
            f.write(toc)
        print(f"Table of contents saved: {blog_path}")
    else:
        print("Warning: Failed to generate table of contents.", file=sys.stderr)

    print(f"\nDone! Processed {len(new_blog_files)} video(s).")
    print(f"Output directory: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
