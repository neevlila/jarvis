import os
import re
import urllib.parse
import requests
import yt_dlp

def download_youtube_video(query, speak_cb):
    """
    Finds the first matching video ID from YouTube search page HTML
    and downloads it in the background to the user's Downloads folder.
    Calls speak_cb to notify the user.
    """
    try:
        search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(search_url, headers=headers, timeout=5)
        video_id = None
        if response.status_code == 200:
            matches = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', response.text)
            if matches:
                unique_matches = []
                for m in matches:
                    if m not in unique_matches:
                        unique_matches.append(m)
                video_id = unique_matches[0]
        
        if not video_id:
            speak_cb("Could not find the video on YouTube.")
            return
            
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(downloads_dir):
            downloads_dir = os.path.dirname(__file__)
            
        speak_cb("Download started, Sir. I will notify you when it's complete.")
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(downloads_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios']
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(watch_url, download=True)
            title = info.get('title', 'video')
            
        speak_cb(f"Successfully downloaded: {title}. Saved to your Downloads folder.")
        
    except Exception as e:
        speak_cb(f"Error downloading video: {str(e)}")
