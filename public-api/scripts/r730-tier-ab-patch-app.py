#!/usr/bin/env python3
"""Apply Tier A/B patches to unified_egregore_service on r730."""
from pathlib import Path

APP = Path("/opt/s2-ecosystem/egregore-training/unified_egregore_service/app.py")
CFG = Path("/opt/s2-ecosystem/egregore-training/unified_egregore_service/config.py")

CFG_SNIPPET = '''
# Tier A/B inference defaults (see HOSTED_AKE_GATEWAY.md)
DEFAULT_USE_PERSONA = os.environ.get("EGREGORE_USE_PERSONA", "0") == "1"
DEFAULT_DO_SAMPLE = os.environ.get("EGREGORE_DO_SAMPLE", "0") == "1"
DEFAULT_TEMPERATURE = float(os.environ.get("EGREGORE_DEFAULT_TEMPERATURE", "0.2"))
DEFAULT_MAX_NEW_TOKENS = int(os.environ.get("EGREGORE_MAX_NEW_TOKENS", "150"))
ADAPTER_LOAD_MODE = os.environ.get("EGREGORE_ADAPTER_LOAD_MODE", "egregore_only")
'''

IMPORT_OLD = """from config import (
    BASE_MODEL, EGREGORE_CONFIG, EGREGORE_PERSONALITIES, REDIS_URL, QUEUE_NAME,
    resolve_adapter_path, resolve_model_load_config, get_effective_base_model,
    DEVICE, USE_CPU_OFFLOAD, REPETITION_PENALTY, NO_REPEAT_NGRAM_SIZE,
    EGREGORE_TEMPERATURE_OVERRIDES,
)"""

IMPORT_NEW = """from config import (
    BASE_MODEL, EGREGORE_CONFIG, EGREGORE_PERSONALITIES, REDIS_URL, QUEUE_NAME,
    resolve_adapter_path, resolve_model_load_config, get_effective_base_model,
    DEVICE, USE_CPU_OFFLOAD, REPETITION_PENALTY, NO_REPEAT_NGRAM_SIZE,
    EGREGORE_TEMPERATURE_OVERRIDES,
    DEFAULT_USE_PERSONA, DEFAULT_DO_SAMPLE, DEFAULT_TEMPERATURE,
    DEFAULT_MAX_NEW_TOKENS, ADAPTER_LOAD_MODE, FOUNDATION_ADAPTER_NAME,
)"""

LOAD_OLD = """        # Load adapters in order (foundation then egregore for 7B stacked)
        if len(adapter_paths) == 1:
            model = PeftModel.from_pretrained(base, adapter_paths[0])
        else:
            model = PeftModel.from_pretrained(base, adapter_paths[0])
            model = model.merge_and_unload()
            model = PeftModel.from_pretrained(model, adapter_paths[1])

        if tokenizer is None:"""

LOAD_NEW = """        # Load adapters — mode must match training graph (see EGREGORE_ADAPTER_LOAD_MODE)
        if len(adapter_paths) == 1:
            model = PeftModel.from_pretrained(base, adapter_paths[0])
        elif ADAPTER_LOAD_MODE == "merge_foundation":
            model = PeftModel.from_pretrained(base, adapter_paths[0])
            model = model.merge_and_unload()
            model = PeftModel.from_pretrained(model, adapter_paths[1])
        elif ADAPTER_LOAD_MODE == "egregore_only":
            # Training used set_adapter(egregore) only — foundation frozen but not active in forward
            model = PeftModel.from_pretrained(base, adapter_paths[-1])
        elif ADAPTER_LOAD_MODE == "foundation_merged":
            model = PeftModel.from_pretrained(base, adapter_paths[0])
            model = model.merge_and_unload()
        else:
            # active: foundation + egregore both registered; activate egregore (foundation as default peft name)
            model = PeftModel.from_pretrained(
                base, adapter_paths[0], adapter_name=FOUNDATION_ADAPTER_NAME, is_trainable=False
            )
            model.load_adapter(adapter_paths[1], adapter_name=egregore)
            model.set_adapter(egregore)
        print(f"  Adapter load mode: {ADAPTER_LOAD_MODE}")

        if tokenizer is None:"""

HELPER = '''

def _resolve_generation_options(data, egregore, temperature):
    """Tier A: env/request overrides for stable decoding."""
    if "temperature" in data:
        temp = float(data["temperature"])
    elif egregore in EGREGORE_TEMPERATURE_OVERRIDES:
        temp = EGREGORE_TEMPERATURE_OVERRIDES[egregore]
    else:
        temp = DEFAULT_TEMPERATURE
    max_new = int(data.get("max_new_tokens") or data.get("max_length") or DEFAULT_MAX_NEW_TOKENS)
    max_new = max(16, min(max_new, 2048))
    do_sample = data.get("do_sample", DEFAULT_DO_SAMPLE)
    if isinstance(do_sample, str):
        do_sample = do_sample.lower() in ("1", "true", "yes")
    use_persona = data.get("use_persona", DEFAULT_USE_PERSONA)
    if isinstance(use_persona, str):
        use_persona = use_persona.lower() in ("1", "true", "yes")
    rep_pen = data.get("repetition_penalty")
    if rep_pen is None and not do_sample:
        rep_pen = 1.0
    elif rep_pen is None:
        rep_pen = REPETITION_PENALTY
    ngram = data.get("no_repeat_ngram_size")
    if ngram is None and not do_sample:
        ngram = 0
    elif ngram is None:
        ngram = NO_REPEAT_NGRAM_SIZE
    return temp, max_new, do_sample, use_persona, float(rep_pen), int(ngram)


def _run_generate(model, inputs, max_new_tokens, temperature, do_sample, repetition_penalty, no_repeat_ngram_size):
    gen_kw = {
        "input_ids": inputs,
        "max_new_tokens": max_new_tokens,
        "num_return_sequences": 1,
        "pad_token_id": tokenizer.eos_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }
    if do_sample:
        gen_kw["temperature"] = max(temperature, 0.01)
        gen_kw["do_sample"] = True
        gen_kw["repetition_penalty"] = repetition_penalty
        if no_repeat_ngram_size > 0:
            gen_kw["no_repeat_ngram_size"] = no_repeat_ngram_size
    else:
        gen_kw["do_sample"] = False
    with torch.no_grad():
        return model.generate(**gen_kw)
'''

