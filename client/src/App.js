import React, { useState } from "react";
import SubmitExp from "./submit_exp/SubmitExp";
import Dashboard from './dashboard/Dashboard';
import {
  Alert,
  AppBar,
  Button,
  Chip,
  CssBaseline,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import PriorityHighIcon from "@mui/icons-material/PriorityHigh";
import RefreshIcon from "@mui/icons-material/Refresh";
import styled from "styled-components";
import { Routes, Route, NavLink, BrowserRouter } from "react-router-dom";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import alabLogo from "./alab_logo.png";
import { LabReadinessProvider, useLabReadiness } from "./LabReadiness";
import { submit_feedback } from "./api_routes";

const headerIconButtonSx = {
  color: "#f5fbff",
  border: "1px solid rgba(255, 255, 255, 0.22)",
  backgroundColor: "rgba(255, 255, 255, 0.06)",
  "&:hover": {
    backgroundColor: "rgba(255, 255, 255, 0.14)",
  },
};

const theme = createTheme({
    palette: {
        primary: {
            main: "#1976d2",
            dark: "#1565c0",
            light: "#42a5f5",
            contrastText: "#ffffff",
        },
        error: {
            main: "#d32f2f",
            dark: "#b71c1c",
            light: "#ef5350",
            contrastText: "#ffffff",
        },
        info: {
            main: "#1976d2",
            dark: "#1565c0",
            light: "#42a5f5",
            contrastText: "#ffffff",
        },
        warning: {
            main: "#d32f2f",
            dark: "#b71c1c",
            light: "#ef5350",
            contrastText: "#ffffff",
        },
    },
    components: {
        MuiButton: {
            styleOverrides: {
                root: {
                    textTransform: "none",
                },
            },
        },
        MuiSwitch: {
            styleOverrides: {
                switchBase: {
                    "&.Mui-checked": {
                        color: "#1976d2",
                    },
                    "&.Mui-checked + .MuiSwitch-track": {
                        backgroundColor: "#1976d2",
                    },
                },
            },
        },
    },
});

const StyledAppBar = styled(AppBar)`
  height: 88px !important;
  background: linear-gradient(135deg, #183245 0%, #24465d 52%, #31556d 100%) !important;
  box-shadow: 0 18px 40px rgba(14, 29, 40, 0.18) !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: row !important;
  align-items: center;
  justify-content: space-between;
  font-family: "Roboto", sans-serif;
  padding: 0 30px;

  a {
    color: inherit;
    text-decoration: none;
  }
`;

const StyledLogo = styled.img`
  height: 100%;
  width: 100%;
  border-radius: 0;
  object-fit: contain;
`;

const StyledLogoTile = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  height: 56px;
  width: 56px;
  border-radius: 16px;
  background-color: rgb(230, 240, 247) !important;
  padding: 6px;
  box-sizing: border-box;
  overflow: hidden;
  margin-right: 26px;
`;

function LabReadyChip() {
  const { labReady, labReadyLabel, deviceRpc } = useLabReadiness();
  const tooltip = labReady
    ? "Lab devices are ready for experiments and direct control."
    : deviceRpc?.detail
      ? `Waiting for device manager (${deviceRpc.detail}).`
      : "Waiting for device manager to finish starting.";
  return (
    <Tooltip title={tooltip}>
      <Chip
        label={labReadyLabel}
        size="small"
        sx={{
          fontWeight: 600,
          bgcolor: labReady ? "#43a047" : "rgba(255, 193, 7, 0.35)",
          color: labReady ? "#ffffff" : "#f5fbff",
          border: labReady
            ? "1px solid #66bb6a"
            : "1px solid rgba(255,255,255,0.25)",
          boxShadow: labReady
            ? "0 0 0 1px rgba(102, 187, 106, 0.35)"
            : "none",
        }}
      />
    </Tooltip>
  );
}

function FeedbackDialog({ open, onClose }) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  const handleClose = () => {
    if (busy) return;
    setMessage("");
    setError("");
    setSent(false);
    onClose();
  };

  const handleSend = async () => {
    const trimmed = message.trim();
    if (!trimmed) {
      setError("Please write a short message.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const response = await submit_feedback(
        trimmed,
        window.location.pathname || "/"
      );
      if (response?.status !== "success") {
        throw new Error(response?.reason || "Failed to send feedback.");
      }
      setSent(true);
      setMessage("");
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      fullWidth
      maxWidth="sm"
      disableEscapeKeyDown={busy}
    >
      <DialogTitle>Send software feedback</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Describe a software or dashboard issue. This messages the software team
          on Slack (not the lab alert channel).
        </Typography>
        {sent ? (
          <Alert severity="success">Feedback sent. Thank you.</Alert>
        ) : (
          <TextField
            autoFocus
            fullWidth
            multiline
            minRows={4}
            label="Message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            disabled={busy}
            inputProps={{ maxLength: 4000 }}
          />
        )}
        {error ? (
          <Alert severity="error" sx={{ mt: 1.5 }}>
            {error}
          </Alert>
        ) : null}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={busy}>
          {sent ? "Close" : "Cancel"}
        </Button>
        {!sent ? (
          <Button
            onClick={handleSend}
            variant="contained"
            disabled={busy}
          >
            {busy ? "Sending…" : "Send"}
          </Button>
        ) : null}
      </DialogActions>
    </Dialog>
  );
}

function AppShell() {
  const [feedbackOpen, setFeedbackOpen] = useState(false);

  return (
    <>
      <StyledAppBar position="sticky">
        <div style={{ display: "flex", alignItems: "center" }}>
          <NavLink to="/">
            <StyledLogoTile>
              <StyledLogo src={alabLogo} />
            </StyledLogoTile>
          </NavLink>
          <Typography
            variant="h5"
            sx={{
              fontWeight: 700,
              letterSpacing: "0.08em",
              ml: 0.5,
              color: "#f5fbff",
              textTransform: "uppercase",
              fontSize: { xs: "1.35rem", sm: "1.62rem" },
            }}
          >
            A-Lab
          </Typography>
        </div>
        <div
          id="user-input-banner-slot"
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            minWidth: 0,
            padding: "0 16px",
            alignSelf: "stretch",
          }}
        />
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <LabReadyChip />
          <Tooltip title="Refresh page (Ctrl+R)">
            <IconButton
              aria-label="Refresh page"
              onClick={() => window.location.reload()}
              size="medium"
              sx={headerIconButtonSx}
            >
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Send software feedback">
            <IconButton
              aria-label="Send software feedback"
              onClick={() => setFeedbackOpen(true)}
              size="medium"
              sx={headerIconButtonSx}
            >
              <PriorityHighIcon />
            </IconButton>
          </Tooltip>
        </div>
      </StyledAppBar>
      <FeedbackDialog
        open={feedbackOpen}
        onClose={() => setFeedbackOpen(false)}
      />
      <Routes>
        <Route path="/*" element={<Dashboard />} />
        {/* <Route path="new-experiment" element={<SubmitExp />} /> */}
      </Routes>
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <LabReadinessProvider>
          <AppShell />
        </LabReadinessProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
