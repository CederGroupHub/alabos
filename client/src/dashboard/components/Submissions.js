import React, { Fragment, useEffect, useMemo, useState } from 'react';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Switch,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  confirm_freeform_submission,
  create_freeform_job,
  create_submission_sample,
  get_freeform_devices,
  get_freeform_job,
  get_labman_submission_schema,
  get_submission_recipes,
  preview_labman_submission,
  preview_submission_recipe,
  resolve_submission_samples,
  submit_labman_submission,
  submit_submission_recipe,
} from '../../api_routes';

/** Browser autofill props — unique tokens so Chrome does not reuse unrelated history. */
function noBrowserAutofill(fieldKey) {
  const token = `alab-no-fill-${fieldKey}`;
  return {
    name: token,
    autoComplete: token,
    inputProps: {
      autoComplete: token,
      'data-lpignore': 'true',
      'data-1p-ignore': 'true',
      'data-form-type': 'other',
    },
  };
}

const LABMAN_TABLE_COLUMNS = [
  {
    key: 'project_name',
    label: 'Project name',
    width: 140,
    help:
      'Prefix of the sample name. Final name is {project}_{index}. Must start with a letter; '
      + 'letters, digits, and hyphens only — no underscore. Example: DEMO.',
  },
  {
    key: 'sample_index',
    label: 'Index',
    width: 88,
    help:
      'Second half of the sample name. Letters/digits only; optional hyphen tag '
      + '(e.g. 1 or 12-a). Example: 1 → DEMO_1.',
  },
  {
    key: 'target_composition',
    label: 'Target composition',
    width: 160,
    help:
      'Chemical formula for balancing. Use normal element capitalization, e.g. LiCoO2. '
      + 'Required with precursors + target mass, unless powder dispenses is set.',
  },
  {
    key: 'precursors',
    label: 'Precursors',
    width: 200,
    help:
      'Comma-separated precursor formulas/powder names, e.g. Li2CO3, Co2O3. '
      + 'Optional _PG suffix for powder-grade Labman bottles (Li2CO3_PG).',
  },
  {
    key: 'target_mass_g',
    label: 'Target mass (g)',
    width: 100,
    type: 'number',
    help: 'Total target mass in grams (> 0). Required with composition + precursors.',
  },
  {
    key: 'powder_dispenses_text',
    label: 'Powder dispenses',
    width: 200,
    help:
      'Optional direct Labman powders as Name:mass_g pairs (comma, semicolon, or newlines), '
      + 'e.g. Li2CO3:1.2, Co2O3:0.8. When set, skips composition/precursor balancing.',
  },
  {
    key: 'ethanol_volume_ul',
    label: 'Ethanol (µL)',
    width: 120,
    type: 'number',
    help: 'Labman EthanolDispenseVolume per replicate. Blank = auto from recipe or default 10000.',
  },
  {
    key: 'drying_duration_second',
    label: 'Drying (s)',
    width: 110,
    type: 'number',
    help: 'Labman slurry drying HeatingDuration (ethanol boil-off, ~80 °C), in seconds.',
  },
  {
    key: 'mixer_speed_rpm',
    label: 'Mixer rpm',
    width: 110,
    type: 'number',
    help: 'Labman MixerSpeed. Blank defaults to 2000 rpm.',
  },
  {
    key: 'mixer_duration_s',
    label: 'Mixer (s)',
    width: 110,
    type: 'number',
    help: 'Labman MixerDuration in seconds. Blank defaults to 540.',
  },
  {
    key: 'transfer_volume_ul',
    label: 'Transfer (µL)',
    width: 120,
    type: 'number',
    help: 'Labman TargetTransferVolume. Blank defaults to the ethanol volume.',
  },
  {
    key: 'min_transfer_mass_g',
    label: 'Min transfer (g)',
    width: 130,
    type: 'number',
    help: 'Labman MinimumTransferMass in grams (optional).',
  },
  {
    key: 'replicates',
    label: 'Replicates',
    width: 110,
    type: 'number',
    help: 'Labman CrucibleReplicates. Blank defaults to 1.',
  },
  {
    key: 'allow_replicates',
    label: 'Allow reps',
    width: 100,
    type: 'boolean',
    help: 'Whether Labman may batch crucible replicates together.',
  },
];

function ColumnHeaderLabel({ label, help }) {
  if (!help) {
    return label;
  }
  return (
    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ display: 'inline-flex' }}>
      <span>{label}</span>
      <Tooltip title={help} arrow placement="top" enterDelay={200}>
        <HelpOutlineIcon
          fontSize="inherit"
          sx={{
            fontSize: 15,
            color: 'text.secondary',
            cursor: 'help',
            opacity: 0.85,
            '&:hover': { color: 'primary.main', opacity: 1 },
          }}
        />
      </Tooltip>
    </Stack>
  );
}

