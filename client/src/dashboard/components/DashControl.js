import React, { Fragment, useEffect, useMemo, useState } from 'react';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import styled from 'styled-components';
import {
  get_dash_control_catalog,
  preview_dash_stages,
  run_dash_stages,
} from '../../api_routes';

const StyledDashControlDiv = styled.div`
  margin: 12px 16px;
  max-width: 1100px;
`;

const FALLBACK_STAGES = [
  {
    key: 'recover_powder',
    label: 'Recover Powder',
    help:
      'Take a crucible from the DASH input rack and recover powder into a vial (weigh, shake, cap/decap).',
  },
  {
    key: 'diffraction_prep',
    label: 'Diffraction (XRD prep only)',
    help:
      'Dispense powder from a vial onto an XRD holder. Skips the Aeris sample scan unless XRD scan is also checked.',
  },
  {
    key: 'xrd_scan',
    label: 'XRD scan',
    help:
      'Scan a prepared XRD holder on Aeris. Alone, start from an auto-rack slot. With XRD prep, includes the sample scan after dispensing.',
  },
  {
    key: 'ending',
    label: 'Ending',
    help:
      'Finish the workflow: optionally print a QR label, then remove the sample from the active lab path.',
  },
];

const FALLBACK_SLOT_SCHEMAS = {
  crucible_slot: {
    label: 'Crucible slot (DASH input rack)',
    min: 1,
    max: 16,
    default: 1,
  },
  vial_slot: {
    label: 'Vial slot (consumable rack A)',
    min: 1,
    max: 40,
    default: 1,
  },
  xrd_auto_slot: {
    label: 'XRD holder slot (auto rack)',
    min: 1,
    max: 16,
    default: 1,
  },
};

const FALLBACK_DEFAULT_STAGES = {
  recover_powder: true,
  diffraction_prep: false,
  xrd_scan: false,
  ending: true,
};

function HelpHintIcon({ help }) {
  if (!help) {
    return null;
  }
  return (
    <Tooltip title={help} arrow>
      <HelpOutlineIcon
        fontSize="inherit"
        onClick={(event) => event.preventDefault()}
        sx={{
          fontSize: 15,
          color: 'text.secondary',
          cursor: 'help',
          opacity: 0.85,
          verticalAlign: 'middle',
          '&:hover': { color: 'primary.main', opacity: 1 },
        }}
      />
    </Tooltip>
  );
}

function StageCheckboxLabel({ label, help }) {
  return (
    <Stack
      direction="row"
      spacing={0.5}
      alignItems="center"
      component="span"
      sx={{ display: 'inline-flex' }}
    >
      <span>{label}</span>
      <HelpHintIcon help={help} />
    </Stack>
  );
}

function inferStartKind(stages) {
  if (stages.recover_powder) {
    return 'crucible_slot';
  }
  if (stages.diffraction_prep) {
    return 'vial_slot';
  }
  if (stages.xrd_scan) {
    return 'xrd_auto_slot';
  }
  return 'vial_slot';
}

function taskChainFromStages(stages) {
  const names = ['Starting'];
  if (stages.recover_powder) {
    names.push('RecoverPowder');
  }
  if (stages.diffraction_prep || stages.xrd_scan) {
    names.push('Diffraction');
  }
  if (stages.ending) {
    names.push('Ending');
  }
  return names;
}

function validationErrorsForStages(stages) {
  const errors = [];
  if (!Object.values(stages).some(Boolean)) {
    errors.push('Select at least one stage.');
  }
  if (stages.recover_powder && stages.xrd_scan && !stages.diffraction_prep) {
    errors.push(
      'Recover Powder + XRD scan requires Diffraction (XRD prep only). Recover yields a vial; the scan needs a prepared holder.',
    );
  }
  return errors;
}

