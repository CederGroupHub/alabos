import React from 'react';
import Paper from '@mui/material/Paper';
import styled from 'styled-components';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import Collapse from '@mui/material/Collapse';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import IconButton from '@mui/material/IconButton';
import { useEffect } from 'react';
import { get_device_verbose_log, get_status } from '../../api_routes';
import { FormControl, FormControlLabel, Switch } from '@mui/material';
import { request_device_pause, release_device_pause } from '../../api_routes';
import Button from '@mui/material/Button';

const StyledDevicesDiv = styled.div`
  margin: 12px 16px;

  .status {
    font-family: Source Code Pro;
    color: black;
  }

  .status-occupied {
    color: green;
  }

  .status-idle {
    color: red;
  }
  
  .task-id {
    font-family: Source Code Pro;
  }

  h3 {
    padding: 4px 8px;
  }

  .attribute-name {
    font-family: Source Code Pro;
    font-weight: 600;
    white-space: nowrap;
    vertical-align: top;
  }

  .attribute-value {
    font-family: Source Code Pro;
    white-space: pre-wrap;
    margin: 0;
    max-height: 260px;
    overflow: auto;
  }

  .in-transit {
    color: #1565c0;
    font-family: Source Code Pro;
  }

  .status-chip {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-family: Source Code Pro;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    white-space: nowrap;
  }

  .connection-notice {
    border-left: 3px solid;
    padding: 4px 0 4px 10px;
    margin-bottom: 4px;
  }

  .connection-notice.connecting {
    border-color: #b26a00;
    color: #7a4a00;
  }

  .connection-notice.failed {
    border-color: #8c435b;
    color: #7a3b50;
  }

  .connection-headline {
    font-weight: 600;
  }

  .device-detail-split {
    display: flex;
    gap: 16px;
    align-items: stretch;
    min-height: 240px;
    margin: 8px 0 16px 0;
  }

  .device-detail-state {
    flex: 0 0 36%;
    min-width: 220px;
    overflow: auto;
  }

  .device-detail-log {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }

  .device-live-log-wrap {
    display: flex;
    flex-direction: column;
    min-width: 0;
    border-radius: 4px;
    overflow: hidden;
    background: #1e2a30;
  }

  .device-live-log {
    font-family: Source Code Pro, monospace;
    font-size: 0.75rem;
    line-height: 1.4;
    background: #1e2a30;
    color: #ffffff;
    height: 220px;
    overflow: auto;
    padding: 8px 10px;
    margin: 0;
    border-radius: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .device-live-log.empty {
    color: #ffffff;
  }

  .device-live-log-resizer {
    flex-shrink: 0;
    height: 10px;
    cursor: ns-resize;
    background: #1e2a30;
    border-top: 1px solid #2c3b42;
  }

  .device-live-log-resizer::after {
    content: "";
    display: block;
    width: 36px;
    height: 3px;
    margin: 3px auto 0;
    border-radius: 2px;
    background: #6b818c;
  }
`;

const DEVICE_ACCENTS = {
  occupiedBg: '#e6f0ef',
  occupiedText: '#2b5b57',
  errorBg: '#f4e8ec',
  errorText: '#8c435b',
  pauseRequestedBg: '#f3ece3',
  pauseRequestedText: '#7a6146',
  pausedBg: '#dce6ec',
  pausedText: '#27485c',
  disabledBg: '#ececec',
  disabledText: '#616161',
  connectingBg: '#fbf0dd',
  connectingText: '#8a5300',
  badgeBg: '#45697c',
  badgeText: '#ffffff',
};

const STATUS_LABELS = {
  CONNECTING: 'NOT CONNECTED',
};


