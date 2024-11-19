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
    splat = splat[idx + 1:]
    if len(splat) == 0:
        return x
    return splat[0]


def convert_metrics_to_df(metrics, model_name):
    # out_df = pd.DataFrame(columns=["dataset", "experiment", "metric", "value"])
    future_df = []
    for dataset_name, experiment_metrics in metrics.items():
        print(dataset_name)
        for experiment, _metrics in experiment_metrics.items():
            print("\t", experiment)
            row = {"model": model_name, "dataset": dataset_name,
                   "experiment": experiment}
            for metric_name, metric in _metrics.items():
                row["n samples"] = len(metric)
                computed_metric = metric.compute()
                print("\t\t", metric_name, computed_metric)
                for k, v in computed_metric.items():
                    row[k] = v
            future_df.append(row)
    out_df = pd.DataFrame(future_df)
    return out_df


def save_to_latex(df, path):
    df.loc[
        :,
        [
            "model",
            "dataset",
            "experiment",
            "n samples",
            "rouge1",
            "rouge2",
            "rougeL",
            "bleu",
        ],
    ].set_index(["model", "dataset", "experiment"]).to_latex(
        path,
        float_format="%.2f",
        # index=False
    )


def get_ref_df(dataset_name):
    return (datasets.load_dataset(
            "json", data_files=f"output/joint_{dataset_name}.jsonl"
            )["train"]
            .to_pandas()
            .set_index("id"))


def get_metrics(dataset_name, model_name, experiment, metrics=None):
    if metrics is None:
        metrics = {}
    if dataset_name not in metrics:
        metrics[dataset_name] = {}
    if experiment not in metrics[dataset_name]:
        metrics[dataset_name][experiment] = {
            "rouge": evaluate.load("rouge"),
            "bleu": evaluate.load("bleu"),
        }
    return metrics


def get_gpt4_data(dataset_name, model_name, experiment):
    preds_ds = datasets.load_dataset(
        "json",
        data_files=f"generation_output/joint_{
            dataset_name}_{model_name}_{experiment}.jsonl",
    )["train"]
    preds_ds = preds_ds.map(
        lambda x: {
            "text_response": x["response"]["body"]["choices"][0]["message"][
                "content"
            ]
        }
    )
    preds_ds = preds_ds.filter(
        lambda x: x["text_response"] is not None)
    preds_ds = preds_ds.map(
        lambda x: {"id": x["custom_id"], "pred": split_at_regetso(x["text_response"])})
    return preds_ds


def get_llama_data(dataset_name, model_name, experiment):
    preds_ds = datasets.load_dataset(
        "json",
        data_files=f"generation_output/joint_{
            dataset_name}_{model_name}_{experiment}.jsonl",
    )["train"]

    preds_ds = preds_ds.map(
        lambda x: {"pred": split_at_regetso(x["regesto_sintetico"])})

    return preds_ds


def eval_llm(args, experiments, model_name, save_table=False):
    metrics = {}
    for dataset_name in args.dataset_names:
        ref_df = get_ref_df(dataset_name)
        for experiment in experiments:
            try:
                if "gpt-4" in model_name:
                    preds_ds = get_gpt4_data(dataset_name, model_name, experiment)
                elif "llama-3.1" in model_name:
                    preds_ds = get_llama_data(dataset_name, model_name, experiment)
            except FileNotFoundError:
                print(f"Skipping: {model_name}, {dataset_name}, {experiment}")
                continue

            metrics = get_metrics(
                dataset_name, model_name, experiment, metrics)
            _metrics = metrics[dataset_name][experiment]
            for i in preds_ds:
                id = i["id"]
                pred = i["pred"]
                ref = ref_df.loc[id, "regesto"]
                if ref is None:
                    continue
                for _, metric in _metrics.items():
                    metric.add(reference=ref, prediction=pred)

    out_df = convert_metrics_to_df(metrics, model_name)
    return out_df


def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        "--dataset_names", type=str, nargs="+", choices=["mgh", "auvray"]
    )

    parser.add_argument("--model_names", type=str, nargs="+",
                        choices=["gpt-4o", "llama-3.1-70b-instruct-hf", "llama-3.1-405b-instruct-hf"])

    parser.add_argument(
        "--experiments",
        type=str,
        default="regesto",
        nargs="+",
        choices=["backtranslate", "format"],
    )

    parser.add_argument("--save_table", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":

    args = parse_args()
    experiments = args.experiments
    all_dfs = []
    for model_name in args.model_names:
        all_dfs.append(eval_llm(args, experiments, model_name,
                       save_table=args.save_table))

    df = pd.concat(all_dfs, axis=0)  # .to_csv("evaluation_results.csv")
    if args.save_table:
        save_to_latex(
            df, "/home/giovanni/Latex/regesti_ircdl/tables/2_shots_eval.tex")
    print("done")