GEN_OLD = """        max_length = data.get("max_length", 200)
        temperature = data.get("temperature", 0.7)
        if egregore in EGREGORE_TEMPERATURE_OVERRIDES:
            temperature = EGREGORE_TEMPERATURE_OVERRIDES[egregore]
        repetition_penalty = data.get("repetition_penalty", REPETITION_PENALTY)
        no_repeat_ngram_size = data.get("no_repeat_ngram_size", NO_REPEAT_NGRAM_SIZE)
        use_persona = data.get("use_persona", True)
        history = data.get("history") or []
        
        model, err = get_model(egregore)
        if err:
            return jsonify({"status": "error", "message": err}), 404
        
        inference_prompt = _format_prompt(egregore, prompt, use_persona=use_persona, history=history)
        inputs = tokenizer(inference_prompt, return_tensors="pt").input_ids
        device, _ = _resolve_device()
        if device == "cuda":
            inputs = inputs.cuda()
        
        with torch.no_grad():
            outputs = model.generate(
                input_ids=inputs,
                max_length=inputs.shape[1] + max_length,
                num_return_sequences=1,
                temperature=temperature,
                do_sample=True,
                repetition_penalty=repetition_penalty,
                no_repeat_ngram_size=no_repeat_ngram_size,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        # Extract only the generated part (after the prompt)"""

GEN_NEW = """        history = data.get("history") or []
        temp, max_new, do_sample, use_persona, rep_pen, ngram = _resolve_generation_options(
            data, egregore, data.get("temperature", 0.7)
        )

        model, err = get_model(egregore)
        if err:
            return jsonify({"status": "error", "message": err}), 404

        inference_prompt = _format_prompt(egregore, prompt, use_persona=use_persona, history=history)
        inputs = tokenizer(inference_prompt, return_tensors="pt").input_ids
        device, _ = _resolve_device()
        if device == "cuda":
            inputs = inputs.cuda()

        outputs = _run_generate(model, inputs, max_new, temp, do_sample, rep_pen, ngram)

        # Extract only the generated part (after the prompt)"""

GEN_RETURN = """        return jsonify({
            "egregore": egregore,
            "prompt": prompt,
            "response": response,
            "status": "success"
        })"""

GEN_RETURN_NEW = """        return jsonify({
            "egregore": egregore,
            "prompt": prompt,
            "response": response,
            "status": "success",
            "meta": {
                "use_persona": use_persona,
                "do_sample": do_sample,
                "max_new_tokens": max_new,
                "adapter_load_mode": ADAPTER_LOAD_MODE,
            },
        })"""


def patch_file(path: Path, replacements: list[tuple[str, str]], insert_after: str | None = None, insert_text: str | None = None):
    text = path.read_text()
    for old, new in replacements:
        if old not in text:
            raise SystemExit(f"patch miss in {path}: {old[:60]}...")
        text = text.replace(old, new, 1)
    if insert_after and insert_text and insert_after in text:
        if "_resolve_generation_options" not in text:
            text = text.replace(insert_after, insert_text + insert_after, 1)
    path.write_text(text)
    print(f"patched {path}")


def main():
    cfg = CFG.read_text()
    if "DEFAULT_USE_PERSONA" not in cfg:
        cfg = cfg.rstrip() + "\n" + CFG_SNIPPET + "\n"
        CFG.write_text(cfg)
        print("updated config.py")

    app = APP.read_text()
    if "DEFAULT_USE_PERSONA" not in app:
        patch_file(APP, [(IMPORT_OLD, IMPORT_NEW)])
        patch_file(APP, [(LOAD_OLD, LOAD_NEW)])
        if "_resolve_generation_options" not in app:
            patch_file(APP, [], insert_after="def generate_tokens(", insert_text=HELPER)
        patch_file(APP, [(GEN_OLD, GEN_NEW)])
        if '"meta":' not in app:
            patch_file(APP, [(GEN_RETURN, GEN_RETURN_NEW)])
    else:
        print("app.py already patched")

    # Patch stream route similarly if present
    app = APP.read_text()
    stream_old = """        max_length = data.get("max_length", 200)
        temperature = data.get("temperature", 0.7)
        if egregore in EGREGORE_TEMPERATURE_OVERRIDES:
            temperature = EGREGORE_TEMPERATURE_OVERRIDES[egregore]
        repetition_penalty = data.get("repetition_penalty", REPETITION_PENALTY)
        no_repeat_ngram_size = data.get("no_repeat_ngram_size", NO_REPEAT_NGRAM_SIZE)
        use_persona = data.get("use_persona", True)
        history = data.get("history") or []
        
        model, err = get_model(egregore)"""
    stream_new = """        history = data.get("history") or []
        temp, max_new, do_sample, use_persona, rep_pen, ngram = _resolve_generation_options(
            data, egregore, data.get("temperature", 0.7)
        )

        model, err = get_model(egregore)"""
    if stream_old in app:
        patch_file(APP, [(stream_old, stream_new)])
    print("done")


if __name__ == "__main__":
    main()
