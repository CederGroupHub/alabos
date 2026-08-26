import React from 'react';
import Paper from '@mui/material/Paper';
import Table from '@mui/material/Table';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import ButtonGroup from '@mui/material/ButtonGroup';
import Stack from '@mui/material/Stack';
import Alert from '@mui/material/Alert';
import Snackbar from '@mui/material/Snackbar';
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


function UserInputAccordion({
  experiment_id,
  experiment_name,
  requests,
  hoverForId,
  onBulkMessage,
}) {
  const [accordionState, setAccordionState] = React.useState(true);
  const [bulkSubmitting, setBulkSubmitting] = React.useState(false);

  const getCompletedOption = (request) =>
    (request.options || []).find((option) => option === "Mark as Completed") || null;

  const handleMarkSectionCompleted = async () => {
    const completableRequests = requests
      .map((request) => ({
        request,
        completedOption: getCompletedOption(request),
      }))
      .filter(({ completedOption }) => completedOption !== null);
    const skippedCount = requests.length - completableRequests.length;

    if (completableRequests.length === 0) {
      onBulkMessage({
        severity: "warning",
        text: skippedCount > 0
          ? `No requests in ${experiment_name} offer the exact 'Mark as Completed' option.`
          : `There are no pending requests in ${experiment_name}.`,
      });
      return;
    }

    setBulkSubmitting(true);
    try {
      await Promise.all(
        completableRequests.map(async ({ request, completedOption }) => {
          const response = await respond_to_userinputrequest(
            request.id,
            completedOption,
            "",
          );
          if (!response.ok) {
            throw new Error(`Failed to update request ${request.id}`);
          }
        })
      );
      onBulkMessage({
        severity: "success",
        text: skippedCount > 0
          ? `Marked ${completableRequests.length} request(s) in ${experiment_name} as completed. Skipped ${skippedCount} request(s) without the exact 'Mark as Completed' option.`
          : `Marked ${completableRequests.length} request(s) in ${experiment_name} as completed.`,
      });
    } catch (error) {
      onBulkMessage({
        severity: "error",
        text: `Failed to mark eligible requests in ${experiment_name} as completed.`,
      });
    } finally {
      setBulkSubmitting(false);
    }
  };

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
          <Stack spacing={2}>
            <Stack direction="row" justifyContent="flex-end">
              <Button
                variant="contained"
                size="small"
                onClick={handleMarkSectionCompleted}
                disabled={bulkSubmitting || requests.length === 0}
              >
                Mark all as completed
              </Button>
            </Stack>
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
          </Stack>
        </AccordionDetails>

      </Accordion>
    </div>
  )
}

function UserInputs({ hoverForId }) {
  //https://upmostly.com/tutorials/how-to-post-requests-react
  const [pending, setPending] = React.useState({});
  const [idToName, setIdToName] = React.useState({});
  const [message, setMessage] = React.useState(null);

  const refreshPendingRequests = React.useCallback(() => {
    get_pending_userinputrequests().then(requests => {
      setPending(requests.pending);
      setIdToName(requests.experiment_id_to_name)
    })
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      refreshPendingRequests();
    }, 2000);
    return () => clearInterval(interval);
  }, [refreshPendingRequests]);

  useEffect(() => {
    refreshPendingRequests();
  }, [refreshPendingRequests]);

  const handleBulkMessage = React.useCallback((nextMessage) => {
    setMessage(nextMessage);
    refreshPendingRequests();
  }, [refreshPendingRequests]);

  return (
    <Stack spacing={2}>
      <div>
        <Typography variant="h5">User Input Requests</Typography>
        <Typography variant="body2" color="text.secondary">
          Resolve pending operator prompts individually, or mark an entire section as completed when appropriate.
        </Typography>
      </div>
      {Object.entries(pending).map(([experiment_id, requests]) => (
        <UserInputAccordion
          experiment_id={experiment_id}
          experiment_name={idToName[experiment_id]}
          requests={requests}
          key={experiment_id}
          hoverForId={hoverForId}
          onBulkMessage={handleBulkMessage}
        />
      ))}
      <Snackbar
        open={message !== null}
        autoHideDuration={5000}
        onClose={() => setMessage(null)}
      >
        {message ? <Alert severity={message.severity}>{message.text}</Alert> : null}
      </Snackbar>
    </Stack>
  )
}


export default UserInputs;
