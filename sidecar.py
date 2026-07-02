#!/usr/bin/env python3
import logging
import os
import pathlib
import inotify_simple
import redis

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

PERSIST_DIR = pathlib.Path(os.getenv('PERSIST_DIR', '/var/log/freeradius/tlscache'))
REDIS_HOST  = os.getenv('REDIS_HOST', 'freeradius-redis.freeradius.svc.cluster.local')
REDIS_PORT  = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB    = int(os.getenv('REDIS_DB', '2'))
SESSION_TTL = int(os.getenv('SESSION_TTL', '28800'))

PERSIST_DIR.mkdir(parents=True, exist_ok=True)

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, socket_connect_timeout=5)
r.ping()
log.info("Connected to Redis db=%d at %s:%d", REDIS_DB, REDIS_HOST, REDIS_PORT)

pulled = 0
for key in r.scan_iter('*'):
    path = PERSIST_DIR / key.decode()
    if not path.exists():
        data = r.get(key)
        if data:
            path.write_bytes(data)
            pulled += 1
log.info("Pulled %d sessions from Redis on startup", pulled)

inotify = inotify_simple.INotify()
inotify.add_watch(str(PERSIST_DIR), inotify_simple.flags.CLOSE_WRITE)
log.info("Watching %s for new TLS sessions", PERSIST_DIR)

while True:
    for event in inotify.read():
        if not event.name:
            continue
        path = PERSIST_DIR / event.name
        if path.exists():
            data = path.read_bytes()
            r.setex(event.name, SESSION_TTL, data)
            log.debug("Pushed %s (%d bytes) TTL=%ds", event.name, len(data), SESSION_TTL)
