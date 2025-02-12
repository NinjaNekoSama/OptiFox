"""This file shall contain the implementation of OptiFox server side code.

More details are listed in file README.md.
"""

from flask import request, Response, render_template
import connexion
import time
from flask_cors import CORS
from utils import logger
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from flask_limiter import Limiter
from flask_caching import Cache

# Initialize the Flask application
app = connexion.App(__name__, specification_dir="./")
# Register the v1 API
app.add_api("swagger_v1.yml")

# Register the v2 API
app.add_api("swagger_v2.yml")
flask_app = app.app

CORS(app.app, resources={r"/*": {"origins": "https://localhost:3000"}})
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP Requests", ["method", "endpoint", "status_code"]
)
# Setup Flask-Limiter for rate limiting
limiter = Limiter(app.app)

# Setup Flask-Caching
cache = Cache(app.app, config={"CACHE_TYPE": "simple"})


@flask_app.before_request
def before_request():
    request._start_time = (
        request.start_time
    ) = flask_app.prometheus_request_start_time = time.time()


@flask_app.after_request
def after_request(response):
    REQUEST_COUNT.labels(request.method, request.path, response.status_code).inc()
    return response


# Prometheus metrics endpoint
@flask_app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/")
@limiter.limit("10 per minute")
@cache.cached(timeout=60)
def home():
    # Render the 'patient_page.html' template when the home route is accessed
    logger.info("Call from the route handler to the search page....")
    return render_template("starting_doc.html")


if __name__ == "__main__":
    # Enable debug mode for detailed error messages and auto-reloading
    app.run(host="0.0.0.0", port=3000)
