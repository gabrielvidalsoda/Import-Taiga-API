# Security Policy

## Supported Versions

This is a small utility script maintained on a single `main` branch. Only the
latest commit on `main` is supported — there are no maintained release
branches.

## Reporting a Vulnerability

This tool handles Taiga credentials (`.env`) and can write to a Taiga
project's issue tracker via the API. If you find a security issue — for
example, credentials being logged, written to disk, or leaked in an error
message — please **do not open a public issue**.

Instead, report it privately to the maintainer:

- Email: [gabrielvidalsoda@gmail.com](mailto:gabrielvidalsoda@gmail.com)

Please include:

- A description of the issue and its potential impact.
- Steps to reproduce it (redacting any real credentials/tokens).
- The version/commit you tested against.

You should receive an acknowledgement within a few days. Once the issue is
confirmed and fixed, we'll coordinate on disclosure and credit you if you'd
like.

## Scope Notes

- `.env` and `config.json` are local-only, gitignored files — they should
  never contain data you're not comfortable having on your own machine, but
  they are not sent anywhere except to the Taiga API you configure.
- The Taiga password is only used in-memory to obtain a session token; it is
  never written to disk by this tool.
