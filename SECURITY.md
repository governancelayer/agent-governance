# Security Policy

Thank you for helping keep the Agent Governance Framework and its ecosystem secure.

## Reporting Security Issues

If you discover a security vulnerability in this repository, please report it through
the [GitHub Security Advisory process](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
for this repository.

Please **do not** report security vulnerabilities through public GitHub issues, discussions,
or pull requests.

## What to Include

To help us triage and respond quickly, please include:

- A description of the vulnerability
- Steps to reproduce the issue
- The potential impact
- Any suggested fixes (optional)

## Scope

This project currently contains specification documents, JSON schemas, and example
payloads. Security concerns most likely to be relevant include:

- Schema definitions that could enable injection or misuse when consumed by implementations
- Example payloads that demonstrate insecure patterns
- Documentation that recommends insecure practices

As the project grows to include reference implementations, the security scope will
expand accordingly.
