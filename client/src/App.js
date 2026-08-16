import SubmitExp from "./submit_exp/SubmitExp";
import Dashboard from './dashboard/Dashboard';
import { AppBar, Typography } from "@mui/material";
import styled from "styled-components";
import { Routes, Route, NavLink, BrowserRouter } from "react-router-dom";
import alabLogo from "./logo512.png";

const StyledAppBar = styled(AppBar)`
  height: 60px !important;
  box-shadow: 0px 2px 4px -1px rgb(0 0 0 / 14%),
    0px 4px 5px 0px rgb(0 0 0 / 10%), 0px 1px 5px 0px rgb(0 0 0 / 6%) !important;
  display: flex;
  flex-direction: row !important;
  align-items: center;
  font-family: roboto;
  padding: 0 20px;

  a {
    color: inherit;
    text-decoration: none;
  }
`;

const StyledLogo = styled.img`
  height: 45px;
  margin-right: 22px;
`;

function App() {
  return (
    <BrowserRouter>
      <StyledAppBar position="sticky">
        <div style={{ display: "flex", alignItems: "center" }}>
          <NavLink to="/"><StyledLogo src={alabLogo} /></NavLink>
          <Typography variant="h5" sx={{ fontWeight: 700, letterSpacing: "0.02em", ml: 0.5 }}>
            A-Lab
          </Typography>
        </div>
      </StyledAppBar>
      <Routes>
        <Route path="/*" element={<Dashboard />} />
        {/* <Route path="new-experiment" element={<SubmitExp />} /> */}
      </Routes>
    </BrowserRouter>
  );
}

export default App;
