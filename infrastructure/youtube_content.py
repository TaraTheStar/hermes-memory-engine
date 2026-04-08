import os
import shutil
import subprocess
import re
import tempfile
from typing import List, Dict, Any, Optional

class YouTubeContentSkill:
    """
    A skill to fetch and process YouTube video transcripts using yt-dlp.
    """
    
    def __init__(self):
        pass

    def _extract_video_id(self, url: str) -> Optional[str]:
        """
        Extracts the video ID from various YouTube URL formats.
        """
        pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(pattern, url)
        return match.group(1) if match else None

    _LANG_PATTERN = re.compile(r'^[a-zA-Z]{2,3}(-[a-zA-Z]{2,4})?$')

    def get_transcript(self, video_url: str, lang: str = 'en') -> Dict[str, Any]:
        """
        Fetches a transcript for the given URL using yt-dlp.
        Returns a dictionary containing the text and metadata.
        """
        video_id = self._extract_video_id(video_url)
        if not video_id:
            return {"status": "error", "error": "Invalid YouTube URL"}

        if not self._LANG_PATTERN.match(lang):
            return {"status": "error", "error": "Invalid language code"}

        # Use a private temp directory to avoid TOCTOU races in shared /tmp
        tmp_dir = tempfile.mkdtemp(prefix="yt_sub_")
        try:
            output_template = os.path.join(tmp_dir, f"yt_sub_{video_id}")

            # Use the validated video_id to construct a canonical URL,
            # rather than passing the raw user-supplied URL to yt-dlp.
            canonical_url = f"https://www.youtube.com/watch?v={video_id}"

            cmd = [
                "yt-dlp",
                "--skip-download",
                "--write-auto-subs",
                "--sub-lang", lang,
                "--convert-subs", "srt",
                "-o", output_template,
                "--", canonical_url
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Find the .srt file yt-dlp created in our private directory
            found_file = None
            for f in os.listdir(tmp_dir):
                if f.endswith(".srt"):
                    found_file = os.path.join(tmp_dir, f)
                    break

            if not found_file:
                return {"status": "error", "error": f"Could not find {lang} subtitles for video {video_id}"}

            with open(found_file, 'r', encoding='utf-8') as f:
                srt_content = f.read()

            # Basic SRT to text conversion
            lines = srt_content.split('\n')
            text_lines = []
            for line in lines:
                line = line.strip()
                if not line or line.isdigit() or "-->" in line:
                    continue
                text_lines.append(line)

            full_text = " ".join(text_lines)

            return {
                "status": "success",
                "video_id": video_id,
                "language": lang,
                "full_text": full_text
            }

        except subprocess.CalledProcessError as e:
            return {
                "status": "error",
                "error": f"yt-dlp failed: {e.stderr}",
                "video_id": video_id
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "video_id": video_id
            }
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

if __name__ == "__main__":
    # Quick Test with the video the user provided
    skill = YouTubeContentSkill()
    test_url = "https://www.youtube.com/watch?v=oYlcUbLAFmw"
    
    print(f"Testing YouTubeContentSkill with {test_url}...")
    result = skill.get_transcript(test_url)
    
    if result["status"] == "success":
        print("Successfully fetched transcript!")
        print(f"Snippet: {result['full_text'][:200]}...")
    else:
        print(f"Failed: {result['error']}")
