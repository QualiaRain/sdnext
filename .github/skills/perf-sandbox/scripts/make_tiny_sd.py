#!/usr/bin/env python
"""
Build a tiny random-weight Stable Diffusion pipeline in diffusers folder layout, fully offline.

Purpose: an end-to-end smoke/benchmark model for SD.Next on a CPU-only box with no access to Hugging Face.
Output is deterministic (fixed seed) so before/after image hashes can be compared.

Usage: venv/bin/python .github/skills/perf-sandbox/scripts/make_tiny_sd.py [output_folder]
Then select it with sd_model_checkpoint "Diffusers/tiny-sd" (settings, config.json, or POST /sdapi/v1/options).
"""
import os
import sys
import json
import string
import torch

out = sys.argv[1] if len(sys.argv) > 1 else 'models/Diffusers/tiny-sd'
os.makedirs(out, exist_ok=True)
torch.manual_seed(0)

from diffusers import StableDiffusionPipeline, UNet2DConditionModel, AutoencoderKL, EulerDiscreteScheduler # pylint: disable=wrong-import-position
from transformers import CLIPTextConfig, CLIPTextModel, CLIPTokenizer # pylint: disable=wrong-import-position

# tokenizer: character-level clip-style bpe vocab with no merges
chars = list(string.ascii_lowercase + string.digits + string.punctuation)
vocab = {}
for c in chars:
    vocab[c] = len(vocab)
for c in chars:
    vocab[c + '</w>'] = len(vocab)
vocab['<|startoftext|>'] = len(vocab)
vocab['<|endoftext|>'] = len(vocab) # highest id, same as real clip, so argmax pooling picks eos
tok_dir = os.path.join(out, 'tokenizer')
os.makedirs(tok_dir, exist_ok=True)
with open(os.path.join(tok_dir, 'vocab.json'), 'w', encoding='utf8') as f:
    json.dump(vocab, f)
with open(os.path.join(tok_dir, 'merges.txt'), 'w', encoding='utf8') as f:
    f.write('#version: 0.2\n')
try:
    tokenizer = CLIPTokenizer(os.path.join(tok_dir, 'vocab.json'), os.path.join(tok_dir, 'merges.txt'), model_max_length=77)
except Exception as e:
    print('slow tokenizer signature failed, trying keyword form:', e)
    tokenizer = CLIPTokenizer(vocab=vocab, merges=[], model_max_length=77)
print('tokenizer:', type(tokenizer).__name__, 'vocab=', len(vocab), 'sample=', tokenizer('a photo of a cat', padding='max_length', max_length=77, truncation=True).input_ids[:12])

text_config = CLIPTextConfig(
    bos_token_id=vocab['<|startoftext|>'],
    eos_token_id=vocab['<|endoftext|>'],
    pad_token_id=vocab['<|endoftext|>'],
    hidden_size=32,
    intermediate_size=64,
    layer_norm_eps=1e-05,
    num_attention_heads=4,
    num_hidden_layers=3,
    max_position_embeddings=77,
    vocab_size=len(vocab),
)
text_encoder = CLIPTextModel(text_config)

unet = UNet2DConditionModel(
    block_out_channels=(32, 64),
    layers_per_block=1,
    sample_size=64,
    in_channels=4,
    out_channels=4,
    down_block_types=('DownBlock2D', 'CrossAttnDownBlock2D'),
    up_block_types=('CrossAttnUpBlock2D', 'UpBlock2D'),
    cross_attention_dim=32,
    attention_head_dim=8,
)

vae = AutoencoderKL(
    block_out_channels=[32, 32, 64, 64], # four levels so the vae scale factor is 8 like real sd
    in_channels=3,
    out_channels=3,
    down_block_types=['DownEncoderBlock2D'] * 4,
    up_block_types=['UpDecoderBlock2D'] * 4,
    latent_channels=4,
    layers_per_block=1,
    sample_size=512,
    scaling_factor=0.18215,
)

scheduler = EulerDiscreteScheduler(beta_start=0.00085, beta_end=0.012, beta_schedule='scaled_linear', num_train_timesteps=1000)

pipe = StableDiffusionPipeline(
    unet=unet,
    vae=vae,
    text_encoder=text_encoder,
    tokenizer=tokenizer,
    scheduler=scheduler,
    safety_checker=None,
    feature_extractor=None,
    requires_safety_checker=False,
)
pipe.save_pretrained(out)
params = sum(p.numel() for m in (unet, vae, text_encoder) for p in m.parameters())
print(f'saved: {out} params={params}')
print(open(os.path.join(out, 'model_index.json'), encoding='utf8').read())