function emptyLabmanRow(overrides = {}) {
  return {
    project_name: '',
    sample_index: '',
    target_composition: '',
    precursors: '',
    target_mass_g: '',
    powder_dispenses_text: '',
    ethanol_volume_ul: '',
    drying_duration_second: '',
    mixer_speed_rpm: '',
    mixer_duration_s: '',
    transfer_volume_ul: '',
    min_transfer_mass_g: '',
    replicates: '',
    allow_replicates: false,
    ...overrides,
  };
}

function emptyRecipeSampleRow(columns = [], overrides = {}) {
  const row = {};
  columns.forEach((col) => {
    if (col.type === 'boolean') {
      row[col.name] = col.default !== undefined ? col.default : false;
    } else if (col.default !== undefined && col.default !== null) {
      row[col.name] = String(col.default);
    } else {
      row[col.name] = '';
    }
  });
  return { ...row, ...overrides };
}

function coerceRecipeSampleRows(rows, columns) {
  const samples = rows
    .filter((row) => String(row.project_name || '').trim() && String(row.sample_index || '').trim())
    .map((row) => {
      const sample = {};
      columns.forEach((col) => {
        const raw = row[col.name];
        if (col.type === 'boolean') {
          sample[col.name] = Boolean(raw);
          return;
        }
        if (col.type === 'number') {
          if (raw !== '' && raw != null) {
            sample[col.name] = Number(raw);
          }
          return;
        }
        if (col.type === 'string_list') {
          const list = String(raw ?? '')
            .split(',')
            .map((part) => part.trim())
            .filter(Boolean);
          if (list.length) {
            sample[col.name] = list;
          }
          return;
        }
        const text = String(raw ?? '').trim();
        if (text) {
          sample[col.name] = text;
        }
      });
      return sample;
    });
  if (!samples.length) {
    throw new Error('Add at least one row with Project name and Index.');
  }
  return samples;
}

const POLL_MS = 1500;

function TabPanel({ value, index, children }) {
  if (value !== index) {
    return null;
  }
  return <Box sx={{ pt: 2 }}>{children}</Box>;
}

function taskSummary(experiment) {
  const tasks = experiment?.tasks || [];
  if (!tasks.length) {
    return 'No tasks';
  }
  return tasks.map((task, idx) => `${idx + 1}. ${task.type}`).join(' → ');
}

