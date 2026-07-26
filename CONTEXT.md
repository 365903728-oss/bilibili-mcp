# Bilibili Content Extraction

This context defines the language used when reading navigable video content through the MCP server.

## Language

**Bilibili-native**:
The product boundary in which every public content capability operates on Bilibili Videos and Bilibili-origin evidence. Supporting another media platform belongs outside this product.
_Avoid_: Universal video MCP, cross-platform media gateway

**Video Discovery**:
A bounded Bilibili-native lookup that turns one topic query into a small ordered set of candidate Videos. It does not automatically retrieve evidence from those Videos or search creators, series, and collections.
_Avoid_: Recommendation engine, cross-video research, global search

**Video**:
A Bilibili work identified by one BVID. A Video may contain one or more Parts.
_Avoid_: Archive, post

**Part**:
One independently playable item within a Video, identified publicly by a one-based page number and internally by a CID.
_Avoid_: Episode, segment, P-video

**Subtitle Segment**:
One timed subtitle cue containing start time, end time, and text.
_Avoid_: Chapter, caption block

**Transcript Range**:
A requested time interval used to select overlapping Subtitle Segments from one Part.
_Avoid_: Chapter range, clip

**Transcript Match**:
A Subtitle Segment whose text contains a case-insensitive literal query after Transcript Range filtering. One Subtitle Segment counts as at most one match, even when the query occurs more than once.
_Avoid_: Semantic match, keyword occurrence

**Transcript Context**:
The bounded neighboring Subtitle Segments returned before and after one Transcript Match. Context stays inside the requested Transcript Range.
_Avoid_: Full transcript, Chapter

**Source URL**:
The canonical Bilibili browser URL for the selected Video Part. It preserves exact BVID casing and includes `p` only when Part identity must be explicit.
_Avoid_: Download URL, subtitle URL

**Timestamp URL**:
A Source URL with `t` set to a Transcript Match's start time, opening that evidence in its selected Part.
_Avoid_: Chapter link, inferred time

**Chapter**:
A named time interval supplied by Bilibili for one Part. Chapters are returned as provided and are never inferred by this server.
_Avoid_: Subtitle Segment, AI chapter
