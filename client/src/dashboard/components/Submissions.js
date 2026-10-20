import React, { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
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
  get_labman_loaded_powders,
  get_sample_position_racks,
  get_submission_recipes,
  preview_submission_workflow,
  resolve_submission_samples,
  submit_submission_workflow,
} from '../../api_routes';

function flattenPositionOptions(racks = []) {
  const options = [];
  racks.forEach((rack) => {
    Object.values(rack.slot_groups || {}).forEach((slots) => {
      (slots || []).forEach((slot) => {
        if (!slot?.name) {
          return;
        }
        const sampleName = slot.sample?.name;
        options.push({
          name: slot.name,
          device_name: rack.device_name,
          status: slot.status,
          sampleName: sampleName || null,
          label: sampleName
            ? `${slot.name} (${sampleName})`
            : `${slot.name}${slot.status === 'OCCUPIED' ? ' (occupied)' : ''}`,
        });
      });
    });
  });
  return options.sort((a, b) => a.name.localeCompare(b.name));
}

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

const STAGE_DEFS = [
  {
    key: 'powder_dosing',
    label: 'Powder dosing (Labman)',
    help:
      'Labman weighs and doses precursors into a crucible (composition, mass, ethanol, mix, dry, transfer). Use this to make a new sample. Cannot be combined with Starting position.',
  },
  {
    key: 'starting',
    label: 'Starting position',
    help:
      'Sample already exists on a rack or device — you only declare its starting position (e.g. BFT_input_rack/slot/3). Use instead of Powder dosing when nothing needs to be dosed.',
  },
  {
    key: 'heating',
    label: 'Furnace heating',
    help:
      'Heat the sample in a furnace (temperature, hold time, ramp/cooling). Requires Powder dosing or Starting so the lab knows where the crucible comes from.',
  },
  {
    key: 'recover_powder',
    label: 'Recover powder',
    help:
      'Recover powder from the crucible into a vial (grind/dump path). Needed after Heating before Diffraction unless you use a filled-vial (assume clean) XRD path.',
  },
  {
    key: 'diffraction',
    label: 'Diffraction',
    help:
      'Run powder XRD (Aeris). After Heating, Recover is required unless the sample is already a filled vial with “assume clean” enabled.',
  },
  {
    key: 'ending',
    label: 'Ending',
    help:
      'Finish the workflow: optionally print and verify a QR label on the vial (“Label vial at ending”), then put the sample away in storage / return slot so it leaves the active lab path cleanly. Skip if you only want intermediate results and will continue later.',
  },
];

const STAGE_TASK = {
  powder_dosing: 'PowderDosing',
  starting: 'Starting',
  heating: 'Heating',
  recover_powder: 'RecoverPowder',
  diffraction: 'Diffraction',
  ending: 'Ending',
};

const FALLBACK_BATCH_FIELDS = [
  { name: 'name', label: 'Batch name', type: 'text', default: 'workflow_batch' },
  { name: 'label_vial', label: 'Label vial at ending', type: 'boolean', default: true },
  {
    name: 'assume_clean',
    label: 'Assume clean XRD holder (filled vial)',
    type: 'boolean',
    default: false,
  },
  { name: 'skip_sample_scan', label: 'Skip sample scan', type: 'boolean', default: false },
  {
    name: 'heating_mode',
    label: 'Furnace heating mode',
    type: 'select',
    options: ['single', 'multi'],
    default: 'single',
  },
];

const DEFAULT_INPUTFILE = {
  ethanol_volume_ul: 10000,
  drying_duration_second: 7200,
  mixer_speed_rpm: 2000,
  mixer_duration_s: 540,
  transfer_volume_ul: 10000,
  min_transfer_mass_g: 5,
  replicates: 1,
  allow_replicates: true,
};

function emptyStages() {
  return Object.fromEntries(STAGE_DEFS.map((s) => [s.key, false]));
}

function defaultStages() {
  return {
    ...emptyStages(),
    powder_dosing: true,
    ending: true,
  };
}

function taskChainFromStages(stages) {
  return STAGE_DEFS.filter((s) => stages[s.key]).map((s) => STAGE_TASK[s.key]);
}

function hasStartPath(stages) {
  return Boolean(stages.powder_dosing || stages.starting);
}

