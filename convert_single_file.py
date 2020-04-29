#!/usr/bin/env python
import json
import os
import sys

import utils.youtube_utils as yt
import utils.audio as audio_utils

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
}
"""
if len(sys.argv) < 2:
    sys.exit("ERROR: Provide a config file\n")
config_file_path = sys.argv[1]

f = open(config_file_path, 'r')
config = json.load(f)

print(json.dumps(config, indent=2))
print()

video = os.path.join("%s/%s.mp4" % (config['video_path'], config['output_file']))
audio = os.path.join("%s/%s.mp3" % (config['audio_path'], config['output_file']))

if not yt.download_video(config['youtube_id'], video):
    print("Unable to download video")
    sys.exit(1)

try:
    track_num = int(os.path.basename(audio).split("_")[0])
except Exception as e:
    track_num = int(os.path.basename(audio)[0:3])

# convert to audio
audio_utils.video_to_audio(video, audio, replace=True)
audio_utils.add_metadata(audio, config['album'], config['artist'],
                         config['album_artist'], config['album_art_file'], track_num=track_num)

