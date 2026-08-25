# TODO

1. Finish `Device Control`.
   Use the device-command examples in the `alab_one` README as the starting reference for what should be exposed in the new Device Control tab.
   On the Sauron computer, inspect the cached browser commands that Jessica and Tudor have been using to send requests directly to device IP addresses.
   Those cached IP-address command patterns are the minimum set that should be exposed in the Device Control UI.

2. Fix `Sample Positions`.
   Check with Tudor exactly how he currently adds and removes samples in MongoDB, including how slots are numbered and how positions are represented.
   Ensure the Sample Positions tab matches Tudor's real MongoDB workflow closely enough that operators no longer need to open MongoDB directly.
   Re-check whether the production source of truth is `devices.attributes.available_slots`, `sample_positions`, live `samples`, or some combination of them.

3. Refine `Data` exports.
   Decide what operators and experimenters actually need in the CSV outputs at the end of an experiment.
   Keep the exports to the minimum genuinely useful fields rather than exposing extra MongoDB data by default.
   Re-check which summary fields are essential for powder dosing, heating, and end-of-run sample tracking.

4. Continue dashboard visual cleanup.
   Keep the overall layout and arrangement unchanged, but continue refining the color system.
   Secondary colors in the Devices tab, especially the bright blue, bright orange, and pause-state red, should be muted so they match the sleeker minimal shell.

5. Check repository visibility settings.
   Confirm whether `alab_one`, `alabos`, `alab_gpss`, and `alab_control` should each be public or private.
   Then set the GitHub repository visibility accordingly and document the intended state somewhere central.

6. Reintroduce `Ruff` checks later.
   The current `alabos` repo does not pass repo-wide Ruff linting because of broad pre-existing issues in scaffold and example files.
   Re-implement Ruff checks once the relevant files have been cleaned up and the intended lint scope has been agreed.

7. Validate `Device Control` against real hardware.
   Check every new Device Control button on the real DASH devices before trusting the UI in production.
   Confirm that the mixed safety model, where reads are direct but actuation requires an ALabOS claim, matches the actual operator workflow in the lab.
   Re-check timeout values and operator-facing error text against real failure behavior on hardware.
   After hardware behavior is confirmed, add automated backend and frontend tests that lock in the validated command flows and error handling.

8. Clean up the `Device Control` UI.
   Improve readability once the backend behavior is settled and the real command set is confirmed.
   Revisit spacing, grouping, and result presentation so manual control is easier to scan during operation.
