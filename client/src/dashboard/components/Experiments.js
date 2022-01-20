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

  .status,
  .task-id,
  .task-type {
    font-family: Source Code Pro;
    color: black;
  }

  .exp-name {
    font-size: 120%;
  }

  .task-id {
    font-size: 90%;
  }

  .status-waiting {
    color: blue;
  }

  .status-running {
    color: green;
  }

  .status-error {
    color: red;
    font-weight: bold;
  }

  .status-ready {
    color: red;
  }

  h3 {
    padding: 4px 8px;
  }
`;

function Experiments({experiments}) {
    console.log(experiments)
    return (
        <TableContainer style={{height: "100%"}} component={Paper}>
            <StyledDevicesDiv>
                <Typography variant="h5">Running Experiments</Typography>
                <Table stickyHeader aria-label="task table">
                    <TableHead>
                        <TableRow>
                            <TableCell align="center"><b>Exp Name</b></TableCell>
                            <TableCell align="center"><b>Task Id</b></TableCell>
                            <TableCell align="center"><b>Type</b></TableCell>
                            <TableCell align="center"><b>Status</b></TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {experiments.map((exp) => (exp.tasks?.map((row, index) => (
                            <TableRow
                                key={row.id}
                            >
                                {index === 0 ? (
                                    <TableCell align="center" rowSpan={exp.tasks.length} component="th" scope="row">
                                        <span className="exp-name">{exp.name}</span>
                                    </TableCell>
                                ) : <></>}
                                <TableCell align="center">
                                    <span className="task-id">{row.id}</span>
                                </TableCell>
                                <TableCell align="center"><span className="task-type">{row.type}</span></TableCell>
                                <TableCell align="center">
                  <span className={`status status-${row.status.toLowerCase()}`}>
                    {row.status}
                  </span>
                                </TableCell>
                            </TableRow>
                        ))))}
                    </TableBody>
                </Table>
            </StyledDevicesDiv>
        </TableContainer>
    )
}

export default Experiments;