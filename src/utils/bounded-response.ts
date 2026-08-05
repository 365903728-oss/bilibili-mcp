import {
  ResourceLimitError,
  UpstreamResponseError,
} from "./errors.js";

function parseDeclaredLength(value: string | null): number | null {
  if (value === null) return null;
  if (!/^\d+$/.test(value)) {
    throw new UpstreamResponseError(
      "Remote service returned an invalid content length",
    );
  }
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed)) {
    throw new UpstreamResponseError(
      "Remote service returned an invalid content length",
    );
  }
  return parsed;
}

export async function readBoundedResponseBytes(
  response: Response,
  maxBytes: number,
  resource: string,
): Promise<Buffer> {
  const declaredLength = parseDeclaredLength(
    response.headers.get("content-length"),
  );
  if (declaredLength !== null && declaredLength > maxBytes) {
    await response.body?.cancel();
    throw new ResourceLimitError(
      "Remote response exceeded its byte limit",
      resource,
      maxBytes,
    );
  }
  if (!response.body) {
    throw new UpstreamResponseError("Remote service returned an empty response");
  }

  const reader = response.body.getReader();
  const chunks: Buffer[] = [];
  let received = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      received += value.byteLength;
      if (received > maxBytes) {
        await reader.cancel();
        throw new ResourceLimitError(
          "Remote response exceeded its byte limit",
          resource,
          maxBytes,
        );
      }
      chunks.push(Buffer.from(value));
    }
  } finally {
    reader.releaseLock();
  }

  if (received === 0) {
    throw new UpstreamResponseError("Remote service returned an empty response");
  }
  return Buffer.concat(chunks, received);
}

export async function parseBoundedJsonResponse<T = unknown>(
  response: Response,
  maxBytes: number,
  resource: string,
): Promise<T> {
  const bytes = await readBoundedResponseBytes(response, maxBytes, resource);
  let text: string;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    throw new UpstreamResponseError("Remote service returned invalid UTF-8");
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    throw new UpstreamResponseError("Remote service returned invalid JSON");
  }
}
