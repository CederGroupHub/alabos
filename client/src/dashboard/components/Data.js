import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  AppBar,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
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
  Toolbar,
  Tooltip,
  Typography,
} from '@mui/material';
import Paper from '@mui/material/Paper';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import CloseIcon from '@mui/icons-material/Close';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import {
  dataReportCsvHref,
  get_data_report_rows,
  get_data_reports,
  get_data_window,
  patch_data_report,
  refresh_data_report,
} from '../../api_routes';

const ALL_FIELDS = 'all';
const PREVIEW_LIMIT = 25;
const CATALOG_POLL_MS = 4000;
const FALLBACK_REPORT = 'sample_report';
const DATA_RANGE_STORAGE_KEY = 'alab.data.date_range';
const COLUMN_WIDTH_STORAGE_PREFIX = 'alab.data.col_widths.';
const MIN_COLUMN_WIDTH = 48;
const DEFAULT_COLUMN_WIDTH = 132;
const EXPAND_COLUMN_WIDTH = 36;

function loadPersistedDateRange() {
  try {
    const raw = window.localStorage.getItem(DATA_RANGE_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    const start = parsed?.start;
    const end = parsed?.end;
    const isoDay = /^\d{4}-\d{2}-\d{2}$/;
    if (typeof start === 'string' && typeof end === 'string' && isoDay.test(start) && isoDay.test(end) && end >= start) {
      return { start, end };
    }
  } catch (err) {
    // Ignore corrupt / unavailable storage.
  }
  return null;
}

function persistDateRange(range) {
  if (!range?.start || !range?.end) {
    return;
  }
  try {
    window.localStorage.setItem(
      DATA_RANGE_STORAGE_KEY,
      JSON.stringify({ start: range.start, end: range.end }),
    );
  } catch (err) {
    // Ignore quota / private-mode failures.
  }
}

function cellText(value) {
  if (Array.isArray(value)) {
    return value.join(', ');
  }
  if (value == null) {
    return '';
  }
  return String(value);
}

function reportCreatedDate(report) {
  const raw = report?.created_at;
  if (!raw) {
    return null;
  }
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date;
}

function reportCreatedDay(report) {
  const date = reportCreatedDate(report);
  if (!date) {
    return '';
  }
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function reportCreatedLabel(report) {
  const date = reportCreatedDate(report);
  if (!date) {
    return '—';
  }
  return date.toLocaleString();
}

function reportOptionLabel(report) {
  if (!report) {
    return '';
  }
  const title = report.title || report.name || '';
  const suffix = report.builtin ? ' (builtin)' : (report.saved ? '' : ' · draft');
  return `${title}${suffix}`;
}

function filterCatalog(catalog, nameQuery, dateQuery) {
  const nameNeedle = nameQuery.trim().toLowerCase();
  const dateNeedle = dateQuery.trim().toLowerCase();
  return catalog.filter((report) => {
    if (nameNeedle) {
      const hay = `${report.title || ''} ${report.name || ''}`.toLowerCase();
      if (!hay.includes(nameNeedle)) {
        return false;
      }
    }
    if (dateNeedle) {
      const day = reportCreatedDay(report).toLowerCase();
      const label = reportCreatedLabel(report).toLowerCase();
      const raw = String(report.created_at || '').toLowerCase();
      if (!day.includes(dateNeedle) && !label.includes(dateNeedle) && !raw.includes(dateNeedle)) {
        return false;
      }
    }
    return true;
  });
}

function pickDefaultReport(reports, preferred) {
  if (preferred && reports.some((report) => report.name === preferred)) {
    return preferred;
  }
  if (reports.some((report) => report.name === FALLBACK_REPORT)) {
    return FALLBACK_REPORT;
  }
  return reports[0]?.name || '';
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

function defaultColumnWidth(column) {
  const label = column?.label || column?.key || '';
  return Math.min(420, Math.max(DEFAULT_COLUMN_WIDTH, label.length * 8 + 32));
}

function loadPersistedColumnWidths(reportName) {
  if (!reportName) {
    return {};
  }
  try {
    const raw = window.localStorage.getItem(`${COLUMN_WIDTH_STORAGE_PREFIX}${reportName}`);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') {
      return {};
    }
    const widths = {};
    Object.entries(parsed).forEach(([key, value]) => {
      if (typeof value === 'number' && Number.isFinite(value)) {
        widths[key] = Math.max(MIN_COLUMN_WIDTH, value);
      }
    });
    return widths;
  } catch (err) {
    return {};
  }
}

function persistColumnWidths(reportName, widths) {
  if (!reportName || !widths) {
    return;
  }
  try {
    window.localStorage.setItem(
      `${COLUMN_WIDTH_STORAGE_PREFIX}${reportName}`,
      JSON.stringify(widths),
    );
  } catch (err) {
    // Ignore quota / private-mode failures.
  }
}

function useReportColumnWidths(reportName, columns) {
  const [widths, setWidths] = useState({});
  const persistTimerRef = useRef(null);

  useEffect(() => {
    const keys = new Set(columns.map((column) => column.key));
    const persisted = loadPersistedColumnWidths(reportName);
    const next = {};
    columns.forEach((column) => {
      if (persisted[column.key] != null) {
        next[column.key] = persisted[column.key];
      } else if (widths[column.key] != null) {
        next[column.key] = widths[column.key];
      } else {
        next[column.key] = defaultColumnWidth(column);
      }
    });
    Object.keys(widths).forEach((key) => {
      if (!keys.has(key)) {
        delete next[key];
      }
    });
    setWidths(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset when report/column set changes
  }, [reportName, columns.map((column) => column.key).join('\0')]);

  useEffect(() => {
    if (!reportName) {
      return undefined;
    }
    if (persistTimerRef.current) {
      clearTimeout(persistTimerRef.current);
    }
    persistTimerRef.current = setTimeout(() => {
      persistColumnWidths(reportName, widths);
    }, 300);
    return () => {
      if (persistTimerRef.current) {
        clearTimeout(persistTimerRef.current);
      }
    };
  }, [reportName, widths]);

  const getWidth = useCallback(
    (columnKey) => {
      if (widths[columnKey] != null) {
        return widths[columnKey];
      }
      const column = columns.find((entry) => entry.key === columnKey);
      return column ? defaultColumnWidth(column) : DEFAULT_COLUMN_WIDTH;
    },
    [columns, widths],
  );

  const startColumnResize = useCallback((event, columnKey) => {
    event.preventDefault();
    event.stopPropagation();
    const startX = event.clientX;
    const startWidth = widths[columnKey] ?? DEFAULT_COLUMN_WIDTH;

    const onMove = (moveEvent) => {
      const delta = moveEvent.clientX - startX;
      const nextWidth = Math.max(MIN_COLUMN_WIDTH, startWidth + delta);
      setWidths((prev) => ({ ...prev, [columnKey]: nextWidth }));
    };

    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }, [widths]);

  const columnCellSx = useCallback(
    (columnKey) => ({
      width: getWidth(columnKey),
      minWidth: getWidth(columnKey),
      maxWidth: getWidth(columnKey),
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
      verticalAlign: 'top',
    }),
    [getWidth],
  );

  const tableMinWidth = useMemo(() => {
    let total = columns.reduce((sum, column) => sum + getWidth(column.key), 0);
    return total;
  }, [columns, getWidth]);

  return {
    getWidth,
    startColumnResize,
    columnCellSx,
    tableMinWidth,
  };
}

function ColumnResizeHandle({ onMouseDown }) {
  return (
    <Box
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize column"
      onMouseDown={onMouseDown}
      onClick={(event) => event.stopPropagation()}
      sx={{
        position: 'absolute',
        top: 0,
        right: 0,
        width: 10,
        height: '100%',
        cursor: 'col-resize',
        zIndex: 2,
        '&::after': {
          content: '""',
          position: 'absolute',
          top: '20%',
          bottom: '20%',
          right: 4,
          width: 2,
          borderRadius: 1,
          bgcolor: 'action.disabled',
          opacity: 0.6,
          transition: 'opacity 0.15s',
        },
        '&:hover::after': {
          opacity: 1,
          bgcolor: 'primary.main',
        },
      }}
    />
  );
}

function ResizableHeaderCell({ label, width, onResizeStart }) {
  return (
    <TableCell
      sx={{
        width,
        minWidth: width,
        maxWidth: width,
        position: 'relative',
        overflow: 'hidden',
        userSelect: 'none',
        whiteSpace: 'nowrap',
        textOverflow: 'ellipsis',
        pr: 1.5,
      }}
    >
      <Box component="span" sx={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {label}
      </Box>
      <ColumnResizeHandle onMouseDown={onResizeStart} />
    </TableCell>
  );
}

function ReportDataTable({
  columns,
  rows,
  isSampleDetail,
  openName,
  setOpenName,
  columnWidths,
}) {
  const { getWidth, startColumnResize, columnCellSx, tableMinWidth } = columnWidths;

  const renderBodyCell = (row, column) => (
    <TableCell key={column.key} sx={columnCellSx(column.key)}>
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
  );

  return (
    <Table stickyHeader size="small" sx={{ tableLayout: 'fixed', minWidth: tableMinWidth + (isSampleDetail ? EXPAND_COLUMN_WIDTH : 0) }}>
      <TableHead>
        <TableRow>
          {isSampleDetail && (
            <TableCell
              sx={{
                width: EXPAND_COLUMN_WIDTH,
                minWidth: EXPAND_COLUMN_WIDTH,
                maxWidth: EXPAND_COLUMN_WIDTH,
              }}
            />
          )}
          {columns.map((column) => (
            <ResizableHeaderCell
              key={column.key}
              label={column.label}
              width={getWidth(column.key)}
              onResizeStart={(event) => startColumnResize(event, column.key)}
            />
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((row, index) => {
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
                  <TableCell sx={{ width: EXPAND_COLUMN_WIDTH, minWidth: EXPAND_COLUMN_WIDTH }}>
                    <IconButton size="small" aria-label={open ? 'Collapse' : 'Expand'}>
                      {open ? <KeyboardArrowDownIcon /> : <KeyboardArrowRightIcon />}
                    </IconButton>
                  </TableCell>
                )}
                {columns.map((column) => renderBodyCell(row, column))}
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
  );
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

function ReportPicker({
  catalog,
  selectedName,
  onSelectName,
  nameQuery,
  onNameQueryChange,
  dateQuery,
  onDateQueryChange,
}) {
  const filtered = useMemo(() => {
    const matches = filterCatalog(catalog, nameQuery, dateQuery);
    if (selectedName && !matches.some((report) => report.name === selectedName)) {
      const selected = catalog.find((report) => report.name === selectedName);
      if (selected) {
        return [selected, ...matches];
      }
    }
    return matches;
  }, [catalog, nameQuery, dateQuery, selectedName]);
  const selected = catalog.find((report) => report.name === selectedName) || null;

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack spacing={1.5}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          Choose a data view
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Newest views are listed first. Filter by name or creation date when the catalog grows.
        </Typography>
        <Stack
          direction={{ xs: 'column', md: 'row' }}
          spacing={1.5}
          alignItems={{ xs: 'stretch', md: 'flex-start' }}
        >
          <TextField
            size="small"
            fullWidth
            label="Search by name"
            placeholder="Title or slug…"
            value={nameQuery}
            onChange={(event) => onNameQueryChange(event.target.value)}
          />
          <TextField
            size="small"
            fullWidth
            label="Search by creation date"
            placeholder="e.g. 2026-09-23"
            value={dateQuery}
            onChange={(event) => onDateQueryChange(event.target.value)}
            helperText="Matches YYYY-MM-DD or the local date shown in the list"
          />
          <Button
            variant="text"
            onClick={() => {
              onNameQueryChange('');
              onDateQueryChange('');
            }}
            disabled={!nameQuery && !dateQuery}
            sx={{ flexShrink: 0, alignSelf: { md: 'center' } }}
          >
            Clear filters
          </Button>
        </Stack>
        <Autocomplete
          options={filtered}
          value={selected}
          onChange={(_event, next) => onSelectName(next?.name || '')}
          getOptionLabel={reportOptionLabel}
          isOptionEqualToValue={(option, value) => option?.name === value?.name}
          noOptionsText={
            catalog.length === 0
              ? 'No data views in catalog'
              : 'No views match these filters'
          }
          ListboxProps={{ style: { maxHeight: 320 } }}
          renderOption={(props, option) => (
            <li {...props} key={option.name}>
              <Box sx={{ py: 0.25, minWidth: 0 }}>
                <Typography variant="body2" noWrap>
                  {reportOptionLabel(option)}
                </Typography>
                <Typography variant="caption" color="text.secondary" display="block" noWrap>
                  {option.name}
                  {' · created '}
                  {reportCreatedLabel(option)}
                </Typography>
              </Box>
            </li>
          )}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Data view"
              placeholder="Select a data view"
              helperText={
                filtered.length === catalog.length
                  ? `${catalog.length} view${catalog.length === 1 ? '' : 's'} in catalog`
                  : `${filtered.length} of ${catalog.length} views match filters`
              }
            />
          )}
        />
      </Stack>
    </Paper>
  );
}

function ReportViewer({
  catalog,
  selectedName,
  appliedRange,
  searchQuery,
  searchField,
  onSearchQueryChange,
  onSearchFieldChange,
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
  const [fullscreen, setFullscreen] = useState(false);

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

  const searching = Boolean(searchQuery.trim());
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

  const effectiveSearchField = searchFieldOptions.some((o) => o.key === searchField)
    ? searchField
    : ALL_FIELDS;

  const filteredRows = useMemo(
    () => filterRows(rows, columns, searchQuery, effectiveSearchField),
    [rows, columns, searchQuery, effectiveSearchField],
  );
  const limitActive = !searching && !showAll;
  const displayRows = limitActive ? filteredRows.slice(0, PREVIEW_LIMIT) : filteredRows;
  const canExpand = !searching && filteredRows.length > PREVIEW_LIMIT;

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
              <Stack spacing={1} sx={{ maxWidth: 560 }}>
                {selectedName ? (
                  <CopyableReportName name={meta?.title || selectedName} />
                ) : (
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                    No data view selected
                  </Typography>
                )}
                <Typography variant="body2" color="text.secondary">
                  {meta?.description || 'Choose a data view above to show its table.'}
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
                      shown: displayRows.length,
                      matched: filteredRows.length,
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
              <Button
                variant="outlined"
                startIcon={<FullscreenIcon />}
                onClick={() => setFullscreen(true)}
                disabled={!selectedName || columns.length === 0}
              >
                Fullscreen
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
              Choose a data view from the picker above.
            </Typography>
          ) : columns.length === 0 || rows.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No snapshot yet. Click Refresh to run the generator for the selected date range.
            </Typography>
          ) : (
            <>
              <TableContainer
                component={Paper}
                sx={{ maxHeight: fullscreen ? 'calc(100vh - 200px)' : (isSampleDetail ? 560 : 360) }}
              >
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
                    {displayRows.map((row, index) => {
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
                    {showAll ? 'Show fewer rows' : `Show all ${filteredRows.length} rows`}
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

      <Dialog
        fullScreen
        open={fullscreen}
        onClose={() => setFullscreen(false)}
      >
        <AppBar sx={{ position: 'relative' }} color="default" elevation={1}>
          <Toolbar>
            <Typography variant="h6" sx={{ flex: 1 }} noWrap>
              {meta?.title || selectedName || 'Data view'}
            </Typography>
            <Button
              color="inherit"
              href={selectedName ? dataReportCsvHref(selectedName) : undefined}
              disabled={!selectedName || rows.length === 0}
              sx={{ mr: 1 }}
            >
              Download CSV
            </Button>
            <IconButton
              edge="end"
              color="inherit"
              onClick={() => setFullscreen(false)}
              aria-label="Close fullscreen"
            >
              <CloseIcon />
            </IconButton>
          </Toolbar>
        </AppBar>
        <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          <Typography variant="body2" color="text.secondary">
            {meta?.description || ''}
            {(windowLabel || updatedAt) && (
              <>
                {' · '}
                {windowLabel ? `Snapshot: ${windowLabel}` : ''}
                {windowLabel && updatedAt ? ' · ' : ''}
                {updatedAt ? `Updated: ${cellText(updatedAt)}` : ''}
              </>
            )}
          </Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
            <TextField
              size="small"
              fullWidth
              label="Search rows"
              value={searchQuery}
              onChange={(event) => onSearchQueryChange(event.target.value)}
            />
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel>Field</InputLabel>
              <Select
                label="Field"
                value={effectiveSearchField}
                onChange={(event) => onSearchFieldChange(event.target.value)}
              >
                {searchFieldOptions.map((option) => (
                  <MenuItem key={option.key} value={option.key}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
          {columns.length === 0 || rows.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No snapshot yet. Click Refresh on the panel, then reopen fullscreen.
            </Typography>
          ) : (
            <TableContainer component={Paper} sx={{ flex: 1, maxHeight: 'calc(100vh - 180px)' }}>
              <Table stickyHeader size="small">
                <TableHead>
                  <TableRow>
                    {columns.map((column) => (
                      <TableCell key={column.key}>{column.label}</TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredRows.map((row, index) => {
                    const rowKey = row.name || row.sample_id || row.task_id || index;
                    return (
                      <TableRow key={rowKey} hover>
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
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Box>
      </Dialog>
    </Card>
  );
}

function Data() {
  const [catalog, setCatalog] = useState([]);
  const [selectedReport, setSelectedReport] = useState('');
  const [catalogNameQuery, setCatalogNameQuery] = useState('');
  const [catalogDateQuery, setCatalogDateQuery] = useState('');
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [windowInfo, setWindowInfo] = useState(null);
  const [appliedRange, setAppliedRange] = useState(null);
  const [draftStart, setDraftStart] = useState('');
  const [draftEnd, setDraftEnd] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchField, setSearchField] = useState(ALL_FIELDS);
  const [catalogError, setCatalogError] = useState('');
  const knownReportNamesRef = useRef(null);

  const refreshWindow = useCallback(async (target = null) => {
    const windowResult = await get_data_window(target);
    const win = windowResult?.window || null;
    setWindowInfo(win);
    if (win?.start_date && win?.end_date) {
      const nextRange = { start: win.start_date, end: win.end_date };
      setAppliedRange(nextRange);
      setDraftStart(win.start_date);
      setDraftEnd(win.end_date);
      persistDateRange(nextRange);
    }
  }, []);

  const refreshCatalog = useCallback(async ({ silent = false } = {}) => {
    if (!silent) {
      setLoadingCatalog(true);
    }
    try {
      const response = await get_data_reports();
      if (response?.status !== 'success') {
        throw new Error(response?.errors || 'Failed to load reports.');
      }
      const reports = response.reports || [];
      const names = reports.map((report) => report.name);
      setCatalog(reports);
      setSelectedReport((previous) => {
        const known = knownReportNamesRef.current;
        if (known) {
          const knownSet = new Set(known);
          const created = reports.find(
            (report) => !report.builtin && !knownSet.has(report.name),
          );
          if (created) {
            return created.name;
          }
          if (previous && !reports.some((report) => report.name === previous)) {
            return pickDefaultReport(reports, null);
          }
        }
        return pickDefaultReport(reports, previous);
      });
      knownReportNamesRef.current = names;
      setCatalogError('');
    } catch (err) {
      if (!silent) {
        setCatalogError(err.message || 'Failed to load reports.');
      }
    } finally {
      if (!silent) {
        setLoadingCatalog(false);
      }
    }
  }, []);

  useEffect(() => {
    refreshWindow(loadPersistedDateRange());
    refreshCatalog();
  }, [refreshWindow, refreshCatalog]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      refreshCatalog({ silent: true });
    }, CATALOG_POLL_MS);
    return () => window.clearInterval(timer);
  }, [refreshCatalog]);

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
    return opts;
  }, []);

  return (
    <Stack spacing={2}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Box>
          <Typography variant="h5">Data</Typography>
          <Typography variant="body2" color="text.secondary">
            Registry-backed reports. Create, change, or remove custom tables from Cursor with{' '}
            <Typography component="span" variant="body2" sx={{ fontFamily: 'monospace' }}>
              /alab-data-report
            </Typography>
            . Open shows the last snapshot; Refresh re-runs the generator for the selected date range.
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

      <Alert severity="info" variant="outlined">
        In Cursor, run{' '}
        <Typography component="span" sx={{ fontFamily: 'monospace', fontWeight: 600 }}>
          /alab-data-report
        </Typography>
        {' '}
        to create, change, or delete a table. Enable the{' '}
        <Typography component="span" sx={{ fontFamily: 'monospace' }}>
          alab-data-reports
        </Typography>
        {' '}
        MCP (dashboard on 8895). This page polls the catalog so new reports appear automatically.
      </Alert>

      {catalogError && <Alert severity="error">{catalogError}</Alert>}
      {loadingCatalog && <CircularProgress size={28} />}

      <ReportPicker
        catalog={catalog}
        selectedName={selectedReport}
        onSelectName={setSelectedReport}
        nameQuery={catalogNameQuery}
        onNameQueryChange={setCatalogNameQuery}
        dateQuery={catalogDateQuery}
        onDateQueryChange={setCatalogDateQuery}
      />

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={1.5}
          alignItems={{ xs: 'stretch', sm: 'center' }}
        >
          <TextField
            size="small"
            fullWidth
            label="Search table rows"
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

      <ReportViewer
        catalog={catalog}
        selectedName={selectedReport}
        appliedRange={appliedRange}
        searchQuery={searchQuery}
        searchField={searchField}
        onSearchQueryChange={setSearchQuery}
        onSearchFieldChange={setSearchField}
      />
    </Stack>
  );
}

export default Data;
