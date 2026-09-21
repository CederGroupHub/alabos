import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Snackbar,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import styled from 'styled-components';
import { clear_sample_position, get_lab_idle, get_sample_position_racks } from '../../api_routes';

const RackContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin: 12px 16px;
`;

const SlotGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
`;

const HighlightedSlot = styled.div`
  border-radius: 8px;
  outline: ${(props) => (props.$active ? '3px solid #1976d2' : 'none')};
  outline-offset: 2px;
  transition: outline-color 0.2s ease;
  min-width: 0;
`;

function TruncatedLine({ children, variant = "body2", sx = {}, ...rest }) {
  return (
    <Typography
      variant={variant}
      title={typeof children === "string" ? children : undefined}
      sx={{
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
        minWidth: 0,
        ...sx,
      }}
      {...rest}
    >
      {children}
    </Typography>
  );
}

function WrappingText({ children, variant = "body2", sx = {}, ...rest }) {
  return (
    <Typography
      variant={variant}
      sx={{
        overflowWrap: "anywhere",
        wordBreak: "break-word",
        whiteSpace: "normal",
        ...sx,
      }}
      {...rest}
    >
      {children}
    </Typography>
  );
}

function slotStatusColor(slot) {
  if (slot.sample?.in_transit) {
    return "#e3f2fd";
  }
  switch (slot.status) {
    case "OCCUPIED":
      return "#e8f5e9";
    case "LOCKED":
      return "#fff8e1";
    default:
      return "#fafafa";
  }
}

function formatWhen(at) {
  if (!at) {
    return "?";
  }
  return String(at).replace("T", " ").slice(0, 19);
}

function formatBadge(summary) {
  if (!summary) {
    return "";
  }
  const parts = [];
  parts.push(`${summary.occupied || 0} occupied`);
  if (summary.locked) {
    parts.push(`${summary.locked} locked`);
  }
  if (summary.in_transit) {
    parts.push(`${summary.in_transit} in transit`);
  }
  return parts.join(" · ");
}

function eventLabel(event) {
  switch (event) {
    case "placed":
      return "Placed";
    case "moved":
      return "Moved";
    case "in_transit":
      return "In transit";
    case "cleared":
      return "Cleared";
    default:
      return event || "Event";
  }
}

function ownershipCaption(sample) {
  if (!sample) {
    return null;
  }
  const parts = [];
  if (sample.campaign) {
    parts.push(`campaign: ${sample.campaign}`);
  }
  if (sample.owner) {
    parts.push(`owner: ${sample.owner}`);
  }
  if (sample.project) {
    parts.push(`project: ${sample.project}`);
  }
  if (sample.experiment_name) {
    parts.push(`exp: ${sample.experiment_name}`);
  }
  return parts.length ? parts.join(" · ") : null;
}

function deviceFromPosition(position) {
  if (!position || typeof position !== "string") {
    return null;
  }
  const device = position.split("/")[0];
  return device || null;
}


/** Newest-first copy of history. */
function historyNewestFirst(history) {
  return [...(history || [])].reverse();
}

/**
 * Build "now" / "before that" lines for the history dialog.
 * Uses live position first; falls back to last_position / latest history entry.
 */
function summarizeMovement(sample) {
  const history = historyNewestFirst(sample?.position_history);
  const transit = sample?.in_transit;
  let nowLabel;
  let nowPosition = sample?.position || null;

  if (transit && (transit.source || transit.destination)) {
    nowLabel = `In transit: ${transit.source || "?"} → ${transit.destination || "?"}`;
    nowPosition = sample?.position || transit.source || null;
  } else if (nowPosition) {
    nowLabel = nowPosition;
  } else if (sample?.last_position) {
    nowLabel = `Unplaced (last known: ${sample.last_position})`;
    nowPosition = null;
  } else {
    nowLabel = "No current position";
  }

  let beforePosition = null;
  let beforeLabel = null;
  for (const entry of history) {
    const candidate = entry.position;
    if (!candidate) {
      continue;
    }
    if (nowPosition && candidate === nowPosition) {
      continue;
    }
    beforePosition = candidate;
    beforeLabel = candidate;
    break;
  }
  if (!beforeLabel && sample?.last_position && sample.last_position !== nowPosition) {
    beforePosition = sample.last_position;
    beforeLabel = sample.last_position;
  }

  return {
    nowLabel,
    nowPosition,
    beforeLabel,
    beforePosition,
    history,
  };
}

