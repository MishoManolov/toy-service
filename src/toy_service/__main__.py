from wsgiref.simple_server import make_server

from toy_service.app import create_app
from toy_service.shortener import Shortener

if __name__ == "__main__":
    with make_server("127.0.0.1", 8000, create_app(Shortener())) as server:
        server.serve_forever()
