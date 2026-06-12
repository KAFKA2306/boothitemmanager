# 0007: Shard Catalog and Search Index

## Status
Accepted

## Context
The project needs to deploy a static front-end via Cloudflare Pages and GitHub Pages. Cloudflare Pages enforces a strict 25 MiB maximum file size limit for static assets. As the booth item catalog grew, both `catalog_summary_part2.json` and `search_index.json` exceeded this limit (reaching ~26 MiB), causing deployments to fail.

Furthermore, reading a massive monolithic JSON file in the browser or via a Cloudflare Worker could hit the 128 MB memory limit per request.

## Decision
We will shard the large data files to keep each piece comfortably under the 25 MiB limit:
1. **Catalog Summary:** Sharded into chunks of 5,000 items each (`catalog_summary_partX.json`).
2. **Search Index:** Sharded into chunks of 10,000 items each (`search_index_partX.json`).

The UI (`index.html`) is updated to fetch the total number of shards from `metadata.json` (`catalog_shards`), and uses `Promise.all()` to concurrently fetch and combine these shards in the browser before rendering the interface.

## Consequences
- **Positive:** Cloudflare Pages deployments succeed as no file exceeds 25 MiB.
- **Positive:** Sharding allows for potential future parallelization or pagination in the client, keeping memory usage stable.
- **Negative:** The client must make multiple HTTP requests to fetch the complete index upon initial load. Given HTTP/2 multiplexing, the performance impact is negligible compared to downloading the same amount of data in a single file.