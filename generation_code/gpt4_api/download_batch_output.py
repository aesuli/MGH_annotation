import json
import sys
import datetime
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
    with open("/home/giovanni/Repos/MGH_annotation/generation_code/gpt4_api/itserr_07.key", "r") as f:
        API_KEY = f.read().strip()
    
    client = AzureOpenAI(
        api_key=API_KEY,
        api_version="2024-10-21",
        azure_endpoint="https://itserr07.openai.azure.com/")
    
    formatted_jsons = get_output(client, output_file_id)

    with open("/home/giovanni/Repos/MGH_annotation/generation_code/gpt4_api/download_logs.jsonl", "a") as f:
        f.write(
            json.dumps({"time": f"{datetime.datetime.now()}", "file_id": output_file_id}) + "\n"
            # f"{datetime.datetime.now()} Downloaded output for {output_file_id}\n"
        )

    with open(f"{output_file_id}.jsonl", "w") as f:
        for l in formatted_jsons:
            f.write(l + "\n")