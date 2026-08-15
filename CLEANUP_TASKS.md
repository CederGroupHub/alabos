# Cleanup Tasks

This file is a scratchpad for repo cleanup and onboarding fixes that should be tackled over time.

## High Priority

- Improve local simulation onboarding and startup reliability.
- Clarify the boundary between `alabos`, lab-specific repos, and low-level driver repos.
- Reduce operator dependence on direct MongoDB edits for state correction.

## TODO

- Add a clear local simulation quickstart that explains MongoDB, RabbitMQ, config variables, and launch order.
- Document which startup steps are required for simulation versus production.
- Make the integration contract with lab-specific repos explicit and versioned where possible.
- Expose more operational recovery actions in the UI instead of requiring raw DB edits.
- Add a note in the startup docs that some optional ALab One features currently depend on external helper code; the long-term fix is to move `trying_camera_functionality` into version control rather than leaving it in `Clutter`.

## Notes

- This repo is the workflow/runtime layer. It should be possible to start the simulation stack without undocumented external Python modules.
