"""
This file is a template to be used for downloading youtube videos from:
http://www.vitragvani.com/pujya-gurudevshree/Video-Pravachans-(Photo-Slide-Show-with-Subtitle).aspx

Modify this file according to the type of Pravachan being downloaded. For example,
the parsing logic, determining the gatha/kalash/shlok logic etc.
"""
import os
from utils import youtube_utils

target_dir = "%s/aadhyatm/D/Samaysaar (19th time)" % os.getenv("HOME")
tmp_dir = "%s/tmp" % os.getenv("HOME")
html_file = "%s/samaysaar.html" % tmp_dir

# create directory if it doesn't exist
if not os.path.exists(target_dir):
    os.makedirs(target_dir)

start_index = -1
end_index = 10000

indices = []

def get_links():
    fh = open(html_file, "r")
    s = fh.read()
    s = s.strip()
    fh.close()

    splt = s.split("</tr>")
    for arr in splt:
        if len(arr) == 0:
            continue
        sp = arr.split("</td>")
        index_str = sp[0].split(">")[-1]
        try:
            index = int(index_str)
            if len(indices) > 0:
                if index not in indices:
                    continue
            if index < start_index:
                continue
            if index > end_index:
                continue
            index = "%03d" % index
        except:
            index = index_str
        lang = sp[3].split(">")[-1]
        if "Guj" in lang:
            lang = "Guj"
        else:
            lang = "Hin"
        gatha = sp[2].split(">")[1]
        gatha = gatha.replace(" ", "")
        gatha = gatha.lower()

        g_splt = gatha.split(",")
        g = ""
        k = ""
        if len(g_splt) > 1:
            g = g_splt[0]
            k = g_splt[1]
        else:
            if "kalash" in g_splt[0]:
                k = g_splt[0]
            else:
                g = g_splt[0]            

        k = k.replace("kalash", "")
        k = k.replace(".", "")

        yt_link = sp[6].split("href=\"")[1].split("\"")[0]
        video_id = yt_link.split("/")[-1]
        fname = "%s_%s" % (index, lang)
        if len(g) > 0:
            fname = "%s_G%s" % (fname, g)
        if len(k) > 0:
            fname = "%s_K%s" % (fname, k)
        
        fname = "%s.mp4" % (fname)
        print("%s - %s" % (fname, video_id))

        final_fname = os.path.join(target_dir, fname)
        youtube_utils.download_video(video_id, final_fname)

get_links()