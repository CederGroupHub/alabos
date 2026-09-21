import React, { useEffect, useRef, useState } from 'react';
import Devices from './components/Devices';
import DeviceControl from './components/DeviceControl';
import DashControl from './components/DashControl';
import BftControl from './components/BftControl';
import MobileRobotControl from './components/MobileRobotControl';
import Data from './components/Data';
import Logs from './components/Logs';
import Experiments from './components/Experiments';
import SamplePositions from './components/SamplePositions';
import LabSettings from './components/LabSettings';
import styled from 'styled-components';
import { useLocation, Link } from "react-router-dom";
import { Alert, Box, Divider, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, FormControl, FormControlLabel, Snackbar, Switch, Typography } from '@mui/material';
import PrecisionManufacturingIcon from '@mui/icons-material/PrecisionManufacturing';
import FactoryIcon from '@mui/icons-material/Factory';
import FireplaceIcon from '@mui/icons-material/Fireplace';
import NotificationsIcon from '@mui/icons-material/Notifications';
import TableChartIcon from '@mui/icons-material/TableChart';
import ViewModuleIcon from '@mui/icons-material/ViewModule';
import SettingsRemoteIcon from '@mui/icons-material/SettingsRemote';
import SettingsIcon from '@mui/icons-material/Settings';
import BuildIcon from '@mui/icons-material/Build';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import ArticleIcon from '@mui/icons-material/Article';
import UserInputs from './components/UserInput';
import LabNotReadyGate from './components/LabNotReadyGate';
import Badge from '@mui/material/Badge';
import { get_pending_userinputrequests } from '../api_routes';
import { useLabReadiness } from '../LabReadiness';

const USER_INPUT_POLL_MS = 5000;
const USER_INPUT_BANNER_MS = 6000;
const USER_INPUT_PROMPT_PREVIEW_LEN = 120;

function collectPendingUserInputs(pending, experimentIdToName) {
  const items = [];
  for (const [experimentId, requests] of Object.entries(pending || {})) {
    const experimentName = (experimentIdToName && experimentIdToName[experimentId]) || experimentId;
    for (const request of requests || []) {
      if (!request?.id) {
        continue;
      }
      items.push({
        id: String(request.id),
        prompt: request.prompt || "",
        experimentName,
      });
    }
  }
  return items;
}

function truncatePrompt(prompt, maxLen = USER_INPUT_PROMPT_PREVIEW_LEN) {
  const text = String(prompt || "").replace(/\s+/g, " ").trim();
  if (text.length <= maxLen) {
    return text;
  }
  return `${text.slice(0, maxLen - 1)}…`;
}

const StyledDashboardDiv = styled.div`
  min-height: calc(100vh - 76px);
  display: flex;
  background:
    radial-gradient(circle at top left, rgba(117, 181, 214, 0.12), transparent 30%),
    linear-gradient(180deg, #f4f8fb 0%, #eef3f7 100%);
`;

const LinkedButton = styled(Link)`
  width: 100%;
  color: inherit;
  text-decoration: inherit;
  cursor: inherit;

  .list-button-round.active {
    background: linear-gradient(135deg, #203d51 0%, #2f5970 100%);
    color: #f8fcff;
    box-shadow: 0 10px 24px rgba(31, 61, 79, 0.18);
  }

  .list-button-round.active .MuiListItemIcon-root {
    color: #f8fcff;
  }

  .list-button-round.active:hover,
  .list-button-round.active.MuiListItemButton-root:hover {
    background: linear-gradient(135deg, #203d51 0%, #2f5970 100%);
    color: #f8fcff;
    box-shadow: 0 10px 24px rgba(31, 61, 79, 0.18);
  }

  .list-button-round.active:hover .MuiListItemIcon-root,
  .list-button-round.active.MuiListItemButton-root:hover .MuiListItemIcon-root {
    color: #f8fcff;
  }

  .list-button-round {
    border-radius: 14px;
    min-height: 48px;
    transition: background-color 160ms ease, box-shadow 160ms ease, color 160ms ease;
  }

  .list-button-round:hover,
  .list-button-round.MuiListItemButton-root:hover {
    background: rgba(35, 72, 93, 0.08);
  }
`;

