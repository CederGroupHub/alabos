import React, { useCallback, useEffect, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
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

function DataSection({ title, description, rows, columns, downloadHref, loading }) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 2 }}>
            <Box>
              <Typography variant="h6">{title}</Typography>
              <Typography variant="body2" color="text.secondary">{description}</Typography>
            </Box>
            <Button href={downloadHref} variant="outlined">
              Download CSV
            </Button>
          </Box>
          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
              <CircularProgress size={28} />
            </Box>
          ) : rows.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No rows for this month. Try an older month or wait for new samples/tasks to complete.
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
                  {rows.slice(0, 25).map((row, index) => (
                    <TableRow key={index}>
                      {columns.map((column) => (
                        <TableCell key={column.key}>
                          {Array.isArray(row[column.key]) ? row[column.key].join(", ") : String(row[column.key] ?? "")}
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

function Data() {
  const [sampleSummary, setSampleSummary] = useState([]);
  const [powderDosing, setPowderDosing] = useState([]);
  const [taskOutcome, setTaskOutcome] = useState([]);
  const [loading, setLoading] = useState(true);
  const [windowInfo, setWindowInfo] = useState(null);
  const [month, setMonth] = useState(null);

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
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
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
          <Typography variant="body1" sx={{ minWidth: 140, textAlign: "center" }}>
            {windowInfo?.label || "Loading..."}
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

      <DataSection
        title="Sample Summary"
        description="Samples created during the selected month."
        rows={sampleSummary}
        loading={loading}
        downloadHref={dataDownloadHref("/sample_summary.csv", month)}
        columns={[
          { key: "sample_id", label: "Sample ID" },
          { key: "name", label: "Name" },
          { key: "position", label: "Position" },
          { key: "last_position", label: "Last Position" },
          { key: "metadata_keys", label: "Metadata Keys" },
        ]}
      />

      <DataSection
        title="Powder Dosing Actuals"
        description="Flattened per-sample Labman dosing results for the selected month."
        rows={powderDosing}
        loading={loading}
        downloadHref={dataDownloadHref("/powder_dosing_actuals.csv", month)}
        columns={[
          { key: "sample_name", label: "Sample" },
          { key: "powder_name", label: "Powder" },
          { key: "target_mass", label: "Target Mass" },
          { key: "dose_mass", label: "Actual Dose Mass" },
          { key: "dose_head_position", label: "Head Position" },
          { key: "dose_timestamp", label: "Dose Timestamp" },
        ]}
      />

      <DataSection
        title="Task Outcome Log"
        description="Task status and result-key overview for the selected month."
        rows={taskOutcome}
        loading={loading}
        downloadHref={dataDownloadHref("/task_outcome_log.csv", month)}
        columns={[
          { key: "task_id", label: "Task ID" },
          { key: "type", label: "Type" },
          { key: "status", label: "Status" },
          { key: "sample_names", label: "Samples" },
          { key: "result_keys", label: "Result Keys" },
        ]}
      />
    </Stack>
  );
}

export default Data;
