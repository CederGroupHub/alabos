import React from 'react';
import { Card, CardContent, Stack, Typography } from '@mui/material';

function DeviceControl() {
  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.5}>
          <Typography variant="h5">Device Control</Typography>
          <Typography variant="body2" color="text.secondary">
            This page is reserved for curated manual device commands from the dashboard.
          </Typography>
          <Typography variant="body2">
            No controls are exposed yet. The next step will be to add an allowlisted command surface rather than raw driver access.
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default DeviceControl;
