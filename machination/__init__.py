def create_secret_file(location, mode='r'):
    """Create file only readable by system(+machination)/admins"""
    # TODO (colin): implement this properly
    return open(location, mode)
