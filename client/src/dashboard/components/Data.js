import React, { useCallback, useEffect, useMemo, useState } from 'react';
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
  DialogTitle,
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
  Tooltip,
  Typography,
} from '@mui/material';
import Paper from '@mui/material/Paper';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import {
  create_data_report_job,
  dataReportCsvHref,
  get_current_data_report_job,
  get_data_report_job,
  get_data_report_rows,
  get_data_reports,
  get_data_window,
  patch_data_report,
  refresh_data_report,
} from '../../api_routes';

const ALL_FIELDS = 'all';
const PREVIEW_LIMIT = 25;
const DEFAULT_REPORTS = [
  'sample_report',
  'sample_summary',
  'powder_dosing_actuals',
  'task_outcome_log',
];

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

function powderMassLines(powders, field) {
  return (powders || []).map((powder) => {
    const name = powder?.powder_name || '?';
    const mass = powder?.[field];
    return mass == null || mass === '' ? name : `${name} ${mass}`;
  });
}

function PowderMassCell({ powders, field, fallback }) {
  const lines = powderMassLines(powders, field);
  if (lines.length === 0) {
    return cellText(fallback);
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
      + ` · ${total} total in snapshot`
      + (allShown ? '' : ` · showing first ${shown}`)
    );
  }
  if (shown < total) {
    return `Showing first ${shown} of ${total} rows in snapshot.`;
  }
  return `${total} row${total === 1 ? '' : 's'} in snapshot.`;
}

function CopyableReportName({ name }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!name) {
      return;
    }
    try {
      await navigator.clipboard.writeText(name);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      // Fallback for older browsers / restricted clipboard access.
      const textarea = document.createElement('textarea');
      textarea.value = name;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'absolute';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand('copy');
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1500);
      } finally {
        document.body.removeChild(textarea);
      }
    }
  };

  if (!name) {
    return null;
  }

  return (
    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ minWidth: 0 }}>
      <Typography
        variant="subtitle1"
        component="span"
        sx={{ fontWeight: 600, lineHeight: 1.3, wordBreak: 'break-word' }}
      >
        {name}
      </Typography>
      <Tooltip title={copied ? 'Copied' : 'Copy report name'}>
        <IconButton
          size="small"
          aria-label="Copy report name"
          onClick={handleCopy}
          sx={{ flexShrink: 0 }}
        >
          <ContentCopyIcon fontSize="inherit" />
        </IconButton>
      </Tooltip>
    </Stack>
  );
}

