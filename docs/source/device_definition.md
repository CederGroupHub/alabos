# Defining new device

To define a device, you should inherit from [`BaseDevice`](alab_management.device_view.device.BaseDevice). `BaseDevice`
provides a basic interface for a device, with a few abstract methods that should be implemented in the derived class.

Other than the required abstract methods, you can also define additional methods that are specific to the device. For
example, you can define a `.do_powder_dosing` function for a powder dosing station, or a `.move_to` function for a robot arm.
The defined methods will be accessible to the task that uses the device.

In this tutorial, we will take the box furnace as an example. 

```{note}
Considering the various communication protocol and the complexity of the device, we will not implement the actual
communication with the device in this tutorial. But the code should be good to run on simulation mode.

If you are interested in how the communication can be implemented, you can check [alab_control](https://github.com/CederGroupHub/alab_control,
where all the communication with the device is implemented for A-Lab.
```

## Implementing `BoxFurnace`
### Connection and basic metadata
### Defining the device interface
#### Setting up the message
#### Error handling
### Mocking the device

## Registering the device
