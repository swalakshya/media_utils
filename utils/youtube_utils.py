# -*- coding: utf-8 -*-

import subprocess
import time
import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

def get_files(playlist_id, playlist_start=None, playlist_end=None, playlist_reverse=False):
    print("Getting all the files to be downloaded...")
    base_cmd = ["youtube-dl"]
    if playlist_start:
        base_cmd.append("--playlist-start")
        base_cmd.append(str(playlist_start))
    if playlist_end:
        base_cmd.append("--playlist-end")
        base_cmd.append(str(playlist_end))

    if playlist_reverse:
        base_cmd.append("--playlist-reverse")

    cmd_dry = ["--get-id", "--get-title"]

    cmd_dry = base_cmd + cmd_dry + [playlist_id]

    print(cmd_dry)
    start = time.time()
    result = subprocess.Popen(cmd_dry, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = result.communicate()
    end = time.time()
    if result.returncode != 0:
        print("Command to get YouTube IDs failed. Errors:\tstdout: %s\nstderr:%s\n" % (out, err))
        return None
    print("Fetching files took %.2f seconds" % (end - start))
    out = out.decode("utf-8")

    files = list()
    lines = out.split('\n')
    for i in range(0, int(len(lines)/2)):
        fname = lines[2 * i]
        id = lines[(2 * i) + 1]
        files.append([id, fname])
    return files

def download_video(video_id, target_f):
    print("Downloading %s..." % target_f)

    # download video
    cmd = ["youtube-dl", "-i", "-f", "mp4", "-o", target_f, video_id]
    start = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    end = time.time()
    print("Downloading took %.2f seconds. Success: %d" % ((end - start), proc.returncode))
    if proc.returncode != 0:
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
            list_item = {"title": title, "video_id": video_id, "position": position}
            if reverse:
                items.insert(0, list_item)
            else:
                items.append(list_item)

        if 'nextPageToken' in response.keys():
            next_token = response['nextPageToken']
        else:
            break

    return items