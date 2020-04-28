#!/usr/bin/env python
import os
import re
import sys

import utils.youtube_utils as yt
import utils.audio as audio_utils

# Video/Audio download options
src_video = "/Users/rjain/aadhyatm/P/video"
src_audio = "/Users/rjain/aadhyatm/P/mp3"

# Audio file metadata options
album_art_file = "/Users/rjain/Aadhyatm Drive/Jainism/images/Acharya_kundkund.jpg"
album = "Niyamsaar"
artist = "Pandit Rishabh Jain"
album_artist = "Acharya Kund Kund"
genre = "Pravachan"

downloaded_folder = "/Users/rjain/Aadhyatm Drive/Jainism/Pravachan/Rishabh Ji/Niyamsaar"

API_KEY = "AIzaSyAaut-x1l6wcFwK-1-MxKK8idIoZhDXPxM"

# yt_id = "mwFDhSDt9uE"
# output = "003_Upodghaat"

yt_id = sys.argv[1]
output = sys.argv[2]

video = os.path.join("%s/%s.mp4" % (src_video, output))
audio = os.path.join("%s/%s.mp3" % (downloaded_folder, output))

if not yt.download_video(yt_id, video):
    print("Unable to download video")
    sys.exit(1)

try:
    track_num = int(os.path.basename(audio).split("_")[0])
except Exception as e:
    track_num = int(os.path.basename(audio)[0:3])

# convert to audio
audio_utils.video_to_audio(video, audio, replace=True)
audio_utils.add_metadata(audio, album, artist,
                         album_artist, album_art_file, track_num=track_num)

