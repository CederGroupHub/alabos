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

const SUBMIT_RESPONSE_API = "/api/userinput/submit";
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



function UserInputs({ userinputs }) {
  //https://upmostly.com/tutorials/how-to-post-requests-react
  class UserInputRow extends React.Component {
    constructor(props) {
      super(props);
      this.state = {
        text: ''
      };
    }
    handleClick = (status) => {
      fetch(SUBMIT_RESPONSE_API, {
        method: 'POST',
        mode: 'cors',
        body: JSON.stringify({
          "request_id": this.props.request.id,
          "status": status,
          "note": this.state.text
        })
      });
    }
    render() {
      return (
        <TableRow
          key={this.props.request.id}
          sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
        >
          <TableCell component="th" scope="row">
            {this.props.request.prompt}
          </TableCell>

          <TableCell align="center">{this.props.request.task_id}</TableCell>
          <TableCell align="center">
            <TextField
              id="outlined-basic"
              label="Note (Optional)"
              variant="outlined"
              onChange={(event) => this.setState({ text: event.target.value })}
              value={this.state.text}
            />
          </TableCell>
          <TableCell align="center">
            <Button
              variant="contained"
              onClick={() => this.handleClick("success")}
            >
              Success
            </Button>
            <Button
              variant="outlined"
              onClick={() => this.handleClick("error")}
            >
              Error
            </Button>
          </TableCell>
        </TableRow>
      );
    }
  }
  return (
    <TableContainer style={{ height: "100%" }} component={Paper}>
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
            {userinputs.map((userinputrequest) => (
              <UserInputRow request={userinputrequest} />
            ))}
          </TableBody>
        </Table>
      </StyledDevicesDiv>
    </TableContainer >
  )
}

export default UserInputs;