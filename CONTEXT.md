# Bilibili Content Extraction

This context defines the language used when reading navigable video content through the MCP server.

## Language

**Bilibili-native**:
The product boundary in which every public content capability operates on Bilibili Videos and Bilibili-origin evidence. Supporting another media platform belongs outside this product.
_Avoid_: Universal video MCP, cross-platform media gateway

**Video Discovery**:
A bounded Bilibili-native lookup that turns one topic query into a small ordered set of candidate Videos. It does not automatically retrieve evidence from those Videos or search creators, series, and collections.
_Avoid_: Recommendation engine, cross-video research, global search

**Creator**:
A Bilibili account identified by one stable numeric `mid`. A display name is fuzzy and not unique; only the `mid` is identity.
_Avoid_: UP 主 display name, handle, author string

**Creator Search**:
A bounded Bilibili-native lookup that turns one query into a small ordered set of Creator candidates identified by `mid`. It never selects one candidate as the Creator and never crawls candidate Videos, Dynamics, transcripts, comments, or other per-candidate evidence.
_Avoid_: Creator resolution, auto-follow, per-candidate crawl

**Favorites Discovery**:
A read-only, bounded traversal of Favorite Memberships belonging to the currently authenticated Bilibili account. It discovers saved Videos but does not retrieve their evidence, synchronize a database, or generate knowledge notes.
_Avoid_: Favorites sync, knowledge base, batch transcript job

**Favorite Folder**:
A Bilibili Favorites container owned by the currently authenticated account.
_Avoid_: Playlist URL, knowledge collection, Watch Later

**Favorite Membership**:
The relationship between one Video and one Favorite Folder. The same Video in two Favorite Folders represents two Favorite Memberships.
_Avoid_: Unique Video, deduplicated result

**Favorites Cursor**:
An opaque continuation token that resumes a bounded Favorites Discovery traversal. It is not a Folder selector or account credential.
_Avoid_: Folder ID, page URL, sync checkpoint

**Creator Content Discovery**:
A bounded Bilibili-native lookup that turns one selected Creator `mid` into a live profile reading, a page of currently listable Video metadata, a Collection/Series container list, one selected container's Video Membership page, or one page of Creator Dynamics. It does not crawl the full catalog automatically and never fetches per-Video evidence.
_Avoid_: Creator crawl, full-catalog sync, per-video evidence fetch

**Creator Dynamic**:
A Bilibili Dynamic published or reposted by the selected Creator, identified by a decimal `dynamic_id`. Its bounded evidence may include text, image URLs and dimensions, referenced BVIDs, and an explicit original Dynamic relationship for reposts.
_Avoid_: Article extraction, downloaded image, OCR result, owned Video

**Dynamic Repost Relationship**:
The relationship between a reposting Creator Dynamic and its original Dynamic evidence. A referenced BVID records only a relationship visible in the Dynamic and does not prove Video ownership.
_Avoid_: Creator-owned Video, duplicate Dynamic, flattened repost text

**Collection**:
A Creator-organized Bilibili container identified by a `collection_id`. It is distinct from a Series, a multi-Part Video, and a Favorite Folder.
_Avoid_: Season, Favorite Folder, Part list

**Series**:
A Creator-organized Bilibili container identified by a `series_id`. It remains a separate upstream family from Collection even when both appear on one Bilibili space page.
_Avoid_: Collection alias, playlist, Favorite Folder

**Container Membership**:
The relationship between one Video and one Collection or Series. The same BVID in multiple containers represents multiple Memberships and is not globally deduplicated.
_Avoid_: Part, unique Video result, Favorite Membership

**Creator Content Cursor**:
An opaque continuation token that resumes a bounded Creator Video, container-list, selected-container Membership, or Dynamic traversal. A member cursor binds the Creator, section, and container identity; a Dynamic cursor binds the Creator and opaque upstream offset. It is not a selector or account credential.
_Avoid_: mid, container selector, page URL, sync checkpoint

**Video**:
A Bilibili work identified by one BVID. A Video may contain one or more Parts.
_Avoid_: Archive, post

**Part**:
One independently playable item within a Video, identified publicly by a one-based page number and internally by a CID.
_Avoid_: Episode, segment, P-video

**Subtitle Segment**:
One timed subtitle cue containing start time, end time, and text.
_Avoid_: Chapter, caption block

**Human Subtitle**:
A Bilibili-provided subtitle track that is not identified by Bilibili as an AI
recognition track. It remains distinct from both a Bilibili AI Subtitle and a
Local ASR Transcript.
_Avoid_: Native subtitle, trusted subtitle

**Bilibili AI Subtitle**:
A Bilibili-provided AI recognition track identified by an `ai-*` language code
(such as `ai-zh`, `ai-en`, `ai-ja`). It is Bilibili-origin evidence, but it is
not a Human Subtitle and is not assumed to be human-checked.
_Avoid_: Subtitle, Local ASR Transcript

**Local ASR Transcript**:
A transcript generated locally from the selected Part's audio by the managed
ASR runtime. It is distinct from every Bilibili-provided subtitle track.
_Avoid_: Bilibili AI Subtitle, fallback subtitle

**Subtitle Integrity**:
Whether a selected subtitle is usable as transcript evidence. Mere presence of
a subtitle track does not establish Subtitle Integrity.
_Avoid_: Subtitle availability, transcript quality score

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
