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
    // const [statusData, setStatusData] = useState({devices: [], experiments: [{
    //   name: "xxxxx",
    //   id: "xxxxxx",
    //   samples: [{name: "xxx", id: "fdfdsf"}],
    //   tasks: [{id: "xxxx", status: "ERROR", type: "Heating"},
    //           {id: "xxxx", status: "RUNNING", type: "Heating"}]
    // }, {
    //   name: "xxxxx",
    //   id: "xxxxxx",
    //   samples: [{name: "xxx", id: "fdfdsf"}],
    //   tasks: [{id: "xxxx", status: "RUNNING", type: "Heating"},
    //           {id: "xxxx", status: "READY", type: "Heating"}]
    // }]});

    const [statusData, setStatusData] = useState({devices: [], experiments: []});

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