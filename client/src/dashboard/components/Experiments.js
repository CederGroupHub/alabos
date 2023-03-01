import { useEffect } from 'react';
import { get_experiment_status, get_experiment_ids } from '../../api_routes';
import LinearProgress from '@mui/material/LinearProgress';//
import * as React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
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
import { HoverText } from '../../utils';

function Row({ experiment_id, hoverForId }) {
  const [open, setOpen] = React.useState(false);
  const [status, setStatus] = React.useState(
    { "_id": "", "status": "", "samples": [], "tasks": [], "progress": 50 }
  );
  const [taskOpen, setTaskOpen] = React.useState(false);
  const [sampleOpen, setSampleOpen] = React.useState(false);

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

  const cancel_task = (task_id) => {
    fetch(`/api/task/cancel/{task_id}`, {
      method: 'GET',
    })
  }

  const cancel_experiment = (experiment_id) => {
    fetch(`/api/experiment/cancel/{experiment_id}`, {
      method: 'GET',
    })
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
          <HoverText defaultText={status.name} hoverText={status.id} variant="body1" active={hoverForId} />
          {/* {status.name} */}
        </TableCell>

        {/* <TableCell align="left">
          <Typography variant="body2">{status.id}</Typography>
        </TableCell> */}

        <TableCell align="right">
          <Typography variant="body2">{status.samples.length}</Typography>
        </TableCell>


        <TableCell align="right"><Typography variant="body2">{status.submitted_at}</Typography></TableCell>
        <TableCell align="right">
          <LinearProgress variant="determinate" value={Math.round(status.progress * 100)} color={progressBarColor()} />
        </TableCell>
        {/* <TableCell align="right">{row.protein}</TableCell> */}

        <TableCell align="right">
          <Button 
            variant="contained" 
            color="error"
            onClick={() => cancel_experiment(status.id)}
          >
            Cancel Experiment
          </Button>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 1 }}>

              <Typography variant="body1" gutterBottom component="div">
                <IconButton
                  aria-label="expand row"
                  size="small"
                  onClick={() => setSampleOpen(!sampleOpen)}
                >
                  {sampleOpen ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                </IconButton>
                Samples
              </Typography>
              <Collapse in={sampleOpen} timeout="auto" unmountOnExit>
                <Table size="small" aria-label="purchases">
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell>Position</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {status.samples.map((sample) => (
                      <TableRow key={sample.id}>
                        <TableCell component="th" scope="row">
                          <HoverText defaultText={sample.name} hoverText={sample.id} variant="body2" active={hoverForId} />
                          {/* {sample.name} */}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body">
                            {sample.position}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Collapse>


              <Typography variant="body1" gutterBottom component="div">
                <IconButton
                  aria-label="expand row"
                  size="small"
                  onClick={() => setTaskOpen(!taskOpen)}
                >
                  {taskOpen ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                </IconButton>
                Tasks
              </Typography>
              <Collapse in={taskOpen} timeout="auto" unmountOnExit>
                <Table size="small" aria-label="purchases">
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell width="50%">Message</TableCell>
                      {/* <TableCell>Result</TableCell> */}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {status.tasks.map((task) => (
                      <TableRow key={task.id}>
                        <TableCell component="th" scope="row">
                          <HoverText defaultText={task.type} hoverText={task.id} variant="body2" active={hoverForId} />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body" color={taskStatusColor(task.status)}>
                            {task.status}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body" style={{
                            whiteSpace: "pre-wrap",
                            display: '-webkit-box',
                            overflow: 'auto',
                            WebkitBoxOrient: 'vertical',
                            WebkitLineClamp: 2,
                          }}>
                            {task.message}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Button 
                            variant="contained" 
                            color="error"
                            onClick={() => cancel_task(task.id)}
                          >
                            Cancel
                          </Button>
                        </TableCell>
                        {/* <TableCell>{task.result}</TableCell>  */}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Collapse>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </React.Fragment>
  );
}

function CollapsibleTable({ experiment_ids, hoverForId }) {
  return (
    <TableContainer component={Paper}>
      <Table aria-label="collapsible table">
        <TableHead>
          <TableRow>
            <TableCell />
            <TableCell>Name</TableCell>
            <TableCell align="right"># Samples</TableCell>
            <TableCell align="right">Submitted At</TableCell>
            <TableCell align="right">Progress</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {experiment_ids.map((experiment_id) => (
            <Row key={experiment_id} experiment_id={experiment_id} hoverForId={hoverForId} />
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

function Experiments({ hoverForId }) {
  const [experimentIds, setExperimentIds] = React.useState([]);


  useEffect(() => {
    const interval = setInterval(() => {
      get_experiment_ids().then(ids => {
        setExperimentIds(ids);
      })
    }, 250);
    return () => clearInterval(interval);
  }, []);

  return (
    <CollapsibleTable experiment_ids={experimentIds} hoverForId={hoverForId} />

  );
}

export default Experiments;