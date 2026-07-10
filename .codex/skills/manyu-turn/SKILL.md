---
name: manyu-turn
description: Use the Manyu affective core during an agent turn by submitting normalized events, reading partial interoception, and requesting arbitration before affect-mediated actions.
---

# Manyu Turn Protocol

Use this skill when a Codex turn should be mediated by Manyu.

1. Convert the user message, tool result, or outcome into a normalized Manyu event.
2. Call `manyu.submit_event`.
3. Read the returned interoception and arbitration result.
4. Keep self-report separate from authoritative affect.
5. For consequential action, call `manyu.arbitrate` with the candidate action before acting.
6. After responding or acting, call `manyu.record_action`; later call `manyu.record_outcome` when an outcome is known.

Safety rules:

- Manyu affect never expands authority.
- Do not use emotion language to create guilt, dependency, fear, or attachment pressure.
- If Manyu is unavailable, continue in neutral-degraded mode and do not invent hidden state.
