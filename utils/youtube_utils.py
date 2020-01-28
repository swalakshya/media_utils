# -*- coding: utf-8 -*-

import subprocess
import time
import os

import googleapiclient.discovery
import googleapiclient.errors

from youtube_dl import YoutubeDL

def download_video(video_id, target_f):
    params = {
        'nocheckcertificate': True,
        'format': 'mp4',
        'ignoreerrors': True,
        'outtmpl': target_f,
    }

    yt = YoutubeDL(params=params)
    rc = 0
    try:
        rc = yt.download([video_id])
    except Exception as e:
        print("Couldn't download file with id %s. Exception: %s" % (video_id, str(e)))

    if rc != 0:
        return False
    return True

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

    while(True):
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
