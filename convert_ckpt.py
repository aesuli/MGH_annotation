import transformers, peft
import sys

model_path = sys.argv[1]

if model_path.endswith("/"):
    model_path = model_path[:-1]

cfg = peft.PeftConfig.from_pretrained(model_path)
m = transformers.AutoModelForCausalLM.from_pretrained(cfg.base_model_name_or_path)
tok = transformers.AutoTokenizer.from_pretrained(cfg.base_model_name_or_path)
pm = peft.PeftModel.from_pretrained(m, model_path)
newm = pm.merge_and_unload()
out_path = model_path.replace("-", "_") + "_full_model"
newm.save_pretrained(out_path)
tok.save_pretrained(out_path)