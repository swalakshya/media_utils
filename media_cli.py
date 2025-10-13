import argparse
import os
import sys

import utils.media
from utils import media
from utils import youtube_utils
from utils.media import add_subtitles


def sbv_to_txt(input_file, output_file):
    media.sbv_to_txt(input_file, output_file)


def download_subtitles(yt_id, output_folder, subs_format, lang, is_auto):
    youtube_utils.download_subtitles(
        yt_id, output_folder,
        sub_format=subs_format,
        lang=lang,
        auto_gen=is_auto)


def transcode_video(
        input_video,
        res, replace_input_file,
        output_file):
    if replace_input_file and output_file is not None:
        print("Either provide --replace OR --output_file. Not both")
        sys.exit(1)

    if not replace_input_file:
        if output_file is None:
            print("Provide output file or flag --replace = True")
            sys.exit(1)
        if os.path.isdir(output_file):
            output_file = "%s/%s" % (output_file, os.path.basename(input_video))
            print("Output file is a folder. New output_file = %s" % output_file)

    media.convert_video(input_video, output_file,
                        res, replace_input_file)


def vtt_to_ass(input_file, output_file):
    if output_file is None:
        output_file = input_file.replace(".vtt", ".ass")

    media.vtt_to_ass(input_file, output_file)

def burn_subtitles(input_file, vtt_file, output_file):
    ass_file = vtt_file.replace(".vtt", ".ass")
    vtt_to_ass(vtt_file, ass_file)
    add_subtitles(input_file, ass_file, output_file)
    os.remove(ass_file)

def audio_to_video(audio, image, video):
    if video is None:
        video = audio.replace(".mp3", ".mp4")
    utils.media.audio_to_video(audio, image, video, replace=True)

def mono_stereo(input_file, output_file=None):
    media.convert_mono_audio_to_stereo(input_file, output_file)

def trim_media_func(input_file, start_time=None, end_time=None):
    media.trim_media(input_file, start_time, end_time)

def video_to_audio_func(
        input_file, output_file,
        album, artist, album_artist, album_art_file,
        title, genre
):
    if not output_file:
        output_file = input_file.replace(".mp4", ".mp3")
        media.video_to_audio(input_file, output_file, replace=True)

    if album is not None and artist is not None and title is not None:
        media.add_mp3_metadata(
            output_file, title, artist, album, album_artist,
            genre, album_art_file
        )

def upload_videos_func(
        folder, playlist_name, credentials_file, language
):
    youtube_utils.upload_videos_to_playlist(
        folder, playlist_name, credentials_file, language
    )

def ocr_pdf_func(file_name, start_page, end_page, language):
    """
    OCR a PDF file to create a searchable PDF using Tesseract.

    Args:
        file_name: Path to input PDF file
        start_page: Starting page number (1-indexed, optional)
        end_page: Ending page number (1-indexed, inclusive, optional)
        language: OCR language code (default: 'hin' for Hindi)
    """
    import tempfile
    from pypdf import PdfReader, PdfWriter
    from pdf_utils.tesseract_ocr import TesseractOCR

    # Validate input file
    if not os.path.exists(file_name):
        print("Error: File not found: %s" % file_name)
        return

    # Generate output filename
    base_name = os.path.splitext(file_name)[0]
    output_file = "%s_searchable.pdf" % base_name

    # Initialize Tesseract OCR
    ocr = TesseractOCR(language=language)

    # Case 1: Process specific page range
    if start_page is not None and end_page is not None:
        print("Processing pages %d to %d..." % (start_page, end_page))

        # Extract specified pages
        reader = PdfReader(file_name)
        total_pages = len(reader.pages)

        # Validate page range
        if start_page < 1 or end_page > total_pages or start_page > end_page:
            print("Error: Invalid page range. PDF has %d pages." % total_pages)
            return

        # Create temporary PDF with extracted pages
        writer = PdfWriter()
        for page_num in range(start_page - 1, end_page):  # Convert to 0-indexed
            writer.add_page(reader.pages[page_num])

        # Save to temporary file
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_pdf_path = temp_pdf.name
        with open(temp_pdf_path, 'wb') as f:
            writer.write(f)

        # Run OCR on temporary PDF
        result = ocr.process_to_searchable_pdf(temp_pdf_path, output_file)

        # Clean up temporary file
        os.remove(temp_pdf_path)

    # Case 2: Process entire PDF
    else:
        print("Processing entire PDF...")
        result = ocr.process_to_searchable_pdf(file_name, output_file)

    # Print result
    if result.success:
        print("\n✓ Success! Searchable PDF created: %s" % output_file)
    else:
        print("\n✗ OCR failed: %s" % result.text_content)


