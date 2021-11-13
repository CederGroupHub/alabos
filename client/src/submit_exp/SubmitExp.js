import React, {useState} from 'react';
import ExperimentFlow from "./components/ExperimentFlow";
import ControlPanel from './components/ControlPanel';
import {Container} from '@mui/material';
import styled from 'styled-components';
import {grey} from '@mui/material/colors';

const MainExpDiv = styled.div`
    display: flex;
    height: calc(100vb-60px);
`;

const ControlPanelContainer = styled.div`
    background-color: ${grey[100]};
    width: 24%;
    min-width: 320px;
    max-width: 400px;
    border-right: 1.2px solid ${grey[300]};
`;

const FlowPanelContainer = styled.div`
    flex: 1 0 0
`;

function SubmitExp() {
    const [sampleNames, setSampleNames] = useState([]);

    return (
        <MainExpDiv>
            <ControlPanelContainer>
                <ControlPanel sampleNames={sampleNames} setSampleNames={setSampleNames}/>
            </ControlPanelContainer>
            <FlowPanelContainer>
                <ExperimentFlow sampleNames={sampleNames}/>
            </FlowPanelContainer>
        </MainExpDiv>
    )
}

export default SubmitExp;
