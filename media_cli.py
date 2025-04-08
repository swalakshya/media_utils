import argparse
from utils import media

def sbv_to_txt(input_file, output_file):
    media.sbv_to_txt(input_file, output_file)

def main(args):
    if args.command == "sbv_to_txt":
        sbv_to_txt(args.input_file, args.output_file)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Media Utilities")

    sub_parsers = parser.add_subparsers(help="cli help", dest="command")

    sbv_txt = sub_parsers.add_parser('sbv_to_txt', help="Convert subtitle file into txt file")
    sbv_txt.add_argument("--input_file", "-i", type=str, help="Input Subtitle File", required=True)
    sbv_txt.add_argument("--output_file", "-o", type=str, help="Output Text File", required=False)

    args = parser.parse_args()

    main(args)
