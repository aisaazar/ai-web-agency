# Local LLM setup

The free local LLM path uses Ollama. The Agency model is derived from `qwen3:0.6b` with a 4096-token context to keep the Windows development/production host memory-safe.

Run `powershell -ExecutionPolicy Bypass -File scripts/setup-local-llm.ps1` once, then configure `AGENCY_LLM_PROVIDER=local`, `AGENCY_LOCAL_LLM_BASE_URL=http://127.0.0.1:11434/v1`, and `AGENCY_LOCAL_LLM_MODEL=agency-qwen3-4k` in the deployment secret/config store.

The setup script never prints API keys or reads `.env` files.
