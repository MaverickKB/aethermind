# Substrate Compatibility Matrix

| Pro artifact | Bundled OSS primitive | Accepted external primitive | Behavior |
| --- | --- | --- | --- |
| internal RC | latest pinned public OSS primitive for the build context | same pinned version | compatible |
| internal RC | latest pinned public OSS primitive for the build context | missing | bundled_bootstrap |
| internal RC | latest pinned public OSS primitive for the build context | older/unknown | block unless explicit bundled override |
| internal RC | latest pinned public OSS primitive for the build context | newer/user-managed | do not downgrade; require compatibility confirmation |

Compatibility means the same data-local `.aethermind/` store remains readable and writable by OSS and Pro-bundled paths.

The OSS primitive is the public base proof and open-source concept. Pro builds above it and adapts the primitive as needed for commercial improvement without silently introducing version conflicts.
