# Security Policy

## Supported versions

The latest minor release of each package (`soon-format` on PyPI,
`@soon-format/soon` and `@soon-format/cli` on npm) receives security fixes.

## Reporting a vulnerability

Please **do not** open a public issue for security reports. Instead, use
GitHub's private vulnerability reporting on this repository
(Security → Report a vulnerability), or email the maintainer at
yasinugur.cs@gmail.com.

You should receive an acknowledgement within 72 hours. Decoders treat all
input as hostile: any crash, hang, or memory blow-up on malformed input in
`decode()` is considered a security bug — please report it.
