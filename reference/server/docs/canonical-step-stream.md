> 来源：[server/docs/canonical-step-stream.md](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/docs/canonical-step-stream.md) · `15f9b75`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# Proven canonical and tail sampling

SQLite's streaming sampler started at `6b0d56e` and was integrated as `8555889`.
The PostgreSQL complete-canonical candidate starts at `335e2b7` and was integrated
as `49a941c`. The tail candidate reuses that same ordered stream after the existing
tail completeness proof. No schema, index, worker, cache, metadata join, winner
policy or public API changes are involved. Each candidate can be reverted without
a data migration.

## Scope and work bound

The existing raw `CountPoints` preflight, source budget, `ValidateRunReadRef`,
incarnation fence and read transaction remain authoritative. The stream is used
only for a published `materialized_revision` equal to captured R or an already
proved complete repaired relation. Exactly one session must be registered, the
logical primary must exist, and the accepted **per-run raw
source count is at most 250,000**. That includes all selected metric/context
tuples, not 250,000 per metric. Existing primary/session/producer and no-step
fallbacks remain in force. A larger admitted query keeps the SQL sampler; it is
not rejected or given a lower source count.

Each metric first uses the existing aggregate for exact canonical count,
endpoints and finite count. When it needs downsampling:

1. Read only `step_key,value,value_state` in canonical key order. For all-finite
   data this is one stream. If nonfinite values exist, a preliminary stream finds
   mandatory gap boundaries before the bucket count can be calculated.
2. Keep only mandatory steps and four candidates per bucket in Go. Memory is
   O(points_per_series), not O(source points). No full history of event metadata
   is retained in Go.
3. Return full metadata only for the selected steps through the existing complete
   canonical-key query. The final ordering is bounded by the selected
   output, rather than a full visible-source CTE.

The narrow reader independently stops at the source ceiling and refuses an
unexpected non-increasing logical step. Such an incomplete relation falls back
to the unchanged SQL sampler. A cancellation or SQL error is returned, never
converted to a partial sample. Query deadlines still apply to all phases.

## Tail proof and parameter handling

Streaming is downstream of the unchanged `SampleStep` admission checks. Repair
still requires a published checkpoint C, `0<C<R`, `C<=B<=R`,
`materialized_revision` in `{-1,C}`, and requested revision at least R. The
unchanged tail reader proves **all** relevant raw candidates in `(C,R]` fit the
4,096-record ceiling across the selected metric names, before filtering contexts
or workers. Incomplete tails, future builds, missing checkpoints, no-step and
multi-session cases retain their existing fallback. No allowance is increased.

`repairedStepRelation` still selects winners by ordinal/seq, removes only the
canonical steps actually replaced, and unions their immutable raw-key winners.
That produces unique logical steps. Late low-seq losers can leave the relation
without a prefix; this does not change their raw-source accounting. Sampling
does not construct or reinterpret the tail.

Every narrow query now uses `stepRelation.statement`: prefix SQL and its bound
arguments are included once, followed by the relation's ordinary arguments. The
aggregate, optional gap pass, bucket pass and unchanged metadata lookup all run
on the same `Read` transaction/queryer. Prefixes can be evaluated more than once,
but their captured snapshot and winner identities cannot change between passes.
The tail candidate only removes sampling's prefix/repair exclusions.

## Exactness

The raw `minMax` implementation remains the oracle. Step subtraction happens as
int63 before conversion to float; bucket division/multiplication follows the
same order, and the exact last endpoint is clamped to the last bucket. Tied
extrema retain the earliest step. Both sides of every finite/nonfinite or
nonfinite-state transition remain mandatory. All-nonfinite data is sampled by
the same rules. Exceeding `gap_boundaries` or `min_max_extrema` returns the same
budget error; neither case truncates output.

Selected integer keys originate from the validated relation. A `VALUES` relation
avoids bind-variable/compound-SELECT limits at the existing 100,000-point output
ceiling, with context cancellation checked while constructing it. The original
metadata lookup preserves session/producer/seq, ordinal, revision, time, unit,
value and state. Scanned diagnostics continue to report the accepted raw count;
input reports canonical count. Duplicate metric selectors remain set membership.

## Local correctness and plan evidence

Only small fixtures are used locally, not a load benchmark. Run from this source
checkout with the workspace environment:

```sh
export MLBOARD_ROOT=/path/to/mlboard
. "$MLBOARD_ROOT/scripts/env.sh"
go test -race ./internal/store ./internal/server \
  -run 'Test(Canonical(Stream|SQL|Tail)|LiveTail|PinnedTail|ProjectedQuery|QueryReadStrategy)' \
  -count=1 -v
```

Use the repository's isolated per-test PostgreSQL schema configuration for the
same command to verify the PostgreSQL stream and literal-key metadata lookup.
No DSN belongs in this document or a public log.

`TestCanonicalSQLSampleMatchesMinMaxV1` compares complete frames with raw v1 for
97-point waves, ties, gaps and sparse wide coordinates, including near MaxInt64,
five output budgets and bounded/unbounded viewports.
`TestCanonicalStreamMatchesCompleteFrames` compares complete query envelopes
with real worker projections: three metric/context tuples, reverse ingestion,
all-nonfinite data, adjacent nonfinite state changes, sparse gaps, tied extrema,
corrections, empty/single-point viewports, pinned old R and multi-session fallback.
The envelope includes event references, applied metadata and raw accounting.

