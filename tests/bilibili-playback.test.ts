import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getPlaybackAudioSet,
  MAX_AUDIO_REPRESENTATIONS,
  MAX_AUDIO_URL_CANDIDATES,
  parsePlaybackAudioSet,
  validatePlaybackMediaUrl,
} from "../src/bilibili/playback.js";
import { SECURITY_LIMITS } from "../src/security/limits.js";
import { credentialManager } from "../src/utils/credentials.js";
import { AsrError } from "../src/utils/errors.js";

const AUDIO_HOST = "https://upos-sz-mirrorcoso1.bilivideo.com";

function representation(
  id: number,
  bandwidth: number,
  baseUrl = `${AUDIO_HOST}/audio.m4s?deadline=1&token=secret`,
) {
  return {
    id,
    bandwidth,
    mimeType: "audio/mp4",
    codecs: "mp4a.40.2",
    baseUrl,
    backupUrl: [
      `${AUDIO_HOST}/backup-1.m4s?deadline=1&token=secret`,
      `${AUDIO_HOST}/backup-2.m4s?deadline=1&token=secret`,
      `${AUDIO_HOST}/backup-3.m4s?deadline=1&token=secret`,
    ],
  };
}

afterEach(() => {
  credentialManager.clearCredentials();
});

describe("Bilibili playback audio selection", () => {
  it("selects the lowest positive bandwidth then numeric ID", () => {
    const result = parsePlaybackAudioSet({
      timelength: 120_000,
      dash: {
        audio: [
          representation(30280, 180_000),
          representation(30232, 67_000, `${AUDIO_HOST}/higher-id.m4s`),
          representation(30216, 67_000, `${AUDIO_HOST}/selected.m4s`),
        ],
      },
    });

    expect(result.durationSeconds).toBe(120);
    expect(result.candidates).toHaveLength(3);
    expect(result.candidates[0]).toMatchObject({
      representationId: 30216,
      bandwidth: 67_000,
      mimeType: "audio/mp4",
    });
    expect(result.candidates[0].url).toContain("selected.m4s");
  });

  it("treats a valid empty DASH audio list as unavailable without fabricating a URL", () => {
    expect(parsePlaybackAudioSet({ timelength: 1_000, dash: { audio: [] } })).toEqual({
      durationSeconds: 1,
      candidates: [],
    });
  });

  it("does not treat missing DASH metadata as a valid empty audio set", () => {
    expect(() => parsePlaybackAudioSet({ timelength: 1_000 })).toThrowError(
      expect.objectContaining({ code: "ASR_AUDIO_UNAVAILABLE" }),
    );
  });

  it("rejects unsupported audio representations", () => {
    expect(() => parsePlaybackAudioSet({
      dash: {
        audio: [{
          ...representation(1, 1),
          mimeType: "video/webm",
          codecs: "opus",
        }],
      },
    })).toThrowError(AsrError);
  });

  it("rejects more than 256 audio representations before normalization", () => {
    expect(() => parsePlaybackAudioSet({
      dash: {
        audio: Array.from(
          { length: MAX_AUDIO_REPRESENTATIONS + 1 },
          (_, index) => representation(index + 1, index + 1),
        ),
      },
    })).toThrowError(
      expect.objectContaining({ code: "ASR_LIMIT_EXCEEDED" }),
    );
  });

  it("rejects Parts longer than two hours", () => {
    expect(() => parsePlaybackAudioSet({
      timelength: 7_200_001,
      dash: { audio: [representation(1, 1)] },
    })).toThrow("7200-second");
  });

  it("accepts only HTTPS allowlisted CDN hosts", () => {
    expect(validatePlaybackMediaUrl(`${AUDIO_HOST}/audio.m4s`)).toContain("bilivideo.com");
    expect(() => validatePlaybackMediaUrl("http://upos.example.com/audio.m4s")).toThrowError(AsrError);
    expect(() => validatePlaybackMediaUrl("https://bilivideo.com.evil.test/audio.m4s")).toThrowError(AsrError);
    expect(() => validatePlaybackMediaUrl("https://user:pass@bilivideo.com/audio.m4s")).toThrowError(AsrError);
    expect(() => validatePlaybackMediaUrl("https://upos.bilivideo.com:8443/audio.m4s")).toThrowError(AsrError);
    expect(() => validatePlaybackMediaUrl("https://shared.akamaized.net/audio.m4s")).toThrowError(AsrError);
    expect(() => validatePlaybackMediaUrl("https://www.bilibili.com/audio.m4s")).toThrowError(AsrError);
  });

  it("ignores an unsafe backup when the selected base URL is valid", () => {
    const item = representation(1, 1);
    item.backupUrl[0] = "https://evil.test/audio.m4s?token=DO_NOT_LEAK";

    const result = parsePlaybackAudioSet({ dash: { audio: [item] } });

    expect(result.candidates[0].url).toContain("bilivideo.com");
    expect(result.candidates).toHaveLength(2);
  });

  it("returns at most three locations from the selected representation", () => {
    const item = representation(1, 1);
    item.backupUrl = Array.from(
      { length: 9 },
      (_, index) => `${AUDIO_HOST}/bounded-backup-${index}.m4s`,
    );

    const result = parsePlaybackAudioSet({ dash: { audio: [item] } });

    expect(result.candidates).toHaveLength(MAX_AUDIO_URL_CANDIDATES);
    expect(result.candidates.map((candidate) => candidate.url)).not.toContain(
      `${AUDIO_HOST}/bounded-backup-2.m4s`,
    );
  });

  it("keeps signed query values out of validation errors", () => {
    const signed = "https://evil.test/audio.m4s?token=TOP_SECRET_VALUE";
    try {
      validatePlaybackMediaUrl(signed);
      throw new Error("expected rejection");
    } catch (error) {
      expect((error as Error).message).not.toContain("TOP_SECRET_VALUE");
      expect((error as Error).message).not.toContain(signed);
    }
  });

  it("calls the first-party playurl endpoint with the resolved BVID/CID and Cookie only at the API layer", async () => {
    credentialManager.setCredentials({
      sessdata: "test-sessdata",
      bili_jct: "test-csrf",
      dedeuserid: "123",
      expiresAt: Date.now() + 60_000,
    });
    const fetchPlayurl = vi.fn().mockResolvedValue({
      timelength: 1_000,
      dash: { audio: [representation(1, 1)] },
    });

    await getPlaybackAudioSet("BV1T6PQzQErF", 12345, fetchPlayurl);

    expect(fetchPlayurl).toHaveBeenCalledOnce();
    expect(fetchPlayurl.mock.calls[0][0]).toBe("/x/player/playurl");
    expect(fetchPlayurl.mock.calls[0][1]).toEqual({
      bvid: "BV1T6PQzQErF",
      cid: 12345,
      fnval: 16,
      fnver: 0,
      fourk: 1,
    });
    expect(fetchPlayurl.mock.calls[0][2].Cookie).toContain("SESSDATA=");
    expect(fetchPlayurl.mock.calls[0][2].Cookie).not.toContain("audio.m4s");
    expect(fetchPlayurl.mock.calls[0][4]).toBe(
      SECURITY_LIMITS.playbackJsonBytes,
    );
  });
});
