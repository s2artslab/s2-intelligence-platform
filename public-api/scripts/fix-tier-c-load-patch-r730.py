#!/usr/bin/env python3
"""Fix botched TIER_C_BLENDED patch in train_egregore_on_foundation_7b.py on r730."""
from pathlib import Path

p = Path("/opt/s2-ecosystem/egregore-training/train_egregore_on_foundation_7b.py")
text = p.read_text(encoding="utf-8")

start = text.index("def load_egregore_dataset")
end = text.index("def prepare_model_with_foundation")
new_fn = '''def load_egregore_dataset(egregore: str, conv_only: bool = False):
    """Load egregore-specific dataset (conv_only = identity only, no foundation)."""
    tier_c = os.environ.get("TIER_C_BLENDED")
    if tier_c and os.path.exists(tier_c):
        path = tier_c
    elif conv_only:
        path = os.path.join(TRAINING_DATA_DIR, f"{egregore}_conv_only_dataset.json")
        if not os.path.exists(path):
            path = os.path.join(TRAINING_DATA_DIR, f"{egregore}_blended_dataset.json")
    else:
        path = os.path.join(TRAINING_DATA_DIR, f"{egregore}_blended_dataset.json")

    response_field = f"{egregore}_response"
    logger.info("Loading dataset from %s...", path)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cap = egregore.capitalize()
    training_texts = []
    for item in data:
        user_input = item.get("question", "").strip()
        response = item.get(response_field, "").strip()
        if not response:
            continue
        if tier_c and path == tier_c:
            training_texts.append(f"{user_input}\n{cap}: {response}\n\n")
        else:
            text = f"User: {user_input}\n{cap}: {response}\n\n"
            training_texts.append(text)

    logger.info("Prepared %d training texts", len(training_texts))
    return training_texts


'''
text = text[:start] + new_fn + text[end:]
p.write_text(text, encoding="utf-8")
print("Fixed load_egregore_dataset")
