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
import Accordion from '@mui/material/Accordion';
import AccordionDetails from '@mui/material/AccordionDetails';
import AccordionSummary from '@mui/material/AccordionSummary';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

/** Preferred affirmative options, in priority order for bulk-complete. */
const AFFIRMATIVE_OPTIONS = [
  "Mark as completed",
  "Mark as Completed",
  "success",
  "OK",
  "Continue",
];

/** Friendlier labels for legacy option strings still used by running tasks. */
const OPTION_DISPLAY_LABELS = {
  success: "Mark as completed",
  OK: "Mark as completed",
  "Mark as Completed": "Mark as completed",
  error: "Error",
};

function displayOptionLabel(option) {
  return OPTION_DISPLAY_LABELS[option] || option;
}

function getCompletedOption(request) {
  const options = request.options || [];
  for (const preferred of AFFIRMATIVE_OPTIONS) {
    const match = options.find((option) => option === preferred);
    if (match) {
      return match;
    }
  }
  return null;
}


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
        <Button onClick={handleClick} size="small">{displayOptionLabel(options[optionIndex])}</Button>
        <Button
          size="small"
          color="primary"
          aria-controls={open ? 'split-button-menu' : undefined}
          aria-expanded={open ? 'true' : undefined}
          aria-label="select response to user input request"
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
        style={{ zIndex: '100' }}
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
                      {displayOptionLabel(option)}
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
  const [optionIndex, setOptionIndex] = React.useState(0);


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
          ? `No requests in ${experiment_name} have a completable option (e.g. Mark as completed / success / OK).`
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
          ? `Marked ${completableRequests.length} request(s) in ${experiment_name} as completed. Skipped ${skippedCount} request(s) without a completable option.`
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
          <Stack
            direction="row"
            alignItems="center"
            spacing={1.5}
            sx={{ flex: 1, minWidth: 0 }}
          >
            <InputHeader accordionState={accordionState} numRequests={requests.length} />
            <Button
              variant="contained"
              size="small"
              onClick={(event) => {
                event.stopPropagation();
                handleMarkSectionCompleted();
              }}
              disabled={bulkSubmitting || requests.length === 0}
              sx={{ flexShrink: 0 }}
            >
              {bulkSubmitting ? "Marking…" : "Mark all as completed"}
            </Button>
          </Stack>
        </AccordionSummary>
        <AccordionDetails sx={{ pt: 1 }}>
            <TableContainer style={{ height: "100%" }
            } component={Paper} >
            <Table stickyHeader aria-label="user input table">
              <TableHead>
                <TableRow>
                  <TableCell align="center"><b>Task</b></TableCell>
                  <TableCell align="center"><b>Prompt</b></TableCell>
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

  useEffect(() => {
    if (message === null) {
      return undefined;
    }
    const timer = window.setTimeout(() => setMessage(null), 5000);
    return () => window.clearTimeout(timer);
  }, [message]);

  return (
    <Stack spacing={2}>
      <div>
        <Typography variant="h5">User Input Requests</Typography>
        <Typography variant="body2" color="text.secondary">
          Resolve pending operator prompts individually, or mark an entire section as completed when appropriate.
        </Typography>
      </div>
      {message && (
        <Alert severity={message.severity} onClose={() => setMessage(null)}>
          {message.text}
        </Alert>
      )}
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
    </Stack>
  )
}


export default UserInputs;
