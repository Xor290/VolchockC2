[
  {
    "name": "http",
    "type": "http",
    "host": "172.18.139.212",
    "port": 80,
    "xor_key": "mysupersecretkey",
    "user_agent": "Mozilla/5.0",
    "uri_paths": ["/api", "/update"],
    "http_headers": {
      "Accept": "application/json"
    }
  },
  {
    "name": "http2",
    "type": "http",
    "host": "172.18.139.212",
    "port": 8080,
    "xor_key": "myothersecretkey",
    "user_agent": "Mozilla/5.0",
    "uri_paths": ["/api", "/update"],
    "http_headers": {
      "Accept": "application/json"
    }
  }
]
