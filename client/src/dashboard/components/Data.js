import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import Paper from '@mui/material/Paper';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import {
  dataDownloadHref,
  get_data_window,
  get_powder_dosing_rows,
  get_sample_summary_rows,
  get_task_outcome_rows,
} from '../../api_routes';

const ALL_FIELDS = 'all';
const PREVIEW_LIMIT = 25;

function cellText(value) {
  if (Array.isArray(value)) {
    return value.join(', ');
  }
  if (value == null) {
    return '';
  }
  return String(value);
}

function rowMatchesQuery(row, columns, query, fieldKey) {
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return true;
  }
  if (fieldKey === ALL_FIELDS) {
    return columns.some((column) => cellText(row[column.key]).toLowerCase().includes(needle));
  }
  const column = columns.find((entry) => entry.key === fieldKey);
  if (!column) {
    return false;
  }
  return cellText(row[column.key]).toLowerCase().includes(needle);
}

function filterRows(rows, columns, query, fieldKey) {
  return rows.filter((row) => rowMatchesQuery(row, columns, query, fieldKey));
}

function DataSection({
  title,
  description,
  rows,
  columns,
  downloadHref,
  loading,
  query,
  fieldKey,
}) {
  const filteredRows = useMemo(
    () => filterRows(rows, columns, query, fieldKey),
    [rows, columns, query, fieldKey],
  );
  const previewRows = filteredRows.slice(0, PREVIEW_LIMIT);
  const searching = Boolean(query.trim());
  const fieldMissing = fieldKey !== ALL_FIELDS && !columns.some((column) => column.key === fieldKey);

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 2 }}>
            <Box>
              <Typography variant="h6">{title}</Typography>
              <Typography variant="body2" color="text.secondary">{description}</Typography>
              {!loading && searching && (
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                  {fieldMissing
                    ? 'This table has no matching field for the selected search target.'
                    : `Showing ${previewRows.length} of ${filteredRows.length} match${filteredRows.length === 1 ? '' : 'es'} (of ${rows.length} this month).`}
                </Typography>
              )}
            </Box>
            <Button href={downloadHref} variant="outlined">
              Download CSV
            </Button>
          </Box>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
              <CircularProgress size={28} />
            </Box>
          ) : fieldMissing ? (
            <Typography variant="body2" color="text.secondary">
              No rows — selected field is not in this table. Choose All fields or another column.
            </Typography>
          ) : filteredRows.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              {searching
                ? 'No rows match this search for the selected month.'
                : 'No rows for this month. Try an older month or wait for new samples/tasks to complete.'}
            </Typography>
          ) : (
            <TableContainer component={Paper} sx={{ maxHeight: 320 }}>
              <Table stickyHeader size="small">
                <TableHead>
                  <TableRow>
                    {columns.map((column) => (
                      <TableCell key={column.key}>{column.label}</TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {previewRows.map((row, index) => (
                    <TableRow key={index}>
                      {columns.map((column) => (
                        <TableCell key={column.key}>
                          {cellText(row[column.key])}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

const SAMPLE_SUMMARY_COLUMNS = [
  { key: 'sample_id', label: 'Sample ID' },
  { key: 'name', label: 'Name' },
  { key: 'position', label: 'Position' },
  { key: 'last_position', label: 'Last Position' },
  { key: 'metadata_keys', label: 'Metadata Keys' },
];

const POWDER_DOSING_COLUMNS = [
  { key: 'sample_name', label: 'Sample' },
  { key: 'powder_name', label: 'Powder' },
  { key: 'target_mass', label: 'Target Mass' },
  { key: 'dose_mass', label: 'Actual Dose Mass' },
  { key: 'dose_head_position', label: 'Head Position' },
  { key: 'dose_timestamp', label: 'Dose Timestamp' },
];

const TASK_OUTCOME_COLUMNS = [
  { key: 'task_id', label: 'Task ID' },
  { key: 'type', label: 'Type' },
  { key: 'status', label: 'Status' },
  { key: 'sample_names', label: 'Samples' },
  { key: 'result_keys', label: 'Result Keys' },
];

const SEARCH_FIELD_OPTIONS = [
  { key: ALL_FIELDS, label: 'All fields' },
  ...[
    ...SAMPLE_SUMMARY_COLUMNS,
    ...POWDER_DOSING_COLUMNS,
    ...TASK_OUTCOME_COLUMNS,
  ].reduce((options, column) => {
    if (!options.some((entry) => entry.key === column.key)) {
      options.push(column);
    }
    return options;
  }, []),
];

function Data() {
  const [sampleSummary, setSampleSummary] = useState([]);
  const [powderDosing, setPowderDosing] = useState([]);
  const [taskOutcome, setTaskOutcome] = useState([]);
  const [loading, setLoading] = useState(true);
  const [windowInfo, setWindowInfo] = useState(null);
  const [month, setMonth] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchField, setSearchField] = useState(ALL_FIELDS);

  const refresh = useCallback(async (targetMonth = null) => {
    setLoading(true);
    const [windowResult, sampleSummaryResult, powderDosingResult, taskOutcomeResult] = await Promise.all([
      get_data_window(targetMonth),
      get_sample_summary_rows(targetMonth),
      get_powder_dosing_rows(targetMonth),
      get_task_outcome_rows(targetMonth),
    ]);
    const activeMonth = windowResult?.window?.month || targetMonth;
    setMonth(activeMonth);
    setWindowInfo(windowResult?.window || null);
    setSampleSummary(sampleSummaryResult?.rows || []);
    setPowderDosing(powderDosingResult?.rows || []);
    setTaskOutcome(taskOutcomeResult?.rows || []);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh(null);
  }, [refresh]);

  const goOlder = () => {
    if (!windowInfo?.older_month) {
      return;
    }
    refresh(windowInfo.older_month);
  };

  const goNewer = () => {
    if (!windowInfo?.newer_month) {
      return;
    }
    refresh(windowInfo.newer_month);
  };

  return (
    <Stack spacing={2}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Box>
          <Typography variant="h5">Data</Typography>
          <Typography variant="body2" color="text.secondary">
            Curated Mongo-backed exports for operators and experimenters.
          </Typography>
          <Typography variant="body2" color="error.main">
            This page is under active development and is not yet fully operational.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <IconButton
            aria-label="Older month"
            onClick={goOlder}
            disabled={loading || !windowInfo?.has_older}
          >
            <ChevronLeftIcon />
          </IconButton>
          <Typography variant="body1" sx={{ minWidth: 140, textAlign: 'center' }}>
            {windowInfo?.label || 'Loading...'}
          </Typography>
          <IconButton
            aria-label="Newer month"
            onClick={goNewer}
            disabled={loading || !windowInfo?.has_newer}
          >
            <ChevronRightIcon />
          </IconButton>
          <Button variant="outlined" onClick={() => refresh(month)} disabled={loading}>
            Refresh
          </Button>
        </Stack>
      </Box>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={1.5}
          alignItems={{ xs: 'stretch', sm: 'center' }}
        >
          <TextField
            size="small"
            fullWidth
            label="Search"
            placeholder="Sample id, name, powder, task type…"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
          <FormControl size="small" sx={{ minWidth: { xs: '100%', sm: 220 } }}>
            <InputLabel id="data-search-field-label">Search in</InputLabel>
            <Select
              labelId="data-search-field-label"
              label="Search in"
              value={searchField}
              onChange={(event) => setSearchField(event.target.value)}
            >
              {SEARCH_FIELD_OPTIONS.map((option) => (
                <MenuItem key={option.key} value={option.key}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button
            variant="text"
            onClick={() => {
              setSearchQuery('');
              setSearchField(ALL_FIELDS);
            }}
            disabled={!searchQuery && searchField === ALL_FIELDS}
            sx={{ whiteSpace: 'nowrap' }}
          >
            Clear
          </Button>
        </Stack>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
          Filters the tables for the selected month. CSV download is still the full month export.
        </Typography>
      </Paper>

      <DataSection
        title="Sample Summary"
        description="Samples created during the selected month."
        rows={sampleSummary}
        loading={loading}
        query={searchQuery}
        fieldKey={searchField}
        downloadHref={dataDownloadHref('/sample_summary.csv', month)}
        columns={SAMPLE_SUMMARY_COLUMNS}
      />

      <DataSection
        title="Powder Dosing Actuals"
        description="Flattened per-sample Labman dosing results for the selected month."
        rows={powderDosing}
        loading={loading}
        query={searchQuery}
        fieldKey={searchField}
        downloadHref={dataDownloadHref('/powder_dosing_actuals.csv', month)}
        columns={POWDER_DOSING_COLUMNS}
      />

      <DataSection
        title="Task Outcome Log"
        description="Task status and result-key overview for the selected month."
        rows={taskOutcome}
        loading={loading}
        query={searchQuery}
        fieldKey={searchField}
        downloadHref={dataDownloadHref('/task_outcome_log.csv', month)}
        columns={TASK_OUTCOME_COLUMNS}
      />
    </Stack>
  );
}

export default Data;
