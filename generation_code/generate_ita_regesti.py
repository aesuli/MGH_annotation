import re
import os
import sys
import json
import random
import datasets
import pandas as pd
from argparse import ArgumentParser

sys.path.insert(0, os.path.dirname(__file__))

from utils import get_regesto_prompt, get_backtranslation_regesto_prompt



def generate(prompts, llm, params):
    return llm.generate(prompts, sampling_params=params)

def prepare_inputs(prompts, llm):
    tokenizer = llm.get_tokenizer()
    prompts = tokenizer.apply_chat_template(
        prompts, truncation=None, padding=False,
        add_generation_prompt=True)
    prompts = tokenizer.batch_decode(prompts)
    return prompts

def get_tp_and_pp_size(model_name):
    tensor_parallel_size = 1
    pipeline_parallel_size = 1
    if "70" in model_name:
        tensor_parallel_size = 4
    if "405" in model_name:
        tensor_parallel_size = 16
    return tensor_parallel_size, pipeline_parallel_size

def get_vllm_llm_and_params(model_name: str, tokenizer_name: str):

    if model_name.split("/")[-1] == "gpt-4o":
        return None, None

    if tokenizer_name != model_name:
        print("vllm will ignore the tokenizer_name and use the same as model_name")

    params = SamplingParams(
        max_tokens=2048,
        min_tokens=256,
        temperature=0.8,
        top_p=0.9,
        # top_k=args.top_k if not args.use_beam_search else -1,
        # repetition_penalty=1.05,
        # use_beam_search=args.use_beam_search,
        # best_of=3 if args.use_beam_search else 1,
        # skip_special_tokens=True,
    )

    # this is not the right way
    tensor_parallel_size, pipeline_parallel_size = get_tp_and_pp_size(model_name)
    llm = LLM(
        model=model_name,
        tokenizer_mode="slow",
        tensor_parallel_size=tensor_parallel_size,
        # pipeline_parallel_size=pipeline_parallel_size,
        max_model_len=8192,
        enforce_eager=True)

    return llm, params

def postprocess_text(text):
    try:
        text = re.sub(r"\s+", " ", text)
    except:
        pass

    return text

def preprocess_samples(x):
    for col in ["regesto", "testo esteso", "apparato"]:
        if x[col] is not None:
            x[col] = " ".join(x[col]).replace("¬ ", "").replace("¬", "")
    return x

def main(args, experiments):
                
    my_folder = "/home/giovanni/"
    models_folder = os.path.join(my_folder, "models/hf_llama/")
    data_path = os.path.join(my_folder, "Repos/MGH_annotation/output/")
    dataset_name = args.dataset_name
    dfs = []
    for regesta_file in os.listdir(data_path):
        if dataset_name not in regesta_file or "escriptorium" not in regesta_file:
            continue
        df = datasets.load_dataset("json", data_files=os.path.join(data_path, regesta_file))["train"]
        df = df.map(preprocess_samples)
        volume = "_".join(regesta_file.split("_")[1:])
        df = df.add_column("volume", [volume]*len(df))
        df = df.map(lambda x: {"id": str(x["numero"]) + "_" + x["volume"]})
        dfs.append(df)
    df = datasets.concatenate_datasets(dfs, axis=0)
    df.to_json(f"output/joint_{args.dataset_name}.jsonl")
    _model_name = args.model_name
    model_path = os.path.join(models_folder, _model_name)

    n_articles = len(df)
    df = df.select(range(n_articles))
    messages = df["testo esteso"]
    ids = df["id"]
    regesti = df["regesto"]
    apparati = df["apparato"]

    llm, params = get_vllm_llm_and_params(model_path, model_path)

    for experiment, prompt_fn in experiments.items():

        prompt_dicts = [prompt_fn(m, messages, regesti, dataset_name, 2) for idx, m in enumerate(messages)]        

        if _model_name == "gpt-4o":
            outfile = f"batch_input_regesto_{dataset_name}_{_model_name}_{experiment}.jsonl"
            with open(outfile, "w") as jf:
                for id, prompt_dict, regesto in zip(ids, prompt_dicts, regesti):
                    request = {
                        "custom_id": f"{id}",
                        "method": "POST",
                        "url": "/chat/completions",
                        "body": {
                            "model": "gpt-4o-2",
                            "messages": prompt_dict,
                            "max_tokens": 1024,
                            "temperature": 0.8,
                        },
                        "real_regesto": regesto,
                    }
                    jf.write(json.dumps(request) + "\n")
            continue


        prompts = prepare_inputs(prompt_dicts, llm)
        output_text = generate(prompts, llm, params)
    
        prompts = []
        count = 0
        outfile = f"generation_output_regesto_{dataset_name}_{_model_name}_{experiment}.jsonl"
        with open(outfile, "w") as jf:
            for id, output, testo, regesto, apparato in zip(ids, output_text, messages, regesti, apparati):
                count += 1
                prompt = output.prompt
                generated_text = postprocess_text(output.outputs[0].text)
    
                to_dump = {
                    "prompt": prompt,
                    "regesto_sintetico": generated_text,
                    "regesto_originale": regesto,
                    "apparato": apparato,
                    "testo_esteso": testo,
                    "id": id,
                }
    
                print(to_dump)
                jf.write(json.dumps(to_dump) + "\n")

def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--model_name", type=str, required=True,
        choices=["llama-3.1-8b-instruct-hf", "llama-3.1-70b-instruct-hf",
                 "llama-3.1-405b-instruct-hf", "anita_8b", "gpt-4o"])
    parser.add_argument("--dataset_name", type=str, required=True)
    return parser.parse_args()

if __name__ == "__main__":

    import os

    experiments = {
        "format": get_regesto_prompt,
        "backtranslate": get_backtranslation_regesto_prompt,}
    args = parse_args()

    if args.model_name != "gpt-4o":
        from transformers import AutoTokenizer
        from vllm import LLM, SamplingParams

    main(args, experiments=experiments)
