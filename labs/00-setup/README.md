# Lab 0 — Setup Verification

## Purpose

Verify that the workspace environment is ready for the workshop: your personal schema exists, the shared M5 data is accessible, and the MMF skill is installed in Genie Code.

## What Databricks/MMF brings

- **Unity Catalog** provides per-user isolation with shared read access to the M5 dataset — no data copying, no permission headaches.
- **Genie Code skills** let you interact with the MMF pipeline through natural language instead of writing boilerplate code.

## Hints

- If the skill check fails, open Genie Code and ask: *"What skills do you have access to?"*
- Your user schema is derived from your email (e.g., `john_doe` for `john.doe@example.com`). All your outputs go there — nothing you do affects other participants.
- If tables are missing from `mmf.m5`, ask the instructor to re-run the data load.
