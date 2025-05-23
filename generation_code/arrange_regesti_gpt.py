
import os
import sys
import json
from pathlib import Path
from argparse import ArgumentParser


PROMPT_TEMPLATE = (
    "The following is a list of text lines that together compose a series of full texts"
    ", with their regesto (summary) and apparatus (few info). I need you to collect together "
    "each full text with its regesto and apparatus. Rewrite all the text and do not omit any part of it."
    "Particulary put together all the lines that are part of the same full text then those of its regesto and finally of the apparatus."
    "One after the other collect all the triplets of full text, regesto and apparatus."
    "Use the following format:\n\n"
    "Triple 1:"
    "Full text:\n\n"
    "Regesto:\n\n"
    "Apparatus:\n\n"
    "Triple 2:"
    "Full text:\n\n"
    "Regesto:\n\n"
    "Apparatus:\n\n"
    "and so on.\n\n\n\n"
    "Lines list:\n\n"
)

def load_lines(file):
    lines = []
    with open(file, "r") as f:
        for line in f:
            lines.append(line.strip())
    return lines

def main(args):

    dataset_dir = Path(args.dataset_name)
    clean_dataset_name = "__".join(args.dataset_name.split("/"))
    if clean_dataset_name.endswith("__"):
        clean_dataset_name = clean_dataset_name[:-2]
    outfile = Path(f"batch_arrange_regesto_{clean_dataset_name}.jsonl")

    with open(outfile, "w") as jf:
        for _file in dataset_dir.glob("*.txt"):
            lines = load_lines(_file)

            prompt = PROMPT_TEMPLATE + "\n".join(lines)
            prompt_dict = [{"role": "user", "content": prompt},]
            request = {
                "custom_id": f"{_file}",
                "method": "POST",
                "url": "/chat/completions",
                "body": {
                    "model": "gpt-4o-2",
                    "messages": prompt_dict,
                    "max_tokens": 16384,
                    "temperature": 0.8,
                }}

            jf.write(json.dumps(request) + "\n")

def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--dataset_name", type=str, required=True)
    return parser.parse_args()

if __name__ == "__main__":
    main(parse_args())
