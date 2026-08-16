# TODO

- Verify whether the Sample Positions UI should derive slot availability and occupancy from `devices` documents, especially device `attributes.available_slots`, instead of relying on the current `sample_positions` plus live `samples` collections.
- Confirm the exact MongoDB source of truth for DASH rack occupancy on the production system:
  `devices` collection, `sample_positions` collection, or both.
- If `devices.attributes.available_slots` is authoritative, update the Sample Positions backend to read from that structure and document the mapping between device attributes and rack slot labels shown in the UI.
