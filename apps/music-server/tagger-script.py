import os
import subprocess
import json
import re
import time
import requests
import musicbrainzngs
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC, Picture

# Initialize MusicBrainz
musicbrainzngs.set_useragent("MusicTaggerCronJob", "0.1", "https://github.com/lollodo/lollo-k3s-ops")

MUSIC_DIR = "/music"
MAX_DURATION = 600  # 10 minutes

def clean_filename(filename):
    name = os.path.splitext(filename)[0]
    name = re.sub(r'\[[a-zA-Z0-9_-]{11}\]', '', name)
    name = re.sub(r'(?i)\(official (video|audio|music video|lyrics|lyric video)\)', '', name)
    name = re.sub(r'(?i)official (video|audio|music video|lyrics|lyric video)', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def get_duration(file_path):
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'json', file_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            return 0
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except Exception as e:
        print(f"Error getting duration for {file_path}: {e}")
        return 0

def search_musicbrainz(query, duration):
    try:
        print(f"Searching MusicBrainz for: {query}")
        results = musicbrainzngs.search_recordings(query=query, limit=10)
        for rec in results.get('recording-list', []):
            mb_length = int(rec.get('length', 0)) / 1000
            if mb_length > 0 and abs(mb_length - duration) < 15:
                return rec
        return None
    except Exception as e:
        print(f"MusicBrainz search error: {e}")
        return None

def get_cover_art(release_id):
    try:
        url = f"https://coverartarchive.org/release/{release_id}/front"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.content
    except Exception as e:
        print(f"Cover Art error: {e}")
    return None

def tag_file(file_path, recording):
    try:
        print(f"Tagging {file_path} with {recording['title']}")
        
        # Get metadata
        title = recording['title']
        artist = recording['artist-credit'][0]['artist']['name'] if 'artist-credit' in recording else None
        album = None
        release_id = None
        date = None
        
        if 'release-list' in recording:
            release = recording['release-list'][0]
            album = release['title']
            release_id = release['id']
            if 'date' in release:
                date = release['date'][:4]

        # Apply basic tags
        audio = mutagen.File(file_path, easy=True)
        if audio is None:
            print(f"Unsupported format for {file_path}")
            return

        audio['title'] = title
        if artist: audio['artist'] = artist
        if album: audio['album'] = album
        if date: audio['date'] = date
        audio.save()

        # Apply cover art
        if release_id:
            cover_data = get_cover_art(release_id)
            if cover_data:
                if file_path.lower().endswith('.mp3'):
                    audio = MP3(file_path, ID3=ID3)
                    try: audio.add_tags()
                    except: pass
                    audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Front Cover', data=cover_data))
                    audio.save()
                elif file_path.lower().endswith('.m4a'):
                    audio = MP4(file_path)
                    audio['covr'] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]
                    audio.save()
                elif file_path.lower().endswith('.flac'):
                    audio = FLAC(file_path)
                    image = Picture()
                    image.type = 3
                    image.mime = 'image/jpeg'
                    image.desc = 'front cover'
                    image.data = cover_data
                    audio.add_picture(image)
                    audio.save()
                print(f"Cover art added for {file_path}")

    except Exception as e:
        print(f"Error tagging {file_path}: {e}")

def process_files():
    for root, dirs, files in os.walk(MUSIC_DIR):
        for file in files:
            if file.lower().endswith(('.mp3', '.m4a', '.flac')):
                file_path = os.path.join(root, file)
                
                try:
                    audio = mutagen.File(file_path, easy=True)
                    if audio and 'title' in audio and audio['title'][0]:
                        # If title doesn't look like filename, it's likely already tagged
                        if not clean_filename(file).startswith(audio['title'][0][:10]):
                            print(f"Skipping already tagged file: {file}")
                            continue
                except:
                    pass

                duration = get_duration(file_path)
                if 0 < duration <= MAX_DURATION:
                    query = clean_filename(file)
                    recording = search_musicbrainz(query, duration)
                    if recording:
                        tag_file(file_path, recording)
                        time.sleep(1)
                    else:
                        print(f"No match found for: {file}")
                elif duration > MAX_DURATION:
                    print(f"Skipping long file (>10min): {file} ({duration}s)")

if __name__ == "__main__":
    process_files()
