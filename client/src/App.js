import SubmitExp from "./submit_exp/SubmitExp";
import Dashboard from './dashboard/Dashboard';
import { AppBar, CssBaseline, Typography } from "@mui/material";
import styled from "styled-components";
import { Routes, Route, NavLink, BrowserRouter } from "react-router-dom";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import alabLogo from "./alab_logo.png";

const theme = createTheme({
  palette: {
    primary: {
      main: "#1976d2",
      dark: "#1565c0",
      light: "#42a5f5",
      contrastText: "#ffffff",
    },
    error: {
      main: "#d32f2f",
      dark: "#b71c1c",
      light: "#ef5350",
      contrastText: "#ffffff",
    },
    info: {
      main: "#1976d2",
      dark: "#1565c0",
      light: "#42a5f5",
      contrastText: "#ffffff",
    },
    warning: {
      main: "#d32f2f",
      dark: "#b71c1c",
      light: "#ef5350",
      contrastText: "#ffffff",
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
        },
      },
    },
    MuiSwitch: {
      styleOverrides: {
        switchBase: {
          "&.Mui-checked": {
            color: "#1976d2",
          },
          "&.Mui-checked + .MuiSwitch-track": {
            backgroundColor: "#1976d2",
          },
        },
      },
    },
  },
});

const StyledAppBar = styled(AppBar)`
  height: 88px !important;
  background: linear-gradient(135deg, #183245 0%, #24465d 52%, #31556d 100%) !important;
  box-shadow: 0 18px 40px rgba(14, 29, 40, 0.18) !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: row !important;
  align-items: center;
  font-family: "Roboto", sans-serif;
  padding: 0 30px;

  a {
    color: inherit;
    text-decoration: none;
  }
`;

const StyledLogo = styled.img`
  height: 100%;
  width: 100%;
  border-radius: 0;
  object-fit: contain;
`;

const StyledLogoTile = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  height: 56px;
  width: 56px;
  border-radius: 16px;
  background-color: rgb(230, 240, 247) !important;
  padding: 6px;
  box-sizing: border-box;
  overflow: hidden;
  margin-right: 26px;
`;

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <StyledAppBar position="sticky">
          <div style={{ display: "flex", alignItems: "center" }}>
            <NavLink to="/">
              <StyledLogoTile>
                <StyledLogo src={alabLogo} />
              </StyledLogoTile>
            </NavLink>
            <Typography
              variant="h5"
              sx={{
                fontWeight: 700,
                letterSpacing: "0.08em",
                ml: 0.5,
                color: "#f5fbff",
                textTransform: "uppercase",
                fontSize: { xs: "1.35rem", sm: "1.62rem" },
              }}
            >
              A-Lab
            </Typography>
          </div>
        </StyledAppBar>
        <Routes>
          <Route path="/*" element={<Dashboard />} />
          {/* <Route path="new-experiment" element={<SubmitExp />} /> */}
        </Routes>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
