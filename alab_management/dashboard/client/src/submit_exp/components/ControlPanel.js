import React from 'react';
import Samples from './Samples';

function ControlPanel({ sampleNames, setSampleNames }) {
    return (
        <Samples sampleNames={sampleNames} setSampleNames={setSampleNames} />
    )
}

export default ControlPanel;
