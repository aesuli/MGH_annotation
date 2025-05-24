
import os
import sys
import json
from pathlib import Path
from argparse import ArgumentParser


PROMPT_TEMPLATE = """The following is a list of text lines that together compose a series of long texts (letters or descriptions of events), with their regesto (a summary) that usually the regesto should include: the name of the author (i.e. the Pope), the name of the recipient, an abstract of the content (with the object and the operative verb), the date (calculated from the year of pontificate), the place. and apparatus (scholarly information).

I need you to collect together triplets containing each long text (that should not contain the regesto itself) with its regesto and apparatus (in text form without separating the parts that compose it). Rewrite all the text and do not omit any part of it. Particularly put together all the lines that are part of the same long text then those of its regesto and finally the apparatus. One after the other collect all the triplets of full text, regesto and apparatus. You can remove the character '¬' indicating that the text continues on the next line without a white space. You should never translate or add any comment. If occasional characters are out of place you if lines appear to be out of order, you should correct them.

Use the format in the example below:

Triplet 1:

Long text:
Ierosolimitano regi. Magnus Dominus et laudabilis nimis etc. \u2014 Felicis recordationis Innocentio papa predecessore nostro septimodecimo Kal. Augusti, soluto debito carnis, ad regionem sancto\u00ac rum spirituum ut credimus evocato, et sequenti die celebratis exequiis ac cum honore debito collocato ipsius corpore in sepulcro, una cum fratribus nostris ad eligendum convenimus successorem, et die tertio, Spiritus sancti gratia invocata, super hoc tractavimus diligenter, et post tractatum diutinum placuit fratribus universis humeris nostris, quamvis insufficientibus, imponere onus istud. Et licet in primis duxerimus resistendum, ne tamen videremur vocationi divine resistere, submisimus humeros ad portandum sperantes in eo qui linguas infantium facit disertas, quod ipse, qui vota Sap. io\u00e6i. fratrum aspirando prevenit, prosequetur etiam adiuvando. Fiduciam enim talem habemus per Christum ad Deum, non quod sufficientes simus cogitare aliquid a nobis, quasi ex nobis, sed nostra sufficientia est ex Deo, qui nos ad suum ministerium evocavit. Non ergo propter obitum prefati predecessoris nostri consternetur cor tuum neque formidet, quasi propter hoc Terre Sancte impediatur succursus, quoniam, etsi illius sufficientie nostra videatur inferior, ad liberationem tamen ipsius votis non minoribus aspiramus quibus ipse Dominus, qui sperantes in se nullatenus deserit, effectum tribuat et pro-Iudith isu7. fectum, ut quod possibilitas nostra non obtinet, eius nobis gratia largiatur. Serenitatem igitur regiam rogamus attentius et monemus et exhortamur in Domino, quatinus de gratie nostre favore securus, utpote qui ad subventionem terre ipsius tota intendimus voluntate, conforteris in Domino et in potentia virtutis ipsius, ad conservationem terre intendens viriliter et prudenter, preliaturus prelia Domini, cum tempus advenerit 30 opportunum, et ob hoc recepturus ab eo gratiam in presenti et gloriam in futuro. Dat. Perusii, VIII Kal. Aug. pont. nostri anno primo.

Regesto:
EX HONORII III REGISTRO. Honorius III papa (Iohannem) regem Hierosolymitanum certiorem faciens de obitu Innocentii III papae et de sua clectione exhortatur, ut de gratiae suae favore securus confortetur in Domino; se enim ad liberationem Terrae Sanctae votis non minoribus quam praedecessorem suum aspirare. 1216, Tul. 25.

Apparatus:
Hon. III Reg. Lib. I, 1. Edimus e Rayn. Ann. eccl. a. 1216, s 18\u201419. Potthast, Reg. 5317.

Triplet 2:

Full text:
Pragensi episcopo. Quesivisti an seculares canonici minus legitime nati suis sint renuntiare beneficiis compellendi, cum de iure ad sacros nequeant ordines promoveri nec in beneficiis secum fuisse probent a Romano pontifice dispensatum nec ecclesia taliter indigeat ordinatis. Ad quod fraternitati tue taliter respondemus, quod si multitudo est in causa, ut huius\u00ac modi non possint sine scandalo removeri, eos in beneficiis sic susceptis poteris conniventibus oculis tolerare. Explicari preterea postulasti, utrum illis sit licitum qui nec voto nec regulari observantia sunt astricti, carnes comedere, quando in sexta feria dies Dominice nativitatis occurrit. Ad hoc tale damus responsum, quod illi qui nec voto nec regulari observantia sunt astricti, in sexta feria, si festum nativitatis Dominice ipso die venire contigerit, carnibus propter festi excellentiam uti possunt secundum consuetudinem ecclesie generalis, nec tamen ii reprehendendi sunt, qui ob devotionem voluerint abstinere. Dat. Laterani, IV Kal. Novembris, pontificatus nostri anno primo.

Regesto:
Honorius III papa (Andreae) episcopo Pragensi quacrenti de saccularibus canonicis minus legitime natis et de licentia carnes comedendi, quando in sexta feria dies Dominicae nativitatis occurrat, respondet. 1216, Oct. 29.

Apparatus:
Hon. III Reg. Lib. I, 44. Edimus ex Rayn. Ann. eccl. a. 1216, 8 45. Potthast, Reg. 6349.

Lines list:
"""


def load_lines(file):
    lines = []
    with open(file, "r") as f:
        for line in f:
            lines.append(line.strip())
    return lines

def main(dataset_name):

    dataset_dir = Path(dataset_name)
    clean_dataset_name = "__".join(dataset_name.split("/"))
    if clean_dataset_name.endswith("__"):
        clean_dataset_name = clean_dataset_name[:-2]
    outfile = Path(f"batch_arrange_regesto_{clean_dataset_name}.jsonl")

    with open(outfile, "w") as jf:
        all_files = dataset_dir.glob("*.txt")
        all_files = sorted(all_files, key=lambda x: int(x.stem.split("_")[-1].split(".")[0]))
        for _file in all_files:
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
    main(sys.argv[1])
