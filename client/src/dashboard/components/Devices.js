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
import ListItemText from '@mui/material/ListItemText';
import ListItem from '@mui/material/ListItem';
import ListSubheader from '@mui/material/ListSubheader';
import Badge from '@mui/material/Badge';
import { Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { useStickyState } from "../../hooks/StickyState";
import { useEffect } from 'react';
import { get_status } from '../../api_routes';
// import STATUS_API from '../../api_routes';
// import useWindowScrollPosition from "../../hooks/useWindowScrollPosition";
// import { Button } from '@mui/material';
// import { Fab } from '@mui/material';
// import Button from '@mui/material/Button';
// import TextField from '@mui/material/TextField';

const STATUS_API = process.env.NODE_ENV === "production" ? "/api/status" : "http://localhost:8896/api/status";

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


function OccupiedSamplePositions({ device, samples }) {
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
              <SingleOccupiedSamplePositionsList position={position} samples={_samples} />
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
      hover: false
    }
    this.handleClick = this.handleClick.bind(this);
  }

  handleClick() {
    // console.log("Handle Clicked....");
    this.setState(prevState => ({
      open: !prevState.open
    }));
    // this.samples = Object.entries(this.props.samples).filter(([position, samples]) => samples.length > 0);
  }
  // handleOnMouseLeave() {
  //   this.setState({
  //     hover: false
  //   });
  // }
  // handleOnMouseEnter() {
  //   this.setState({
  //     hover: true
  //   });
  // }

  render() {
    if (this.state.hover) {
      this.subheadercolor = "white"
    } else {
      this.subheadercolor = "red"
    }

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
            onClick={this.handleClick}
            // onMouseEnter={this.handleOnMouseEnter}
            // onMouseLeave={this.onMouseLeave}
            color={this.subheadercolor}>
            <Badge badgeContent={this.props.samples.length} color="primary">
              {this.props.position}
            </Badge>
          </ ListSubheader>}
      >
        <Collapse in={this.state.open} timeout="auto" unmountOnExit>
          {this.props.samples.map((sample) => (
            <ListItem
              key={sample}
              disableGutters
            >
              <ListItemText primary={sample} />
            </ListItem>
          ))}
        </Collapse>
      </List>
    );
  }
}

function Devices() {
  const [devices, setDevices] = React.useState([]);

  useEffect(() => {
    const interval = setInterval(() => {
      get_status().then(data => {
        console.log(data.devices);
        setDevices(data.devices);
      })

    }, 100);
    return () => clearInterval(interval);
  }, []);


  return (
    <TableContainer style={{ height: "100%" }} component={Paper}>
      <StyledDevicesDiv>
        <Typography variant="h4" component="h3">Device View</Typography>
        <Table stickyHeader aria-label="device table">
          <TableHead>
            <TableRow>
              <TableCell><b>Device Name</b></TableCell>
              <TableCell align="center"><b>Type</b></TableCell>
              <TableCell align="center"><b>Samples</b></TableCell>
              <TableCell align="center"><b>Status</b></TableCell>
              <TableCell align="center"><b>Device Message</b></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {devices.map((row) => (
              <TableRow
                key={row.name}
                sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
              >
                <TableCell component="th" scope="row">
                  {row.name}
                </TableCell>
                <TableCell align="center">{row.type}</TableCell>
                <TableCell align="center" size="small" width="5%">
                  <OccupiedSamplePositions samples={row.samples} name={row.name} key={String(row.name + "-samplepositions")} />
                  {/* {OccupiedSamplePositions(row.name, row.samples)} */}
                </TableCell>
                < TableCell align="center" >
                  <span className={`status status-${row.status.toLowerCase()}`}>
                    {row.status === "OCCUPIED" || row.status === "IDLE" ? '⬤' : ''} {row.status}
                  </span>
                </TableCell>
                <TableCell align="center"><span className="message">{row.message}</span></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </StyledDevicesDiv >
    </TableContainer >
  )
}

export default Devices;