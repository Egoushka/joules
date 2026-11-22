"""Task 3: one local LLM answer of exactly 200 tokens. mlx-lm, Qwen2.5-0.5B-Instruct 4-bit,
greedy, fixed prompt, EOS suppressed so the length is always 200. Offline (cached weights)."""
import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import mlx.core as mx
from mlx_lm import load, stream_generate
from mlx_lm.sample_utils import make_sampler

N = 200
model, tok = load("mlx-community/Qwen2.5-0.5B-Instruct-4bit")
msgs = [{"role": "user", "content": "Explain how a heat pump works, in plain words."}]
prompt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
eos = list(tok.eos_token_ids) if hasattr(tok, "eos_token_ids") else [tok.eos_token_id]

def no_eos(tokens, logits):
    logits[:, eos] = -mx.inf
    return logits

n = 0
for _ in stream_generate(model, tok, prompt=prompt, max_tokens=N, sampler=make_sampler(temp=0.0),
                         logits_processors=[no_eos]):
    n += 1
print("tokens=%d" % n)
