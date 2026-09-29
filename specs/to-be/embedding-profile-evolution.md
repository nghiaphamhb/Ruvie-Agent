# Embedding profile evolution after MVP

## Current MVP decision

The runtime accepts `EMBEDDING_MODEL_ID`, `EMBEDDING_DIMENSION`, and
`EMBEDDING_DISTANCE_METRIC`. It does not require a model version because the
current provider contract sends only a model ID and many compatible APIs do
not expose a separate version parameter.

The active PostgreSQL schema still uses `vector(1024)` and a cosine HNSW
index. Startup therefore continues to require dimension `1024` and metric
`cosine`. Those checks protect the database from vectors that its column or
index cannot handle.

## Problems to solve before profiles become configurable

1. **Schema and runtime agreement.** Move dimension and metric support into an
   explicit database profile or index design. Alembic migrations must remain
   deterministic and must not derive schema from the machine's `.env` file.
2. **Safe profile isolation.** Retrieval must select only chunks created by a
   compatible model, dimension, and metric. Changing `EMBEDDING_MODEL_ID`
   cannot silently mix old and new vector spaces.
3. **Re-embedding lifecycle.** Define how a profile change creates a new index,
   schedules existing revisions for re-embedding, switches reads, and retires
   the previous vectors without losing citations.
4. **Metric-specific queries.** Support only named metrics with matching
   pgvector operators and index opclasses, such as cosine, L2, or inner
   product. Validate that the search expression and index use the same metric.
5. **Provider provenance.** If a provider later exposes an immutable revision,
   deployment ID, or digest, store it as optional provenance. Do not require a
   fabricated commit SHA from providers that do not supply one.
6. **Startup validation.** Compare runtime profile settings with the applied
   database schema/index and fail before accepting uploads when they differ.
7. **Migration configuration.** Let Alembic require only `DATABASE_URL`; it
   should not need live embedding or LLM provider credentials to migrate the
   database.

## Proposed implementation order

1. Add a persistent embedding profile identifier and attach chunks/revisions
   to it.
2. Make retrieval filter by that identifier in the authorized database query.
3. Add a migration and re-embedding command for each newly supported profile.
4. Add runtime/schema compatibility checks.
5. Only then allow dimension or distance metric values beyond the MVP pair.

## Completion criteria

- Two incompatible profiles can coexist without cross-profile retrieval.
- A profile migration can be resumed after interruption without duplicate
  chunks or loss of old citations.
- Unsupported dimensions and metrics fail at startup with a clear message.
- Migration SQL can be generated with `DATABASE_URL` alone.
- Provider requests use only fields supported by that provider's contract.
