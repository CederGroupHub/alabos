# Defining task
BaseTask serves two roles in alabos. First, it is used to define experiments that are sent 
to the workflow scheduling system. Second, it is used within the workflow system to reserve resources 
(devices and sample positions) and execute tasks on the system.

Similar to define devices, we need to inherit classes from BaseTask.

