import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import styled from 'styled-components';
import {
  get_mobile_robot_catalog,
  preview_mobile_robot_segment,
  run_mobile_robot_segment,
} from '../../api_routes';

const StyledMobileRobotControlDiv = styled.div`
  margin: 12px 16px;
`;

const PAGE_ACCENTS = {
  border: '#d8e0e6',
  shell: '#f6f8fa',
  title: '#21323f',
  text: '#2b3d49',
  muted: '#5f7483',
  successBg: '#edf6f2',
  successText: '#2d6150',
  warningBg: '#f7efe6',
  warningText: '#7a5f3f',
};

const DEMO_ACCENTS = {
  border: '#c62828',
  shell: '#fdecec',
  title: '#b71c1c',
  text: '#1a1a1a',
  muted: '#5f3a3a',
  chipBg: '#f8d7da',
  chipText: '#8a1f1f',
};

const DEMO_CONFIRM_COPY = (
  'This DEMO path moves Alfred on the Labman ↔ BFT route without taking Labman '
  + 'indexing-rack control and without polling Labman.\n\n'
  + 'Before you continue, confirm that:\n'
  + '• the chosen Labman quadrant is already oriented toward the opening,\n'
  + '• Labman is not moving that quadrant / indexing rack,\n'
  + '• the physical subrack / crucibles match the slots you selected.\n\n'
  + 'If any of that is unsure, Cancel and use the normal transfer instead.'
);

