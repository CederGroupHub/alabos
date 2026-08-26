import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import styled from 'styled-components';
import {
  claim_device_control,
  execute_device_control_command,
  get_device_control_catalog,
  release_device_control,
} from '../../api_routes';

const StyledDeviceControlDiv = styled.div`
  margin: 12px 16px;
`;

const PAGE_ACCENTS = {
  border: '#d8e0e6',
  shell: '#f6f8fa',
  title: '#21323f',
  text: '#2b3d49',
  muted: '#5f7483',
  badgeIdleBg: '#e6edf1',
  badgeIdleText: '#355062',
  badgeBusyBg: '#eef2f5',
  badgeBusyText: '#5d6f7b',
  successBg: '#edf6f2',
  successText: '#2d6150',
  warningBg: '#f7efe6',
  warningText: '#7a5f3f',
};

const HIDDEN_COMMANDS_BY_DEVICE = {
  DASH_capper: new Set(['open_top_gripper', 'close_top_gripper']),
};

function visibleCommands(deviceName, commands) {
  const hidden = HIDDEN_COMMANDS_BY_DEVICE[deviceName] || new Set();
  return (commands || []).filter((command) => !hidden.has(command.command_name));
}

function prettyJson(value) {
  if (value === undefined || value === null || value === '') {
    return 'No response yet.';
  }
  if (typeof value === 'string') {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

function DeviceControl() {
  const [catalog, setCatalog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [claimTokens, setClaimTokens] = useState({});
  const [pending, setPending] = useState({});
  const [results, setResults] = useState({});
  const [commandParams, setCommandParams] = useState({});

  const refreshCatalog = async ({ showSpinner = false } = {}) => {
    if (showSpinner) {
      setLoading(true);
    }
    try {
      const response = await get_device_control_catalog();
      if (response.status !== 'success') {
        throw new Error(response.errors || 'Failed to load device catalog.');
      }
      const devices = response.data?.devices || [];
      setCatalog(devices);
      setClaimTokens((previous) => {
        const next = { ...previous };
        devices.forEach((device) => {
          if (device.manual_task_id) {
            next[device.device_name] = device.manual_task_id;
          } else if (device.dashboard_status !== 'OCCUPIED') {
            delete next[device.device_name];
          }
        });
        return next;
      });
      setError('');
    } catch (fetchError) {
      setError(fetchError.message || 'Failed to load device catalog.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshCatalog({ showSpinner: true });
    const intervalId = window.setInterval(() => refreshCatalog(), 4000);
    return () => window.clearInterval(intervalId);
  }, []);

  const implementedDevices = useMemo(
    () => catalog.filter((device) => device.implementation_status === 'implemented'),
    [catalog],
  );

  const notImplementedDevices = useMemo(
    () => catalog.filter((device) => device.implementation_status !== 'implemented'),
    [catalog],
  );

  const setDevicePending = (deviceName, key, value) => {
    setPending((previous) => ({
      ...previous,
      [deviceName]: {
        ...(previous[deviceName] || {}),
        [key]: value,
      },
    }));
  };

  const setDeviceResult = (deviceName, payload, severity = 'success') => {
    setResults((previous) => ({
      ...previous,
      [deviceName]: {
        severity,
        payload,
      },
    }));
  };

  const handleClaim = async (deviceName) => {
    setDevicePending(deviceName, 'claim', true);
    try {
      const response = await claim_device_control(deviceName);
      if (response.status !== 'success') {
        throw new Error(response.errors || 'Failed to claim device.');
      }
      setClaimTokens((previous) => ({
        ...previous,
        [deviceName]: response.data.manual_task_id,
      }));
      setDeviceResult(deviceName, response.data, 'success');
      await refreshCatalog();
    } catch (claimError) {
      setDeviceResult(deviceName, claimError.message || 'Failed to claim device.', 'error');
    } finally {
      setDevicePending(deviceName, 'claim', false);
    }
  };

  const handleRelease = async (deviceName) => {
    setDevicePending(deviceName, 'release', true);
    try {
      const response = await release_device_control(deviceName, claimTokens[deviceName]);
      if (response.status !== 'success') {
        throw new Error(response.errors || 'Failed to release device.');
      }
      setClaimTokens((previous) => {
        const next = { ...previous };
        delete next[deviceName];
        return next;
      });
      setDeviceResult(deviceName, response.data, 'success');
      await refreshCatalog();
    } catch (releaseError) {
      setDeviceResult(deviceName, releaseError.message || 'Failed to release device.', 'error');
    } finally {
      setDevicePending(deviceName, 'release', false);
    }
  };

  const handleParamChange = (deviceName, commandName, paramName, value, type) => {
    let normalizedValue = value;
    if (type === 'bool') {
      normalizedValue = value.target.checked;
    } else {
      normalizedValue = value.target.value;
    }

    setCommandParams((previous) => ({
      ...previous,
      [deviceName]: {
        ...(previous[deviceName] || {}),
        [commandName]: {
          ...((previous[deviceName] || {})[commandName] || {}),
          [paramName]: normalizedValue,
        },
      },
    }));
  };

  const getCommandParamsForDevice = (deviceName, command) => {
    const values = commandParams[deviceName]?.[command.command_name] || {};
    const prepared = {};
    Object.entries(command.params || {}).forEach(([name, schema]) => {
      if (Object.prototype.hasOwnProperty.call(values, name)) {
        prepared[name] = values[name];
      } else if (schema.type === 'bool') {
        prepared[name] = schema.default !== undefined ? schema.default : true;
      } else if (schema.default !== undefined) {
        prepared[name] = schema.default;
      } else {
        prepared[name] = '';
      }
    });
    return prepared;
  };

  const handleCommand = async (deviceName, command) => {
    const devicePendingKey = `command:${command.command_name}`;
    setDevicePending(deviceName, devicePendingKey, true);
    try {
      const params = getCommandParamsForDevice(deviceName, command);
      const response = await execute_device_control_command(
        deviceName,
        command.command_name,
        command.mode === 'actuate' ? claimTokens[deviceName] : null,
        params,
      );
      if (response.status !== 'success') {
        throw new Error(response.errors || 'Command failed.');
      }
      setDeviceResult(deviceName, response.data, 'success');
      await refreshCatalog();
    } catch (commandError) {
      setDeviceResult(deviceName, commandError.message || 'Command failed.', 'error');
    } finally {
      setDevicePending(deviceName, devicePendingKey, false);
    }
  };

  const statusChip = (device) => {
    const isBusy = device.dashboard_status !== 'IDLE';
    return (
      <Chip
        size="small"
        label={device.dashboard_status}
        sx={{
          backgroundColor: isBusy ? PAGE_ACCENTS.badgeBusyBg : PAGE_ACCENTS.badgeIdleBg,
          color: isBusy ? PAGE_ACCENTS.badgeBusyText : PAGE_ACCENTS.badgeIdleText,
          fontWeight: 600,
        }}
      />
    );
  };

  return (
    <StyledDeviceControlDiv>
      <Stack spacing={2.5}>
        <Box>
          <Typography variant="h5">Device Control</Typography>
          <Typography variant="body2" color="text.secondary">
            Read-only health and state checks can run directly. Any actuation command must first claim the device in ALabOS, then keep that manual claim until release.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Robot arms and static racks are intentionally excluded from this page.
          </Typography>
        </Box>

        {error && <Alert severity="error">{error}</Alert>}
        {loading && <CircularProgress size={28} />}

        {implementedDevices.map((device) => {
          const deviceCommands = visibleCommands(device.device_name, device.allowlisted_commands);
          const readCommands = deviceCommands.filter((command) => command.mode === 'read');
          const actuateCommands = deviceCommands.filter((command) => command.mode === 'actuate');
          const isClaimedHere = claimTokens[device.device_name] && claimTokens[device.device_name] === device.manual_task_id;
          const isUnavailable = device.claim_state === 'Unavailable';

          return (
            <Card
              key={device.device_name}
              variant="outlined"
              sx={{ borderColor: PAGE_ACCENTS.border }}
            >
              <CardContent>
                <Stack spacing={2}>
                  <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={1.5}>
                    <Box>
                      <Typography variant="h6" sx={{ color: PAGE_ACCENTS.title }}>
                        {device.label}
                      </Typography>
                      <Typography variant="body2" sx={{ color: PAGE_ACCENTS.muted }}>
                        {device.device_name}
                      </Typography>
                      <Typography variant="body2" sx={{ color: PAGE_ACCENTS.text, mt: 0.5 }}>
                        {device.description}
                      </Typography>
                    </Box>
                    <Stack direction="row" spacing={1} alignItems="flex-start" flexWrap="wrap">
                      {statusChip(device)}
                      <Chip
                        size="small"
                        label={device.claim_state}
                        sx={{
                          backgroundColor: device.manual_claimed ? PAGE_ACCENTS.successBg : PAGE_ACCENTS.shell,
                          color: device.manual_claimed ? PAGE_ACCENTS.successText : PAGE_ACCENTS.badgeBusyText,
                          fontWeight: 600,
                        }}
                      />
                    </Stack>
                  </Stack>

                  <Stack
                    direction={{ xs: 'column', lg: 'row' }}
                    spacing={2}
                    alignItems={{ xs: 'stretch', lg: 'flex-start' }}
                  >
                    <Stack spacing={1.5} sx={{ flexShrink: 0 }}>
                      <Typography variant="body2" sx={{ color: PAGE_ACCENTS.text }}>
                        <strong>Dashboard message:</strong> {device.message || 'No active message.'}
                      </Typography>

                      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                        <Button
                          variant="contained"
                          disabled={Boolean(device.manual_claimed) || isUnavailable || pending[device.device_name]?.claim}
                          onClick={() => handleClaim(device.device_name)}
                        >
                          {pending[device.device_name]?.claim ? 'Claiming…' : 'Claim Device'}
                        </Button>
                        <Button
                          variant="outlined"
                          disabled={!isClaimedHere || pending[device.device_name]?.release}
                          onClick={() => handleRelease(device.device_name)}
                        >
                          {pending[device.device_name]?.release ? 'Releasing…' : 'Release Device'}
                        </Button>
                      </Stack>
                    </Stack>

                    <Alert
                      severity={results[device.device_name]?.severity || 'info'}
                      sx={{ flex: 1, minWidth: 0, width: '100%' }}
                    >
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                        {prettyJson(results[device.device_name]?.payload)}
                      </pre>
                    </Alert>
                  </Stack>

                  <Divider />

                  <Stack spacing={2}>
                    <CommandSection
                      title="Read-only"
                      commands={readCommands}
                      device={device}
                      pending={pending}
                      onCommand={handleCommand}
                      getCommandParamsForDevice={getCommandParamsForDevice}
                      onParamChange={handleParamChange}
                      claimTokens={claimTokens}
                      disableActuation={false}
                    />

                    <CommandSection
                      title="Actuation"
                      commands={actuateCommands}
                      device={device}
                      pending={pending}
                      onCommand={handleCommand}
                      getCommandParamsForDevice={getCommandParamsForDevice}
                      onParamChange={handleParamChange}
                      claimTokens={claimTokens}
                      disableActuation={!isClaimedHere}
                    />
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          );
        })}

        <Card variant="outlined" sx={{ borderColor: PAGE_ACCENTS.border }}>
          <CardContent>
            <Stack spacing={1.5}>
              <Typography variant="h6" sx={{ color: PAGE_ACCENTS.title }}>
                Not Yet Implemented
              </Typography>
              {notImplementedDevices.map((device) => (
                <Card
                  key={device.device_name}
                  variant="outlined"
                  sx={{ borderColor: PAGE_ACCENTS.border, background: PAGE_ACCENTS.shell }}
                >
                  <CardContent>
                    <Stack spacing={0.75}>
                      <Typography variant="subtitle1" sx={{ color: PAGE_ACCENTS.title }}>
                        {device.label}
                      </Typography>
                      <Typography variant="body2" sx={{ color: PAGE_ACCENTS.muted }}>
                        {device.device_name}
                      </Typography>
                      <Typography variant="body2" sx={{ color: PAGE_ACCENTS.text }}>
                        {device.description}
                      </Typography>
                      <Chip
                        size="small"
                        label="Not yet implemented"
                        sx={{
                          width: 'fit-content',
                          backgroundColor: PAGE_ACCENTS.warningBg,
                          color: PAGE_ACCENTS.warningText,
                          fontWeight: 600,
                        }}
                      />
                      <Typography variant="body2" sx={{ color: PAGE_ACCENTS.warningText }}>
                        {device.not_implemented_reason}
                      </Typography>
                    </Stack>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          </CardContent>
        </Card>
      </Stack>
    </StyledDeviceControlDiv>
  );
}

function CommandSection({
  title,
  commands,
  device,
  pending,
  onCommand,
  getCommandParamsForDevice,
  onParamChange,
  disableActuation,
}) {
  const simpleCommands = commands.filter((command) => !Object.keys(command.params || {}).length);
  const paramCommands = commands.filter((command) => Object.keys(command.params || {}).length);

  const renderCommands = (commandList) => commandList.map((command) => (
    <CommandControl
      key={command.command_name}
      command={command}
      device={device}
      pending={pending}
      onCommand={onCommand}
      getCommandParamsForDevice={getCommandParamsForDevice}
      onParamChange={onParamChange}
      disableActuation={disableActuation}
    />
  ));

  return (
    <Stack spacing={1.5}>
      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
        {title}
      </Typography>
      {commands.length === 0 && (
        <Typography variant="body2" color="text.secondary">
          No commands configured.
        </Typography>
      )}
      {simpleCommands.length > 0 && (
        <Stack direction="row" flexWrap="wrap" sx={{ alignItems: 'center', gap: 1 }}>
          {renderCommands(simpleCommands)}
        </Stack>
      )}
      {paramCommands.length > 0 && (
        <Stack
          direction="row"
          flexWrap="wrap"
          sx={{ alignItems: 'center', gap: 1 }}
        >
          {renderCommands(paramCommands)}
        </Stack>
      )}
    </Stack>
  );
}

function CommandControl({
  command,
  device,
  pending,
  onCommand,
  getCommandParamsForDevice,
  onParamChange,
  disableActuation,
}) {
  const values = getCommandParamsForDevice(device.device_name, command);
  const isPending = pending[device.device_name]?.[`command:${command.command_name}`];
  const paramEntries = Object.entries(command.params || {});
  const hasParams = paramEntries.length > 0;

  const runButton = (
    <Button
      variant={command.mode === 'read' ? 'outlined' : 'contained'}
      disabled={Boolean(disableActuation) || isPending}
      onClick={() => onCommand(device.device_name, command)}
    >
      {isPending ? 'Running…' : command.label}
    </Button>
  );

  if (!hasParams) {
    return runButton;
  }

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 1,
        border: `1px solid ${PAGE_ACCENTS.border}`,
        borderRadius: 1,
        px: 1.25,
        py: 1,
      }}
    >
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        {command.label}
      </Typography>
      {paramEntries.map(([name, schema]) => (
        schema.type === 'bool' ? (
          <Stack key={name} direction="row" alignItems="center">
            <Switch
              checked={Boolean(values[name])}
              onChange={(event) => onParamChange(device.device_name, command.command_name, name, event, schema.type)}
            />
            <Typography variant="body2">
              {name === 'close_gripper'
                ? 'Close gripper before shaking'
                : name === 'frequency'
                  ? 'Frequency (Hz)'
                  : name === 'duration_seconds'
                    ? 'Duration (seconds)'
                    : name}
            </Typography>
          </Stack>
        ) : (
          <TextField
            key={name}
            size="small"
            label={
              name === 'duration_seconds'
                ? 'Duration (seconds)'
                : name === 'frequency'
                  ? 'Frequency (Hz)'
                  : name
            }
            type="number"
            value={values[name]}
            onChange={(event) => onParamChange(device.device_name, command.command_name, name, event, schema.type)}
            inputProps={schema.type === 'int' ? { step: 1 } : { step: 'any' }}
            sx={{ width: name === 'duration_seconds' || name === 'frequency' ? 160 : 120 }}
          />
        )
      ))}
      {runButton}
    </Box>
  );
}

export default DeviceControl;
