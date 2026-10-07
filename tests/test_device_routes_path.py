"""Device routes must accept device names containing "/" (GPSS: ``gpss/auto_balance``)."""

from flask import Flask

from alab_management.dashboard.routes.device import device_bp


def test_device_routes_accept_names_with_a_slash():
    app = Flask(__name__)
    app.register_blueprint(device_bp)
    adapter = app.url_map.bind("localhost")
    for suffix in ("", "/signals", "/verbose-log"):
        _endpoint, args = adapter.match(f"/api/device/gpss/auto_balance{suffix}")
        assert args == {"device_name": "gpss/auto_balance"}, suffix
