# Lab data persistence — before vs after (Sept 2026)

Presentation outline for the AlabOS / A-Lab data work of the week of **~13–20 September 2026**.

**Audience:** lab operators, scientists who submit experiments, and anyone who used to “wipe Mongo and start over” after every AlabOS restart.

**Repos this describes:**

| Layer | Repo / surface |
|---|---|
| AlabOS core + dashboard (8895) | `alab_management` |
| A-Lab OS launcher / bootstrap (8894) | `alab_one` → `restart_launcher` |
| Live Mongo DB | typically `Alab` |
| Archive / completed Mongo DB | typically `Alab(completed)` |

---

## 1. One-sentence thesis

**Before:** Restarting AlabOS routinely treated the live database as disposable — full dumps every time, often followed by wiping live state — so sample locations and mid-campaign identity did not survive day-to-day recovery.

**After:** Launch is start-only by default. Persistent sample location data stays in Mongo. Day-to-day recovery moved to **Lab settings** on the dashboard, with explicit actions that separate *ephemeral software state* from *physical occupancy* and from *nuclear wipe*.

---

## 2. Mental model: three kinds of “state”

Everything in this redesign hangs on distinguishing:

| Kind of state | Examples | Should survive normal restart? |
|---|---|---|
| **Ephemeral runtime** | Live task IDs, device locks, Dramatiq actors, `_lock` / `requests` collections, position *reservations* (`sample_positions.task_id`), in-transit flags, open experiment status | No — safe to cancel / release |
| **Physical occupancy map** | `samples.position` (“this crucible is in DASH_input_rack/slot/2 right now”) | Yes, unless an operator intentionally clears it |
| **Persistent sample memory** | Sample `_id`, name, metadata/results, `last_position`, `position_history`, archived copies in `Alab(completed)` | Yes — never lose casually |

Old workflows collapsed all three into “drop the live DB.”

---

## 3. How it used to work (before ~13 Sept 2026)

### 3.1 Restart = heavy ritual

Typical operator loop when AlabOS misbehaved or someone needed a “clean” lab:

1. Stop / kill AlabOS processes (often multiple terminals / browser tabs).
2. Run a **full `mongodump` of essentially every Mongo database** on every restart (massive redundancy; disk filled with near-identical copies of `Alab(completed)`, Labman, etc.).
3. Often run **`alabos clean -a`** (or equivalent “clean all”) which **drops the live AlabOS database** (`Alab`).
4. Run setup again and relaunch.

The Tk restart GUI and launcher defaults made this easy to do as the default path. Wiping live Alab was treated as normal recovery, not last resort.

### 3.2 What wiping the live DB actually destroyed

Dropping live `Alab` removed (among other things):

- Running / queued **tasks** and open **experiments**
- Device lock / request state
- **Sample documents that only lived in the live DB** (anything not already copied into `Alab(completed)`)
- Current **`samples.position`** occupancy — after wipe, software no longer knew what was on which rack
- Any mid-flight results not yet archived

Operators often relied on **physical memory** (“I know what’s on the bench”) plus occasional Mongo spelunking, because the software map was gone.

### 3.3 What `Alab(completed)` was for

Finished work was (and still is) intended to land in the completed / archive database. That archive was **not** a substitute for a live occupancy map:

- You could not reliably “restore last week’s rack layout” from completed alone.
- Even when `last_position` existed on older sample docs (field added earlier, June 2026), **routine wipes + nulling of live `position`** meant operators still lost the *live* map after restart.
- Notion P0 language at the time: *“Sample locations in the live Alab database are wiped on a restart — ability to find physical samples is lost; position shows null.”*

### 3.4 Fields that existed but did not solve the workflow

| Field | When it appeared | What it meant | Why it wasn’t enough alone |
|---|---|---|---|
| `position` | Long-standing | Current slot, or `null` if unplaced | Cleared / lost when live DB wiped or when recovery null’d occupancy without a UI story |
| `last_position` | **2026-06-29** (`e20e40e`) | Most recently recorded physical location; not cleared when `position` becomes `null` | Survived some cleanups in theory, but operators still wiped live DB; no lab-wide UI; reset/cleanup paths still confused with “empty the lab” |
| `in_transit` | Earlier mobile work | Source → destination while a move is in progress | Useful for crashes mid-move; not a full history or lab map |

