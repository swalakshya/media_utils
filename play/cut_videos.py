#!/usr/bin/env python
import os
import pathlib
from utils import media

csv_file = '/Users/rajatj/Adhyatm Work/Tattvarta Sutra/list.txt'
base_folder = '/Users/rajatj/jain9.rajat@gmail.com - Google Drive/My Drive/Jainism/Pravachan/Rishabh Ji/Tattvartha Sutra/'
file_indices = dict()

def get_all_files():
    f = pathlib.Path(base_folder)
    files = list()
    for file in list(f.rglob("*.mp4")):
        files.append(str(file))
    files.sort()
    for f in files:
        fname = os.path.basename(f)
        index = int(fname.split(".")[0].split("_")[0])
        file_indices[index] = f

def process(line):
    l = line.split(',')
    if len(l) <= 1:
        print("Skipping %s" % line)
        return
    index = -1
    try:
        index = int(l[0])
    except:
        return
    print("Processing %s" % line)
    start = None
    end = None
    if l[1]:
        start = l[1]
    if l[2]:
        end = l[2]
    fname = file_indices[index]
    media.trim_media(fname, start, end, dry=False)

def main():
    get_all_files()
    fh = open(csv_file, 'r')
    for line in fh.readlines():
        process(line.strip())

if __name__ == '__main__':
    main()