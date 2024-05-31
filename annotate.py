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
            if f != 'METS.xml':
                page_number = int(f.split('_')[3].split('.')[0])
                if page_number < first_page:
                    continue
                with zip_ref.open(f) as fp:
                    bs = BeautifulSoup(fp.read().decode(encoding='utf-8'), features='xml')
                    # get all the content blocks
                    tls = bs.find_all('TextLine')

                    # determine page center and main line width
                    # to successively filter out non-relevant content
                    starts = []
                    ends = []
                    widths = []
                    for tl in tls:
                        string = tl.find_next('String')
                        hpos = int(string['HPOS'])
                        width = int(string['WIDTH'])
                        if width > 1500:
                            starts.append(hpos)
                            widths.append(width)
                            ends.append(hpos + width)
                    line_width = mean(widths)
                    page_center = (mean(ends) + mean(starts)) // 2

                    # determine a book-global center and line width
                    page_centers.append(page_center)
                    line_widths.append(line_width)

                    for tl in tls:
                        # segment info
                        string = tl.find_next('String')
                        hpos = int(string['HPOS'])
                        vpos = int(string['VPOS'])
                        width = int(string['WIDTH'])
                        content = string["CONTENT"]

                        # determine if it is just a number (remove periods)
                        is_number = 0
                        try:
                            is_number = int(content.replace('.', ''))
                        except:
                            pass

                        if hpos > (page_center + line_width / 2) and width < line_width / 2:
                            # remove if it is too on the right and short
                            continue
                        elif hpos < (page_center - line_width * 1.05 / 2) and width < line_width / 2:
                            # remove if it is too on the left and short
                            continue
                        elif vpos < top_margin and width < line_width / 2:
                            # remove if it is high and short
                            continue
                        elif is_number and abs(hpos - page_center) < line_width / 5:
                            # if it is a number and it is centered, then it is a regesto number
                            # save the lines accumulated till now as the previous regesto
                            regesta.append((last_number, lines))
                            last_number = is_number
                            lines = []
                        else:
                            # anything else is content of the current regesto
                            lines.append(string)

                    # when we reach the end of a page we remove any eventual footnote
                    idx = len(lines) - 1
                    remove = -1
                    while idx >= 0:
                        content = lines[idx]['CONTENT']
                        width = lines[idx]['WIDTH']
                        hpos = lines[idx]['HPOS']

                        if content[:5].count(')') > 0:
                            # footnotes likely have a ) at the very beginning
                            remove = idx

                        if content.startswith('"') or content.startswith('9') or content.startswith('REG.'):
                            # other chars footnotes likely start with
                            remove = idx

                        idx -= 1
                        if len(lines) - idx > MAX_FOOTER_LINES:
                            # do not go too much up in the page
                            break
                    if remove >= 0:
                        lines = lines[:remove]

                    lines.append(f'PAGE {page_number}')
            if page_number >= last_page:
                break

        # determine a book-global center and line width
        global mean_line_width
        mean_line_width = mean(line_widths)
        global mean_center_page
        mean_center_page = mean(page_centers)
    return regesta


def extract_text(lines):
    text = []
    for line in lines:
        if type(line) == str and line.startswith('PAGE'):
            continue
        text.append(line['CONTENT'])
    return text


REGESTO = 'regesto'
APPARATO = 'apparato'
TESTO_ESTESO = 'testo esteso'


