import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
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
import { DATA_DOWNLOADS, get_powder_dosing_rows, get_sample_summary_rows, get_task_outcome_rows } from '../../api_routes';

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
              No rows yet. This export will populate once the relevant samples/tasks have run.
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

  const refresh = async () => {
    setLoading(true);
    const [sampleSummaryResult, powderDosingResult, taskOutcomeResult] = await Promise.all([
      get_sample_summary_rows(),
      get_powder_dosing_rows(),
      get_task_outcome_rows(),
    ]);
    setSampleSummary(sampleSummaryResult?.rows || []);
    setPowderDosing(powderDosingResult?.rows || []);
    setTaskOutcome(taskOutcomeResult?.rows || []);
    setLoading(false);
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <Stack spacing={2}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Box>
          <Typography variant="h5">Data</Typography>
          <Typography variant="body2" color="text.secondary">
            Curated Mongo-backed exports for operators and experimenters.
          </Typography>
        </Box>
        <Button variant="outlined" onClick={refresh}>Refresh</Button>
      </Box>

      <DataSection
        title="Sample Summary"
        description="Current sample inventory and basic metadata from the working lab database."
        rows={sampleSummary}
        loading={loading}
        downloadHref={DATA_DOWNLOADS.sampleSummary}
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
        description="Flattened per-sample Labman dosing results, including target and actual dispensed masses."
        rows={powderDosing}
        loading={loading}
        downloadHref={DATA_DOWNLOADS.powderDosing}
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
        description="Recent task status and result-key overview from the task collection."
        rows={taskOutcome}
        loading={loading}
        downloadHref={DATA_DOWNLOADS.taskOutcome}
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
