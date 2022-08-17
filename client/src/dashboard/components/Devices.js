import React from 'react';
import Paper from '@mui/material/Paper';
import styled from 'styled-components';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import Collapse from '@mui/material/Collapse';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListSubheader from '@mui/material/ListSubheader';
import Badge from '@mui/material/Badge';
import { Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { useEffect } from 'react';
import { get_status } from '../../api_routes';
import { HoverText } from '../../utils';
import { FormControl, FormControlLabel, Switch } from '@mui/material';


const StyledDevicesDiv = styled.div`
  margin: 12px 16px;

  .status {
    font-family: Source Code Pro;
    color: black;
  }

  .status-occupied {
    color: green;
  }

  .status-idle {
    color: red;
  }
  
  .task-id {
    font-family: Source Code Pro;
  }

  h3 {
    padding: 4px 8px;
  }
`;


const statusRowColors = {
  OCCUPIED: '#e8f5e9',
  ERROR: '#c62828',
  default: '#ffffff',
}
const statusTextColors = {
  OCCUPIED: "#000000",
  ERROR: "#ffffff",
  default: "#000000",
}

const statusSubtextColors = {
  OCCUPIED: "#9e9e9e",
  ERROR: "#ffffff",
  default: "#9e9e9e",
}


function OccupiedSamplePositions({ device, samples, hoverForId }) {
  var total_samples = 0;
  // samples.map(sample => {
  //   total_samples += sample.samples.length;
  // })
  for (let _samples of Object.values(samples)) {
    total_samples += _samples.length;
  }
  const var_name = String(device) + '-accordionState'
  const [accordionState, setAccordionState] = React.useState(false, var_name);
  // const [accordionState, setAccordionState] = React.useState(true);
  return (
    <div>
      <Accordion elevation={0} expanded={accordionState} onChange={(e, expanded) => setAccordionState(expanded)}>
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
        >
          <Typography variant="body1">{total_samples}</Typography>
        </AccordionSummary>
        <AccordionDetails>
          {
            Object.entries(samples).map(([position, _samples]) => (
              <SingleOccupiedSamplePositionsList position={position} samples={_samples} key={position} hoverForId={hoverForId} />
            ))
          }
        </AccordionDetails>
      </Accordion>
    </div >
  );
}
class SingleOccupiedSamplePositionsList extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      open: false,
    }
    this.handleClick = this.handleClick.bind(this);
  }

  handleClick() {
    this.setState(prevState => ({
      open: !prevState.open
    }));
  }

  render() {

    return (
      <List
        sx={{
          bgcolor: 'background.paper',
          // overflow: 'auto',
          maxHeight: 300,
        }}
        dense={true}
        subheader={
          <ListSubheader
            component="div"
            id="nested-list-subheader"
            onClick={this.handleClick}>
            <Badge badgeContent={this.props.samples.length} color="primary">
              {this.props.position}
            </Badge>
          </ ListSubheader>}
      >
        <Collapse in={this.state.open} timeout="auto" unmountOnExit>
          {this.props.samples.map((sample) => (
            <ListItem
              key={sample.id}
              disableGutters
            >
              {/* <ListItemText primary={sample} /> */}
              <HoverText defaultText={sample.name} hoverText={sample.id} variant="body2" active={this.props.hoverForId} />
            </ListItem>
          ))}
        </Collapse>
      </List>
    );
  }
}

function Devices({ hoverForId }) {
  const [devices, setDevices] = React.useState([]);
  const [onlyActive, setOnlyActive] = React.useState(true);

  useEffect(() => {
    const interval = setInterval(() => {
      get_status().then(data => {
        setDevices(data.devices);
      })

    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const DisplayDeviceRowFilter = (row) => {
    if (row.status != "IDLE") {
      return true
    }
    for (let samples of Object.values(row.samples)) {
      if (samples.length > 0) {
        return true
      }
    }
    return false
  }

  const FilteredDevices = (onlyActive) => {
    if (onlyActive) {
      return devices.filter(DisplayDeviceRowFilter)
    } else {
      return devices
    }
  }


  return (
    <><FormControl component="fieldset" variant="standard" sx={{ padding: "0px 16px" }}>
      <FormControlLabel
        control={<Switch checked={onlyActive} onChange={() => (setOnlyActive(!onlyActive))} name="Only show active Devices" />}
        label="Only show active Devices" />
    </FormControl><TableContainer style={{ height: "100%" }} component={Paper}>
        <StyledDevicesDiv>
          <Table stickyHeader aria-label="device table">
            <TableHead>
              <TableRow>
                <TableCell><b>Device Name</b></TableCell>
                <TableCell align="center"><b>Samples</b></TableCell>
                <TableCell align="center" width="50%"><b>Device Message</b></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {FilteredDevices(onlyActive).map((row) => (
                <TableRow
                  key={row.name}
                  sx={{
                    '&:last-child td, &:last-child th': { border: 0 },
                    bgcolor: statusRowColors[row.status] ?? statusRowColors.default,
                  }}
                >
                  <TableCell component="th" scope="row">
                    <Typography
                      variant="body1"
                      sx={{
                        color: statusTextColors[row.status] ?? statusTextColors.default,
                      }}
                    >
                      {row.name}
                    </Typography>
                    <Typography variant="caption"
                      sx={{ color: statusSubtextColors[row.status] ?? statusTextColors.default }}
                    >{row.type}</Typography>
                  </TableCell>
                  {/* <TableCell align="center">{row.type}</TableCell> */}
                  <TableCell align="center" size="small">
                    <OccupiedSamplePositions samples={row.samples} name={row.name} key={String(row.name + "-samplepositions")} hoverForId={hoverForId} />
                  </TableCell>
                  <TableCell align="center" width="50%">
                    <Typography variant="caption">{row.message}</Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </StyledDevicesDiv>
      </TableContainer></>
  )
}

export default Devices;