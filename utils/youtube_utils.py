# -*- coding: utf-8 -*-
import os
import shutil
import time
import yt_dlp

import googleapiclient.discovery
import googleapiclient.errors

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

from utils import media
from utils import utils


TMP_DIR = "%s/tmp" % (os.getenv("HOME"))


def download_transcript_for_video(video_id, output_folder, lang="hi", output_format="txt", api_key=None, video_title=None):
    """
    Download transcript for a single video using YouTube Transcript API.
    This avoids VTT conversion issues and provides clean text.

    Args:
        video_id: YouTube video ID
        output_folder: Folder to save the transcript
        lang: Language code (e.g., 'hi', 'gu', 'en')
        output_format: 'txt' or 'srt'
        api_key: YouTube Data API v3 key (optional, uses video_id as title if not provided)
        video_title: Pre-fetched video title (optional, avoids API call if provided)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Use pre-fetched title if provided, otherwise fetch it
        if not video_title:
            video_title = video_id  # Default fallback

            if api_key:
                try:
                    youtube = googleapiclient.discovery.build(
                        'youtube', 'v3', developerKey=api_key)

                    request = youtube.videos().list(
                        part='snippet',
                        id=video_id
                    )
                    response = request.execute()

                    if response.get('items'):
                        video_title = response['items'][0]['snippet']['title']
                    else:
                        print("Warning: Could not find video metadata for %s, using video ID as title" % video_id)
                except Exception as e:
                    print("Warning: Could not fetch video title via API: %s, using video ID as title" % str(e))
            else:
                print("Note: No API key provided, using video ID as filename")

        # Sanitize filename
        safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title[:100]  # Limit length

        # Try to get transcript using the fetch method
        transcript = YouTubeTranscriptApi().fetch(video_id, languages=[lang])

        if output_format == "txt":
            # Extract just the text from snippets
            text_lines = [snippet.text for snippet in transcript.snippets]
            output_text = ' '.join(text_lines)

            output_file = os.path.join(output_folder, "%s [%s].txt" % (safe_title, video_id))
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_text)
            print("Saved transcript to: %s" % output_file)

        elif output_format == "srt":
            # Convert to SRT format
            output_file = os.path.join(output_folder, "%s [%s].srt" % (safe_title, video_id))
            with open(output_file, 'w', encoding='utf-8') as f:
                for i, snippet in enumerate(transcript.snippets, start=1):
                    start_time = format_timestamp(snippet.start)
                    end_time = format_timestamp(snippet.start + snippet.duration)
                    f.write("%d\n" % i)
                    f.write("%s --> %s\n" % (start_time, end_time))
                    f.write("%s\n\n" % snippet.text)
            print("Saved transcript to: %s" % output_file)

        return True

    except NoTranscriptFound:
        print("No transcript found for video %s in language %s" % (video_id, lang))
        return False
    except TranscriptsDisabled:
        print("Transcripts are disabled for video %s" % video_id)
        return False
    except Exception as e:
        print("Error downloading transcript for video %s: %s" % (video_id, str(e)))
        return False

def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return "%02d:%02d:%02d,%03d" % (hours, minutes, secs, millis)

def download_subtitles(yt_id, output_folder, sub_format="srt",
                       auto_gen=True, lang="hi", api_key=None):
    """
    Download subtitles for YouTube video(s) or playlist.
    Uses YouTube Transcript API for clean transcripts without VTT conversion issues.

    Args:
        yt_id: YouTube video ID, URL, or playlist ID/URL
        output_folder: Folder to save subtitles
        sub_format: 'srt' or 'txt'
        auto_gen: Not used anymore (kept for compatibility)
        lang: Language code (e.g., 'hi', 'gu', 'en')
        api_key: YouTube Data API v3 key (optional, for better filenames)
    """
    print("Downloading subtitles for ID %s, format %s, lang %s in folder %s" % (
        yt_id, sub_format, lang, output_folder
    ))

    if sub_format not in ["srt", "txt"]:
        print("Incompatible format %s. Please use 'srt' or 'txt'" % sub_format)
        return False

    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Check if it's a playlist or single video
    from yt_dlp import YoutubeDL

    # Determine if it's a playlist by checking if ID starts with PL
    is_playlist = yt_id.startswith('PL') or 'list=' in yt_id or '/playlist' in yt_id

    try:
        if is_playlist:
            # Extract playlist info with full metadata (includes titles)
            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': 'in_playlist'}
            with YoutubeDL(ydl_opts) as ydl:
                # Make sure we have the full playlist URL
                playlist_url = yt_id if yt_id.startswith('http') else 'https://www.youtube.com/playlist?list=%s' % yt_id
                info = ydl.extract_info(playlist_url, download=False)

                if 'entries' in info:
                    print("Detected playlist with %d videos" % len(info['entries']))
                    # Store both video_id and title
                    video_ids = []
                    video_titles = {}
                    for entry in info['entries']:
                        if entry and 'id' in entry:
                            vid_id = entry['id']
                            video_ids.append(vid_id)
                            # yt_dlp provides 'title' even with extract_flat
                            if 'title' in entry and entry['title']:
                                video_titles[vid_id] = entry['title']
                else:
                    print("Warning: Could not extract playlist entries")
                    return False
        else:
            # Single video - just extract the video ID
            video_ids = [yt_id]
            video_titles = {}
            print("Processing single video: %s" % yt_id)

        # Download transcript for each video
        success_count = 0
        for i, video_id in enumerate(video_ids, 1):
            print("\n[%d/%d] Processing video: %s" % (i, len(video_ids), video_id))
            # Pass title from yt_dlp if available, otherwise use API key or fall back to video_id
            title = video_titles.get(video_id) if video_titles else None
            if download_transcript_for_video(video_id, output_folder, lang, sub_format, api_key, video_title=title):
                success_count += 1
            # Add delay to avoid hitting YouTube's rate limit
            if i < len(video_ids):  # Don't delay after the last video
                time.sleep(5)

        print("\n" + "="*50)
        print("Successfully downloaded %d/%d transcripts" % (success_count, len(video_ids)))
        print("="*50)
        return success_count > 0

    except Exception as e:
        print("Error processing ID %s: %s" % (yt_id, str(e)))
        import traceback
        traceback.print_exc()
        return False


def download_video(video_id, target_f, force_encode=False, clean_tmp=True):
    start = time.time()
    if clean_tmp:
        if os.path.exists(TMP_DIR):
            shutil.rmtree(TMP_DIR)
        os.makedirs(TMP_DIR)
    tmp_file = "%s/yt_download_video.mp4" % TMP_DIR
    params = {
        'nocheckcertificate': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]',
        'ignoreerrors': True,
        'outtmpl': tmp_file,
    }

    yt = yt_dlp.YoutubeDL(params)
    rc = 0
    try:
        rc = yt.download([video_id])
    except Exception as e:
        print("Couldn't download file with id %s. Exception: %s" % (video_id, str(e)))

    if rc != 0:
        return False

    tmp_file_mkv = tmp_file.replace('.mp4', '.mkv')
    tmp_file_mkv1 = tmp_file + ".mkv"
    tmp_file_webm = tmp_file + ".webm"
    should_encode = force_encode
    if os.path.exists(tmp_file_mkv):
        tmp_file = tmp_file_mkv
        should_encode = True
    elif os.path.exists(tmp_file_mkv1):
        tmp_file = tmp_file_mkv1
        should_encode = True
    elif os.path.exists(tmp_file_webm):
        tmp_file = tmp_file_webm
        should_encode = True
    if should_encode:
        print("Re-encoding file using handbrake %s" % tmp_file)
        media.convert_video(tmp_file, target_f)
        os.remove(tmp_file)
    else:
        shutil.copy(tmp_file, target_f)
        os.remove(tmp_file)
    end_time = time.time()
    total_time = end_time - start
    print("Downloading video took %0.0f seconds" % total_time)
    return True


"""This function requires google developers API key. This can be obtained from
https://console.developers.google.com/
Look at the credentials tab on the menu.
"""
def get_playlist_items(playlist_id, api_key, reverse=False):
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=api_key)

    items = list()
    # Each item will contain the following properties
    # - title
    # - video_id

    next_token = None

    while True:
        if next_token is None:
            request = youtube.playlistItems().list(
                part="snippet",
                maxResults=50,
                playlistId=playlist_id
            )
        else:
            request = youtube.playlistItems().list(
                part="snippet",
                maxResults=50,
                playlistId=playlist_id,
                pageToken=next_token
            )
        response = request.execute()

        for item in response['items']:
            title = item['snippet']['title']
            video_id = item['snippet']['resourceId']['videoId']
            position = item['snippet']['position']
            list_item = {"title": title,
                         "video_id": video_id, "position": position}
            if reverse:
                items.insert(0, list_item)
            else:
                items.append(list_item)

        if 'nextPageToken' in response.keys():
            next_token = response['nextPageToken']
        else:
            break

    return items


def get_authenticated_service(credentials_file):
    """
    Authenticate with YouTube using OAuth 2.0.

    Args:
        credentials_file: Path to client_secrets.json file

    Returns:
        Authenticated YouTube API service object
    """
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    import pickle

    SCOPES = ['https://www.googleapis.com/auth/youtube.upload',
              'https://www.googleapis.com/auth/youtube']

    creds = None
    token_file = 'token.pickle'

    # Load existing credentials
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_file):
                print("Error: Credentials file not found: %s" % credentials_file)
                print("Please download OAuth 2.0 credentials from Google Cloud Console")
                return None

            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for future use
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)

    youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=creds)
    return youtube


def get_video_title_from_file(video_file):
    """
    Extract video title from filename (without extension).
    This ensures consistent title extraction for both checking and uploading.

    Args:
        video_file: Path to video file

    Returns:
        Title string (filename without extension)
    """
    return os.path.splitext(os.path.basename(video_file))[0]


def get_existing_playlist_videos(youtube, playlist_id):
    """
    Fetch all existing videos in a playlist.

    Args:
        youtube: Authenticated YouTube service object
        playlist_id: ID of the playlist

    Returns:
        Set of video titles that already exist in the playlist
    """
    existing_titles = set()
    next_page_token = None

    print("Fetching existing videos from playlist...")

    while True:
        request = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )

        try:
            response = request.execute()

            for item in response.get('items', []):
                title = item['snippet']['title']
                existing_titles.add(title)

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        except Exception as e:
            print("Warning: Could not fetch existing videos: %s" % str(e))
            break

    print("Found %d existing videos in playlist" % len(existing_titles))
    return existing_titles


def find_or_create_playlist(youtube, playlist_name):
    """
    Find existing playlist by name or create new one.

    Args:
        youtube: Authenticated YouTube service object
        playlist_name: Name of the playlist

    Returns:
        Playlist ID
    """
    # Search for existing playlist
    request = youtube.playlists().list(
        part='snippet',
        mine=True,
        maxResults=50
    )
    response = request.execute()

    for item in response.get('items', []):
        if item['snippet']['title'] == playlist_name:
            print("Found existing playlist: %s" % playlist_name)
            return item['id']

    # Create new playlist if not found
    print("Creating new playlist: %s" % playlist_name)
    request = youtube.playlists().insert(
        part='snippet,status',
        body={
            'snippet': {
                'title': playlist_name,
                'description': 'Created via YouTube Utils'
            },
            'status': {
                'privacyStatus': 'unlisted'
            }
        }
    )
    response = request.execute()
    return response['id']


def upload_video(youtube, video_file, title, playlist_id, language='hi'):
    """
    Upload a video to YouTube with resumable upload.

    Args:
        youtube: Authenticated YouTube service object
        video_file: Path to video file
        title: Video title
        playlist_id: ID of playlist to add video to
        language: Language code (hi, gu, en, etc.)

    Returns:
        Video ID if successful, None otherwise
    """
    from googleapiclient.http import MediaFileUpload

    print("Uploading: %s" % os.path.basename(video_file))

    body = {
        'snippet': {
            'title': title,
            'description': 'Uploaded via YouTube Utils',
            'categoryId': '22',  # People & Blogs
            'defaultLanguage': language,
            'defaultAudioLanguage': language
        },
        'status': {
            'privacyStatus': 'unlisted',
            'selfDeclaredMadeForKids': False
        }
    }

    # Create resumable upload
    media = MediaFileUpload(
        video_file,
        chunksize=1024*1024,  # 1MB chunks
        resumable=True
    )

    request = youtube.videos().insert(
        part='snippet,status',
        body=body,
        media_body=media
    )

    response = None
    try:
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print("  Upload progress: %d%%" % progress)

        video_id = response['id']
        print("  ✓ Uploaded successfully! Video ID: %s" % video_id)

        # Add to playlist
        youtube.playlistItems().insert(
            part='snippet',
            body={
                'snippet': {
                    'playlistId': playlist_id,
                    'resourceId': {
                        'kind': 'youtube#video',
                        'videoId': video_id
                    }
                }
            }
        ).execute()

        print("  ✓ Added to playlist")
        return video_id

    except Exception as e:
        print("  ✗ Upload failed: %s" % str(e))
        return None


def upload_videos_to_playlist(folder, playlist_name, credentials_file, language='hi'):
    """
    Upload all videos from a folder to a YouTube playlist.

    Args:
        folder: Path to folder containing video files
        playlist_name: Name of playlist (creates if doesn't exist)
        credentials_file: Path to OAuth 2.0 credentials JSON
        language: Language code (hi, gu, en, etc.)

    Returns:
        Number of successfully uploaded videos
    """
    # Supported video extensions
    VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv',
                        '.vob', '.webm', '.m4v', '.mpg', '.mpeg']

    print("="*60)
    print("YouTube Video Uploader")
    print("="*60)

    # Validate folder
    if not os.path.exists(folder):
        print("Error: Folder not found: %s" % folder)
        return 0

    # Find all video files
    video_files = []
    for file in os.listdir(folder):
        file_path = os.path.join(folder, file)
        if os.path.isfile(file_path):
            ext = os.path.splitext(file)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                video_files.append(file_path)

    if not video_files:
        print("No video files found in folder: %s" % folder)
        return 0

    video_files.sort()
    print("\nFound %d video file(s)" % len(video_files))

    # Authenticate
    print("\nAuthenticating with YouTube...")
    youtube = get_authenticated_service(credentials_file)
    if not youtube:
        return 0

    print("✓ Authentication successful!")

    # Find or create playlist
    print("\nSetting up playlist...")
    playlist_id = find_or_create_playlist(youtube, playlist_name)
    if not playlist_id:
        print("Failed to create/find playlist")
        return 0

    print("✓ Playlist ID: %s" % playlist_id)

    # Fetch existing videos in playlist for idempotency check
    print("")
    existing_titles = get_existing_playlist_videos(youtube, playlist_id)

    # Upload videos
    print("\n" + "="*60)
    print("Starting uploads...")
    print("="*60 + "\n")

    success_count = 0
    skipped_count = 0
    failed_count = 0

    for i, video_file in enumerate(video_files, 1):
        print("[%d/%d] %s" % (i, len(video_files), os.path.basename(video_file)))

        # Extract title using shared function
        title = get_video_title_from_file(video_file)

        # Check if video already exists in playlist
        if title in existing_titles:
            print("  ⊘ Skipped - already exists in playlist (title: '%s')" % title)
            skipped_count += 1
        else:
            # Upload the video
            video_id = upload_video(youtube, video_file, title, playlist_id, language)
            if video_id:
                success_count += 1
                # Add to existing titles set so we don't re-upload if there are duplicates in folder
                existing_titles.add(title)
            else:
                failed_count += 1

        print("")  # Blank line between videos

    # Summary
    print("="*60)
    print("Upload Summary")
    print("="*60)
    print("Total videos in folder: %d" % len(video_files))
    print("Successfully uploaded: %d" % success_count)
    print("Skipped (already exist): %d" % skipped_count)
    print("Failed: %d" % failed_count)
    print("")
    print("Playlist: %s" % playlist_name)
    print("Playlist ID: %s" % playlist_id)
    print("Playlist URL: https://www.youtube.com/playlist?list=%s" % playlist_id)
    print("="*60)

    return success_count
