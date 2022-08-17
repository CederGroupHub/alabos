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
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import ButtonGroup from '@mui/material/ButtonGroup';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import ClickAwayListener from '@mui/material/ClickAwayListener';
import Grow from '@mui/material/Grow';
import Popper from '@mui/material/Popper';
import MenuItem from '@mui/material/MenuItem';
import MenuList from '@mui/material/MenuList';
import { useEffect } from 'react';
import { get_pending_userinputrequests, respond_to_userinputrequest } from '../../api_routes';
import { HoverText } from '../../utils';
import Badge from '@mui/material/Badge';

// import * as React from 'react';
import Accordion from '@mui/material/Accordion';
import AccordionDetails from '@mui/material/AccordionDetails';
import AccordionSummary from '@mui/material/AccordionSummary';
// import Typography from '@mui/material/Typography';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';


// export default function ControlledAccordions() {
//   const [expanded, setExpanded] = React.useState(false);

//   const handleChange = (panel) => (event, isExpanded) => {
//     setExpanded(isExpanded ? panel : false);
//   };

//   return (
//     <div>
//       <Accordion expanded={expanded === 'panel1'} onChange={handleChange('panel1')}>
//         <AccordionSummary
//           expandIcon={<ExpandMoreIcon />}
//           aria-controls="panel1bh-content"
//           id="panel1bh-header"
//         >
//           <Typography sx={{ width: '33%', flexShrink: 0 }}>
//             General settings
//           </Typography>
//           <Typography sx={{ color: 'text.secondary' }}>I am an accordion</Typography>
//         </AccordionSummary>
//         <AccordionDetails>
//           <Typography>
//             Nulla facilisi. Phasellus sollicitudin nulla et quam mattis feugiat.
//             Aliquam eget maximus est, id dignissim quam.
//           </Typography>
//         </AccordionDetails>
//       </Accordion>
//       <Accordion expanded={expanded === 'panel2'} onChange={handleChange('panel2')}>
//         <AccordionSummary
//           expandIcon={<ExpandMoreIcon />}
//           aria-controls="panel2bh-content"
//           id="panel2bh-header"
//         >
//           <Typography sx={{ width: '33%', flexShrink: 0 }}>Users</Typography>
//           <Typography sx={{ color: 'text.secondary' }}>
//             You are currently not an owner
//           </Typography>
//         </AccordionSummary>
//         <AccordionDetails>
//           <Typography>
//             Donec placerat, lectus sed mattis semper, neque lectus feugiat lectus,
//             varius pulvinar diam eros in elit. Pellentesque convallis laoreet
//             laoreet.
//           </Typography>
//         </AccordionDetails>
//       </Accordion>
//       <Accordion expanded={expanded === 'panel3'} onChange={handleChange('panel3')}>
//         <AccordionSummary
//           expandIcon={<ExpandMoreIcon />}
//           aria-controls="panel3bh-content"
//           id="panel3bh-header"
//         >
//           <Typography sx={{ width: '33%', flexShrink: 0 }}>
//             Advanced settings
//           </Typography>
//           <Typography sx={{ color: 'text.secondary' }}>
//             Filtering has been entirely disabled for whole web server
//           </Typography>
//         </AccordionSummary>
//         <AccordionDetails>
//           <Typography>
//             Nunc vitae orci ultricies, auctor nunc in, volutpat nisl. Integer sit
//             amet egestas eros, vitae egestas augue. Duis vel est augue.
//           </Typography>
//         </AccordionDetails>
//       </Accordion>
//       <Accordion expanded={expanded === 'panel4'} onChange={handleChange('panel4')}>
//         <AccordionSummary
//           expandIcon={<ExpandMoreIcon />}
//           aria-controls="panel4bh-content"
//           id="panel4bh-header"
//         >
//           <Typography sx={{ width: '33%', flexShrink: 0 }}>Personal data</Typography>
//         </AccordionSummary>
//         <AccordionDetails>
//           <Typography>
//             Nunc vitae orci ultricies, auctor nunc in, volutpat nisl. Integer sit
//             amet egestas eros, vitae egestas augue. Duis vel est augue.
//           </Typography>
//         </AccordionDetails>
//       </Accordion>
//     </div>
//   );
// }


function SplitButton({ options, optionIndex, setOptionIndex, handleClick }) {
  const [open, setOpen] = React.useState(false);
  const anchorRef = React.useRef(null);
  // const [selectedIndex, setSelectedIndex] = React.useState(1);

  // const handleClick = () => {
  //   console.info(`You clicked ${options[selectedIndex]}`);
  // };

  const handleMenuItemClick = (event, index) => {
    setOptionIndex(index);
    setOpen(false);
  };

  const handleToggle = () => {
    setOpen((prevOpen) => !prevOpen);
  };

  const handleClose = (event) => {
    if (anchorRef.current && anchorRef.current.contains(event.target)) {
      return;
    }

    setOpen(false);
  };

  return (
    <React.Fragment>
      <ButtonGroup variant="contained" ref={anchorRef} aria-label="split button" fullWidth>
        <Button onClick={handleClick} size="small" >{options[optionIndex]}</Button>
        <Button
          size="small"
          color="primary"
          aria-controls={open ? 'split-button-menu' : undefined}
          aria-expanded={open ? 'true' : undefined}
          aria-label="select reponse to user input request"
          aria-haspopup="menu"
          onClick={handleToggle}
        >
          <ArrowDropDownIcon />
        </Button>
      </ButtonGroup>
      <Popper
        open={open}
        anchorEl={anchorRef.current}
        role={undefined}
        transition
        disablePortal
        style={{ zIndex: '100' }} //hack to get popper to show up on top of other elements
      >
        {({ TransitionProps, placement }) => (
          <Grow
            {...TransitionProps}
            style={{
              transformOrigin:
                placement === 'bottom' ? 'center top' : 'center bottom',
            }}
          >
            <Paper>
              <ClickAwayListener onClickAway={handleClose}>
                <MenuList id="split-button-menu" autoFocusItem>
                  {options.map((option, index) => (
                    <MenuItem
                      key={option}
                      selected={index === optionIndex}
                      onClick={(event) => handleMenuItemClick(event, index)}
                    >
                      {option}
                    </MenuItem>
                  ))}
                </MenuList>
              </ClickAwayListener>
            </Paper>
          </Grow>
        )}
      </Popper>
    </React.Fragment>
  );
}


