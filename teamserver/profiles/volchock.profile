[
  {
    "name": "http",
    "type": "http",
    "port": 8080,
    "user_agent": "Mozilla/5.0",
    "uri_paths": ["/api", "/update"],
    "http_headers": {
      "Accept": "application/json"
    }
  },

  {
    "name": "quic",
    "type": "quic",
    "port": 443,
    "user_agent": "curl/8.14.1",
    "certfile": "teamserver/profiles/quic_server.crt",
    "keyfile": "teamserver/profiles/quic_server.key"
  },

  {
    "name": "dns",
    "type": "dns",
    "port": 5300
  }
]
