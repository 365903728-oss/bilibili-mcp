# Research Note: Bilibili Account Automation Policy

## Research Topic

- Topic: Official Bilibili position on automated account actions and creator workflows
- Date: 2026-09-04
- Owner: Codex
- Related task, PRD, ticket, or plan: Product-direction `grill-with-docs` interview and ADR 0002
- Refresh before: specifying or implementing any account mutation, creator publishing, comment, like, follow, danmaku, or account-management capability

## Question

Does Bilibili officially permit automated account actions, merely tolerate them, or subject them to policy and technical risk controls?

## Context

Why this matters for `@xzxzzx/bilibili-mcp`:

- The user wants broader adoption and is considering creator-oriented write capabilities while keeping the product primarily focused on reading through MCP and CLI.
- A public package must distinguish an officially authorized creator integration from an unofficial Cookie-authenticated Web action that happens to work technically.

What decision or implementation this may affect:

- Whether Account Mutation should ever enter the public tool surface, which actions are viable, and whether they require a separate official Open Platform adapter.

## Sources

| Source | Type | Date checked | Notes |
|--------|------|--------------|-------|
| [Bilibili User Service Agreement](https://www.bilibili.com/blackboard/protocal/licence.html) | official agreement | 2026-09-04 | Updated 2025-04-30; section 5.6(3) addresses unapproved automated programs and scripts |
| [Bilibili Open Platform Developer Service Agreement](https://open.bilibili.com/agreement/developer-service) | official agreement | 2026-09-04 | Updated 2025-05-28; application review, linked-UP authorization, permitted scope, data duties, and enforcement |
| [Bilibili Open Platform documentation index](https://open.bilibili.com/doc) | official documentation | 2026-09-04 | Lists account authorization, Video and article publish/delete/query, data access, live capabilities, sandbox, and webhooks |
| [Bilibili Open Platform Privacy Policy](https://open.bilibili.com/agreement/privacy-policy) | official policy | 2026-09-04 | Describes revocable UP authorization and associated application access to manuscript management |
| [Official creator-certification rules](https://www.bilibili.com/blackboard/era/6Zh6CzZtsy2TQDIg.html) | official rules | 2026-09-04 | Prohibits automated review manipulation, repetitive bulk posts, and machine-generated bulk publishing abuses |
| [Bilibili account punishment rules](https://www.bilibili.com/blackboard/blackroomrule_v17.html) | official rules | 2026-09-04 | Describes content removal and restrictions on publishing, comments, danmaku, messages, following, Favorites, and accounts |

## Findings

1. Bilibili's published policy is not a blanket tolerance of automation. The general user agreement says that automated programs, bots, crawlers, or scripts may not obtain platform services, content, or data without Bilibili's prior explicit written permission.
2. Bilibili provides a sanctioned automation route through its Open Platform. Developers and applications are reviewed, an UP account must explicitly associate with the application, permissions are scoped and revocable, and the public documentation advertises creator-oriented publication, deletion, query, data, and live capabilities.
3. Official permission is capability-specific. The sources reviewed support authorized manuscript/content management, but do not establish a general public authorization for Cookie-based automated comments, likes, follows, danmaku, or arbitrary consumer-account actions.
4. Community and creator rules expressly target automated review manipulation, metric inflation, repetitive or irrelevant bulk content, and other abuse. Published remedies include rejecting or deleting content and restricting or banning account functions.
5. Technical success is not policy permission. An unofficial Web endpoint may work at low volume and still be outside the published authorization path; HTTP risk controls, CAPTCHAs, rate limits, or delayed account enforcement can occur without public thresholds.

## Applicability To This Project

Current interpretation:

- Continue treating reading and account mutation as distinct capability families.
- If creator mutations are pursued, evaluate the official Open Platform first and bind every operation to the authorizing UP account and granted scope.
- Treat Cookie-authenticated Web mutations as policy and account-risk candidates, not as officially approved merely because another open-source project implements them.
- Do not describe any unofficial automation as “Bilibili-approved” without written authorization or an applicable official API contract.

Not established by this research:

- That every automated read or write request will be blocked or punished.
- The unpublished rate, behavior, device, or account signals used by Bilibili risk controls.
- That an Open Platform permission exists for comments, likes, follows, or danmaku beyond the capabilities visible in the reviewed official documentation.
- A legal conclusion for a specific deployment or business model.

## Decision Impact

Recommended project action:

- Keep Account Mutation outside ordinary read-tool expansion. If user demand supports creator workflows, start a separate discovery task around officially documented Open Platform publication and content management before considering Cookie-based social interactions.
- Require explicit confirmation, preview, idempotency, audit-safe results, and narrowly scoped credentials for any future mutation design.

Rules or files that may need updates if a mutation direction is approved:

- `CONTEXT.md`, a dedicated ADR, product requirements, tool schemas and handlers, credential architecture, user-facing permission documentation, security tests, and release acceptance.

## Risks And Unknowns

- Agreements and available Open Platform capabilities may change.
- Application review, eligible developer identity, scopes, quotas, audit requirements, and commercial restrictions require account-specific confirmation inside the Open Platform console.
- Bilibili does not publish a complete risk-control threshold model, so absence of enforcement during testing is weak evidence.

## Staleness Notes

Refresh this research when:

- any Account Mutation reaches requirements or implementation planning
- Bilibili updates its user agreement, Open Platform agreements, documentation, or community enforcement rules
- a specific Open Platform application and permission set becomes available for live verification

## Follow-Up

- [ ] Decide whether the first possible mutation track is officially authorized creator manuscript management or whether all mutations remain deferred while reading capabilities grow.