function UserInputRow({ request_id, task_id, prompt, options }) {
  const [note, setNote] = React.useState("");
  const [optionIndex, setOptionIndex] = React.useState(0); //passed to splitbutton


  function handleClick(status) {
    respond_to_userinputrequest(request_id, options[optionIndex], note)
  }
  return (
    <TableRow
      sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
    >
      <TableCell component="th" scope="row">
        <Typography variant="body2" component="p">
          {prompt}
        </Typography>
      </TableCell>

      <TableCell align="center">{task_id}</TableCell>
      <TableCell align="center">
        <TextField
          id="outlined-basic"
          label="Note (Optional)"
          variant="outlined"
          onChange={(event) => setNote(event.target.value)}
          value={note}
        // autoFocus={focused}
        // onClick={(event) => setFocused(true)}
        />
      </TableCell>
      <TableCell align="center" key="$request_id-cell4">
        <SplitButton options={options} optionIndex={optionIndex} setOptionIndex={setOptionIndex} handleClick={handleClick} />
      </TableCell>
    </TableRow>
  );
}


// function UserInputs() {
//   //https://upmostly.com/tutorials/how-to-post-requests-react
//   const [pending, setPending] = React.useState([]);

//   useEffect(() => {
//     const interval = setInterval(() => {
//       get_pending_userinputrequests().then(requests => {
//         setPending(requests);
//       })
//     }, 250);
//     return () => clearInterval(interval);
//   }, []);

//   return (
//     < TableContainer style={{ height: "100%" }
//     } component={Paper} >
//       <StyledDevicesDiv>
//         <Typography variant="h4" component="h3">User Input Requests</Typography>
//         <Table stickyHeader aria-label="user input table">
//           <TableHead>
//             <TableRow>
//               <TableCell align="center"><b>Prompt</b></TableCell>
//               <TableCell align="center"><b>Task ID</b></TableCell>
//               <TableCell align="center"><b>Notes</b></TableCell>
//               <TableCell align="center"><b>Send Response</b></TableCell>
//             </TableRow>
//           </TableHead>
//           <TableBody>
//             {pending.map((request) => (
//               // UserInputRow(request_id)
//               <UserInputRow request_id={request.id} task_id={request.task_id} prompt={request.prompt} options={request.options} key={String(request.id)} />
//             ))}
//           </TableBody>
//         </Table>
//       </StyledDevicesDiv>
//     </TableContainer >
//   )
// }

function UserInputAccordion({ experiment_id, experiment_name, requests, hoverForId = false }) {
  const [accordionState, setAccordionState] = React.useState(false);

  const InputHeader = ({ accordionState, numRequests }) => {
    if (accordionState) {
      return (
        <HoverText defaultText={experiment_name} hoverText={experiment_id} variant="h6" active={hoverForId} />
      )
    } else {
      return (
        <Badge badgeContent={numRequests} color="error">
          <HoverText defaultText={experiment_name} hoverText={experiment_id} variant="h6" active={hoverForId} />
        </Badge>
      )
    }
  }
  return (
    <div>
      <Accordion elevation={2} expanded={accordionState} onChange={(e, expanded) => setAccordionState(expanded)}>
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
        >
          <InputHeader accordionState={accordionState} numRequests={requests.length} />
        </AccordionSummary>
        <AccordionDetails>
          <TableContainer style={{ height: "100%" }
          } component={Paper} >
            <Table stickyHeader aria-label="user input table">
              <TableHead>
                <TableRow>
                  <TableCell align="center"><b>Prompt</b></TableCell>
                  <TableCell align="center"><b>Task ID</b></TableCell>
                  <TableCell align="center"><b>Notes</b></TableCell>
                  <TableCell align="center"><b>Send Response</b></TableCell>
                </TableRow>
              </TableHead>
              {
                requests.map((request) => (
                  <UserInputRow request_id={request.id} task_id={request.task_id} prompt={request.prompt} options={request.options} key={request.id} />
                ))
              }
            </Table>
          </TableContainer >
        </AccordionDetails>

      </Accordion>
    </div>
  )
}

function UserInputs() {
  //https://upmostly.com/tutorials/how-to-post-requests-react
  const [pending, setPending] = React.useState({});
  const [idToName, setIdToName] = React.useState({});

  useEffect(() => {
    const interval = setInterval(() => {
      get_pending_userinputrequests().then(requests => {
        setPending(requests.pending);
        setIdToName(requests.experiment_id_to_name)
      })
    }, 250);
    return () => clearInterval(interval);
  }, []);

  return (
    Object.entries(pending).map(([experiment_id, requests]) => (
      <UserInputAccordion experiment_id={experiment_id} experiment_name={idToName[experiment_id]} requests={requests} key={experiment_id} />
    )))
}


export default UserInputs;