export default function Submissions() {
  const [tab, setTab] = useState(0);
  const [recipes, setRecipes] = useState([]);
  const [recipesError, setRecipesError] = useState('');
  const [selectedRecipe, setSelectedRecipe] = useState(null);
  const [formValues, setFormValues] = useState({});
  const [recipeSampleRows, setRecipeSampleRows] = useState([]);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);

  const [devices, setDevices] = useState([]);
  const [deviceName, setDeviceName] = useState('');
  const [prompt, setPrompt] = useState('');
  const [sampleMode, setSampleMode] = useState('existing');
  const [sampleQuery, setSampleQuery] = useState('');
  const [sampleHits, setSampleHits] = useState([]);
  const [selectedSample, setSelectedSample] = useState(null);
  const [newSampleName, setNewSampleName] = useState('');
  const [newSampleTags, setNewSampleTags] = useState('');
  const [assertPlaced, setAssertPlaced] = useState(true);
  const [placementPosition, setPlacementPosition] = useState('');
  const [freeformJob, setFreeformJob] = useState(null);
  const [draft, setDraft] = useState(null);

  const [labmanSchema, setLabmanSchema] = useState(null);
  const [labmanError, setLabmanError] = useState('');
  const [labmanBatchName, setLabmanBatchName] = useState('labman_batch');
  const [labmanRows, setLabmanRows] = useState([
    emptyLabmanRow({
      project_name: 'DEMO',
      sample_index: '1',
      target_composition: 'LiCoO2',
      precursors: 'Li2CO3, Co2O3',
      target_mass_g: '2',
      ethanol_volume_ul: '10000',
      drying_duration_second: '7200',
    }),
  ]);
  const [labmanPreview, setLabmanPreview] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await get_submission_recipes();
        if (!cancelled) {
          setRecipes(data.recipes || []);
        }
      } catch (err) {
        if (!cancelled) {
          setRecipesError(String(err?.message || err));
        }
      }
      try {
        const data = await get_labman_submission_schema();
        if (!cancelled) {
          if (data.status === 'error') {
            setLabmanError(data.errors || data.error || 'Could not load Labman schema');
          } else {
            setLabmanSchema(data);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setLabmanError(String(err?.message || err));
        }
      }
      try {
        const data = await get_freeform_devices();
        if (!cancelled) {
          const list = data.devices || [];
          setDevices(list);
          if (list.length && !deviceName) {
            setDeviceName(list[0].name);
          }
        }
      } catch {
        /* allow recipes tab without freeform catalog */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [deviceName]);

  const selectedDevice = useMemo(
    () => devices.find((entry) => entry.name === deviceName) || null,
    [devices, deviceName],
  );

  const openRecipe = (recipe) => {
    setSelectedRecipe(recipe);
    setPreview(null);
    setMessage(null);
    const defaults = {};
    (recipe.fields || []).forEach((field) => {
      if (field.default !== undefined) {
        defaults[field.name] = field.default;
      } else if (field.type === 'boolean') {
        defaults[field.name] = false;
      } else {
        defaults[field.name] = '';
      }
    });
    setFormValues(defaults);
    if (recipe.samples_table) {
      setRecipeSampleRows([emptyRecipeSampleRow(recipe.sample_columns || [])]);
    } else {
      setRecipeSampleRows([]);
    }
  };

  const setField = (name, value) => {
    setFormValues((prev) => ({ ...prev, [name]: value }));
  };

  const recipeSampleColumns = selectedRecipe?.sample_columns || [];

  const setRecipeSampleCell = (rowIndex, key, value) => {
    setRecipeSampleRows((prev) =>
      prev.map((row, idx) => (idx === rowIndex ? { ...row, [key]: value } : row)),
    );
  };

  const addRecipeSampleRow = () => {
    setRecipeSampleRows((prev) => [
      ...prev,
      emptyRecipeSampleRow(recipeSampleColumns),
    ]);
  };

  const removeRecipeSampleRow = (rowIndex) => {
    setRecipeSampleRows((prev) => {
      if (prev.length <= 1) {
        return [emptyRecipeSampleRow(recipeSampleColumns)];
      }
      return prev.filter((_, idx) => idx !== rowIndex);
    });
  };

  const buildPayload = () => {
    const payload = { ...formValues };
    if (selectedRecipe?.samples_table) {
      payload.samples = coerceRecipeSampleRows(recipeSampleRows, recipeSampleColumns);
    }
    // Coerce batch-level numeric / list fields
    (selectedRecipe?.fields || []).forEach((field) => {
      if (field.type === 'number' && payload[field.name] !== '' && payload[field.name] != null) {
        payload[field.name] = Number(payload[field.name]);
      }
      if (field.type === 'string_list' && typeof payload[field.name] === 'string') {
        payload[field.name] = payload[field.name]
          .split(',')
          .map((part) => part.trim())
          .filter(Boolean);
      }
    });
    return payload;
  };

  const runPreview = async () => {
    if (!selectedRecipe) {
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const data = await preview_submission_recipe(selectedRecipe.id, buildPayload());
      if (data.status === 'error') {
        setMessage({ severity: 'error', text: data.errors || data.error || 'Preview failed' });
        setPreview(null);
      } else {
        setPreview(data);
      }
    } catch (err) {
      setMessage({ severity: 'error', text: String(err?.message || err) });
    } finally {
      setBusy(false);
    }
  };

  const runSubmit = async () => {
    if (!selectedRecipe) {
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const data = await submit_submission_recipe(selectedRecipe.id, buildPayload());
      if (data.status === 'error') {
        setMessage({ severity: 'error', text: data.errors || data.error || 'Submit failed' });
      } else {
        const expId = data.data?.exp_id || data.exp_id;
        setMessage({
          severity: 'success',
          text: `Submitted experiment ${expId}. Open Experiments to track it.`,
        });
        setPreview(null);
      }
    } catch (err) {
      setMessage({ severity: 'error', text: String(err?.message || err) });
    } finally {
      setBusy(false);
    }
  };

  const buildLabmanPayload = () => {
    const samples = labmanRows
      .filter((row) => String(row.project_name || '').trim() && String(row.sample_index || '').trim())
      .map((row) => {
        const sample = {
          project_name: String(row.project_name).trim(),
          sample_index: String(row.sample_index).trim(),
        };
        const textFields = ['target_composition', 'powder_dispenses_text'];
        textFields.forEach((key) => {
          const value = String(row[key] ?? '').trim();
          if (value) {
            sample[key] = value;
          }
        });
        const precursors = String(row.precursors ?? '')
          .split(',')
          .map((part) => part.trim())
          .filter(Boolean);
        if (precursors.length) {
          sample.precursors = precursors;
        }
        [
          'target_mass_g',
          'ethanol_volume_ul',
          'drying_duration_second',
          'mixer_speed_rpm',
          'mixer_duration_s',
          'transfer_volume_ul',
          'min_transfer_mass_g',
          'replicates',
        ].forEach((key) => {
          const raw = row[key];
          if (raw !== '' && raw != null) {
            sample[key] = Number(raw);
          }
        });
        sample.allow_replicates = Boolean(row.allow_replicates);
        return sample;
      });
    if (!samples.length) {
      throw new Error('Add at least one row with Project name and Index.');
    }
    return {
      name: labmanBatchName.trim() || 'labman_batch',
      samples,
    };
  };

  const setLabmanCell = (rowIndex, key, value) => {
    setLabmanRows((prev) =>
      prev.map((row, idx) => (idx === rowIndex ? { ...row, [key]: value } : row)),
    );
  };

  const addLabmanRow = () => {
    setLabmanRows((prev) => [...prev, emptyLabmanRow()]);
  };

  const removeLabmanRow = (rowIndex) => {
    setLabmanRows((prev) => {
      if (prev.length <= 1) {
        return [emptyLabmanRow()];
      }
      return prev.filter((_, idx) => idx !== rowIndex);
    });
  };

  const runLabmanPreview = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const data = await preview_labman_submission(buildLabmanPayload());
      if (data.status === 'error') {
        setMessage({ severity: 'error', text: data.errors || data.error || 'Preview failed' });
        setLabmanPreview(null);
      } else {
        setLabmanPreview(data);
      }
    } catch (err) {
      setMessage({ severity: 'error', text: String(err?.message || err) });
    } finally {
      setBusy(false);
    }
  };

  const runLabmanSubmit = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const data = await submit_labman_submission(buildLabmanPayload());
      if (data.status === 'error') {
        setMessage({ severity: 'error', text: data.errors || data.error || 'Submit failed' });
      } else {
        const expId = data.data?.exp_id || data.exp_id;
        setMessage({
          severity: 'success',
          text: `Submitted Labman experiment ${expId}. Open Experiments to track it.`,
        });
        setLabmanPreview(null);
      }
    } catch (err) {
      setMessage({ severity: 'error', text: String(err?.message || err) });
    } finally {
      setBusy(false);
    }
  };

  const searchSamples = async () => {
    setBusy(true);
    try {
      const data = await resolve_submission_samples(sampleQuery);
      setSampleHits(data.samples || []);
    } catch (err) {
      setMessage({ severity: 'error', text: String(err?.message || err) });
    } finally {
      setBusy(false);
    }
  };

  const ensureSampleId = async () => {
    if (sampleMode === 'existing') {
      if (!selectedSample?.sample_id) {
        throw new Error('Select an existing sample first.');
      }
      return {
        sample_id: selectedSample.sample_id,
        sample_name: selectedSample.name,
        reuse_existing: true,
      };
    }
    if (!newSampleName.trim()) {
      throw new Error('Enter a name for the new sample.');
    }
    const tags = newSampleTags
      .split(',')
      .map((part) => part.trim())
      .filter(Boolean);
    const created = await create_submission_sample({
      name: newSampleName.trim(),
      tags,
      position: assertPlaced && placementPosition.trim() ? placementPosition.trim() : null,
      metadata: {},
    });
    if (created.status === 'error') {
      throw new Error(created.errors || created.error || 'Could not create sample');
    }
    return {
      sample_id: created.sample_id,
      sample_name: created.name,
      reuse_existing: true,
    };
  };

  const startFreeform = async () => {
    setBusy(true);
    setMessage(null);
    setDraft(null);
    try {
      const sample = await ensureSampleId();
      if (!deviceName) {
        throw new Error('Pick a target device.');
      }
      if (!prompt.trim()) {
        throw new Error('Enter a free-form request.');
      }
      const body = {
        prompt: prompt.trim(),
        device_name: deviceName,
        sample_id: sample.sample_id,
        sample_name: sample.sample_name,
        reuse_existing: sample.reuse_existing,
        physical_placement: assertPlaced
          ? {
              operator_asserted: true,
              position: placementPosition.trim() || null,
            }
          : null,
      };
      const job = await create_freeform_job(body);
      if (job.status === 'error' || job.http_status >= 400) {
        throw new Error(job.errors || job.error || 'Could not start free-form job');
      }
      setFreeformJob(job);
    } catch (err) {
      setMessage({ severity: 'error', text: String(err?.message || err) });
      setBusy(false);
    }
  };

  useEffect(() => {
    if (!freeformJob?.id) {
      return undefined;
    }
    if (freeformJob.status === 'succeeded' || freeformJob.status === 'failed') {
      setBusy(false);
      if (freeformJob.status === 'succeeded') {
        setDraft(freeformJob.draft || null);
      } else {
        setMessage({
          severity: 'error',
          text: freeformJob.error || 'Free-form job failed',
        });
      }
      return undefined;
    }
    const timer = setInterval(async () => {
      try {
        const next = await get_freeform_job(freeformJob.id);
        setFreeformJob(next);
      } catch {
        /* keep polling */
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [freeformJob]);

  const confirmFreeform = async () => {
    if (!draft) {
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const data = await confirm_freeform_submission({
        experiment: draft.experiment,
        job_id: freeformJob?.id,
      });
      if (data.status === 'error') {
        throw new Error(data.errors || data.error || 'Confirm failed');
      }
      const expId = data.data?.exp_id || data.exp_id;
      setMessage({
        severity: 'success',
        text: `Submitted experiment ${expId}. Open Experiments to track it.`,
      });
      setDraft(null);
      setFreeformJob(null);
    } catch (err) {
      setMessage({ severity: 'error', text: String(err?.message || err) });
    } finally {
      setBusy(false);
    }
  };

  const renderRecipeField = (field) => {
    if (field.type === 'boolean') {
      return (
        <FormControlLabel
          key={field.name}
          control={
            <Switch
              checked={Boolean(formValues[field.name])}
              onChange={(event) => setField(field.name, event.target.checked)}
            />
          }
          label={field.label}
        />
      );
    }
    if (field.type === 'select' && field.options) {
      return (
        <FormControl fullWidth key={field.name} size="small">
          <InputLabel>{field.label}</InputLabel>
          <Select
            label={field.label}
            value={formValues[field.name] ?? ''}
            onChange={(event) => setField(field.name, event.target.value)}
          >
            {field.options.map((option) => (
              <MenuItem key={option} value={option}>
                {option}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      );
    }
    return (
      <TextField
        key={field.name}
        size="small"
        fullWidth
        label={field.label}
        helperText={field.help}
        type={field.type === 'number' ? 'number' : 'text'}
        {...noBrowserAutofill(field.name)}
        value={formValues[field.name] ?? ''}
        onChange={(event) => setField(field.name, event.target.value)}
        required={field.required}
        multiline={field.type === 'textarea'}
        minRows={field.type === 'textarea' ? 3 : undefined}
      />
    );
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1100 }}>
      <Typography variant="h5" gutterBottom>
        Submissions
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Guided recipes for multi-device workflows, Labman-only dosing, or free-form single-device runs.
      </Typography>

      {message && (
        <Alert severity={message.severity} sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message.text}
        </Alert>
      )}

      <Tabs value={tab} onChange={(_, value) => setTab(value)}>
        <Tab label="Recipes" />
        <Tab label="Labman" />
        <Tab label="Free-form (one device)" />
      </Tabs>

      <TabPanel value={tab} index={0}>
        {recipesError && <Alert severity="error">{recipesError}</Alert>}
        <Stack
          direction={{ xs: 'column', md: 'row' }}
          spacing={2}
          useFlexGap
          flexWrap="wrap"
          alignItems="stretch"
        >
          {recipes.map((recipe) => (
            <Card
              key={recipe.id}
              sx={{
                width: 280,
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <CardActionArea
                onClick={() => openRecipe(recipe)}
                sx={{
                  flex: 1,
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'stretch',
                }}
              >
                <CardContent sx={{ flex: 1 }}>
                  <Typography variant="subtitle1">{recipe.title}</Typography>
                  {recipe.description ? (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                      {recipe.description}
                    </Typography>
                  ) : null}
                  <Stack
                    direction="row"
                    spacing={0.5}
                    alignItems="center"
                    sx={{ mt: 1 }}
                    useFlexGap
                    flexWrap="wrap"
                  >
                    {(recipe.task_chain || []).map((task, index) => (
                      <Fragment key={task}>
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
                    ))}
                  </Stack>
                </CardContent>
              </CardActionArea>
            </Card>
          ))}
        </Stack>
      </TabPanel>

      <TabPanel value={tab} index={1}>
        {labmanError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {labmanError}
          </Alert>
        )}
        <Alert severity="info" sx={{ mb: 2 }}>
          {labmanSchema?.description ||
            'Submit PowderDosing → Ending only. One row per sample — add rows as needed.'}
        </Alert>
        <Stack spacing={2}>
          <TextField
            size="small"
            label="Batch name"
            {...noBrowserAutofill('labman-batch')}
            value={labmanBatchName}
            onChange={(event) => setLabmanBatchName(event.target.value)}
            sx={{ maxWidth: 360 }}
          />
          <TableContainer
            component={Paper}
            variant="outlined"
            sx={{
              maxWidth: '100%',
              borderRadius: 2,
              borderColor: 'divider',
              boxShadow: 'none',
            }}
          >
            <Table
              stickyHeader
              sx={{
                minWidth: 1680,
                '& .MuiTableCell-root': {
                  borderColor: 'divider',
                },
                '& .MuiTableBody-root .MuiTableRow-root:hover': {
                  backgroundColor: 'action.hover',
                },
              }}
            >
              <TableHead>
                <TableRow>
                  <TableCell
                    sx={{
                      width: 56,
                      bgcolor: 'grey.50',
                      fontWeight: 600,
                      fontSize: 14,
                      color: 'text.secondary',
                      py: 1.5,
                    }}
                  >
                    #
                  </TableCell>
                  {LABMAN_TABLE_COLUMNS.map((col) => (
                    <TableCell
                      key={col.key}
                      sx={{
                        minWidth: col.width,
                        bgcolor: 'grey.50',
                        fontWeight: 600,
                        fontSize: 14,
                        color: 'text.secondary',
                        whiteSpace: 'nowrap',
                        py: 1.5,
                      }}
                    >
                      <ColumnHeaderLabel label={col.label} help={col.help} />
                    </TableCell>
                  ))}
                  <TableCell sx={{ width: 56, bgcolor: 'grey.50', py: 1.5 }} />
                </TableRow>
              </TableHead>
              <TableBody>
                {labmanRows.map((row, rowIndex) => (
                  <TableRow key={`labman-row-${rowIndex}`}>
                    <TableCell sx={{ py: 1.5, color: 'text.secondary', fontSize: 15 }}>
                      {rowIndex + 1}
                    </TableCell>
                    {LABMAN_TABLE_COLUMNS.map((col) => (
                      <TableCell key={col.key} sx={{ py: 1.25, px: 1.25 }}>
                        {col.type === 'boolean' ? (
                          <Checkbox
                            checked={Boolean(row[col.key])}
                            onChange={(event) =>
                              setLabmanCell(rowIndex, col.key, event.target.checked)
                            }
                          />
                        ) : (
                          <TextField
                            variant="standard"
                            fullWidth
                            type={col.type === 'number' ? 'number' : 'text'}
                            {...noBrowserAutofill(`labman-${col.key}-${rowIndex}`)}
                            value={row[col.key] ?? ''}
                            onChange={(event) =>
                              setLabmanCell(rowIndex, col.key, event.target.value)
                            }
                            InputProps={{
                              disableUnderline: true,
                              sx: {
                                fontSize: 15,
                                px: 1,
                                py: 0.5,
                                borderRadius: 1,
                                bgcolor: 'transparent',
                                transition: 'background-color 0.15s ease',
                                '&:hover': { bgcolor: 'grey.100' },
                                '&.Mui-focused': { bgcolor: 'grey.100' },
                              },
                            }}
                            inputProps={{
                              style: { padding: '6px 0', fontSize: 15 },
                            }}
                          />
                        )}
                      </TableCell>
                    ))}
                    <TableCell sx={{ py: 1.25 }}>
                      <IconButton
                        aria-label="Remove sample row"
                        onClick={() => removeLabmanRow(rowIndex)}
                        sx={{ color: 'text.secondary' }}
                      >
                        <DeleteOutlineIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <Stack direction="row" spacing={1} alignItems="center">
            <Button startIcon={<AddIcon />} variant="outlined" onClick={addLabmanRow}>
              Add sample row
            </Button>
            <Button variant="outlined" onClick={runLabmanPreview} disabled={busy}>
              Preview
            </Button>
            <Button variant="contained" onClick={runLabmanSubmit} disabled={busy}>
              {busy ? <CircularProgress size={18} /> : 'Submit to Labman'}
            </Button>
          </Stack>
          <Typography variant="caption" color="text.secondary">
            Sample names become {'{project}_{index}'}. Use either target composition + precursors +
            mass, or powder dispenses as Name:mass_g pairs. Optional Labman columns can stay blank
            for defaults.
          </Typography>
          {labmanPreview && (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Preview: {labmanPreview.sample_count ?? 0} sample(s) —{' '}
                  {taskSummary(labmanPreview.experiment)}
                </Typography>
                {(labmanPreview.labman_inputfiles || []).map((entry) => (
                  <Box key={entry.sample} sx={{ mb: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      {entry.sample} → Labman InputFile
                    </Typography>
                    <Typography
                      component="pre"
                      sx={{
                        fontSize: 12,
                        bgcolor: 'grey.100',
                        p: 1,
                        borderRadius: 1,
                        overflow: 'auto',
                        maxHeight: 200,
                      }}
                    >
                      {JSON.stringify(entry.inputfile, null, 2)}
                    </Typography>
                  </Box>
                ))}
              </CardContent>
            </Card>
          )}
        </Stack>
      </TabPanel>

      <TabPanel value={tab} index={2}>
        <Alert severity="info" sx={{ mb: 2 }}>
          Run one action on one device. For full workflows (dose → heat → XRD), use Recipes — we do
          not compose novel multi-device flows from free-form text yet. For Labman-only dosing, use
          the Labman tab.
        </Alert>
        <Stack spacing={2} sx={{ maxWidth: 720 }}>
          <FormControl fullWidth size="small">
            <InputLabel>Target device</InputLabel>
            <Select
              label="Target device"
              value={deviceName}
              onChange={(event) => setDeviceName(event.target.value)}
            >
              {devices.map((device) => (
                <MenuItem key={device.name} value={device.name}>
                  {device.label || device.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {selectedDevice && (
            <Typography variant="caption" color="text.secondary">
              Task type: {selectedDevice.task_type}. {selectedDevice.help}
            </Typography>
          )}
          <TextField
            label="Request"
            placeholder="e.g. heat at 800 °C for 3 hours, crucible already inside"
            {...noBrowserAutofill('freeform-request')}
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            multiline
            minRows={3}
            fullWidth
          />
          <Divider />
          <Typography variant="subtitle2">Sample provenance (required)</Typography>
          <Stack direction="row" spacing={1}>
            <Button
              variant={sampleMode === 'existing' ? 'contained' : 'outlined'}
              onClick={() => setSampleMode('existing')}
            >
              Existing sample
            </Button>
            <Button
              variant={sampleMode === 'new' ? 'contained' : 'outlined'}
              onClick={() => setSampleMode('new')}
            >
              New sample
            </Button>
          </Stack>
          {sampleMode === 'existing' ? (
            <Stack spacing={1}>
              <Stack direction="row" spacing={1}>
                <TextField
                  size="small"
                  fullWidth
                  label="Search by name or id"
                  {...noBrowserAutofill('sample-search')}
                  value={sampleQuery}
                  onChange={(event) => setSampleQuery(event.target.value)}
                />
                <Button variant="outlined" onClick={searchSamples} disabled={busy}>
                  Search
                </Button>
              </Stack>
              {sampleHits.map((hit) => (
                <Card
                  key={hit.sample_id}
                  variant={selectedSample?.sample_id === hit.sample_id ? 'outlined' : 'elevation'}
                  sx={{
                    borderColor:
                      selectedSample?.sample_id === hit.sample_id ? 'primary.main' : undefined,
                    borderWidth: selectedSample?.sample_id === hit.sample_id ? 2 : undefined,
                  }}
                >
                  <CardActionArea onClick={() => setSelectedSample(hit)}>
                    <CardContent sx={{ py: 1.5 }}>
                      <Typography variant="body2">
                        {hit.name}{' '}
                        <Typography component="span" variant="caption" color="text.secondary">
                          {hit.sample_id}
                        </Typography>
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        position: {hit.position || '—'}
                      </Typography>
                    </CardContent>
                  </CardActionArea>
                </Card>
              ))}
            </Stack>
          ) : (
            <Stack spacing={1}>
              <TextField
                size="small"
                label="New sample name"
                {...noBrowserAutofill('new-sample-name')}
                value={newSampleName}
                onChange={(event) => setNewSampleName(event.target.value)}
                fullWidth
              />
              <TextField
                size="small"
                label="Tags (comma-separated)"
                {...noBrowserAutofill('new-sample-tags')}
                value={newSampleTags}
                onChange={(event) => setNewSampleTags(event.target.value)}
                fullWidth
              />
            </Stack>
          )}
          <FormControlLabel
            control={
              <Switch checked={assertPlaced} onChange={(event) => setAssertPlaced(event.target.checked)} />
            }
            label="Sample is already on this device (operator-asserted placement)"
          />
          {assertPlaced && (
            <TextField
              size="small"
              label="Position (optional)"
              placeholder="e.g. BFT_box_d/slot/3"
              {...noBrowserAutofill('placement-position')}
              value={placementPosition}
              onChange={(event) => setPlacementPosition(event.target.value)}
              fullWidth
            />
          )}
          <Button variant="contained" onClick={startFreeform} disabled={busy}>
            {busy && !draft ? <CircularProgress size={18} sx={{ mr: 1 }} /> : null}
            Propose single-device draft
          </Button>
          {freeformJob && (
            <Typography variant="caption" color="text.secondary">
              Job {freeformJob.id}: {freeformJob.status}
            </Typography>
          )}
          {draft && (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Draft
                </Typography>
                <Typography variant="body2" sx={{ mb: 1 }}>
                  {taskSummary(draft.experiment)}
                </Typography>
                <Typography
                  component="pre"
                  sx={{
                    fontSize: 12,
                    bgcolor: 'grey.100',
                    p: 1,
                    borderRadius: 1,
                    overflow: 'auto',
                    maxHeight: 240,
                  }}
                >
                  {JSON.stringify(draft.experiment, null, 2)}
                </Typography>
                <Button sx={{ mt: 1 }} variant="contained" onClick={confirmFreeform} disabled={busy}>
                  Confirm & submit
                </Button>
              </CardContent>
            </Card>
          )}
        </Stack>
      </TabPanel>

      <Dialog
        open={Boolean(selectedRecipe)}
        onClose={() => !busy && setSelectedRecipe(null)}
        fullWidth
        maxWidth={selectedRecipe?.samples_table ? 'lg' : 'md'}
      >
        <DialogTitle>{selectedRecipe?.title}</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {selectedRecipe?.description}
          </Typography>
          <Stack
            component="form"
            autoComplete="off"
            spacing={2}
            onSubmit={(event) => event.preventDefault()}
          >
            {(selectedRecipe?.fields || []).map(renderRecipeField)}
            {selectedRecipe?.samples_table ? (
              <>
                <Typography variant="body2" color="text.secondary">
                  One row per sample — add rows for a batch, or leave a single row for one sample.
                  Names become {'{project}_{index}'}.
                </Typography>
                <TableContainer
                  component={Paper}
                  variant="outlined"
                  sx={{
                    maxWidth: '100%',
                    borderRadius: 2,
                    borderColor: 'divider',
                    boxShadow: 'none',
                  }}
                >
                  <Table
                    stickyHeader
                    size="small"
                    sx={{
                      minWidth: Math.max(720, recipeSampleColumns.length * 120),
                      '& .MuiTableCell-root': { borderColor: 'divider' },
                      '& .MuiTableBody-root .MuiTableRow-root:hover': {
                        backgroundColor: 'action.hover',
                      },
                    }}
                  >
                    <TableHead>
                      <TableRow>
                        <TableCell
                          sx={{
                            width: 48,
                            bgcolor: 'grey.50',
                            fontWeight: 600,
                            fontSize: 13,
                            color: 'text.secondary',
                          }}
                        >
                          #
                        </TableCell>
                        {recipeSampleColumns.map((col) => (
                          <TableCell
                            key={col.name}
                            sx={{
                              minWidth: col.width || 120,
                              bgcolor: 'grey.50',
                              fontWeight: 600,
                              fontSize: 13,
                              color: 'text.secondary',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            <ColumnHeaderLabel label={col.label} help={col.help} />
                          </TableCell>
                        ))}
                        <TableCell sx={{ width: 48, bgcolor: 'grey.50' }} />
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {recipeSampleRows.map((row, rowIndex) => (
                        <TableRow key={`recipe-sample-row-${rowIndex}`}>
                          <TableCell sx={{ color: 'text.secondary', fontSize: 14 }}>
                            {rowIndex + 1}
                          </TableCell>
                          {recipeSampleColumns.map((col) => {
                            const autofill = noBrowserAutofill(
                              `recipe-${selectedRecipe.id}-${col.name}-${rowIndex}`,
                            );
                            if (col.type === 'boolean') {
                              return (
                                <TableCell key={col.name} sx={{ py: 1, px: 1 }}>
                                  <Checkbox
                                    checked={Boolean(row[col.name])}
                                    onChange={(event) =>
                                      setRecipeSampleCell(
                                        rowIndex,
                                        col.name,
                                        event.target.checked,
                                      )
                                    }
                                  />
                                </TableCell>
                              );
                            }
                            return (
                              <TableCell key={col.name} sx={{ py: 1, px: 1 }}>
                                <TextField
                                  variant="standard"
                                  fullWidth
                                  type={col.type === 'number' ? 'number' : 'text'}
                                  name={autofill.name}
                                  autoComplete={autofill.autoComplete}
                                  value={row[col.name] ?? ''}
                                  onChange={(event) =>
                                    setRecipeSampleCell(rowIndex, col.name, event.target.value)
                                  }
                                  InputProps={{
                                    disableUnderline: true,
                                    sx: {
                                      fontSize: 14,
                                      px: 1,
                                      py: 0.5,
                                      borderRadius: 1,
                                      '&:hover': { bgcolor: 'grey.100' },
                                      '&.Mui-focused': { bgcolor: 'grey.100' },
                                    },
                                  }}
                                  inputProps={{
                                    ...autofill.inputProps,
                                    style: { padding: '4px 0', fontSize: 14 },
                                  }}
                                />
                              </TableCell>
                            );
                          })}
                          <TableCell>
                            <IconButton
                              aria-label="Remove sample row"
                              onClick={() => removeRecipeSampleRow(rowIndex)}
                              sx={{ color: 'text.secondary' }}
                            >
                              <DeleteOutlineIcon />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
                <Button startIcon={<AddIcon />} variant="outlined" onClick={addRecipeSampleRow}>
                  Add sample row
                </Button>
              </>
            ) : null}
            {preview && (
              <Alert severity="info">
                Preview: {preview.sample_count ?? preview.experiment?.samples?.length ?? 0} sample(s).{' '}
                {taskSummary(preview.experiment)}
              </Alert>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedRecipe(null)} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={runPreview} disabled={busy}>
            Preview
          </Button>
          <Button variant="contained" onClick={runSubmit} disabled={busy}>
            {busy ? <CircularProgress size={18} /> : 'Submit'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
