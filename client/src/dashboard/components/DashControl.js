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
  get_dash_control_catalog,
  preview_dash_segment,
  run_dash_segment,
} from '../../api_routes';

const StyledDashControlDiv = styled.div`
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

function prettyJson(value) {
  if (value === undefined || value === null || value === '') {
    return 'No preview yet.';
  }
  if (typeof value === 'string') {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

function defaultFormState(segment) {
  return {
    slot: segment.params?.slot?.default ?? 1,
    options: {
      advanced_place: segment.options?.advanced_place?.default ?? true,
      label_vial: segment.options?.label_vial?.default ?? false,
      remove_at_end: segment.options?.remove_at_end?.default ?? true,
      batch_name: segment.default_batch_name || '',
    },
  };
}

function DashControl() {
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
      const response = await get_dash_control_catalog();
      if (response.status !== 'success') {
        throw new Error(response.errors || 'Failed to load DASH segments.');
      }
      const nextSegments = response.data?.segments || [];
      setSegments(nextSegments);
      setForms((previous) => {
        const next = { ...previous };
        nextSegments.forEach((segment) => {
          if (!next[segment.id]) {
            next[segment.id] = defaultFormState(segment);
          }
        });
        return next;
      });
      setError('');
    } catch (fetchError) {
      setError(fetchError.message || 'Failed to load DASH segments.');
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
    return {
      params: {
        slot: Number(form.slot) || 1,
      },
      options: {
        advanced_place: Boolean(form.options?.advanced_place),
        label_vial: Boolean(form.options?.label_vial),
        remove_at_end: Boolean(form.options?.remove_at_end),
        batch_name: form.options?.batch_name || undefined,
      },
    };
  };

  const handlePreview = async (segment) => {
    setSegmentPending(segment.id, 'preview', true);
    setError('');
    try {
      const response = await preview_dash_segment(segment.id, buildRequestBody(segment));
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
      const response = await run_dash_segment(segment.id, buildRequestBody(segment));
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
    <StyledDashControlDiv>
      <Stack spacing={2.5}>
        <Typography
          variant="subtitle2"
          sx={{
            color: '#d32f2f',
            fontWeight: 700,
            letterSpacing: '0.03em',
          }}
        >
          This page is still under development.
        </Typography>

        <Box>
          <Typography variant="h5">DASH Control</Typography>
          <Typography variant="body2" color="text.secondary">
            Run a single DASH workflow slice. Each segment submits exactly 1 sample
            through AlabOS (Starting &rarr; task chain &rarr; optional Ending).
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Preview first to confirm the task chain, then Run to submit. After Run,
            check User Input Requests &mdash; Starting/Ending prompts must be answered
            before the workflow proceeds.
          </Typography>
        </Box>

        {error && <Alert severity="error">{error}</Alert>}
        {loading && <CircularProgress size={28} />}

        {orderedSegments.map((segment) => {
          const form = forms[segment.id] || defaultFormState(segment);
          const result = results[segment.id];
          const isPreviewing = pending[segment.id]?.preview;
          const isRunning = pending[segment.id]?.run;
          const slotSchema = segment.params?.slot || {};
          const hasRemoveAtEnd = segment.options?.remove_at_end !== undefined;
          const hasLabelVial = segment.options?.label_vial !== undefined;

          return (
            <Card key={segment.id} variant="outlined" sx={{ borderColor: PAGE_ACCENTS.border }}>
              <CardContent>
                <Stack spacing={2}>
                  <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={1.5}>
                    <Box>
                      <Typography variant="h6" sx={{ color: PAGE_ACCENTS.title }}>
                        {segment.label}
                      </Typography>
                      <Typography variant="body2" sx={{ color: PAGE_ACCENTS.text, mt: 0.5 }}>
                        {segment.description}
                      </Typography>
                    </Box>
                    <Stack direction="row" spacing={1} alignItems="flex-start" sx={{ flexShrink: 0 }}>
                      <Chip
                        size="small"
                        label={segment.task_chain_display}
                        sx={{
                          backgroundColor: PAGE_ACCENTS.shell,
                          color: PAGE_ACCENTS.text,
                          fontWeight: 600,
                        }}
                      />
                      <Chip
                        size="small"
                        label="1 sample"
                        sx={{
                          backgroundColor: '#e8f0fe',
                          color: '#1a56db',
                          fontWeight: 600,
                        }}
                      />
                    </Stack>
                  </Stack>

                  {segment.has_diffraction && (
                    <Alert severity="info" variant="outlined" sx={{ py: 0.25 }}>
                      Prep only (skip Aeris scans)
                    </Alert>
                  )}

                  <Stack direction={{ xs: 'column', lg: 'row' }} spacing={2} flexWrap="wrap">
                    <TextField
                      size="small"
                      type="number"
                      label={slotSchema.label || 'Slot'}
                      helperText={`${slotSchema.min || 1} – ${slotSchema.max || 16}`}
                      value={form.slot}
                      onChange={(event) => updateForm(segment.id, (current) => ({
                        ...current,
                        slot: event.target.value,
                      }))}
                      inputProps={{
                        min: slotSchema.min || 1,
                        max: slotSchema.max || 16,
                      }}
                      sx={{ width: 220 }}
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

                  <Stack spacing={0.5}>
                    <Stack direction="row" alignItems="center" spacing={1}>
                      <Switch
                        checked={Boolean(form.options?.advanced_place)}
                        onChange={(event) => updateForm(segment.id, (current) => ({
                          ...current,
                          options: {
                            ...current.options,
                            advanced_place: event.target.checked,
                          },
                        }))}
                      />
                      <Typography variant="body2">
                        Advanced place (Clutter pick/place scripts)
                      </Typography>
                    </Stack>

                    {hasRemoveAtEnd && (
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
                          Remove sample at end (run Ending task)
                        </Typography>
                      </Stack>
                    )}

                    {hasLabelVial && (
                      <Stack direction="row" alignItems="center" spacing={1}>
                        <Switch
                          checked={Boolean(form.options?.label_vial)}
                          onChange={(event) => updateForm(segment.id, (current) => ({
                            ...current,
                            options: {
                              ...current.options,
                              label_vial: event.target.checked,
                            },
                          }))}
                        />
                        <Typography variant="body2">
                          Print QR label on vial
                        </Typography>
                      </Stack>
                    )}
                  </Stack>

                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                    <Button
                      variant="outlined"
                      disabled={isPreviewing}
                      onClick={() => handlePreview(segment)}
                    >
                      {isPreviewing ? 'Previewing\u2026' : 'Preview'}
                    </Button>
                    <Button
                      variant="contained"
                      disabled={isRunning}
                      onClick={() => handleRun(segment)}
                    >
                      {isRunning ? 'Submitting\u2026' : 'Run'}
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
                            {' \u2014 '}
                            {sample.start_position}
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
    </StyledDashControlDiv>
  );
}

export default DashControl;
