import React, { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  FormControlLabel,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import SettingsIcon from "@mui/icons-material/Settings";
import {
  apply_control_profile,
  clear_lab_occupancy,
  control_backup,
  control_nuclear,
  control_refresh_definitions,
  get_control_config,
  get_lab_idle,
  put_control_config,
  reset_lab,
} from "../../api_routes";

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForDashboardAndReload() {
  for (let i = 0; i < 90; i++) {
    try {
      const res = await fetch("/api/status", { mode: "cors" });
      if (res.ok) {
        window.location.reload();
        return;
      }
    } catch {
      // dashboard still restarting
    }
    await sleep(1000);
  }
  window.location.reload();
}

function IdleBanner({ idle, reasons, controlAvailable }) {
  if (controlAvailable === false) {
    return (
      <Alert severity="info" sx={{ mb: 2 }}>
        Bootstrap control plane (8894) is not reachable. Backup, refresh
        definitions, nuclear wipe, and Advanced config need the A-Lab OS app
        shell. Release locks &amp; tasks and Clear occupancy still work here.
      </Alert>
    );
  }
  if (idle) {
    return (
      <Alert severity="success" sx={{ mb: 2 }}>
        Lab is idle — backup, refresh, clear occupancy, and nuclear are allowed.
      </Alert>
    );
  }
  return (
    <Alert severity="warning" sx={{ mb: 2 }}>
      Lab is not idle
      {reasons?.length ? `: ${reasons.join("; ")}` : "."} Finish or Release
      locks &amp; tasks before backup / clear occupancy / refresh / nuclear.
    </Alert>
  );
}

function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  confirmColor = "error",
  requireTyped,
  onConfirm,
  onClose,
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [typed, setTyped] = useState("");

  const handleClose = () => {
    if (busy) return;
    setError(null);
    setTyped("");
    onClose();
  };

  const handleConfirm = async () => {
    if (requireTyped && typed.trim() !== requireTyped) {
      setError(`Type ${requireTyped} exactly to continue.`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onConfirm();
      setTyped("");
      onClose();
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} disableEscapeKeyDown={busy}>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText component="div">{body}</DialogContentText>
        {requireTyped && (
          <TextField
            autoFocus
            fullWidth
            margin="dense"
            label={`Type ${requireTyped} to confirm`}
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            disabled={busy}
          />
        )}
        {error && (
          <DialogContentText sx={{ mt: 2 }} color="error">
            {error}
          </DialogContentText>
        )}
      </DialogContent>
      <DialogActions>
        <Button
          onClick={handleConfirm}
          color={confirmColor}
          disabled={busy}
        >
          {busy ? "Working…" : confirmLabel}
        </Button>
        <Button onClick={handleClose} disabled={busy} autoFocus>
          Cancel
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function ActionCard({ title, facts, children, actions }) {
  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        <Typography
          variant="h6"
          sx={{ fontWeight: 700, color: "#203d51", mb: 1.25 }}
        >
          {title}
        </Typography>
        {facts?.length ? (
          <Box
            component="ul"
            sx={{
              m: 0,
              mb: 1.5,
              pl: 0,
              listStyle: "none",
            }}
          >
            {facts.map((fact) => (
              <Typography
                key={fact.label}
                component="li"
                variant="body1"
                sx={{
                  color: "#203d51",
                  lineHeight: 1.55,
                  mb: 1,
                  "&:last-child": { mb: 0 },
                }}
              >
                <Box
                  component="span"
                  sx={{
                    fontWeight: 700,
                    color: fact.tone === "warn" ? "#8a4b08" : "#203d51",
                  }}
                >
                  {fact.label}:{" "}
                </Box>
                {fact.text}
              </Typography>
            ))}
          </Box>
        ) : null}
        {children}
      </CardContent>
      {actions && <CardActions sx={{ px: 2, pb: 2 }}>{actions}</CardActions>}
    </Card>
  );
}

export default function LabSettings() {
  const [idle, setIdle] = useState(true);
  const [reasons, setReasons] = useState([]);
  const [controlAvailable, setControlAvailable] = useState(null);
  const [config, setConfig] = useState(null);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const [resetOpen, setResetOpen] = useState(false);
  const [clearOpen, setClearOpen] = useState(false);
  const [refreshOpen, setRefreshOpen] = useState(false);
  const [nuclearOpen, setNuclearOpen] = useState(false);
  const [nuclearBackupBeforeWipe, setNuclearBackupBeforeWipe] = useState(true);

  const refreshIdle = useCallback(async () => {
    try {
      const res = await get_lab_idle();
      if (res?.status === "success" && res.data) {
        setIdle(Boolean(res.data.idle));
        setReasons(res.data.reasons || []);
      }
    } catch (err) {
      setReasons([String(err.message || err)]);
      setIdle(false);
    }
  }, []);

  const refreshControl = useCallback(async () => {
    try {
      const { ok, data } = await get_control_config();
      if (!ok) {
        setControlAvailable(false);
        setConfig(null);
        return;
      }
      setControlAvailable(true);
      setConfig(data.config || data);
    } catch {
      setControlAvailable(false);
      setConfig(null);
    }
  }, []);

  useEffect(() => {
    refreshIdle();
    refreshControl();
    const interval = setInterval(() => {
      refreshIdle();
    }, 5000);
    return () => clearInterval(interval);
  }, [refreshIdle, refreshControl]);

  const setOk = (text) => {
    setMessage(text);
    setError(null);
  };
  const setFail = (text) => {
    setError(text);
    setMessage(null);
  };

  const saveConfigField = async (patch) => {
    if (!config) return;
    const next = { ...config, ...patch };
    const { ok, data } = await put_control_config(next);
    if (!ok) {
      setFail(data.error || data.reason || "Failed to save config");
      return;
    }
    setConfig(data.config || next);
    setOk("Saved advanced settings.");
  };

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
        <SettingsIcon sx={{ color: "#203d51" }} />
        <Typography variant="h5" sx={{ fontWeight: 700, color: "#203d51" }}>
          Lab settings
        </Typography>
      </Box>
      <Typography
        variant="body1"
        sx={{ color: "#203d51", mb: 2.5, lineHeight: 1.55, maxWidth: 720 }}
      >
        Day-to-day recovery lives here: unstick software, clear empty-lab
        occupancy, back up MongoDB, and refresh device definitions. Read each
        card before you click — several actions are destructive or irreversible
        for live work.
      </Typography>

      <IdleBanner
        idle={idle}
        reasons={reasons}
        controlAvailable={controlAvailable}
      />
      {message && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Alert severity="warning" sx={{ mb: 2.5, maxWidth: 820 }}>
        <Typography variant="body1" sx={{ fontWeight: 700, mb: 0.75 }}>
          Recovery note (important)
        </Typography>
        <Typography variant="body1" sx={{ lineHeight: 1.55, mb: 1 }}>
          <strong>Release locks &amp; tasks alone is not enough right now</strong> if
          you want to run new experiments. Clearing task IDs frees device locks,
          but samples can still occupy slots in software (
          <code>samples.position</code>). That blocks the next task from reserving
          those devices — the old “ghost sample” / stuck-reserve problem.
        </Typography>
        <Typography variant="body1" sx={{ lineHeight: 1.55, mb: 1 }}>
          To clear and reset the lab for a fresh run <strong>without</strong> wiping
          sample identities, last-known locations, movement history, or cancelled
          task/experiment records: press{" "}
          <strong>Release locks &amp; tasks</strong>, then{" "}
          <strong>Clear occupancy</strong> (lab must be idle for Clear). Physically
          empty or re-rack the bench to match.
        </Typography>
        <Typography variant="body1" sx={{ lineHeight: 1.55 }}>
          If that still leaves the lab unusable, use{" "}
          <strong>Nuclear wipe</strong> (Advanced; backup-on by default). Nuclear
          drops the live Alab database — last resort only.
        </Typography>
      </Alert>

      <ActionCard
        title="Release locks & tasks"
        facts={[
          {
            label: "When",
            text: "After a crash, or when experiments / devices / locks look stuck.",
          },
          {
            label: "Does",
            text: "Cancels live and queued work; releases devices, locks, and reservations.",
          },
          {
            label: "Keeps",
            text: "Sample positions and movement history.",
          },
          {
            label: "Limitation",
            text: "Not enough by itself to run again — leftover sample positions still block devices. Follow with Clear occupancy (see note above).",
            tone: "warn",
          },
          {
            label: "Does not",
            text: "Emergency-stop hardware that is already moving.",
            tone: "warn",
          },
        ]}
        actions={
          <Button
            variant="contained"
            color="warning"
            onClick={() => setResetOpen(true)}
          >
            Release locks & tasks
          </Button>
        }
      />

      <ActionCard
        title="Clear occupancy"
        facts={[
          {
            label: "When",
            text: "The physical lab is empty, or you need software to treat every slot as empty.",
          },
          {
            label: "Does",
            text: "Sets current position empty, unlocks slot reservations, appends history.",
          },
          {
            label: "Keeps",
            text: "Sample identity, last-known location, and full movement history.",
          },
          {
            label: "Requires",
            text: "Lab idle — run Release locks & tasks first if anything is still running.",
            tone: "warn",
          },
          {
            label: "With Release locks",
            text: "This pair is the non-nuclear reset: clear stuck work + empty the occupancy map while keeping sample records, last-known location, and histories. Use Nuclear wipe only if that fails.",
          },
        ]}
        actions={
          <Button
            variant="contained"
            color="error"
            disabled={!idle}
            onClick={() => setClearOpen(true)}
          >
            Clear occupancy
          </Button>
        }
      />

      <ActionCard
        title="Backup MongoDB"
        facts={[
          {
            label: "When",
            text: "Lab must be idle (or Backup on launch at cold start before services come up).",
          },
          {
            label: "Live Alab",
            text: "New dated snapshot under backup/live/ every run — never overwrites prior live dumps.",
          },
          {
            label: "Other DBs",
            text: "Rolling overwrite under backup/current/ (Alab(completed), Labman, …); whole current/ archives every N days.",
          },
        ]}
        actions={
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
            <Button
              variant="contained"
              disabled={!idle || controlAvailable === false}
              onClick={async () => {
                try {
                  const { ok, data } = await control_backup();
                  if (!ok) {
                    setFail(data.error || data.reason || "Backup failed");
                    await refreshIdle();
                    return;
                  }
                  setOk(data.message || "MongoDB backup finished.");
                } catch (err) {
                  setFail(String(err.message || err));
                }
              }}
            >
              Backup MongoDB now
            </Button>
            <FormControlLabel
              control={
                <Switch
                  checked={Boolean(config?.backup_mongodb)}
                  disabled={controlAvailable === false || !config}
                  onChange={(e) =>
                    saveConfigField({ backup_mongodb: e.target.checked })
                  }
                />
              }
              label="Backup on launch"
            />
          </Box>
        }
      />

      <ActionCard
        title="Restart lab with refreshed definitions"
        facts={[
          {
            label: "When",
            text: "After you change device or slot definitions in code.",
          },
          {
            label: "Does",
            text: "Stops services, rebuilds devices & slots (alabos clean + setup), then starts again.",
          },
          {
            label: "Requires",
            text: "Lab idle. Sample documents are not deleted.",
          },
        ]}
        actions={
          <Button
            variant="contained"
            disabled={!idle || controlAvailable === false}
            onClick={() => setRefreshOpen(true)}
          >
            Refresh devices & slots
          </Button>
        }
      />

      <ActionCard
        title="Profiles"
        facts={[
          {
            label: "Does",
            text: "Applies saved environment defaults (database name and related flags).",
          },
          {
            label: "Does not",
            text: "Wipe or dump data by itself — only changes settings for the next launch / action.",
          },
        ]}
        actions={
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
            <Button
              variant="outlined"
              disabled={controlAvailable === false}
              onClick={async () => {
                const { ok, data } = await apply_control_profile("production");
                if (!ok) {
                  setFail(data.error || "Failed to apply profile");
                  return;
                }
                setConfig(data.config);
                setOk("Applied Production profile.");
              }}
            >
              Production (Alab)
            </Button>
            <Button
              variant="outlined"
              disabled={controlAvailable === false}
              onClick={async () => {
                const { ok, data } = await apply_control_profile("sim");
                if (!ok) {
                  setFail(data.error || "Failed to apply profile");
                  return;
                }
                setConfig(data.config);
                setOk("Applied Sim lab profile.");
              }}
            >
              Sim lab (Alab_sim)
            </Button>
          </Box>
        }
      />

      <Divider sx={{ my: 3 }} />
      <Typography
        variant="h6"
        sx={{ fontWeight: 700, color: "#203d51" }}
        gutterBottom
      >
        Advanced
      </Typography>
      <Typography
        variant="body1"
        sx={{ color: "#203d51", mb: 2, lineHeight: 1.55, maxWidth: 720 }}
      >
        Rare or install-time settings. Nuclear wipe drops the entire live AlabOS
        database — it does not drop Alab(completed).
      </Typography>

      <ActionCard
        title="Nuclear wipe live Alab"
        facts={[
          {
            label: "When",
            text: "Sim lab or a brand-new install — not routine recovery.",
            tone: "warn",
          },
          {
            label: "Does",
            text: "Stops services, drops the live database, runs setup, restarts.",
          },
          {
            label: "Loses",
            text: "Mid-experiment samples that are not yet in Alab(completed).",
            tone: "warn",
          },
          {
            label: "Confirm",
            text: "You must type the live database name exactly.",
          },
          {
            label: "Backup",
            text: "Use the toggle next to the button (on by default) to run the same MongoDB backup as Backup now before wiping.",
          },
        ]}
        actions={
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
            <Button
              variant="outlined"
              color="error"
              disabled={!idle || controlAvailable === false}
              onClick={() => setNuclearOpen(true)}
            >
              Nuclear wipe…
            </Button>
            <FormControlLabel
              control={
                <Switch
                  checked={nuclearBackupBeforeWipe}
                  disabled={!idle || controlAvailable === false}
                  onChange={(e) => setNuclearBackupBeforeWipe(e.target.checked)}
                />
              }
              label="Backup MongoDB before wipe"
            />
          </Box>
        }
      />

      {config && controlAvailable !== false && (
        <ActionCard
          title="Launch & paths"
          facts={[
            {
              label: "Does",
              text: "Edits defaults used by the bootstrap shell on the next launch or refresh.",
            },
          ]}
        >
          <FormControlLabel
            control={
              <Switch
                checked={Boolean(config.launch_worker)}
                onChange={(e) =>
                  saveConfigField({ launch_worker: e.target.checked })
                }
              />
            }
            label="Launch worker"
          />
          <TextField
            fullWidth
            margin="dense"
            label="Log directory"
            value={config.log_directory || ""}
            onChange={(e) =>
              setConfig({ ...config, log_directory: e.target.value })
            }
            onBlur={() => saveConfigField({ log_directory: config.log_directory })}
          />
          <TextField
            fullWidth
            margin="dense"
            label="Backup directory"
            value={config.backup_directory || ""}
            onChange={(e) =>
              setConfig({ ...config, backup_directory: e.target.value })
            }
            onBlur={() =>
              saveConfigField({ backup_directory: config.backup_directory })
            }
          />
          <TextField
            fullWidth
            margin="dense"
            label="Rolling archive interval (days)"
            type="number"
            value={config.backup_archive_interval_days ?? 60}
            onChange={(e) =>
              setConfig({
                ...config,
                backup_archive_interval_days: Number(e.target.value),
              })
            }
            onBlur={() =>
              saveConfigField({
                backup_archive_interval_days:
                  config.backup_archive_interval_days,
              })
            }
          />
          <FormControlLabel
            control={
              <Switch
                checked={config.backup_use_gzip !== false}
                onChange={(e) =>
                  saveConfigField({ backup_use_gzip: e.target.checked })
                }
              />
            }
            label="Use mongodump --gzip"
          />
          <TextField
            fullWidth
            margin="dense"
            label="AlabOS port"
            type="number"
            value={config.alabos_port ?? 8895}
            onChange={(e) =>
              setConfig({ ...config, alabos_port: Number(e.target.value) })
            }
            onBlur={() => saveConfigField({ alabos_port: config.alabos_port })}
          />
          <TextField
            fullWidth
            margin="dense"
            label="Database name"
            value={config.database_name || ""}
            onChange={(e) =>
              setConfig({ ...config, database_name: e.target.value })
            }
            onBlur={() =>
              saveConfigField({ database_name: config.database_name })
            }
          />
          <TextField
            fullWidth
            margin="dense"
            label="mongodump path"
            value={config.mongodump_path || ""}
            onChange={(e) =>
              setConfig({ ...config, mongodump_path: e.target.value })
            }
            onBlur={() =>
              saveConfigField({ mongodump_path: config.mongodump_path })
            }
          />
        </ActionCard>
      )}

      <ConfirmDialog
        open={resetOpen}
        title="Release locks & tasks"
        body={
          <>
            <Typography variant="body1" sx={{ color: "#203d51", mb: 1, lineHeight: 1.55 }}>
              <strong>Does:</strong> Cancels every running and queued experiment
              and releases devices so you can submit again.
            </Typography>
            <Typography variant="body1" sx={{ color: "#203d51", mb: 1, lineHeight: 1.55 }}>
              <strong>Keeps:</strong> Sample positions and movement history.
            </Typography>
            <Typography variant="body1" sx={{ color: "#8a4b08", lineHeight: 1.55 }}>
              <strong>Does not:</strong> Emergency-stop hardware that is already
              moving.
            </Typography>
          </>
        }
        confirmLabel="Release locks & tasks"
        confirmColor="warning"
        onClose={() => setResetOpen(false)}
        onConfirm={async () => {
          const response = await reset_lab();
          if (response.status !== "success") {
            throw new Error(
              response.reason || "Release locks & tasks failed."
            );
          }
          setOk("Released locks and tasks.");
          await refreshIdle();
        }}
      />

      <ConfirmDialog
        open={clearOpen}
        title="Clear occupancy"
        body={
          <>
            <Typography variant="body1" sx={{ color: "#203d51", mb: 1, lineHeight: 1.55 }}>
              <strong>Does:</strong> Sets every sample&apos;s current position to
              empty and unlocks slot reservations.
            </Typography>
            <Typography variant="body1" sx={{ color: "#203d51", mb: 1, lineHeight: 1.55 }}>
              <strong>Keeps:</strong> Identity, last-known location, and movement
              history.
            </Typography>
            <Typography variant="body1" sx={{ color: "#8a4b08", lineHeight: 1.55 }}>
              <strong>Confirm:</strong> Type CLEAR to continue.
            </Typography>
          </>
        }
        confirmLabel="Clear occupancy"
        requireTyped="CLEAR"
        onClose={() => setClearOpen(false)}
        onConfirm={async () => {
          const response = await clear_lab_occupancy();
          if (response.status !== "success") {
            throw new Error(response.reason || "Clear occupancy failed.");
          }
          const n = response.data?.samples_cleared ?? 0;
          setOk(`Cleared occupancy for ${n} sample(s).`);
          await refreshIdle();
        }}
      />

      <ConfirmDialog
        open={refreshOpen}
        title="Refresh devices & slots"
        body={
          <>
            <Typography variant="body1" sx={{ color: "#203d51", mb: 1, lineHeight: 1.55 }}>
              <strong>Does:</strong> Stops AlabOS services, rebuilds device and
              sample-position definitions from code, then starts services again.
            </Typography>
            <Typography variant="body1" sx={{ color: "#203d51", lineHeight: 1.55 }}>
              <strong>Requires:</strong> Lab stays idle. Sample documents are not
              deleted.
            </Typography>
          </>
        }
        confirmLabel="Refresh and restart"
        confirmColor="primary"
        onClose={() => setRefreshOpen(false)}
        onConfirm={async () => {
          const { ok, data } = await control_refresh_definitions();
          if (!ok) {
            throw new Error(data.error || data.reason || "Refresh failed");
          }
          setOk(data.message || "Definitions refreshed; services restarted.");
          await waitForDashboardAndReload();
        }}
      />

      <ConfirmDialog
        open={nuclearOpen}
        title="Nuclear wipe live Alab"
        body={
          <>
            <Typography variant="body1" sx={{ color: "#203d51", mb: 1, lineHeight: 1.55 }}>
              <strong>Does:</strong> Drops the entire live database{" "}
              <strong>{config?.database_name || "Alab"}</strong>, then runs setup
              and restarts.
            </Typography>
            {nuclearBackupBeforeWipe ? (
              <Typography variant="body1" sx={{ color: "#203d51", mb: 1, lineHeight: 1.55 }}>
                <strong>Backup first:</strong> Runs the same MongoDB backup as
                Backup now, then wipes.
              </Typography>
            ) : (
              <Typography variant="body1" sx={{ color: "#8a4b08", mb: 1, lineHeight: 1.55 }}>
                <strong>No backup:</strong> Wipe proceeds without a MongoDB dump.
                Turn on Backup MongoDB before wipe if you need a safety copy.
              </Typography>
            )}
            <Typography variant="body1" sx={{ color: "#8a4b08", mb: 1, lineHeight: 1.55 }}>
              <strong>Loses:</strong> Mid-experiment samples not yet in
              Alab(completed).
            </Typography>
            <Typography variant="body1" sx={{ color: "#8a4b08", lineHeight: 1.55 }}>
              <strong>Confirm:</strong> Type the database name exactly.
            </Typography>
          </>
        }
        confirmLabel="Wipe and restart"
        requireTyped={config?.database_name || "Alab"}
        onClose={() => setNuclearOpen(false)}
        onConfirm={async () => {
          const name = config?.database_name || "Alab";
          const { ok, data } = await control_nuclear(
            name,
            nuclearBackupBeforeWipe
          );
          if (!ok) {
            throw new Error(data.error || data.reason || "Nuclear wipe failed");
          }
          setOk(data.message || "Live database wiped; services restarted.");
          await waitForDashboardAndReload();
        }}
      />
    </Box>
  );
}
