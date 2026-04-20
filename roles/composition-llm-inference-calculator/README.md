# LLM Inference Calculator

[llm-inference-calculator](https://github.com/alexziskind1/llm-inference-calculator) is a web tool for estimating LLM inference requirements including memory, compute, and throughput.

Built from source via the upstream Dockerfile (Vite/React → nginx).

## Ports

Internal port `80` (nginx). Exposed via Traefik at `llmcalc.<domain>`.

## DNS

Registers subdomain: `llmcalc`
