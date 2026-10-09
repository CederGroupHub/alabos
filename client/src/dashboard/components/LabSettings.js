import React, { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Chip,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  FormControlLabel,
  Link,
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

function IdleStatus({ idle, reasons, controlAvailable }) {
  return (
    <Box sx={{ mb: 2.5, maxWidth: 820 }}>
      <Chip
        size="small"
        label={idle ? "Lab idle" : "Lab not idle"}
        sx={{
          fontWeight: 600,
          mb: 0.75,
          bgcolor: idle ? "rgba(67, 160, 71, 0.12)" : "rgba(32, 61, 81, 0.08)",
          color: idle ? "#2e7d32" : "#203d51",
          border: idle
            ? "1px solid rgba(67, 160, 71, 0.35)"
            : "1px solid rgba(32, 61, 81, 0.18)",
        }}
      />
      {!idle && reasons?.length ? (
        <Typography
          variant="body2"
          sx={{ color: "#5a7384", lineHeight: 1.5, mb: 0.5 }}
        >
          {reasons.join("; ")}. Use Reset lab software (or Release locks only)
          before backup / refresh / nuclear.
        </Typography>
      ) : null}
      {controlAvailable === false ? (
        <Typography variant="body2" sx={{ color: "#5a7384", lineHeight: 1.5 }}>
          Bootstrap control plane (8894) is not reachable. Backup, refresh,
          nuclear wipe, and Advanced config need the A-Lab OS app shell. Reset
          lab software still works here.
        </Typography>
      ) : null}
    </Box>
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

  const [resetSoftwareOpen, setResetSoftwareOpen] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [clearOpen, setClearOpen] = useState(false);
  const [edgeCasesOpen, setEdgeCasesOpen] = useState(false);
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
        Day-to-day recovery: reset stuck software for a fresh run, back up
        MongoDB, and refresh device definitions. Nuclear wipe (Advanced) is a
        last resort that drops the live database.
      </Typography>

      <IdleStatus
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

      <ActionCard
        title="Reset lab software"
        facts={[
          {
            label: "When",
            text: "After a crash, or when you want a clean software state for a new run.",
          },
          {
            label: "Does",
            text: "Releases locks & tasks, then clears occupancy so every slot is empty in software.",
          },
          {
            label: "Keeps",
            text: "Sample identities, last-known locations, movement history, and Alab(completed).",
          },
          {
            label: "Does not",
            text: "Emergency-stop hardware that is already moving. Match the physical bench after.",
          },
        ]}
        actions={
          <Box sx={{ width: "100%" }}>
            <Button
              variant="contained"
              color="primary"
              onClick={() => setResetSoftwareOpen(true)}
            >
              Reset lab software
            </Button>
            <Box sx={{ mt: 1.25 }}>
              <Link
                component="button"
                type="button"
                variant="body2"
                underline="hover"
                onClick={() => setEdgeCasesOpen((open) => !open)}
                sx={{ color: "#5a7384" }}
              >
                {edgeCasesOpen
                  ? "Hide separate steps"
                  : "Need only one step? (edge cases)"}
              </Link>
            </Box>
            <Collapse in={edgeCasesOpen}>
              <Box
                sx={{
                  mt: 1.5,
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 1,
                  alignItems: "center",
                }}
              >
                <Button
                  variant="outlined"
                  color="warning"
                  size="small"
                  onClick={() => setResetOpen(true)}
                >
                  Release locks & tasks only
                </Button>
                <Button
                  variant="outlined"
                  color="warning"
                  size="small"
                  disabled={!idle}
                  onClick={() => setClearOpen(true)}
                >
                  Clear occupancy only
                </Button>
              </Box>
            </Collapse>
          </Box>
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
        open={resetSoftwareOpen}
        title="Reset lab software"
        body={
          <>
            <Typography variant="body1" sx={{ color: "#203d51", mb: 1, lineHeight: 1.55 }}>
              Cancels live work and releases locks, then clears every sample
              position in software so the lab looks empty for a new run.
            </Typography>
            <Typography variant="body1" sx={{ color: "#203d51", lineHeight: 1.55 }}>
              Does not drop the database or erase Alab(completed). Match the
              physical bench afterward.
            </Typography>
          </>
        }
        confirmLabel="Reset lab software"
        confirmColor="primary"
        onClose={() => setResetSoftwareOpen(false)}
        onConfirm={async () => {
          const release = await reset_lab();
          if (release.status !== "success") {
            throw new Error(
              release.reason || "Release locks & tasks failed."
            );
          }
          await refreshIdle();
          const clear = await clear_lab_occupancy();
          if (clear.status !== "success") {
            throw new Error(
              clear.reason ||
                "Locks released, but clear occupancy failed. Try Clear occupancy only."
            );
          }
          const n = clear.data?.samples_cleared ?? 0;
          setOk(
            `Lab software reset. Cleared occupancy for ${n} sample(s).`
          );
          await refreshIdle();
        }}
      />

      <ConfirmDialog
        open={resetOpen}
        title="Release locks & tasks only"
        body={
          <>
            <Typography variant="body1" sx={{ color: "#203d51", mb: 1, lineHeight: 1.55 }}>
              Cancels running and queued work and releases devices. Leaves sample
              positions as they are.
            </Typography>
            <Typography variant="body1" sx={{ color: "#203d51", lineHeight: 1.55 }}>
              Does not emergency-stop hardware that is already moving.
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
        title="Clear occupancy only"
        body={
          <>
            <Typography variant="body1" sx={{ color: "#203d51", mb: 1, lineHeight: 1.55 }}>
              Sets every sample&apos;s current position empty and unlocks slots.
              Lab must already be idle.
            </Typography>
            <Typography variant="body1" sx={{ color: "#8a4b08", lineHeight: 1.55 }}>
              Type CLEAR to continue.
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
