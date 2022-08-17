import React, { useEffect, useState } from 'react';
import Devices from './components/Devices';
import Experiments from './components/Experiments';
import styled from 'styled-components';
import { useLocation, Link } from "react-router-dom";
import { Box, Divider, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, FormControl, FormControlLabel, Switch } from '@mui/material';
import PrecisionManufacturingIcon from '@mui/icons-material/PrecisionManufacturing';
import FireplaceIcon from '@mui/icons-material/Fireplace';
import NotificationsIcon from '@mui/icons-material/Notifications';
import UserInputs from './components/UserInput';
import Badge from '@mui/material/Badge';
import { grey } from '@mui/material/colors';
import { get_pending_userinputrequests } from '../api_routes';

const StyledDashboardDiv = styled.div`
  height: calc(100vh - 60px);
  display: flex;
`;

const LinkedButton = styled(Link)`
  width: 100%;
  color: inherit;
  text-decoration: inherit;
  cursor: inherit;

  .active {
    background-color: #eaeaea;
  }

  .list-button-round {
    border-radius: 12px;
  }
`;

const pullerWidth = 12;
const drawerWidth = 240;

const StyledBox = styled(Box)(() => ({
  // backgroundColor: theme.palette.mode === 'light' ? '#fff' : grey[800],
  // backgroundColor: grey[50],
}));

const Puller = styled(Box)(() => ({
  width: pullerWidth / 2,
  height: 60,
  // backgroundColor: theme.palette.mode === 'light' ? grey[300] : grey[900],
  backgroundColor: grey[800],
  borderRadius: 3,
  position: 'absolute',
  // left: 8,
  // top: 'calc(50% - 15px)',
}));

function Sidebar({ hoverForId, setHoverForId, handleHoverForIdChange }) {
  const [numUserInputRequests, setNumUserInputRequests] = useState(0);
  const { hash } = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
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
    </List>



  )
  useEffect(() => {
    const interval = setInterval(() => {
      get_pending_userinputrequests().then(result => {
        var numRequests = 0;
        for (let requests of Object.values(result.pending)) {
          numRequests += requests.length;
        }
        setNumUserInputRequests(numRequests);
      })
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box sx={{ display: "flex" }}>
      <StyledBox
        sx={{
          position: 'absolute',
          borderTopLeftRadius: 8,
          borderTopRightRadius: 8,
          visibility: 'visible',
          width: pullerWidth,
          height: 'calc(100% - 60px)',
          top: 60,
          // right: -,
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
          width: drawerWidth, minWidth: "15%", flexShrink: 0, margin: "12px 0",
          [`& .MuiDrawer-paper`]: { width: 300, boxSizing: 'border-box', display: "contents", padding: "8px" }
        }}>
        {drawerContents}
      </Drawer>
    </Box >
  )
}

function Dashboard() {
  const { hash } = useLocation();
  const [hoverForId, setHoverForId] = useState(false);


  const handleHoverForIdChange = (checked) => {
    setHoverForId(checked);
  }

  const SwitchContent = () => {
    console.log(hash)
    switch (hash) {
      case "#device":
        return <Devices hoverForId={hoverForId} />;
      case "#userinput":
        return <UserInputs hoverForId={hoverForId} />
      case "#experiment":
      case "":
        return <Experiments hoverForId={hoverForId} />
      default:
        return null
    }
  }

  return (
    <StyledDashboardDiv>
      <Sidebar hoverForId={hoverForId} setHoverForId={setHoverForId} handleHoverForIdChange={(event) => { handleHoverForIdChange(event.target.checked) }} />
      <Box component="main" sx={{ flexGrow: 1, margin: "16px 12px" }}>
        <SwitchContent />
      </Box>
    </StyledDashboardDiv>
  )
}

export default Dashboard;