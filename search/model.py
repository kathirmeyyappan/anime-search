"""Self-hosted open-weight LLM (Qwen2.5-7B-Instruct via vLLM) on a Modal GPU
container — no external LLM API, no HTTP server layer. agent.py imports `app`
and `Model` from here directly (same App, one deploy unit — see agent.py) and
calls Model.generate(...) as a Modal method; vLLM's .chat() handles the
model's chat template internally, so no manual prompt formatting needed.
"""

import modal

app = modal.App("anime-search")

MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"

vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm==0.21.0")
)

hf_cache_vol = modal.Volume.from_name("anime-search-hf-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("anime-search-vllm-cache", create_if_missing=True)


@app.cls(
    image=vllm_image,
    gpu="A10G",
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
    scaledown_window=5 * 60,
)
class Model:
    @modal.enter()
    def load(self):
        from vllm import LLM

        self.llm = LLM(model=MODEL_NAME, dtype="bfloat16", max_model_len=8192)

    @modal.method()
    def generate(self, messages: list[dict], max_tokens: int = 1024) -> str:
        from vllm import SamplingParams

        params = SamplingParams(temperature=0.2, max_tokens=max_tokens)
        outputs = self.llm.chat(messages, params)
        return outputs[0].outputs[0].text