function DashControl() {
  const [stageDefs, setStageDefs] = useState(FALLBACK_STAGES);
  const [slotSchemas, setSlotSchemas] = useState(FALLBACK_SLOT_SCHEMAS);
  const [stages, setStages] = useState(FALLBACK_DEFAULT_STAGES);
  const [slot, setSlot] = useState(1);
  const [batchName, setBatchName] = useState('');
  const [labelVial, setLabelVial] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [pending, setPending] = useState({ preview: false, run: false });
  const [result, setResult] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const response = await get_dash_control_catalog();
        if (response.status !== 'success') {
          throw new Error(response.errors || 'Failed to load DASH catalog.');
        }
        if (cancelled) {
          return;
        }
        const data = response.data || {};
        if (Array.isArray(data.stages) && data.stages.length) {
          setStageDefs(data.stages);
        }
        if (data.slot_schemas) {
          setSlotSchemas(data.slot_schemas);
        }
        if (data.default_stages) {
          setStages(data.default_stages);
        }
        setError('');
      } catch (fetchError) {
        if (!cancelled) {
          setError(fetchError.message || 'Failed to load DASH catalog.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const startKind = useMemo(() => inferStartKind(stages), [stages]);
  const slotSchema = slotSchemas[startKind] || FALLBACK_SLOT_SCHEMAS[startKind];
  const chain = useMemo(() => taskChainFromStages(stages), [stages]);
  const validationErrors = useMemo(() => validationErrorsForStages(stages), [stages]);
  const canSubmit = validationErrors.length === 0;

  useEffect(() => {
    const min = slotSchema?.min ?? 1;
    const max = slotSchema?.max ?? 16;
    setSlot((current) => {
      const value = Number(current) || min;
      if (value < min) {
        return min;
      }
      if (value > max) {
        return max;
      }
      return value;
    });
  }, [slotSchema?.min, slotSchema?.max]);

  const toggleStage = (key, checked) => {
    setStages((previous) => ({
      ...previous,
      [key]: checked,
    }));
    setResult(null);
  };

  const buildRequestBody = () => ({
    stages,
    params: {
      slot: Number(slot) || 1,
    },
    options: {
      batch_name: batchName || undefined,
      label_vial: Boolean(stages.ending && labelVial),
    },
  });

  const handlePreview = async () => {
    if (!canSubmit) {
      return;
    }
    setPending((previous) => ({ ...previous, preview: true }));
    setError('');
    try {
      const response = await preview_dash_stages(buildRequestBody());
      if (response.status !== 'success') {
        throw new Error(response.errors || 'Preview failed.');
      }
      setResult({ severity: 'info', payload: response.data });
    } catch (previewError) {
      setError(previewError.message || 'Preview failed.');
    } finally {
      setPending((previous) => ({ ...previous, preview: false }));
    }
  };

  const handleRun = async () => {
    if (!canSubmit) {
      return;
    }
    setPending((previous) => ({ ...previous, run: true }));
    setError('');
    try {
      const response = await run_dash_stages(buildRequestBody());
      if (response.status !== 'success') {
        throw new Error(response.errors || 'Run failed.');
      }
      setResult({ severity: 'success', payload: response.data });
    } catch (runError) {
      setError(runError.message || 'Run failed.');
    } finally {
      setPending((previous) => ({ ...previous, run: false }));
    }
  };

  return (
    <StyledDashControlDiv>
      <Stack spacing={2.5}>
        <Box>
          <Typography variant="h5">DASH Control</Typography>
          <Typography variant="body2" color="text.secondary">
            Build a one-sample DASH workflow from Recover Powder, XRD prep, XRD scan, and Ending.
            Preview the task chain, then Run. Confirm Starting/Ending prompts under User Input
            Requests.
          </Typography>
        </Box>

        {error && <Alert severity="error">{error}</Alert>}
        {loading && <CircularProgress size={28} />}

        {!loading && (
          <>
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Stages
              </Typography>
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: {
                    xs: '1fr',
                    sm: 'repeat(2, minmax(0, 1fr))',
                  },
                  gap: 1,
                  mb: 1,
                }}
              >
                {stageDefs.map((stage) => (
                  <FormControlLabel
                    key={stage.key}
                    sx={{
                      m: 0,
                      width: '100%',
                      height: '100%',
                      alignItems: 'center',
                      px: 1.25,
                      py: 1.25,
                      border: '1px solid',
                      borderColor: stages[stage.key] ? 'primary.light' : 'divider',
                      borderRadius: 1,
                      bgcolor: stages[stage.key] ? 'action.selected' : 'background.paper',
                      '& .MuiFormControlLabel-label': { width: '100%' },
                    }}
                    control={
                      <Checkbox
                        size="small"
                        checked={Boolean(stages[stage.key])}
                        onChange={(event) => toggleStage(stage.key, event.target.checked)}
                      />
                    }
                    label={<StageCheckboxLabel label={stage.label} help={stage.help} />}
                  />
                ))}
              </Box>

              <Stack
                direction="row"
                spacing={0.5}
                alignItems="center"
                sx={{ mb: 0.5 }}
                useFlexGap
                flexWrap="wrap"
              >
                <Typography variant="body2" color="text.secondary" component="span">
                  Task chain:
                </Typography>
                {canSubmit ? (
                  chain.map((task, index) => (
                    <Fragment key={`${task}-${index}`}>
                      {index > 0 && (
                        <Typography
                          component="span"
                          variant="body2"
                          color="text.secondary"
                          aria-hidden
                          sx={{ px: 0.25, lineHeight: 1 }}
                        >
                          →
                        </Typography>
                      )}
                      <Chip size="small" label={task} />
                    </Fragment>
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary" component="span">
                    (invalid)
                  </Typography>
                )}
              </Stack>
            </Box>

            {validationErrors.length > 0 && (
              <Alert severity="error">
                {validationErrors.map((message) => (
                  <Typography key={message} variant="body2">
                    {message}
                  </Typography>
                ))}
              </Alert>
            )}

            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} flexWrap="wrap">
              <TextField
                size="small"
                type="number"
                label={slotSchema?.label || 'Slot'}
                helperText={`${slotSchema?.min ?? 1} – ${slotSchema?.max ?? 16}`}
                value={slot}
                onChange={(event) => setSlot(event.target.value)}
                inputProps={{
                  min: slotSchema?.min ?? 1,
                  max: slotSchema?.max ?? 16,
                }}
                sx={{ width: 280 }}
              />
              <TextField
                size="small"
                label="Batch name"
                value={batchName}
                onChange={(event) => setBatchName(event.target.value)}
                placeholder="Optional"
                sx={{ minWidth: 320, flex: 1 }}
              />
            </Stack>

            {stages.ending && (
              <Stack direction="row" alignItems="center" spacing={1}>
                <Switch
                  checked={labelVial}
                  onChange={(event) => setLabelVial(event.target.checked)}
                />
                <Typography variant="body2">Print QR label on vial</Typography>
              </Stack>
            )}

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
              <Button
                variant="outlined"
                disabled={!canSubmit || pending.preview || pending.run}
                onClick={handlePreview}
              >
                {pending.preview ? 'Previewing\u2026' : 'Preview'}
              </Button>
              <Button
                variant="contained"
                disabled={!canSubmit || pending.preview || pending.run}
                onClick={handleRun}
              >
                {pending.run ? 'Submitting\u2026' : 'Run'}
              </Button>
            </Stack>

            {result?.payload && (
              <Alert severity={result.severity || 'info'}>
                <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
                  {result.payload.batch_name}
                  {result.payload.experiment_id
                    ? ` · experiment ${result.payload.experiment_id}`
                    : ''}
                </Typography>
                {(result.payload.samples || []).map((sample) => (
                  <Typography key={sample.sample_name} variant="body2">
                    <strong>{sample.sample_name}</strong>
                    {' \u2014 '}
                    {sample.start_position}
                    {' ('}
                    {sample.task_chain}
                    {')'}
                  </Typography>
                ))}
                {result.payload.note && (
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    {result.payload.note}
                  </Typography>
                )}
              </Alert>
            )}
          </>
        )}
      </Stack>
    </StyledDashControlDiv>
  );
}

export default DashControl;