def annotate(regesta):
    annotated = []
    for id, lines in regesta:
        # split the lines defining an entry in regesto, apparato, and testo esteso
        # three states and simple heuristics
        entry = {}
        entry['numero'] = id
        state = REGESTO
        apparato_start = 0
        last_height = 0
        for i, line in enumerate(lines):
            if type(line) == str and line.startswith('PAGE'):
                continue
            hpos = int(line['HPOS'])
            vpos = int(line['VPOS'])
            width = int(line['WIDTH'])
            height = int(line['HEIGHT'])
            content = line['CONTENT']
            if state == REGESTO and hpos > 1200:
                # a segment of text aligned to the right is the date at the end of the regesto
                entry[REGESTO] = extract_text(lines[:i + 1])
                state = APPARATO
                last_vpos = vpos
                apparato_start = i + 1
            elif state == APPARATO:
                delta_vpos = vpos - last_height - last_vpos
                if (delta_vpos > 0 and i != apparato_start) or len(re.findall('[0-9]', content)) == 0:
                    # a vertical gap, or a line with no digits, marks the beginning of testo esteso
                    entry[APPARATO] = extract_text(lines[apparato_start:i])
                    entry[TESTO_ESTESO] = extract_text(lines[i:])
                    state = TESTO_ESTESO
                    break
                last_vpos = vpos
            last_height = height
        if state == REGESTO:
            # no apparato found, typically because the date at the end of the
            # regesto is merged with the last line of the main regesto text
            # backup heuristic
            for i, line in enumerate(lines):
                if type(line) == str and line.startswith('PAGE'):
                    continue
                hpos = int(line['HPOS'])
                vpos = int(line['VPOS'])
                width = int(line['WIDTH'])
                if state == REGESTO and hpos + width < mean_center_page * 1.2:
                    # the first short line in this case likely belongs to apparato
                    entry[REGESTO] = extract_text(lines[:i])
                    state = APPARATO
                    last_vpos = vpos
                    apparato_start = i
                elif state == APPARATO:
                    # once apparato is found, repeat the code to find testo esteso
                    delta_vpos = vpos - last_height - last_vpos
                    if delta_vpos > 0 and i != apparato_start:
                        entry[APPARATO] = extract_text(lines[apparato_start:i])
                        entry[TESTO_ESTESO] = extract_text(lines[i:])
                        state = TESTO_ESTESO
                        break
                    last_vpos = vpos
                last_height = height
        if state == APPARATO:
            # if testo esteso is not found, check again
            for i in range(apparato_start + 1, len(lines) - apparato_start):
                if type(lines[i]) != str:
                    hpos = int(lines[i]['HPOS'])
                    width = int(lines[i]['WIDTH'])
                    if abs(hpos + width / 2 - mean_center_page) < 200:
                        # a centered line is likely the first line of testo esteso
                        break
                else:
                    break
            entry[APPARATO] = extract_text(lines[apparato_start: i])
            entry[TESTO_ESTESO] = extract_text(lines[i:])
        annotated.append(entry)
    return annotated


def refine(annotated):
    # a few effective final refinement
    for entry in annotated:
        if REGESTO in entry and len(entry[REGESTO]) > 2:
            line = entry[REGESTO][-2]
            if len(re.findall('[0-9]', line)) > 2 and line.count('.') > 3:
                # sometimes, when backup heuristic is used to find the apparato,
                # a line of the apparato is placed before the date in the regesto.
                # if the penultimate line of regesto contains numbers and periods
                # this is likely the case
                entry[APPARATO].insert(0, line)
                entry[REGESTO].remove(line)
        if APPARATO in entry:
            while len(entry[APPARATO]) > 0:
                if len(re.findall('[0-9]', entry[APPARATO][-1])) == 0:
                    # all the ending lines in apparato that contain no numbers
                    # belong to testo esteso
                    entry[TESTO_ESTESO].insert(0, entry[APPARATO].pop())
                else:
                    break
        if TESTO_ESTESO in entry and len(entry[TESTO_ESTESO]) == 1:
            # if testo esteso has a single line it means that there
            # is not testo esteso and that line belongs to apparato
            line = entry[TESTO_ESTESO][0]
            del entry[TESTO_ESTESO]
            if APPARATO in entry:
                entry[APPARATO].append(line)
            else:
                entry[APPARATO] = [line]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=str, help='Input zip file or directory containing zip files')
    args = parser.parse_args()

    files = []
    if os.path.isfile(args.input) and args.input.endswith('.zip'):
        files.append(args.input)
    elif os.path.isdir(args.input):
        for file in os.listdir(args.input):
            if file.endswith('.zip'):
                files.append(os.path.join(args.input, file))
    else:
        print("Invalid input. Please specify a zip file or a directory containing zip files.")

    for file in files:
        first_page = None
        last_page = None
        # each MGH volume has its start and end for the section with regesta
        # it is much more practical to state it explicitly than to guess a heuristic
        if 'mgh_1' in file:
            first_page = 20
            last_page = 758
        elif 'mgh_2' in file:
            first_page = 23
            last_page = 586
        elif 'mgh_3' in file:
            first_page = 31
            last_page = 760
        regesta = process_zip_file(file, first_page, last_page)
        annotated = annotate(regesta)
        refine(annotated)
        json_file = file[:-4] + '.json'
        with open(json_file, mode='wt', encoding='utf-8') as outputfile:
            json.dump(annotated, outputfile, indent=2)


# This code is specifically devised to extract a structured annotation out the output
# produced by eScriptorium (in ALTO format) on pdf files of three volumes of
# Monumenta Germaniae Historica: Epistolae Saeculi XIII
if __name__ == '__main__':
    main()