// A device that has not finished connecting is the one state an operator can usually fix from the
// dashboard, so it gets a full explanation rather than a colour: what it is waiting on, where to
// go and answer it, and the fact that answering is enough (no relaunch).
function ConnectionNotice({ attributes }) {
  const status = attributes?.connection_status;
  if (status !== 'connecting' && status !== 'failed') {
    return null;
  }
  const waited = attributes?.connection_waiting_seconds;
  const prompt = attributes?.connection_user_input_prompt;

  if (status === 'failed') {
    return (
      <div className="connection-notice failed">
        <Typography variant="body2" className="connection-headline">
          Not connected — connection failed
        </Typography>
        <Typography variant="caption" display="block">
          {attributes?.connection_error || 'alabos could not connect to this device at launch.'}
          {' '}This device is disabled until the connection is restored and the lab is relaunched.
        </Typography>
      </div>
    );
  }

  return (
    <div className="connection-notice connecting">
      <Typography variant="body2" className="connection-headline">
        Not connected — still connecting{waited ? ` (${waited}s)` : ''}
      </Typography>
      {prompt ? (
        <Typography variant="caption" display="block">
          This device is waiting for you. Open <b>User Input Requests</b> and answer:{' '}
          <b>“{prompt}”</b>. It will join the lab automatically once you respond — you do not need
          to restart the lab.
        </Typography>
      ) : (
        <Typography variant="caption" display="block">
          The rest of the lab launched without it, and it will join automatically once the
          connection completes — you do not need to restart the lab. If it stays like this, check{' '}
          <b>User Input Requests</b> and that the hardware is powered on and reachable.
        </Typography>
      )}
    </div>
  );
}


// Attribute values come straight from the device's database document, so they can be anything from a
// number to a nested mission plan. Primitives read best inline; anything structured is pretty-printed
// so it stays truthful rather than being flattened into something ambiguous.
function AttributeValue({ value }) {
  if (value === null || value === undefined) {
    return <Typography variant="caption" sx={{ color: "#9e9e9e" }}>—</Typography>;
  }
  if (typeof value === "object") {
    return <pre className="attribute-value">{JSON.stringify(value, null, 2)}</pre>;
  }
  return <Typography variant="body2" className="attribute-value">{String(value)}</Typography>;
}


const DEFAULT_LOG_HEIGHT = 220;

