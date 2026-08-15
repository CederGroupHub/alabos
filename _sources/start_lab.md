# Launching lab

## Enable simulation mode
By default, the simulation mode is on to avoid accidentally connecting to the actual devices. You can
set the environment variable `SIM_MODE_FLAG` to `FALSE` to disable the simulation mode.

```bash
export SIM_MODE_FLAG=TRUE  # this is the default value
```

```{danger}
Run `export SIM_MODE_FLAG=FALSE` only when you are on the *production server*.
```

```{note}
As in this tutorial, we will always run the code with the simulation mode on.
```

## Config file location
By default, there should be a config file in the root dir of the project. 
If you want to use a different config file, you can set the environment 
variable `CONFIG_FILE` to the path of the config file before running the 
commands afterwards.

```bash
export ALABOS_CONFIG_PATH=/path/to/config.toml
```

## Set up / clean up the lab
Before starting the lab, `alabos` needs to scan the definition folders to register all
the available devices and sample positions

```bash
alabos setup
```

To clean up the lab, run the following command:

```bash
alabos clean
```

If you would like to clean up the set up and start from scratch, you can run the following command:

```bash
alabos clean -a
```

A prompt will ask you to confirm the action.



## Start the lab and the worker
To start the lab, run the following command
```bash
alabos launch

# you can also specify the host and port
# alabos launch --host localhost --port 8895
```

Now you will see the `alabos` dashboard at `http://localhost:8895` in your browser. However,
to let the tasks run, you need to start the worker as well. 

```bash
alabos launch_worker

# you can also specify the number of processes and threads for the worker
# for higher parallelism
# alabos launch_worker --processes 4 --threads 16
```

## Summary
After setting up the lab with command `alabos setup`, you can start the lab and the worker with the commands `alabos launch` and `alabos launch_worker`. 
```bash
##############
# Terminal 1 #
##############

alabos launch


##############
# Terminal 2 #
##############

alabos launch_worker
```