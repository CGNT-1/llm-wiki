# The redactor knows the missing shapes, in linear time

Date: 2026-09-27. Audit 2026-09-27, findings B-4 (second part: shapes that passed) and
B-6 (slow rules).

## What was wrong (reproduced)

- Passing through unredacted: `sshpass -p …`, `docker login -p …`, credentials in a URL
  query (`?api_key=`, `&access_token=`, a signed URL's `sig=`), Google OAuth access tokens
  (`ya29.…`), Telegram bot tokens, Slack incoming-webhook URLs, and a PEM private key with
  no END line (the output of `head id_rsa`).
- Two rules backtracked quadratically. The URL-userinfo rule began with `\b`, so on
  `a.a.a…` the scheme run could start at every dot and was rescanned from each: 6.73 s on
  40 KB. The MySQL `-p` rule scanned lazily to the end of the line from every `mysql`:
  2.51 s on 40 KB of `mysql `.

## Alternatives considered

1. Keep one regex per command and add `sshpass`/`docker login` the same lazy way.
   Rejected: that multiplies the quadratic case.
2. Chosen: command passwords in one pass per line (`_redact_command_passwords`): find the
   command once, then the `-p` flag after it — attached only for MySQL clients (`-p db`
   prompts and names a database), attached or separated for `sshpass` and
   `docker login`; a quoted password is taken whole. The URL rule starts where no scheme
   character precedes (`(?<![a-z0-9+.-])`) instead of `\b`. New table rules for the other
   shapes; a PEM block with no END line is redacted to the end of the text (fail closed).

Measured after: 0.017 s (`a.` × 20 000) and 0.018 s (`mysql ` × 7 000); the 200 KB
adversarial cases in the test run in under 0.1 s each.

## Sources (fetched 2026-09-27)

- OWASP, ReDoS, https://community.owasp.org/attacks/Regular_expression_Denial_of_Service_-_ReDoS —
  "most Regular Expression implementations may reach extreme situations that cause them to
  work very slowly (exponentially related to input size)"; "if the input (token) fails to
  match, the engine goes back to previous positions where it could take a different path."
- sshpass(1), https://linux.die.net/man/1/sshpass — "-p password: The password is given on
  the command line." "The -p option should be considered the least secure of all of
  sshpass's options."
- Slack, Sending messages using incoming webhooks,
  https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks — URL shape
  `https://hooks.slack.com/services/` followed by a workspace id, a bot id and a 24-character secret; "Your
  webhook URL contains a secret. Don't share it online".
- Telegram Bot API, https://core.telegram.org/bots/api#authorizing-your-bot — "The token
  looks something like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`".

Limits touched, with their basis: the Telegram secret length `{30,}` (documented example
34, issued 35; below 30 a `12:30:45` clock would not match anyway); the ya29 length
`{20,}` keeps the prefix rules' floor.

## Guard

`tests/test_the_redactor_knows_the_missing_shapes.py`: every shape above is redacted and
four look-alikes are kept; every rule's own alphabet repeated to 200 KB is redacted
within `SHORT_TIMEOUT` (the old code took minutes). 11 of the tests fail on the previous
`secret_redact.py`.

## Files

- `scripts/secret_redact.py`
- `tests/test_the_redactor_knows_the_missing_shapes.py`
