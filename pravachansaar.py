#!/usr/bin/env python
import os
import re

import utils.youtube_utils as yt
import utils.audio as audio_utils

"""
pip requirements:
    - eyed3
    - google-api-python-client
    - google-auth-oauthlib
    - youtube_dl

other utils:
    - mplayer
    - youtube_dl
    - lame
"""

# All variables

# Playlist Options
playlist = "PL3mMNbUd3zjvTWg3X00MxAb-DjIJd9xNC"
playlist_start = None
playlist_end = 7
playlist_reverse = True

# Video/Audio download options
src_video = "/Users/rjain/aadhyatm/P/video"
src_audio = "/Users/rjain/aadhyatm/P/mp3"

# Audio file metadata options
album_art_file = "/Users/rjain/Aadhyatm Drive/Jainism/images/Acharya_kundkund.jpg"
album = "Pravachansaar"
artist = "Pandit Rishabh Jain"
album_artist = "Acharya Kund Kund"
genre = "Pravachan"

downloaded_folder = "/Users/rjain/Aadhyatm Drive/Jainism/Pravachan/Rishabh Ji/Pravachansaar"

API_KEY = "AIzaSyAaut-x1l6wcFwK-1-MxKK8idIoZhDXPxM"


def get_details(fname):
    """Return value is a list:
    [serial_number, date, gaatha number, kalash number, other]
    other can be details like "prastavna", "parishist", "upodghaat" etc.

    Eg. files:
    2019-05-22-SHRI PRAVACHANSARJI-PRASTAVNA-Shri Rishavji-2
    2019-05-27-SHRI PRAVACHANSARJI-G-7-8-Shri Rishavji-7
    2019-05-26-SHRI PRAVACHANSARJI-G-6-Shri Rishavji-6
    2019-11-15-SHRI PRAVACHANSARJI-G-145-146-147-Shri Rishavji-152
    """

    result = list()

    # get date
    re_m = re.match('(\d\d\d\d-\d\d-\d\d).*', fname)
    if re_m is not None:
        date = re_m.groups()[0]
        result.append(date)
    else:
        print("Could not find date in file %s" % fname)
        result.append("")

    # get serial number
    re_m = re.match('.*-(\d+)', fname)
    if re_m is not None:
        serial_num = re_m.groups()[0]
        result.append(serial_num)
    else:
        print("Could not find serial number in file %s" % fname)
        return None

    # get gathas
    g_k = fname.split("RJI-")[1].split("Shri")[0]
    g_k_splt = g_k.split("K")

    gatha_string = g_k_splt[0]
    if len(g_k_splt) > 1:
        kalash_string = g_k_splt[1]
    else:
        kalash_string = ""

    while True:
        if gatha_string.startswith('G'):
            gatha_string = gatha_string[1:]
        elif gatha_string.startswith('-'):
            gatha_string = gatha_string[1:]
        else:
            break

    # remove trailing "-"
    while True:
        if gatha_string.endswith("-"):
            gatha_string = gatha_string[:-1]
        else:
            break

    # do same for k
    while True:
        if kalash_string.startswith('K'):
            kalash_string = kalash_string[1:]
        elif kalash_string.startswith('-'):
            kalash_string = kalash_string[1:]
        else:
            break

    while True:
        if kalash_string.endswith('-'):
            kalash_string = kalash_string[:-1]
        else:
            break

    if len(gatha_string) > 0:
        g = gatha_string.split('-')
        gathas = []
        if isint(g[0]):
            gathas.append(g[0])
        if len(g) > 1:
            if isint(g[-1]):
                gathas.append(g[-1])
        result.append(gathas)
    else:
        result.append(list())

    # get kalash
    if len(kalash_string) > 0:
        kalash = []
        k = kalash_string.split('-')
        if isint(k[0]):
            kalash.append(k[0])
        if len(k) > 1:
            if isint(k[-1]):
                kalash.append(k[-1])
        result.append(kalash)
    else:
        result.append(list())

    # get misc
    misc = ["PRASTAVNA", "UPODGHAT", "PARISHIST"]
    misc_elems = []
    for s in misc:
        if s in fname:
            misc_elems.append(s.capitalize())
    result.append(misc_elems)

    return result

def new_fname(fname):
    meta = get_details(fname)
    if meta is None:
        return None

    # serial number and date
    final_fname = "%03d" % (int(meta[1]))

    # gatha
    if len(meta[2]) > 0:
        final_fname = "%s_G-%s" % (final_fname, "-".join(meta[2]))

    # kalash
    if len(meta[3]) > 0:
        final_fname = "%s_K-%s" % (final_fname, "-".join(meta[3]))

    # misc
    if len(meta[4]) > 0:
        final_fname = "%s_%s" % (final_fname, "_".join(meta[4]))
    return final_fname


def get_downloaded_files():
    files = []
    for r, d, f in os.walk(downloaded_folder):
        for file in f:
            if '.mp3' in file:
                # only append the index
                files.append(file.split("_")[0])
    files.sort()
    return files
    # print(files)


def get_files():
    all_files = yt.get_playlist_items(
        playlist_id=playlist, api_key=API_KEY, reverse=True)
    downloaded_files = get_downloaded_files()
    new_files = list()
    for file in all_files:
        new_f = new_fname(file['title'])
        if new_f is None:
            continue
        new_f_index = new_f.split("_")[0]
        if new_f_index not in downloaded_files:
            f1 = file
            f1['new_f'] = new_f
            new_files.append(f1)

    print("Already downloaded files...")
    print(downloaded_files)

    print()
    if len(new_files) == 0:
        print("No new files to download")
    else:
        print("New files to download")
        for f in new_files:
            print(f)

    return new_files


def download_files(files_dict):
    failed_files = set()
    failed_audio_files = set()
    for item in files_dict:
        print("Downloading %s..." % item['title'])
        f = new_fname(item['title'])
        video = os.path.join(src_video, f) + ".mp4"
        audio = os.path.join(src_audio, f) + ".mp3"

        # download video
        if not yt.download_video(item['video_id'], video):
            failed_files.add([item['title'], item['video_id']])

        track_num = int(os.path.basename(audio).split("_")[0])

        # convert to audio
        audio_utils.video_to_audio(video, audio, replace=True)
        audio_utils.add_metadata(audio, album, artist,
                                 album_artist, album_art_file, track_num=track_num)

    if len(failed_files) > 0:
        print("Failed to download files: %s" % str(failed_files))
    if len(failed_audio_files) > 0:
        print("Failed to convert files: %s" % str(failed_audio_files))


def isint(s):
    try:
        b = int(s)
    except:
        return False
    return True


files = get_files()
download_files(files)
