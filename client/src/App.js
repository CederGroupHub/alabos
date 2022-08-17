import SubmitExp from "./submit_exp/SubmitExp";
import Dashboard from './dashboard/Dashboard';
import { AppBar } from "@mui/material";
import styled from "styled-components";
import { Routes, Route, Link, NavLink, BrowserRouter } from "react-router-dom";


const StyledAppBar = styled(AppBar)`
  height: 60px !important;
  box-shadow: 0px 2px 4px -1px rgb(0 0 0 / 14%),
    0px 4px 5px 0px rgb(0 0 0 / 10%), 0px 1px 5px 0px rgb(0 0 0 / 6%) !important;
  display: flex;
  flex-direction: row !important;
  align-items: center;
  font-family: roboto;

  a {
    color: inherit;
    text-decoration: none;
  }

  .nav-link {
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 0 24px;
    box-sizing: border-box;
    filter: brightness(90%);
    border-bottom: 4px solid transparent;
  }

  .nav-link: hover {
    filter: brightness(85%);
  }

  .nav-link: active {
    filter: brightness(75%);
  }

  .link-active {
    text-shadow: .25px 0px .5px,
    -.25px 0px .5px;  
    border-bottom: 4px solid;
    filter: brightness(100%) !important;
  }
`;

const StyledNav = styled.nav`
  margin: 0 12px;
  display: flex;
  height: 100%;
  align-items: center
`;

function App() {
  return (
    <BrowserRouter>
      <StyledAppBar position="sticky">
        <StyledNav>
          <NavLink to="/" className={({ isActive }) => isActive ? 'link-active nav-link' : 'nav-link'}>Dashboard</NavLink>
          <NavLink to="/new-experiment" className={({ isActive }) => isActive ? 'link-active nav-link' : 'nav-link'}>New Experiment</NavLink>
        </StyledNav>
      </StyledAppBar>
      <Routes>
        <Route path="/*" element={<Dashboard />} />
        <Route path="new-experiment" element={<SubmitExp />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;