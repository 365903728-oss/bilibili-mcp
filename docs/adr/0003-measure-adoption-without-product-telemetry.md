# ADR 0003: Measure Adoption Without Product Telemetry

Status: Accepted on 2026-09-04.

The project will judge adoption through Public Adoption Signals such as GitHub Stars, npm aggregate downloads, forks, and voluntary user issues or discussions. The MCP server and CLI will not add call tracking, unique-user identifiers, analytics beacons, or other product telemetry merely to measure growth. These public aggregates cannot prove active or unique usage, so they are directional signals rather than exact user counts.
