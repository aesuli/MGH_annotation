import os
import time
import datetime
import sys
import json
from openai import AzureOpenAI

if __name__ == "__main__":

    # Configuration
    with open("/home/giovanni/Repos/MGH_annotation/generation_code/gpt4_api/itserr_07.key", "r") as f:
        API_KEY = f.read().strip()

    client = AzureOpenAI(
        api_key=API_KEY,
        api_version="2024-10-21",
        azure_endpoint="https://itserr07.openai.azure.com/")

    with open("/home/giovanni/Repos/MGH_annotation/generation_code/gpt4_api/upload_logs.jsonl", "r") as f:
        current_upload_logs = [json.loads(l) for l in f.readlines()]

    current_batch_logs_path = "/home/giovanni/Repos/MGH_annotation/generation_code/gpt4_api/batch_logs.jsonl"
    if os.path.exists(current_batch_logs_path):
        with open(current_batch_logs_path, "r") as f:
            current_batch_logs = [json.loads(l) for l in f.readlines()]
    else:
        current_batch_logs = []

    current_upload_logs = [l for l in current_upload_logs if l["file_id"] not in [b["file_id"] for b in current_batch_logs]]

    for idx, i in enumerate(current_upload_logs):
        print(f"idx: {idx}, file_name: {i['file_name']}], file_id: {i['file_id']}")
    selected_idx = int(input("Digit the idx of the file you want to run:\n"))

    # Submit a batch job with the file
    file_id = current_upload_logs[selected_idx]["file_id"]
    batch_response = client.batches.create(
        input_file_id=file_id,
        endpoint="/chat/completions",
        completion_window="24h",
    )

    # Save batch ID for later use
    batch_id = batch_response.id
    with open("/home/giovanni/Repos/MGH_annotation/generation_code/gpt4_api/batch_logs.jsonl", "a") as f:
        f.write(
            json.dumps({"time": f"{datetime.datetime.now()}", "batch_id":batch_id, "file_id":file_id}) + "\n"
            # f"{datetime.datetime.now()} Batch Id: {batch_id}\n"
        )

    print(batch_response.model_dump_json(indent=2))

    status = "validating"
    while status not in ("completed", "failed", "canceled"):
        time.sleep(60)
        batch_response = client.batches.retrieve(batch_id)
        status = batch_response.status
        print(f"{datetime.datetime.now()} Batch Id: {batch_id},  Status: {status}")
    
    if batch_response.status == "failed":
        for error in batch_response.errors.data:  
            print(f"Error code {error.code} Message {error.message}")