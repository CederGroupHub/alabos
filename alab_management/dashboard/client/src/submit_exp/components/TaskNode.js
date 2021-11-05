import React, { useState } from 'react';
import { TextField, Select, MenuItem, Paper, InputLabel, Divider, IconButton, FormControl } from '@mui/material';
import styled from 'styled-components';
import { Handle } from 'react-flow-renderer';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import lightBlue from '@mui/material/colors/lightBlue';

const TASK_TYPES = ["Heating", "Moving", "Weighting"];

const ARG_LIST = {
    "Weighting": {
        "samples": ["sample_1"],
        "args": ["Chemical Name", "Amount"],
    },
    "Heating": {
        "samples": ["sample_1", "sample_2", "sample_3", "sample_4"],
        "args": ["setpoints"],
    },
    "Moving": {
        "samples": ["sample"],
        "args": ["dest"],
    }
}

const Task = styled(Paper)`
    width: 256px;
`

const TaskTitle = styled.div`
    padding: 0 12px 0 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: ${lightBlue[50]};
`;

const TaskContent = styled.div`
    padding: 4px 16px 8px 16px;
    display: flex;
    flex-direction: column
`

function TaskNode({ data }) {
    const [ taskType, setTaskType ] = useState('');
    const [ hideArgs, setHideArgs ] = useState(false);
    const [ samples, setSamples ] = useState({})

    const sampleNames = data.sampleNames;

    const onChange = (event) => {
        setTaskType(event.target.value); 
        if (TASK_TYPES.includes(event.target.value)) {
            let _samples = {}

            for (let i = 0; i < ARG_LIST[event.target.value].samples.length; i++) {
                _samples[ARG_LIST[event.target.value].samples[i]] = "";
            }
            
            setSamples(_samples)
        } else {
            setSamples({})
        }
    };

    const onSampleChange = (event) => {
        setSamples((samples) => {
            const [ sample, sampleName ] = event.target.value.split(".")
            samples[sample] = sampleName;
            return samples
        })
    }

    const onClick = () => {
        setHideArgs(!hideArgs);
    }

    return (
        <>
            <Handle type="target" position="left" style={{ borderRadius: "0" }} />
            <Handle type="source" position="right" style={{ borderRadius: "10px" }} />
            <Task>
                <TaskTitle>
                    <IconButton onClick={onClick}>
                        {
                            hideArgs ? <ExpandMoreIcon /> : <ExpandLessIcon />
                        }
                        
                    </IconButton>
                    <InputLabel id="demo-simple-select-label"><h4>Task: </h4></InputLabel>
                    <Select
                        labelId="demo-simple-select-label"
                        id="demo-simple-select"
                        label="Task"
                        variant="standard"
                        onChange={onChange}
                        value={taskType}
                        style={{ marginLeft: "16px", flex: "1 0 0" }}
                    >
                        {
                            TASK_TYPES.map((task_name) => {
                                return (
                                    <MenuItem key={task_name} value={task_name}>{task_name}</MenuItem>
                                )
                            })
                        }
                    </Select>
                </TaskTitle>
                {taskType && !hideArgs && <Divider />}
                {taskType && !hideArgs && (
                    <>
                        <TaskContent>
                            {
                                ARG_LIST[taskType].samples.map((sample) => {
                                    return (
                                        <FormControl key={`${sample}-form`} style={{ margin: "8px 0"}}>
                                            <InputLabel id={sample}>{sample}</InputLabel>
                                            <Select
                                                labelId={sample}
                                                id={`${sample}-select`}
                                                label={sample}
                                                size="small"
                                                variant="standard"
                                                onChange={onSampleChange}
                                                value={samples[sample] ? `${sample}.${samples[sample]}` : samples[sample]}
                                                style={{ flex: "1 0 0", width: "200px" }}
                                            >
                                                {
                                                    sampleNames.map((sp_n) => {
                                                        return (
                                                            <MenuItem key={`${sample}.${sp_n}`} value={`${sample}.${sp_n}`}>
                                                                {sp_n}
                                                            </MenuItem>
                                                        )
                                                    })
                                                }
                                            </Select>
                                        </FormControl>
                                    )
                                })
                            }
                        </TaskContent>
                        <Divider />
                        <TaskContent>
                            {
                                ARG_LIST[taskType].args.map((arg) => {
                                    return (
                                        <TextField
                                            id="outlined-required"
                                            variant="standard"
                                            key={arg}
                                            label={arg}
                                        />
                                    )
                                })
                            }
                        </TaskContent>
                    </>
                )}
            </Task>
        </>
    )
}

export default TaskNode;