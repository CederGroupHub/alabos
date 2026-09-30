import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import {
  confirm_freeform_submission,
  create_freeform_job,
  create_submission_sample,
  get_freeform_devices,
  get_freeform_job,
  get_submission_recipes,
  preview_submission_recipe,
  resolve_submission_samples,
  submit_submission_recipe,
} from '../../api_routes';

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
  const [csvText, setCsvText] = useState('');
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
    setCsvText('');
  };

  const setField = (name, value) => {
    setFormValues((prev) => ({ ...prev, [name]: value }));
  };

  const buildPayload = () => {
    const payload = { ...formValues };
    if (selectedRecipe?.supports_csv && csvText.trim()) {
      payload.csv_text = csvText;
    }
    // Coerce numeric fields
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
        Guided recipes for known multi-device workflows, or free-form single-device runs with sample
        provenance.
      </Typography>

      {message && (
        <Alert severity={message.severity} sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message.text}
        </Alert>
      )}

      <Tabs value={tab} onChange={(_, value) => setTab(value)}>
        <Tab label="Recipes" />
        <Tab label="Free-form (one device)" />
      </Tabs>

      <TabPanel value={tab} index={0}>
        {recipesError && <Alert severity="error">{recipesError}</Alert>}
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} useFlexGap flexWrap="wrap">
          {recipes.map((recipe) => (
            <Card key={recipe.id} sx={{ width: 280 }}>
              <CardActionArea onClick={() => openRecipe(recipe)}>
                <CardContent>
                  <Typography variant="subtitle1">{recipe.title}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {recipe.description}
                  </Typography>
                  <Stack direction="row" spacing={0.5} sx={{ mt: 1 }} useFlexGap flexWrap="wrap">
                    {(recipe.task_chain || []).map((task) => (
                      <Chip key={task} size="small" label={task} />
                    ))}
                  </Stack>
                </CardContent>
              </CardActionArea>
            </Card>
          ))}
        </Stack>
      </TabPanel>

      <TabPanel value={tab} index={1}>
        <Alert severity="info" sx={{ mb: 2 }}>
          Run one action on one device. For full workflows (dose → heat → XRD), use Recipes — we do
          not compose novel multi-device flows from free-form text yet.
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
                value={newSampleName}
                onChange={(event) => setNewSampleName(event.target.value)}
                fullWidth
              />
              <TextField
                size="small"
                label="Tags (comma-separated)"
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
        maxWidth="md"
      >
        <DialogTitle>{selectedRecipe?.title}</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {selectedRecipe?.description}
          </Typography>
          <Stack spacing={2}>
            {(selectedRecipe?.fields || []).map(renderRecipeField)}
            {selectedRecipe?.supports_csv && (
              <TextField
                label="CSV (optional, same columns as notebook)"
                value={csvText}
                onChange={(event) => setCsvText(event.target.value)}
                multiline
                minRows={4}
                fullWidth
                helperText={selectedRecipe.csv_help}
              />
            )}
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
