"""Plotly dashboard for ALAB management."""

from .plotly_dashboard import app


def launch(host: str, port: str):
    """Runs the plotly dashboard at the given host:port.

    Args:
        host (str): hostname to serve the dashboard on (typically 0.0.0.0 to allow external connections)
        port (str): port to serve the dashboard on
    """
    app.run(host=host, port=str(port), debug=True)
