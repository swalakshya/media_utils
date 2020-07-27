#!/usr/bin/env python
import json
import os
import sys
import shutil
from copy import deepcopy
import utils.youtube_utils as yt
import utils.media as media_utils

"""
This file reads a config file in the following format.
{
    "video_path": <path where video file is downloaded>,
    "audio_path": <path where audio file is downloaded>,
    "album_art_file": <...>,
    "album": <...>,
    "artist": <...>,
    "album_artist": <....>,
    "genre": <....>,
    "youtube_id": <...>,
    "output_file": <...>,
    "start": <...>,
    "end": <...>
}
"""

TMP_DIR = "%s/tmp" % os.getenv("HOME")


def download_videos_and_combine(video_list, video_final):
    hb = handbrake_config()
    curr_dir = os.getcwd()
    shutil.rmtree(TMP_DIR)
    os.mkdir(TMP_DIR)
    os.chdir(TMP_DIR)
    i = 1
    videos = list()
    for v in video_list:
        video_name = "v%d.mp4" % i
        tmp_vname = "tmpv%d.mp4" % i
        if not yt.download_video(v, tmp_vname):
            print("Couldn't download %s" % v)
            sys.exit(1)
        videos.append(video_name)
        ret = media_utils.convert_video(tmp_vname, video_name,
                                        preset_file=hb['preset_file'],
                                        preset_name=hb['preset_name'])
        if not ret:
            print("Couldn't convert video %s" % v)
            sys.exit(1)
        i += 1
    os.chdir(curr_dir)

    # combine videos
    ret = media_utils.combine_videos(TMP_DIR, videos, video_final)
    if not ret:
        print("Couldn't convert videos")
        return False
    return True


def handbrake_config():
    if len(sys.argv) >= 3:
        cfg = sys.argv[2]
    else:
        cfg = "handbrake.cfg"
    print("Using handbrake config file %s" % cfg)
    f = open(cfg, 'r')
    c = json.load(f)
    return c


def main():
    if len(sys.argv) < 2:
        sys.exit("ERROR: Provide a config file\n")
    config_file_path = sys.argv[1]

    f = open(config_file_path, 'r')
    config = json.load(f)

    print(json.dumps(config, indent=2))
    print()

    nc = deepcopy(config)
    videos = config['videos']
    for video in videos:
        for key, value in video.items():
            nc[key] = value
        download(nc)


def download(config):
    video = os.path.join("%s/%s.mp4" % (config['video_path'], config['output_file']))
    audio = os.path.join("%s/%s.mp3" % (config['audio_path'], config['output_file']))

    if os.path.exists(video):
        os.remove(video)
    if os.path.exists(audio):
        os.remove(audio)

    if config['youtube_id'] is not None and config['youtube_parts'] is not None:
        print("Exactly one of youtube_id and youtube_parts should be set")
        sys.exit(1)
    if (not config['youtube_id']) and (not config['youtube_parts']):
        print("Exactly one of youtube_id and youtube_parts should be set")
        sys.exit(1)

    if config['youtube_id']:
        if not yt.download_video(config['youtube_id'], video):
            print("Unable to download video")
            sys.exit(1)
    if config['youtube_parts']:
        if not download_videos_and_combine(config['youtube_parts'], video):
            print("Unable to download and combine videos")
            sys.exit(1)

    try:
        track_num = int(os.path.basename(audio).split("_")[0])
    except Exception as e:
        track_num = int(os.path.basename(audio)[0:3])

    # convert to audio
    media_utils.trim_media(video, config['start'], config['end'])
    media_utils.video_to_audio(video, audio, replace=True)
    media_utils.add_metadata(audio, config['album'], config['artist'],
                             config['album_artist'], config['album_art_file'],
                             track_num=track_num)

if __name__ == '__main__':
    main()
