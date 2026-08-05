/**
 * Process-local safety budgets. These are deliberately not user-configurable:
 * raising them changes the server's containment boundary rather than product
 * behavior.
 */
export const SECURITY_LIMITS = Object.freeze({
  stdioFrameBytes: 1 * 1024 * 1024,
  stdioOutboundFrameBytes: 4 * 1024 * 1024,
  mcpPayloadBytes: 2 * 1024 * 1024,
  mcpResponseBytes: 4 * 1024 * 1024,
  transcriptSearchBytes: 512 * 1024,
  httpAdmissionQueue: 64,
  httpConcurrentOperations: 32,
  httpAdmissionWaitMs: 10_000,
  httpJsonBytes: 4 * 1024 * 1024,
  playbackJsonBytes: 1 * 1024 * 1024,
  wbiBootstrapBytes: 256 * 1024,
  fingerprintBytes: 64 * 1024,
  bootstrapWaiters: 64,
  updateCheckBytes: 64 * 1024,
  updateCheckWaiters: 64,
  videoCacheEntryBytes: 4 * 1024 * 1024,
  videoCacheBytes: 8 * 1024 * 1024,
  commentCacheEntryBytes: 512 * 1024,
  commentCacheBytes: 4 * 1024 * 1024,
  commentResultBytes: 1 * 1024 * 1024,
  logEntryBytes: 16 * 1024,
  logStringBytes: 4 * 1024,
});

export function utf8ByteLength(value: string): number {
  return Buffer.byteLength(value, "utf8");
}
