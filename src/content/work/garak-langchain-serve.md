---
title: garak — LangChain Serve generator
summary: An open-source contribution to NVIDIA's garak, the LLM vulnerability scanner. It lets garak probe any model or RAG chain deployed behind a LangChain Serve endpoint.
year: 2024
role: Open-source contributor
tags: [Python, LLM security, LangChain, Open source]
link: https://github.com/NVIDIA/garak/pull/588
order: 2
---

[garak](https://github.com/NVIDIA/garak) is NVIDIA's open-source scanner for large language models. It sends batteries of probes — prompt injection, jailbreaks, data leakage, toxicity and more — to a model and uses detectors to judge whether the replies show a weakness. Every model it talks to goes through a *generator*, a small adapter for one kind of backend.

## The gap

Many LLM applications aren't just a model. They're chains: a retriever, a prompt template and a model, deployed together with [LangChain Serve](https://python.langchain.com/docs/langserve/) as an HTTP API. garak could scan the model underneath, but not the application people actually ship, where the retrieval and prompting change how it behaves.

## What I added

[Pull request #588](https://github.com/NVIDIA/garak/pull/588), merged in April 2024, adds a `LangChainServeLLMGenerator`. You point garak at a deployment with one environment variable and it scans that chain like any other model:

<pre><code>export LANGCHAIN_SERVE_URI=http://127.0.0.1:8000/rag-chroma-private
garak --model_type langchain_serve --probes promptinject</code></pre>

The generator validates the URI, names itself after the deployed chain and calls the chain's `invoke` endpoint for each prompt. Errors are handled so that a long scan isn't lost over one bad reply: client errors and malformed or empty responses are logged and skipped, while server errors are raised. The PR also includes unit tests and adds a refusal phrase common to Gemini models to garak's mitigation detector, so those refusals are counted as the model declining.

The generator still ships with garak as `garak/generators/langchain_serve.py`.
