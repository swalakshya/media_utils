import os
import time
import shutil
import sys
import sox

from utils import utils

if sys.version_info[0] >= 3:
    from urllib.request import urlopen
elif sys.version_info[0] < 3:
    from urllib import urlopen

from google.cloud import speech

from mutagen.mp3 import EasyMP3
from mutagen.id3 import APIC, ID3

DEFAULT_PRESET = "H.264 MKV 480p30"

def download_subtitles(yt_id, output_folder, sub_format="vtt",
                       auto_gen=True, lang="hi"):
    print("Downloading subtitles for ID %s, format %s, lang %s, auto %s in folder %s" %(
        yt_id, sub_format, lang, auto_gen, output_folder
    ))
    if sub_format not in ["vtt", "srt"]:
        print("Incompatible format %s" % (sub_format))
        return False

    command = [ "yt-dlp" ]
    if auto_gen:
        command = command + ["--write-auto-sub", "--no-check-certificate"]

    command = command + [
        "--sub-lang", lang
    ]
    if sub_format == "srt":
        command = command + [
            "--convert-subtitles", sub_format
        ]
    command = command + [
        "--skip-download",
        yt_id
    ]

    curr_dir = os.getcwd()
    os.chdir(output_folder)
    print("Command %s" % ' '.join(command))
    ret = utils.run_shell_command(command)
    if not ret:
        print("Command Failed!")
        sys.exit(1)
    os.chdir(curr_dir)


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
            # encoding = 3,
            mime = "image/jpeg",
            type = 3,
            desc = u'Cover',
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
        if not replace:
            print("Skipping %s as it already exists" % audio_file)
            return False
        os.remove(audio_file)
    start = time.time()
    if os.path.exists("audiodump.wav"):
        os.remove("audiodump.wav")
    print("Converting %s to audio %s" % (os.path.basename(video_file), os.path.basename(audio_file)))
    utils.run_shell_cmd_proc(["mplayer", "-novideo", "-nocorrect-pts", "-ao",
                              "pcm:waveheader", video_file], hide_output=False)
    utils.run_shell_cmd_proc(["lame", "-v", "audiodump.wav", audio_file], hide_output=False)
    os.remove("audiodump.wav")

    end = time.time()
    print("Converting to audio took %.2f seconds" % (end - start))
    return True


def audio_to_video(audio_file, image_file, video_file, replace=False):
    if os.path.isfile(video_file):
        if not replace:
            print("Skipping %s as it already exists" % video_file)
            return False
        os.remove(video_file)

    start = time.time()
    print("Converting audio file %s to video using static image %s" % (audio_file, image_file))
    cmd = ["ffmpeg", "-loop", "1", "-i", image_file, "-i", audio_file,
           "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
           "-pix_fmt", "yuv420p", "-shortest", video_file]
    utils.run_shell_command(cmd, hide_output=False)
    end = time.time()
    print("Converting to vidoe took %.2f seconds" % (end - start))
    return True


def trim_media(media_file, start, end, dry=False):
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
        return True
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
    if not dry:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)

        utils.run_shell_command(cmd)
        shutil.copy(tmp_file, media_file)
        os.remove(tmp_file)
    end_time = time.time()
    print("Trimming the file took %.2f seconds" % (end_time - start_time))
    return True


def convert_bitrate(audio, bitrate="160000"):
    audio_out = "tmp_%s" % audio
    cmd = ['sox', audio, '-r', bitrate, audio_out]

    utils.run_shell_command(cmd)
    shutil.copy(audio_out, audio)
    os.remove(audio_out)
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
    utils.run_shell_command(cmd)
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
    utils.run_shell_cmd_proc(cmd, hide_output=False)
    return True

def add_subtitles(input_video, subtitles_file, video_final, title=None):
    print("Adding subtitles %s to video %s" % (subtitles_file, input_video))
    cmd = [
        "ffmpeg", "-i", input_video, "-i", subtitles_file, "-c", "copy", "-c:s", "mov_text", "-metadata:s:s:0"
    ]
    if title is not None:
        cmd += [ "title=%s" % title]
    cmd += [video_final]
    utils.run_shell_cmd_proc(cmd, hide_output=False)
    return True


# This is Work in Progress
# Do not use it yet!
def audio_to_text(input_audio,
    encoding=speech.RecognitionConfig.AudioEncoding.MP3,
    language='hi'):
    client = speech.SpeechClient()

    with open(input_audio, 'rb') as f:
        audio_content = f.read()

    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(
        encoding=encoding,
        sample_rate_hertz=8000,
        language_code=language,
        use_enhanced=True,
        # A model must be specified to use enhanced model.
        model="phone_call",
    )

    response = client.recognize(config=config, audio=audio)

    for i, result in enumerate(response.results):
        alternative = result.alternatives[0]
        print("-" * 20)
        print(f"First alternative of result {i}")
        print(f"Transcript: {alternative.transcript}")

    return response


"""
def burn_subtitles(input_video, subtitles_file, output_video, title=None,
                   font_name=None, font_size=None, font_colour=None):
    print("Burning subtitles %s to video %s") % (subtitles_file, input_video)

    # Step 1. Convert file to .ass
    if not subtitles_file.endswith("ass"):
        new_subtitles_file =

    # Step 2. Burn the subtitles into the file
"""

def sbv_to_txt(input_file, output_file=None):
    if output_file is None:
        if input_file.endswith("sbv"):
            output_file = input_file.replace('.sbv', '.txt')
        if input_file.endswith("srt"):
            output_file = input_file.replace('.srt', '.txt')

    print("Converting input subtitle file %s into output text file %s" % (
        input_file, output_file
    ))

    output_txt = []
    fh = open(input_file, 'r')
    for line in fh.readlines():
        line = line.strip()
        if ':' in line:
            continue
        # ignore lines which only have numbers in it
        try:
            val = int(line)
            continue
        except ValueError:
            pass
        output_txt.append(line)

    output_str = ' '.join(output_txt)
    output_str = output_str.replace('  ', ' ')

    oh = open(output_file, 'w')
    oh.write(output_str)
    oh.close()