function stageDisabledReason(key, stages) {
  if (key === 'heating' && !hasStartPath(stages)) {
    return 'Enable Powder dosing or Starting first.';
  }
  if (key === 'recover_powder' && !hasStartPath(stages)) {
    return 'Enable Powder dosing or Starting first.';
  }
  return '';
}

function joinHintText(stages) {
  const hints = [];
  if (!hasStartPath(stages)) {
    hints.push('Choose Powder dosing or Starting position.');
  }
  if (stages.heating && stages.diffraction && !stages.recover_powder) {
    hints.push('Diffraction after Heating needs Recover (auto-enabled when Diffraction is turned on).');
  }
  if (stages.powder_dosing && stages.starting) {
    hints.push('Use either Powder dosing or Starting, not both.');
  }
  if (!hints.length) {
    return 'Heating and Recover need a start stage; Diffraction after Heating requires Recover. Filled-vial (assume clean) turns Recover off.';
  }
  return hints.join(' ');
}

function formatErrors(errors) {
  if (Array.isArray(errors)) {
    return errors.join(' ');
  }
  return String(errors || 'Request failed');
}

function HelpHintIcon({ help }) {
  if (!help) {
    return null;
  }
  return (
    <Tooltip title={help} arrow placement="top" enterDelay={200}>
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

function formatColumnHelp(help, min, max) {
  const parts = [];
  if (help) {
    parts.push(String(help));
  }
  const hasMin = min != null && min !== '';
  const hasMax = max != null && max !== '';
  if (hasMin || hasMax) {
    if (hasMin && hasMax) {
      parts.push(`Allowed range: ${min} to ${max}.`);
    } else if (hasMin) {
      parts.push(`Minimum: ${min}.`);
    } else {
      parts.push(`Maximum: ${max}.`);
    }
  }
  return parts.join(' ');
}

function ColumnHeaderLabel({ label, help, min, max }) {
  const tip = formatColumnHelp(help, min, max);
  if (!tip) {
    return label;
  }
  return (
    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ display: 'inline-flex' }}>
      <span>{label}</span>
      <HelpHintIcon help={tip} />
    </Stack>
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

function emptyRecipeSampleRow(columns = [], overrides = {}) {
  const row = {};
  columns.forEach((col) => {
    if (col.type === 'boolean') {
      row[col.name] = col.default !== undefined ? col.default : false;
    } else if (col.type === 'powder_multi_select' || col.type === 'string_list') {
      if (Array.isArray(col.default)) {
        row[col.name] = [...col.default];
      } else if (col.default != null && String(col.default).trim()) {
        row[col.name] = String(col.default)
          .split(',')
          .map((part) => part.trim())
          .filter(Boolean);
      } else {
        row[col.name] = [];
      }
    } else if (col.default !== undefined && col.default !== null) {
      row[col.name] = String(col.default);
    } else {
      row[col.name] = '';
    }
  });
  return { ...row, ...overrides };
}

function coerceRecipeSampleRows(rows, columns) {
  const samples = [];
  rows.forEach((row, rowIndex) => {
    if (!String(row.project_name || '').trim() || !String(row.sample_index || '').trim()) {
      return;
    }
    const sample = {};
    const prefix = `Row ${rowIndex + 1}: `;
    columns.forEach((col) => {
      const raw = row[col.name];
      if (col.type === 'boolean') {
        sample[col.name] = Boolean(raw);
        return;
      }
      if (col.type === 'number') {
        if (raw === '' || raw == null) {
          return;
        }
        const value = Number(raw);
        if (Number.isNaN(value)) {
          throw new Error(`${prefix}${col.label || col.name} must be a number.`);
        }
        if (col.min != null && value < Number(col.min)) {
          throw new Error(`${prefix}${col.label || col.name} must be ≥ ${col.min}.`);
        }
        if (col.max != null && value > Number(col.max)) {
          throw new Error(`${prefix}${col.label || col.name} must be ≤ ${col.max}.`);
        }
        sample[col.name] = value;
        return;
      }
      if (col.type === 'string_list' || col.type === 'powder_multi_select') {
        const list = Array.isArray(raw)
          ? raw.map((part) => String(part).trim()).filter(Boolean)
          : String(raw ?? '')
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
    samples.push(sample);
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

function buildColumnsForStages(nextStages, recipes, presetColumns = []) {
  const nameCols = ['project_name', 'sample_index'];
  const dosingCols = [
    'target_composition',
    'precursors',
    'target_mass_g',
    'powder_dispenses_text',
    'ethanol_volume_ul',
    'drying_duration_second',
    'mixer_speed_rpm',
    'mixer_duration_s',
    'transfer_volume_ul',
    'min_transfer_mass_g',
    'replicates',
    'allow_replicates',
  ];
  const startCols = ['position'];
  const heatCols = [
    'heating_temperature_c',
    'heating_duration_minutes',
    'ramping_rate_c_per_min',
    'cooling_rate_c_per_min',
  ];
  const wanted = new Set(nameCols);
  if (nextStages.powder_dosing) dosingCols.forEach((k) => wanted.add(k));
  if (nextStages.starting) startCols.forEach((k) => wanted.add(k));
  if (nextStages.heating) heatCols.forEach((k) => wanted.add(k));

  const catalogCols = {};
  recipes.forEach((r) => {
    (r.sample_columns || []).forEach((c) => {
      catalogCols[c.name] = c;
    });
    Object.entries(r.inputfile_defaults || {}).forEach(([key, value]) => {
      if (!catalogCols[key]) {
        catalogCols[key] = {
          name: key,
          label: key,
          type: typeof value === 'boolean' ? 'boolean' : 'number',
          default: value,
        };
      }
    });
  });
  Object.entries(DEFAULT_INPUTFILE).forEach(([key, value]) => {
    if (!catalogCols[key]) {
      catalogCols[key] = {
        name: key,
        label: key,
        type: typeof value === 'boolean' ? 'boolean' : 'number',
        default: value,
      };
    }
  });
  (presetColumns || []).forEach((c) => {
    catalogCols[c.name] = c;
  });

  const order = [...nameCols, ...dosingCols, ...startCols, ...heatCols];
  const cols = [...wanted]
    .map((name) => catalogCols[name])
    .filter(Boolean)
    .sort((a, b) => order.indexOf(a.name) - order.indexOf(b.name));
  return cols;
}

export default function Submissions() {
  const [tab, setTab] = useState(0);
  const [recipes, setRecipes] = useState([]);
  const [recipesError, setRecipesError] = useState('');
  const [presetId, setPresetId] = useState('powder_dosing_only');
  const [builderReady, setBuilderReady] = useState(false);
  const [formValues, setFormValues] = useState({});
  const [recipeSampleRows, setRecipeSampleRows] = useState([]);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);
  const [freeformMessage, setFreeformMessage] = useState(null);
  const freeformMessageRef = useRef(null);

  const [devices, setDevices] = useState([]);
  const [deviceName, setDeviceName] = useState('');
  const [prompt, setPrompt] = useState('');
  const [sampleMode, setSampleMode] = useState('existing');
  const [sampleQuery, setSampleQuery] = useState('');
  const [sampleHits, setSampleHits] = useState([]);
  const [selectedSample, setSelectedSample] = useState(null);
  const [newSampleName, setNewSampleName] = useState('');
  const [newSampleTags, setNewSampleTags] = useState('');
  const [placementPosition, setPlacementPosition] = useState(null);
  const [positionOptions, setPositionOptions] = useState([]);
  const [freeformJob, setFreeformJob] = useState(null);
  const [draft, setDraft] = useState(null);

  const [stages, setStages] = useState(defaultStages);
  const [stageColumns, setStageColumns] = useState([]);
  const [validationErrors, setValidationErrors] = useState([]);
  const [rowsToAdd, setRowsToAdd] = useState(10);
  const [loadedPowders, setLoadedPowders] = useState([]);
  const [loadedPowdersError, setLoadedPowdersError] = useState('');
  const [loadedPowdersLoading, setLoadedPowdersLoading] = useState(false);

  const refreshLoadedPowders = async () => {
    setLoadedPowdersLoading(true);
    try {
      const data = await get_labman_loaded_powders();
      if (data?.status === 'success') {
        setLoadedPowders(data.powders || []);
        setLoadedPowdersError('');
      } else {
        setLoadedPowders([]);
        setLoadedPowdersError(
          String(data?.errors || data?.error || 'Could not load Labman powders'),
        );
      }
    } catch (err) {
      setLoadedPowders([]);
      setLoadedPowdersError(String(err?.message || err));
    } finally {
      setLoadedPowdersLoading(false);
    }
  };

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
      try {
        const data = await get_sample_position_racks();
        if (!cancelled && data?.status === 'success') {
          setPositionOptions(flattenPositionOptions(data.racks || []));
        }
      } catch {
        /* position picker optional if racks API unavailable */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [deviceName]);

  const freeformPositionOptions = useMemo(() => {
    if (!deviceName) {
      return positionOptions;
    }
    const forDevice = positionOptions.filter(
      (opt) =>
        opt.device_name === deviceName || opt.name.startsWith(`${deviceName}/`),
    );
    return forDevice.length ? forDevice : positionOptions;
  }, [positionOptions, deviceName]);

  const selectedDevice = useMemo(
    () => devices.find((entry) => entry.name === deviceName) || null,
    [devices, deviceName],
  );

  const selectedPreset = useMemo(
    () => recipes.find((r) => r.id === presetId) || null,
    [recipes, presetId],
  );

  useEffect(() => {
    if (stages.powder_dosing) {
      refreshLoadedPowders();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stages.powder_dosing]);

  const batchFields = useMemo(() => {
    const byName = {};
    FALLBACK_BATCH_FIELDS.forEach((f) => {
      byName[f.name] = f;
    });
    (selectedPreset?.fields || []).forEach((f) => {
      if (f.name === 'advanced_place') {
        return;
      }
      byName[f.name] = f;
    });
    delete byName.advanced_place;
    return Object.values(byName);
  }, [selectedPreset]);

  const applyStages = (nextStages, { rows } = {}) => {
    setStages(nextStages);
    setPreview(null);
    setValidationErrors([]);
    const cols = buildColumnsForStages(
      nextStages,
      recipes,
      selectedPreset?.sample_columns || [],
    );
    setStageColumns(cols);
    setRecipeSampleRows((prev) => {
      const source = rows || (prev.length ? prev : [{}]);
      return source.map((row) => emptyRecipeSampleRow(cols, row));
    });
  };

  const applyPreset = (recipe) => {
    if (!recipe) {
      return;
    }
    setPresetId(recipe.id);
    setPreview(null);
    setMessage(null);
    setValidationErrors([]);
    const nextStages = { ...emptyStages(), ...(recipe.stages || {}) };
    const defaults = {};
    (recipe.fields || FALLBACK_BATCH_FIELDS).forEach((field) => {
      if (field.default !== undefined) {
        defaults[field.name] = field.default;
      } else if (field.type === 'boolean') {
        defaults[field.name] = false;
      } else {
        defaults[field.name] = '';
      }
    });
    if (!defaults.name) {
      defaults.name = recipe.id;
    }
    setFormValues(defaults);
    setStages(nextStages);
    const cols =
      recipe.sample_columns?.length
        ? recipe.sample_columns
        : buildColumnsForStages(nextStages, recipes, recipe.sample_columns || []);
    setStageColumns(cols);
    setRecipeSampleRows([emptyRecipeSampleRow(cols)]);
  };

  const clearStages = () => {
    setPresetId('');
    setPreview(null);
    setValidationErrors([]);
    setFormValues({ name: 'workflow_batch', label_vial: true });
    applyStages(emptyStages(), { rows: [{}] });
  };

  useEffect(() => {
    if (!recipes.length || builderReady) {
      return;
    }
    const preset =
      recipes.find((r) => r.id === 'powder_dosing_only') || recipes[0];
    applyPreset(preset);
    setBuilderReady(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recipes, builderReady]);

  const toggleStage = (key, checked) => {
    const next = { ...stages, [key]: checked };
    if (key === 'powder_dosing' && checked) {
      next.starting = false;
    }
    if (key === 'starting' && checked) {
      next.powder_dosing = false;
    }
    if (key === 'diffraction' && checked && next.heating && !next.recover_powder) {
      if (!formValues.assume_clean) {
        next.recover_powder = true;
      }
    }
    if (key === 'recover_powder' && checked && formValues.assume_clean) {
      setFormValues((prev) => ({ ...prev, assume_clean: false }));
    }
    if (!hasStartPath(next)) {
      next.heating = false;
      next.recover_powder = false;
    }
    applyStages(next);
  };

  const setField = (name, value) => {
    if (name === 'assume_clean' && value && stages.recover_powder) {
      applyStages({ ...stages, recover_powder: false });
    }
    setFormValues((prev) => ({ ...prev, [name]: value }));
  };

  const recipeSampleColumns = stageColumns;

  const setRecipeSampleCell = (rowIndex, key, value) => {
    setRecipeSampleRows((prev) =>
      prev.map((row, idx) => (idx === rowIndex ? { ...row, [key]: value } : row)),
    );
  };

  const addRecipeSampleRows = (count = 1) => {
    const n = Math.min(500, Math.max(1, Math.floor(Number(count) || 1)));
    setRecipeSampleRows((prev) => [
      ...prev,
      ...Array.from({ length: n }, () => emptyRecipeSampleRow(recipeSampleColumns)),
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
    return {
      name: formValues.name || presetId || 'workflow_batch',
      preset_id: presetId || undefined,
      stages: { ...stages },
      samples: coerceRecipeSampleRows(recipeSampleRows, recipeSampleColumns),
      ending: { label_vial: Boolean(formValues.label_vial) },
      diffraction: {
        assume_clean: Boolean(formValues.assume_clean),
        skip_sample_scan: Boolean(formValues.skip_sample_scan),
      },
      heating: {
        mode: formValues.heating_mode === 'multi' ? 'multi' : 'single',
      },
      label_vial: Boolean(formValues.label_vial),
      assume_clean: Boolean(formValues.assume_clean),
      skip_sample_scan: Boolean(formValues.skip_sample_scan),
      heating_mode: formValues.heating_mode === 'multi' ? 'multi' : 'single',
    };
  };

  const runPreview = async () => {
    setBusy(true);
    setMessage(null);
    setValidationErrors([]);
    try {
      const data = await preview_submission_workflow(buildPayload());
      if (data.status === 'error') {
        const errs = data.errors || data.error || 'Preview failed';
        setValidationErrors(Array.isArray(errs) ? errs : [String(errs)]);
        setMessage({ severity: 'error', text: formatErrors(errs) });
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
    setBusy(true);
    setMessage(null);
    setValidationErrors([]);
    try {
      const data = await submit_submission_workflow(buildPayload());
      if (data.status === 'error') {
        const errs = data.errors || data.error || 'Submit failed';
        setValidationErrors(Array.isArray(errs) ? errs : [String(errs)]);
        setMessage({ severity: 'error', text: formatErrors(errs) });
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
    if (!placementPosition) {
      throw new Error('Select the sample’s current position from the list.');
    }
    const created = await create_submission_sample({
      name: newSampleName.trim(),
      tags,
      position: placementPosition,
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
    setFreeformMessage(null);
    setDraft(null);
    try {
      const sample = await ensureSampleId();
      if (!deviceName) {
        throw new Error('Pick a target device.');
      }
      if (!prompt.trim()) {
        throw new Error('Enter a free-form request.');
      }
      if (!placementPosition) {
        throw new Error('Select where the sample is right now (searchable position list).');
      }
      const body = {
        prompt: prompt.trim(),
        device_name: deviceName,
        sample_id: sample.sample_id,
        sample_name: sample.sample_name,
        reuse_existing: sample.reuse_existing,
        physical_placement: {
          operator_asserted: true,
          position: placementPosition,
        },
      };
      const job = await create_freeform_job(body);
      if (job.status === 'error' || job.http_status >= 400) {
        throw new Error(job.errors || job.error || 'Could not start free-form job');
      }
      setFreeformJob(job);
    } catch (err) {
      setFreeformMessage({ severity: 'error', text: String(err?.message || err) });
      setBusy(false);
    }
  };

  useEffect(() => {
    if (!freeformMessage) {
      return undefined;
    }
    freeformMessageRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    return undefined;
  }, [freeformMessage]);

  useEffect(() => {
    if (!freeformJob?.id) {
      return undefined;
    }
    if (freeformJob.status === 'succeeded' || freeformJob.status === 'failed') {
      setBusy(false);
      if (freeformJob.status === 'succeeded') {
        setDraft(freeformJob.draft || null);
        setFreeformMessage(null);
      } else {
        setFreeformMessage({
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
    setFreeformMessage(null);
    try {
      const data = await confirm_freeform_submission({
        experiment: draft.experiment,
        job_id: freeformJob?.id,
      });
      if (data.status === 'error') {
        throw new Error(data.errors || data.error || 'Confirm failed');
      }
      const expId = data.data?.exp_id || data.exp_id;
      setFreeformMessage({
        severity: 'success',
        text: `Submitted experiment ${expId}. Open Experiments to track it.`,
      });
      setDraft(null);
      setFreeformJob(null);
    } catch (err) {
      setFreeformMessage({ severity: 'error', text: String(err?.message || err) });
    } finally {
      setBusy(false);
    }
  };

  const renderRecipeField = (field) => {
    if (field.type === 'boolean') {
      const helper =
        field.name === 'assume_clean'
          ? 'Turns Recover off when enabled (filled vial).'
          : null;
      return (
        <Box key={field.name}>
          <FormControlLabel
            control={
              <Switch
                checked={Boolean(formValues[field.name])}
                onChange={(event) => setField(field.name, event.target.checked)}
              />
            }
            label={field.label}
          />
          {helper ? (
            <Typography variant="caption" color="text.secondary" display="block" sx={{ ml: 6 }}>
              {helper}
            </Typography>
          ) : null}
        </Box>
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

  const visibleBatchFields = batchFields.filter((field) => {
    if (field.name === 'label_vial') return stages.ending;
    if (['assume_clean', 'skip_sample_scan'].includes(field.name)) {
      return stages.diffraction;
    }
    if (field.name === 'heating_mode') return stages.heating;
    return true;
  });

  const chain = taskChainFromStages(stages);
  const needsSampleTable = Boolean(
    stages.powder_dosing || stages.starting || stages.heating,
  );

  return (
    <Box sx={{ p: 3, maxWidth: 1100 }}>
      <Typography variant="h5" gutterBottom>
        Submissions
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Build a workflow from stages (Powder dosing, Heating, Recover, XRD, Ending). Optionally load a
        preset to pre-fill stages and columns.
      </Typography>

      {tab === 0 && message && (
        <Alert severity={message.severity} sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message.text}
        </Alert>
      )}

      <Tabs value={tab} onChange={(_, value) => setTab(value)}>
        <Tab label="Recipes" />
        <Tab label="Free-form (one device)" />
      </Tabs>

      <TabPanel value={tab} index={0}>
        {recipesError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {recipesError}
          </Alert>
        )}

        <Stack spacing={2}>
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={1}
            alignItems={{ sm: 'center' }}
          >
            <FormControl size="small" sx={{ minWidth: 280, flex: 1 }}>
              <InputLabel>Load preset</InputLabel>
              <Select
                label="Load preset"
                value={presetId || ''}
                onChange={(event) => {
                  const id = event.target.value;
                  if (!id) {
                    clearStages();
                    return;
                  }
                  const recipe = recipes.find((r) => r.id === id);
                  if (recipe) {
                    applyPreset(recipe);
                  }
                }}
              >
                {recipes.map((recipe) => (
                  <MenuItem key={recipe.id} value={recipe.id}>
                    {recipe.title}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button variant="outlined" onClick={clearStages} disabled={busy}>
              Clear stages
            </Button>
          </Stack>
          {selectedPreset?.description ? (
            <Typography variant="body2" color="text.secondary">
              {selectedPreset.description}
            </Typography>
          ) : null}

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
                  md: 'repeat(3, minmax(0, 1fr))',
                },
                gap: 1,
                mb: 1,
              }}
            >
              {STAGE_DEFS.map((stage) => {
                const disabledReason = stageDisabledReason(stage.key, stages);
                const control = (
                  <FormControlLabel
                    disabled={Boolean(disabledReason)}
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
                        disabled={Boolean(disabledReason)}
                        onChange={(event) => toggleStage(stage.key, event.target.checked)}
                      />
                    }
                    label={<StageCheckboxLabel label={stage.label} help={stage.help} />}
                  />
                );
                if (disabledReason) {
                  return (
                    <Tooltip key={stage.key} title={disabledReason} arrow>
                      <Box sx={{ width: '100%' }}>{control}</Box>
                    </Tooltip>
                  );
                }
                return <Box key={stage.key}>{control}</Box>;
              })}
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
              {chain.length ? (
                chain.map((task, index) => (
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
                ))
              ) : (
                <Typography variant="body2" color="text.secondary" component="span">
                  (none)
                </Typography>
              )}
            </Stack>
            <Typography variant="caption" color="text.secondary" display="block">
              {joinHintText(stages)}
            </Typography>
          </Box>

          {validationErrors.length > 0 && (
            <Alert severity="error">
              {validationErrors.map((err) => (
                <Typography key={err} variant="body2">
                  {err}
                </Typography>
              ))}
            </Alert>
          )}

          <Stack
            component="form"
            autoComplete="off"
            spacing={2}
            onSubmit={(event) => event.preventDefault()}
          >
            {visibleBatchFields.map(renderRecipeField)}

            {needsSampleTable && recipeSampleColumns.length ? (
              <>
                <Typography variant="body2" color="text.secondary">
                  One row per sample — add rows for a batch, or leave a single row for one sample.
                  Names become {'{project}_{index}'}.
                </Typography>
                {stages.powder_dosing && (
                  <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                    <Typography variant="body2" color="text.secondary">
                      Precursors: select from powders loaded on Labman
                      {loadedPowdersLoading
                        ? ' (loading…)'
                        : ` (${loadedPowders.length} available)`}
                      .
                    </Typography>
                    <Button size="small" onClick={refreshLoadedPowders} disabled={loadedPowdersLoading}>
                      Refresh powders
                    </Button>
                    {loadedPowdersError && (
                      <Alert severity="warning" sx={{ py: 0, flex: '1 1 100%' }}>
                        {loadedPowdersError}
                      </Alert>
                    )}
                  </Stack>
                )}
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
                      borderCollapse: 'separate',
                      '& .MuiTableCell-root': {
                        borderColor: 'divider',
                        borderRight: '1px solid',
                        borderRightColor: 'divider',
                      },
                      '& .MuiTableCell-root:last-of-type': {
                        borderRight: 'none',
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
                            <ColumnHeaderLabel
                              label={col.label}
                              help={col.help}
                              min={col.min}
                              max={col.max}
                            />
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
                              `recipe-${presetId || 'custom'}-${col.name}-${rowIndex}`,
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
                            if (col.type === 'powder_multi_select') {
                              const selected = Array.isArray(row[col.name])
                                ? row[col.name]
                                : String(row[col.name] || '')
                                    .split(',')
                                    .map((part) => part.trim())
                                    .filter(Boolean);
                              return (
                                <TableCell key={col.name} sx={{ py: 1, px: 1, minWidth: 220 }}>
                                  <Autocomplete
                                    multiple
                                    size="small"
                                    options={loadedPowders}
                                    value={selected}
                                    disableCloseOnSelect
                                    loading={loadedPowdersLoading}
                                    noOptionsText={
                                      loadedPowdersError
                                        ? 'Labman powders unavailable'
                                        : 'No loaded powders'
                                    }
                                    onChange={(_event, value) =>
                                      setRecipeSampleCell(rowIndex, col.name, value)
                                    }
                                    renderTags={(value, getTagProps) =>
                                      value.map((option, index) => (
                                        <Chip
                                          size="small"
                                          label={option}
                                          {...getTagProps({ index })}
                                          key={`${option}-${index}`}
                                        />
                                      ))
                                    }
                                    renderInput={(params) => (
                                      <TextField
                                        {...params}
                                        variant="standard"
                                        placeholder={selected.length ? '' : 'Select powders'}
                                        InputProps={{
                                          ...params.InputProps,
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
                                      />
                                    )}
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
                                  error={Boolean((() => {
                                    if (col.type !== 'number') return false;
                                    const raw = row[col.name];
                                    if (raw === '' || raw == null) return false;
                                    const value = Number(raw);
                                    if (Number.isNaN(value)) return true;
                                    if (col.min != null && value < Number(col.min)) return true;
                                    if (col.max != null && value > Number(col.max)) return true;
                                    return false;
                                  })())}
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
                                    ...(col.type === 'number'
                                      ? {
                                          min: col.min,
                                          max: col.max,
                                          step: col.step != null ? col.step : 'any',
                                        }
                                      : {}),
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
                <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
                  <Button
                    startIcon={<AddIcon />}
                    variant="outlined"
                    onClick={() => addRecipeSampleRows(1)}
                  >
                    Add sample row
                  </Button>
                  <TextField
                    size="small"
                    type="number"
                    label="Rows"
                    value={rowsToAdd}
                    onChange={(event) => setRowsToAdd(event.target.value)}
                    sx={{ width: 96 }}
                    {...(() => {
                      const autofill = noBrowserAutofill('rows-to-add');
                      return {
                        name: autofill.name,
                        autoComplete: autofill.autoComplete,
                        inputProps: {
                          ...autofill.inputProps,
                          min: 1,
                          max: 500,
                          step: 1,
                        },
                      };
                    })()}
                  />
                  <Button
                    variant="outlined"
                    onClick={() => addRecipeSampleRows(rowsToAdd)}
                  >
                    Add {Math.min(500, Math.max(1, Math.floor(Number(rowsToAdd) || 1)))} sample
                    rows
                  </Button>
                </Stack>
              </>
            ) : null}

            {preview && (
              <Alert severity="info">
                Preview: {preview.sample_count ?? preview.experiment?.samples?.length ?? 0}{' '}
                sample(s). {taskSummary(preview.experiment)}
              </Alert>
            )}

            <Stack direction="row" spacing={1}>
              <Button onClick={runPreview} disabled={busy} variant="outlined">
                Preview
              </Button>
              <Button variant="contained" onClick={runSubmit} disabled={busy}>
                {busy ? <CircularProgress size={18} /> : 'Submit'}
              </Button>
            </Stack>
          </Stack>
        </Stack>
      </TabPanel>

      <TabPanel value={tab} index={1}>
        <Alert severity="info" sx={{ mb: 2 }}>
          Single-device Heating only: the sample must already sit in a furnace slot you select
          below. For dose → heat → XRD (or any multi-step flow), use Recipes instead.
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
                  <CardActionArea
                    onClick={() => {
                      setSelectedSample(hit);
                      if (hit.position) {
                        setPlacementPosition(hit.position);
                        const host = String(hit.position).split('/')[0];
                        if (host && devices.some((d) => d.name === host)) {
                          setDeviceName(host);
                        }
                      }
                    }}
                  >
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
          <Divider />
          <Typography variant="subtitle2">Where is the sample now?</Typography>
          <Typography variant="caption" color="text.secondary">
            Free-form only runs a Heating task on the selected furnace — it will not move the
            crucible there. Pick the exact slot from the lab map (searchable). Selecting an
            existing sample with a known position fills this in.
          </Typography>
          <Autocomplete
            size="small"
            options={freeformPositionOptions}
            value={
              freeformPositionOptions.find((opt) => opt.name === placementPosition) ||
              (placementPosition
                ? { name: placementPosition, label: placementPosition }
                : null)
            }
            onChange={(_, option) => {
              const name = option?.name || null;
              setPlacementPosition(name);
              if (name) {
                const host = String(name).split('/')[0];
                if (host && devices.some((d) => d.name === host)) {
                  setDeviceName(host);
                }
              }
            }}
            getOptionLabel={(option) => option.label || option.name || ''}
            isOptionEqualToValue={(a, b) => a.name === b.name}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Current position"
                placeholder="Search slots…"
                required
              />
            )}
            fullWidth
          />
          <Button variant="contained" onClick={startFreeform} disabled={busy}>
            {busy && !draft ? <CircularProgress size={18} sx={{ mr: 1 }} /> : null}
            Propose single-device draft
          </Button>
          {freeformMessage && (
            <Box ref={freeformMessageRef}>
              <Alert
                severity={freeformMessage.severity}
                onClose={() => setFreeformMessage(null)}
              >
                {freeformMessage.text}
              </Alert>
            </Box>
          )}
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
    </Box>
  );
}
