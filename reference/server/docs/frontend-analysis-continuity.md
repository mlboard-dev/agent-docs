> 来源：[server/docs/frontend-analysis-continuity.md](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/docs/frontend-analysis-continuity.md) · `15f9b75`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# Analysis continuity and typed fields

2026-10-26 module changelog (B2/B5/U2/U3/P5).

## Fields and local failures

`FieldRef` v1 is an encoded string: `field:v1:` + `encodeURIComponent(canonical JSON)`.
The canonical object key order uses JavaScript `<` / `>` comparison, independent of browser locale.
The decoded strict union is:

```ts
type FieldRef =
  | { version: 1; kind: "config"; pointer: string }
  | { version: 1; kind: "table_column"; name: string }
  | { version: 1; kind: "metadata"; name: "run" | "run_id" | "step" }
  | { version: 1; kind: "metric"; name: string; context: object;
      stat: "last" | "min" | "max" };
```

Config pointers use RFC 6901 escapes (`/a~1b` differs from `/a/b`). Metric context keeps JSON types and nested structure. For run-row chart options (`x_field`, `y_field`, `group_by`, `label_field`, `dimensions`, `axis_scales`, `inverse_axes`), agents should supply these encoded identities; raw table column names continue to work. Existing dotted/label fields resolve only when they uniquely identify a current field. Ambiguity fails locally and asks for a new selection; it never rewrites the stored definition.

Parameter labels omit the `config:` protocol prefix: simple keys appear as `lr` or `optimizer.lr`; literal punctuation keys use bracket notation, so `["optimizer.lr"]` remains distinct. Field descriptions retain the full JSON Pointer. This changes labels, not stored field identities or legacy resolution.

Table snapshots use a canonical typed tuple containing project/run/incarnation, metric/context and logical stream. Delimiters in names cannot merge different streams; reordered context keys identify the same stream, while number/string context values remain different. User columns are stored as `table_column` references and auxiliary run/Step data as `metadata` references. User columns named `$run`, `$step`, `__proto__`, or even an entire valid encoded FieldRef remain literal columns. Legacy strings resolve only to one current candidate; a collision with auxiliary metadata or another encoded identity is a local ambiguity error. Native table headings and CSV retain the literal user column names. Compare definitions continue to accept only config/metric identities.

Analysis-wide zoom reset first updates every remembered session and every panel's pending saved interaction, including filtered, paged and unmounted panels. It clears X/Y ranges and undo history while retaining hidden/solo selection. An account/origin/analysis-scoped reset marker suppresses stale saved-range fallback for panels not previously mounted. Mounted readers cancel pending viewport timers; a generation check rejects writes from an older Plot, including after permission/cache clearing. Reset listeners also reconcile a reset that happened between render and registration. These are bounded in-memory reading preferences; no frames or credentials are stored. The separate v5 design explores explicit global-reset wording and other new scope controls before product UI changes.

Derived config traversal is bounded to 32 levels / 10,000 nodes and uses an iterative validator. Config raw view/download is reachable before derivation, including old deep JSON. A local React boundary contains config, comparison and panel errors while preserving navigation and other panels. Cache/list/selection byte estimates use an iterative compact-JSON counter, so old deeply nested metadata does not fail during cache serialization. Cache estimation failures bypass caching and preserve the successful response.

## Saved comparison definitions

`dashboard.spec.view.analysis` stores `mlboard.compare/v1`: baseline `{run_id,run_incarnation}` or `null`, statistic, difference-only, typed field directions (`up|down`) and optional visible field identities. Directions and visibility are limited to 200 entries; unknown properties/versions and duplicate equivalent field identities fail validation. The surrounding dashboard retains fixed incarnation pins or a dynamic selector, personal/project visibility and existing `If-Match` draft/conflict behavior. A changed/missing baseline never silently becomes another saved baseline.

This stores a live definition, not downloaded results or a frozen snapshot. Saved comparisons use the same dashboard APIs and can be reopened, adjusted, copied and saved. Public links currently publish the explicitly previewed run projection; they do not publish a saved comparison definition. The share dialog states this limitation.

The main navigation/save flow consistently calls these definitions “分析方案” / “保存分析方案”; the comparison dialog may use “保存比较方案”. A revision conflict retains the draft and offers inspection or a separate copy. Copy creation has its own action error, so an earlier update conflict does not appear as a new copy-save failure.

Disposable comparison controls use account/project-scoped session state (30-minute TTL, 100 scopes, 512 KiB). Run links carry a validated internal source path plus bounded scroll/anchor information through Run tabs. Returning restores the task; direct Run URLs retain their project fallback. Chart interaction persistence and panel animations are maintained by the chart module.

Temporary focus layout hides both navigation rails while preserving filters and selection. It is scoped to the current account and analysis task, keeps ordinary navigation on detail/admin pages, and does not overwrite the user's normal sidebar preferences. Charts/Runs/Compare share the project scope; a saved dashboard has its own scope. Mobile disables both the control and effective focus state while retaining the desktop preference for a return to wider layout.

