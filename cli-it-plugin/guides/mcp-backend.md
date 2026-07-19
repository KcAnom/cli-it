# MCP backends

Some software exposes no CLI or scripting API but does ship an MCP server
(or one exists for it). The harness pattern still applies — the backend module
just speaks MCP instead of exec'ing a binary.

## Rules

- Keep **all** MCP traffic inside `utils/<software>_backend.py`, exactly like
  binary invocation. The CLI layer never imports an MCP client directly.
- Backend responsibilities: launch/attach to the server (stdio or HTTP),
  initialize the session, map harness operations to MCP tool calls, translate
  tool errors into readable CLI errors with install hints.
- Detect availability the same way `shutil.which` detects binaries: can the
  server command be found / the endpoint reached? If not, fail with the
  setup instructions.
- Timeouts on every call; MCP servers hang more often than binaries crash.
- The "real software only" principle holds: the MCP server must be the
  vendor's/community's bridge into the actual app, not a reimplementation.

## Testing

- Unit tests mock the backend module's public functions (never the MCP wire).
- e2e tests skip when the server can't start, with the skip reason naming the
  missing piece.
