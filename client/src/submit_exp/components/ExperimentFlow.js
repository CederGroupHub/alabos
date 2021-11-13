import React, {useState, useRef, useCallback, useEffect} from 'react';
import ReactFlow, {removeElements, addEdge, Controls} from 'react-flow-renderer';
import {Button} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import CallMadeIcon from '@mui/icons-material/CallMade';
import DeleteIcon from '@mui/icons-material/Delete';
import TaskNode from './TaskNode';
import {uid} from 'uid';
import styled from 'styled-components';
import {grey} from '@mui/material/colors';

const FlowDiv = styled.div`
    height: calc(100vh - 60px - 36px - 32px - 1.2px);
`;

const RoundButton = styled(Button)`
  border-radius: 14px !important;
`;

const NODE_TYPE = {
    task: TaskNode
}

function ExperimentFlow({sampleNames}) {
    const [els, setEls] = useState([{
        id: uid(32),
        position: {x: 50, y: 100},
        type: "task",
        data: {sampleNames: sampleNames},
    }]);

    const [selectedNode, setSelectedNode] = useState({})

    const xPos = useRef(50);

    const addNode = useCallback(() => {
        xPos.current += 280;
        setEls((els) => {
            return [
                ...els,
                {
                    id: uid(32),
                    position: {x: xPos.current, y: 100},
                    type: "task",
                    data: {sampleNames: sampleNames}
                }
            ];
        });
    }, [sampleNames]);

    useEffect(() => {
        setEls((els) => {
            return els.map((node) => {
                node.data = {...node.data, sampleNames: sampleNames}
                console.log(node)
                return node
            })
        })
    }, [sampleNames])

    const onConnect = (params) => setEls((els) => addEdge({animated: true, ...params}, els));
    const onElementsRemove = (elementsToRemove) =>
        setEls((els) => removeElements(elementsToRemove, els));

    return (
        <div>
            <div style={{padding: "16px", backgroundColor: grey[100], borderBottom: `1.2px solid ${grey[300]}`}}>
                <RoundButton color="primary" style={{margin: "0 8px"}} variant="contained" onClick={addNode}
                             startIcon={<AddIcon/>}>
                    Add Node
                </RoundButton>
                <RoundButton color="primary" style={{margin: "0 8px"}} variant="contained" startIcon={<CallMadeIcon/>}>
                    Submit
                </RoundButton>
            </div>
            <FlowDiv>
                <ReactFlow
                    elements={els}
                    onConnect={onConnect}
                    onElementsRemove={onElementsRemove}
                    onSelectionChange={(selectedElements) => {
                        const node = selectedElements?.[0]
                        setSelectedNode(node)
                    }}
                    nodeTypes={NODE_TYPE}
                >
                </ReactFlow>
            </FlowDiv>

        </div>
    );
}

export default ExperimentFlow;