import os
import subprocess
import json
import re
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

    def get_transcript(self, video_url: str, lang: str = 'en') -> Dict[str, Any]:
        """
        Fetches a transcript for the given URL using yt-dlp.
        Returns a dictionary containing the text and metadata.
        """
        video_id = self._extract_video_id(video_url)
        if not video_id:
            return {"status": "error", "error": "Invalid YouTube URL"}

        try:
            # Using a more robust approach:
            # 1. Get the subtitles via yt-dlp command line
            # 2. Download the sub as a .vtt or .srt file
            
            output_template = f"/tmp/yt_sub_{video_id}"
            
            # We'll try to get the subtitles. 
            # --write-auto-subs: get auto-generated if manual is missing
            # --sub-lang: specify language
            # --skip-download: don't download the video
            # --convert-subs srt: convert to srt for easier parsing
            cmd = [
                "yt-dlp",
                "--skip-download",
                "--write-auto-subs",
                "--sub-lang", lang,
                "--convert-subs", "srt",
                "-o", output_template,
                video_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # yt-dlp creates files like: /tmp/yt_sub_ID.en.srt
            # We need to find the actual file created.
            found_file = None
            for f in os.listdir("/tmp"):
                if f.startswith(f"yt_sub_{video_id}") and f.endswith(".srt"):
                    found_file = os.path.join("/tmp", f)
                    break
            
            if not found_file:
                return {"status": "error", "error": f"Could not find {lang} subtitles for video {video_id}"}

            with open(found_file, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            # Basic SRT to text conversion
            # Remove timestamps and indices
            lines = srt_content.split('\n')
            text_lines = []
            for line in lines:
                line = line.strip()
                if not line or line.isdigit() or "-->" in line:
                    continue
                text_lines.append(line)
            
            full_text = " ".join(text_lines)
            
            # Cleanup
            os.remove(found_file)

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
