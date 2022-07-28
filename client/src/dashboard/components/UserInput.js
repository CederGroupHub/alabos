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
import { Chip, TextField, Button } from '@mui/material';


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



function UserInputs({ userinputs }) {
  //https://upmostly.com/tutorials/how-to-post-requests-react
  function handleClick({ request_id }) {
    fetch('http://localhost:8896/', {  //TODO get IP/port dynamically
      method: 'POST',
      mode: 'cors',
      body: JSON.stringify({
        "request_id": request_id,
        "status": "success"
      })
    })

  }
  return (
    <TableContainer style={{ height: "100%" }} component={Paper}>
      <StyledDevicesDiv>
        <Typography variant="h4" component="h3">Requests for User Input</Typography>
        <Table stickyHeader aria-label="user input table">
          <TableHead>
            <TableRow>
              <TableCell><b>Request</b></TableCell>
              <TableCell align="center"><b>Task ID</b></TableCell>
              <TableCell align="center"><b>Response</b></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {userinputs.map((row) => (
              <TableRow
                key={row.response_id}
                sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
              >
                <TableCell component="th" scope="row">
                  {row.prompt}
                </TableCell>
                <TableCell align="center">{row.task_id}</TableCell>
                <TableCell align="center">
                  <Button
                    variant="contained"
                    onClick={handleClick(row.request_id)}
                  >
                    Complete
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </StyledDevicesDiv>
    </TableContainer>
  )
}

export default UserInputs;