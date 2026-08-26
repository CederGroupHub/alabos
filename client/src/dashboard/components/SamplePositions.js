import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  ButtonGroup,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Snackbar,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import styled from 'styled-components';
import { clear_sample_position, get_sample_position_racks, place_sample_in_position } from '../../api_routes';

const RackContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
`;

const SlotGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
`;

function slotStatusColor(slot) {
  switch (slot.status) {
    case "OCCUPIED":
      return "#e8f5e9";
    case "LOCKED":
      return "#fff8e1";
    default:
      return "#fafafa";
  }
}

function PlaceSampleDialog({ open, onClose, position, unplacedSamples, onSubmit }) {
  const [mode, setMode] = useState("new");
  const [sampleName, setSampleName] = useState("");
  const [sampleId, setSampleId] = useState("");

  useEffect(() => {
    if (open) {
      setMode(unplacedSamples.length > 0 ? "existing" : "new");
      setSampleName("");
      setSampleId("");
    }
  }, [open, unplacedSamples]);

  const handleSubmit = () => {
    if (mode === "existing" && sampleId) {
      onSubmit(position, { sample_id: sampleId });
      return;
    }
    if (mode === "new" && sampleName.trim()) {
      onSubmit(position, { sample_name: sampleName.trim() });
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Place Sample</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <Typography variant="body2">Target position: {position}</Typography>
          {unplacedSamples.length > 0 && (
            <Tabs value={mode} onChange={(_event, value) => setMode(value)}>
              <Tab label="Use Existing Sample" value="existing" />
              <Tab label="Create New Sample" value="new" />
            </Tabs>
          )}
          {mode === "existing" && unplacedSamples.length > 0 ? (
            <FormControl fullWidth>
              <InputLabel id="existing-sample-label">Unplaced Sample</InputLabel>
              <Select
                labelId="existing-sample-label"
                label="Unplaced Sample"
                value={sampleId}
                onChange={(event) => setSampleId(event.target.value)}
              >
                {unplacedSamples.map((sample) => (
                  <MenuItem key={sample.sample_id} value={sample.sample_id}>
                    {sample.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          ) : (
            <TextField
              fullWidth
              label="Sample Name"
              value={sampleName}
              onChange={(event) => setSampleName(event.target.value)}
            />
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={(mode === "existing" && !sampleId) || (mode === "new" && !sampleName.trim())}
        >
          Place Sample
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function SlotCard({ slot, onPlace, onClear }) {
  const occupied = slot.status === "OCCUPIED";
  return (
    <Card variant="outlined" sx={{ bgcolor: slotStatusColor(slot), minHeight: 165 }}>
      <CardContent>
        <Stack spacing={1.25}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="subtitle1">Slot {slot.slot_number}</Typography>
            <Chip label={slot.status} size="small" />
          </Stack>
          <Typography variant="body2" sx={{ wordBreak: "break-word" }}>
            {slot.name}
          </Typography>
          {slot.sample ? (
            <Box>
              <Typography variant="body2"><b>{slot.sample.name}</b></Typography>
              <Typography variant="caption" color="text.secondary">
                {slot.sample.sample_id}
              </Typography>
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No sample present.
            </Typography>
          )}
          {slot.locked_by_task_id && !occupied && (
            <Typography variant="caption" color="text.secondary">
              Locked by task {slot.locked_by_task_id}
            </Typography>
          )}
          <ButtonGroup size="small" variant="outlined">
            <Button onClick={() => onPlace(slot.name)} disabled={slot.status !== "EMPTY"}>
              Place
            </Button>
            <Button onClick={() => onClear(slot.name)} disabled={!occupied}>
              Clear
            </Button>
          </ButtonGroup>
        </Stack>
      </CardContent>
    </Card>
  );
}

function SamplePositions() {
  const [racks, setRacks] = useState([]);
  const [unplacedSamples, setUnplacedSamples] = useState([]);
  const [selectedPosition, setSelectedPosition] = useState(null);
  const [message, setMessage] = useState(null);

  const refresh = () => {
    get_sample_position_racks().then((result) => {
      if (result && result.status === "success") {
        setRacks(result.racks);
        setUnplacedSamples(result.unplaced_samples || []);
      }
    });
  };

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
  }, []);

  const handlePlace = async (position, payload) => {
    const res = await place_sample_in_position(position, payload);
    const result = await res.json();
    if (result.status === "success") {
      setSelectedPosition(null);
      setMessage({ severity: "success", text: `Updated ${position}.` });
      refresh();
    } else {
      setMessage({ severity: "error", text: result.errors || "Failed to place sample." });
    }
  };

  const handleClear = async (position) => {
    const res = await clear_sample_position(position);
    const result = await res.json();
    if (result.status === "success") {
      setMessage({ severity: "success", text: `Cleared ${position}.` });
      refresh();
    } else {
      setMessage({ severity: "error", text: result.errors || "Failed to clear position." });
    }
  };

  return (
    <RackContainer>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Box>
          <Typography variant="h5">Sample Positions</Typography>
          <Typography variant="body2" color="text.secondary">
            Manual rack occupancy editor for DASH loading positions.
          </Typography>
          <Typography variant="body2" color="error.main">
            This page is under active development and is not yet fully operational.
          </Typography>
        </Box>
        <Button variant="outlined" onClick={refresh}>Refresh</Button>
      </Box>

      {unplacedSamples.length > 0 && (
        <Alert severity="info">
          There are {unplacedSamples.length} samples with no current position. You can place them into a rack slot from this page.
        </Alert>
      )}

      {racks.map((rack) => (
        <Card key={rack.device_name} variant="outlined">
          <CardContent>
            <Stack spacing={2}>
              <Box>
                <Typography variant="h6">{rack.display_name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {rack.device_name}
                </Typography>
              </Box>
              {Object.entries(rack.slot_groups).map(([groupName, slots]) => (
                <Box key={groupName}>
                  <Typography variant="subtitle1" sx={{ mb: 1 }}>
                    {groupName}
                  </Typography>
                  <SlotGrid>
                    {slots.map((slot) => (
                      <SlotCard
                        key={slot.name}
                        slot={slot}
                        onPlace={setSelectedPosition}
                        onClear={handleClear}
                      />
                    ))}
                  </SlotGrid>
                </Box>
              ))}
            </Stack>
          </CardContent>
        </Card>
      ))}

      <PlaceSampleDialog
        open={selectedPosition !== null}
        onClose={() => setSelectedPosition(null)}
        position={selectedPosition}
        unplacedSamples={unplacedSamples}
        onSubmit={handlePlace}
      />

      <Snackbar
        open={message !== null}
        autoHideDuration={4000}
        onClose={() => setMessage(null)}
      >
        {message ? <Alert severity={message.severity}>{message.text}</Alert> : null}
      </Snackbar>
    </RackContainer>
  );
}

export default SamplePositions;
