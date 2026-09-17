import React, { useEffect, useState } from 'react';
import { Box, Tab, Tabs, Typography } from '@mui/material';
import { get_launch_log_sources, get_launch_log_tail } from '../../api_routes';

const DEFAULT_LOG_HEIGHT = 420;

function LogPane({ sourceId }) {
  const [lines, setLines] = useState([]);
  const [available, setAvailable] = useState(false);
  const [reason, setReason] = useState(null);
  const preRef = React.useRef(null);
  const stickToBottom = React.useRef(true);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      get_launch_log_tail(sourceId, 400).then((data) => {
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
  }, [sourceId]);

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

  let emptyMessage = 'Waiting for the first log line…';
  if (!available && reason === 'no_launch_dir') {
    emptyMessage = 'Launch log directory is not configured. Start AlabOS from the A-Lab OS launcher.';
  } else if (!available && reason === 'no_file') {
    emptyMessage = 'No log file yet for this service (it may not be launched this session).';
  }

  const text = lines.length > 0 ? lines.join('\n') : emptyMessage;

  return (
    <Box sx={{ mt: 1.5 }}>
      <pre
        ref={preRef}
        onScroll={onScroll}
        style={{
          margin: 0,
          height: DEFAULT_LOG_HEIGHT,
          overflow: 'auto',
          padding: '12px 14px',
          borderRadius: 12,
          background: '#0f1c24',
          color: lines.length > 0 ? '#d7e6ef' : '#8aa0ad',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
          fontSize: 12,
          lineHeight: 1.45,
          border: '1px solid rgba(34, 62, 81, 0.2)',
        }}
      >
        {text}
      </pre>
    </Box>
  );
}

export default function Logs() {
  const [sources, setSources] = useState([]);
  const [tab, setTab] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      get_launch_log_sources().then((data) => {
        if (cancelled || !data) {
          return;
        }
        setSources(data.sources || []);
      });
    };
    load();
    const interval = setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const active = sources[tab] || sources[0];

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, color: '#203d51', mb: 0.5 }}>
        Logs
      </Typography>
      <Typography variant="body2" sx={{ color: '#5f7483', mb: 2 }}>
        Live tails of this launch&apos;s Lab overview and service stdout (same files the launcher writes under launches/).
      </Typography>
      <Tabs
        value={Math.min(tab, Math.max(sources.length - 1, 0))}
        onChange={(_event, next) => setTab(next)}
        variant="scrollable"
        scrollButtons="auto"
      >
        {(sources.length ? sources : [
          { id: 'lab', title: 'Lab' },
          { id: 'alabos_launch', title: 'alabos launch' },
          { id: 'alabos_worker', title: 'alabos worker' },
          { id: 'alab_one_dashboard', title: 'alab_one dashboard' },
        ]).map((source) => (
          <Tab key={source.id} label={source.title} />
        ))}
      </Tabs>
      {active ? <LogPane sourceId={active.id} /> : null}
    </Box>
  );
}
