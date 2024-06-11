# Annotating Regesta in MGH

This is a simple script with a few heuristics to annotate the main parts of each regesto in three epistolae volumes of MGH.
The parts are:
- number
- regesto
- apparato
- full text

## Input

The script is specifically devised to process the output of the processing of the pdf version of the following MGH volumes:
[Epistolae saeculi XIII e regestis pontificum Romanorum selectae - tomus I](https://www.dmgh.de/mgh_epp_saec_xiii_1/index.htm#page/(III)/mode/1up)
[Epistolae saeculi XIII e regestis pontificum Romanorum selectae - tomus II](https://www.dmgh.de/mgh_epp_saec_xiii_2/index.htm#page/(III)/mode/1up)
[Epistolae saeculi XIII e regestis pontificum Romanorum selectae - tomus III](https://www.dmgh.de/mgh_epp_saec_xiii_3/index.htm#page/(III)/mode/1up)

The OCR is done in [eScriptorium](https://gitlab.com/scripta/escriptorium/-/blob/develop/README.md?ref_type=heads), with default segmentation, and transcription made using the [catmus print large model](https://zenodo.org/records/10592716).

Transcription is exported from eScriptorium using the ALTO format.

## Output

The output of the script are three json files, one for each volume. 
Each entry of the json is an annotated regesto, with the four part listed above.
Line in each entry are still split according to the OCR.
The script does not use machine learning, because the process is simple enough to be explicitly coded using a few heuristics based on string positions, content, and sizes.
The output still contain a few errors, but it has been largely improved with a pass from a human annotator, see the [output folder](ouput)

## Future work

Lines can be merged is a single piece of text by adding a check for hyphenation characters and properly merging them.
Given the overall good quality of the output, machine learning can be used to perform training data cleaning and self-correct the remaining errors.
The output can be used to train a machine learning model to extract regesta from other OCR-processed volumes that are not simple as these to be processed with heuristics.

## Acknowledgment

This activity is supported by the [ITSERR project](https://www.itserr.it/).

Finanziato dall'Unione europea - NextGenerationEU
