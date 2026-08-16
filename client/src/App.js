import SubmitExp from "./submit_exp/SubmitExp";
import Dashboard from './dashboard/Dashboard';
import { AppBar, CssBaseline, Typography } from "@mui/material";
import styled from "styled-components";
import { Routes, Route, NavLink, BrowserRouter } from "react-router-dom";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import alabLogo from "./logo512.png";

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
  height: 76px !important;
  background: linear-gradient(135deg, #183245 0%, #24465d 52%, #31556d 100%) !important;
  box-shadow: 0 18px 40px rgba(14, 29, 40, 0.18) !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: row !important;
  align-items: center;
  font-family: "Roboto", sans-serif;
  padding: 0 28px;

  a {
    color: inherit;
    text-decoration: none;
  }
`;

const StyledLogo = styled.img`
  height: 48px;
  width: 48px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.12);
  padding: 6px;
  margin-right: 24px;
`;

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <StyledAppBar position="sticky">
          <div style={{ display: "flex", alignItems: "center" }}>
            <NavLink to="/"><StyledLogo src={alabLogo} /></NavLink>
            <Typography
              variant="h5"
              sx={{
                fontWeight: 700,
                letterSpacing: "0.08em",
                ml: 0.5,
                color: "#f5fbff",
                textTransform: "uppercase",
                fontSize: { xs: "1.2rem", sm: "1.45rem" },
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