function DeviceLogPane({ deviceName, open }) {
  const [lines, setLines] = React.useState([]);
  const [available, setAvailable] = React.useState(false);
  const [reason, setReason] = React.useState(null);
  const [height, setHeight] = React.useState(DEFAULT_LOG_HEIGHT);
  const preRef = React.useRef(null);
  const stickToBottom = React.useRef(true);

  useEffect(() => {
    if (!open) {
      setHeight(DEFAULT_LOG_HEIGHT);
      return undefined;
    }
    let cancelled = false;
    const load = () => {
      get_device_verbose_log(deviceName, 200).then((data) => {
        if (cancelled || !data) {
          return;
        }
        setAvailable(Boolean(data.available));
        setReason(data.reason || null);
        setLines(data.lines || []);
      });
    };
    load();
    const interval = setInterval(load, 1000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [open, deviceName]);

  useEffect(() => {
    const el = preRef.current;
    if (el && stickToBottom.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [lines]);

  const onScroll = (event) => {
    const el = event.target;
    stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 24;
  };

  const onResizeStart = (event) => {
    event.preventDefault();
    const startY = event.clientY;
    const startHeight = height;
    const onMove = (moveEvent) => {
      const next = startHeight + (moveEvent.clientY - startY);
      setHeight(Math.max(DEFAULT_LOG_HEIGHT, next));
    };
    const onUp = () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  let emptyMessage = 'Waiting for the first log line…';
  if (!available && reason === 'no_file') {
    emptyMessage = 'No log file yet. It appears once this device is next called.';
  }

  const text = lines.length > 0 ? lines.join('\n') : emptyMessage;

  return (
    <div className="device-detail-log">
      <Typography variant="subtitle2" gutterBottom>Live log</Typography>
      <div className="device-live-log-wrap">
        <pre
          ref={preRef}
          className={lines.length > 0 ? 'device-live-log' : 'device-live-log empty'}
          style={{ height }}
          onScroll={onScroll}
        >
          {text}
        </pre>
        <div
          className="device-live-log-resizer"
          role="separator"
          aria-orientation="horizontal"
          aria-label="Drag to make the live log taller"
          onMouseDown={onResizeStart}
        />
      </div>
    </div>
  );
}


function DeviceAttributes({ attributes }) {
  const entries = Object.entries(attributes || {});
  if (entries.length === 0) {
    return (
      <Typography variant="caption" sx={{ color: "#9e9e9e" }}>
        This device does not publish any attributes. Add names to its `dashboard_attributes` to show them here.
      </Typography>
    );
  }
  return (
    <Table size="small" aria-label="device attributes">
      <TableBody>
        {entries.map(([name, value]) => (
          <TableRow key={name} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
            <TableCell className="attribute-name" width="220">{name}</TableCell>
            <TableCell><AttributeValue value={value} /></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}


function Row({ device, hoverForId }) {
  const [open, setOpen] = React.useState(false);
  const attributeCount = Object.keys(device.attributes || {}).length;

  const rowColor = () => {
    switch (device.status) {
      case "OCCUPIED":
        return DEVICE_ACCENTS.occupiedBg;
      case "ERROR":
        return DEVICE_ACCENTS.errorBg;
      case "PAUSE_REQUESTED":
        return DEVICE_ACCENTS.pauseRequestedBg;
      case "PAUSED":
        return DEVICE_ACCENTS.pausedBg;
      case "DISABLED":
        return DEVICE_ACCENTS.disabledBg;
      case "CONNECTING":
        return DEVICE_ACCENTS.connectingBg;
      default:
        return "#ffffff";
    }
  }

  const textColor = (task_status) => {
    switch (task_status) {
      case "OCCUPIED":
        return DEVICE_ACCENTS.occupiedText;
      case "ERROR":
        return DEVICE_ACCENTS.errorText;
      case "PAUSE_REQUESTED":
        return DEVICE_ACCENTS.pauseRequestedText;
      case "PAUSED":
        return DEVICE_ACCENTS.pausedText;
      case "DISABLED":
        return DEVICE_ACCENTS.disabledText;
      case "CONNECTING":
        return DEVICE_ACCENTS.connectingText;
      default:
        return "#000000";
    }
  }

  const subtextColor = (task_status) => {
    switch (task_status) {
      case "OCCUPIED":
        return DEVICE_ACCENTS.occupiedText;
      case "ERROR":
        return DEVICE_ACCENTS.errorText;
      case "PAUSE_REQUESTED":
        return DEVICE_ACCENTS.pauseRequestedText;
      case "PAUSED":
        return DEVICE_ACCENTS.pausedText;
      case "DISABLED":
        return DEVICE_ACCENTS.disabledText;
      case "CONNECTING":
        return DEVICE_ACCENTS.connectingText;
      default:
        return "#9e9e9e";
    }
  }

  const permanentlyDisabled = Boolean(device.attributes?.disabled);
  const connectionStatus = device.attributes?.connection_status;
  const notConnected = connectionStatus === "connecting" || connectionStatus === "failed";

  const PauseButton = ({ pause_state, device_name, permanently_disabled, connecting }) => {
    if (permanently_disabled) {
      return (
        <Typography variant="caption" sx={{ color: DEVICE_ACCENTS.disabledText }}>
          Disabled
        </Typography>
      );
    }
    // The pause on a connecting device is applied by alabos, not an operator, so offering
    // "Release" here would imply it is the way to make the device usable. It is not.
    if (connecting) {
      return (
        <Typography variant="caption" sx={{ color: DEVICE_ACCENTS.connectingText }}>
          Connecting…
        </Typography>
      );
    }
    switch (pause_state) {
      case "RELEASED":
        return (
          <Button
            variant="contained"
            color="error"
            onClick={() => { request_device_pause(device_name) }}
          >
            Pause
          </Button>
        )
      case "REQUESTED":
        return (
          <Button
            variant="contained"
            color="primary"
            onClick={() => release_device_pause(device_name)}
          >
            Cancel Pause Request
          </Button>
        )
      case "PAUSED":
        return (
          <Button
            variant="contained"
            color="primary"
            onClick={() => release_device_pause(device_name)}
          >
            Release
          </Button>
        )
    }
  }



  return (
    <React.Fragment key={device.name}>
      <TableRow
        sx={{
          '& > *': { borderBottom: attributeCount > 0 && open ? 'unset' : undefined },
          bgcolor: rowColor(device.status),
        }}
      >
        <TableCell align="center" padding="none" width="48">
          <IconButton
            aria-label="show device details"
            size="small"
            onClick={() => setOpen(!open)}
            sx={{ color: textColor(device.status) }}
          >
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell component="th" scope="row">
          <Typography
            variant="body1"
            sx={{
              color: textColor(device.status),
            }}
          >
            {device.name}
          </Typography>
          <Typography variant="caption"
            sx={{ color: subtextColor(device.status) }}
          >{device.type}</Typography>
        </TableCell>
        <TableCell align="center">
          <span
            className="status-chip"
            style={{
              backgroundColor: rowColor(device.status) === "#ffffff" ? "#eeeeee" : rowColor(device.status),
              color: textColor(device.status) === "#000000" ? "#5f5f5f" : textColor(device.status),
            }}
          >
            {STATUS_LABELS[device.status] || device.status}
          </span>
        </TableCell>
        <TableCell align="center" size="small">
          <OccupiedSamplePositions samples={device.samples} />
        </TableCell>
        <TableCell align="left" width="45%" >
          <ConnectionNotice attributes={device.attributes} />
          {!notConnected &&
            <Typography variant="caption" sx={{
              color: textColor(device.status),
              whiteSpace: "pre-wrap",
              display: '-webkit-box',
              overflow: 'auto',
              WebkitBoxOrient: 'vertical',
              WebkitLineClamp: 3,
            }}>{device.message}</Typography>
          }
        </TableCell>
        <TableCell align="center">
          <PauseButton
            pause_state={device.pause_status}
            device_name={device.name}
            permanently_disabled={permanentlyDisabled}
            connecting={connectionStatus === "connecting"}
          />
        </TableCell>
      </TableRow>
      <TableRow sx={{ bgcolor: rowColor(device.status) }}>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <div className="device-detail-split">
              <div className="device-detail-state">
                <Typography variant="subtitle2" gutterBottom>Device state</Typography>
                <DeviceAttributes attributes={device.attributes} />
              </div>
              <DeviceLogPane deviceName={device.name} open={open} />
            </div>
          </Collapse>
        </TableCell>
      </TableRow>
    </React.Fragment>
  );
}



function OccupiedSamplePositions({ samples }) {
  let total_samples = 0;
  for (const occupied of Object.values(samples || {})) {
    total_samples += occupied.length;
  }
  return <Typography variant="body1">{total_samples}</Typography>;
}

function Devices({ hoverForId }) {
  const [devices, setDevices] = React.useState([]);
  const [hideIdleDevices, setHideIdleDevices] = React.useState(false);

  useEffect(() => {
    get_status().then(data => {
      setDevices(data.devices);
    })

    const interval = setInterval(() => {
      get_status().then(data => {
        setDevices(data.devices);
      })

    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const DisplayDeviceRowFilter = (row) => {
    if (row.status != "IDLE") {
      return true
    }
    for (let samples of Object.values(row.samples)) {
      if (samples.length > 0) {
        return true
      }
    }
    return false
  }

  const FilteredDevices = (hideIdle) => {
    if (hideIdle) {
      return devices.filter(DisplayDeviceRowFilter)
    } else {
      return devices
    }
  }


  return (
    <><FormControl component="fieldset" variant="standard" sx={{ padding: "0px 16px" }}>
      <FormControlLabel
        control={
          <Switch
            checked={hideIdleDevices}
            onChange={() => setHideIdleDevices(!hideIdleDevices)}
            name="Hide idle devices with no samples"
          />
        }
        label="Hide idle devices with no samples" />
    </FormControl><TableContainer style={{ height: "100%" }} component={Paper}>
        <StyledDevicesDiv>
          <Table stickyHeader aria-label="device table">
            <TableHead>
              <TableRow>
                <TableCell padding="none" width="48" />
                <TableCell><b>Name</b></TableCell>
                <TableCell align="center"><b>Status</b></TableCell>
                <TableCell align="center"><b>Samples</b></TableCell>
                <TableCell align="center" width="45%"><b>Message</b></TableCell>
                <TableCell align="center">Pause</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {FilteredDevices(hideIdleDevices).map((device) => (
                <Row key={device.name} device={device} hoverForId={hoverForId} />
              ))}
            </TableBody>
          </Table>
        </StyledDevicesDiv>
      </TableContainer></>
  )
}

export default Devices;
