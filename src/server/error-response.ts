import { buildStructuredErrorPayload } from "../utils/error-guidance.js";
import { ValidationError } from "../utils/errors.js";
import { ResourceLimitError } from "../utils/errors.js";
import { SECURITY_LIMITS } from "../security/limits.js";

export function buildValidationErrorPayload(
  error: unknown,
): Record<string, unknown> {
  // Only typed expected validation failures keep their controlled message.
  // Unexpected exceptions must never leak engine wording into MCP output.
  const validationError =
    error instanceof ValidationError
      ? error
      : new ValidationError("Invalid input");

  return buildStructuredErrorPayload(
    validationError,
  ) as unknown as Record<string, unknown>;
}

export function buildGenericErrorPayload(
  error: unknown,
): Record<string, unknown> {
  return buildStructuredErrorPayload(error) as unknown as Record<string, unknown>;
}

export function toTextContent(payload: unknown) {
  const text = JSON.stringify(payload, null, 2);
  if (Buffer.byteLength(text, "utf8") > SECURITY_LIMITS.mcpPayloadBytes) {
    throw new ResourceLimitError(
      "MCP payload exceeded its byte limit",
      "mcp_payload_bytes",
      SECURITY_LIMITS.mcpPayloadBytes,
    );
  }
  const result = {
    content: [
      {
        type: "text" as const,
        text,
      },
    ],
  };
  assertBoundedToolResult(result);
  return result;
}

export function toStructuredContent(payload: Record<string, unknown>) {
  const text = JSON.stringify(payload, null, 2);
  if (Buffer.byteLength(text, "utf8") > SECURITY_LIMITS.mcpPayloadBytes) {
    throw new ResourceLimitError(
      "MCP payload exceeded its byte limit",
      "mcp_payload_bytes",
      SECURITY_LIMITS.mcpPayloadBytes,
    );
  }
  const response = {
    content: [{ type: "text" as const, text }],
    structuredContent: payload,
  };
  assertBoundedToolResult(response);
  return response;
}

export function toErrorTextContent(payload: unknown) {
  const result = {
    ...toTextContent(payload),
    isError: true,
  };
  assertBoundedToolResult(result);
  return result;
}

function assertBoundedToolResult(result: unknown): void {
  if (
    Buffer.byteLength(JSON.stringify(result), "utf8") >
    SECURITY_LIMITS.mcpResponseBytes
  ) {
    throw new ResourceLimitError(
      "MCP response exceeded its byte limit",
      "mcp_response_bytes",
      SECURITY_LIMITS.mcpResponseBytes,
    );
  }
}
