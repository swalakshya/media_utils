import os
import subprocess
import time
import shutil
import sys
import sox

if sys.version_info[0] >= 3:
    from urllib.request import urlopen
elif sys.version_info[0] < 3:
    from urllib import quote_plus, quote
    from urllib import urlopen

from mutagen.mp3 import EasyMP3
from mutagen.id3 import APIC, ID3

DEFAULT_PRESET = "H.265\ MKV\ 720p30"

def add_metadata(target_f, album, artist, album_artist, album_art_file,
                  track_num=None, title=None, genre="Pravachan"):
    # Taken from https://www.programcreek.com/python/example/63462/mutagen.mp3.EasyMP3
    # https://github.com/cooperhammond/irs/blob/master/irs/interact/tagger.py

    tags = EasyMP3(target_f)
    # tags["title"] = title
    tags["artist"] = artist
    tags["album"] = album
    tags["albumartist"] = album_artist
    if track_num is not None:
        tags["tracknumber"] = str(track_num)
    if title is not None:
        tags["title"] = title
    tags.save()

    mp3 = EasyMP3(target_f, ID3=ID3)
    try:
        mp3.add_tags()
    except:
        pass

    mp3.tags.add(
        APIC(
            encoding = 3,
            mime = "image/jpg",
            type = 3,
            desc = "cover",
            data = urlopen("file://%s" % album_art_file).read()
        )
    )
    mp3.save()


def remove_metadata(target_f):
    mp3 = EasyMP3(target_f)
    mp3.delete()
    mp3.save()


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
    retcode = proc.returncode
    if retcode != 0:
        return False
    proc1 = subprocess.Popen(["lame", "-v", "audiodump.wav", audio_file],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc1.communicate()
    retcode = proc1.returncode
    if retcode != 0:
        return False
    os.remove("audiodump.wav")

    end = time.time()
    print("Converting to audio took %.2f seconds" % (end - start))
    return True

def trim_media(media_file, start, end):
    print_str = "Trimming the file"
    if start:
        print_str = "%s from %s" % (print_str, start)
    else:
        print_str = "%s from start" % print_str
    if end:
        print_str = "%s to %s" % (print_str, end)
    else:
        print_str = "%s to end" % print_str
    start_time = time.time()
    tmp_dir = "%s/tmp" % os.getenv("HOME")

    if start is None and end is None:
        return
    print(print_str)
    cmd = ["ffmpeg", "-i", media_file]
    if start:
        cmd += ["-ss", start]
    if end:
        cmd += ["-to", end]
    cmd += ["-c", "copy"]
    tmp_file = "%s/tmp.%s" % (tmp_dir, media_file[-3:])
    cmd += [tmp_file]
    print("Trim command: %s" % cmd)
    if os.path.exists(tmp_file):
        os.remove(tmp_file)

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    retcode = proc.returncode
    if retcode != 0:
        return False
    shutil.move(tmp_file, media_file)
    end_time = time.time()
    print("Trimming the file took %.2f seconds" % (end_time - start_time))
    return True

def convert_bitrate(audio, bitrate="160000"):
    audio_out = "tmp_%s" % audio
    cmd = ['sox', audio, '-r', bitrate, audio_out]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    retcode = proc.returncode
    if retcode != 0:
        return False
    shutil.move(audio_out, audio)
    return True

def combine_audio(input_audio_list, audio_final):
    # First change to common bitrate
    for f in input_audio_list:
        convert_bitrate(f)
    cnb = sox.Combiner()
    cnb.convert(samplerate=48000, n_channels=2)
    cnb.build(input_audio_list, audio_final, 'concatenate')

def combine_videos(source_dir, input_video_list, video_final):
    print("Converting videos %s to %s" % (str(input_video_list), video_final))
    # create tmp file
    curr_dir = os.getcwd()
    os.chdir(source_dir)
    fh = open('file.txt', 'w')
    for f in input_video_list:
        fh.write('file %s\n' % f)
    fh.close()
    cmd = [ "ffmpeg", "-f", "concat", "-i", "file.txt", video_final]
    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    proc.communicate()
    retcode = proc.returncode
    os.remove('file.txt')
    if retcode != 0:
        return False
    os.chdir(curr_dir)
    return True

def convert_video(input_video, output_video, preset_name=DEFAULT_PRESET,
                  preset_file=None):
    """
    This is to convert a video to a H265 format using handbrake. This can be used
    to later combine two videos from YouTube which may not necessarily be in the same
    format leading to problems in combining them.
    """
    print("Converting video %s to %s using preset %s" % (input_video, output_video, preset_name))
    cmd = ["HandBrakeCLI"]
    if preset_file:
        cmd +=  ["--preset-import-file", preset_file]
    cmd += ["-Z", preset_name,
            "-i", input_video,
            "-o", output_video]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    retcode = proc.returncode
    if retcode != 0:
        return False
    return True
