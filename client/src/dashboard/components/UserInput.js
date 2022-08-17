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
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
// import Icon from '@mui/material/Icon';

// import * as React from 'react';
import Accordion from '@mui/material/Accordion';
import AccordionDetails from '@mui/material/AccordionDetails';
import AccordionSummary from '@mui/material/AccordionSummary';
// import Typography from '@mui/material/Typography';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';


function SplitButton({ options, optionIndex, setOptionIndex, handleClick }) {
  const [open, setOpen] = React.useState(false);
  const anchorRef = React.useRef(null);

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
      <ButtonGroup variant="outlined" ref={anchorRef} aria-label="split button" fullWidth
        disableElevation={false}>
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
          <ArrowDropDownIcon /> Options
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


function UserInputRow({ request_id, task_name, task_id, prompt, options, hoverForId = false }) {
  const [note, setNote] = React.useState("");
  const [optionIndex, setOptionIndex] = React.useState(0); //passed to splitbutton


  function handleClick() {
    respond_to_userinputrequest(request_id, options[optionIndex], note)
  }
  return (
    <TableRow
      sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
    >
      <TableCell align="center">
        <HoverText defaultText={task_name} hoverText={task_id} variant="body1" active={hoverForId} />
      </TableCell>

      <TableCell component="th" scope="row">
        <Typography variant="body2" component="p">
          {prompt}
        </Typography>
      </TableCell>

      <TableCell align="center" key="$request_id-cell4">
        <TextField
          id="outlined-basic"
          label="Note (Optional)"
          variant="outlined"
          onChange={(event) => setNote(event.target.value)}
          value={note}
          size="small"
          fullWidth
        // autoFocus={focused}
        // onClick={(event) => setFocused(true)}
        />
        <SplitButton options={options} optionIndex={optionIndex} setOptionIndex={setOptionIndex} handleClick={handleClick} />
      </TableCell>
    </TableRow>
  );
}


function UserInputAccordion({ experiment_id, experiment_name, requests, hoverForId }) {
  const [accordionState, setAccordionState] = React.useState(true);

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
                  <TableCell align="center"><b>Task</b></TableCell>
                  <TableCell align="center"><b>Prompt</b></TableCell>
                  {/* <TableCell align="center"><b>User Notes</b></TableCell> */}
                  <TableCell align="center"><b>Send Response</b></TableCell>
                </TableRow>
              </TableHead>
              {
                requests.map((request) => (
                  <UserInputRow request_id={request.id} task_name={request.task.type} task_id={request.task.id} prompt={request.prompt} options={request.options} key={request.id} hoverForId={hoverForId} />
                ))
              }
            </Table>
          </TableContainer >
        </AccordionDetails>

      </Accordion>
    </div>
  )
}

function UserInputs({ hoverForId }) {
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
      <UserInputAccordion experiment_id={experiment_id} experiment_name={idToName[experiment_id]} requests={requests} key={experiment_id} hoverForId={hoverForId} />
    )))
}


export default UserInputs;