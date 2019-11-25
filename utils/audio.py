import os
import subprocess
import time

import eyed3

# Adds metadata to the mp3 file
def add_metadata(target_f, album, artist, album_artist, album_art_file, genre="Pravachan"):
    print("Adding metadata for file %s" % os.path.basename(target_f))
    track_num_str = os.path.basename(target_f).split("_")[0]
    try:
        track_num = int(track_num_str)
    except:
        track_num = int(track_num_str.split("-")[0])
    # set file metadata

    audio = eyed3.load(target_f)

    if audio.tag is None:
        audio.initTag()
    
    audio.tag.images.set(3, open(album_art_file, 'rb').read(), 'image/jpg')
    audio.tag.artist = artist
    audio.tag.album_artist = album_artist
    audio.tag.album = album
    audio.tag.composer = album_artist
    audio.tag.track_num = (track_num, 0)
    audio.tag.genre = genre
    audio.tag.save()

def video_to_audio(video_file, audio_file, replace=False):
    if os.path.isfile(audio_file):
        if replace:
            print("Skipping %s as it already exists" % audio_file)
            return False
        os.remove(audio_file)
    start = time.time()
    if os.path.exists("audiodump.wav"):
        os.remove("audiodump.wav")
    print("Converting %s to audio %s" % (os.path.basename(video_file), os.path.basename(audio_file)))
    proc = subprocess.Popen(["mplayer", "-novideo", "-nocorrect-pts", "-ao", "pcm:waveheader", video_file],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    proc1 = subprocess.Popen(["lame", "-v", "audiodump.wav", audio_file],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc1.communicate()
    os.remove("audiodump.wav")

    end = time.time()
    print("Converting to audio took %.2f seconds" % (end - start))
    return True
