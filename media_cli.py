import argparse
import os

from utils import media

def sbv_to_txt(input_file, output_file):
    media.sbv_to_txt(input_file, output_file)

def download_subtitles(yt_id, output_folder, subs_format, lang, is_auto):
    media.download_subtitles(yt_id, output_folder,
                             sub_format=subs_format,
                             lang=lang,
                             auto_gen=is_auto)


def main(parser_args):
    if parser_args.command == "sbv_to_txt":
        sbv_to_txt(parser_args.input_file, parser_args.output_file)

    elif parser_args.command == "subtitles":
        download_subtitles(
            parser_args.id, parser_args.output_folder, parser_args.format,
            parser_args.lang, parser_args.auto)


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

    args = parser.parse_args()

    main(args)
