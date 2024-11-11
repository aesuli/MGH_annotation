import argparse
import json
import os
import re
import zipfile
from statistics import mean

from bs4 import BeautifulSoup

mean_center_page = 0
mean_line_width = 0

MAX_FOOTER_LINES = 15


def process_zip_file(file, first_page, last_page):
    top_margin = 300
    regesta = []
    with (zipfile.ZipFile(file, 'r') as zip_ref):
        last_number = 1
        lines = []
        page_centers = []
        line_widths = []
        for f in zip_ref.namelist():
            # process only page files
            if f == 'METS.xml':
                continue
            else:
                page_number = int(f.split("Page")[1].split(".")[0])
                with zip_ref.open(f) as fp:
                    bs = BeautifulSoup(fp.read().decode(encoding='utf-8'), features='xml')
                    "ciao"
    return regesta

if __name__ == "__main__":
    import sys
    zip_file = sys.argv[1]
    out = process_zip_file(zip_file, 1, 1000)
