import { useEffect } from 'react';
import { get_experiment_status, get_experiment_ids, reset_lab, cancel_experiment, cancel_task } from '../../api_routes';
import LinearProgress from '@mui/material/LinearProgress';//
import * as React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Collapse from '@mui/material/Collapse';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import IconButton from '@mui/material/IconButton';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import { HoverText } from '../../utils';

const timezoneOffset = (new Date()).getTimezoneOffset();

const CANCELABLE_TASK_STATUSES = new Set([
  "WAITING",
  "READY",
  "INITIATED",
  "REQUESTING_RESOURCES",
  "RUNNING",
  "FINISHING",
]);

function experimentCanBeCancelled(status) {
  return (status.tasks || []).some((task) => CANCELABLE_TASK_STATUSES.has(task.status));
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitUntilExperimentsHaveNoLiveTasks(experimentIds, { timeoutMs = 90000, intervalMs = 1000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  let latest = [];
  while (Date.now() < deadline) {
    latest = await Promise.all((experimentIds || []).map((id) => get_experiment_status(id)));
    const stillLive = latest.some((status) => !status || experimentCanBeCancelled(status));
    if (!stillLive) {
      return latest;
    }
    await sleep(intervalMs);
  }
  throw new Error("Reset was sent, but some tasks are still finishing. Check the list and try again if needed.");
}

async function waitUntilExperimentShowsCancelled(experimentId, { timeoutMs = 90000, intervalMs = 1000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  let latest = null;
  while (Date.now() < deadline) {
    latest = await get_experiment_status(experimentId);
    if (latest && latest.status === "CANCELLED" && !experimentCanBeCancelled(latest)) {
      return latest;
    }
    await sleep(intervalMs);
  }
  throw new Error("Cancel was sent, but the experiment still has live tasks. Check the list and try again if needed.");
}

async function waitUntilTaskIsNotLive(experimentId, taskId, { timeoutMs = 90000, intervalMs = 1000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const latest = await get_experiment_status(experimentId);
    const task = (latest && latest.tasks || []).find((entry) => entry.id === taskId);
    if (task && !CANCELABLE_TASK_STATUSES.has(task.status)) {
      return latest;
    }
    await sleep(intervalMs);
  }
  throw new Error("Cancel was sent, but the task is still live. Check the list and try again if needed.");
}

function experimentStatusLabel(status) {
  switch (status) {
    case "CANCELLED":
      return "Cancelled — no live tasks";
    case "ERROR":
      return "Error";
    case "COMPLETED":
      return "Completed";
    case "RUNNING":
      return "Running";
    default:
      return status || "";
  }
}

function CancelConfirmDialog({ open, setOpen, type, id, experimentId, onCancelled }) {
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(null);

  const handleClose = () => {
    if (busy) {
      return;
    }
    setError(null);
    setOpen(false);
  };

  const handleCancel = async () => {
    setBusy(true);
    setError(null);
    try {
      const response = type === "experiment"
        ? await cancel_experiment(id)
        : await cancel_task(id);
      if (response.status !== "success") {
        setError(response.reason || response.errors || "Cancel failed.");
        return;
      }
      if (type === "experiment") {
        await waitUntilExperimentShowsCancelled(id);
      } else {
        await waitUntilTaskIsNotLive(experimentId, id);
      }
      if (onCancelled) {
        await onCancelled();
      }
      await sleep(300);
      setError(null);
      setOpen(false);
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      disableEscapeKeyDown={busy}
    >
      <DialogTitle>Cancel {type === "experiment" ? "Experiment" : "Task"}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          Are you sure you want to cancel this {type === "experiment" ? "experiment" : "task"} ({id})?
          Samples stay where they are. Devices booked by queued tasks are released.
        </DialogContentText>
        {busy && (
          <DialogContentText sx={{ mt: 2 }}>
            {type === "experiment"
              ? "Cancelling… waiting until this experiment shows as Cancelled with no live tasks."
              : "Cancelling… waiting until this task is no longer live."}
          </DialogContentText>
        )}
        {error && (
          <DialogContentText sx={{ mt: 2 }} color="error">
            {error}
          </DialogContentText>
        )}
      </DialogContent>
      <DialogActions>
        {!busy && (
          <Button onClick={handleCancel} color="error">
            Yes
          </Button>
        )}
        {busy && (
          <Button disabled>
            Cancelling…
          </Button>
        )}
        <Button onClick={handleClose} autoFocus disabled={busy}>
          No
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function Row({ experiment_id, hoverForId, onExperimentCancelled, refreshEpoch }) {
  const [open, setOpen] = React.useState(false);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [dialogId, setDialogId] = React.useState("");
  const [dialogType, setDialogType] = React.useState("Task");
  const [status, setStatus] = React.useState(
    { "_id": "", "status": "", "samples": [], "tasks": [], "progress": 0 }
  );
  const [taskOpen, setTaskOpen] = React.useState(false);
  const [sampleOpen, setSampleOpen] = React.useState(false);

  useEffect(() => {
    get_experiment_status(experiment_id).then(status => {
      setStatus(status);
    })
    if (status.progress === 1.0) {
      return;
    }
    const refreshPeriod = open ? 1000 : 30000; //refresh every second if open, every 30 seconds if closed

    const interval = setInterval(() => {
      get_experiment_status(experiment_id).then(status => {
        setStatus(status);
      })
    }, refreshPeriod);
    return () => clearInterval(interval);
  }, [status.progress, open, refreshEpoch, experiment_id]);

  const refreshStatus = () => {
    return get_experiment_status(experiment_id).then(nextStatus => {
      setStatus(nextStatus);
    });
  };

  const handleCancel = (id, type) => {
    setDialogOpen(true);
    setDialogId(id);
    setDialogType(type);
  };

  const progressBarColor = () => {
    switch (status.status) {
      case "RUNNING":
        return "primary";
      case "ERROR":
        return "error";
      case "COMPLETED":
        return "success";
      case "CANCELLED":
        return "inherit";
      default:
        return "warning";
    }
  }

  const taskStatusColor = (task_status) => {
    switch (task_status) {
      case "RUNNING":
        return "primary";
      case "REQUESTING_RESOURCES":
        return "orange";
      case "WAITING":
        return "secondary";
      case "ERROR":
        return "error";
      case "COMPLETED":
        return "inherit";
      case "CANCELLED":
        return "gray";
      default:
        return "inherit";
    }
  }

  function timestampInLocale(timestamp_string) {
    const localTime = new Date(timestamp_string);
    localTime.setMinutes(localTime.getMinutes() + timezoneOffset);
    return `${localTime.toLocaleString()}`
  }

  return (
    <React.Fragment>
      <CancelConfirmDialog
        open={dialogOpen}
        setOpen={setDialogOpen}
        type={dialogType}
        id={dialogId}
        experimentId={experiment_id}
        onCancelled={async () => {
          await refreshStatus();
          if (onExperimentCancelled) {
            await onExperimentCancelled();
          }
        }}
      />
      <TableRow sx={{ '& > *': { borderBottom: 'unset' } }}>
        <TableCell>
          <IconButton
            aria-label="expand row"
            size="small"
            onClick={() => setOpen(!open)}
          >
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell component="th" scope="row">
          <HoverText defaultText={status.name} hoverText={status.id} variant="body1" active={hoverForId} />
          {/* {status.name} */}
        </TableCell>

        {/* <TableCell align="left">
          <Typography variant="body2">{status.id}</Typography>
        </TableCell> */}

        <TableCell align="left">
          <Typography variant="body2">{status.samples.length}</Typography>
        </TableCell>


        <TableCell align="left"><Typography variant="body2">{timestampInLocale(status.submitted_at)}</Typography></TableCell>
        <TableCell align="center" sx={{ width: 220 }}>
          <Box
            sx={{
              width: "100%",
              mx: "auto",
              border: "1px solid",
              borderColor: "text.primary",
              borderRadius: "2px",
              overflow: "hidden",
              bgcolor: "grey.100",
              height: 14,
            }}
          >
            <LinearProgress
              variant="determinate"
              value={Math.round((status.progress || 0) * 100)}
              color={progressBarColor()}
              sx={{
                height: 14,
                bgcolor: "transparent",
                "& .MuiLinearProgress-bar": {
                  transition: "transform 0.2s linear",
                },
              }}
            />
          </Box>
          <Typography variant="caption" color={status.status === "CANCELLED" ? "text.secondary" : "text.primary"}>
            {experimentStatusLabel(status.status)}
          </Typography>
        </TableCell>
        {/* <TableCell align="right">{row.protein}</TableCell> */}

        <TableCell align="left">
          <Button
            variant="contained"
            color="error"
            disabled={!experimentCanBeCancelled(status)}
            onClick={() => handleCancel(status.id, "experiment")}
          >
            {status.status === "CANCELLED" ? "Cancelled" : "Cancel Experiment"}
          </Button>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 1 }}>

              <Typography variant="body1" gutterBottom component="div">
                <IconButton
                  aria-label="expand row"
                  size="small"
                  onClick={() => setSampleOpen(!sampleOpen)}
                >
                  {sampleOpen ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                </IconButton>
                Samples
              </Typography>
              <Collapse in={sampleOpen} timeout="auto" unmountOnExit>
                <Table size="small" aria-label="purchases">
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell>Position</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {status.samples.map((sample) => (
                      <TableRow key={sample.id}>
                        <TableCell component="th" scope="row">
                          <HoverText defaultText={sample.name} hoverText={sample.id} variant="body2" active={hoverForId} />
                          {/* {sample.name} */}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body">
                            {sample.position}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Collapse>


              <Typography variant="body1" gutterBottom component="div">
                <IconButton
                  aria-label="expand row"
                  size="small"
                  onClick={() => setTaskOpen(!taskOpen)}
                >
                  {taskOpen ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                </IconButton>
                Tasks
              </Typography>
              <Collapse in={taskOpen} timeout="auto" unmountOnExit>
                <Table size="small" aria-label="purchases">
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell width="50%">Message</TableCell>
                      <TableCell>Cancel Task</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {status.tasks.map((task) => (
                      <TableRow key={task.id}>
                        <TableCell component="th" scope="row">
                          <HoverText defaultText={task.type} hoverText={task.id} variant="body2" active={hoverForId} />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body" color={taskStatusColor(task.status)}>
                            {task.status}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body" style={{
                            whiteSpace: "pre-wrap",
                            display: '-webkit-box',
                            overflow: 'auto',
                            WebkitBoxOrient: 'vertical',
                            WebkitLineClamp: 2,
                          }}>
                            {task.message}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="outlined"
                            color="error"
                            disabled={!CANCELABLE_TASK_STATUSES.has(task.status)}
                            onClick={() => handleCancel(task.id, "task")}
                          >
                            Cancel
                          </Button>
                        </TableCell>
                        {/* <TableCell>{task.result}</TableCell>  */}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Collapse>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </React.Fragment>
  );
}

function CollapsibleTable({ experiment_ids, hoverForId, onExperimentCancelled, refreshEpoch }) {
  return (
    <TableContainer component={Paper}>
      <Table aria-label="collapsible table">
        <TableHead>
          <TableRow>
            <TableCell />
            <TableCell>Name</TableCell>
            <TableCell align="left"># Samples</TableCell>
            <TableCell align="left">Submitted At</TableCell>
            <TableCell align="center" sx={{ width: 220 }}>Progress</TableCell>
            <TableCell align="left">Cancel Exp</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {experiment_ids.map((experiment_id) => (
            <Row key={experiment_id} experiment_id={experiment_id} hoverForId={hoverForId} onExperimentCancelled={onExperimentCancelled} refreshEpoch={refreshEpoch} />
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

function ResetLabDialog({ open, setOpen, experimentIds, onReset }) {
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(null);

  const handleClose = () => {
    if (busy) {
      return;
    }
    setError(null);
    setOpen(false);
  };

  const handleReset = async () => {
    setBusy(true);
    setError(null);
    const idsAtStart = [...(experimentIds || [])];
    try {
      const response = await reset_lab();
      if (response.status !== "success") {
        setError(response.reason || "Reset lab failed.");
        return;
      }
      await waitUntilExperimentsHaveNoLiveTasks(idsAtStart);
      await onReset();
      await sleep(300);
      setError(null);
      setOpen(false);
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      disableEscapeKeyDown={busy}
    >
      <DialogTitle>Reset lab</DialogTitle>
      <DialogContent>
        <DialogContentText>
          This cancels every running and queued experiment and releases devices
          so you can submit again. Cancelled experiments stay on this list,
          marked cancelled, with no live tasks. It does not dismiss Labman or
          other maintenance prompts, and it does not emergency-stop hardware
          that is already moving.
        </DialogContentText>
        {busy && (
          <DialogContentText sx={{ mt: 2 }}>
            Resetting… waiting until every experiment shows no live tasks.
          </DialogContentText>
        )}
        {error && (
          <DialogContentText sx={{ mt: 2 }} color="error">
            {error}
          </DialogContentText>
        )}
      </DialogContent>
      <DialogActions>
        {!busy && (
          <Button onClick={handleReset} color="error">
            Reset everything
          </Button>
        )}
        {busy && (
          <Button disabled>
            Resetting…
          </Button>
        )}
        <Button onClick={handleClose} autoFocus disabled={busy}>
          Cancel
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function Experiments({ hoverForId }) {
  const [experimentIds, setExperimentIds] = React.useState([]);
  const [resetOpen, setResetOpen] = React.useState(false);
  const [refreshEpoch, setRefreshEpoch] = React.useState(0);

  const refreshExperimentIds = async () => {
    const ids = await get_experiment_ids();
    setExperimentIds(ids || []);
    setRefreshEpoch((value) => value + 1);
  };

  useEffect(() => {
    refreshExperimentIds();
    const interval = setInterval(refreshExperimentIds, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
        <Button
          variant="contained"
          color="error"
          disabled={resetOpen}
          onClick={() => setResetOpen(true)}
        >
          Reset lab
        </Button>
      </Box>
      <ResetLabDialog
        open={resetOpen}
        setOpen={setResetOpen}
        experimentIds={experimentIds}
        onReset={refreshExperimentIds}
      />
      <CollapsibleTable
        experiment_ids={experimentIds}
        hoverForId={hoverForId}
        onExperimentCancelled={refreshExperimentIds}
        refreshEpoch={refreshEpoch}
      />
    </Box>
  );
}

export default Experiments;