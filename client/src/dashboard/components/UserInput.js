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

  // Button{
  //   margin: 0px 8px;
  // }
`;


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

function UserInputs() {
  //https://upmostly.com/tutorials/how-to-post-requests-react
  const [pending, setPending] = React.useState([]);

  useEffect(() => {
    const interval = setInterval(() => {
      get_pending_userinputrequests().then(requests => {
        setPending(requests);
      })
    }, 250);
    return () => clearInterval(interval);
  }, []);

  return (
    < TableContainer style={{ height: "100%" }
    } component={Paper} >
      <StyledDevicesDiv>
        <Typography variant="h4" component="h3">User Input Requests</Typography>
        <Table stickyHeader aria-label="user input table">
          <TableHead>
            <TableRow>
              <TableCell align="center"><b>Prompt</b></TableCell>
              <TableCell align="center"><b>Task ID</b></TableCell>
              <TableCell align="center"><b>Notes</b></TableCell>
              <TableCell align="center"><b>Send Response</b></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {pending.map((request) => (
              // UserInputRow(request_id)
              <UserInputRow request_id={request.id} task_id={request.task_id} prompt={request.prompt} options={request.options} key={String(request.id)} />
            ))}
          </TableBody>
        </Table>
      </StyledDevicesDiv>
    </TableContainer >
  )
}

export default UserInputs;