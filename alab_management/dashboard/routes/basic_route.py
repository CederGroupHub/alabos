from pathlib import Path
from typing import cast
from flask import Blueprint, send_from_directory

modules = Blueprint(
    "basic_route",
    __name__,
    static_folder=(Path(__file__).parent.parent / "ui").as_posix(),
)


@modules.route("/", defaults={"path": ""})
@modules.route("/<path:path>")
def serve(path):
    if path != "" and (Path(modules.static_folder) / path).exists():  # type: ignore
        return send_from_directory(cast(str, modules.static_folder), path)
    return send_from_directory(cast(str, modules.static_folder), "index.html")
