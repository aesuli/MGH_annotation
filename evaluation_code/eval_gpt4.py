import json
import pandas as pd

import evaluate
import datasets
from argparse import ArgumentParser


def split_at_regetso(x):
    if "regesto" not in x.lower():
        return x
    splat = [i for i in x.split("\n") if len(i) > 0]
    idx = min(i for i in range(len(splat)) if "regesto" in splat[i].lower())
    splat =  splat[idx + 1:]
    if len(splat) == 0:
        return x
    return splat[0]

def eval_gpt4(args, experiments, save_table=False):
    metrics = {}
    for dataset_name in args.dataset_names:
        ref_df = datasets.load_dataset("json", data_files=f"output/joint_{dataset_name}.jsonl")["train"].to_pandas().set_index("id")
        metrics[dataset_name] = {}
        for experiment in experiments:
            metrics[dataset_name][experiment] = {"rouge": evaluate.load("rouge"), "bleu": evaluate.load("bleu"),}
            _metrics = metrics[dataset_name][experiment]
            preds_ds = datasets.load_dataset("json", data_files=f"generation_output/joint_{dataset_name}_preds_{experiment}.jsonl")["train"]
            preds_ds = preds_ds.map(lambda x: {"text_response": x["response"]["body"]["choices"][0]["message"]["content"]})
            preds_ds = preds_ds.filter(lambda x: x["text_response"] is not None)

            for i in preds_ds:
                id = i["custom_id"]
                pred = i["text_response"]
                pred = split_at_regetso(pred)
                ref = ref_df.loc[id, "regesto"]
                if ref is None:
                    continue
                for _, metric in _metrics.items():
                    metric.add(reference=ref, prediction=pred)

    # out_df = pd.DataFrame(columns=["dataset", "experiment", "metric", "value"])
    future_df = []
    for dataset_name, experiment_metrics in metrics.items():
        print(dataset_name)
        for experiment, _metrics in experiment_metrics.items():
            print("\t", experiment)
            row = {"dataset": dataset_name, "experiment": experiment}
            for metric_name, metric in _metrics.items():
                row["n samples"] = len(metric)
                print("\t\t", metric_name, metric)
                computed_metric = metric.compute()
                for k, v in computed_metric.items():
                    row[k] = v
            future_df.append(row)
    out_df = pd.DataFrame(future_df)
    if save_table:
        out_df.loc[
            :, ["dataset", "experiment", "n samples", "rouge1", "rouge2", "rougeL", "bleu"]
        ].set_index(["dataset", "experiment"]).to_latex(
            "/home/giovanni/Latex/regesti_ircdl/tables/2_shots_eval.tex", 
            float_format="%.2f",
            # index=False
            )
    return out_df

def eval_llama(args, experiments, save_table=False):
    pass

def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        "--dataset_names",
        type=str, nargs="+", choices=["mgh", "auvray"])
    parser.add_argument(
        "--model_name",
        type=str, default="gpt-4o")
    parser.add_argument(
        "--experiments",
        type=str, default="regesto", nargs="+", choices=["backtranslate", "format"])
    parser.add_argument(
        "--save_table",
        action="store_true")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    experiments = args.experiments
    current_df = eval_gpt4(args, experiments, save_table=args.save_table)
    print("done")