function ReportPanel({
  panelIndex,
  catalog,
  selectedName,
  onSelectName,
  appliedRange,
  searchQuery,
  searchField,
}) {
  const meta = catalog.find((item) => item.name === selectedName) || null;
  const [columns, setColumns] = useState([]);
  const [rows, setRows] = useState([]);
  const [rowDetail, setRowDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [updatedAt, setUpdatedAt] = useState(null);
  const [windowLabel, setWindowLabel] = useState(null);
  const [showAll, setShowAll] = useState(false);
  const [openName, setOpenName] = useState(null);
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveTitle, setSaveTitle] = useState('');

  const loadSnapshot = useCallback(async (name) => {
    if (!name) {
      setColumns([]);
      setRows([]);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const response = await get_data_report_rows(name);
      if (response?.status !== 'success') {
        throw new Error(response?.errors || 'Failed to load report snapshot.');
      }
      const report = response.report || {};
      setColumns(report.columns || []);
      setRows(report.rows || []);
      setRowDetail(report.row_detail || null);
      setUpdatedAt(report.updated_at || null);
      const win = report.window;
      setWindowLabel(
        win?.start_date && win?.end_date
          ? `${win.start_date} → ${win.end_date}`
          : null,
      );
    } catch (err) {
      setError(err.message || 'Failed to load report.');
      setColumns([]);
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSnapshot(selectedName);
    setShowAll(false);
    setOpenName(null);
  }, [selectedName, loadSnapshot]);

  const handleRefresh = async () => {
    if (!selectedName) {
      return;
    }
    setRefreshing(true);
    setError('');
    try {
      const response = await refresh_data_report(selectedName, appliedRange);
      if (response?.status !== 'success') {
        throw new Error(response?.errors || 'Refresh failed.');
      }
      const report = response.report || {};
      setColumns(report.columns || []);
      setRows(report.rows || []);
      setRowDetail(report.row_detail || null);
      setUpdatedAt(report.updated_at || null);
      const win = report.window || response.window;
      setWindowLabel(
        win?.start_date && win?.end_date
          ? `${win.start_date} → ${win.end_date}`
          : (response.window?.label || null),
      );
    } catch (err) {
      setError(err.message || 'Refresh failed.');
    } finally {
      setRefreshing(false);
    }
  };

  const handleSave = async () => {
    if (!selectedName) {
      return;
    }
    const response = await patch_data_report(selectedName, {
      saved: true,
      title: saveTitle.trim() || meta?.title || selectedName,
    });
    if (response?.status !== 'success') {
      setError(response?.errors || 'Save failed.');
      return;
    }
    setSaveOpen(false);
  };

  const filteredRows = useMemo(
    () => filterRows(rows, columns, searchQuery, searchField),
    [rows, columns, searchQuery, searchField],
  );
  const searching = Boolean(searchQuery.trim());
  const limitActive = !searching && !showAll;
  const displayRows = limitActive ? filteredRows.slice(0, PREVIEW_LIMIT) : filteredRows;
  const canExpand = !searching && filteredRows.length > PREVIEW_LIMIT;
  const isSampleDetail = rowDetail === 'sample_report';

  const searchFieldOptions = useMemo(() => {
    const opts = [{ key: ALL_FIELDS, label: 'All fields' }];
    columns.forEach((column) => {
      if (!opts.some((entry) => entry.key === column.key)) {
        opts.push(column);
      }
    });
    return opts;
  }, [columns]);

  // Parent search field may target another panel's columns; fall back to all fields.
  const effectiveSearchField = searchFieldOptions.some((o) => o.key === searchField)
    ? searchField
    : ALL_FIELDS;

  const filteredForCaption = useMemo(
    () => filterRows(rows, columns, searchQuery, effectiveSearchField),
    [rows, columns, searchQuery, effectiveSearchField],
  );
  const displayForCaption = (!searching && !showAll)
    ? filteredForCaption.slice(0, PREVIEW_LIMIT)
    : filteredForCaption;

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2}>
          <Stack
            direction={{ xs: 'column', md: 'row' }}
            spacing={1.5}
            justifyContent="space-between"
            alignItems={{ xs: 'stretch', md: 'flex-start' }}
          >
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Stack spacing={1.5} sx={{ maxWidth: 480 }}>
                <Typography
                  variant="overline"
                  color="text.secondary"
                  display="block"
                  sx={{ lineHeight: 1.5, letterSpacing: '0.08em' }}
                >
                  Panel {panelIndex + 1}
                </Typography>
                <FormControl size="small" fullWidth>
                  <InputLabel id={`report-select-${panelIndex}`}>Report</InputLabel>
                  <Select
                    labelId={`report-select-${panelIndex}`}
                    label="Report"
                    value={selectedName || ''}
                    onChange={(event) => onSelectName(event.target.value)}
                  >
                    {catalog.map((report) => (
                      <MenuItem key={report.name} value={report.name}>
                        {report.title || report.name}
                        {report.builtin ? ' (builtin)' : ''}
                        {report.saved ? '' : ' · draft'}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                {selectedName && (
                  <CopyableReportName name={meta?.title || selectedName} />
                )}
                <Typography variant="body2" color="text.secondary">
                  {meta?.description || 'Select a report.'}
                </Typography>
                {(windowLabel || updatedAt) && (
                  <Typography variant="caption" color="text.secondary" display="block">
                    {windowLabel ? `Snapshot window: ${windowLabel}` : ''}
                    {windowLabel && updatedAt ? ' · ' : ''}
                    {updatedAt ? `Updated: ${cellText(updatedAt)}` : ''}
                  </Typography>
                )}
                {!loading && rows.length > 0 && (
                  <Typography variant="caption" color="text.secondary" display="block">
                    {matchCaption({
                      searching,
                      query: searchQuery,
                      shown: displayForCaption.length,
                      matched: filteredForCaption.length,
                      total: rows.length,
                    })}
                  </Typography>
                )}
              </Stack>
            </Box>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              <Button
                variant="contained"
                onClick={handleRefresh}
                disabled={!selectedName || refreshing || loading}
              >
                {refreshing ? 'Refreshing…' : 'Refresh'}
              </Button>
              <Button
                variant="outlined"
                onClick={() => {
                  setSaveTitle(meta?.title || selectedName || '');
                  setSaveOpen(true);
                }}
                disabled={!selectedName}
              >
                Save
              </Button>
              <Button
                variant="outlined"
                href={selectedName ? dataReportCsvHref(selectedName) : undefined}
                disabled={!selectedName || rows.length === 0}
              >
                Download CSV
              </Button>
            </Stack>
          </Stack>

          {error && <Alert severity="error">{error}</Alert>}

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
              <CircularProgress size={28} />
            </Box>
          ) : !selectedName ? (
            <Typography variant="body2" color="text.secondary">
              Choose a report from the dropdown.
            </Typography>
          ) : columns.length === 0 || rows.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No snapshot yet. Click Refresh to run the generator for the selected date range.
            </Typography>
          ) : (
            <>
              <TableContainer component={Paper} sx={{ maxHeight: isSampleDetail ? 560 : 360 }}>
                <Table stickyHeader size="small">
                  <TableHead>
                    <TableRow>
                      {isSampleDetail && <TableCell sx={{ width: 36 }} />}
                      {columns.map((column) => (
                        <TableCell key={column.key}>{column.label}</TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {displayForCaption.map((row, index) => {
                      const rowKey = row.name || row.sample_id || row.task_id || index;
                      const open = isSampleDetail && openName === row.name;
                      return (
                        <React.Fragment key={rowKey}>
                          <TableRow
                            hover={isSampleDetail}
                            sx={isSampleDetail ? { cursor: 'pointer' } : undefined}
                            onClick={
                              isSampleDetail
                                ? () => setOpenName(open ? null : row.name)
                                : undefined
                            }
                          >
                            {isSampleDetail && (
                              <TableCell>
                                <IconButton size="small" aria-label={open ? 'Collapse' : 'Expand'}>
                                  {open ? <KeyboardArrowDownIcon /> : <KeyboardArrowRightIcon />}
                                </IconButton>
                              </TableCell>
                            )}
                            {columns.map((column) => (
                              <TableCell key={column.key}>
                                {column.key === 'target_masses' || column.key === 'actual_masses' ? (
                                  <PowderMassCell
                                    powders={row.powders}
                                    field={column.key === 'target_masses' ? 'target_mass' : 'actual_mass'}
                                    fallback={row[column.key]}
                                  />
                                ) : (
                                  cellText(row[column.key])
                                )}
                              </TableCell>
                            ))}
                          </TableRow>
                          {open && (
                            <TableRow>
                              <TableCell colSpan={columns.length + 1}>
                                <Stack spacing={1.5} sx={{ py: 1 }}>
                                  <Typography variant="caption" color="text.secondary">
                                    {`IDs: ${cellText(row.sample_ids)}`}
                                  </Typography>
                                  {(row.powders || []).length > 0 && (
                                    <Table size="small">
                                      <TableHead>
                                        <TableRow>
                                          <TableCell>Powder</TableCell>
                                          <TableCell>Target</TableCell>
                                          <TableCell>Actual</TableCell>
                                          <TableCell>Delta</TableCell>
                                        </TableRow>
                                      </TableHead>
                                      <TableBody>
                                        {row.powders.map((powder, powderIndex) => (
                                          <TableRow key={`${row.name}-p-${powderIndex}`}>
                                            <TableCell>{cellText(powder.powder_name)}</TableCell>
                                            <TableCell>{cellText(powder.target_mass)}</TableCell>
                                            <TableCell>{cellText(powder.actual_mass)}</TableCell>
                                            <TableCell>{cellText(powder.delta_mass)}</TableCell>
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
                    {showAll ? 'Show fewer rows' : `Show all ${filteredForCaption.length} rows`}
                  </Button>
                </Box>
              )}
            </>
          )}
        </Stack>
      </CardContent>

      <Dialog open={saveOpen} onClose={() => setSaveOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>Save report</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Marks this registry entry as saved so it stays easy to find. Does not re-run the generator.
          </Typography>
          <TextField
            autoFocus
            fullWidth
            label="Title"
            value={saveTitle}
            onChange={(event) => setSaveTitle(event.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSave}>Save</Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
}

function Data() {
  const [catalog, setCatalog] = useState([]);
  const [panelReports, setPanelReports] = useState([...DEFAULT_REPORTS]);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [windowInfo, setWindowInfo] = useState(null);
  const [appliedRange, setAppliedRange] = useState(null);
  const [draftStart, setDraftStart] = useState('');
  const [draftEnd, setDraftEnd] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchField, setSearchField] = useState(ALL_FIELDS);
  const [catalogError, setCatalogError] = useState('');
  const [askPrompt, setAskPrompt] = useState('');
  const [askJob, setAskJob] = useState(null);
  const [askError, setAskError] = useState('');
  const [askSuccess, setAskSuccess] = useState('');
  const [askSubmitting, setAskSubmitting] = useState(false);

  const refreshWindow = useCallback(async (target = null) => {
    const windowResult = await get_data_window(target);
    const win = windowResult?.window || null;
    setWindowInfo(win);
    if (win?.start_date && win?.end_date) {
      const nextRange = { start: win.start_date, end: win.end_date };
      setAppliedRange(nextRange);
      setDraftStart(win.start_date);
      setDraftEnd(win.end_date);
    }
  }, []);

  const refreshCatalog = useCallback(async () => {
    setLoadingCatalog(true);
    try {
      const response = await get_data_reports();
      if (response?.status !== 'success') {
        throw new Error(response?.errors || 'Failed to load reports.');
      }
      const reports = response.reports || [];
      setCatalog(reports);
      setPanelReports((previous) => previous.map((name, index) => {
        if (reports.some((report) => report.name === name)) {
          return name;
        }
        return reports[index]?.name || reports[0]?.name || name;
      }));
      setCatalogError('');
    } catch (err) {
      setCatalogError(err.message || 'Failed to load reports.');
    } finally {
      setLoadingCatalog(false);
    }
  }, []);

  useEffect(() => {
    refreshWindow(null);
    refreshCatalog();
  }, [refreshWindow, refreshCatalog]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const response = await get_current_data_report_job();
      if (cancelled || response?.status !== 'success' || !response.job) {
        return;
      }
      setAskJob(response.job);
    })();
    return () => { cancelled = true; };
  }, []);

  const askRunning = askJob && (askJob.status === 'queued' || askJob.status === 'running');

  useEffect(() => {
    if (!askJob?.id || !askRunning) {
      return undefined;
    }
    const timer = window.setInterval(async () => {
      const response = await get_data_report_job(askJob.id);
      if (response?.status !== 'success' || !response.job) {
        return;
      }
      const job = response.job;
      setAskJob(job);
      if (job.status === 'succeeded') {
        setAskError('');
        setAskSuccess(
          job.report_name
            ? `Created “${job.report_name}”. Select Refresh on that panel to fill the table.`
            : 'Report agent finished. Reload catalog and Refresh the new report.',
        );
        await refreshCatalog();
        if (job.report_name) {
          setPanelReports((previous) => {
            const copy = [...previous];
            copy[0] = job.report_name;
            return copy;
          });
        }
      } else if (job.status === 'failed') {
        setAskSuccess('');
        setAskError(job.error || 'Report agent failed.');
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [askJob?.id, askRunning, refreshCatalog]);

  const submitAsk = async () => {
    const prompt = askPrompt.trim();
    if (!prompt || askSubmitting || askRunning) {
      return;
    }
    setAskSubmitting(true);
    setAskError('');
    setAskSuccess('');
    try {
      const response = await create_data_report_job(prompt);
      if (response?.status !== 'success') {
        throw new Error(response?.errors || 'Failed to start report agent.');
      }
      setAskJob(response.job);
      setAskPrompt('');
    } catch (err) {
      setAskError(err.message || 'Failed to start report agent.');
    } finally {
      setAskSubmitting(false);
    }
  };

  const goOlder = () => {
    if (!windowInfo?.older_month) {
      return;
    }
    refreshWindow({ month: windowInfo.older_month });
  };

  const goNewer = () => {
    if (!windowInfo?.newer_month) {
      return;
    }
    refreshWindow({ month: windowInfo.newer_month });
  };

  const applyCustomRange = () => {
    if (!draftStart || !draftEnd || draftEnd < draftStart) {
      return;
    }
    refreshWindow({ start: draftStart, end: draftEnd });
  };

  const rangeInvalid = Boolean(draftStart && draftEnd && draftEnd < draftStart);

  const searchFieldOptions = useMemo(() => {
    const opts = [{ key: ALL_FIELDS, label: 'All fields' }];
    // Union of column keys from catalog titles only — panels refine locally.
    return opts;
  }, []);

  const askStatusColor = {
    queued: 'default',
    running: 'info',
    succeeded: 'success',
    failed: 'error',
  }[askJob?.status] || 'default';

  return (
    <Stack spacing={2}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Box>
          <Typography variant="h5">Data</Typography>
          <Typography variant="body2" color="text.secondary">
            Registry-backed reports. Open shows the last snapshot; Refresh re-runs the read-only generator for the selected date range.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <IconButton
            aria-label="Older month"
            onClick={goOlder}
            disabled={!windowInfo?.has_older}
          >
            <ChevronLeftIcon />
          </IconButton>
          <Typography variant="body1" sx={{ minWidth: 140, textAlign: 'center' }}>
            {windowInfo?.label || 'Loading...'}
          </Typography>
          <IconButton
            aria-label="Newer month"
            onClick={goNewer}
            disabled={!windowInfo?.has_newer}
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
            disabled={!draftStart || !draftEnd || rangeInvalid}
          >
            Apply range
          </Button>
          <Button variant="outlined" onClick={() => { refreshWindow(appliedRange); refreshCatalog(); }}>
            Reload catalog
          </Button>
        </Stack>
      </Box>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack spacing={1.5}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Ask for a report
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Describe a table you need. A Cursor agent will write a read-only generator and register it in the Data catalog.
          </Typography>
          <TextField
            multiline
            minRows={3}
            fullWidth
            label="Describe the table you need"
            placeholder="e.g. Samples created in the date range with name, created_at, and experiment id"
            value={askPrompt}
            onChange={(event) => setAskPrompt(event.target.value)}
            disabled={askSubmitting || askRunning}
          />
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
            <Button
              variant="contained"
              onClick={submitAsk}
              disabled={!askPrompt.trim() || askSubmitting || askRunning}
            >
              {askSubmitting || askRunning ? 'Working…' : 'Submit'}
            </Button>
            {askJob?.status && (
              <Chip
                size="small"
                label={askJob.status}
                color={askStatusColor}
              />
            )}
            {askJob?.report_name && askJob.status === 'succeeded' && (
              <Typography variant="body2" color="text.secondary">
                {askJob.report_name}
              </Typography>
            )}
          </Stack>
          {askError && <Alert severity="error">{askError}</Alert>}
          {askSuccess && <Alert severity="success">{askSuccess}</Alert>}
          {askJob?.log_tail && (
            <Box
              component="pre"
              sx={{
                m: 0,
                p: 1.5,
                maxHeight: 180,
                overflow: 'auto',
                bgcolor: 'action.hover',
                borderRadius: 1,
                fontFamily: 'Source Code Pro, monospace',
                fontSize: 12,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {askJob.log_tail}
            </Box>
          )}
        </Stack>
      </Paper>

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
            placeholder="Filter visible snapshot rows…"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
          <FormControl size="small" sx={{ minWidth: { xs: '100%', sm: 180 } }}>
            <InputLabel id="data-search-field-label">Search in</InputLabel>
            <Select
              labelId="data-search-field-label"
              label="Search in"
              value={searchField}
              onChange={(event) => setSearchField(event.target.value)}
            >
              {searchFieldOptions.map((option) => (
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
          >
            Clear
          </Button>
        </Stack>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
          Search filters the loaded snapshot only. Refresh recomputes from Alab + Alab(completed) via the report module.
        </Typography>
      </Paper>

      {catalogError && <Alert severity="error">{catalogError}</Alert>}
      {loadingCatalog && <CircularProgress size={28} />}

      {panelReports.map((name, index) => (
        <ReportPanel
          key={`panel-${index}`}
          panelIndex={index}
          catalog={catalog}
          selectedName={name}
          onSelectName={(next) => {
            setPanelReports((previous) => {
              const copy = [...previous];
              copy[index] = next;
              return copy;
            });
          }}
          appliedRange={appliedRange}
          searchQuery={searchQuery}
          searchField={searchField}
        />
      ))}
    </Stack>
  );
}

export default Data;
