# Persistent sample location migration

ALabOS sample documents store current occupancy separately from durable location evidence:

- `position` is the currently booked sample position and may be cleared during cleanup.
- `last_position` is the last physical slot where the sample was recorded.
- `location_state` distinguishes present, in-transit, unconfirmed, removed, and unknown samples.
- `location_history` is the append-only movement audit trail.

## Sauron deployment

Perform this migration in a controlled maintenance window with the ALabOS managers and workers
stopped. Deploy matching versions of `alabos` and `alab_one`, activate the production environment,
and confirm that `ALABOS_CONFIG_PATH` points to the intended production configuration.

Preview the migration:

```bash
alabos backfill_sample_locations --dry-run
```

Apply it only after checking the reported sample count:

```bash
alabos backfill_sample_locations
```

The command is idempotent. It only fills missing fields, preserves existing `last_position` values,
and initializes history as empty because past movements cannot be reconstructed reliably.
