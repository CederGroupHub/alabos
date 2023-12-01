def config_file_update(sim_mode: bool = False):
    """Update the config file."""
    from alab_management.config import AlabConfig

    print(f"config_file_update: sim_mode = {sim_mode}")
    # AlabConfig(sim_mode)
    config = AlabConfig(sim_mode=sim_mode)
    print(f"config = {config}")
