import SubmitExp from './submit_exp/SubmitExp';
import {AppBar} from '@mui/material';
import styled from 'styled-components';

const StyledAppBar = styled(AppBar)`
  height: 60px !important;
  box-shadow: 0px 2px 4px -1px rgb(0 0 0 / 14%), 0px 4px 5px 0px rgb(0 0 0 / 10%), 0px 1px 5px 0px rgb(0 0 0 / 6%) !important;
  display: flex;
  justify-content: center;
  `;

function App() {
    return (
        <>
            <StyledAppBar position="relative">
                <div style={{
                    display: "flex",
                    alignItems: "center",
                    fontWeight: 500,
                    fontSize: "1.3em",
                    margin: "0 16px"
                }}>
                    Alab Management - New Experiment
                </div>
            </StyledAppBar>
            <SubmitExp/>
        </>
    );
}

export default App;
