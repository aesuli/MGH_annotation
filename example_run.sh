myinput=$1
python arrange_regesta_for_gpt.py $myinput
file_path=$(basename $myinput)
python generation_code/arrange_regesti_gpt.py lines_${file_path::-4}
# python generation_code/gpt4_api/upload_batch_input.py batch_arrange_regesto_${myinput::-4}.json

# sleep 5
# python generation_code/gpt4_api/run_batch_job.py
# python generation_code/gpt4_api/download_batch_output.py # check the file name