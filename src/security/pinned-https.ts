import { promises as dns } from "node:dns";
import https from "node:https";
import { isIP, type LookupFunction } from "node:net";
import { Readable } from "node:stream";

import { createAbortError, throwIfAborted } from "./operation-context.js";

export interface ResolvedAddress {
  address: string;
  family: 4 | 6;
}

export type AddressResolver = (
  hostname: string,
) => Promise<ResolvedAddress[]>;

export class FakeIpDnsError extends Error {
  constructor() {
    super("Media hostname resolved only to the standard Fake-IP range");
    this.name = "FakeIpDnsError";
  }
}

function parseIpv4(address: string): number[] | null {
  if (isIP(address) !== 4) return null;
  const octets = address.split(".").map(Number);
  return octets.length === 4 ? octets : null;
}

function isPublicIpv4(address: string): boolean {
  const octets = parseIpv4(address);
  if (!octets) return false;
  const [a, b, c] = octets;
  if (a === 0 || a === 10 || a === 127) return false;
  if (a === 100 && b >= 64 && b <= 127) return false;
  if (a === 169 && b === 254) return false;
  if (a === 172 && b >= 16 && b <= 31) return false;
  if (a === 192 && b === 168) return false;
  if (a === 192 && b === 0 && c === 0) return false;
  if (a === 192 && b === 0 && c === 2) return false;
  if (a === 192 && b === 88 && c === 99) return false;
  if (a === 198 && (b === 18 || b === 19)) return false;
  if (a === 198 && b === 51 && c === 100) return false;
  if (a === 203 && b === 0 && c === 113) return false;
  if (a >= 224) return false;
  return true;
}

function isStandardFakeIpv4(address: string): boolean {
  const octets = parseIpv4(address);
  return octets !== null && octets[0] === 198 && (octets[1] === 18 || octets[1] === 19);
}

function parseIpv6(address: string): number[] | null {
  if (isIP(address) !== 6 || address.includes("%")) return null;
  let normalized = address.toLowerCase();
  const ipv4Match = /(?:^|:)(\d+\.\d+\.\d+\.\d+)$/.exec(normalized);
  if (ipv4Match) {
    const octets = parseIpv4(ipv4Match[1]);
    if (!octets) return null;
    const first = ((octets[0] << 8) | octets[1]).toString(16);
    const second = ((octets[2] << 8) | octets[3]).toString(16);
    normalized = normalized.slice(0, -ipv4Match[1].length) + `${first}:${second}`;
  }
  if ((normalized.match(/::/g) ?? []).length > 1) return null;
  const [leftText, rightText = ""] = normalized.split("::");
  const left = leftText ? leftText.split(":") : [];
  const right = rightText ? rightText.split(":") : [];
  if (
    [...left, ...right].some((part) => !/^[0-9a-f]{1,4}$/.test(part))
  ) {
    return null;
  }
  const missing = 8 - left.length - right.length;
  if (
    (normalized.includes("::") && missing < 1) ||
    (!normalized.includes("::") && missing !== 0)
  ) {
    return null;
  }
  return [
    ...left.map((part) => Number.parseInt(part, 16)),
    ...Array.from({ length: missing }, () => 0),
    ...right.map((part) => Number.parseInt(part, 16)),
  ];
}

function isPublicIpv6(address: string): boolean {
  const words = parseIpv6(address);
  if (!words) return false;
  // Only globally routable 2000::/3 addresses are eligible.
  if ((words[0] & 0xe000) !== 0x2000) return false;
  // Documentation, benchmarking, Teredo, ORCHID and 6to4 are not direct
  // globally-routable CDN endpoints and can encode special destinations.
  if (words[0] === 0x2001 && words[1] === 0x0db8) return false;
  if (words[0] === 0x2001 && words[1] === 0x0002) return false;
  if (words[0] === 0x2001 && words[1] === 0x0000) return false;
  if (
    words[0] === 0x2001 &&
    (words[1] & 0xfff0) === 0x0010
  ) {
    return false;
  }
  if (
    words[0] === 0x2001 &&
    (words[1] & 0xfff0) === 0x0020
  ) {
    return false;
  }
  if (words[0] === 0x2002) return false;
  return true;
}

export function isPublicIpAddress(address: string): boolean {
  const family = isIP(address);
  if (family === 4) return isPublicIpv4(address);
  if (family === 6) return isPublicIpv6(address);
  return false;
}

const defaultResolver: AddressResolver = async (hostname) => {
  const answers = await dns.lookup(hostname, {
    all: true,
    verbatim: true,
  });
  return answers
    .filter((answer): answer is { address: string; family: 4 | 6 } =>
      answer.family === 4 || answer.family === 6
    )
    .map((answer) => ({
      address: answer.address,
      family: answer.family,
    }));
};

