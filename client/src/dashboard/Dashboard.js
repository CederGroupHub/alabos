import React, {useState} from 'react';
import Devices from './components/Devices';
import Experiments from './components/Experiments';
import styled from 'styled-components';
import useInterval from '@use-it/interval';

const STATUS_API = "/api/status";

const StyledDashboardDiv = styled.div`
  margin: 12px 8px;
  height: calc(100vh - 60px - 24px);
  display: flex;
`;

const StyledDevicesDiv = styled.div`
  height: 100%;
  width: calc(50vw - 20px);
  margin-right: 12px;
`;

const StyledExperimentsDiv = styled.div`
  height: 100%;
  width: calc(50vw - 8px);
`;

function Dashboard() {
    const [statusData, setStatusData] = useState({
        devices: [{
            name: "furnace",
            type: "Furnace",
            status: "IDLE",
            task: "null",
        }, {
            name: "scale",
            type: "Scale",
            status: "IDLE",
            task: "null",
        }, {
            name: "robot_arm",
            type: "RobotArm",
            status: "OCCUPIED",
            task: "6196fc9b5d573f2efdd8d98d",
        }], experiments: [{
            name: "Firing baking soda",
            id: "xxxxxx",
            samples: [{name: "soda", id: "fdfdsf"}],
            tasks: [
                {id: "6196fc9b5d573f2efdd8d989", status: "COMPLETED", type: "Starting"},
                {id: "6196fc9b5d573f2efdd8d98a", status: "COMPLETED", type: "Pouring"},
                {id: "6196fc9b5d573f2efdd8d98b", status: "COMPLETED", type: "Weighing"},
                {id: "6196fc9b5d573f2efdd8d98c", status: "COMPLETED", type: "Heating"},
                {id: "6196fc9b5d573f2efdd8d98d", status: "RUNNING", type: "Weighing"},
                {id: "6196fc9b5d573f2efdd8d98e", status: "WAITING", type: "Ending"},
            ]
        }]
    });

    // const [statusData, setStatusData] = useState({devices: [], experiments: []});

    useInterval(() => {
        fetch(STATUS_API)
            .then(res => res.json())
            .then(result => {
                setStatusData(result);
            })
    }, 1000);

    return (
        <StyledDashboardDiv>
            <StyledDevicesDiv>
                <Devices devices={statusData.devices}/>
            </StyledDevicesDiv>
            <StyledExperimentsDiv>
                <Experiments experiments={statusData.experiments}/>
            </StyledExperimentsDiv>
        </StyledDashboardDiv>
    )
}

export default Dashboard;