function prettyJson(value) {
  if (value === undefined || value === null || value === '') {
    return 'No preview yet.';
  }
  if (typeof value === 'string') {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

function parseIntList(value) {
  return value
    .split(/[,\s]+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => Number.parseInt(item, 10))
    .filter((item) => !Number.isNaN(item));
}

function formatIntList(values) {
  return (values || []).join(' ');
}

function usesLabmanFields(segment) {
  return segment.param_kind === 'labman_to_rack' || segment.param_kind === 'rack_to_labman';
}

function slotFieldName(segment) {
  return segment.param_kind === 'labman_to_rack' ? 'crucible_slots' : 'slots';
}

function defaultFormState(segment) {
  const params = {};
  Object.entries(segment.params || {}).forEach(([name, schema]) => {
    if (schema.default !== undefined) {
      params[name] = schema.default;
    } else if (schema.type === 'int_list') {
      params[name] = [];
    } else if (schema.type === 'enum') {
      params[name] = schema.choices?.[0] || '';
    } else {
      params[name] = '';
    }
  });
  return {
    params,
    options: {
      remove_at_end: segment.options?.remove_at_end?.default ?? true,
      batch_name: segment.default_batch_name || '',
    },
    slotText: {},
    destinationSlotText: {},
  };
}

function MobileRobotControl() {
  const [segments, setSegments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [forms, setForms] = useState({});
  const [pending, setPending] = useState({});
  const [results, setResults] = useState({});
  const [demoConfirmSegment, setDemoConfirmSegment] = useState(null);

  const refreshCatalog = async ({ showSpinner = false } = {}) => {
    if (showSpinner) {
      setLoading(true);
    }
    try {
      const response = await get_mobile_robot_catalog();
      if (response.status !== 'success') {
        throw new Error(response.errors || 'Failed to load mobile robot segments.');
      }
      const nextSegments = response.data?.segments || [];
      setSegments(nextSegments);
      setForms((previous) => {
        const next = { ...previous };
        nextSegments.forEach((segment) => {
          if (!next[segment.id]) {
            const defaults = defaultFormState(segment);
            const slotField = slotFieldName(segment);
            defaults.slotText = {
              [slotField]: formatIntList(defaults.params[slotField]),
            };
            if (defaults.params.destination_slots?.length) {
              defaults.destinationSlotText = {
                destination_slots: formatIntList(defaults.params.destination_slots),
              };
            }
            next[segment.id] = defaults;
          }
        });
        return next;
      });
      setError('');
    } catch (fetchError) {
      setError(fetchError.message || 'Failed to load mobile robot segments.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshCatalog({ showSpinner: true });
  }, []);

  const setSegmentPending = (segmentId, action, value) => {
    setPending((previous) => ({
      ...previous,
      [segmentId]: {
        ...(previous[segmentId] || {}),
        [action]: value,
      },
    }));
  };

  const updateForm = (segmentId, updater) => {
    setForms((previous) => ({
      ...previous,
      [segmentId]: updater(previous[segmentId] || {}),
    }));
  };

  const buildRequestBody = (segment) => {
    const form = forms[segment.id] || defaultFormState(segment);
    const slotField = slotFieldName(segment);
    const params = {
      ...form.params,
      [slotField]: parseIntList(form.slotText?.[slotField] || ''),
    };
    const destinationText = form.destinationSlotText?.destination_slots;
    if (destinationText && destinationText.trim()) {
      params.destination_slots = parseIntList(destinationText);
    } else {
      delete params.destination_slots;
    }
    return {
      params,
      options: {
        remove_at_end: Boolean(form.options?.remove_at_end),
        batch_name: form.options?.batch_name || undefined,
      },
    };
  };

  const handlePreview = async (segment) => {
    setSegmentPending(segment.id, 'preview', true);
    setError('');
    try {
      const response = await preview_mobile_robot_segment(segment.id, buildRequestBody(segment));
      if (response.status !== 'success') {
        throw new Error(response.errors || 'Preview failed.');
      }
      setResults((previous) => ({
        ...previous,
        [segment.id]: {
          severity: 'info',
          payload: response.data,
        },
      }));
    } catch (previewError) {
      setError(previewError.message || 'Preview failed.');
    } finally {
      setSegmentPending(segment.id, 'preview', false);
    }
  };

  const handleRun = async (segment) => {
    setSegmentPending(segment.id, 'run', true);
    setError('');
    try {
      const response = await run_mobile_robot_segment(segment.id, buildRequestBody(segment));
      if (response.status !== 'success') {
        throw new Error(response.errors || 'Run failed.');
      }
      setResults((previous) => ({
        ...previous,
        [segment.id]: {
          severity: 'success',
          payload: response.data,
        },
      }));
    } catch (runError) {
      setError(runError.message || 'Run failed.');
    } finally {
      setSegmentPending(segment.id, 'run', false);
    }
  };

  const requestRun = (segment) => {
    if (segment.demo) {
      setDemoConfirmSegment(segment);
      return;
    }
    handleRun(segment);
  };

  const confirmDemoRun = () => {
    const segment = demoConfirmSegment;
    setDemoConfirmSegment(null);
    if (segment) {
      handleRun(segment);
    }
  };

  const normalSegments = useMemo(
    () => segments.filter((segment) => !segment.demo),
    [segments],
  );
  const demoSegments = useMemo(
    () => segments.filter((segment) => Boolean(segment.demo)),
    [segments],
  );

  const renderSegmentCard = (segment) => {
          const form = forms[segment.id] || defaultFormState(segment);
          const slotField = slotFieldName(segment);
          const slotLabel = segment.params?.[slotField]?.label || 'Slots';
          const destinationLabel = segment.params?.destination_slots?.label || 'Destination slots';
          const destinationHelper = segment.param_kind === 'rack_to_labman'
            ? 'Optional. Defaults to 1…n in this Labman subrack (max 4).'
            : `Optional. Defaults to the same numbers. Rack: ${segment.destination_rack || ''}`;
          const result = results[segment.id];
          const isPreviewing = pending[segment.id]?.preview;
          const isRunning = pending[segment.id]?.run;
          const accents = segment.demo ? DEMO_ACCENTS : PAGE_ACCENTS;

          return (
            <Card
              key={segment.id}
              variant="outlined"
              sx={{
                borderColor: accents.border,
                backgroundColor: segment.demo ? DEMO_ACCENTS.shell : 'inherit',
              }}
            >
              <CardContent>
                <Stack spacing={2}>
                  <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={1.5}>
                    <Box>
                      <Typography variant="h6" sx={{ color: accents.title }}>
                        {segment.label}
                      </Typography>
                      <Typography variant="body2" sx={{ color: accents.muted }}>
                        {segment.source_station} → {segment.destination_station}
                      </Typography>
                      <Typography variant="body2" sx={{ color: accents.text, mt: 0.5 }}>
                        {segment.description}
                      </Typography>
                    </Box>
                    <Chip
                      size="small"
                      label={segment.demo
                        ? `DEMO · ${segment.source_station} → ${segment.destination_station}`
                        : `${segment.source_station} → ${segment.destination_station}`}
                      sx={{
                        width: 'fit-content',
                        backgroundColor: segment.demo ? DEMO_ACCENTS.chipBg : PAGE_ACCENTS.shell,
                        color: segment.demo ? DEMO_ACCENTS.chipText : PAGE_ACCENTS.text,
                        fontWeight: 600,
                      }}
                    />
                  </Stack>

                  <Stack direction={{ xs: 'column', lg: 'row' }} spacing={2} flexWrap="wrap">
                    {usesLabmanFields(segment) && (
                      <>
                        <FormControl size="small" sx={{ minWidth: 160 }}>
                          <InputLabel id={`${segment.id}-quadrant-label`}>Quadrant</InputLabel>
                          <Select
                            labelId={`${segment.id}-quadrant-label`}
                            label="Quadrant"
                            value={form.params?.quadrant ?? 1}
                            onChange={(event) => updateForm(segment.id, (current) => ({
                              ...current,
                              params: {
                                ...current.params,
                                quadrant: Number(event.target.value),
                              },
                            }))}
                          >
                            {(segment.params?.quadrant?.choices || []).map((choice) => (
                              <MenuItem key={choice} value={choice}>{choice}</MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                        <FormControl size="small" sx={{ minWidth: 180 }}>
                          <InputLabel id={`${segment.id}-subrack-label`}>Subrack</InputLabel>
                          <Select
                            labelId={`${segment.id}-subrack-label`}
                            label="Subrack"
                            value={form.params?.subrack || 'SubRackA'}
                            onChange={(event) => updateForm(segment.id, (current) => ({
                              ...current,
                              params: {
                                ...current.params,
                                subrack: event.target.value,
                              },
                            }))}
                          >
                            {(segment.params?.subrack?.choices || []).map((choice) => (
                              <MenuItem key={choice} value={choice}>{choice}</MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </>
                    )}

                    <TextField
                      size="small"
                      label={slotLabel}
                      helperText="Space- or comma-separated slot numbers"
                      value={form.slotText?.[slotField] || ''}
                      onChange={(event) => updateForm(segment.id, (current) => ({
                        ...current,
                        slotText: {
                          ...(current.slotText || {}),
                          [slotField]: event.target.value,
                        },
                      }))}
                      sx={{ minWidth: 260 }}
                    />

                    <TextField
                      size="small"
                      label={destinationLabel}
                      helperText={destinationHelper}
                      value={form.destinationSlotText?.destination_slots || ''}
                      onChange={(event) => updateForm(segment.id, (current) => ({
                        ...current,
                        destinationSlotText: {
                          destination_slots: event.target.value,
                        },
                      }))}
                      sx={{ minWidth: 260 }}
                    />

                    <TextField
                      size="small"
                      label="Batch name"
                      value={form.options?.batch_name || ''}
                      onChange={(event) => updateForm(segment.id, (current) => ({
                        ...current,
                        options: {
                          ...current.options,
                          batch_name: event.target.value,
                        },
                      }))}
                      sx={{ minWidth: 320, flex: 1 }}
                    />
                  </Stack>

                  <Stack direction="row" alignItems="center" spacing={1}>
                    <Switch
                      checked={Boolean(form.options?.remove_at_end)}
                      onChange={(event) => updateForm(segment.id, (current) => ({
                        ...current,
                        options: {
                          ...current.options,
                          remove_at_end: event.target.checked,
                        },
                      }))}
                    />
                    <Typography variant="body2">
                      Remove samples at end (run Ending task)
                    </Typography>
                  </Stack>

                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                    <Button
                      variant="outlined"
                      disabled={isPreviewing}
                      onClick={() => handlePreview(segment)}
                      color={segment.demo ? 'error' : 'primary'}
                    >
                      {isPreviewing ? 'Previewing…' : 'Preview'}
                    </Button>
                    <Button
                      variant="contained"
                      disabled={isRunning}
                      onClick={() => requestRun(segment)}
                      color={segment.demo ? 'error' : 'primary'}
                    >
                      {isRunning ? 'Submitting…' : (segment.demo ? 'Run DEMO' : 'Run')}
                    </Button>
                  </Stack>

                  {result?.payload?.samples?.length > 0 && (
                    <Box>
                      <Typography variant="subtitle2" sx={{ mb: 1 }}>
                        {result.payload.batch_name} ({result.payload.sample_count} sample
                        {result.payload.sample_count === 1 ? '' : 's'})
                      </Typography>
                      <Stack spacing={0.75}>
                        {result.payload.samples.map((sample) => (
                          <Typography key={sample.sample_name} variant="body2" sx={{ color: accents.text }}>
                            <strong>{sample.sample_name}</strong>
                            {' — '}
                            {sample.start_position}
                            {' → '}
                            {sample.destination_position}
                            {' ('}
                            {sample.task_chain}
                            {')'}
                          </Typography>
                        ))}
                      </Stack>
                    </Box>
                  )}

                  <Divider />

                  <Alert severity={result?.severity || 'info'}>
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                      {prettyJson(result?.payload)}
                    </pre>
                  </Alert>
                </Stack>
              </CardContent>
            </Card>
          );
  };

  return (
    <StyledMobileRobotControlDiv>
      <Stack spacing={2.5}>
        <Box>
          <Typography variant="h5">Mobile Robot Control</Typography>
          <Typography variant="body2" color="text.secondary">
            LABMAN ↔ BFT crucible transfers through AlabOS. Each direction builds a small batch
            (Starting → Moving → optional Ending) so the mobile robot executes the correct
            program legs. DASH hops are Prometheus, on BFT Control.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Preview first to confirm source and destination positions, then run to submit directly
            to AlabOS. After Run, check User Input Requests — Starting/Ending prompts must be
            answered before the robot moves.
          </Typography>
        </Box>

        {error && <Alert severity="error">{error}</Alert>}
        {loading && <CircularProgress size={28} />}

        {normalSegments.map((segment) => renderSegmentCard(segment))}

        {demoSegments.length > 0 && (
          <Box
            sx={{
              mt: 1,
              p: 2,
              borderRadius: '12px',
              border: `1px solid ${DEMO_ACCENTS.border}`,
              backgroundColor: DEMO_ACCENTS.shell,
            }}
          >
            <Typography variant="h6" sx={{ color: DEMO_ACCENTS.title, fontWeight: 700 }}>
              DEMO — no Labman control
            </Typography>
            <Typography variant="body2" sx={{ color: DEMO_ACCENTS.text, mt: 0.5, mb: 2 }}>
              These paths run the same Alfred Labman ↔ BFT motion without requesting Labman
              indexing-rack control or polling Labman. Use only when you have already staged
              the quadrant at the opening yourself.
            </Typography>
            <Stack spacing={2}>
              {demoSegments.map((segment) => renderSegmentCard(segment))}
            </Stack>
          </Box>
        )}
      </Stack>

      <Dialog
        open={Boolean(demoConfirmSegment)}
        onClose={() => setDemoConfirmSegment(null)}
      >
        <DialogTitle sx={{ color: DEMO_ACCENTS.title }}>
          Run DEMO without Labman control?
        </DialogTitle>
        <DialogContent>
          <DialogContentText component="div" sx={{ whiteSpace: 'pre-wrap', color: DEMO_ACCENTS.text }}>
            {demoConfirmSegment
              ? `${demoConfirmSegment.label}\n\n${DEMO_CONFIRM_COPY}`
              : DEMO_CONFIRM_COPY}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDemoConfirmSegment(null)}>Cancel</Button>
          <Button onClick={confirmDemoRun} color="error" variant="contained">
            I understand — run DEMO
          </Button>
        </DialogActions>
      </Dialog>
    </StyledMobileRobotControlDiv>
  );
}

export default MobileRobotControl;
