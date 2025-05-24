import argparse
import json
import os
import re
import zipfile
from statistics import mean
from pathlib import Path

from bs4 import BeautifulSoup

FULL_REGESTA_NUMBERS = {
    "1a": {"pages": 321, "regesta": 1113}, "1b": {"pages": 320, "regesta":1366},
    "2a": {"pages": 256, "regesta": 922}, "2b": {"pages": 256, "regesta": 1384},
    "3a": {"pages": 153, "regesta": 488}, "3b": {"pages": 153, "regesta": 900},
}

mean_center_page = 0
mean_line_width = 0

MAX_FOOTER_LINES = 15
SKIPPED_PAGES = [13]

french_months = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]


def check_maybe_number(string, page_width):
    hpos = int(string['HPOS'])
    vpos = int(string['VPOS'])
    width = int(string['WIDTH'])
    # fix many ocr mistakes, some make sense some are just random
    content = (
        string["CONTENT"].strip()
        .replace("I27.)", "1227.")
        .replace("I2al.", "1231.")
        .replace("I2a7.", "1227.")
        .replace("mxi]", "1227.")
        .replace("Im7.", "1227.")
        .replace("1811.)", "181].")
        .replace("1228,", "1228.")
        .replace("12297)", "1229")
        .replace("1229), 1", "1229.")
        .replace('1229]".', "1229.")
        .replace("1229l.", "1229.")
        .replace('40.)', "1240.")
        .replace("f227. —", "1227.")
        .replace("172.)", "1227.")
        .replace("122s. —", "1227.")
        .replace("1228 1]", "1228.")
        .replace("1228 1.", "1228.")
        .replace("1229] :.", "1229.")
        .replace("Im29]t.", "1229.")
        .replace("fI2gol", "1230.")
        .replace("¡Ia3ol", "1230.")
        .replace("1230.) —", "1230.")
        .replace("prasol.)", "1230.")
        .replace("1230 t.]", "1231.")
        # .replace("1231.)", "1231.")
        .replace("123l.)", "1231.")
        .replace("123l. —", "1231.")
        .replace("1230).", "1231.")
        .replace("1231,", "1231.")
        .replace("1231.—", "1231.")
        .replace("1231.1", "1231.")
        .replace("tait.", "1231.")
        .replace("f23t.'", "1231.")
        .replace("1231f.", "1232.")
        .replace("1233. —", "1232.")
        .replace("12337).", "1233.")
        .replace("nx7.", "1227.")
    )

    # remove trailing dashes
    if "122" in content:
        content = re.sub(r"—$", "", content).strip()

    # check if the line is on the left or right
    line_type = "left" if hpos < (page_width // 2 - 150) else "right"

    # determine if it could be a regesto header
    is_maybe_number = any([
        re.search(r"1\d{3} ?\.[])]*$", content),
        re.search(r"1\d{3} f\.[])]*$", content),
        # re.search(r"1227$", content),
        re.search(r"^\d{4}", content),
        # any(m in content for m in french_months),
    ])

    return {
        "hpos": hpos,
        "vpos": vpos,
        "width": width,
        "content": content,
        "line_type": line_type,
        "is_maybe_number": is_maybe_number,
    }


def process_zip_file(file, first_page, last_page):
    top_margin = 300
    regesta = []
    with (zipfile.ZipFile(file, 'r') as zip_ref):
        last_number = 0
        lines = []

        for f in zip_ref.namelist():
            # process only page files
            if f == 'METS.xml':
                continue
            else:

                with zip_ref.open(f) as fp:
                    bs = BeautifulSoup(fp.read().decode(
                        encoding='utf-8'), features='xml')

                    tls = bs.find_all('TextLine')
                    for tl in tls:
                        string = tl.find_next("String")
                        lines.append(string["CONTENT"])
                        tagref = string['TAGREFS'] if "TAGREFS" in string else None

    return lines


if __name__ == "__main__":
    import sys
    n_pages = 2000
    zip_file = sys.argv[1]
    if len(sys.argv) > 2:
        n_pages = int(sys.argv[2])

    processed_zip_file = process_zip_file(zip_file, 1, n_pages)
    print(processed_zip_file)

    out_dir = Path(f"lines_{zip_file.split('/')[-1].replace('.zip', '')}")
    out_dir.mkdir(exist_ok=True)
    count = 0
    file_count = 0
    f = open(out_dir / f"file_{file_count}.txt", "w")

    for id, line in enumerate(processed_zip_file):
        f.write(line + "\n")
        if (id + 1) % 200 == 0:
            f.close()
            file_count += 1
            f = open(out_dir / f"file_{file_count}.txt", "w")
