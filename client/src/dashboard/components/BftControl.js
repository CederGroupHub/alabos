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
  get_bft_control_catalog,
  preview_bft_segment,
  run_bft_segment,
} from '../../api_routes';

const StyledBftControlDiv = styled.div`
  margin: 12px 16px;
`;

const PAGE_ACCENTS = {
  border: '#d8e0e6',
  shell: '#f6f8fa',
  title: '#21323f',
  text: '#2b3d49',
  muted: '#5f7483',
};

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

function usesFurnace(segment) {
  return segment.param_kind === 'rack_to_furnace' || segment.param_kind === 'furnace_to_rack';
}

function defaultFormState(segment) {
  const params = {};
  Object.entries(segment.params || {}).forEach(([name, schema]) => {
    if (schema.default !== undefined) {
      params[name] = schema.default;
    } else if (schema.type === 'int_list') {
      params[name] = [];
    } else {
      params[name] = '';
    }
  });
  return {
    params,
    options: {
      remove_at_end: segment.options?.remove_at_end?.default ?? true,
      load_into_furnace: segment.options?.load_into_furnace?.default ?? true,
      batch_name: segment.default_batch_name || '',
    },
    slotText: {},
    destinationSlotText: {},
  };
}

function BftControl() {
  const [segments, setSegments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [forms, setForms] = useState({});
  const [pending, setPending] = useState({});
  const [results, setResults] = useState({});

  const refreshCatalog = async ({ showSpinner = false } = {}) => {
    if (showSpinner) {
      setLoading(true);
    }
    try {
      const response = await get_bft_control_catalog();
      if (response.status !== 'success') {
        throw new Error(response.errors || 'Failed to load BFT Control segments.');
      }
      const nextSegments = response.data?.segments || [];
      setSegments(nextSegments);
      setForms((previous) => {
        const next = { ...previous };
        nextSegments.forEach((segment) => {
          if (!next[segment.id]) {
            const defaults = defaultFormState(segment);
            defaults.slotText = {
              slots: formatIntList(defaults.params.slots),
            };
            next[segment.id] = defaults;
          }
        });
        return next;
      });
      setError('');
    } catch (fetchError) {
      setError(fetchError.message || 'Failed to load BFT Control segments.');
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
    const params = {
      ...form.params,
      slots: parseIntList(form.slotText?.slots || ''),
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
        ...(segment.options?.load_into_furnace
          ? { load_into_furnace: Boolean(form.options?.load_into_furnace) }
          : {}),
        batch_name: form.options?.batch_name || undefined,
      },
    };
  };

  const handlePreview = async (segment) => {
    setSegmentPending(segment.id, 'preview', true);
    setError('');
    try {
      const response = await preview_bft_segment(segment.id, buildRequestBody(segment));
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
      const response = await run_bft_segment(segment.id, buildRequestBody(segment));
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

  const orderedSegments = useMemo(
    () => [...segments].sort((left, right) => left.label.localeCompare(right.label)),
    [segments],
  );

  return (
    <StyledBftControlDiv>
      <Stack spacing={2.5}>
        <Box>
          <Typography variant="h5">BFT Control</Typography>
          <Typography variant="body2" color="text.secondary">
            Prometheus transfers: BFT rack ⇄ furnace cycle, furnace → BFT, and BFT rack → DASH.
            The furnace cycle is one task: crucibles onto the furnace rack, door open / load /
            close, door open / unload / close, then crucibles back to the same BFT slots.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Destination slots must be unique. Preview first, then run. Confirm Starting/Ending
            User Input Requests before Prometheus moves.
          </Typography>
        </Box>

        {error && <Alert severity="error">{error}</Alert>}
        {loading && <CircularProgress size={28} />}

        {orderedSegments.map((segment) => {
          const form = forms[segment.id] || defaultFormState(segment);
          const result = results[segment.id];
          const isPreviewing = pending[segment.id]?.preview;
          const isRunning = pending[segment.id]?.run;
          const sourceLabel = segment.params?.slots?.label || 'Source slots';
          const destLabel = segment.params?.destination_slots?.label || 'Destination slots';
          const destMin = segment.params?.destination_slots?.min;
          const destMax = segment.params?.destination_slots?.max;
          const sourceMin = segment.params?.slots?.min;
          const sourceMax = segment.params?.slots?.max;

          return (
            <Card key={segment.id} variant="outlined" sx={{ borderColor: PAGE_ACCENTS.border }}>
              <CardContent>
                <Stack spacing={2}>
                  <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={1.5}>
                    <Box>
                      <Typography variant="h6" sx={{ color: PAGE_ACCENTS.title }}>
                        {segment.label}
                      </Typography>
                      <Typography variant="body2" sx={{ color: PAGE_ACCENTS.muted }}>
                        {segment.source_station} → {segment.destination_station}
                      </Typography>
                      <Typography variant="body2" sx={{ color: PAGE_ACCENTS.text, mt: 0.5 }}>
                        {segment.description}
                      </Typography>
                    </Box>
                    <Chip
                      size="small"
                      label="Prometheus"
                      sx={{
                        width: 'fit-content',
                        backgroundColor: PAGE_ACCENTS.shell,
                        color: PAGE_ACCENTS.text,
                        fontWeight: 600,
                      }}
                    />
                  </Stack>

                  <Stack direction={{ xs: 'column', lg: 'row' }} spacing={2} flexWrap="wrap">
                    {usesFurnace(segment) && (
                      <FormControl size="small" sx={{ minWidth: 140 }}>
                        <InputLabel id={`${segment.id}-furnace-label`}>Furnace</InputLabel>
                        <Select
                          labelId={`${segment.id}-furnace-label`}
                          label="Furnace"
                          value={form.params?.furnace_box || 'a'}
                          onChange={(event) => updateForm(segment.id, (current) => ({
                            ...current,
                            params: {
                              ...current.params,
                              furnace_box: event.target.value,
                            },
                          }))}
                        >
                          {(segment.params?.furnace_box?.choices || ['a', 'b', 'c', 'd']).map((choice) => (
                            <MenuItem key={choice} value={choice}>
                              {`BFT_box_${choice}`}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    )}

                    <TextField
                      size="small"
                      label={sourceLabel}
                      helperText={`Space- or comma-separated slots ${sourceMin}–${sourceMax}`}
                      value={form.slotText?.slots || ''}
                      onChange={(event) => updateForm(segment.id, (current) => ({
                        ...current,
                        slotText: {
                          ...(current.slotText || {}),
                          slots: event.target.value,
                        },
                      }))}
                      sx={{ minWidth: 260 }}
                    />

                    <TextField
                      size="small"
                      label={destLabel}
                      helperText={`Unique slots ${destMin}–${destMax}. Leave blank to use the same numbers.`}
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

                  {segment.options?.load_into_furnace && (
                    <Stack direction="row" alignItems="center" spacing={1}>
                      <Switch
                        checked={Boolean(form.options?.load_into_furnace)}
                        onChange={(event) => updateForm(segment.id, (current) => ({
                          ...current,
                          options: {
                            ...current.options,
                            load_into_furnace: event.target.checked,
                          },
                        }))}
                      />
                      <Typography variant="body2">
                        Cycle rack through furnace (crucibles in, load, unload, crucibles back)
                      </Typography>
                    </Stack>
                  )}

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
                    >
                      {isPreviewing ? 'Previewing…' : 'Preview'}
                    </Button>
                    <Button
                      variant="contained"
                      disabled={isRunning}
                      onClick={() => handleRun(segment)}
                    >
                      {isRunning ? 'Submitting…' : 'Run'}
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
                          <Typography key={sample.sample_name} variant="body2" sx={{ color: PAGE_ACCENTS.text }}>
                            <strong>{sample.sample_name}</strong>
                            {' — '}
                            {sample.start_position}
                            {sample.furnace_position ? ` → ${sample.furnace_position}` : ''}
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
        })}
      </Stack>
    </StyledBftControlDiv>
  );
}

export default BftControl;
