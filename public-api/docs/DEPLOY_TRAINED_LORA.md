# Deploy trained egregore LoRAs (r730)

After the nine SFT LoRA training week, use this checklist.

## 1. Unified LoRA API (`:8100`)

```bash
# On r730
bash /opt/s2-ecosystem/public-api/scripts/setup-unified-8100-r730.sh
systemctl status unified-egregore
curl http://127.0.0.1:8100/egregores/available
```

Weights: `/mnt/bipra/egregore-training/trained_models/`

**Note:** Tesla P40 needs `EGREGORE_DEVICE=cpu` in the unified service (set by setup script). First `/generate` loads the model (~20–30s); hosted chat can take 1–2 minutes per reply on CPU.

## 2. Hosted gateway (`:3020`)

Port **3010** is the legacy Python S² API. The Ake gateway runs on **3020**.

```bash
cp /opt/s2-ecosystem/public-api/scripts/r730-public-api.env /opt/s2-ecosystem/public-api/.env
# Production: HOSTED_REQUIRE_BILLING=true, LAB_HOSTED_UNLOCK=false
systemctl enable --now s2-public-api
curl http://127.0.0.1:3020/health
```

`hosted_inference` should be `unified-lora` when `:8100` is healthy.

## 3. Benchmarks (from dev PC)

```bash
cd "APPs/S2 Intelligence/benchmark"
pip install -r REQUIREMENTS.txt datasets requests
export UNIFIED_EGREGORE_URL=http://192.168.1.78:8100
export BENCHMARK_LORA_TIMEOUT=180
python run_all_standard_benchmarks.py --backends lora --lora-egregores ake --limit 50
```

## 4. Apps (PSLA)

Point `S2_API_URL` at the gateway (`http://192.168.1.78:3020` on LAN, or `https://api.s2artslab.com` when proxied). Keep `USE_HOSTED_GATEWAY=true`.

**Post-training checklist (PSLA repo):** `APPs/pro-se-legal/docs/AFTER_R730_TRAINING.md` — tunnel, `test-s2-hosted-chat.ps1`, restart services, confirm `source` is `hosted-unified-lora` when possible.

```powershell
cd APPs\pro-se-legal
.\scripts\start-s2-api-tunnel.ps1   # separate terminal
.\scripts\test-s2-hosted-chat.ps1 -OwnerId your-local-owner-id
```

## 5. Optional: Ollama `s2-ake-lora`

Current BIPRA weights are **GPT-2**. Ollama `s2-ake` uses **Llama 3.2**. Merge into Ollama only after **7B** Ake adapters exist (`docs/LORA_TO_OLLAMA.md`).

## 6. Train further (when benchmarks say so)

| Signal | Action |
|--------|--------|
| Wrong tone, right facts | DPO: `rlhf_pipeline.py` |
| Weak domains | v2 dataset + retrain |
| Need speed + quality | `train_egregore_on_foundation_7b.py`, vLLM with 7B LoRAs |
