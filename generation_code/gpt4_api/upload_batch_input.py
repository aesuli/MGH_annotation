import sys
import datetime

from openai import AzureOpenAI

# Configuration


if __name__ == "__main__":
    
    file_to_upload = sys.argv[1]

    with open("/home/giovanni/Repos/MGH_annotation/generation_code/gpt4_api/itserr_07.key", "r") as f:
        API_KEY = f.read().strip()
    
    client = AzureOpenAI(
        api_key=API_KEY,
        api_version="2024-10-21",
        azure_endpoint="https://itserr07.openai.azure.com/")
    
    file = client.files.create(
      file=open(file_to_upload, "rb"),
      purpose="batch")
    
    print(file.model_dump_json(indent=2))
    with open(f"data_upload_output_{datetime.datetime.now()}", "w") as jf:
        jf.write(file.model_dump_json(indent=2))