**`position_history` did not exist yet** as the operator-facing timeline (added with the Sept persistence work).

### 3.5 Pain points (why we changed it)

1. **Lost occupancy after every “clean” restart** — cannot answer “where is sample X?” from the UI.
2. **Ghost samples / stuck reserves** — leftover `position` or locks blocking the next experiment with opaque waits.
3. **Cancel vs wipe confusion** — Cancel experiment, reset, clean, and drop-DB all felt similar; operators could not predict side effects.
4. **Backup disk bloat** — dumping *all* DBs on every Go, including huge completed archives, with high redundancy.
5. **No lab-wide occupancy view** — only ad-hoc Mongo queries or station-specific UIs (e.g. consumable rack on another port).
6. **Launcher owned too much recovery** — dangerous options lived on the start screen next to “Go.”

---

## 4. What we built (week of ~13–20 Sept 2026)

Work landed mainly **17 Sept**, with follow-ons through **18–20 Sept**. Theme: **stop treating live sample data as disposable.**

### 4.1 Launcher becomes bootstrap-only

**Repo:** `alab_one` / `restart_launcher`

| Before | After |
|---|---|
| Tk GUI with many recovery knobs on start | Browser `--app` shell on `127.0.0.1:8894`; Start Menu “A-Lab OS” |
| Easy to wipe live DB on Go | **`alabos clean -a` / nuclear wipe off by default**; nuclear requires typing the live DB name |
| Full multi-DB dump every restart | **Split backup policy** (see §4.5); Backup on launch is optional |
| Recovery = restart ritual | **Day-to-day recovery → Lab settings on 8895** |

Go is intentionally **launch-only** (optionally backup first). Advanced clean/setup moved out of the default splash path.

Key commits (alab_one):

- `85c04da30` (2026-09-17) — browser launcher + single-instance
- `49372c485` (2026-09-17) — clean -a off by default; type DB name to wipe
- `320c33c33` (2026-09-17) — silent bootstrap; Lab settings as control surface
- `5c12934e4` (2026-09-17) — split Mongo backup (dated live + rolling other DBs)

### 4.2 Sample location persistence

**Repo:** `alab_management` / `sample_view`

| Field | Behavior now |
|---|---|
| `position` | Current occupancy. Cleared only when something intentionally unplaces the sample (Ending, Clear occupancy, per-slot Clear, etc.). **Not** wiped by “Release locks & tasks.” |
| `last_position` | Updated when moving *to* a real slot; **retained** when `position` becomes `null`. Last known location. |
| `position_history` | Append-only log (capped, e.g. 200 entries): events such as `placed` / `moved` / `in_transit` / `cleared`, with timestamps. |
| `in_transit` | Still records mid-move source/destination; cleared when move completes or ownership is released. |

**Release locks & tasks** clears ephemeral ownership (`task_id`, `in_transit`, position *reservations*) but **keeps** `position` / `last_position` / history.

Key commit:

- `c8a6e2c` (2026-09-17) — persist occupancy across reset + Sample Positions view
- Earlier related: `d6cbb87` (2026-09-04) — persist location history across cleanup (foundation)

### 4.3 Sample Positions UI (dashboard)

Lab-wide occupancy on **8895**:

- Device-oriented list of powder-holding slots (racks, XRD holders, arms, Alfred structure, …; cap-only noise hidden)
- **Find sample** (name / id / position)
- **Now / Before** plus **History** timeline (jump to slots)
- Per-slot **Clear** (idle-gated) — Place removed from UI so Starting tasks own placement (avoids dual-write hangs)
- Campaign / owner captions when tags/metadata provide them

### 4.4 Lab settings page (the control surface)

**Files:** `client/.../LabSettings.js`, `alab_management/lab_reset.py`, `dashboard/routes/lab_settings.py`, plus launcher control APIs on 8894.

Intro copy on the page:

> Day-to-day recovery lives here: unstick software, clear empty-lab occupancy, back up MongoDB, and refresh device definitions.

