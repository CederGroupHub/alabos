def config_file_update(sim_mode: bool = False):
    """Update the config file."""
    import os

    from alab_management.config import AlabConfig  # type: ignore

    if sim_mode:
        os.environ["SIM_MODE_FLAG"] = "True"

    AlabConfig()
