"""
SCOPE development entry point.

Usage:
    python run.py            →  http://127.0.0.1:5000

The same application is also mounted under the /scope path prefix so the
sandbox preview gateway can proxy it — running it locally at the root
path works exactly the same way.
"""
import os

from app import create_app


class PathPrefixMiddleware:
    """Allow the WSGI app to be mounted under an optional path prefix."""

    def __init__(self, wsgi_app, prefix="/scope"):
        self.wsgi_app = wsgi_app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if path == self.prefix or path.startswith(self.prefix + "/"):
            environ["SCRIPT_NAME"] = self.prefix
            environ["PATH_INFO"] = path[len(self.prefix):] or "/"
        return self.wsgi_app(environ, start_response)


app = create_app()
app.wsgi_app = PathPrefixMiddleware(app.wsgi_app)

if __name__ == "__main__":
    # Enable SCOPE_DEBUG=1 for auto-reload during local development.
    debug_mode = os.environ.get("SCOPE_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5002, debug=debug_mode, threaded=True)
