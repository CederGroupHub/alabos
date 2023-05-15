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
import { request_device_pause, release_device_pause } from '../../api_routes';
import Button from '@mui/material/Button';

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


function Row({ device, hoverForId }) {
  const rowColor = () => {
    switch (device.status) {
      case "OCCUPIED":
        return '#e8f5e9';
      case "ERROR":
        return '#c62828';
      case "PAUSE_REQUESTED":
        return '#ffe0b2';
      case "PAUSED":
        return '#ef6c00';
      default:
        return "#ffffff";
    }
  }

  const textColor = (task_status) => {
    switch (task_status) {
      case "ERROR":
      case "PAUSED":
        return '#ffffff';
      default:
        return "#000000";
    }
  }

  const subtextColor = (task_status) => {
    switch (task_status) {
      case "ERROR":
      case "PAUSED":
        return '#ffffff';
      default:
        return "#9e9e9e";
    }
  }

  const PauseButton = ({ pause_state, device_name }) => {
    switch (pause_state) {
      case "RELEASED":
        return <Button variant="contained" color="error" onClick={() => { request_device_pause(device_name) }}>Pause</Button>
      case "REQUESTED":
        return <Button variant="contained" color="primary" onClick={() => release_device_pause(device_name)}>Cancel Pause Request</Button>
      case "PAUSED":
        return <Button variant="contained" color="primary" onClick={() => release_device_pause(device_name)}>Release</Button>
    }
  }



  return (
    <TableRow
      key={device.name}
      sx={{
        '&:last-child td, &:last-child th': { border: 0 },
        bgcolor: rowColor(device.status),
      }}
    >
      <TableCell component="th" scope="row">
        <Typography
          variant="body1"
          sx={{
            color: textColor(device.status),
          }}
        >
          {device.name}
        </Typography>
        <Typography variant="caption"
          sx={{ color: subtextColor(device.status) }}
        >{device.type}</Typography>
      </TableCell>
      {/* <TableCell align="center">{row.type}</TableCell> */}
      <TableCell align="center" size="small">
        <OccupiedSamplePositions samples={device.samples} name={device.name} key={String(device.name + "-samplepositions")} hoverForId={hoverForId} />
      </TableCell>
      <TableCell align="left" width="50%" >
        <Typography variant="caption" sx={{
          color: textColor(device.status),
          whiteSpace: "pre-wrap",
          display: '-webkit-box',
          overflow: 'auto',
          WebkitBoxOrient: 'vertical',
          WebkitLineClamp: 3,
        }}>{device.message}</Typography>
      </TableCell>
      <TableCell align="center">
        <PauseButton pause_state={device.pause_status} device_name={device.name} />
      </TableCell>
    </TableRow >
  );
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
    get_status().then(data => {
      setDevices(data.devices);
    })

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
                <TableCell><b>Name</b></TableCell>
                <TableCell align="center"><b>Samples</b></TableCell>
                <TableCell align="center" width="50%"><b>Message</b></TableCell>
                <TableCell align="center">Pause</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {FilteredDevices(onlyActive).map((device) => (
                <Row key={device.name} device={device} hoverForId={hoverForId} />
              ))}
            </TableBody>
          </Table>
        </StyledDevicesDiv>
      </TableContainer></>
  )
}

export default Devices;