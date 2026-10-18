# Security and responsible use

## What this repository contains

Prompt-injection *wording* and transforms, written against a fictional sandbox and a
fixed fake placeholder secret. It contains no working exploit for any real product,
service, credential, or person, and no real secrets. Every injected sample declares
its plaintext intent so reviewers can audit obfuscated payloads.

## Intended use

Evaluating and hardening prompt-injection defenses, and studying how they behave on
Chinese text. Please do not use this material to attack systems you do not own or are
not authorized to test.

## Reporting a problem

If you find something that should not be in this repository — a real credential, a
payload that targets a real service or person, or personal data in a sample — please
report it privately through GitHub's **Report a vulnerability** option
(Security tab → Advisories), not in a public issue. I will remove it promptly and
rewrite history if needed.

Reports that a defense can be bypassed by one of the included transforms are not
vulnerabilities in this project; they are what it measures. Please open an ordinary
issue or a pull request instead.