Dashboard save/copy readers are bound to the exact draft object that installed them. Compare always saves its current definition; a chart reader left behind by an advanced-JSON or collaboration mode change cannot overwrite it. Panel edits clear only the edited panel's persisted interaction when its coordinate/data identity changes. Titles, layout and line styling retain interaction. The same exported identity is used by the chart session key so a run-row field change does not recover an incompatible in-memory viewport.

Initial chart snapshots compare JSON values independently of object key insertion order. Loading an interaction serialized by Go must not mark an unchanged saved definition dirty merely because the browser exports the same keys in another order. Existing scope-local display preferences can still produce a real local adjustment; initialization does not silently discard them or change section-default semantics.

User-triggered card expansion animates actual card position and size over 240ms, with the section boundary on the same timeline. It never scales the Canvas or heading. A row is cleared before widening a later card; unsafe custom layouts use their natural final grid. If needed to keep the heading and up to 120px of plot readable, scrolling follows the same geometry phases instead of snapping after completion. Restore only reveals a clipped heading; browser scroll clamping during a shrinking layout is handled separately from user scrolling. Wheel, touch scrolling, scrolling keys and scrollbar use take priority. Reversal, section collapse, source/layout replacement, resize and unmount release temporary geometry; reduced motion uses the final layout immediately. Saved expansion and asynchronous data never initiate scrolling.

`ReadFreshness` separates connection state, reading/refresh failure, pause and the last successful HTTP/cache receipt. Cache hits retain the cache entry's original confirmation time. A zoomed view uses the represented detail result's confirmation, including a retained detail result, rather than a newer overview receipt. A transient failed refresh preserves the previous confirmation time. This timestamp does not claim that a Canvas has finished drawing; rendering confirmation needs the chart pipeline's own evidence.

Access failures (401/403/404) clear the affected confirmed values/time, chart session and retained detail display. Retries keep the refusal until a successful authorized response; a later 500 does not restore the old picture. Private cached responses are silently evicted, and pending responses authorized before the failure are removed from the join map without being aborted: a remounted panel must make a fresh authorized request, and an older late result cannot refill its cache. Ordinary network/500/429 failures without prior access loss keep the previously confirmed view.

## Candidates and selection

Filters define candidates independently of the current selection. The shared bar keeps the selected count and color dots; its existing selection dialog reports matching / retained outside filters / unverified identities. Missing from the first loaded page is never treated as a mismatch. The dialog provides verification, add-all-matches and replace-with-matches. Full candidate actions follow actual server pages with cancellation/progress and existing browser budgets. Budget details appear on failure, rather than as permanent interface instructions. Folder-wide selection explicitly confirms inclusion of runs outside current filters.

## CSV and raw values

Default CSV export quotes cells and prefixes formula/control-character text with an apostrophe. Actual numeric negatives remain numeric. Run, comparison and frame exports also provide original-value JSON. Unit tests verify formula prefixes, whitespace/control characters, quoting and original values. No real Microsoft Office Excel, LibreOffice or Numbers open/save/reopen acceptance was performed; the unit tests do not establish those applications' behavior.

## Bounded reads

Normal list continuation appends only `next_cursor`. Reset, membership changes, resume or an expired cursor reconcile the loaded bounded chain. Ten ordinary one-row pages require ten reads, compared with the previous repeated-chain total of 55; this is a functional request-count test, not a throughput benchmark.

Run summary hydration follows intersecting table rows plus a small page-local buffer. Loading summaries for all currently loaded rows is explicit; metric sorting and CSV stay disabled until all loaded summaries succeed. Cancellation, returned revision consistency and incarnation-specific caches are retained.

The request queue reserves one slot for interaction work (desktop total 4, phone total 2), schedules foreground before background, and ages waiting work to equal priority after bounded waiting. A continuous-interaction regression verifies that background reads still progress. Queue time counters are available via `requestQueueDiagnostics()`.

Series catalog identity excludes point revisions and includes run incarnation. The last confirmed catalog remains visible during reconciliation. New metric discovery uses 30-second periodic refresh, project reset/membership refresh, foreground resume and manual refresh; the backend currently has no catalog revision protocol. This is a bounded fallback, not a claim of immediate new-metric discovery.

Project/Run charts and structured evaluation distinguish an unconfirmed catalog from a confirmed empty one. A stable loading/error placeholder replaces the false empty state; existing cards remain visible when catalog reconciliation fails. Retries use the existing catalog resource.

The P7 client review adds caller row and full reconstructed byte checks before retaining a frame baseline. A dedicated budget error cannot trigger an extra read. An advertised hint can recover once from schema `validation_error` or a malformed/missing baseline; HTTP query-budget/timeout/resource errors, throttling and authorization failures retain their original failure. Private in-flight responses, continuation pages and fallback attempts are fenced by the auth generation; public reads remain independent. Prototype-like column/row identities and explicit null/value-state gaps are covered by reconstruction tests. Optional identity construction first checks 64 KiB / 10,000 nodes; exceeding this skips compression while preserving the ordinary query. Baseline retention charges the encoded body, key and token together against its item/total limits. The optional protocol and server flag remain owned by the P7 module.

