import React, { useEffect, useState } from 'react';
import Devices from './components/Devices';
import Experiments from './components/Experiments';
import styled from 'styled-components';
import useInterval from '@use-it/interval';
import { useLocation, Link } from "react-router-dom";
import { Box, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText } from '@mui/material';
import PrecisionManufacturingIcon from '@mui/icons-material/PrecisionManufacturing';
import FireplaceIcon from '@mui/icons-material/Fireplace';
import NotificationsIcon from '@mui/icons-material/Notifications';
import UserInputs from './components/UserInput';
import Badge from '@mui/material/Badge';

const STATUS_API = process.env.NODE_ENV === "production" ? "/api/status" : "http://localhost:8896/api/status";
const PENDING_IDS_API = process.env.NODE_ENV === "production" ? "/api/userinput/pending" : "http://localhost:8896/api/userinput/pending";


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

const initialData = process.env.NODE_ENV === 'production' ? { devices: [], experiments: [], userinputrequests: [] } : {
  devices: [{
    name: "furnace",
    type: "Furnace",
    status: "OCCUPIED",
    message: "test_message",
    task: "6196fc9b5d573f2efdd8d98c",
    samples: {
      position1: []
    }
  }, {
    name: "scale",
    type: "Scale",
    status: "IDLE",
    task: "null",
    message: "test_message",
    samples: {
      position1: [
        "6196fc9b5d573f2efdd8d98c",
        "6196fc9b5d573f2efdd8d98c",
      ],
      position2: [
        "6196fc9b5d573f2efdd8d98c",
        "6196fc9b5d573f2efdd8d98c",
      ]
    }
  }, {
    name: "robot_arm",
    type: "RobotArm",
    status: "OCCUPIED",
    task: "6196fc9b5d573f2efdd8d98c",
    message: "test_message",
    samples: {
      position1: [
        "6196fc9b5d573f2efdd8d98c",
        "6196fc9b5d573f2efdd8d98c",
      ],
      position2: [
        "6196fc9b5d573f2efdd8d98c",
        "6196fc9b5d573f2efdd8d98c",
      ]
    }
  }], experiments: [{
    name: "Firing baking soda",
    id: "xxxxxx",
    samples: [{ name: "soda", id: "fdfdsf" }],
    tasks: [
      { id: "6196fc9b5d573f2efdd8d989", status: "COMPLETED", type: "Starting" },
      { id: "6196fc9b5d573f2efdd8d98a", status: "COMPLETED", type: "Pouring" },
      { id: "6196fc9b5d573f2efdd8d98b", status: "COMPLETED", type: "Weighing" },
      { id: "6196fc9b5d573f2efdd8d98c", status: "RUNNING", type: "Heating" },
      { id: "6196fc9b5d573f2efdd8d98d", status: "WAITING", type: "Weighing" },
      { id: "6196fc9b5d573f2efdd8d98e", status: "WAITING", type: "Ending" },
    ]
  }],
  userinputrequests: [{ id: "6196fc9b5d573f2efdd8d981", status: "pending", task_id: "6196fc9b5d573f2efdd8d989", prompt: "Move sample1 to tray1/slot/0" }]
};

function Sidebar() {
  const [numUserInputRequests, setNumUserInputRequests] = useState(0);
  const { hash } = useLocation();

  useEffect(() => {
    const interval = setInterval(() => {
      fetch(PENDING_IDS_API, { mode: 'cors' })
        .then(res => res.json())
        .then(result => {
          setNumUserInputRequests(result.pending_requests.length);
        })
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box sx={{ display: "flex" }}>
      <Drawer variant='permanent' sx={{
        width: 280, minWidth: "15%", flexShrink: 0, margin: "12px 0",
        [`& .MuiDrawer-paper`]: { width: 300, boxSizing: 'border-box', display: "contents", padding: "8px" }
      }}>
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
        </List>
      </Drawer>
    </Box>
  )
}

function Dashboard() {
  // const [statusData, setStatusData] = useState(initialData);
  const { hash } = useLocation();

  // useEffect(() => {
  //   const interval = setInterval(() => {
  //     fetch(STATUS_API, { mode: 'cors' })
  //       .then(res => res.json())
  //       .then(result => {
  //         setStatusData(result);
  //       })
  //   }, 1000);
  //   return () => clearInterval(interval);
  // }, []);

  // useInterval(() => {
  //   fetch(STATUS_API, { mode: 'cors' })
  //     .then(res => res.json())
  //     .then(result => {
  //       setStatusData(result);
  //     })
  // }, 1000);

  const SwitchContent = () => {
    console.log(hash)
    switch (hash) {
      case "#device":
        // return <Devices devices={statusData.devices} />
        return <Devices />;

      case "#userinput":
        return <UserInputs />
      case "#experiment":
      case "":
        return <Experiments />
      default:
        return null
    }
  }

  return (
    <StyledDashboardDiv>
      <Sidebar />
      <Box component="main" sx={{ flexGrow: 1, margin: "16px 12px" }}>
        <SwitchContent />
      </Box>
    </StyledDashboardDiv>
  )
}

export default Dashboard;