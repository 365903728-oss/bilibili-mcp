import { EventEmitter } from "node:events";
import https from "node:https";
import { PassThrough } from "node:stream";
import { describe, expect, it, vi } from "vitest";

import {
  isPublicIpAddress,
  pinnedHttpsFetch,
  resolvePinnedAddress,
  type AddressResolver,
} from "../src/security/pinned-https.js";

describe("pinned playback HTTPS", () => {
  it.each([
    "0.0.0.0",
    "10.0.0.1",
    "100.64.0.1",
    "127.0.0.1",
    "169.254.1.1",
    "172.16.0.1",
    "192.168.0.1",
    "198.18.0.1",
    "224.0.0.1",
    "::1",
    "fe80::1",
    "fc00::1",
    "2001:db8::1",
    "2002:0808:0808::1",
  ])("rejects special or non-routable address %s", (address) => {
    expect(isPublicIpAddress(address)).toBe(false);
  });

  it.each(["8.8.8.8", "1.1.1.1", "2606:4700:4700::1111"])(
    "accepts a globally routable address %s",
    (address) => {
      expect(isPublicIpAddress(address)).toBe(true);
    },
  );

  it.each([
    ["lower boundary", "198.18.0.0"],
    ["upper boundary", "198.19.255.255"],
  ])("classifies all-%s DNS answers as standard Fake-IP", async (_label, address) => {
    await expect(
      resolvePinnedAddress("cdn.bilivideo.com", async () => [
        { address, family: 4 },
      ]),
    ).rejects.toMatchObject({ name: "FakeIpDnsError" });
  });

  it("classifies a multi-answer candidate only when every answer is standard Fake-IP", async () => {
    await expect(
      resolvePinnedAddress("cdn.bilivideo.com", async () => [
        { address: "198.18.0.1", family: 4 },
        { address: "198.19.255.254", family: 4 },
      ]),
    ).rejects.toMatchObject({ name: "FakeIpDnsError" });
  });

  it.each(["198.17.255.255", "198.20.0.0"])(
    "does not classify adjacent address %s as standard Fake-IP",
    async (address) => {
      await expect(
        resolvePinnedAddress("cdn.bilivideo.com", async () => [
          { address, family: 4 },
        ]),
      ).resolves.toMatchObject({ address, family: 4 });
    },
  );

  it("does not classify mixed Fake-IP and other DNS answers as standard Fake-IP", async () => {
    for (const answers of [
      [
        { address: "198.18.0.1", family: 4 as const },
        { address: "8.8.8.8", family: 4 as const },
      ],
      [
        { address: "198.19.255.254", family: 4 as const },
        { address: "127.0.0.1", family: 4 as const },
      ],
    ]) {
      await expect(
        resolvePinnedAddress("cdn.bilivideo.com", async () => answers),
      ).rejects.toMatchObject({
        name: "Error",
        message: "Media hostname did not resolve to public addresses",
      });
    }
  });

  it("rejects empty, mixed-publicity, and resolver-failure answers", async () => {
    await expect(
      resolvePinnedAddress("cdn.bilivideo.com", async () => []),
    ).rejects.toThrow("public addresses");
    await expect(
      resolvePinnedAddress("cdn.bilivideo.com", async () => [
        { address: "8.8.8.8", family: 4 },
        { address: "127.0.0.1", family: 4 },
      ]),
    ).rejects.toThrow("public addresses");
    await expect(
      resolvePinnedAddress("cdn.bilivideo.com", async () => {
        throw new Error("synthetic resolver detail");
      }),
    ).rejects.toThrow("resolution failed");
  });

  it("pins the approved address, preserves TLS hostname, and strips credentials", async () => {
    const resolver: AddressResolver = vi.fn(async () => [
      { address: "8.8.8.8", family: 4 },
    ]);
    let capturedOptions: https.RequestOptions | undefined;
    const request = ((
      _url: URL,
      options: https.RequestOptions,
      callback: (incoming: PassThrough) => void,
    ) => {
      capturedOptions = options;
      const emitter = new EventEmitter() as EventEmitter & {
        end: () => void;
        destroy: (error?: Error) => void;
      };
      emitter.destroy = (error?: Error) => {
        if (error) queueMicrotask(() => emitter.emit("error", error));
      };
      emitter.end = () => {
        queueMicrotask(() => {
          const incoming = new PassThrough() as PassThrough & {
            statusCode: number;
            statusMessage: string;
            headers: Record<string, string>;
          };
          incoming.statusCode = 200;
          incoming.statusMessage = "OK";
          incoming.headers = { "content-type": "audio/mp4" };
          callback(incoming);
          incoming.end("audio");
        });
      };
      return emitter;
    }) as unknown as typeof https.request;

    const input = new Request(
      "https://cdn.bilivideo.com/audio.m4a",
      {
        headers: {
          Cookie: "SESSDATA=synthetic-secret",
          Authorization: "Bearer synthetic-secret",
          "Proxy-Authorization": "Basic synthetic-secret",
          "X-Test": "kept",
        },
      },
    );
    const response = await pinnedHttpsFetch(
      input,
      { headers: { "X-Test": "overridden" } },
      { resolver, request },
    );

    expect(await response.text()).toBe("audio");
    expect(resolver).toHaveBeenCalledOnce();
    expect(capturedOptions?.servername).toBe("cdn.bilivideo.com");
    expect(capturedOptions?.headers).toMatchObject({
      "x-test": "overridden",
    });
    expect(capturedOptions?.headers).not.toHaveProperty("cookie");
    expect(capturedOptions?.headers).not.toHaveProperty("authorization");
    expect(capturedOptions?.headers).not.toHaveProperty(
      "proxy-authorization",
    );

    await new Promise<void>((resolve, reject) => {
      const lookup = capturedOptions?.lookup;
      expect(lookup).toBeTypeOf("function");
      lookup!(
        "cdn.bilivideo.com",
        {},
        (error, address, family) => {
          try {
            expect(error).toBeNull();
            expect(address).toBe("8.8.8.8");
            expect(family).toBe(4);
            resolve();
          } catch (assertionError) {
            reject(assertionError);
          }
        },
      );
    });

    await new Promise<void>((resolve, reject) => {
      const lookup = capturedOptions?.lookup;
      expect(lookup).toBeTypeOf("function");
      lookup!(
        "cdn.bilivideo.com",
        { all: true },
        (error, addresses) => {
          try {
            expect(error).toBeNull();
            expect(addresses).toEqual([
              { address: "8.8.8.8", family: 4 },
            ]);
            resolve();
          } catch (assertionError) {
            reject(assertionError);
          }
        },
      );
    });
  });

  it("rejects non-media hosts before DNS or network dispatch", async () => {
    const resolver = vi.fn(async () => [
      { address: "8.8.8.8", family: 4 as const },
    ]);
    const request = vi.fn();

    await expect(
      pinnedHttpsFetch(
        "https://example.com/audio.m4a",
        {},
        {
          resolver,
          request: request as unknown as typeof https.request,
        },
      ),
    ).rejects.toThrow("approved media URL");
    expect(resolver).not.toHaveBeenCalled();
    expect(request).not.toHaveBeenCalled();
  });
});
