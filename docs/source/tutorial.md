# Tutorial
In this section, we will guide you how to implement a simple autonomous lab for solid-state synthesis
using `alabos` package.

## Automated solid-state synthesis
The solid-state synthesis is one of the most important methods to synthesize inorganic powder materials. Usually, the precursors
are provided in powder form and are mixed together in a specific ratio. The mixture is then heated to a high temperature
for a certain period of time, where the new phase will form. The new phase is then ground and characterized 
using X-ray diffraction.

In this tutorial, we will implement a basic autonomous lab for solid-state synthesis. The lab will include 
a powder dosing and mixing station, four box furnaces, four tube furnaces, a powder grinding station, an XRD
machine. Apart from the devices, we will also provide a set of analysis tasks that will be
executed after the synthesis is finished to interpret the results.

We will implement the interface for various device and tasks that will be used in the lab. The device includes
```
- Labman (for powder dosing)
- Robot Arm
- Box Furnace
- Tube Furnace
- Devices in Powder Grinding Station (Mainly used in the powder recovery task)
- Devices in XRD Sample preparation station (Mainly used in the Diffraction task)
- XRD machine
```
The tasks include
```
- PowderDosing
- Moving
- Manual Heating
- Heating
- HeatingWithAtmosphere
- PowderRecovery
- XRD
```

## The structure of the tutorial
We will start the tutorial from setting up the definition folder, where we will define the devices and tasks, where
the demo of the functionalities of the `alabos` package will be shown. The next step will be to start the simulated lab
and submit the synthesis task. We will also show how to implement the close-loop synthesis, where the synthesis task
new experiment will be submitted after the old one is finished.

```{toctree}
:maxdepth: 1
:hidden:

setup
device_definition
task_definition
start_lab
submit_experiments
```