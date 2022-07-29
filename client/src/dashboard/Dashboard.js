import React, { useState } from 'react';
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

const STATUS_API = "/api/status";

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
    task: "6196fc9b5d573f2efdd8d98c",
    samples: {
      position1: [
        "6196fc9b5d573f2efdd8d98c",
        "6196fc9b5d573f2efdd8d98c",
      ]
    }
  }, {
    name: "scale",
    type: "Scale",
    status: "IDLE",
    task: "null",
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

function Dashboard() {
  const [statusData, setStatusData] = useState(initialData);
  const { hash } = useLocation();

  useInterval(() => {
    fetch(STATUS_API)
      .then(res => res.json())
      .then(result => {
        setStatusData(result);
      })
  }, 1000);

  const SwitchContent = () => {
    console.log(hash)
    switch (hash) {
      case "#device":
        return <Devices devices={statusData.devices} />
      case "#userinput":
        return <UserInputs userinputs={statusData.userinputrequests} />
      case "#experiment":
      case "":
        return <Experiments experiments={statusData.experiments} />
      default:
        return null
    }
  }

  return (
    <StyledDashboardDiv>
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
                    <Badge badgeContent={statusData.userinputrequests.length} color="error">
                      <NotificationsIcon color="action" />
                    </Badge>                  </ListItemIcon>
                  <ListItemText primary="User Input Requests" />

                </ListItemButton>
              </LinkedButton>
            </ListItem>
          </List>
        </Drawer>
      </Box>
      <Box component="main" sx={{ flexGrow: 1, margin: "16px 12px" }}>
        <SwitchContent />
      </Box>
    </StyledDashboardDiv>
  )
}

export default Dashboard;