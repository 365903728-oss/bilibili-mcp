import { server } from "../../src/server.js";

type ServerWithRequestHandlers = {
  _requestHandlers?: Map<string, unknown>;
};

export function getMcpHandler<TRequest, TResponse>(
  method: string,
): (
  request: TRequest,
  extra?: { signal?: AbortSignal },
) => Promise<TResponse> {
  const handlers = (server as unknown as ServerWithRequestHandlers)
    ._requestHandlers;

  if (!handlers) {
    throw new Error("MCP SDK request handler map is not available");
  }

  const handler = handlers.get(method);
  if (!handler) {
    throw new Error(`${method} handler not registered`);
  }

  return handler as (
    request: TRequest,
    extra?: { signal?: AbortSignal },
  ) => Promise<TResponse>;
}
