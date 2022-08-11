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
import { useStickyState } from '../../hooks/StickyState';
import { useEffect } from 'react';
import { get_pending_userinputrequests, respond_to_userinputrequest } from '../../api_routes';
const SUBMIT_RESPONSE_API = process.env.NODE_ENV === "production" ? "/api/userinput/submit" : "http://localhost:8896/api/userinput/submit";


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

  Button{
    margin: 0px 8px;
  }
`;

function UserInputRow({ request_id, task_id, prompt }) {
  // const [note, setNote] = useStickyState("", String(request.id) + "-note");
  const [note, setNote] = React.useState("");


  // useEffect(() => {
  //   const interval = setInterval(() => {
  //     fetch(SPECIFIC_ID_API_PREFIX + request_id, { mode: 'cors' })
  //       .then(res => res.json())
  //       .then(result => {
  //         setRequest(result.data);
  //       })
  //   }, 1000);
  //   return () => clearInterval(interval);
  // }, []);

  function handleClick(status) {
    respond_to_userinputrequest(request_id, status, note)
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
        <Button
          variant="contained"
          onClick={() => handleClick("success")}
        >
          Success
        </Button>
        <Button
          variant="outlined"
          onClick={() => handleClick("error")}
        >
          Error
        </Button>
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
              <UserInputRow request_id={request.id} task_id={request.task_id} prompt={request.prompt} key={String(request.id)} />
            ))}
          </TableBody>
        </Table>
      </StyledDevicesDiv>
    </TableContainer >
  )
}

export default UserInputs;