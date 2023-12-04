def config_file_update(sim_mode: bool = False):
    """Update the config file."""
    from alab_management.config import AlabConfig  # type: ignore

    AlabConfig(sim_mode=sim_mode)
