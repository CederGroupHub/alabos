# Submitting the synthesis experiments

The `alabos` manages each user submission as a separate experiment. Each experiment will define a list of samples you would
like to synthesize, along with the sequence of tasks that need to be performed to synthesize the samples. To ensure the order
of execution, the tasks are defined within a directed acyclic graph (DAG), where the vertices represent the tasks and the edges
represent the dependencies between the tasks.

In typical autonomous lab, there are some tasks that can hold one or multiple samples. For example, one furnace can hold up to
8 samples, while the powder recovery can hold only one sample. So, the task DAG can have multiple incoming/outgoing edges, 
indicating that one task can be dependent on multiple tasks or multiple tasks can be dependent on one task.

One typical task DAG for A-Lab is shown below, where 16 samples are synthesized in one powder dosing task, followed by two heating task, and
finally passing through the powder recovery and diffraction tasks one by one.

```{mermaid}
:caption: Task DAG for A-Lab

%%{init:{'flowchart':{'nodeSpacing': 10, 'rankSpacing': 50}}}%%
flowchart LR
  A[PowderDosing]--> B[Heating]
  A --> C[Heating]
  B --> D1[PowderRecovery]
  B --> F1[PowderRecovery]
  B --> G1[PowderRecovery]
  B --> E1[PowderRecovery]
  B --> H1[PowderRecovery]
  B --> I1[PowderRecovery]
  B --> J1[PowderRecovery]
  B --> K1[PowderRecovery]
  C --> D2[PowderRecovery]
  C --> F2[PowderRecovery]
  C --> G2[PowderRecovery]
  C --> E2[PowderRecovery]
  C --> H2[PowderRecovery]
  C --> I2[PowderRecovery]
  C --> J2[PowderRecovery]
  C --> K2[PowderRecovery]
  D1 --> D3[Diffraction]
  F1 --> F3[Diffraction]
  G1 --> G3[Diffraction]
  E1 --> E3[Diffraction]
  H1 --> H3[Diffraction]
  I1 --> I3[Diffraction]
  J1 --> J3[Diffraction]
  K1 --> K3[Diffraction]
  D2 --> D4[Diffraction]
  F2 --> F4[Diffraction]
  G2 --> G4[Diffraction]
  E2 --> E4[Diffraction]
  H2 --> H4[Diffraction]
  I2 --> I4[Diffraction]
  J2 --> J4[Diffraction]
  K2 --> K4[Diffraction]
  D3 --> D6[Ending]
  F3 --> F6[Ending]
  G3 --> G6[Ending]
  E3 --> E6[Ending]
  H3 --> H6[Ending]
  I3 --> I6[Ending]
  J3 --> J6[Ending]
  K3 --> K6[Ending]
  D4 --> D7[Ending]
  F4 --> F7[Ending]
  G4 --> G7[Ending]
  E4 --> E7[Ending]
  H4 --> H7[Ending]
  I4 --> I7[Ending]
  J4 --> J7[Ending]
  K4 --> K7[Ending]
```

## Builder class
AlabOS offers users a [`ExperimentBuilder`](alab_management.builders.experimentbuilder.ExperimentBuilder) class to define the
experiment. 

## Advanced submission