const pullerWidth = 12;
const drawerWidth = 240;

const StyledBox = styled(Box)(() => ({
  backdropFilter: 'blur(8px)',
}));

const Puller = styled(Box)(() => ({
  width: pullerWidth / 2,
  height: 60,
  backgroundColor: '#28475c',
  borderRadius: 3,
  position: 'absolute',
}));

function Sidebar({ hoverForId, setHoverForId, handleHoverForIdChange, onOpenUserInputRequest }) {
  const [numUserInputRequests, setNumUserInputRequests] = useState(0);
  const [userInputBanner, setUserInputBanner] = useState(null);
  const knownUserInputIdsRef = useRef(null);
  const { hash } = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { labReady } = useLabReadiness();
  // const [hoverForId, setHoverForId] = useState(false);


  const drawerContents = (
    <List sx={{ [`& .MuiListItem-root`]: { padding: "4px 8px" } }}>
      <ListItem>
        <LinkedButton to="/#experiment">
          <ListItemButton className={hash === "#experiment" || hash === "" ? "active list-button-round" : "list-button-round"}>
            <ListItemIcon>
              <FireplaceIcon />
            </ListItemIcon>
            <ListItemText primary="Experiments" />
          </ListItemButton>
        </LinkedButton>
      </ListItem>
      <ListItem>
        <LinkedButton to="/#device">
          <ListItemButton className={hash === "#device" ? "active list-button-round" : "list-button-round"}>
            <ListItemIcon>
              <PrecisionManufacturingIcon />
            </ListItemIcon>
            <ListItemText primary="Devices" />
          </ListItemButton>
        </LinkedButton>
      </ListItem>
      <ListItem>
        <LinkedButton to="/#sample-positions">
          <ListItemButton className={hash === "#sample-positions" ? "active list-button-round" : "list-button-round"}>
            <ListItemIcon>
              <ViewModuleIcon />
            </ListItemIcon>
            <ListItemText primary="Sample Positions" />
          </ListItemButton>
        </LinkedButton>
      </ListItem>
      <ListItem>
        <LinkedButton to="/#data">
          <ListItemButton className={hash === "#data" ? "active list-button-round" : "list-button-round"}>
            <ListItemIcon>
              <TableChartIcon />
            </ListItemIcon>
            <ListItemText primary="Data" />
          </ListItemButton>
        </LinkedButton>
      </ListItem>
      <ListItem>
        <LinkedButton to="/#logs">
          <ListItemButton className={hash === "#logs" ? "active list-button-round" : "list-button-round"}>
            <ListItemIcon>
              <ArticleIcon />
            </ListItemIcon>
            <ListItemText primary="Logs" />
          </ListItemButton>
        </LinkedButton>
      </ListItem>
      <ListItem>
        <LinkedButton to="/#lab-settings">
          <ListItemButton className={hash === "#lab-settings" ? "active list-button-round" : "list-button-round"}>
            <ListItemIcon>
              <SettingsIcon />
            </ListItemIcon>
            <ListItemText primary="Lab settings" />
          </ListItemButton>
        </LinkedButton>
      </ListItem>
      <Divider />
      <ListItem>
        <LinkedButton to="/#userinput">
          <ListItemButton className={hash === "#userinput" ? "active list-button-round" : "list-button-round"}>
            <ListItemIcon>
              <Badge badgeContent={numUserInputRequests} color="error">
                <NotificationsIcon color="action" />
              </Badge>
            </ListItemIcon>
            <ListItemText primary="User Input Requests" />
          </ListItemButton>
        </LinkedButton>
      </ListItem>
      <Divider />
      <ListItem>
        <FormControl component="fieldset" variant="standard" sx={{ padding: "0px 16px" }}>
          <FormControlLabel
            control={
              <Switch checked={hoverForId} onChange={handleHoverForIdChange} name="Hover for ID" />
            }
            label="Hover for ID"
          />
        </FormControl>
      </ListItem>
      <Divider sx={{ mt: 1 }} />
      <ListItem sx={{ display: 'block', pt: 1.5, pb: 0.5, px: 2 }}>
        <Typography
          variant="caption"
          sx={{
            display: 'block',
            fontWeight: 700,
            color: '#355062',
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}
        >
          Direct hardware control
        </Typography>
        <Typography
          variant="caption"
          sx={{ display: 'block', color: '#5f7483', mt: 0.25, lineHeight: 1.35 }}
        >
          {labReady
            ? "For integration testing and debugging"
            : "Waiting for lab devices…"}
        </Typography>
      </ListItem>
      <Box sx={{ opacity: labReady ? 1 : 0.55 }}>
      <ListItem>
        <LinkedButton to="/#device-control">
          <ListItemButton className={hash === "#device-control" ? "active list-button-round" : "list-button-round"}>
            <ListItemIcon>
              <SettingsRemoteIcon />
            </ListItemIcon>
            <ListItemText primary="Device Control" />
          </ListItemButton>
        </LinkedButton>
      </ListItem>
      <ListItem>
        <LinkedButton to="/#mobile-robot-control">
          <ListItemButton className={hash === "#mobile-robot-control" ? "active list-button-round" : "list-button-round"}>
            <ListItemIcon>
              <SmartToyIcon />
            </ListItemIcon>
            <ListItemText primary="Mobile Robot Control" />
          </ListItemButton>
        </LinkedButton>
      </ListItem>
      <ListItem>
        <LinkedButton to="/#bft-control">
          <ListItemButton className={hash === "#bft-control" ? "active list-button-round" : "list-button-round"}>
            <ListItemIcon>
              <FactoryIcon />
            </ListItemIcon>
            <ListItemText primary="BFT Control" />
          </ListItemButton>
        </LinkedButton>
      </ListItem>
      <ListItem>
        <LinkedButton to="/#dash-control">
          <ListItemButton className={hash === "#dash-control" ? "active list-button-round" : "list-button-round"}>
            <ListItemIcon>
              <BuildIcon />
            </ListItemIcon>
            <ListItemText primary="DASH Control" />
          </ListItemButton>
        </LinkedButton>
      </ListItem>
      </Box>
    </List>



  )
  useEffect(() => {
    const pollPendingUserInputs = () => {
      get_pending_userinputrequests().then((result) => {
        if (!result?.pending) {
          return;
        }
        const items = collectPendingUserInputs(
          result.pending,
          result.experiment_id_to_name,
        );
        setNumUserInputRequests(items.length);

        const currentIds = new Set(items.map((item) => item.id));
        if (knownUserInputIdsRef.current === null) {
          knownUserInputIdsRef.current = currentIds;
          return;
        }

        const newItems = items.filter(
          (item) => !knownUserInputIdsRef.current.has(item.id),
        );
        knownUserInputIdsRef.current = currentIds;
        if (newItems.length === 0) {
          return;
        }

        const newest = newItems[newItems.length - 1];
        const preview = truncatePrompt(newest.prompt);
        setUserInputBanner({
          focusId: newest.id,
          title:
            newItems.length === 1
              ? "New user input request"
              : `${newItems.length} new user input requests`,
          detail: preview
            ? `${newest.experimentName}: ${preview}`
            : newest.experimentName,
        });
      });
    };

    pollPendingUserInputs();
    const interval = setInterval(pollPendingUserInputs, USER_INPUT_POLL_MS);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box sx={{ display: "flex" }}>
      <StyledBox
        sx={{
          position: 'absolute',
          borderTopLeftRadius: 10,
          borderTopRightRadius: 10,
          visibility: 'visible',
          width: pullerWidth,
          height: 'calc(100% - 76px)',
          top: 76,
          left: 0,
          display: { xs: "block", sm: "none" },
        }}
      >
        <Badge badgeContent={numUserInputRequests} color="error" sx={{
          left: 8,
          top: 'calc(50% - 30px)',
        }} onClick={() => setMobileOpen(true)}>
          <Puller onClick={() => setMobileOpen(true)} />
        </Badge>
      </StyledBox>
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile.
        }}
        sx={{
          display: { xs: 'block', sm: 'none' },
          '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
        }}
      >
        {drawerContents}
      </Drawer>
      <Drawer
        variant='permanent'
        sx={{
          display: { xs: "none", sm: "block" },
          width: drawerWidth, minWidth: "15%", flexShrink: 0, margin: "20px 0",
          [`& .MuiDrawer-paper`]: {
            width: 300,
            boxSizing: 'border-box',
            display: "contents",
            padding: "14px 12px",
          }
        }}>
        {drawerContents}
      </Drawer>
      <Snackbar
        open={Boolean(userInputBanner)}
        autoHideDuration={USER_INPUT_BANNER_MS}
        onClose={(_event, reason) => {
          if (reason === "clickaway") {
            return;
          }
          setUserInputBanner(null);
        }}
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
        sx={{ top: { xs: 16, sm: 84 } }}
      >
        {userInputBanner ? (
          <Alert
            severity="warning"
            variant="filled"
            icon={<NotificationsIcon fontSize="inherit" />}
            onClick={() => {
              if (typeof onOpenUserInputRequest === "function") {
                onOpenUserInputRequest(userInputBanner.focusId);
              }
              setUserInputBanner(null);
            }}
            sx={{
              cursor: "pointer",
              width: "100%",
              maxWidth: 560,
              boxShadow: "0 12px 28px rgba(33, 58, 75, 0.28)",
              alignItems: "flex-start",
            }}
          >
            <Typography variant="subtitle2" component="div">
              {userInputBanner.title}
            </Typography>
            <Typography variant="body2" component="div" sx={{ opacity: 0.95 }}>
              {userInputBanner.detail}
            </Typography>
            <Typography variant="caption" component="div" sx={{ mt: 0.5, opacity: 0.9 }}>
              Click to open and scroll to this request
            </Typography>
          </Alert>
        ) : null}
      </Snackbar>
    </Box >
  )
}

