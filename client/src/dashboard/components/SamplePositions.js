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
import { clear_sample_position, get_lab_idle, get_sample_position_racks, block_sample_position, unblock_sample_position, unblock_all_sample_positions } from '../../api_routes';

const RackContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin: 12px 16px;
`;

const SlotGrid = styled.div`
  display: grid;
  grid-template-columns: ${(props) =>
    props.$columns
      ? `repeat(${props.$columns}, minmax(0, 1fr))`
      : "repeat(auto-fill, minmax(140px, 1fr))"};
  gap: 8px;
  ${(props) =>
    props.$columns
      ? `max-width: ${props.$columns * 156}px;`
      : ""}
`;

const HighlightedSlot = styled.div`
  border-radius: 6px;
  outline: ${(props) => (props.$active ? '2px solid #1976d2' : 'none')};
  outline-offset: 1px;
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
  if (slot.blocked) {
    return "#fce4ec";
  }
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
  if (summary.blocked_count) {
    parts.push(`${summary.blocked_count} blocked`);
  }
  return parts.join(" · ");
}

/** Humanize slot-group keys like ``crucible_slot`` → ``Crucible Slot``. */
function formatSlotGroupTitle(groupName) {
  if (!groupName || typeof groupName !== "string") {
    return groupName;
  }
  return groupName
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

/** Fixed column count for racks whose physical layout is fixed. */
function slotGridColumns(deviceName, groupName) {
  if (deviceName === "BFT_input_rack") {
    return 3;
  }
  if (deviceName === "DASH_input_rack") {
    return 4;
  }
  if (
    deviceName === "DASH_consumable_rack_A"
    && (groupName === "crucible_slot" || groupName === "vial_slot")
  ) {
    return 5;
  }
  return null;
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

function SlotCard({
  slot,
  highlighted,
  onClear,
  onBlock,
  onUnblock,
  onShowSample,
  slotRef,
  clearDisabled,
  clearDisabledReason,
}) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const occupied = slot.status === "OCCUPIED";
  const inTransit = Boolean(slot.sample?.in_transit);
  const clearBlocked = !occupied || clearDisabled;
  const canToggleBlock = slot.can_toggle_block !== false && !slot.locked_by_task_id;
  const sample = slot.sample;
  const ownership = ownershipCaption(sample);
  const statusLabel = inTransit
    ? "TRANSIT"
    : slot.blocked
      ? "BLOCKED"
      : slot.status;
  const statusColor = inTransit
    ? "info"
    : slot.blocked
      ? "error"
      : slot.status === "OCCUPIED"
        ? "success"
        : slot.status === "LOCKED"
          ? "warning"
          : "default";

  return (
    <HighlightedSlot $active={highlighted} ref={slotRef}>
      <Card
        variant="outlined"
        title={slot.name}
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
            gap: 0.6,
            p: 1,
            "&:last-child": { pb: 1 },
            minWidth: 0,
          }}
        >
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            spacing={0.5}
            sx={{ minWidth: 0 }}
          >
            <Typography variant="body2" sx={{ fontWeight: 700, lineHeight: 1.25 }}>
              {slot.slot_number}
            </Typography>
            <Chip
              label={statusLabel}
              size="small"
              color={statusColor}
              sx={{
                height: 20,
                fontSize: "0.7rem",
                "& .MuiChip-label": { px: 0.7 },
              }}
            />
          </Stack>

          {sample ? (
            <Box sx={{ minWidth: 0 }}>
              <TruncatedLine
                variant="caption"
                sx={{ fontWeight: 700, lineHeight: 1.2, display: "block" }}
              >
                {sample.name}
              </TruncatedLine>
              <Button
                size="small"
                onClick={() => setDetailsOpen((prev) => !prev)}
                endIcon={detailsOpen ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                sx={{
                  px: 0,
                  minHeight: 0,
                  py: 0,
                  mt: 0.15,
                  fontSize: "0.7rem",
                  textTransform: "none",
                }}
              >
                {detailsOpen ? "Hide" : "Details"}
              </Button>
              <Collapse in={detailsOpen} timeout="auto" unmountOnExit>
                <Box
                  sx={{
                    mt: 0.5,
                    pt: 0.5,
                    borderTop: "1px solid",
                    borderColor: "divider",
                    minWidth: 0,
                  }}
                >
                  <Stack spacing={0.5}>
                    <WrappingText variant="caption" color="text.secondary" display="block">
                      {sample.sample_id}
                    </WrappingText>
                    <WrappingText variant="caption" color="text.secondary" display="block">
                      {slot.name}
                    </WrappingText>
                    {ownership && (
                      <WrappingText variant="caption" color="text.secondary" display="block">
                        {ownership}
                      </WrappingText>
                    )}
                    {sample.tags?.length > 0 && (
                      <WrappingText variant="caption" color="text.secondary" display="block">
                        {sample.tags.join(" · ")}
                      </WrappingText>
                    )}
                    <Button
                      size="small"
                      onClick={() => onShowSample(sample)}
                      sx={{
                        px: 0,
                        alignSelf: "flex-start",
                        textTransform: "none",
                        minHeight: 0,
                        py: 0,
                        fontSize: "0.7rem",
                      }}
                    >
                      History
                    </Button>
                  </Stack>
                </Box>
              </Collapse>
            </Box>
          ) : (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ lineHeight: 1.2, minHeight: "1.2em" }}
            >
              {slot.blocked ? (slot.blocked_reason || "Blocked") : "Empty"}
            </Typography>
          )}

          {slot.locked_by_task_id && !occupied && (
            <TruncatedLine variant="caption" color="text.secondary">
              Locked
            </TruncatedLine>
          )}

          <Stack direction="row" spacing={0.5} sx={{ mt: "auto", pt: 0.25 }}>
            {slot.blocked ? (
              <Button
                size="small"
                variant="outlined"
                color="error"
                onClick={() => onUnblock(slot.name)}
                disabled={!canToggleBlock}
                title={
                  !canToggleBlock
                    ? "Position is locked by a task; release the lock before changing block state."
                    : undefined
                }
                sx={{
                  flex: 1,
                  minWidth: 0,
                  px: 0.4,
                  py: 0.25,
                  fontSize: "0.7rem",
                  lineHeight: 1.25,
                }}
              >
                Unblock
              </Button>
            ) : (
              <Button
                size="small"
                variant="outlined"
                color="warning"
                onClick={() => onBlock(slot.name)}
                disabled={!canToggleBlock}
                title={
                  !canToggleBlock
                    ? "Position is locked by a task; release the lock before changing block state."
                    : undefined
                }
                sx={{
                  flex: 1,
                  minWidth: 0,
                  px: 0.4,
                  py: 0.25,
                  fontSize: "0.7rem",
                  lineHeight: 1.25,
                }}
              >
                Block
              </Button>
            )}
            <Button
              size="small"
              variant="outlined"
              onClick={() => onClear(slot.name)}
              disabled={clearBlocked}
              title={
                occupied && clearDisabled
                  ? clearDisabledReason || "Lab is not idle"
                  : undefined
              }
              sx={{
                flex: 1,
                minWidth: 0,
                px: 0.4,
                py: 0.25,
                fontSize: "0.7rem",
                lineHeight: 1.25,
              }}
            >
              Clear
            </Button>
          </Stack>
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
  onBlock,
  onUnblock,
  onShowSample,
  clearDisabled,
  clearDisabledReason,
}) {
  const summary = rack.summary || {};
  const occupiedCount = summary.occupied || 0;
  const hasOccupied = occupiedCount > 0;
  let rowBg;
  if (rack.all_blocked) {
    rowBg = open ? "#f8bbd0" : "#fce4ec";
  } else if (hasOccupied) {
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
                {rack.all_blocked && (
                  <Alert severity="error">
                    All positions on this device are blocked — automation cannot use it.
                  </Alert>
                )}
                {Object.entries(rack.slot_groups).map(([groupName, slots]) => (
                  <Box key={groupName}>
                    <Typography variant="subtitle1" sx={{ mb: 1 }}>
                      {formatSlotGroupTitle(groupName)}
                    </Typography>
                    <SlotGrid $columns={slotGridColumns(rack.device_name, groupName)}>
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
                          onBlock={onBlock}
                          onUnblock={onUnblock}
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

  const handleBlock = async (position) => {
    const res = await block_sample_position(position, {
      reason: "Blocked by the user through the UI",
    });
    const result = await res.json();
    if (result.status === "success") {
      setMessage({ severity: "success", text: `Blocked ${position}.` });
      refresh();
    } else {
      setMessage({
        severity: "error",
        text: result.errors || result.reason || "Failed to block position.",
      });
    }
  };

  const handleUnblock = async (position) => {
    const res = await unblock_sample_position(position);
    const result = await res.json();
    if (result.status === "success") {
      setMessage({ severity: "success", text: `Unblocked ${position}.` });
      refresh();
    } else {
      setMessage({
        severity: "error",
        text: result.errors || result.reason || "Failed to unblock position.",
      });
    }
  };

  const handleUnblockAll = async () => {
    const confirmed = window.confirm(
      "Unblock all sample positions? This clears operator blocks only — occupancy and task locks are unchanged."
    );
    if (!confirmed) {
      return;
    }
    const res = await unblock_all_sample_positions();
    const result = await res.json();
    if (result.status === "success") {
      const count = result.unblocked_count ?? 0;
      setMessage({
        severity: "success",
        text: `Unblocked ${count} position(s).`,
      });
      refresh();
    } else {
      setMessage({
        severity: "error",
        text: result.errors || result.reason || "Failed to unblock all positions.",
      });
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
            software when the lab is idle. Use <b>Block</b> to keep automation from
            assigning a slot (even when empty). Initial placement comes from experiment{" "}
            <b>Starting</b> tasks (notebooks / submission) — Place was removed so GUI
            and scripts do not fight over the same slots.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} flexShrink={0}>
          <Button variant="outlined" color="warning" onClick={handleUnblockAll}>
            Unblock all positions
          </Button>
          <Button variant="outlined" onClick={refresh}>Refresh</Button>
        </Stack>
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
                  onBlock={handleBlock}
                  onUnblock={handleUnblock}
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
