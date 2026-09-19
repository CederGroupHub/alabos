import { useEffect } from 'react';
import { get_experiment_status, get_experiment_ids, cancel_experiment, cancel_task } from '../../api_routes';
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
import Alert from '@mui/material/Alert';
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

function taskMentionsLabman(task) {
  const text = `${task?.type || ""} ${task?.description || ""}`.toLowerCase();
  return (
    text.includes("labman")
    || text.includes("powder dosing")
    || text.includes("powderdosing")
  );
}
function experimentHasLiveTasks(status) {
  return (status.tasks || []).some((task) => CANCELABLE_TASK_STATUSES.has(task.status));
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitUntilExperimentShowsCancelled(experimentId, { timeoutMs = 90000, intervalMs = 1000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  let latest = null;
  while (Date.now() < deadline) {
    latest = await get_experiment_status(experimentId);
    if (
      latest
      && latest.status === "CANCELLED"
      && !experimentHasLiveTasks(latest)
    ) {
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

function firstDescription(steps) {
  if (!steps || !steps.length) {
    return null;
  }
  return steps[0].description || steps[0].type || null;
}

function progressHeadline(status) {
  const steps = status.progress_steps || {};
  const current = firstDescription(steps.current);
  if (current) {
    return `Now: ${current}`;
  }
  // Terminal status is already shown on the line above — don't repeat it.
  if (
    status.status === "COMPLETED"
    || status.status === "CANCELLED"
    || status.status === "ERROR"
  ) {
    return null;
  }
  const next = firstDescription(steps.next);
  if (next) {
    return `Next: ${next}`;
  }
  const previous = firstDescription(steps.previous);
  if (previous) {
    return `Last: ${previous}`;
  }
  return null;
}

function ProgressStepCell({ label, tasks }) {
  const entries = tasks || [];
  return (
    <Box sx={{ flex: 1, minWidth: 0, px: 1 }}>
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
        {label}
      </Typography>
      {entries.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          —
        </Typography>
      ) : (
        entries.slice(0, 3).map((task, index) => (
          <Box key={task.id} sx={{ mb: entries.length > 1 ? 0.5 : 0 }}>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {task.description || task.type}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {task.status}
              {index === 2 && entries.length > 3 ? ` (+${entries.length - 3} more)` : ""}
            </Typography>
          </Box>
        ))
      )}
    </Box>
  );
}

function ProgressStepsStrip({ progressSteps }) {
  const steps = progressSteps || { previous: [], current: [], next: [] };
  return (
    <Box
      sx={{
        display: "flex",
        gap: 1,
        mb: 2,
        p: 1.5,
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1,
        bgcolor: "grey.50",
        flexWrap: "wrap",
      }}
    >
      <ProgressStepCell label="Previous" tasks={steps.previous} />
      <ProgressStepCell label="Now" tasks={steps.current} />
      <ProgressStepCell label="Next" tasks={steps.next} />
    </Box>
  );
}

function liveTasksFromStatus(status) {
  return (status?.tasks || []).filter((task) => CANCELABLE_TASK_STATUSES.has(task.status));
}

function sampleStayLines(status) {
  return (status?.samples || []).map((sample) => {
    const where = sample.position || sample.last_position || "unknown";
    return `${sample.name || sample.id} @ ${where}`;
  });
}

function formatCancelSummary(data) {
  if (!data || typeof data !== "object") {
    return "Experiment cancel finished.";
  }
  const parts = [];
  if (data.tasks_cancelled != null) {
    parts.push(`Cancelled ${data.tasks_cancelled} task${data.tasks_cancelled === 1 ? "" : "s"}`);
  }
  if (data.positions_unlocked != null) {
    parts.push(`unlocked ${data.positions_unlocked} position${data.positions_unlocked === 1 ? "" : "s"}`);
  }
  if (data.devices_released != null) {
    parts.push(`released ${data.devices_released} device${data.devices_released === 1 ? "" : "s"}`);
  }
  if (data.resource_requests_cancelled != null && data.resource_requests_cancelled > 0) {
    parts.push(`dropped ${data.resource_requests_cancelled} resource request${data.resource_requests_cancelled === 1 ? "" : "s"}`);
  }
  if (data.user_inputs_dismissed != null && data.user_inputs_dismissed > 0) {
    parts.push(`dismissed ${data.user_inputs_dismissed} prompt${data.user_inputs_dismissed === 1 ? "" : "s"}`);
  }
  if (data.experiment_closed) {
    parts.push("experiment marked cancelled");
  }
  if (data.archived_to_completed) {
    parts.push("archived to Alab(completed)");
  }
  if (data.samples_pruned != null && data.samples_pruned > 0) {
    parts.push(`pruned ${data.samples_pruned} live sample${data.samples_pruned === 1 ? "" : "s"}`);
  }
  return parts.length ? parts.join(" · ") : "Experiment cancel finished.";
}

function CancelConfirmDialog({ open, setOpen, type, id, experimentId, experimentStatus, onCancelled }) {
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [phase, setPhase] = React.useState("confirm"); // confirm | busy | done
  const [summary, setSummary] = React.useState("");

  React.useEffect(() => {
    if (open) {
      setBusy(false);
      setError(null);
      setPhase("confirm");
      setSummary("");
    }
  }, [open, id, type]);

  const isExperiment = type === "experiment";
  const liveTasks = isExperiment ? liveTasksFromStatus(experimentStatus) : [];
  const sampleLines = isExperiment ? sampleStayLines(experimentStatus) : [];
  const hasLabmanTasks = liveTasks.some(taskMentionsLabman);

  const handleClose = () => {
    if (busy) {
      return;
    }
    setError(null);
    setPhase("confirm");
    setSummary("");
    setOpen(false);
  };

  const handleCancel = async () => {
    setBusy(true);
    setError(null);
    setPhase("busy");
    try {
      const response = isExperiment
        ? await cancel_experiment(id)
        : await cancel_task(id);
      if (response.status !== "success") {
        setError(response.reason || response.errors || "Cancel failed.");
        setPhase("confirm");
        return;
      }
      if (isExperiment) {
        await waitUntilExperimentShowsCancelled(id);
        setSummary(formatCancelSummary(response.data));
        if (onCancelled) {
          await onCancelled();
        }
        setPhase("done");
      } else {
        await waitUntilTaskIsNotLive(experimentId, id);
        if (onCancelled) {
          await onCancelled();
        }
        await sleep(300);
        setOpen(false);
        setPhase("confirm");
      }
    } catch (err) {
      setError(String(err.message || err));
      setPhase("confirm");
    } finally {
      setBusy(false);
    }
  };

  const previewCap = 8;

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      disableEscapeKeyDown={busy}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>
        {phase === "done"
          ? "Experiment cancelled"
          : `Cancel ${isExperiment ? "Experiment" : "Task"}`}
      </DialogTitle>
      <DialogContent>
        {phase === "done" ? (
          <DialogContentText component="div">
            <Typography variant="body1" sx={{ mb: 1 }}>
              {summary}
            </Typography>
          </DialogContentText>
        ) : isExperiment ? (
          <DialogContentText component="div">
            <Box component="ul" sx={{ m: 0, mb: 2, pl: 2 }}>
              <Typography component="li" variant="body2" sx={{ mb: 0.5 }}>
                <Box component="span" sx={{ fontWeight: 700 }}>Stops in AlabOS:</Box>
                {" "}this experiment’s software work (live + waiting tasks, bookings, prompts).
              </Typography>
              <Typography component="li" variant="body2" sx={{ mb: 0.5 }}>
                <Box component="span" sx={{ fontWeight: 700 }}>Leaves:</Box>
                {" "}samples where they are; other experiments alone.
              </Typography>
              <Typography component="li" variant="body2">
                <Box component="span" sx={{ fontWeight: 700 }}>Does not stop:</Box>
                {" "}Labman, robot arms, or other hardware already running. Those keep
                going until they finish or you stop them on the machine.
              </Typography>
            </Box>

            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
              AlabOS tasks that will be marked cancelled
            </Typography>
            {hasLabmanTasks ? (
              <Alert severity="warning" sx={{ mb: 1.5 }}>
                <Typography variant="body2" sx={{ fontWeight: 700, mb: 0.5 }}>
                  Labman will keep running
                </Typography>
                <Typography variant="body2">
                  Powder dosing tasks below are AlabOS software only. Cancel does{" "}
                  <Box component="span" sx={{ fontWeight: 700 }}>not</Box> abort
                  the Labman workflow already submitted to a quadrant. Stop Labman
                  from the Labman UI if you need the hardware to stop.
                </Typography>
              </Alert>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                This is software only — cancelling a task ends AlabOS tracking, not
                hardware already in motion.
              </Typography>
            )}
            {liveTasks.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                Nothing live to cancel; experiment will be marked cancelled if still open.
              </Typography>
            ) : (
              <Box component="ul" sx={{ m: 0, mb: 1.5, pl: 2 }}>
                {liveTasks.slice(0, previewCap).map((task) => (
                  <Typography key={task.id} component="li" variant="body2">
                    {task.description || task.type} ({task.status})
                  </Typography>
                ))}
                {liveTasks.length > previewCap ? (
                  <Typography component="li" variant="body2" color="text.secondary">
                    +{liveTasks.length - previewCap} more
                  </Typography>
                ) : null}
              </Box>
            )}

            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
              Samples stay
            </Typography>
            {sampleLines.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                No samples on this experiment.
              </Typography>
            ) : (
              <Box component="ul" sx={{ m: 0, mb: 1.5, pl: 2 }}>
                {sampleLines.map((line) => (
                  <Typography key={line} component="li" variant="body2">
                    {line}
                  </Typography>
                ))}
              </Box>
            )}

            <Typography variant="body2" color="text.secondary">
              Also frees this experiment’s device/slot reservations in AlabOS.
            </Typography>
          </DialogContentText>
        ) : (
          <DialogContentText>
            Are you sure you want to cancel this task ({id})?
            Samples stay where they are. Devices booked by queued tasks are released.
          </DialogContentText>
        )}
        {phase === "busy" && (
          <DialogContentText sx={{ mt: 2 }}>
            {isExperiment
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
        {phase === "done" ? (
          <Button onClick={handleClose} autoFocus>
            Close
          </Button>
        ) : (
          <>
            {!busy && (
              <Button onClick={handleCancel} color="error">
                Yes, cancel
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
          </>
        )}
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
    { "_id": "", "status": "", "samples": [], "tasks": [], "progress": 0, "progress_steps": { previous: [], current: [], next: [] } }
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

  const headline = progressHeadline(status);

  return (
    <React.Fragment>
      <CancelConfirmDialog
        open={dialogOpen}
        setOpen={setDialogOpen}
        type={dialogType}
        id={dialogId}
        experimentId={experiment_id}
        experimentStatus={status}
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
        <TableCell align="left" sx={{ width: 300, maxWidth: 300, pr: 4 }}>
          <Box
            sx={{
              width: "100%",
              maxWidth: 240,
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
          {headline ? (
            <Typography
              variant="caption"
              display="block"
              color="text.secondary"
              sx={{
                mt: 0.25,
                maxWidth: 240,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
              title={headline}
            >
              {headline}
            </Typography>
          ) : null}
        </TableCell>
        {/* <TableCell align="right">{row.protein}</TableCell> */}

        <TableCell align="left">
          <Button
            variant="contained"
            color="error"
            disabled={!experimentHasLiveTasks(status)}
            onClick={() => handleCancel(status.id, "experiment")}
          >
            Cancel Experiment
          </Button>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 1 }}>
              <ProgressStepsStrip progressSteps={status.progress_steps} />

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
                    {status.tasks.map((task) => {
                      const isCurrent = (status.progress_steps?.current || []).some(
                        (entry) => entry.id === task.id
                      );
                      return (
                      <TableRow
                        key={task.id}
                        sx={isCurrent ? { bgcolor: "action.hover" } : undefined}
                      >
                        <TableCell component="th" scope="row">
                          <HoverText defaultText={task.description || task.type} hoverText={task.id} variant="body2" active={hoverForId} />
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
                      );
                    })}
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
            <TableCell align="left" sx={{ width: 300, maxWidth: 300, pr: 4 }}>Progress</TableCell>
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

function Experiments({ hoverForId }) {
  const [experimentIds, setExperimentIds] = React.useState([]);
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