export async function resolvePinnedAddress(
  hostname: string,
  resolver: AddressResolver = defaultResolver,
): Promise<ResolvedAddress> {
  let answers: ResolvedAddress[];
  try {
    answers = await resolver(hostname);
  } catch {
    throw new Error("Media hostname resolution failed");
  }
  if (
    answers.length > 0 &&
    answers.length <= 32 &&
    answers.every(
      (answer) => answer.family === 4 && isStandardFakeIpv4(answer.address),
    )
  ) {
    throw new FakeIpDnsError();
  }
  if (
    answers.length === 0 ||
    answers.length > 32 ||
    answers.some(
      (answer) =>
        (answer.family !== 4 && answer.family !== 6) ||
        isIP(answer.address) !== answer.family ||
        !isPublicIpAddress(answer.address),
    )
  ) {
    throw new Error("Media hostname did not resolve to public addresses");
  }
  return answers[0];
}

export interface PinnedHttpsFetchOptions {
  resolver?: AddressResolver;
  request?: typeof https.request;
}

export async function pinnedHttpsFetch(
  input: string | URL | Request,
  init: RequestInit = {},
  options: PinnedHttpsFetchOptions = {},
): Promise<Response> {
  const url = new URL(
    input instanceof Request ? input.url : input.toString(),
  );
  if (
    url.protocol !== "https:" ||
    url.port !== "" ||
    url.username !== "" ||
    url.password !== "" ||
    !(
      url.hostname.toLowerCase() === "bilivideo.com" ||
      url.hostname.toLowerCase().endsWith(".bilivideo.com") ||
      url.hostname.toLowerCase() === "bilivideo.cn" ||
      url.hostname.toLowerCase().endsWith(".bilivideo.cn")
    )
  ) {
    throw new Error("Pinned HTTPS requires an approved media URL");
  }
  const method =
    init.method ?? (input instanceof Request ? input.method : "GET");
  if (method.toUpperCase() !== "GET") {
    throw new Error("Pinned HTTPS only supports GET");
  }
  const signal =
    init.signal ?? (input instanceof Request ? input.signal : undefined);
  throwIfAborted(signal ?? undefined);
  const pinned = await resolvePinnedAddress(
    url.hostname,
    options.resolver,
  );
  throwIfAborted(signal ?? undefined);

  const headers = new Headers(
    input instanceof Request ? input.headers : undefined,
  );
  if (init.headers !== undefined) {
    new Headers(init.headers).forEach((value, key) => {
      headers.set(key, value);
    });
  }
  headers.delete("cookie");
  headers.delete("authorization");
  headers.delete("proxy-authorization");
  const requestImpl = options.request ?? https.request;
  const lookup: LookupFunction = (_hostname, lookupOptions, callback) => {
    if (lookupOptions.all) {
      callback(null, [pinned]);
      return;
    }
    callback(null, pinned.address, pinned.family);
  };

  return await new Promise<Response>((resolve, reject) => {
    let settled = false;
    let request: ReturnType<typeof https.request>;
    const onAbort = () => {
      request?.destroy(createAbortError());
      if (!settled) {
        settled = true;
        reject(createAbortError());
      }
    };
    const removeAbortListener = () => {
      signal?.removeEventListener("abort", onAbort);
    };
    request = requestImpl(
      url,
      {
        method: "GET",
        headers: Object.fromEntries(headers.entries()),
        lookup,
        servername: url.hostname,
      },
      (incoming) => {
        if (settled) {
          incoming.destroy();
          return;
        }
        settled = true;
        const responseHeaders = new Headers();
        for (const [key, value] of Object.entries(incoming.headers)) {
          if (Array.isArray(value)) {
            for (const item of value) responseHeaders.append(key, item);
          } else if (value !== undefined) {
            responseHeaders.set(key, value);
          }
        }
        const status = incoming.statusCode ?? 502;
        const body =
          status === 204 || status === 304
            ? null
            : (Readable.toWeb(incoming) as ReadableStream<Uint8Array>);
        incoming.once("close", removeAbortListener);
        resolve(
          new Response(body, {
            status,
            statusText: incoming.statusMessage ?? "",
            headers: responseHeaders,
          }),
        );
      },
    );
    signal?.addEventListener("abort", onAbort, { once: true });
    request.once("error", () => {
      removeAbortListener();
      if (settled) return;
      settled = true;
      reject(new Error("Pinned HTTPS request failed"));
    });
    request.end();
  });
}
