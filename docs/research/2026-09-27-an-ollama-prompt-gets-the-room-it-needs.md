# An Ollama prompt gets the room it needs, or fails out loud

Date: 2026-09-27. Audit 2026-09-27, new finding after C-6.

## The problem (fact, read in the code)

`scripts/llm_client.py::_call_ollama` posts to Ollama's OpenAI-compatible
`/v1/chat/completions` and sends no context size. A compile draft is sized by
this product at up to 32 768 "tokens" of 1 UTF-8 byte each (C-6), i.e. up to
~32 KB of text. Ollama's own default window is 4 096 tokens on a machine with
less than 24 GiB of VRAM. A compile prompt larger than that is cut by the server,
and the client is told nothing: the answer comes back as if the whole prompt had
been read.

## Sources

1. Ollama, *OpenAI compatibility* (docs.ollama.com/api/openai-compatibility),
   read 2026-09-27: "The OpenAI API does not have a way of setting the context
   size for a model." The only remedy it gives is a Modelfile with
   `PARAMETER num_ctx <context size>` and `ollama create`.
2. Ollama, *Chat* API (docs.ollama.com/api/chat) and `docs/api.md` in the
   ollama repository, read 2026-09-27: `options.num_ctx` is "Context length size
   (number of tokens)", `options.num_predict` "Maximum number of tokens to
   generate"; `format` "Can be `json` or a JSON schema"; the response carries
   `prompt_eval_count` "Number of tokens in the prompt", `eval_count` and
   `done_reason`. `POST /api/show` returns `model_info` with a
   `<architecture>.context_length` key (example `"llama.context_length": 8192`).
3. Ollama, *FAQ* and *Context length* (docs.ollama.com/faq,
   docs.ollama.com/context-length), read 2026-09-27: "By default, Ollama uses a
   context window size of 4096 tokens"; the context-length page gives
   "< 24 GiB VRAM: 4k context", "24-48 GiB VRAM: 32k context", ">= 48 GiB VRAM:
   256k context". Both say it can be set with `OLLAMA_CONTEXT_LENGTH` on the
   server or `num_ctx` in the API options.
4. ollama/ollama issue #7907, server log quoted in the issue:
   `level=WARN source=runner.go:129 msg="truncating input prompt" limit=2048
   prompt=17624 keep=5 new=2048` — the truncation is a server-side warning only.
5. openclaw/openclaw issue #4028 (independent client, same failure): "context
   gets silently truncated to 4096 tokens regardless of configured context
   window size", log `"truncating input prompt" limit=4096 prompt=10573 keep=4
   new=4096`; cause: the OpenAI-compatible path "does not pass the
   `options.num_ctx` parameter to Ollama", "whereas the native Ollama API accepts
   an `options` object containing `num_ctx`".
6. ollama/ollama issue #9749: "Different extensions specifying varying `num_ctx`
   values cause Ollama to unload and reload the same model with different context
   sizes, resulting in significant delays".

Sources 1–3 are Ollama's primary documentation; 4–6 are independent reports of
the behaviour from three different clients. The docs disagree on the default
(4 096 in the FAQ, VRAM tiers on the context-length page, 2 048 in older
releases, as issue #7907 shows); the decision below does not depend on which is
current.

## Alternatives

- **A. Native `/api/chat` with `options.num_ctx` sized for this call.** Ollama's
  own documented per-request control. Chosen.
- **B. Keep `/v1` and detect truncation afterwards** by comparing
  `usage.prompt_tokens` with an estimate. Detects the loss but cannot prevent it:
  every oversized prompt would fail, although the model could have read it.
- **C. Ask the operator to set `OLLAMA_CONTEXT_LENGTH` or build a Modelfile.**
  A standing chore for the owner, and invisible when forgotten. Rejected.
- **D. Cut the prompt ourselves to fit the default.** Masking, forbidden by
  law 6. Rejected.

## Decision

- The Ollama backend calls `POST <host>/api/chat` (derived from the configured
  endpoint the same way the `/api/tags` probe already is), with
  `options.num_ctx`, `options.num_predict` = the call's `max_tokens`,
  `options.temperature`, `format` = the JSON schema when one is given, and
  `stream: false`. Usage is read from `prompt_eval_count`, `eval_count` and
  `total_duration`.
- **`num_ctx` has a stated basis.** A token of a byte-level tokenizer covers at
  least one UTF-8 byte, so the prompt's UTF-8 byte length bounds its token count
  from above — the same bound `context_budget.count_tokens` already uses for
  prompts. To it are added `max_tokens` (the answer must fit in the same window)
  and `OLLAMA_TEMPLATE_TOKENS = 256` for the chat template's role markers (a
  Qwen-style template adds a few dozen; the post-call check below catches an
  allowance that proves too small). The sum is rounded up to a power of two and
  never below 4 096 (Ollama's documented default, so a small call never shrinks
  the loaded window): source 6 shows every distinct `num_ctx` reloads the model,
  and powers of two keep the distinct values to a handful.
- **The model's own limit.** `POST /api/show` gives the model's trained
  `context_length`; the window is not raised past it. The operator can lower the
  ceiling further for a machine with little memory with
  `MEMORY_OLLAMA_MAX_CONTEXT` (a memory limit is an operating condition, law 9).
- **No silent cut.** When the reply shows the prompt filled the window
  (`prompt_eval_count` at or above the window less the answer's `max_tokens`),
  the call fails with the failure class `context_overflow` instead of returning
  an answer to a prompt the model never fully read. When the window was not
  capped the byte bound keeps a real prompt far below that line, so the check
  fires only on a capped window or a template allowance that proved too small.

## Trade-offs and what stays uncertain

- The byte bound over-reserves: a Russian text is ~3 bytes per token (C-6), so
  the window is up to ~3 times larger than the prompt needs, which costs memory
  for the KV cache. Measuring real tokens needs a tokenizer endpoint Ollama does
  not document; the ceiling variable is the operator's lever.
- `prompt_eval_count` does not count a prompt prefix Ollama reused from its
  cache, so when the window was capped a truncated prompt with a cached prefix
  could pass the check. It cannot pass when the window was not capped.
- One more local request per call (`/api/show`); it is not cached, so a model
  replaced under the same name is read fresh.
- Not run against a real Ollama: none is installed on this host. The request
  and response shapes are those of sources 1–2; the tests use a loopback stub.
- Thinking models: the request does not set `think`; how a given model's
  thinking text is returned is left as Ollama's default.