**Idle gate:** Backup, Clear occupancy, Refresh definitions, and Nuclear require the lab to be idle (no live tasks, no open experiments, no reserved sample positions). Release locks & tasks is how you *get* idle.

Below: each card / button, in presentation order.

---

#### A. Release locks & tasks

| | |
|---|---|
| **API** | `POST /api/lab-settings/reset_lab` → `reset_lab_software_state()` |
| **When** | After a crash; experiments / devices / locks look stuck |
| **Does** | Cancels live tasks; dismisses experiment user-input prompts; drops `_lock` + `requests`; releases devices; clears mobile-robot queue attrs; unlocks sample-position reservations; clears sample `task_id` / `in_transit`; closes open experiments as CANCELLED; archives those experiments to completed when configured; may prune archived unplaced docs from live |
| **Keeps** | `samples.position`, `last_position`, `position_history`, sample identity |
| **Does not** | Emergency-stop hardware already moving; empty the occupancy map |
| **Limitation (called out in UI)** | **Not enough by itself to run new work** if leftover `position` values still occupy slots (“ghost samples”). Follow with Clear occupancy when the bench should be empty in software. |

#### B. Clear occupancy

| | |
|---|---|
| **API** | `POST /api/lab-settings/clear_occupancy` → `clear_lab_occupancy()` |
| **When** | Physical lab is empty *or* you need software to treat every slot as empty |
| **Requires** | Lab idle (run Release first if needed) |
| **Does** | Sets every sample `position` to empty via `move_sample(..., None)` (appends `cleared` history); clears remaining in-transit; unlocks reservations; archives terminal live experiments missing from completed; **prunes** live sample/task/experiment docs that already have a completed copy and are unplaced |
| **Keeps** | Identity; `last_position` / history on docs that remain; **never deletes a live doc without an `Alab(completed)` copy** |
| **Pair with Release** | **Non-nuclear reset:** Release + Clear occupancy |

#### C. Backup MongoDB now + “Backup on launch”

| | |
|---|---|
| **Where** | Lab settings button (8894 control plane) and/or launcher Go if Backup on launch is enabled |
| **Requires** | Idle for on-demand backup (launch-time backup can run before services come up) |
| **Live `Alab`** | New **dated snapshot** under `backup/live/` every run — **never overwrites** prior live dumps |
| **Other DBs** (`Alab(completed)`, Labman, …) | Rolling overwrite under `backup/current/`; whole `current/` archived on an interval (default ~60 days) under `archive/` |
| **Toggle** | **Backup on launch** — saved into launcher config; optional |

#### D. Refresh devices & slots

| | |
|---|---|
| **When** | After changing device or slot definitions in code |
| **Does** | Stops services → rebuilds devices & slots (`alabos clean` + setup path, **not** nuclear drop of sample data) → starts again |
| **Requires** | Idle |
| **Does not** | Delete sample documents |

#### E. Profiles

| Button | Effect |
|---|---|
| **Production (Alab)** | Applies env defaults for live production DB name / related flags |
| **Sim lab (Alab_sim)** | Same for simulation DB |
| **Does not** | Wipe or dump data by itself — only settings for next launch / action |

#### F. Advanced — Nuclear wipe live Alab

| | |
|---|---|
| **When** | Sim lab or brand-new install — **not** routine recovery |
| **Does** | Stop → `alabos clean -a` (drop live DB) → setup → restart |
| **Loses** | Everything only in live Alab, including mid-experiment samples not yet in completed |
| **Does not drop** | `Alab(completed)` |
| **Confirm** | Must type the live database name exactly |
| **Backup toggle** | “Backup MongoDB before wipe” (default **on**) |

#### G. Advanced — Launch & paths

Edits bootstrap defaults: launch worker, log directory, backup directory, archive interval days, mongodump gzip, AlabOS port, database name, etc. These do not wipe data by themselves.

---

### 4.5 Split Mongo backup policy (why backups changed)

**Problem:** Dumping every database on every restart duplicated huge completed archives.

**Policy now:**

