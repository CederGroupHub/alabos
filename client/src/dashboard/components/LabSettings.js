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
        shell. Reset lab and Clear occupancy still work here.
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
      {reasons?.length ? `: ${reasons.join("; ")}` : "."} Finish or Reset lab
      before backup / clear occupancy / refresh / nuclear.
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

function ActionCard({ title, description, children, actions }) {
  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {description}
        </Typography>
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
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
        <SettingsIcon color="action" />
        <Typography variant="h5">Lab settings</Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Recover from crashes, clear software occupancy, back up MongoDB, and
        refresh device/slot definitions — without using the old launcher
        checklist for day-to-day work.
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

      <ActionCard
        title="Reset lab"
        description="Use after a crash or when tasks/locks are stuck. Cancels live work and releases devices, locks, and reservations. Keeps sample positions and movement history."
        actions={
          <Button
            variant="contained"
            color="warning"
            onClick={() => setResetOpen(true)}
          >
            Reset lab
          </Button>
        }
      />

      <ActionCard
        title="Clear occupancy"
        description="Use when the physical lab is empty (or you want software to treat every slot as empty). Sets current position to empty, unlocks reservations, appends history. Keeps sample identity, last-known location, and history. Does not cancel experiments — Reset first if anything is still running."
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
        description="Point-in-time mongodump of all databases. Allowed only when the lab is idle. Optional backup-on-launch runs during bootstrap before services start (cold start is idle)."
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
        description="Stop services, rebuild devices & slots from code (alabos clean + setup), then start again. Use after changing device/slot definitions in code. Lab must be idle."
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
        description="Apply saved environment defaults (database name and related flags). Does not wipe data by itself."
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
      <Typography variant="h6" gutterBottom>
        Advanced
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Rare or install-time settings. Nuclear wipe drops the entire live AlabOS
        database (not Alab(completed)).
      </Typography>

      <ActionCard
        title="Nuclear wipe live Alab"
        description="Stop services, drop the live database, run setup, restart. For sim / brand-new install only. Requires typing the database name."
        actions={
          <Button
            variant="outlined"
            color="error"
            disabled={!idle || controlAvailable === false}
            onClick={() => setNuclearOpen(true)}
          >
            Nuclear wipe…
          </Button>
        }
      />

      {config && controlAvailable !== false && (
        <ActionCard
          title="Launch & paths"
          description="Defaults used by the bootstrap shell on next launch / refresh."
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
        title="Reset lab"
        body={
          <>
            Cancels every running and queued experiment and releases devices so
            you can submit again. Keeps sample positions and history. Does not
            emergency-stop hardware that is already moving.
          </>
        }
        confirmLabel="Reset everything"
        confirmColor="warning"
        onClose={() => setResetOpen(false)}
        onConfirm={async () => {
          const response = await reset_lab();
          if (response.status !== "success") {
            throw new Error(response.reason || "Reset lab failed.");
          }
          setOk("Lab reset finished.");
          await refreshIdle();
        }}
      />

      <ConfirmDialog
        open={clearOpen}
        title="Clear occupancy"
        body={
          <>
            Sets every sample&apos;s current position to empty and unlocks slot
            reservations. Identity, last-known location, and movement history
            are kept. Type CLEAR to confirm.
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
            Stops AlabOS services, rebuilds device and sample-position
            definitions from code, then starts services again. Lab must stay
            idle. Sample documents are not deleted.
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
            Drops the entire live database{" "}
            <strong>{config?.database_name || "Alab"}</strong>, then runs setup
            and restarts. Mid-experiment samples not yet in Alab(completed) will
            be lost. Type the database name to confirm.
          </>
        }
        confirmLabel="Wipe and restart"
        requireTyped={config?.database_name || "Alab"}
        onClose={() => setNuclearOpen(false)}
        onConfirm={async () => {
          const name = config?.database_name || "Alab";
          const { ok, data } = await control_nuclear(name);
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
