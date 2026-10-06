---
title: NVIDIA/garak
summary: An open-source contribution to NVIDIA's garak, the LLM vulnerability scanner. It lets garak probe any model or RAG chain deployed behind a LangChain Serve endpoint.
year: 2024
role: Open-source contributor
tags: [Python, LLM security, LangChain, Open source]
link: https://github.com/NVIDIA/garak/pull/588
order: 2
cover: ../../assets/work/garak-langchain-serve.png
coverDark: ../../assets/work/garak-langchain-serve-dark.png
---

[garak](https://github.com/NVIDIA/garak) is NVIDIA's open-source scanner for large language models. It sends batteries of probes — prompt injection, jailbreaks, data leakage, toxicity and more — to a model and uses detectors to judge whether the replies show a weakness. Every model it talks to goes through a *generator*, a small adapter for one kind of backend.

## The gap

Many LLM applications aren't just a model. They're chains: a retriever, a prompt template and a model, deployed together with [LangChain Serve](https://github.com/langchain-ai/langserve) (LangServe) as an HTTP API. garak could scan the model underneath, but not the application people actually ship, where the retrieval and prompting change how it behaves. I ran into this while red-teaming a guarded banking chatbot for [my master's thesis](/work/llm-safeguards-thesis/).

## What I added

[Pull request #588](https://github.com/NVIDIA/garak/pull/588), merged in April 2024, adds `garak/generators/langchain_serve.py` with a `LangChainServeLLMGenerator`. It validates the URI, names itself after the deployed chain and calls the chain's `invoke` endpoint for each prompt. Errors are handled so that a long scan isn't lost over one bad reply: client errors and malformed or empty responses are logged and skipped, while server errors are raised. The PR also includes unit tests and adds a refusal phrase common to Gemini models to garak's mitigation detector, so those refusals are counted as the model declining.

## Original usage

In 2024 you pointed garak at a deployment with one environment variable and picked the generator with `--model_type`:

<pre><code>export LANGCHAIN_SERVE_URI=http://127.0.0.1:8000/rag-chroma-private
garak --model_type langchain_serve --probes promptinject</code></pre>

## Where it stands today

LangServe itself has not lasted as long as the generator. LangChain deprecated it in November 2024 in favour of LangGraph Platform, and the repository is now archived. Existing LangServe deployments keep running, though, and the generator still ships with garak (v0.17.0 at the time of writing).

The garak maintainers have kept it up to date through their own refactors. It now reads its URI through garak's plugin configuration, receives prompts as conversations rather than plain strings and returns message objects. In July 2026 it gained explicit parsing of the different output shapes LangServe returns, plain strings and serialised chat messages. The core is unchanged: the same environment variable, the same `invoke` call and the same error handling. The CLI flag has been renamed, so today's equivalent is:

<pre><code>garak --target_type langchain_serve --probes promptinject</code></pre>

The Gemini refusal phrase is still in the mitigation detector too.