```
backup/
  live/          # dated snapshots of live Alab only — keep history
  current/       # rolling dump of other DBs (completed, Labman, …)
  archive/       # periodic copies of current/
  legacy/        # old full-clone style dumps (migration / historical)
```

Live Alab is the DB that changes constantly during a shift and is most painful to lose mid-campaign — hence dated, non-overwriting snapshots. Completed data changes less often — rolling + periodic archive is enough.

### 4.6 Cancel experiment vs Lab settings

| Action | Scope | Hardware | Sample `position` |
|---|---|---|---|
| **Cancel experiment** (Experiments page) | That experiment’s tasks / resources | Does **not** abort Labman / robots already moving | Samples stay where they are |
| **Release locks & tasks** | Whole lab software state | Does not e-stop motion | Occupancy **kept** |
| **Clear occupancy** | Whole lab map | None | Occupancy **cleared** in software |
| **Nuclear wipe** | Drop live DB | Services restarted empty | Occupancy **gone** from live |

Cancel dialog copy was also clarified so operators see Cancels / Releases / Keeps / Does not before confirming.

### 4.7 Position-conflict User Input (related)

If a task needs a slot that is still OCCUPIED after Release (ghost occupancy), ResourceManager no longer silent-retries forever. Operators get a User Input to **Clear conflicting position(s)** or keep waiting. This makes the Release-without-Clear failure mode loud instead of mysterious.

---

## 5. Intended operator workflows now

### 5.1 Normal morning / restart AlabOS

1. Open **A-Lab OS** launcher (8894).
2. Optionally leave **Backup on launch** on (Lab settings or launcher config).
3. Press **Go** — starts services only; **does not wipe** live Alab.
4. Work in the dashboard (8895). Use **Sample Positions** to see what software thinks is on the bench.

### 5.2 Soft recovery after a crash (preferred)

1. Ensure robots/Labman are in a safe physical state (human judgment — software will not e-stop for you).
2. **Lab settings → Release locks & tasks.**
3. If you need a fresh empty map for new experiments: physically empty / re-rack the bench, then **Clear occupancy** (lab must be idle).
4. Submit new work. Use **Starting** tasks (user confirm) to re-establish sample presence — do not rely on a GUI “Place” button (removed from Sample Positions for now).

### 5.3 When occupancy is wrong for one slot

Use **Sample Positions → Clear** on that slot (idle-gated), then place via the normal experiment Starting path.

### 5.4 After editing device/slot code

**Lab settings → Refresh devices & slots** (idle). Sample docs stay.

### 5.5 Last resort

**Nuclear wipe** (type DB name; backup-before-wipe on). Prefer sim / new install. Not the daily path.

### 5.6 Recovery path cheat sheet

| Path | Intent | Tasks / experiments | `samples.position` | History / `last_position` |
|---|---|---|---|---|
| **A. Release only** | Unstick software; keep map | Cancelled / closed | **Kept** | Kept |
| **B. Release + Clear occupancy** | Empty software map; keep identities | Cancelled; prune archived leftovers | **Cleared** | Kept on remaining / completed docs |
| **C. Nuclear wipe** | Drop live DB | Deleted from live | **Gone** from live | Gone from live |

**B** is the non-nuclear default after a crash when you want to run again on an empty bench. **A alone** can leave ghosts that block reservations.

---

## 6. Before / after comparison (slide-friendly)

| Topic | Before ~13 Sept | Now |
|---|---|---|
| Default Go | Often coupled to heavy clean / wipe habits | Launch-only; wipe gated |
| Live sample positions after restart | Frequently null / gone | Persist unless Clear / Nuclear |
| Last known location | Field existed (June) but workflow still wiped live DB | Kept across Release; shown in Sample Positions / Data |
| Movement history | Not operator-visible timeline | `position_history` + History UI |
| Lab occupancy UI | Mongo / partial station UIs | Sample Positions on 8895 |
| Day-to-day recovery | Launcher / drop DB | Lab settings cards |
| Backup every restart | Full multi-DB dumps, high redundancy | Dated live snapshots + rolling other DBs |
| Cancel clarity | Unclear side effects | Explicit dialog facts |
| Ghost occupancy | Silent stuck waits | Clear occupancy + conflict User Input |

