# Substrate Compatibility Matrix

| Pro artifact | Bundled OSS primitive | Accepted external primitive | Behavior |
| --- | --- | --- | --- |
| internal RC | latest pinned public OSS primitive for the build context | same pinned version | compatible |
| internal RC | latest pinned public OSS primitive for the build context | missing | bundled_bootstrap |
| internal RC | latest pinned public OSS primitive for the build context | older/unknown | block unless explicit bundled override |
| internal RC | latest pinned public OSS primitive for the build context | newer/user-managed | do not downgrade; require compatibility confirmation |

Compatibility means the same data-local `.aethermind/` store remains readable and writable by OSS and Pro-bundled paths.

The bundled compatibility range is `>=0.1.0,<0.3.0`. Canonical writes use
`layers.aem`. A legacy `layers.jsonl` file remains a read-only prefix in the
unified result, followed by new AEM records. The coordinator never rewrites or
deletes the legacy file.

The OSS primitive is the public base proof and open-source concept. Pro builds above it and adapts the primitive as needed for commercial improvement without silently introducing version conflicts.
