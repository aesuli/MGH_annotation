import sys
import datetime
import json
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
    
    upload_info = file.model_dump_json(indent=2)
    upload_info_dict = json.loads(upload_info)
    upload_info_dict["filename"] = file_to_upload
    upload_info = json.dumps(upload_info_dict)
    with open(f"data_upload_output_{datetime.datetime.now()}", "w") as jf:
        jf.write(file.model_dump_json(indent=2))

    with open("/home/giovanni/Repos/MGH_annotation/generation_code/gpt4_api/upload_logs.jsonl", "a") as f:
        f.write(
            json.dumps({"time": f"{datetime.datetime.now()}", "file_name": file_to_upload, "file_id": file.id}) + "\n"
            # f"{datetime.datetime.now()} Uploaded file {file_to_upload} with file_id {file.id}\n"
        )