---

## 7. Databases at a glance

| Database | Role |
|---|---|
| **`Alab` (live)** | Current experiments, tasks, devices, **live sample docs + occupancy** |
| **`Alab(completed)`** | Archive of finished / cancelled experiments and associated sample/task copies |
| **Labman / others** | External or supporting systems; included in rolling “other DB” backups |

**Hard prune rule (Clear occupancy / Release prune path):** never delete a live document unless the same `_id` exists in completed.

---

## 8. What is intentionally not done yet (honest slide)

Useful for Q&A so expectations stay accurate:

- **“Continue after crash with samples left in place”** as a first-class product path — high desire; today Release alone is not enough to always resume cleanly; Clear is still often required for new runs.
- **Sample identity reuse** on resubmit (same name → new `_id` today).
- **Full archive-then-purge** workflow as a dedicated Archive button (partial prune exists inside Clear; broader design deferred).
- **Place** restored on Sample Positions (Clear-only for now; Starting owns placement).
- **Alfred seat filing** during mobile trips (structure visible; seat-level identity while on the robot has been incomplete depending on stack).
- Larger **DB overhaul** (sample-centric results hub, format migration) — separate from this occupancy P0.

---

## 9. Key commits (for speakers / appendix)

### alab_management

| Date | Commit | Summary |
|---|---|---|
| 2026-06-29 | `e20e40e` | Introduced `last_position` on Sample (earlier than “last week”) |
| 2026-09-04 | `d6cbb87` | Persist sample location history across cleanup |
| 2026-09-17 | `c8a6e2c` | Persist occupancy across reset; Sample Positions view |
| 2026-09-17 | `be139a0` | Lab settings: reset, clear occupancy, launcher control actions |
| 2026-09-17 | `fc6e626` | Rename/clarify “Release locks & tasks”; clearer backup copy |
| 2026-09-17 | `8946636` | Idle-gate Sample Positions Clear |
| 2026-09-17 | `c7ce382` | Clear conflicting positions User Input when blocked |
| 2026-09-18 | `e510a8a` | Safer archive of cancelled experiments + UI refresh |

### alab_one (launcher / backup)

| Date | Commit | Summary |
|---|---|---|
| 2026-09-17 | `85c04da30` | Browser `--app` launcher, single-instance |
| 2026-09-17 | `49372c485` | clean -a off by default; type DB name to wipe |
| 2026-09-17 | `320c33c33` | Bootstrap launcher; Lab settings as control surface |
| 2026-09-17 | `5c12934e4` | Split Mongo backup policy |

---

## 10. Suggested talk flow (15–20 min)

1. **Problem story** (2 min): “We wiped Alab every restart and lost where samples were.”
2. **Three kinds of state** (§2) (2 min).
3. **Before** walkthrough (§3) (3 min).
4. **Demo Lab settings cards** (§4.4) live or screenshots (5–7 min).
5. **Sample Positions + history** (2 min).
6. **Backup policy** one diagram (§4.5) (2 min).
7. **Workflows A/B/C** cheat sheet (§5.6) (2 min).
8. **Not yet** honesty (§8) + Q&A.

---

## 11. Source pointers

| Topic | Path |
|---|---|
| Release / Clear / idle / prune | `alab_management/lab_reset.py` |
| Lab settings API | `alab_management/dashboard/routes/lab_settings.py` |
| Lab settings UI copy | `client/src/dashboard/components/LabSettings.js` |
| Sample fields | `alab_management/sample_view/sample.py` |
| `move_sample` / history | `alab_management/sample_view/sample_view.py` |
| Sample Positions UI | `client/src/dashboard/components/SamplePositions.js` |
| Launcher nuclear / backup | `alab_one/.../restart_launcher/runner.py`, `mongo_backup.py`, `config.py` |
| Session notes (scratch) | `alab_one/agent_temp/done.md`, `software_todo_p0_p1.md` |

---

*Document prepared for internal presentation use. Reflects intended behavior of the Lab settings + persistence work landed mid-September 2026; verify against the deployed dashboard if copy has drifted slightly.*
