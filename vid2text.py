#!/usr/bin/env python3
"""Download a video and transcribe its audio to text."""

import argparse
import os
import subprocess
import sys
import tempfile

import whisper


def download_audio(url, output_path):
    """Download video and extract audio using yt-dlp."""
    print(f"Downloading audio from: {url}")
    cmd = [
        "yt-dlp",
        "-x",                        # extract audio only
        "--audio-format", "mp3",     # convert to mp3
        "-o", output_path,
        "--no-playlist",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error downloading: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("Download complete.")


def transcribe_audio(audio_path, model_name="base"):
    """Transcribe audio file using Whisper."""
    print(f"Loading Whisper model '{model_name}'...")
    model = whisper.load_model(model_name)
    print("Transcribing...")
    result = model.transcribe(audio_path)
    return result["text"]


def main():
    parser = argparse.ArgumentParser(description="Download a video and transcribe it to text.")
    parser.add_argument("url", help="URL of the video (Instagram reel, YouTube, etc.)")
    parser.add_argument("-o", "--output", default="transcript.txt", help="Output file for transcript (default: transcript.txt)")
    parser.add_argument("-m", "--model", default="base", choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size (default: base)")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "audio.mp3")
        download_audio(args.url, audio_path)
        transcript = transcribe_audio(audio_path, args.model)

    print(f"\n--- Transcript ---\n{transcript}\n")

    with open(args.output, "w") as f:
        f.write(transcript)
    print(f"Transcript saved to: {args.output}")


if __name__ == "__main__":
    main()
