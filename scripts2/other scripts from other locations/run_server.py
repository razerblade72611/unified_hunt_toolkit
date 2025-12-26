
from __future__ import annotations

import logging

from web.server import create_app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    app.run(debug=True)
