import time
import datetime
import sys
from openai import AzureOpenAI

if __name__ == "__main__":

    file_id = sys.argv[1]

    # Configuration
    with open("/home/giovanni/Repos/MGH_annotation/generation_code/gpt4_api/itserr_07.key", "r") as f:
        API_KEY = f.read().strip()
    
    client = AzureOpenAI(
        api_key=API_KEY,
        api_version="2024-10-21",
        azure_endpoint="https://itserr07.openai.azure.com/")


    # Submit a batch job with the file
    batch_response = client.batches.create(
        input_file_id=file_id,
        endpoint="/chat/completions",
        completion_window="24h",
    )
    
    # Save batch ID for later use
    batch_id = batch_response.id
    
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