## Verification

Module tests cover collision/deep-data/raw JSON/CSV cases; comparison save/reopen resolution and CAS/ACL; candidate classification; pagination/cancellation; summary identity/visibility; locale-independent identities and queue starvation. Final commands and logs are recorded under `outputs/next-optimization-implementation/web/`. Root performs the integrated real-browser acceptance. No large-data performance claim is made here.

Root's isolated production-browser acceptance confirmed that a newly saved definition reopens with its window/solo intact and Save disabled. Access revocation removed the rendered chart and stayed blocked through retry/collapse/reopen; restoring membership required a successful authorized retry. A later 500 preserving that refusal is unit-tested rather than browser-simulated.

The earlier second-card expansion browser check retained the clicked heading at 302.59px and left about 373px of plot visible in a 720px viewport. Restore kept the heading below the workspace header. That check covered the previous implementation; the annotation follow-up below replaces the expansion transition. Neither check is a chart rendering/performance benchmark.

## Browser annotation follow-up

Hover now belongs to the current chart: its vertical pointer and tooltip show all visible logical curves at that coordinate, without dimming the other curves or broadcasting pointers to other cards. Clicking a plotted curve toggles solo; legend buttons independently show/hide curves, with a color swatch and highlighted label for each visible curve (no checkbox). From a solo view, clicking another legend adds it to the visible set. Buttons expose their state with aria-pressed and support keyboard activation. The reset beside the legend (also available in the chart menu) restores all curves without changing zoom. The former solo status strip is removed. Legacy `shared_cursor` remains readable to preserve saved-definition compatibility, but the cross-card relay and its settings control are removed. Zoom reset retains the circular arrow glyph in a square button immediately left of Expand; desktop controls are 28px, mobile 36px.

Every signed-in desktop page uses the same sidebar controls. Expanded navigation shows one row each for collapse, appearance/current theme, and account/display name; compact navigation retains their icon positions. Each navigation entry transitions its own hover/selected background, avoiding a transparent gap while waiting for a traveling indicator. Page content uses a brief opacity transition without translation; headings and navigation remain stationary. The mobile header retains its drawer/account/theme controls. The project split uses an explicit shrinkable grid row so its scroller cannot extend below the visible workspace.

Project Charts now use one native workspace scroll container for their title, tabs, filters and panels. Those controls scroll out naturally instead of permanently consuming chart height. The run rail stays usable within the remaining viewport, and source navigation saves/restores the actual outer scroller. Other project tabs retain their existing content scroll layout. Per-panel confirmation timestamps are no longer displayed: ordinary successful/background reads add no footer; initial loading, read failures and paused updates retain their status. Internal confirmation metadata and authorization/error handling are unchanged.

Classification pagination follows the locally inspected TensorBoard 2.20.0 layout: previous/next above and below each paginated category, with shared range/page controls. “每分类每页行数” selects 1/2/3/4/6 rows for all categories (default 3), saved as optional `view.presentation.display.rows_per_page`. Automatic layout uses the actual resolved CSS grid columns, including window/sidebar changes. Fixed layouts use the cards' natural starting rows: a card spanning several rows belongs to its starting row, and mixed-width rows are paginated by their actual membership rather than an average card count. Temporary expansion does not change that membership. Column changes keep the previously first visible card within the resulting page; search/group/depth/row-count changes reset pages, and shrinking contents clamp them. Bottom navigation returns to that category's heading.

Existing `panels_per_page` definitions and `panelsPerPage` browser preferences retain their original card-count behavior until a row count is explicitly selected. Their controls show the equivalent rounded-up row count for the current columns, including a temporary numeric option when needed; that option cannot write an out-of-range `rows_per_page`. Reading or saving an unchanged legacy definition does not migrate its stored pagination or mark it dirty. New row preferences take precedence when both fields exist. Page positions remain transient. At most 12 automatic columns and 6 selected rows create 72 placeholders per category; only the current page mounts placeholders, while Canvas instances retain the existing visibility gating and offscreen disposal. Grid observers detach on collapse, replacement and unmount, and ignore late callbacks from a previous scope.

Expansion now interpolates each card's real position and size directly between its current visible geometry and the natural destination for 240ms. The former collision-avoidance staging could briefly turn a multirow grid into a tall single-column stack, moving the section boundary and page scroll far beyond the final layout. The updated user-approved behavior allows brief card crossings, keeps the section height inside its start/end envelope, and advances only the final required scroll compensation on the same progress. Heading, plot and card remain one element; neither Canvas nor text is scaled. Rapid reversals start from the current geometry, and resize/unmount/reduced-motion paths release temporary styles. Targeted sampled-frame coverage includes 6/24/72-card expand/restore, monotonic height/scroll, and retained row pagination/visibility behavior. Earlier no-overlap browser evidence describes the previous policy; current integrated browser acceptance is recorded separately.

Runs follow controls now share the line with the experiment path rather than adding a row above it. Export actions consistently say “导出 CSV”; CSV formula/control-character escaping is unchanged.
