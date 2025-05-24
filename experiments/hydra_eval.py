#pylint: disable=import-error,no-value-for-parameter
import sys
import os
import json
import glob
import logging
import gc
import contextlib

import datasets
import hydra
from omegaconf import OmegaConf
from evaluate import load as load_metric

import torch
from vllm import LLM, SamplingParams

from vllm.distributed.parallel_state import (
    destroy_model_parallel,
    destroy_distributed_environment,
)

sys.path.insert(0, "/home/gpucce/Repos/MGH_annotation/generation_code")
from utils import get_regesto_prompt, join_lines
from generate_ita_regesti import prepare_inputs



log = logging.getLogger(__name__)

class cltk_tokenizer:
    def __init__(self):
        from cltk import NLP
        self.tokenizer = NLP(language="lat", suppress_banner=True)

    def __call__(self, inputs):
        doc = self.tokenizer.analyze(inputs)
        return [token.string for token in doc.tokens]

@hydra.main(version_base=None, config_path="configs", config_name="config")
def main(cfg):

    os.environ["CUDA_VISIBLE_DEVICES"] = cfg.model.device
    os.environ["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"
    log.info(OmegaConf.to_yaml(cfg))

    dataset_name = cfg.dataset.dataset_name
    dss = sorted(glob.glob(f"/home/gpucce/Repos/MGH_annotation/output/escriptorium_{dataset_name}*"))
    dss = [datasets.load_dataset("json", data_files=i)["train"] for i in dss]
    ds = datasets.concatenate_datasets(dss)
    ds = ds.train_test_split(test_size=0.1)

    llm = LLM(cfg.model.model_name_or_path)
    sampling_params = SamplingParams(
        temperature=0,
        top_p=0.95,
        top_k=40,
        max_tokens=128,
    )

    full_input = ds["train"]
    inputs = [
        get_regesto_prompt(join_lines(i) if i is not None else "", [], [], dataset_name="mgh", n=0)
        for i in full_input["testo esteso"]
    ]

    if cfg.dataset.n_samples > 0:
        inputs = inputs[:cfg.dataset.n_samples]

    prepared_inputs = prepare_inputs(inputs, llm)
    output = llm.generate(
        prepared_inputs,
        sampling_params=sampling_params,
    )

    tokenizer = cltk_tokenizer()
    bleu = load_metric("bleu", tokenizer=tokenizer)
    rouge = load_metric("rouge", tokenizer=tokenizer)

    out_samples = []
    for full_text, regesto, synthetic_regesto in zip(full_input["testo esteso"], full_input["regesto"], output):
        if regesto is None or full_text is None:
            continue
        out_samples.append({
            "full_text": join_lines(full_text),
            "predictions": synthetic_regesto.outputs[0].text,
            "references": join_lines(regesto)})
        rouge.add(
            predictions=synthetic_regesto.outputs[0].text,
            reference=join_lines(regesto)
        )
        bleu.add(
            predictions=synthetic_regesto.outputs[0].text,
            reference=join_lines(regesto)
        )

    # Delete the llm object and free the memory
    destroy_model_parallel()
    destroy_distributed_environment()
    # del llm.llm_engine.model_executor
    del llm
    with contextlib.suppress(AssertionError):
        torch.distributed.destroy_process_group()
    gc.collect()
    torch.cuda.empty_cache()
    # ray.shutdown()
    print("Successfully delete the llm pipeline and free the GPU memory.")
    
    out = {"rouge": rouge.compute(), "bleu": bleu.compute()}

    with open('output.json', 'w') as f:
        json.dump(out, f)

    with open('./data.jsonl', 'w') as f:
        for i in out_samples:
            f.write(json.dumps(i) + "\n")

    log.info(out)
    return out

if __name__ == "__main__":
    main()