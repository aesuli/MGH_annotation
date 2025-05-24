# Copyright 2025 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
# Full training
python trl/scripts/sft.py \
    --model_name_or_path Qwen/Qwen2-0.5B \
    --dataset_name trl-lib/Capybara \
    --learning_rate 2.0e-5 \
    --num_train_epochs 1 \
    --packing \
    --per_device_train_batch_size 2 \
    --gradient_accumulation_steps 8 \
    --gradient_checkpointing \
    --logging_steps 25 \
    --eval_strategy steps \
    --eval_steps 100 \
    --output_dir Qwen2-0.5B-SFT \
    --push_to_hub

# LoRA
python trl/scripts/sft.py \
    --model_name_or_path Qwen/Qwen2-0.5B \
    --dataset_name trl-lib/Capybara \
    --learning_rate 2.0e-4 \
    --num_train_epochs 1 \
    --packing \
    --per_device_train_batch_size 2 \
    --gradient_accumulation_steps 8 \
    --gradient_checkpointing \
    --logging_steps 25 \
    --eval_strategy steps \
    --eval_steps 100 \
    --use_peft \
    --lora_r 32 \
    --lora_alpha 16 \
    --output_dir Qwen2-0.5B-SFT \
    --push_to_hub
"""

import argparse
import os
import sys

from datasets import load_dataset, concatenate_datasets
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
from transformers.models.auto.modeling_auto import MODEL_FOR_IMAGE_TEXT_TO_TEXT_MAPPING_NAMES


from trl import (
    ModelConfig,
    ScriptArguments,
    SFTConfig,
    SFTTrainer,
    TrlParser,
    get_kbit_device_map,
    get_peft_config,
    get_quantization_config,
)

from omegaconf import DictConfig, OmegaConf
import hydra

sys.path.insert(
    0, "/home/gpucce/Repos/MGH_annotation/generation_code"
    # os.path.join(os.path.dirname(os.path.dirname(__file__)), "generation_code")
)

from utils import get_regesto_prompt, join_lines

def main(cfg):

    def make_parser(subparsers: argparse._SubParsersAction = None):
        dataclass_types = (ScriptArguments, SFTConfig, ModelConfig)
        if subparsers is not None:
            parser = subparsers.add_parser("sft", help="Run the SFT training script", dataclass_types=dataclass_types)
        else:
            parser = TrlParser(dataclass_types)
        return parser

    parser = make_parser()
    script_args, training_args, model_args = parser.parse_args_and_config()


    ################
    # Model init kwargs & Tokenizer
    ################
    quantization_config = get_quantization_config(model_args)
    model_kwargs = dict(
        revision=model_args.model_revision,
        trust_remote_code=model_args.trust_remote_code,
        attn_implementation=model_args.attn_implementation,
        torch_dtype=model_args.torch_dtype,
        use_cache=False if training_args.gradient_checkpointing else True,
        device_map=get_kbit_device_map() if quantization_config is not None else None,
        quantization_config=quantization_config,
    )

    # Create model
    config = AutoConfig.from_pretrained(model_args.model_name_or_path)
    valid_image_text_architectures = MODEL_FOR_IMAGE_TEXT_TO_TEXT_MAPPING_NAMES.values()

    if config.architectures and any(arch in valid_image_text_architectures for arch in config.architectures):
        from transformers import AutoModelForImageTextToText

        model_kwargs.pop("use_cache", None)  # Image models do not support cache
        model = AutoModelForImageTextToText.from_pretrained(model_args.model_name_or_path, **model_kwargs)
    else:
        model = AutoModelForCausalLM.from_pretrained(model_args.model_name_or_path, **model_kwargs)

    # Create tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_args.model_name_or_path, trust_remote_code=model_args.trust_remote_code, use_fast=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    ################
    # Dataset
    ################raw_datasets = datasets.concatenate_datasets([
    raw_datasets = concatenate_datasets([load_dataset(
            "json", data_files=
            f"/raid/homes/giovanni.puccetti/Repos/MGH_annotation/"
            f"output/escriptorium_mgh_{i}.json",
            split="train")
        for i in range(1,3)
    ])
    raw_datasets = raw_datasets.filter(
        lambda x: x["testo esteso"] is not None and x["regesto"] is not None
    )
    raw_full_texts = raw_datasets["testo esteso"]
    raw_regesti = raw_datasets["regesto"]

    raw_datasets = raw_datasets.map(
        # lambda x: {
        #     "prompt": "Full Text:\n\n" + " ".join(x["testo esteso"]),
        #     "completion": "\n\nRegesto:\n\n" + " ".join(x["regesto"])
        # })
        lambda x: {
            "messages": get_regesto_prompt(
                join_lines(x["testo esteso"]),
                raw_regesti,
                raw_full_texts,
                dataset_name="mgh",
                n=0,) + [{"role": "assistant", "content": join_lines(x["regesto"])}]
        })
    raw_datasets = raw_datasets.train_test_split(
        test_size=0.1, seed=training_args.seed)
    raw_datasets["validation"] = raw_datasets["test"]
    del raw_datasets["test"]
    for i in range(3):
        for h, k in raw_datasets["train"][i].items():

            print(h, k)


    ################
    # Training
    ################
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=raw_datasets["train"],
        eval_dataset=raw_datasets["validation"],
        processing_class=tokenizer,
        peft_config=get_peft_config(model_args),
    )

    trainer.train()

    # Save and push to hub
    trainer.save_model(training_args.output_dir)
    if training_args.push_to_hub:
        trainer.push_to_hub(dataset_name=script_args.dataset_name)




if __name__ == "__main__":
    main(cfg)
