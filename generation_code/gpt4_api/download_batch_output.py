import json
import sys
import datetime
from pathlib import Path
from openai import AzureOpenAI

def get_output(client, output_file_id):

    file_response = client.files.content(output_file_id)
    raw_responses = file_response.text.strip().split('\n')

    formatted_jsons = []
    for raw_response in raw_responses:
        json_response = json.loads(raw_response)
        formatted_json = json.dumps(json_response)
        formatted_jsons.append(formatted_json)

    return formatted_jsons
        

if __name__ == "__main__":

    output_file_id = sys.argv[1]

    # Configuration
    key_path = Path(__file__).parent / "itserr_07.key"
    with open(key_path, "r") as f:
        API_KEY = f.read().strip()

    client = AzureOpenAI(
        api_key=API_KEY,
        api_version="2024-10-21",
        azure_endpoint="https://itserr07.openai.azure.com/")

    formatted_jsons = get_output(client, output_file_id)

    download_logs_path = Path(__file__).parent / "download_logs.jsonl"
    download_logs_path.touch(exist_ok=True)
    with open(download_logs_path, "a") as f:
        f.write(
            json.dumps({"time": f"{datetime.datetime.now()}", "file_id": output_file_id}) + "\n"
            # f"{datetime.datetime.now()} Downloaded output for {output_file_id}\n"
        )

    with open(f"{output_file_id}.jsonl", "w") as f:
        for l in formatted_jsons:
            f.write(l + "\n")