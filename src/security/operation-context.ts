import { AsyncLocalStorage } from "node:async_hooks";

interface OperationContext {
  signal?: AbortSignal;
}

const operationContext = new AsyncLocalStorage<OperationContext>();

export function runWithOperationSignal<T>(
  signal: AbortSignal | undefined,
  operation: () => Promise<T>,
): Promise<T> {
  return operationContext.run({ signal }, operation);
}

export function getOperationSignal(
  explicitSignal?: AbortSignal,
): AbortSignal | undefined {
  return explicitSignal ?? operationContext.getStore()?.signal;
}

export function createAbortError(): DOMException {
  return new DOMException("The operation was aborted.", "AbortError");
}

export function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) {
    throw createAbortError();
  }
}

export function linkAbortSignal(
  source: AbortSignal | undefined,
  target: AbortController,
): () => void {
  if (!source) return () => {};
  if (source.aborted) {
    target.abort(createAbortError());
    return () => {};
  }
  const onAbort = () => target.abort(createAbortError());
  source.addEventListener("abort", onAbort, { once: true });
  return () => source.removeEventListener("abort", onAbort);
}

export function abortableDelay(
  milliseconds: number,
  signal?: AbortSignal,
): Promise<void> {
  throwIfAborted(signal);
  if (milliseconds <= 0) return Promise.resolve();

  return new Promise<void>((resolve, reject) => {
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, milliseconds);
    const onAbort = () => {
      clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
      reject(createAbortError());
    };
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}
