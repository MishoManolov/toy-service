import os
from wsgiref.simple_server import make_server

from toy_service.app import create_app
from toy_service.shortener import Shortener
from toy_service.storage import SqliteLinkStore

if __name__ == "__main__":
    path = os.environ.get("TOY_SERVICE_DB", "toy_service.db")
    with SqliteLinkStore(path) as store:
        app = create_app(Shortener(store=store))
        with make_server("127.0.0.1", 8000, app) as server:
            server.serve_forever()