`TestCanonicalStreamPostgresFreshIdentityWithoutStatistics` builds 1,028 canonical
points in one random, isolated test schema: analyze the old identity, then add a
fresh one with two contexts, without updating statistics. Autoanalysis is disabled
only for that per-test table so the fixture remains deterministic. The test
checks that the fresh incarnation is absent from MCV statistics, verifies exact
plateau keys and full event metadata, and uses pgx's query tracer to assert the
production call uses ordered narrow streams plus literal-key lookups, without
the old visible/stats/extrema SQL. Before enabling the PG branch this regression
fails because it observes the old bucket join. It is not a timing benchmark.

`TestCanonicalTailStreamUsesRealPrefixAndPropagatesCancellation` builds a genuine
repaired prefix with low-seq losers, high-seq replacements, a new step and a NaN.
It reads the real ordered relation, checks the winners and samples it. A wrapper
cancels a real driver query after its first row and waits for cancellation;
the sampler must return an error without a partial sample, close its rows and
permit a later transaction to write. `TestCanonicalTailStreamMatchesRawFramesForMixedWinners`
compares complete raw query envelopes for two contexts, gaps, checkpoint/partial
build states and a pinned old R while metadata advances. The existing tail
suite also covers exact 4,096-record admission/overflow, large VALUES parameter
sets, huge coordinates, future build fallback and a worker publishing while a
read snapshot remains open.

`TestCanonicalStreamNarrowReadAndFinalLookup` logs real SQLite EQP for the narrow
stream, the output lookup and the baseline finite SQL sampler. It asserts that
the stream seeks the metric/context/step range in canonical primary-key order,
without a source-sized temporary sort; the output lookup must seek all eight
primary-key columns. Its output-sized ORDER BY remains. This is a SQL-plan
comparison, not phase timing or a measurement of rows physically touched.

Observed with modernc.org/sqlite v1.40.1 / SQLite 3.50.4, on a 97-step/two-context fixture with
75 selected source rows and a 16-point output budget:

```text
narrow stream:
  SEARCH scalar_canonical USING INDEX sqlite_autoindex_scalar_canonical_1
    (run_incarnation=? AND name=? AND context=? AND has_step=? AND step_key>? AND step_key<?)
selected metadata:
  SCAN 16 CONSTANT ROWS
  SEARCH p USING INDEX sqlite_autoindex_scalar_canonical_1
    (run_incarnation=? AND name=? AND context=? AND has_step=? AND step_key=? AND session_key=? AND producer_key=? AND seq_key=?)
  USE TEMP B-TREE FOR ORDER BY
baseline finite sampler (excerpt):
  MATERIALIZE stats
  SEARCH scalar_canonical ... (same metric/context/step range)
  USE TEMP B-TREE FOR GROUP BY
  MATERIALIZE extrema
  SEARCH scalar_canonical ... (same metric/context/step range)
  BLOOM FILTER ON s (bucket=?)
  SEARCH s USING AUTOMATIC COVERING INDEX (bucket=?)
  USE TEMP B-TREE FOR GROUP BY
```

The preliminary count/endpoints aggregate exists in both implementations and is
outside these excerpts. The plan therefore supports removal of the two SQL
grouping stages and the stats join, not a claim of one total source pass or
zero SQL work. SQLite and PostgreSQL focused race suites passed, including the
unchanged tail and historical-frame regressions. Local raw test logs are kept
under the workspace's `outputs/canonical-stream/` and are not source artifacts.

## PostgreSQL risk and remote adoption gate

The preceding 6b0d56e remote reports contain request latency and aggregate
diagnostics, not SQL phase profiles. They do not prove which subquery consumed
the time. This candidate removes repeated SQL aggregation/join work, but moves
narrow row decoding and bucket selection into Go. PostgreSQL must transfer and
decode up to 250,000 three-column source rows per admitted run, rather than
returning only selected metadata rows. The preliminary aggregate still runs in
the database, and nonfinite data requires an additional narrow gap-boundary pass.
This can cost more network, application CPU and allocation even if it avoids a
stats-sensitive SQL join. PostgreSQL still chooses the access plan: it can sort
the narrow stream or use a hash join to match selected keys to metadata, rather
than physically probing the PK once per selected key. Do not infer improvement
from local EQP or correctness test duration. No LATERAL/OFFSET barrier or planner
setting is introduced.

Small-fixture stale-statistics plans reproduced poor nested loops, but the
original 335e PostgreSQL timeout plan was not captured. Later isolated 50k plans,
after system autoanalysis, used healthy hash joins. The candidate therefore
removes a demonstrated planner-sensitive component; it is not a proven diagnosis
or performance fix for that earlier incident. The tail candidate removes the
same sampling joins only after repair is proved, but repair and metadata lookup
still execute their existing SQL. Prefix construction/evaluation, source scans,
transfer and decoding remain costs. No live-workload improvement follows from
passing correctness tests alone.

Before adoption, the remote audit must compare the same 50k-step double-metric
fixture and resource limits against the accepted complete-stream `49a941c`
baseline (or the actual approved bundle), recording completed/timeout/error
counts, successful latency, CPU/memory, ACK latency under live writes and exact
frame/oracle checks. Keep projection/cache mode and raw source accounting
explicit. Verify the actual image/source commit and distinguish complete
canonical, tail and raw fallback requests. Include statistics timestamps and
plans where available, without altering the benchmark's statistics. PostgreSQL
performance has not been measured locally; remote evidence is the adoption gate.
