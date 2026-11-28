# mini-http-server

A small HTTP/1.1 server written in Python using only the standard library.
It serves HTML, CSS and images from a web root, supports `GET` and `HEAD`,
returns proper error codes, and logs every request.

## Requirements

- Python 3.10 or newer
- No third-party packages (`requirements.txt` is intentionally empty)

## Setup and usage

```bash
git clone https://github.com/rajrituroy2005/mini-http-server.git
cd mini-http-server
python server.py            # serves on http://127.0.0.1:8080
python server.py 9000       # optional: choose a different port
```

Open <http://127.0.0.1:8080> in a browser. Press `Ctrl+C` to stop.
Run from the project root so the relative `www/` web root is found.

Defaults live in `config.py`:

| Setting    | Default       | Meaning                          |
|------------|---------------|----------------------------------|
| `HOST`     | `127.0.0.1`   | Bind address (local only)        |
| `PORT`     | `8080`        | Port, overridable on command line |
| `WEB_ROOT` | `www`         | Folder served to clients         |

## Supported behaviour

| Request             | Result                                   |
|---------------------|------------------------------------------|
| `GET /`             | 200, homepage (`www/index.html`)         |
| `GET /about.html`   | 200, about page                          |
| `GET /style.css`    | 200, `text/css`                          |
| `GET /missing.html` | 404, custom 404 page                     |
| `POST /` (also PUT, DELETE, PATCH, OPTIONS, TRACE) | 405, with `Allow: GET, HEAD` |
| `GET /../config.py` | Rejected (404); nothing outside `www/` is served |
| `HEAD /`            | 200, headers only, no body               |
| Malformed request   | 400                                      |

## Architecture

```
Client (browser / curl)
        |
        v
server.py  (ThreadingHTTPServer + Handler)
   |  1. parse + validate request, reject unsupported methods
   |  2. strip query string
   |  3. call static_files.get_file_response(path)
   |        -> (status, content_type, body_bytes)
   |  4. send headers (Content-Type, Content-Length) and body
   |  5. call request_logger.log_request(...)
   v
Response to client            logs/server.log
```

| Module              | Owner    | Responsibility                                            |
|---------------------|----------|-----------------------------------------------------------|
| `server.py`         | Person 1 | HTTP handler, status codes, GET/HEAD, wiring the modules  |
| `static_files.py`   | Person 2 | File lookup, MIME types, 404 page, path-traversal defence |
| `request_logger.py` | Person 3 | One log line per request, to console and `logs/server.log`|
| `config.py`         | Shared   | Host, port, web root                                      |

Shared interfaces:

```python
get_file_response(path) -> (status_code, content_type, body_bytes)
log_request(method, path, status, client_ip, duration_seconds)
```

Every response, successful or not, goes through `Handler._send`, which is where
logging happens, so failures (404, 405, 400) are logged exactly like successes.

## Logging

Each request writes one line to the console and to `logs/server.log`:

```
2026-11-23 14:10:03 INFO 127.0.0.1 - GET / - 200 - 3.2ms
2026-11-23 14:10:04 INFO 127.0.0.1 - GET /missing.html - 404 - 1.1ms
```

Fields: timestamp, level, client IP, method, path, status code, processing time.
`server.py` passes the duration in seconds; the logger converts it to milliseconds.
CR/LF characters in paths are escaped so a request cannot forge extra log lines.
`logs/*.log` is git-ignored.

## Testing

Automated tests (standard `unittest`, no server needs to be running):

```bash
python -m unittest discover -s tests -t . -v
```

| File                        | Covers                                                                 |
|-----------------------------|------------------------------------------------------------------------|
| `tests/test_logger.py`      | Log format, ms conversion, failures logged, log-injection protection   |
| `tests/test_static_files.py`| Index mapping, MIME types, images as bytes, 404, query strings, traversal |
| `tests/test_server.py`      | Starts a real server on a free port; checks 200/404/405/400, HEAD, traversal, and that every request is logged |

Manual check with curl (server running on 8080):

```bash
curl -i  http://127.0.0.1:8080/                  # 200, homepage
curl -i  http://127.0.0.1:8080/about.html        # 200
curl -i  http://127.0.0.1:8080/style.css         # 200, Content-Type: text/css
curl -i  http://127.0.0.1:8080/missing.html      # 404
curl -i -X POST http://127.0.0.1:8080/           # 405, Allow: GET, HEAD
curl -i --path-as-is http://127.0.0.1:8080/../config.py   # rejected, no file contents
curl -I  http://127.0.0.1:8080/                  # HEAD: 200, headers only
cat logs/server.log                              # one entry per request above
```

Then open the site in a browser and confirm the homepage loads with its CSS.

## Demo script (for the final presentation)

1. `python server.py`, then open `http://127.0.0.1:8080` in a browser.
2. Click through to the About page; visit a non-existent page to show the 404 page.
3. In a second terminal run the curl commands above (POST, HEAD, traversal).
4. Show `logs/server.log` with the status codes and timings.
5. Run the unit tests and show them passing.

## Limitations

- No authentication, HTTPS, caching or database (out of scope for v1).
- Binds to `127.0.0.1` only; do not expose it to a network.
- Only `GET` and `HEAD` are supported.
