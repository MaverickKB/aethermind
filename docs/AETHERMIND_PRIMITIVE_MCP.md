# AetherMind Primitive MCP Architecture

The AetherMind primitive MCP server is a neutral adapter over the OSS data-local primitive. The public AetherMind harness plugin has the same architectural status: it is a harness/substrate adapter, not the Pro architecture and not a distributed Pro runtime.

## Tool contract

Every tool takes explicit `data_root` or `root`. There is no hidden cwd assumption.

Read-safe tools:

- `status`
- `read_layers`
- future `read_texture`, `validate_store`, `manifest`, `export`

Write tools:

- `init_store`
- `write_layer`
- future `write_texture`, `import_layers`

Write tools are policy controlled by allowed roots, denied roots, init policy, and write-enabled mode.

## Policy errors

The MCP substrate reports bounded errors that Pro can map into CORTEX pressure codes:

- `data_root_required`
- `root_denied_by_policy`
- `root_not_allowed_by_policy`
- `mcp_write_tools_disabled`
- `mcp_init_disabled`
- `uninitialized_data_root`

## Pro relationship

Pro may ship or call this MCP-compatible substrate and may install, detect, or repair the public harness plugin when a harness needs it. Pro remains the single installed host coordinator above those adapters: Atlas host profile, Ember/CORTEX pressure and repair semantics, support/export, and harness-neutral Agent Comms for Hermes, Grok Build, Codex, Claude/Claude Code, and future harnesses.

Harness integration must be configurable. Commercial harnesses, custom harnesses, and bring-your-own local agents should use the same universal contract with configurable settings, custom resume-session definitions, and optional tracker/HUD status for last check-in or manual intervention. If a harness needs plugin-mediated access, Pro should detect, install, or repair the plugin without making the plugin Pro's implementation base.