function Dashboard() {
  const { hash } = useLocation();
  const [hoverForId, setHoverForId] = useState(false);
  const [focusUserInputRequestId, setFocusUserInputRequestId] = useState(null);


  const handleHoverForIdChange = (checked) => {
    setHoverForId(checked);
  }

  const openUserInputRequest = (requestId) => {
    setFocusUserInputRequestId(requestId ? String(requestId) : null);
    if (window.location.hash !== "#userinput") {
      window.location.hash = "userinput";
    }
  };

  const SwitchContent = () => {
    switch (hash) {
      case "#device":
        return <Devices hoverForId={hoverForId} />;
      case "#sample-positions":
        return <SamplePositions />;
      case "#data":
        return <Data />;
      case "#logs":
        return <Logs />;
      case "#lab-settings":
        return <LabSettings />;
      case "#device-control":
        return (
          <LabNotReadyGate>
            <DeviceControl />
          </LabNotReadyGate>
        );
      case "#mobile-robot-control":
        return (
          <LabNotReadyGate>
            <MobileRobotControl />
          </LabNotReadyGate>
        );
      case "#bft-control":
        return (
          <LabNotReadyGate>
            <BftControl />
          </LabNotReadyGate>
        );
      case "#dash-control":
        return (
          <LabNotReadyGate>
            <DashControl />
          </LabNotReadyGate>
        );
      case "#userinput":
        return (
          <UserInputs
            hoverForId={hoverForId}
            focusRequestId={focusUserInputRequestId}
            onFocusHandled={() => setFocusUserInputRequestId(null)}
          />
        );
      case "#experiment":
      case "":
        return <Experiments hoverForId={hoverForId} />
      default:
        return null
    }
  }

  return (
    <StyledDashboardDiv>
      <Sidebar
        hoverForId={hoverForId}
        setHoverForId={setHoverForId}
        handleHoverForIdChange={(event) => { handleHoverForIdChange(event.target.checked) }}
        onOpenUserInputRequest={openUserInputRequest}
      />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          margin: "20px 18px 22px 8px",
          p: { xs: 1.5, sm: 2.5 },
          borderRadius: "24px",
          background: "rgba(255, 255, 255, 0.72)",
          border: "1px solid rgba(34, 62, 81, 0.08)",
          boxShadow: "0 18px 44px rgba(33, 58, 75, 0.08)",
          backdropFilter: "blur(10px)",
        }}
      >
        <SwitchContent />
      </Box>
    </StyledDashboardDiv>
  )
}

export default Dashboard;
