// import React from 'react';
// import Paper from '@mui/material/Paper';
import styled from 'styled-components';
// import Table from '@mui/material/Table';
// import TableBody from '@mui/material/TableBody';
// import TableCell from '@mui/material/TableCell';
// import TableContainer from '@mui/material/TableContainer';
// import TableHead from '@mui/material/TableHead';
// import TableRow from '@mui/material/TableRow';
// import Typography from '@mui/material/Typography';
import { get_status } from '../../api_routes';
import { useEffect } from 'react';
import { get_experiment_status, get_experiment_ids } from '../../api_routes';
import LinearProgress from '@mui/material/LinearProgress';//
import * as React from 'react';
import Box from '@mui/material/Box';
import Collapse from '@mui/material/Collapse';
import IconButton from '@mui/material/IconButton';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import { createTheme } from '@mui/material/styles';

const StyledExpDiv = styled.div`
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

function Row({ experiment_id }) {
  const [open, setOpen] = React.useState(false);
  const [status, setStatus] = React.useState(
    { "_id": "", "status": "", "samples": [], "tasks": [], "progress": 50 }
  );

  useEffect(() => {
    const interval = setInterval(() => {
      get_experiment_status(experiment_id).then(status => {
        setStatus(status);
      })
    }, 250);
    return () => clearInterval(interval);
  }, []);

  const progressBarColor = () => {
    switch (status.status) {
      case "RUNNING":
        return "primary";
      case "ERROR":
        return "error";
      case "COMPLETED":
        return "success";
      default:
        return "warning";
    }
  }

  const taskStatusColor = (task_status) => {
    switch (task_status) {
      case "RUNNING":
        return "primary";
      case "REQUESTING_RESOURCES":
        return "orange";
      case "WAITING":
        return "secondary";
      case "ERROR":
        return "error";
      case "COMPLETED":
        return "inherit";
      default:
        return "inherit";
    }
  }

  return (
    <React.Fragment>
      <TableRow sx={{ '& > *': { borderBottom: 'unset' } }}>
        <TableCell>
          <IconButton
            aria-label="expand row"
            size="small"
            onClick={() => setOpen(!open)}
          >
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell component="th" scope="row">
          {status.name}
        </TableCell>

        <TableCell align="left">
          <Typography variant="body2">{status.id}</Typography>
        </TableCell>

        <TableCell align="right">
          <Typography variant="body2">{status.samples.length}</Typography>
        </TableCell>



        <TableCell align="right"><Typography variant="body2">{status.submitted_at}</Typography></TableCell>
        <TableCell align="right">
          <LinearProgress variant="determinate" value={Math.round(status.progress * 100)} color={progressBarColor()} />
        </TableCell>
        {/* <TableCell align="right">{row.protein}</TableCell> */}
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 1 }}>

              <Typography variant="h6" gutterBottom component="div">
                Tasks
              </Typography>
              <Table size="small" aria-label="purchases">
                <TableHead>
                  <TableRow>
                    <TableCell>Type</TableCell>
                    {/* <TableCell>Task ID</TableCell> */}
                    <TableCell>Status</TableCell>
                    {/* <TableCell>Result</TableCell> */}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {status.tasks.map((task) => (
                    <TableRow key={task.id}>
                      <TableCell component="th" scope="row">
                        {task.type}
                      </TableCell>
                      {/* <TableCell>{task.id}</TableCell> */}
                      <TableCell>
                        <Typography variant="body" color={taskStatusColor(task.status)}>
                          {task.status}
                        </Typography>
                      </TableCell>
                      {/* <TableCell>{task.result}</TableCell> */}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              <Typography variant="h6" gutterBottom component="div">
                Samples
              </Typography>
              <Table size="small" aria-label="purchases">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Sample ID</TableCell>
                    <TableCell>Position</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {status.samples.map((sample) => (
                    <TableRow key={sample.id}>
                      <TableCell component="th" scope="row">
                        {sample.name}
                      </TableCell>
                      <TableCell>{sample.id}</TableCell>
                      <TableCell>
                        <Typography variant="body">
                          {sample.position}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </React.Fragment>
  );
}

function CollapsibleTable({ experiment_ids }) {
  return (
    <TableContainer component={Paper}>
      <Table aria-label="collapsible table">
        <TableHead>
          <TableRow>
            <TableCell />
            <TableCell>Name</TableCell>
            <TableCell align="left">Experiment ID</TableCell>

            <TableCell align="right"># Samples</TableCell>
            <TableCell align="right">Submitted At</TableCell>
            <TableCell align="right">Progress</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {experiment_ids.map((experiment_id) => (
            <Row key={experiment_id} experiment_id={experiment_id} />
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

//



function Experiments() {
  const [experimentIds, setExperimentIds] = React.useState([]);


  useEffect(() => {
    const interval = setInterval(() => {
      get_experiment_ids().then(ids => {
        console.log(ids);
        setExperimentIds(ids);
      })
    }, 250);
    return () => clearInterval(interval);
  }, []);

  return (
    <CollapsibleTable experiment_ids={experimentIds} />

  );
}

export default Experiments;




    // <TableContainer style={{ height: "100%" }} component={Paper}>
    //   <StyledExpDiv>
    //     <Typography variant="h4" component="h3">Running Experiments</Typography>
    //     <Table stickyHeader aria-label="task table">
    //       <TableHead>
    //         <TableRow>
    //           <TableCell align="center"><b>Exp Name</b></TableCell>
    //           {/* <TableCell align="center"><b>Task Id</b></TableCell> */}
    //           <TableCell align="center"><b>Type</b></TableCell>
    //           <TableCell align="center"><b>Status</b></TableCell>
    //         </TableRow>
    //       </TableHead>
    //       <TableBody>
    //         {experiments.map((exp) => (exp.tasks?.map((row, index) => (
    //           <TableRow
    //             key={row.id}
    //           >
    //             {index === 0 ? (
    //               <TableCell align="center" rowSpan={exp.tasks.length} component="th" scope="row">
    //                 <span className="exp-name">{exp.name}</span>
    //               </TableCell>
    //             ) : <></>}
    //             {/* <TableCell align="center">
    //                                 <span className="task-id">{row.id}</span>
    //                             </TableCell> */}
    //             <TableCell align="center"><span className="task-type">{row.type}</span></TableCell>
    //             <TableCell align="center">
    //               <span className={`status status-${row.status.toLowerCase()}`}>
    //                 {row.status}
    //               </span>
    //             </TableCell>
    //           </TableRow>
    //         ))))}
    //       </TableBody>
    //     </Table>
    //   </StyledExpDiv>
    // </TableContainer>