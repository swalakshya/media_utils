# -*- coding: utf-8 -*-
import os
import shutil

import googleapiclient.discovery
import googleapiclient.errors

from utils import media

from youtube_dl import YoutubeDL

TMP_DIR = "%s/tmp" % (os.getenv("HOME"))

def download_video(video_id, target_f, force_encode=False):
    tmp_file = "%s/yt_download_video.mp4" % TMP_DIR
    params = {
        'nocheckcertificate': True,
        'format': 'bestvideo+bestaudio',
        'ignoreerrors': True,
        'outtmpl': tmp_file,
    }

    yt = YoutubeDL(params=params)
    rc = 0
    try:
        rc = yt.download([video_id])
    except Exception as e:
        print("Couldn't download file with id %s. Exception: %s" % (video_id, str(e)))

    if rc != 0:
        return False

    tmp_file_mkv = tmp_file.replace('.mp4', '.mkv')
    should_encode = force_encode
    if os.path.exists(tmp_file_mkv):
        tmp_file = tmp_file_mkv
        should_encode = True
    if should_encode:
        print("Re-encoding file using handbrake %s" % tmp_file)
        media.convert_video(tmp_file, target_f)
        os.remove(tmp_file)
    else:
        shutil.move(tmp_file, target_f)
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
