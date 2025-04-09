import argparse
import os
import sys

from utils import media
from utils import youtube_utils

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
        help="Format of subtitles (srt/vtt)"
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

    args = parser.parse_args()

    main(args)
