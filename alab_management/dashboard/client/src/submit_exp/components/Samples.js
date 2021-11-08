import React, { useRef } from 'react';
import { Chip, TextField, Button } from '@mui/material';
import styled from 'styled-components';

const AddSampleDiv = styled.div`
    display: flex;
    align-items: baseline;
    margin-bottom: 16px;
`;

function Samples({ style, sampleNames, setSampleNames }) {
    const sampleNameInput = useRef('') 
    
    const onDelete = (data) => () => {
        setSampleNames((c) => c.filter((_c) => _c !== data));
    };

    const onClick = () => {
        setSampleNames((c) => c.includes(sampleNameInput.current.value) ? 
        sampleNames : [...sampleNames, sampleNameInput.current.value])
    }
    return (
        <div style={{...style, margin: "16px"}}>
            <AddSampleDiv>
                <TextField id="add_sample_input" size="small" inputRef={sampleNameInput} style={{ width: "50%" }} label="Sample Name" variant="standard" />
                <Button variant="outlined" onClick={onClick} style={{ marginLeft: "16px" }}>Add sample</Button>
            </AddSampleDiv>
            <h4>Samples:</h4>
            {
                sampleNames.map((data) => {
                    return (
                        <Chip
                            style={{ margin: "0 4px"}}
                            key={data}
                            label={data}
                            onDelete={onDelete(data)}
                        />
                    )})
            }

        </div>
    )
}

export default Samples;