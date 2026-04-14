#!/usr/bin/env python3
"""Generate categorized blog-like references from transcripts using a local Ollama model."""

import argparse
import glob
import json
import os
import sys
import urllib.request


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
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "")
    except urllib.error.URLError as e:
        print(f"Error connecting to Ollama: {e}", file=sys.stderr)
        print("Make sure Ollama is running (ollama serve).", file=sys.stderr)
        sys.exit(1)


def load_transcripts(directory):
    """Load all transcript*.txt files from the given directory."""
    pattern = os.path.join(directory, "transcript*.txt")
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"No transcript files found in {directory}", file=sys.stderr)
        sys.exit(1)

    transcripts = []
    for f in files:
        with open(f, "r") as fh:
            content = fh.read().strip()
            if content:
                transcripts.append({"file": os.path.basename(f), "text": content})
    return transcripts


def build_prompt(transcripts):
    """Build the prompt for the LLM."""
    transcript_block = ""
    for i, t in enumerate(transcripts, 1):
        transcript_block += f"\n--- Transcript {i} (from {t['file']}) ---\n{t['text']}\n"

    return f"""You are a helpful assistant that organizes knowledge from video transcripts into a clean, reusable blog-style reference document.

Below are transcripts from several short videos (Instagram reels). Your task:

1. Read each transcript carefully.
2. Categorize each one into a genre/topic. Use categories like: Life Improvements, Coding, Graphic Design, Productivity, Mindset, Health, Finance, etc. Create new categories as needed.
3. For each transcript, write a clean, concise blog-like entry with:
   - A short descriptive **title**
   - The **category/genre**
   - A **summary** (2-3 sentences of what the video teaches)
   - **Key takeaways** (bullet points of actionable items)
   - The **source transcript file** name

4. Group entries by category.
5. Use clean Markdown formatting.

Here are the transcripts:
{transcript_block}

Now generate the organized blog-style reference document in Markdown:"""


def main():
    parser = argparse.ArgumentParser(description="Generate categorized blog references from transcripts using Ollama.")
    parser.add_argument("-d", "--directory", default=".", help="Directory containing transcript*.txt files (default: current dir)")
    parser.add_argument("-m", "--model", default="gemma4", help="Ollama model to use (default: gemma4)")
    parser.add_argument("-o", "--output", default="blog_reference.md", help="Output Markdown file (default: blog_reference.md)")
    args = parser.parse_args()

    print(f"Loading transcripts from: {args.directory}")
    transcripts = load_transcripts(args.directory)
    print(f"Found {len(transcripts)} transcript(s): {[t['file'] for t in transcripts]}")

    prompt = build_prompt(transcripts)

    print(f"Sending to Ollama ({args.model})... this may take a moment.")
    result = query_ollama(prompt, model=args.model)

    if not result.strip():
        print("Error: Got empty response from Ollama.", file=sys.stderr)
        sys.exit(1)

    with open(args.output, "w") as f:
        f.write(result)

    print(f"\nBlog reference saved to: {args.output}")
    print(f"\n--- Preview ---\n{result[:500]}...")


if __name__ == "__main__":
    main()
