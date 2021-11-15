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

const StyledDevicesDiv = styled.div`
  margin: 12px 16px;

  .status {
    font-family: ui-monospace,SFMono-Regular,SF Mono,
      Menlo,Consolas,Liberation Mono,monospace;
    color: black;
  }

  .status-occupied {
    color: red;
  }

  .status-idle {
    color: green;
  }
  
  .task-id {
    font-family: ui-monospace,SFMono-Regular,SF Mono,
      Menlo,Consolas,Liberation Mono,monospace;
  }

  h3 {
    padding: 4px 8px;
  }
`;

function Devices({devices}) {
    return (
        <TableContainer style={{height: "100%"}} component={Paper}>
            <StyledDevicesDiv>
                <Typography variant="h5">Device View</Typography>
                <Table stickyHeader aria-label="device table">
                    <TableHead>
                        <TableRow>
                            <TableCell><b>Device Name</b></TableCell>
                            <TableCell align="center"><b>Type</b></TableCell>
                            <TableCell align="center"><b>Status</b></TableCell>
                            <TableCell align="center"><b>Task</b></TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {devices.map((row) => (
                            <TableRow
                                key={row.name}
                                sx={{'&:last-child td, &:last-child th': {border: 0}}}
                            >
                                <TableCell component="th" scope="row">
                                    {row.name}
                                </TableCell>
                                <TableCell align="center">{row.type}</TableCell>
                                <TableCell align="center">
                  <span className={`status status-${row.status.toLowerCase()}`}>
                    {row.status === "OCCUPIED" || row.status === "IDLE" ? '⬤' : ''} {row.status}
                  </span>
                                </TableCell>
                                <TableCell align="center"><span className="task-id">{row.task}</span></TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </StyledDevicesDiv>
        </TableContainer>
    )
}

export default Devices;