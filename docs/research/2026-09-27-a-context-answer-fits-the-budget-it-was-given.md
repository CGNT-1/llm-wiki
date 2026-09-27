# A context answer fits the budget it was given

Date: 2026-09-27. Audit 2026-09-27 B-12.

## What was wrong (measured on the live vault, 2026-09-27)

`get_context` for one decision page with `token_budget=2048` returned about 4.3 KB:
200 bytes of `text` and 4.1 KB of lists and traces. `pages` and `decisions` were the
same item twice; `retrieval_trace`, `materialization_trace` and `packing_trace` named
the same item a third, fourth and fifth time. The budget bounded only `text`, and it
was counted at one token per UTF-8 byte, so a 2048-token budget admitted about 500
tokens of text and dropped the page body (4.9 KB) as "budget". The same answer's cost
block counted `chars/4`, and code-navigation answers counted `ceil(bytes/4)`: three
estimators, two of them in one answer.

## Sources (fetched 2026-09-27)

1. tiktoken README — <https://github.com/openai/tiktoken>: "On average, in practice,
   each token corresponds to about 4 bytes."
2. Anthropic, Token counting — <https://platform.claude.com/docs/en/build-with-claude/token-counting>:
   "The token count is an **estimate**. In some cases, the actual number of input
   tokens used when creating a message might differ by a small amount." and "Claude
   4.7 and later models … use a newer tokenizer. The same input text produces
   approximately 30 percent more tokens than on earlier models." An exact count needs
   the provider's endpoint and the target model; an offline answer path can only
   estimate.
3. Petrov et al., "Language Model Tokenizers Introduce Unfairness Between Languages",
   arXiv:2305.15425 — <https://arxiv.org/abs/2305.15425>: "The same text translated
   into different languages can have drastically different tokenization lengths, with
   differences up to 15 times in some cases." Counting characters undercounts scripts
   that take several bytes per character (Cyrillic, CJK); counting bytes does not.
4. Anthropic, "Writing effective tools for agents" —
   <https://www.anthropic.com/engineering/writing-tools-for-agents>: "Tool
   implementations should take care to return only high signal information back to
   agents." and "We suggest implementing some combination of pagination, range
   selection, filtering, and/or truncation with sensible default parameter values for
   any tool responses that could use up lots of context."

## Decision

- One estimator for every answer: `answer_budget.estimate_text_tokens`, UTF-8 bytes
  divided by 4, rounded up (source 1; bytes rather than characters per source 3).
  `answer_budget.estimate_tokens` applies it to the serialized answer, the cost block
  names it `utf8_bytes/4`, and `code_navigation_renderer` imports it instead of
  keeping its own copy. For ASCII text the numbers equal the old `chars/4` up to
  rounding.
- `token_budget` bounds the whole `data` body of a `get_context` answer, as it
  already does for code answers. The text is packed into what the item list leaves:
  the answer is built, measured, and rebuilt with the text allowance reduced by the
  excess until it fits. Each pass strictly lowers the allowance, so it ends; when not
  even an empty text fits, the answer is an error naming the budget, never a silently
  larger answer. The compiler still counts UTF-8 bytes; it is handed four bytes per
  allowed token, the same quantity.
- One list: `items` names each packed item once. The typed copies (`pages`,
  `symbols`, `decisions`, `incidents`, `active_task`, `evidence`) and the retrieval and
  materialization traces are gone; `dropped` keeps what the packer left out and why.
- The prompt budgets of compile and the LLM client keep one token per byte: there the
  number guards a provider's hard context window, where over-counting is the safe
  side. That is a different quantity (a ceiling for a request), not an answer's size.

## Alternatives rejected

- Keep the byte-per-token count for answers: a 2048-token budget buys ~500 tokens of
  text (source 1 says a token is ~4 bytes).
- `chars/4` everywhere: undercounts Cyrillic answers about 2x (source 3), and this
  vault is written largely in Russian.
- Call the provider's count endpoint: needs a network round trip and a key on a local,
  offline answer path (source 2).

## Trade-off

The estimate is not the model's tokenizer; on newer Claude tokenizers the real count
can be ~30% higher (source 2). The budget is the product's estimate, and the answer
says so in `answer_cost.estimate_method`.
