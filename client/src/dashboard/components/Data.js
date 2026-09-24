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
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import {
  dataDownloadHref,
  get_data_window,
  get_powder_dosing_rows,
  get_sample_report_rows,
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

function formatPowderLine(powder) {
  const name = powder?.powder_name || '?';
  return `${name} target=${powder?.target_mass ?? ''} actual=${powder?.actual_mass ?? ''}`;
}

function PowderSummaryCell({ powders, summary }) {
  const lines = (powders || []).map(formatPowderLine).filter(Boolean);
  if (lines.length === 0) {
    return cellText(summary);
  }
  return (
    <Box component="div" sx={{ whiteSpace: 'pre-line', lineHeight: 1.45 }}>
      {lines.join('\n')}
    </Box>
  );
}

function matchCaption({ searching, query, shown, matched, total }) {
  if (searching) {
    const needle = query.trim();
    const allShown = shown >= matched;
    return (
      `${matched} match${matched === 1 ? '' : 'es'} for “${needle}”`
      + ` · ${total} total in this range`
      + (allShown ? '' : ` · showing first ${shown}`)
    );
  }
  if (shown < total) {
    return `Showing first ${shown} of ${total} rows in this range.`;
  }
  return `${total} row${total === 1 ? '' : 's'} in this range.`;
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
  const [showAll, setShowAll] = useState(false);
  const filteredRows = useMemo(
    () => filterRows(rows, columns, query, fieldKey),
    [rows, columns, query, fieldKey],
  );
  const searching = Boolean(query.trim());
  const fieldMissing = fieldKey !== ALL_FIELDS && !columns.some((column) => column.key === fieldKey);
  const limitActive = !searching && !showAll;
  const displayRows = limitActive ? filteredRows.slice(0, PREVIEW_LIMIT) : filteredRows;
  const canExpand = !searching && filteredRows.length > PREVIEW_LIMIT;

  useEffect(() => {
    setShowAll(false);
  }, [query, fieldKey, rows]);

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 2 }}>
            <Box>
              <Typography variant="h6">{title}</Typography>
              <Typography variant="body2" color="text.secondary">{description}</Typography>
              {!loading && !fieldMissing && rows.length > 0 && (
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                  {matchCaption({
                    searching,
                    query,
                    shown: displayRows.length,
                    matched: filteredRows.length,
                    total: rows.length,
                  })}
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
                ? 'No rows match this search for the selected date range.'
                : 'No rows for this date range. Try a wider range or wait for new samples/tasks to complete.'}
            </Typography>
          ) : (
            <>
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
                    {displayRows.map((row, index) => (
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
              {canExpand && (
                <Box>
                  <Button size="small" onClick={() => setShowAll((value) => !value)}>
                    {showAll ? 'Show fewer rows' : `Show all ${filteredRows.length} rows`}
                  </Button>
                </Box>
              )}
            </>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

function SampleReportSection({
  rows,
  loading,
  query,
  fieldKey,
  downloadHref,
}) {
  const [openName, setOpenName] = useState(null);
  const [showAll, setShowAll] = useState(false);
  const filteredRows = useMemo(
    () => filterRows(rows, SAMPLE_REPORT_COLUMNS, query, fieldKey),
    [rows, query, fieldKey],
  );
  const searching = Boolean(query.trim());
  const limitActive = !searching && !showAll;
  const displayRows = limitActive ? filteredRows.slice(0, PREVIEW_LIMIT) : filteredRows;
  const canExpand = !searching && filteredRows.length > PREVIEW_LIMIT;

  useEffect(() => {
    setShowAll(false);
  }, [query, fieldKey, rows]);

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 2 }}>
            <Box>
              <Typography variant="h6">Sample Report</Typography>
              <Typography variant="body2" color="text.secondary">
                One row per sample name. Trailing numeric copies (Sample_66_1) are folded
                into Sample_66. Click a row for Labman target vs actual masses and every
                task that mentions those sample IDs.
              </Typography>
              {!loading && rows.length > 0 && (
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                  {matchCaption({
                    searching,
                    query,
                    shown: displayRows.length,
                    matched: filteredRows.length,
                    total: rows.length,
                  })}
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
          ) : filteredRows.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              {searching
                ? 'No rows match this search for the selected date range.'
                : 'No rows for this date range. Try a wider range or wait for new samples/tasks to complete.'}
            </Typography>
          ) : (
            <>
              <TableContainer component={Paper} sx={{ maxHeight: 560 }}>
                <Table stickyHeader size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ width: 36 }} />
                      {SAMPLE_REPORT_COLUMNS.map((column) => (
                        <TableCell key={column.key}>{column.label}</TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {displayRows.map((row) => {
                      const open = openName === row.name;
                      return (
                        <React.Fragment key={row.name}>
                          <TableRow
                            hover
                            sx={{ cursor: 'pointer' }}
                            onClick={() => setOpenName(open ? null : row.name)}
                          >
                            <TableCell>
                              <IconButton size="small" aria-label={open ? 'Collapse' : 'Expand'}>
                                {open ? <KeyboardArrowDownIcon /> : <KeyboardArrowRightIcon />}
                              </IconButton>
                            </TableCell>
                            {SAMPLE_REPORT_COLUMNS.map((column) => (
                              <TableCell key={column.key}>
                                {column.key === 'powder_summary' ? (
                                  <PowderSummaryCell
                                    powders={row.powders}
                                    summary={row.powder_summary}
                                  />
                                ) : (
                                  cellText(row[column.key])
                                )}
                              </TableCell>
                            ))}
                          </TableRow>
                          {open && (
                            <TableRow>
                              <TableCell colSpan={SAMPLE_REPORT_COLUMNS.length + 1}>
                                <Stack spacing={1.5} sx={{ py: 1 }}>
                                  <Typography variant="caption" color="text.secondary">
                                    {`IDs: ${cellText(row.sample_ids)}`}
                                    {row.heating_source ? ` | Heating source: ${row.heating_source}` : ''}
                                  </Typography>
                                  {(row.powders || []).length > 0 && (
                                    <Table size="small">
                                      <TableHead>
                                        <TableRow>
                                          <TableCell>Powder</TableCell>
                                          <TableCell>Target</TableCell>
                                          <TableCell>Actual</TableCell>
                                          <TableCell>Delta</TableCell>
                                          <TableCell>Doses</TableCell>
                                        </TableRow>
                                      </TableHead>
                                      <TableBody>
                                        {row.powders.map((powder, index) => (
                                          <TableRow key={`${row.name}-powder-${index}`}>
                                            <TableCell>{cellText(powder.powder_name)}</TableCell>
                                            <TableCell>{cellText(powder.target_mass)}</TableCell>
                                            <TableCell>{cellText(powder.actual_mass)}</TableCell>
                                            <TableCell>{cellText(powder.delta_mass)}</TableCell>
                                            <TableCell>{cellText(powder.dose_count)}</TableCell>
                                          </TableRow>
                                        ))}
                                      </TableBody>
                                    </Table>
                                  )}
                                  {(row.related_tasks || []).length > 0 && (
                                    <Table size="small">
                                      <TableHead>
                                        <TableRow>
                                          <TableCell>Task</TableCell>
                                          <TableCell>Status</TableCell>
                                          <TableCell>Task ID</TableCell>
                                        </TableRow>
                                      </TableHead>
                                      <TableBody>
                                        {row.related_tasks.map((task) => (
                                          <TableRow key={task.task_id}>
                                            <TableCell>{cellText(task.type)}</TableCell>
                                            <TableCell>{cellText(task.status)}</TableCell>
                                            <TableCell>{cellText(task.task_id)}</TableCell>
                                          </TableRow>
                                        ))}
                                      </TableBody>
                                    </Table>
                                  )}
                                </Stack>
                              </TableCell>
                            </TableRow>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
              {canExpand && (
                <Box>
                  <Button size="small" onClick={() => setShowAll((value) => !value)}>
                    {showAll ? 'Show fewer rows' : `Show all ${filteredRows.length} rows`}
                  </Button>
                </Box>
              )}
            </>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

const SAMPLE_REPORT_COLUMNS = [
  { key: 'name', label: 'Sample' },
  { key: 'aliases', label: 'Aliases' },
  { key: 'powder_summary', label: 'Powders (target / actual)' },
  { key: 'crucible', label: 'Crucible' },
  { key: 'mixing_pot', label: 'Mixing pot' },
  { key: 'heating_temperature', label: 'Heating T' },
  { key: 'dwell_hours', label: 'Dwell (h)' },
  { key: 'task_summary', label: 'Related tasks' },
];

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
    ...SAMPLE_REPORT_COLUMNS,
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
  const [sampleReport, setSampleReport] = useState([]);
  const [sampleSummary, setSampleSummary] = useState([]);
  const [powderDosing, setPowderDosing] = useState([]);
  const [taskOutcome, setTaskOutcome] = useState([]);
  const [loading, setLoading] = useState(true);
  const [windowInfo, setWindowInfo] = useState(null);
  const [appliedRange, setAppliedRange] = useState(null);
  const [draftStart, setDraftStart] = useState('');
  const [draftEnd, setDraftEnd] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchField, setSearchField] = useState(ALL_FIELDS);

  const refresh = useCallback(async (target = null) => {
    setLoading(true);
    const [windowResult, sampleReportResult, sampleSummaryResult, powderDosingResult, taskOutcomeResult] = await Promise.all([
      get_data_window(target),
      get_sample_report_rows(target),
      get_sample_summary_rows(target),
      get_powder_dosing_rows(target),
      get_task_outcome_rows(target),
    ]);
    const win = windowResult?.window || null;
    setWindowInfo(win);
    if (win?.start_date && win?.end_date) {
      const nextRange = { start: win.start_date, end: win.end_date };
      setAppliedRange(nextRange);
      setDraftStart(win.start_date);
      setDraftEnd(win.end_date);
    } else if (typeof target === 'string' && target) {
      setAppliedRange({ month: target });
    } else if (target && typeof target === 'object') {
      setAppliedRange(target);
    }
    setSampleReport(sampleReportResult?.rows || []);
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
    refresh({ month: windowInfo.older_month });
  };

  const goNewer = () => {
    if (!windowInfo?.newer_month) {
      return;
    }
    refresh({ month: windowInfo.newer_month });
  };

  const applyCustomRange = () => {
    if (!draftStart || !draftEnd) {
      return;
    }
    if (draftEnd < draftStart) {
      return;
    }
    refresh({ start: draftStart, end: draftEnd });
  };

  const rangeInvalid = Boolean(draftStart && draftEnd && draftEnd < draftStart);
  const downloadRange = appliedRange;

  return (
    <Stack spacing={2}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Box>
          <Typography variant="h5">Data</Typography>
          <Typography variant="body2" color="text.secondary">
            Curated Mongo-backed exports for operators and experimenters.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
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
          <TextField
            size="small"
            type="date"
            label="From"
            value={draftStart}
            onChange={(event) => setDraftStart(event.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ width: 160 }}
          />
          <TextField
            size="small"
            type="date"
            label="To"
            value={draftEnd}
            onChange={(event) => setDraftEnd(event.target.value)}
            InputLabelProps={{ shrink: true }}
            error={rangeInvalid}
            helperText={rangeInvalid ? 'To must be on/after From' : undefined}
            sx={{ width: 160 }}
          />
          <Button
            variant="contained"
            onClick={applyCustomRange}
            disabled={loading || !draftStart || !draftEnd || rangeInvalid}
          >
            Apply range
          </Button>
          <Button
            variant="outlined"
            onClick={() => refresh(downloadRange)}
            disabled={loading}
          >
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
          Search filters the loaded tables. CSV download uses the full selected date range
          (not just the search hits). While searching, every match is listed — not capped at 25.
        </Typography>
      </Paper>

      <SampleReportSection
        rows={sampleReport}
        loading={loading}
        query={searchQuery}
        fieldKey={searchField}
        downloadHref={dataDownloadHref('/sample_report.csv', downloadRange)}
      />

      <DataSection
        title="Sample Summary"
        description="Samples created during the selected date range."
        rows={sampleSummary}
        loading={loading}
        query={searchQuery}
        fieldKey={searchField}
        downloadHref={dataDownloadHref('/sample_summary.csv', downloadRange)}
        columns={SAMPLE_SUMMARY_COLUMNS}
      />

      <DataSection
        title="Powder Dosing Actuals"
        description="Flattened per-sample Labman dosing results for the selected date range."
        rows={powderDosing}
        loading={loading}
        query={searchQuery}
        fieldKey={searchField}
        downloadHref={dataDownloadHref('/powder_dosing_actuals.csv', downloadRange)}
        columns={POWDER_DOSING_COLUMNS}
      />

      <DataSection
        title="Task Outcome Log"
        description="Task status and result-key overview for the selected date range."
        rows={taskOutcome}
        loading={loading}
        query={searchQuery}
        fieldKey={searchField}
        downloadHref={dataDownloadHref('/task_outcome_log.csv', downloadRange)}
        columns={TASK_OUTCOME_COLUMNS}
      />
    </Stack>
  );
}

export default Data;
