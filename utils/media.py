import os
import time
import shutil
import sys
import sox
import webvtt
import pysubs2
from pysubs2 import Color, Alignment

from utils import utils

if sys.version_info[0] >= 3:
    from urllib.request import urlopen
elif sys.version_info[0] < 3:
    from urllib import urlopen

from google.cloud import speech

from mutagen.mp3 import EasyMP3, MP3
from mutagen.id3 import APIC, ID3, TIT2, TALB, TPE1, TCON, TPE2

TMP_DIR = "%s/tmp" % (os.getenv("HOME"))

def add_mp3_metadata(
        file_path: str,
        title: str,
        artist: str,  # Added artist field
        album: str,
        album_artist: str,
        genre: str,
        album_art_path: str = None
):
    """
    Adds metadata (title, artist, album, album artist, genre, and album art) to an MP3 file.

    Args:
        file_path (str): The path to the MP3 file.
        title (str): The title of the song.
        artist (str): The artist(s) of the specific track.
        album (str): The album name.
        album_artist (str): The album artist (main artist for the entire album).
        genre (str): The genre of the song.
        album_art_path (str, optional): The path to the album art image file (e.g., JPG, PNG).
                                        Defaults to None.
    """
    try:
        # Load the MP3 file
        audio = MP3(file_path, ID3=ID3)

        # Add ID3 tag if not present
        try:
            audio.delete()
            audio.add_tags()
        except:
            audio.add_tags()

        # Set the metadata fields
        audio.tags.add(TIT2(encoding=3, text=[title]))          # Title
        audio.tags.add(TPE1(encoding=3, text=[artist]))         # Artist (performer of the track)
        audio.tags.add(TALB(encoding=3, text=[album]))          # Album
        audio.tags.add(TPE2(encoding=3, text=[album_artist]))   # Album Artist (main artist for the album)
        audio.tags.add(TCON(encoding=3, text=[genre]))          # Genre

        # Add album art if a path is provided
        if album_art_path and os.path.exists(album_art_path):
            try:
                # Determine the MIME type of the image
                mime_type = "image/jpeg" if album_art_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
                with open(album_art_path, 'rb') as album_art_file:
                    audio.tags.add(
                        APIC(
                            encoding=3,         # UTF-8
                            mime=mime_type,     # image/jpeg or image/png
                            type=3,             # 3 is for Front Cover
                            desc=u'Cover',
                            data=album_art_file.read()
                        )
                    )
                print(f"Album art '{album_art_path}' added successfully.")
            except Exception as e:
                print(f"Error adding album art: {e}")
        elif album_art_path:
            print(f"Warning: Album art file not found at '{album_art_path}'. Skipping album art.")

        # Save the changes to the MP3 file
        audio.save()
        print(f"Metadata successfully added to '{file_path}'.")

    except FileNotFoundError:
        print(f"Error: MP3 file not found at '{file_path}'.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


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
    print("Converting to video took %.2f seconds" % (end - start))
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


def convert_video(input_video, output_video, res,
                  replace=False):
    """
    This is to convert a video to a H265 format using handbrake. This can be used
    to later combine two videos from YouTube which may not necessarily be in the same
    format leading to problems in combining them.
    """
    if res not in ["1080", "720", "480"]:
        print("res should be one of 1080, 720, 480")
        sys.exit(1)
    print("Converting video %s to %s using res %s" % (input_video, output_video, res))
    cmd = ["HandBrakeCLI"]
    preset = "Fast %sp30" % res

    if replace:
        fname = os.path.basename(input_video)
        output_video = "%s/%s" % (TMP_DIR, fname)

    cmd += ["-Z", preset,
            "-i", input_video,
            "-o", output_video]
    ret = utils.run_shell_cmd_proc(cmd, hide_output=False)

    if ret and replace:
        shutil.move(output_video, input_video)

    return True

def add_subtitles(input_video, subtitles_file, video_final):
    print("Adding subtitles %s to video %s" % (subtitles_file, input_video))
    cmd = [
        "ffmpeg", "-i", input_video, "-vf", "ass=%s" % subtitles_file, video_final]
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


def sbv_to_txt(input_file, output_file=None):
    if output_file is None:
        if input_file.endswith("sbv"):
            output_file = input_file.replace('.sbv', '.txt')
        if input_file.endswith("srt"):
            output_file = input_file.replace('.srt', '.txt')
        if input_file.endswith("vtt"):
            output_file = input_file.replace(".vtt", ".txt")

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

def vtt_to_ass(vtt_file, ass_file, font_name="Eczar", font_size=24,
               bg_color=(0, 0, 0, 128), fg_color=(255, 255, 255)):
    """
    Converts a VTT subtitle file to an ASS subtitle file with custom styling.

    Args:
        vtt_file (str): Path to the input VTT file.
        ass_file (str): Path to the output ASS file.
        font_name (str): Name of the font to use in the ASS file.
        font_size (int): Font size for the subtitles.
        bg_color (tuple): Background color as (red, green, blue, alpha) - integers 0-255.
        fg_color (tuple): Foreground color as (red, green, blue) - integers 0-255.
    """
    try:
        # Load the VTT file
        captions = webvtt.read(vtt_file)

        # Create a new SubRipFile object for ASS
        subs = pysubs2.SSAFile()

        # Set default style
        style = pysubs2.SSAStyle(
            fontname=font_name,
            fontsize=font_size,
            primarycolor=Color(fg_color[2], fg_color[1], fg_color[0], 0),  # ASS uses BGR
            secondarycolor=Color(fg_color[2], fg_color[1], fg_color[0], 0),
            outlinecolor=Color(0, 0, 0, 0),  # Optional outline
            backcolor=Color(bg_color[2], bg_color[1], bg_color[0], bg_color[3]), # ASS uses BGR with alpha
            borderstyle=4,  # 1=Outline + opaque box, 3=Opaque box only
            outline=1,      # Outline width
            shadow=0,       # Shadow depth
            alignment=Alignment.BOTTOM_CENTER,    # 2=Bottom center
            marginl=10,
            marginr=10,
            marginv=10,
            bold=False,
            italic=False,
            underline=False,
            strikeout=False,
            scalex=100,
            scaley=100,
            spacing=0,
            angle=0,
        )
        subs.styles["Default"] = style

        # Convert VTT cues to ASS events
        for caption in captions:
            start_ms = int(caption.start_in_seconds * 1000)
            end_ms = int(caption.end_in_seconds * 1000)
            text = caption.text.replace("\n", "\\N")  # Use \N for newlines in ASS

            event = pysubs2.SSAEvent(start=start_ms, end=end_ms, text=text, style="Default")
            subs.events.append(event)

        # Save the subtitles to an ASS file
        subs.save(ass_file)
        print(f"Successfully converted '{vtt_file}' to '{ass_file}' with custom styling.")

    except FileNotFoundError:
        print(f"Error: Input VTT file '{vtt_file}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

def srt_to_txt(input_file, output_file=None):
    """
    Converts an SRT subtitle file to plain text using pysubs2 library.
    This properly handles SRT format and avoids duplicates.

    Args:
        input_file (str): Path to the input SRT file
        output_file (str, optional): Path to the output TXT file.
                                     If None, replaces .srt with .txt
    """
    if output_file is None:
        output_file = input_file.replace('.srt', '.txt')

    print("Converting SRT file %s to text file %s" % (input_file, output_file))

    try:
        # Load the SRT file using pysubs2
        subs = pysubs2.load(input_file)

        # Extract text from all subtitle events
        text_lines = []
        for line in subs:
            # Get the text and remove any formatting tags
            text = line.text.strip()
            if text:  # Only add non-empty lines
                text_lines.append(text)

        # Join all text with spaces
        output_text = ' '.join(text_lines)

        # Write to output file
        with open(output_file, 'w', encoding='utf-8') as fh:
            fh.write(output_text)

        print("Successfully converted to %s" % output_file)
        return True

    except Exception as e:
        print("Error converting SRT to TXT: %s" % str(e))
        return False

def convert_mono_audio_to_stereo(input_file, output_file=None):
    replace = False
    if output_file is None:
        output_file = "%s/%s.mp3" % (TMP_DIR, "tmp_audio")
        replace = True

    cmd = [
        "ffmpeg", "-i", input_file, "-ac", "2", "-af",
        "pan=stereo|c0=c0|c1=c0", output_file
    ]

    utils.run_shell_command(cmd)
    if replace:
        shutil.move(output_file, input_file)