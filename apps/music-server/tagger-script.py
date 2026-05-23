import os
import subprocess
import json
import re
import time
import requests
import musicbrainzngs
import mutagen
import acoustid
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, USLT, SYLT
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC, Picture
from PIL import Image
from io import BytesIO

# Initialize MusicBrainz
musicbrainzngs.set_useragent("MusicTaggerCronJob", "0.2", "https://github.com/lollodo/lollo-k3s-ops")

MUSIC_DIR = "/music"
MAX_DURATION = 600
# Free AcoustID API Key (for basic use)
ACOUSTID_API_KEY = "89W95A8D" 

def clean_text(text):
    if not text: return ""
    # Remove weird characters, normalize whitespace, ensure UTF-8
    text = text.encode('utf-8', 'ignore').decode('utf-8')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_duration(file_path):
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'json', file_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except: return 0

def get_fingerprint(file_path, duration):
    try:
        # Start at 25% to avoid intros/ads
        offset = duration * 0.25
        # Use ffmpeg to extract 120s from the offset and pipe to fpcalc
        cmd = f'ffmpeg -ss {offset} -t 120 -i "{file_path}" -f wav -ar 44100 -ac 2 -loglevel quiet - | fpcalc -'
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in result.stdout.splitlines():
            if line.startswith("FINGERPRINT="):
                return line.split("=")[1]
    except Exception as e:
        print(f"Fingerprinting error for {file_path}: {e}")
    return None

def get_lyrics(artist, title):
    try:
        url = f"https://lrclib.net/api/get?artist_name={artist}&track_name={title}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('syncedLyrics') or data.get('plainLyrics')
    except: pass
    return None

def get_optimized_cover(release_id):
    try:
        # MusicBrainz cover art archive allows requesting specific sizes
        url = f"https://coverartarchive.org/release/{release_id}/front-1000"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content))
            # Ensure it's exactly 1000x1000 or resize if needed
            if img.size != (1000, 1000):
                img = img.resize((1000, 1000), Image.Resampling.LANCZOS)
            
            output = BytesIO()
            img.save(output, format="JPEG", quality=85, optimize=True)
            return output.getvalue()
    except Exception as e:
        print(f"Cover optimization error: {e}")
    return None

def organize_file(file_path, artist, year, album, title, track_num=None):
    try:
        artist = re.sub(r'[\\/:*?"<>|]', '_', artist)
        album = re.sub(r'[\\/:*?"<>|]', '_', album)
        title = re.sub(r'[\\/:*?"<>|]', '_', title)
        
        album_folder = f"{year} - {album}" if year else album
        new_dir = os.path.join(MUSIC_DIR, artist, album_folder)
        os.makedirs(new_dir, exist_ok=True)
        
        ext = os.path.splitext(file_path)[1]
        new_name = f"{track_num:02d} - {title}{ext}" if track_num else f"{title}{ext}"
        new_path = os.path.join(new_dir, new_name)
        
        if file_path != new_path:
            print(f"Moving: {file_path} -> {new_path}")
            os.rename(file_path, new_path)
            return new_path
    except Exception as e:
        print(f"Organize error: {e}")
    return file_path

def tag_file(file_path, recording):
    try:
        title = clean_text(recording['title'])
        artist = clean_text(recording['artist-credit'][0]['artist']['name'])
        album = None
        release_id = None
        year = None
        track_num = None

        if 'release-list' in recording:
            release = recording['release-list'][0]
            album = clean_text(release['title'])
            release_id = release['id']
            year = release.get('date', '')[:4]
            if 'medium-list' in release:
                track_num = int(release['medium-list'][0]['track-list'][0]['number'])

        # Apply basic tags
        audio = mutagen.File(file_path, easy=True)
        audio['title'] = title
        audio['artist'] = artist
        if album: audio['album'] = album
        if year: audio['date'] = year
        if track_num: audio['tracknumber'] = str(track_num)
        audio.save()

        # Lyrics
        lyrics = get_lyrics(artist, title)
        if lyrics:
            audio_full = mutagen.File(file_path)
            if file_path.endswith('.mp3'):
                audio_full.tags.add(USLT(encoding=3, lang='eng', desc='', text=lyrics))
            elif file_path.endswith('.flac'):
                audio_full['lyrics'] = lyrics
            audio_full.save()

        # Cover Art
        if release_id:
            cover_data = get_optimized_cover(release_id)
            if cover_data:
                # Save folder.jpg
                album_dir = os.path.dirname(file_path)
                with open(os.path.join(album_dir, 'folder.jpg'), 'wb') as f:
                    f.write(cover_data)
                
                # Embed
                if file_path.lower().endswith('.mp3'):
                    audio_emb = MP3(file_path, ID3=ID3)
                    audio_emb.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Front Cover', data=cover_data))
                    audio_emb.save()
                elif file_path.lower().endswith('.m4a'):
                    audio_emb = MP4(file_path)
                    audio_emb['covr'] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]
                    audio_emb.save()
                elif file_path.lower().endswith('.flac'):
                    audio_emb = FLAC(file_path)
                    img = Picture()
                    img.type = 3; img.mime = 'image/jpeg'; img.data = cover_data
                    audio_emb.add_picture(img)
                    audio_emb.save()

        # Reorganize
        return organize_file(file_path, artist, year, album, title, track_num)

    except Exception as e:
        print(f"Error tagging {file_path}: {e}")
    return file_path

def process_files():
    for root, dirs, files in os.walk(MUSIC_DIR):
        for file in files:
            if file.lower().endswith(('.mp3', '.m4a', '.flac')) and file != 'folder.jpg':
                file_path = os.path.join(root, file)
                duration = get_duration(file_path)
                
                if 0 < duration <= MAX_DURATION:
                    print(f"Processing: {file}")
                    recording = None
                    
                    # 1. Fingerprint match
                    fingerprint = get_fingerprint(file_path, duration)
                    if fingerprint:
                        try:
                            matches = acoustid.lookup(ACOUSTID_API_KEY, fingerprint, duration, meta=['recordings', 'releasegroups', 'compress'])
                            if matches['results']:
                                rid = matches['results'][0]['recordings'][0]['id']
                                recording = musicbrainzngs.get_recording_by_id(rid, includes=['artists', 'releases'])['recording']
                        except: pass
                    
                    # 2. Fallback to filename search
                    if not recording:
                        query = re.sub(r'\[.*?\]|\(.*?\)', '', file).split('.')[0].strip()
                        results = musicbrainzngs.search_recordings(query=query, limit=5)
                        for rec in results.get('recording-list', []):
                            mb_len = int(rec.get('length', 0)) / 1000
                            if mb_len > 0 and abs(mb_len - duration) < 15:
                                recording = rec; break
                    
                    if recording:
                        tag_file(file_path, recording)
                        time.sleep(1)
                elif duration > MAX_DURATION:
                    print(f"Skipping long file: {file}")

if __name__ == "__main__":
    process_files()