function PositionHistoryTimeline({ history, onJump }) {
  if (!history || history.length === 0) {
    return (
      <Typography variant="caption" color="text.secondary">
        No movement history yet (older samples only start logging after new moves).
      </Typography>
    );
  }
  return (
    <Stack spacing={1}>
      {history.map((entry, index) => {
        const jumpTarget = entry.position;
        const canJump = Boolean(jumpTarget && onJump && deviceFromPosition(jumpTarget));
        return (
          <Box
            key={`${entry.at}-${entry.event}-${index}`}
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: 1,
              py: 0.5,
              borderBottom: "1px solid #eee",
            }}
          >
            <Box>
              <Typography variant="body2">
                <b>{eventLabel(entry.event)}</b>
                {" · "}
                {entry.position || "(none)"}
                {entry.destination ? ` → ${entry.destination}` : ""}
              </Typography>
              <Typography variant="caption" color="text.secondary" display="block">
                {formatWhen(entry.at)}
                {entry.task_id ? ` · task ${entry.task_id}` : ""}
              </Typography>
            </Box>
            {canJump && (
              <Button size="small" onClick={() => onJump(jumpTarget)}>
                Jump
              </Button>
            )}
          </Box>
        );
      })}
    </Stack>
  );
}

function SampleDetailDialog({ open, onClose, sample, onJumpToPosition }) {
  if (!sample) {
    return null;
  }
  const summary = summarizeMovement(sample);
  const jump = (position) => {
    if (onJumpToPosition && position) {
      onJumpToPosition(position);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Movement history — {sample.name}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Sample ID: {sample.sample_id}
          </Typography>
          {ownershipCaption(sample) && (
            <Typography variant="body2">{ownershipCaption(sample)}</Typography>
          )}

          <Paper variant="outlined" sx={{ p: 1.5 }}>
            <Stack spacing={1}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" gap={1}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Now
                  </Typography>
                  <Typography variant="body1">{summary.nowLabel}</Typography>
                </Box>
                {summary.nowPosition && onJumpToPosition && (
                  <Button size="small" variant="outlined" onClick={() => jump(summary.nowPosition)}>
                    Jump
                  </Button>
                )}
              </Stack>
              <Stack direction="row" justifyContent="space-between" alignItems="center" gap={1}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Before that
                  </Typography>
                  <Typography variant="body1">
                    {summary.beforeLabel || "No earlier position recorded"}
                  </Typography>
                </Box>
                {summary.beforePosition && onJumpToPosition && (
                  <Button size="small" variant="outlined" onClick={() => jump(summary.beforePosition)}>
                    Jump
                  </Button>
                )}
              </Stack>
            </Stack>
          </Paper>

          <Typography variant="subtitle2">Timeline (newest first)</Typography>
          <PositionHistoryTimeline history={summary.history} onJump={jump} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

function SlotCard({ slot, highlighted, onClear, onShowSample, slotRef, clearDisabled, clearDisabledReason }) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const occupied = slot.status === "OCCUPIED";
  const inTransit = Boolean(slot.sample?.in_transit);
  const clearBlocked = !occupied || clearDisabled;
  const sample = slot.sample;
  const ownership = ownershipCaption(sample);
  const shortId = sample?.sample_id
    ? `${String(sample.sample_id).slice(0, 8)}…`
    : null;

  return (
    <HighlightedSlot $active={highlighted} ref={slotRef}>
      <Card
        variant="outlined"
        sx={{
          bgcolor: slotStatusColor(slot),
          height: "100%",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <CardContent
          sx={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            gap: 1,
            py: 1.5,
            "&:last-child": { pb: 1.5 },
            minWidth: 0,
          }}
        >
          <Stack spacing={0.75} sx={{ minWidth: 0 }}>
            <Typography variant="subtitle1">
              Slot {slot.slot_number}
            </Typography>
            <Stack
              direction="row"
              flexWrap="wrap"
              sx={{ minWidth: 0, gap: 0.75 }}
            >
              {inTransit && <Chip label="IN TRANSIT" size="small" color="info" />}
              <Chip label={slot.status} size="small" />
            </Stack>
          </Stack>

          <TruncatedLine variant="caption" color="text.secondary" title={slot.name}>
            {slot.name}
          </TruncatedLine>

          {sample ? (
            <Box sx={{ minWidth: 0 }}>
              <TruncatedLine variant="body2" sx={{ fontWeight: 700 }}>
                {sample.name}
              </TruncatedLine>
              {shortId && (
                <TruncatedLine variant="caption" color="text.secondary">
                  {shortId}
                </TruncatedLine>
              )}
              <Button
                size="small"
                onClick={() => setDetailsOpen((prev) => !prev)}
                endIcon={detailsOpen ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                sx={{ px: 0, mt: 0.25, textTransform: "none" }}
              >
                {detailsOpen ? "Hide details" : "Details"}
              </Button>
              <Collapse in={detailsOpen} timeout="auto" unmountOnExit>
                <Box
                  sx={{
                    mt: 1,
                    pt: 1,
                    borderTop: "1px solid",
                    borderColor: "divider",
                    minWidth: 0,
                  }}
                >
                  <Stack spacing={0.75}>
                    <Box>
                      <Typography variant="caption" color="text.secondary" display="block">
                        Sample name
                      </Typography>
                      <WrappingText variant="body2" sx={{ fontWeight: 700 }}>
                        {sample.name}
                      </WrappingText>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary" display="block">
                        Sample ID
                      </Typography>
                      <WrappingText variant="caption" color="text.secondary" display="block">
                        {sample.sample_id}
                      </WrappingText>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary" display="block">
                        Position
                      </Typography>
                      <WrappingText variant="caption" color="text.secondary" display="block">
                        {slot.name}
                      </WrappingText>
                    </Box>
                    {ownership && (
                      <Box>
                        <Typography variant="caption" color="text.secondary" display="block">
                          Context
                        </Typography>
                        <WrappingText variant="caption" color="text.secondary" display="block">
                          {ownership}
                        </WrappingText>
                      </Box>
                    )}
                    {sample.tags?.length > 0 && (
                      <Box>
                        <Typography variant="caption" color="text.secondary" display="block">
                          Tags
                        </Typography>
                        <WrappingText variant="caption" color="text.secondary" display="block">
                          {sample.tags.join(" · ")}
                        </WrappingText>
                      </Box>
                    )}
                    <Button
                      size="small"
                      onClick={() => onShowSample(sample)}
                      sx={{ px: 0, alignSelf: "flex-start", textTransform: "none" }}
                    >
                      History
                    </Button>
                  </Stack>
                </Box>
              </Collapse>
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No sample present.
            </Typography>
          )}

          {slot.locked_by_task_id && !occupied && (
            <WrappingText variant="caption" color="text.secondary">
              Locked by task {slot.locked_by_task_id}
            </WrappingText>
          )}

          <Box sx={{ flexGrow: 1 }} />
          <Button
            size="small"
            variant="outlined"
            fullWidth
            onClick={() => onClear(slot.name)}
            disabled={clearBlocked}
            title={
              occupied && clearDisabled
                ? clearDisabledReason || "Lab is not idle"
                : undefined
            }
          >
            Clear
          </Button>
        </CardContent>
      </Card>
    </HighlightedSlot>
  );
}

function DeviceOccupancyRow({
  rack,
  open,
  onToggle,
  highlightedPosition,
  slotRefs,
  onClear,
  onShowSample,
  clearDisabled,
  clearDisabledReason,
}) {
  const summary = rack.summary || {};
  const occupiedCount = summary.occupied || 0;
  const hasOccupied = occupiedCount > 0;
  let rowBg;
  if (hasOccupied) {
    // Match OCCUPIED slot tint; slightly stronger when the row is expanded.
    rowBg = open ? "#c8e6c9" : "#e8f5e9";
  } else if (open) {
    rowBg = "#f5f9fb";
  }
  return (
    <>
      <TableRow
        hover
        sx={{
          "& > *": { borderBottom: open ? "unset" : undefined },
          bgcolor: rowBg,
          cursor: "pointer",
        }}
        onClick={onToggle}
      >
        <TableCell width={48}>
          <IconButton
            size="small"
            aria-label={open ? "Collapse" : "Expand"}
            onClick={(event) => {
              event.stopPropagation();
              onToggle();
            }}
          >
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell>
          <Typography variant="subtitle1">{rack.display_name}</Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            {rack.device_name}
          </Typography>
        </TableCell>
        <TableCell>
          <Chip
            size="small"
            label={formatBadge(summary) || "empty"}
            sx={{ fontFamily: "Source Code Pro, monospace" }}
          />
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={3} sx={{ py: 0, bgcolor: "#fafafa" }}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ py: 2, px: 1 }}>
              <Stack spacing={2}>
                {Object.entries(rack.slot_groups).map(([groupName, slots]) => (
                  <Box key={groupName}>
                    <Typography variant="subtitle1" sx={{ mb: 1 }}>
                      {groupName}
                    </Typography>
                    <SlotGrid>
                      {slots.map((slot) => (
                        <SlotCard
                          key={slot.name}
                          slot={slot}
                          highlighted={highlightedPosition === slot.name}
                          slotRef={(node) => {
                            if (node) {
                              slotRefs.current[slot.name] = node;
                            } else {
                              delete slotRefs.current[slot.name];
                            }
                          }}
                          onClear={onClear}
                          onShowSample={onShowSample}
                          clearDisabled={clearDisabled}
                          clearDisabledReason={clearDisabledReason}
                        />
                      ))}
                    </SlotGrid>
                  </Box>
                ))}
              </Stack>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}

function SamplePositions() {
  const [racks, setRacks] = useState([]);
  const [liveSamples, setLiveSamples] = useState([]);
  const [unplacedSamples, setUnplacedSamples] = useState([]);
  const [inTransitSamples, setInTransitSamples] = useState([]);
  const [expanded, setExpanded] = useState({});
  const [findQuery, setFindQuery] = useState("");
  const [highlightedPosition, setHighlightedPosition] = useState(null);
  const [detailSample, setDetailSample] = useState(null);
  const [message, setMessage] = useState(null);
  const [labIdle, setLabIdle] = useState(true);
  const [idleReasons, setIdleReasons] = useState([]);
  const slotRefs = useRef({});
  const scrollTimer = useRef(null);
  const highlightTimer = useRef(null);

  const refreshIdle = () => {
    get_lab_idle()
      .then((res) => {
        if (res && res.status === "success" && res.data) {
          setLabIdle(Boolean(res.data.idle));
          setIdleReasons(res.data.reasons || []);
        }
      })
      .catch(() => {
        // Keep last known idle state if the idle endpoint fails.
      });
  };

  const refresh = () => {
    get_sample_position_racks().then((result) => {
      if (result && result.status === "success") {
        setRacks(result.racks || []);
        setLiveSamples(result.live_samples || []);
        setUnplacedSamples(result.unplaced_samples || []);
        setInTransitSamples(result.in_transit_samples || []);
      }
    });
    refreshIdle();
  };

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => () => {
    if (scrollTimer.current) {
      clearTimeout(scrollTimer.current);
    }
    if (highlightTimer.current) {
      clearTimeout(highlightTimer.current);
    }
  }, []);

  const findMatches = useMemo(() => {
    const q = findQuery.trim().toLowerCase();
    if (!q) {
      return [];
    }
    return liveSamples
      .filter((sample) => {
        const hay = [
          sample.name,
          sample.sample_id,
          sample.position,
          sample.campaign,
          sample.owner,
          sample.project,
          sample.experiment_name,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return hay.includes(q);
      })
      .slice(0, 12);
  }, [findQuery, liveSamples]);

  // Busiest devices first so occupied racks are easy to spot at the top.
  const sortedRacks = useMemo(() => {
    return [...racks].sort((a, b) => {
      const occupiedA = a.summary?.occupied || 0;
      const occupiedB = b.summary?.occupied || 0;
      if (occupiedB !== occupiedA) {
        return occupiedB - occupiedA;
      }
      const nameA = a.display_name || a.device_name || "";
      const nameB = b.display_name || b.device_name || "";
      return nameA.localeCompare(nameB);
    });
  }, [racks]);

  const jumpToPosition = (position, { keepQuery } = {}) => {
    const device_name = deviceFromPosition(position);
    if (!device_name || !position) {
      setMessage({
        severity: "info",
        text: "That position is not on a known occupancy device.",
      });
      return;
    }
    const known = racks.some((rack) => rack.device_name === device_name);
    if (!known) {
      setMessage({
        severity: "info",
        text: `${device_name} is not in the occupancy list (filtered out or not registered).`,
      });
      return;
    }
    setExpanded((prev) => ({ ...prev, [device_name]: true }));
    setHighlightedPosition(position);
    if (!keepQuery) {
      setFindQuery((prev) => prev || position);
    }
    if (scrollTimer.current) {
      clearTimeout(scrollTimer.current);
    }
    if (highlightTimer.current) {
      clearTimeout(highlightTimer.current);
    }
    scrollTimer.current = setTimeout(() => {
      const node = slotRefs.current[position];
      if (node && typeof node.scrollIntoView === "function") {
        node.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 320);
    highlightTimer.current = setTimeout(() => {
      setHighlightedPosition(null);
    }, 8000);
  };

  const jumpToSample = (sample) => {
    if (!sample?.position) {
      setMessage({
        severity: "info",
        text: "That sample has no current occupancy slot to jump to.",
      });
      return;
    }
    if (sample.name) {
      setFindQuery(sample.name);
    }
    jumpToPosition(sample.position, { keepQuery: true });
  };

  const openSampleHistory = (sample) => {
    setDetailSample(sample);
  };

  const clearDisabledReason = idleReasons.length
    ? `Lab is not idle: ${idleReasons.join("; ")}. Use Release locks & tasks first.`
    : "Lab is not idle. Use Release locks & tasks first.";

  const handleClear = async (position) => {
    if (!labIdle) {
      setMessage({
        severity: "warning",
        text: clearDisabledReason,
      });
      return;
    }
    const res = await clear_sample_position(position);
    const result = await res.json();
    if (result.status === "success") {
      setMessage({ severity: "success", text: `Cleared ${position}.` });
      refresh();
    } else {
      setMessage({ severity: "error", text: result.errors || result.reason || "Failed to clear position." });
    }
  };

  return (
    <RackContainer>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 2 }}>
        <Box>
          <Typography variant="h5">Sample Positions</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 640 }}>
            Occupancy for devices that can hold powder samples (vials, crucibles, XRD
            holders). Cap-only slots are hidden. Use <b>Clear</b> to free a slot in
            software when the lab is idle. Initial placement comes from experiment{" "}
            <b>Starting</b> tasks (notebooks / submission) — Place was removed so GUI
            and scripts do not fight over the same slots.
          </Typography>
        </Box>
        <Button variant="outlined" onClick={refresh}>Refresh</Button>
      </Box>

      {!labIdle && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Clear is disabled while the lab is busy
          {idleReasons.length ? `: ${idleReasons.join("; ")}` : "."} Finish work or use
          Lab settings → Release locks &amp; tasks first.
        </Alert>
      )}

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Find sample
        </Typography>
        <TextField
          fullWidth
          size="small"
          placeholder="Search by name, id, or position…"
          value={findQuery}
          onChange={(event) => setFindQuery(event.target.value)}
        />
        {findQuery.trim() && (
          <List dense sx={{ mt: 1, maxHeight: 280, overflow: "auto" }}>
            {findMatches.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ px: 2, py: 1 }}>
                No placed samples match.
              </Typography>
            ) : (
              findMatches.map((sample) => {
                const summary = summarizeMovement(sample);
                return (
                  <ListItemButton
                    key={sample.sample_id}
                    alignItems="flex-start"
                    onClick={() => openSampleHistory(sample)}
                  >
                    <ListItemText
                      primary={sample.name}
                      secondary={
                        <>
                          <Typography variant="caption" display="block">
                            Now: {summary.nowLabel}
                          </Typography>
                          <Typography variant="caption" display="block" color="text.secondary">
                            Before: {summary.beforeLabel || "—"}
                          </Typography>
                          {ownershipCaption(sample) && (
                            <Typography variant="caption" display="block" color="text.secondary">
                              {ownershipCaption(sample)}
                            </Typography>
                          )}
                        </>
                      }
                    />
                    <Stack direction="row" spacing={0.5} sx={{ mt: 0.5 }} onClick={(e) => e.stopPropagation()}>
                      <Button size="small" onClick={() => openSampleHistory(sample)}>
                        History
                      </Button>
                      <Button
                        size="small"
                        disabled={!sample.position}
                        onClick={() => jumpToSample(sample)}
                      >
                        Jump
                      </Button>
                    </Stack>
                  </ListItemButton>
                );
              })
            )}
          </List>
        )}
      </Paper>

      {inTransitSamples.length > 0 && (
        <Alert severity="warning">
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {inTransitSamples.length} sample(s) in transit
          </Typography>
          <Stack spacing={0.5}>
            {inTransitSamples.map((sample) => (
              <Stack
                key={sample.sample_id}
                direction="row"
                spacing={1}
                alignItems="center"
                flexWrap="wrap"
              >
                <Typography variant="body2">
                  <b>{sample.name}</b>: {sample.source || "?"} → {sample.destination || "?"}
                  {sample.last_position ? ` (last known: ${sample.last_position})` : ""}
                </Typography>
                {(sample.position || sample.source) && (
                  <Button
                    size="small"
                    onClick={() => jumpToSample({
                      ...sample,
                      device_name: sample.device_name
                        || (sample.position || sample.source || "").split("/")[0],
                      position: sample.position || sample.source,
                    })}
                  >
                    Jump
                  </Button>
                )}
              </Stack>
            ))}
          </Stack>
        </Alert>
      )}

      {unplacedSamples.length > 0 && (
        <Accordion disableGutters>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography>
              {unplacedSamples.length} sample(s) with no current position
              {" "}(last_position may still show prior rack)
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Stack spacing={1}>
              {unplacedSamples.map((sample) => (
                <Box key={sample.sample_id}>
                  <Typography variant="body2">
                    <b>{sample.name}</b>
                    {sample.last_position ? ` · last known: ${sample.last_position}` : ""}
                  </Typography>
                  <Button size="small" onClick={() => openSampleHistory(sample)}>
                    History
                  </Button>
                </Box>
              ))}
            </Stack>
          </AccordionDetails>
        </Accordion>
      )}

      {racks.length === 0 ? (
        <Alert severity="info">
          No occupancy hosts registered yet. Run lab setup so racks / mobile / Labman positions appear here.
        </Alert>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell width={48} />
                <TableCell>Device</TableCell>
                <TableCell>Occupancy</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedRacks.map((rack) => (
                <DeviceOccupancyRow
                  key={rack.device_name}
                  rack={rack}
                  open={Boolean(expanded[rack.device_name])}
                  onToggle={() => setExpanded((prev) => ({
                    ...prev,
                    [rack.device_name]: !prev[rack.device_name],
                  }))}
                  highlightedPosition={highlightedPosition}
                  slotRefs={slotRefs}
                  onClear={handleClear}
                  onShowSample={openSampleHistory}
                  clearDisabled={!labIdle}
                  clearDisabledReason={clearDisabledReason}
                />
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <SampleDetailDialog
        open={detailSample !== null}
        onClose={() => setDetailSample(null)}
        sample={detailSample}
        onJumpToPosition={(position) => jumpToPosition(position)}
      />

      <Snackbar
        open={message !== null}
        autoHideDuration={4000}
        onClose={() => setMessage(null)}
      >
        {message ? <Alert severity={message.severity}>{message.text}</Alert> : null}
      </Snackbar>
    </RackContainer>
  );
}

export default SamplePositions;