def main(parser_args):
    if parser_args.command == "sbv_to_txt":
        sbv_to_txt(parser_args.input_file, parser_args.output_file)

    elif parser_args.command == "subtitles":
        download_subtitles(
            parser_args.id, parser_args.output_folder, parser_args.format,
            parser_args.lang, parser_args.auto)

    elif parser_args.command == "transcode":
        transcode_video(
            parser_args.input_video,
            parser_args.res, parser_args.replace,
            parser_args.output_file
        )

    elif parser_args.command == "vtt_to_ass":
        vtt_to_ass(parser_args.input_file,
                   parser_args.output_file)

    elif parser_args.command == "burn_subtitles":
        burn_subtitles(
            parser_args.input_file, parser_args.vtt_file,
            parser_args.output_file
        )

    elif parser_args.command == "audio_to_video":
        audio_to_video(
            parser_args.audio, parser_args.image,
            parser_args.output
        )

    elif parser_args.command == "mono_to_stereo":
        mono_stereo(
            parser_args.input_file, parser_args.output_file
        )

    elif parser_args.command == "trim_media":
        trim_media_func(
            parser_args.input_file, parser_args.start_time,
            parser_args.end_time
        )
    elif parser_args.command == "video_to_audio":
        video_to_audio_func(
            parser_args.input_file, parser_args.output_file,
            parser_args.album, parser_args.artist,
            parser_args.album_artist, parser_args.album_art_file,
            parser_args.title, parser_args.genre
        )

    elif parser_args.command == "upload_videos":
        upload_videos_func(
            parser_args.folder, parser_args.playlist,
            parser_args.credentials, parser_args.language
        )

    elif parser_args.command == "ocr_pdf":
        ocr_pdf_func(
            parser_args.file_name, parser_args.start_page,
            parser_args.end_page, parser_args.language
        )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Media Utilities")

    sub_parsers = parser.add_subparsers(help="cli help", dest="command")

    cwd = os.getcwd()

    sbv_txt = sub_parsers.add_parser(
        'sbv_to_txt',
        help="Convert subtitle file into txt file")
    sbv_txt.add_argument(
        "--input_file", "-i",
        type=str, help="Input Subtitle File", required=True)
    sbv_txt.add_argument(
        "--output_file", "-o",
        type=str, help="Output Text File", required=False)

    subtitles = sub_parsers.add_parser(
        'subtitles',
        help="Download subtitles of a youtube video or playlist"
    )
    subtitles.add_argument("--id", type=str,
                           required=True,
                           help="YouTube video/playlist ID")
    subtitles.add_argument(
        "--output_folder", "-o",
        default=cwd,
        help="Output folder where subtitles will be stored"
    )
    subtitles.add_argument(
        "--lang", "-l", default="hi",
        help="Subtitle language"
    )
    subtitles.add_argument(
        "--format", "-f", default="srt",
        help="Format of subtitles (srt/txt)"
    )
    subtitles.add_argument(
        "--auto", "-a", action='store_true',
        help="Download auto generated titles (default false)"
    )

    transcode_vid = sub_parsers.add_parser(
        "transcode",
        help="Transcode Video using Handbrake"
    )
    transcode_vid.add_argument(
        "--input_video", "-i",
        type=str, required=True,
        help="Input File that needs to be transcoded")
    transcode_vid.add_argument(
        "--res", default="1080",
        help="Which format to transcode? (1080/720/480). Default=1080"
    )
    transcode_vid.add_argument(
        "--replace", action="store_true",
        help="Whether to replace the input file itself (default false)"
    )
    transcode_vid.add_argument(
        "--output_file", "-o",
        type=str, help="Output File (or folder)"
    )

    vtt_ass = sub_parsers.add_parser(
        "vtt_to_ass",
        help="Convert vtt to ass file"
    )
    vtt_ass.add_argument(
        "--input_file", "-i", type=str,
        help="Input vtt file"
    )
    vtt_ass.add_argument(
        "--output_file", "-o", type=str,
        help="Output ass file"
    )

    brn_subtitles = sub_parsers.add_parser(
        "burn_subtitles",
        help="Burn subtitles into the video file"
    )

    brn_subtitles.add_argument(
        "--input_file", "-i", type=str,
        help="Input video file")
    brn_subtitles.add_argument(
        "--vtt_file", "-v", type=str,
        help="Subtitles (vtt) file")
    brn_subtitles.add_argument(
        "--output_file", "-o", type=str,
        help="Output video file"
    )

    aud_to_vid = sub_parsers.add_parser(
        "audio_to_video",
        help="Convert audio file to video using a static image file"
    )

    aud_to_vid.add_argument(
        "--audio", "-a", type=str,
        help="Audio file"
    )

    aud_to_vid.add_argument(
        "--image", "-i", type=str,
        help="Image File"
    )

    aud_to_vid.add_argument(
        "--output", "-o", type=str,
        help="Output file path (optional)"
    )

    trans_aud = sub_parsers.add_parser(
        "transcribe_audio",
        help="Generate captions for the audio file"
    )

    # trans_aud.add_argument(
    #     "--input_file", "-i", type=str,
    #     help="Input audio file"
    # )
    # trans_aud.add_argument(
    #     "--language", "-l", type=str,
    #     default="hi", help="Audio language (hi/gu)"
    # )
    # trans_aud.add_argument(
    #     "--output_file", "-o", type=str,
    #     help="Output File"
    # )
    # trans_aud.add_argument(
    #     "--generate_vtt", default=False,
    #     help="Generate vtt file as well?"
    # )

    mono_to_stereo = sub_parsers.add_parser(
        "mono_to_stereo",
        help="Convert a mono-track video/audio file to a stereo file"
    )
    mono_to_stereo.add_argument(
        "--input_file", "-i", type=str,
        help="Input audio/video file"
    )
    mono_to_stereo.add_argument(
        "--output_file", "-o", type=str,
        help="Output audio/video file. If NULL, then the input file will be replaced."
    )

    trim_media_parser = sub_parsers.add_parser(
        "trim_media",
        help="Trim a video/audio file in place"
    )
    trim_media_parser.add_argument(
        "--input_file", "-i", type=str,
        help="Input audio/video file"
    )
    trim_media_parser.add_argument(
        "--start_time", "-s", type=str,
        help="Start time. If none, video is not cut at start"
    )
    trim_media_parser.add_argument(
        "--end-time", "-e", type=str,
        help="End time. If none, video is not at end"
    )

    video_to_audio_parser = sub_parsers.add_parser(
        "video_to_audio",
        help="Extract audio from a video file"
    )
    video_to_audio_parser.add_argument(
        "--input_file", "-i", type=str,
        help="Input video file"
    )
    video_to_audio_parser.add_argument(
        "--output_file", "-o", type=str,
        help="Output audio file. If not provided, will replace the input file with .mp3 extension"
    )
    video_to_audio_parser.add_argument(
        "--album", type=str, default=None,
        help="Album Name"
    )
    video_to_audio_parser.add_argument(
        "--artist", type=str, default=None,
        help="Artist Name"
    )
    video_to_audio_parser.add_argument(
        "--title", type=str, default=None,
        help="Title of the audio file"
    )
    video_to_audio_parser.add_argument(
        "--album_artist", type=str, default=None,
        help="Album Artist Name"
    )
    video_to_audio_parser.add_argument(
        "--album_art_file", type=str, default=None,
        help="Album Art File (image file) to be embedded in the audio file"
    )
    video_to_audio_parser.add_argument(
        "--genre", type=str, default=None,
        help="Genre of the audio file"
    )

    upload_videos_parser = sub_parsers.add_parser(
        "upload_videos",
        help="Upload videos from a folder to YouTube playlist"
    )
    upload_videos_parser.add_argument(
        "--folder", "-f", type=str, required=True,
        help="Folder containing video files to upload"
    )
    upload_videos_parser.add_argument(
        "--playlist", "-p", type=str, required=True,
        help="Name of the YouTube playlist (will be created if doesn't exist)"
    )
    upload_videos_parser.add_argument(
        "--credentials", "-c", type=str, required=True,
        help="Path to OAuth 2.0 credentials JSON file (client_secrets.json)"
    )
    upload_videos_parser.add_argument(
        "--language", "-l", type=str, default="hi",
        help="Video language code (hi=Hindi, gu=Gujarati, en=English, etc.)"
    )

    ocr_pdf_parser = sub_parsers.add_parser(
        "ocr_pdf",
        help="OCR a PDF file to create a searchable PDF using Tesseract"
    )
    ocr_pdf_parser.add_argument(
        "--file_name", "-f", type=str, required=True,
        help="Input PDF file to process"
    )
    ocr_pdf_parser.add_argument(
        "--start_page", "-s", type=int, default=None,
        help="Starting page number (1-indexed, optional)"
    )
    ocr_pdf_parser.add_argument(
        "--end_page", "-e", type=int, default=None,
        help="Ending page number (1-indexed, inclusive, optional)"
    )
    ocr_pdf_parser.add_argument(
        "--language", "-l", type=str, default="hin",
        help="OCR language code (hin=Hindi, guj=Gujarati, eng=English, etc.)"
    )

    args = parser.parse_args()

    main(args)
