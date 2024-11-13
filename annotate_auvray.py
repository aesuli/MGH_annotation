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
SKIPPED_PAGES = [13]

def check_maybe_number(string, page_width):
    hpos = int(string['HPOS'])
    vpos = int(string['VPOS'])
    width = int(string['WIDTH'])
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
        .replace("12337).", "1232.")
        .replace("nx7.", "1227.")
    )
    if "122" in content:
        content = re.sub(r"—$", "", content).strip()

    # check if the line is on the left or right
    line_type = "left" if hpos < page_width // 2 else "right"

    # determine if it could be a regesto number (remove periods)
    is_maybe_number = any([
        # re.match(r'\d+', content),
        re.search(r'1\d{3}\.[])]*$', content),
        re.search(r'1\d{3} f\.[])]*$', content),
        re.search(r'1227$', content),
        # 500 < width < 1000,
    ])

    if is_maybe_number:
        if re.match(r"I{1,3}\.", content):
            is_maybe_number = False


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
                print(f"PAGE N. {page_number}")
                if page_number in SKIPPED_PAGES:
                    continue
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

                    # if len(starts["left"]) < 3 or len(starts["right"]) < 3:
                    #     continue

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
                            next_string = tls[idx + 1].find_next('String')
                            next_content = next_string["CONTENT"]
                            if any([
                                "«" in next_content[:6],
                                re.match("I{1,3}\.", next_content),
                                re.match(r"IV\.", next_content),
                                re.match(r"V\.", next_content),
                            ]):
                                continue

                            regesta.append((last_number, lines, content))
                            last_number = last_number + 1
                            lines = {"left": [], "right": [], "all": []}

                        else:
                            # anything else is content of the current regesto
                            lines[line_type].append(string)
                            lines["all"].append(string)

                    for line_type in ["left", "right", "all"]:
                        _lines = lines[line_type]
                        page_ids = [idx for i in _lines if isinstance(i, str)]
                        page_n = None
                        if len(page_ids) > 0:
                            page_n = _lines.pop(page_ids[0])[5:]
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
                            # new_page_number = f'PAGE {page_number}'
                            # if page_n is not None:
                            #     new_page_number += ' ' + page_n
                            # _lines.append(new_page_number)
                            # lines["all"].append(new_page_number)

                    # idx_to_pop = []
                    # for idx, line in enumerate(lines["all"]):
                    #     if line not in lines["left"] and line not in lines["right"]:
                    #         idx_to_pop.append(idx)

                    # for idx in idx_to_pop[::-1]:
                    #     lines["all"].pop(idx)


            if page_number >= last_page:
                break


    return regesta

def split_in_test_and_regesto(tls):
    split_idx = len(tls)
    for idx in range(1, len(tls)):
        c_content = tls[idx]["CONTENT"]
        n_content = tls[idx + 1]["CONTENT"] if idx < len(tls) - 1 else None
        first_word = tls[0]["CONTENT"].split(" ")[0].lower()
        all_fs = re.findall(r" f\.", c_content)
        if c_content.startswith("«") or c_content.startswith(".."):
            if not c_content.startswith("«.,"): # per un regesto specifico
                split_idx = idx
                break
        if len(all_fs) >= 1:
            split_idx = idx + 1
            if n_content is not None and ")" in n_content:
                split_idx = idx + 2
            break
        if n_content is not None and len(all_fs) == 1 and re.search(r"re[gcqo](est)?\.", n_content.lower()):
            split_idx = idx + 1
            break
        if re.search(r"re[gcqo](est)?\.", c_content.lower()):
            if any(w.lower() == first_word for w in c_content.split(" ")):
                split_idx = idx + 1
                break
    return tls[:split_idx], tls[split_idx:]

if __name__ == "__main__":
    import sys
    zip_file = sys.argv[1]
    regesta = process_zip_file(zip_file, 1, 2000)

    multi_reg = {}
    for sample in regesta:
        js = []
        for j in sample[1]["all"]:
            if isinstance(j, str):
                continue
            if re.search(r"re[gcqo](est)?\.", j["CONTENT"].lower()):
                js.append(j)
        if len(js) > 1:
            multi_reg[sample[0]] = sample[1]["all"]
    missing_reg = {i[0]:i[1]["all"] for i in regesta if not any(re.search(r"re[gcqo](est)?\.", j["CONTENT"].lower() if not isinstance(j, str) else j) for j in i[1]["all"])}

    regesta = [(i[0], [j for j in i[1]["all"]], i[2]) for i in regesta if i[0] not in multi_reg.keys() and i[0] not in missing_reg.keys()]

    regesta = [(i[0], split_in_test_and_regesto(i[1]), i[2]) for i in regesta]

    out_strings = [
        {
            "numero": i,
            "header": "" if idx == 0 else regesta[idx - 1][2],
            "regesto": [l["CONTENT"] if not isinstance(l, str) else l for l in c[0]],
            "testo_esteso": [l["CONTENT"] if not isinstance(l, str) else l for l in c[1]],
            "apparato":None
        }
        for idx, (i, c, h) in enumerate(regesta) if i not in multi_reg and i not in missing_reg]

    with open("test_output.json", 'w') as jf:
        json.dump(out_strings, jf, indent=4)
        # for line_out in out_strings:
        #     jf.write(json.dumps(line_out) + "\n")
