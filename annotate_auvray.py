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

def check_maybe_number(string, page_width):
    hpos = int(string['HPOS'])
    vpos = int(string['VPOS'])
    width = int(string['WIDTH'])
    content = (
        string["CONTENT"]
        .replace("I27.)", "1227.")
        .replace("I2a7.", "1227.")
        .replace("Im7.", "1227.")
    )

    # check if the line is on the left or right
    line_type = "left" if hpos < page_width // 2 else "right"

    # determine if it could be a regesto number (remove periods)
    is_maybe_number = any([
        # re.match(r'\d+', content),
        re.search(r'1\d{3}\.[])]*$', content),
        # 500 < width < 1000,
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
        lines = {"left": [], "right": [], "all": []}
        page_centers = {"left": [], "right": []}
        line_widths = {"left": [], "right": []}
        for f in zip_ref.namelist():
            # process only page files
            if f == 'METS.xml':
                continue
            else:
                page_number = int(f.split("Page")[1].split(".")[0])
                starts = {"left": [], "right": []}
                widths = {"left": [], "right": []}
                ends = {"left": [], "right": []}
                with zip_ref.open(f) as fp:
                    bs = BeautifulSoup(fp.read().decode(encoding='utf-8'), features='xml')
                    page_height = int(bs.find('Page')['HEIGHT'])
                    page_width = int(bs.find('Page')['WIDTH'])
                    tls = bs.find_all('TextLine')
                    for tl in tls:
                        string = tl.find_next("String")
                        hpos = int(string['HPOS'])
                        width = int(string['WIDTH'])
                        if width > 1000:
                            line_type = "left" if hpos < (page_width // 2 - 300) else "right"
                            starts[line_type].append(hpos)
                            widths[line_type].append(width)
                            ends[line_type].append(hpos + width)

                    if len(starts["left"]) < 3 or len(starts["right"]) < 3:
                        continue

                    line_width = dict()
                    page_center = dict()
                    for line_type in ["left", "right"]:
                        line_width[line_type] = mean(widths[line_type])
                        page_center[line_type] = (mean(ends[line_type]) - mean(starts[line_type])) // 2

                        # determine a book-global center and line width
                        page_centers[line_type].append(page_center[line_type])
                        line_widths[line_type].append(line_width[line_type])

                    for idx, tl in enumerate(tls):

                        # segment info
                        string = tl.find_next('String')
                        out = check_maybe_number(string, page_width)
                        hpos = out["hpos"]
                        vpos = out["vpos"]
                        width = out["width"]
                        content = out["content"]
                        line_type = out["line_type"]
                        is_maybe_number = out["is_maybe_number"]

                        # if width < line_width[line_type] / 2:
                        #     # remove if it is too on the right and short
                        #     continue
                        # elif width < line_width[line_type] / 2:
                        #     # remove if it is too on the left and short
                        #     continue

                        if not is_maybe_number and width < line_width[line_type] / 2:
                            # remove if it is too short
                            continue
                        elif not is_maybe_number and vpos < top_margin and width < line_width[line_type] / 2:
                            # remove if it is high and short
                            continue

                        elif is_maybe_number:
                            # una linea che inizia con un numero e finisce con un anno (4 cifre) e un punto è il numero di un regesto
                            # is_number = is_maybe_number and re.search(r"1\d{3}\.[])]*$", content)
                            # alcune volte l'anno è alla riga successiva
                            # if is_maybe_number and not is_number and idx + 1 < len(tls):
                            #     next_content = tls[idx + 1].find_next('String')["CONTENT"]
                            #     is_number = re.search(r"\d{4}\.[])]?", next_content)
                            # if is_number:
                            # try:
                            #     is_number = int(is_maybe_number.group())
                            # except:
                            #     pass
                            # if it is a number and it is centered, then it is a regesto number
                            # save the lines accumulated till now as the previous regesto
                            regesta.append((last_number, lines))
                            last_number = last_number + 1
                            lines = {"left": [], "right": [], "all": []}

                        else:
                            # anything else is content of the current regesto
                            lines[line_type].append(string)
                            lines["all"].append(string)

                    for line_type in ["left", "right"]:
                        _lines = lines[line_type]
                        page_ids = [idx for i in _lines if isinstance(i, str)]
                        page_n = None
                        if len(page_ids) > 0:
                            page_n = _lines.pop(page_ids[0])[:5]
                        # when we reach the end of a page we remove any eventual footnote
                        idx = len(_lines) - 1
                        remove = -1
                        while idx >= 0:
                            content = _lines[idx]['CONTENT']
                            width = _lines[idx]['WIDTH']
                            hpos = _lines[idx]['HPOS']

                            if content[:5].count(')') > 0:
                                # footnotes likely have a ) at the very beginning
                                remove = idx

                            if content.startswith('"') or content.startswith('9') or content.startswith('REG.'):
                                # other chars footnotes likely start with
                                remove = idx

                            idx -= 1
                            if len(_lines) - idx > MAX_FOOTER_LINES:
                                # do not go too much up in the page
                                break
                        if remove >= 0:
                            _lines = _lines[:remove]
                            new_page_number = f'PAGE {page_number}'
                            if page_n is not None:
                                new_page_number += ' ' + page_n
                            _lines.append(new_page_number)
                            lines["all"].append(new_page_number)

                    # idx_to_pop = []
                    # for idx, line in enumerate(lines["all"]):
                    #     if line not in lines["left"] and line not in lines["right"]:
                    #         idx_to_pop.append(idx)

                    # for idx in idx_to_pop[::-1]:
                    #     lines["all"].pop(idx)


            if page_number >= last_page:
                break


    return regesta

if __name__ == "__main__":
    import sys
    zip_file = sys.argv[1]
    out = process_zip_file(zip_file, 1, 2000)
    with open("test_output.txt", 'w') as jf:
        json.dump(out, jf, indent=4)
