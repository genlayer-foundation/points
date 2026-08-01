#!/usr/bin/env python
"""Sync the production database into local db.sqlite3.

Production is dumped with pg_dump, restored into a local Postgres container,
brought up to the current schema, and only then converted to SQLite. The
conversion never talks to production: `dumpdata` issues a query per row for
many-to-many fields, which over a remote link runs at roughly 90 rows/minute
and never finishes against a ~56k-user database.

Usage:
    python scripts/sync_prod_to_sqlite.py                  # full sync
    python scripts/sync_prod_to_sqlite.py --reuse-dump     # skip pg_dump, use newest backup
    python scripts/sync_prod_to_sqlite.py --reuse-postgres # skip download+restore entirely
    python scripts/sync_prod_to_sqlite.py --keep-container # leave Postgres running afterwards

All user passwords become 'pass'.
"""
import argparse
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = BACKEND_DIR / 'backups'
SNAPSHOT = BACKEND_DIR / 'prod_snapshot.json'

PROD_PARAM = '/tally/prod/database_url'
PG_IMAGE = 'postgres:17'
CONTAINER = 'tally-local-pg'
PG_PORT = '5434'
PG_PASSWORD = 'localpass'
LOCAL_DB_URL = f'postgresql://postgres:{PG_PASSWORD}@localhost:{PG_PORT}/postgres'

# contenttypes and auth.permission are deliberately NOT excluded: the m2m rows
# in users_user_user_permissions reference production's permission ids, and a
# freshly migrated database generates different ones, which fails loaddata's
# foreign key check at commit time.
DUMPDATA_EXCLUDES = ['sessions', 'admin.logentry', 'leaderboard.leaderboardentry']

# Docker platform must be explicit: a cached amd64 postgres image on Apple
# Silicon dies with "exec format error".
DOCKER_PLATFORM = 'linux/arm64' if platform.machine() == 'arm64' else 'linux/amd64'


def log(msg):
    print(f'\n=== {msg}', flush=True)


def run(cmd, **kwargs):
    kwargs.setdefault('check', True)
    return subprocess.run(cmd, **kwargs)


def capture(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()


def dump_production():
    log('Dumping production with pg_dump')
    url = capture([
        'aws', 'ssm', 'get-parameter', '--name', PROD_PARAM,
        '--with-decryption', '--query', 'Parameter.Value', '--output', 'text',
    ])
    rest = url.split('://', 1)[1]
    creds, hostpart = rest.split('@', 1)
    user, password = creds.split(':', 1)
    hostport, dbname = hostpart.split('/', 1)
    host, _, port = hostport.partition(':')
    port = port or '5432'

    BACKUP_DIR.mkdir(exist_ok=True)
    out = BACKUP_DIR / f'tally_prod_{datetime.now():%Y%m%d_%H%M%S}.sql'
    print(f'{host}:{port}/{dbname} -> {out.name}', flush=True)
    run([
        'docker', 'run', '--rm', '--platform', DOCKER_PLATFORM,
        '-v', f'{BACKUP_DIR}:/backup',
        '-e', f'PGPASSWORD={password}',
        PG_IMAGE, 'pg_dump',
        '-h', host, '-p', port, '-U', user, '-d', dbname,
        '--no-owner', '--no-acl', '--clean', '--if-exists',
        '--format=plain', f'--file=/backup/{out.name}',
    ])
    return out


def latest_dump():
    dumps = sorted(BACKUP_DIR.glob('tally_prod_*.sql'), key=lambda p: p.stat().st_mtime)
    if not dumps:
        sys.exit('No dump found in backups/. Run without --reuse-dump.')
    return dumps[-1]


def start_postgres():
    log('Starting local Postgres container')
    existing = capture(['docker', 'ps', '-aq', '-f', f'name=^{CONTAINER}$'])
    if existing:
        run(['docker', 'start', CONTAINER], stdout=subprocess.DEVNULL)
    else:
        run([
            'docker', 'run', '-d', '--name', CONTAINER, '--platform', DOCKER_PLATFORM,
            '-e', f'POSTGRES_PASSWORD={PG_PASSWORD}', '-e', 'POSTGRES_DB=postgres',
            '-p', f'{PG_PORT}:5432', PG_IMAGE,
        ], stdout=subprocess.DEVNULL)

    for _ in range(60):
        ready = subprocess.run(
            ['docker', 'exec', CONTAINER, 'pg_isready', '-U', 'postgres'],
            capture_output=True,
        )
        if ready.returncode == 0:
            print(f'Postgres ready on localhost:{PG_PORT}', flush=True)
            return
        time.sleep(2)
    sys.exit('Postgres container did not become ready.')


def restore(dump_path):
    log(f'Restoring {dump_path.name} into local Postgres')
    run(['docker', 'cp', str(dump_path), f'{CONTAINER}:/tmp/dump.sql'])
    # The dump carries --clean --if-exists, so restoring over an existing copy
    # is fine; ON_ERROR_STOP=0 tolerates the drop statements on a fresh volume.
    run([
        'docker', 'exec', '-e', f'PGPASSWORD={PG_PASSWORD}', CONTAINER,
        'psql', '-q', '-U', 'postgres', '-d', 'postgres',
        '-v', 'ON_ERROR_STOP=0', '-f', '/tmp/dump.sql',
    ], stdout=subprocess.DEVNULL)


def manage(args, db_url=None):
    env = os.environ.copy()
    if db_url:
        env['DATABASE_URL'] = db_url
    else:
        env.pop('DATABASE_URL', None)
    run([sys.executable, '-u', 'manage.py'] + args, cwd=BACKEND_DIR, env=env)


def export_snapshot():
    # Production's schema lags the code, so migrate the local copy first or
    # dumpdata fails on columns that only exist in the models.
    log('Migrating local Postgres copy up to current schema')
    manage(['migrate'], db_url=LOCAL_DB_URL)

    log('Exporting snapshot from local Postgres')
    args = ['dumpdata', '--indent', '2']
    for label in DUMPDATA_EXCLUDES:
        args += ['--exclude', label]
    args += ['--output', str(SNAPSHOT)]
    manage(args, db_url=LOCAL_DB_URL)
    print(f'{SNAPSHOT.name}: {SNAPSHOT.stat().st_size / 1e9:.1f} GB', flush=True)


def rebuild_sqlite():
    log('Creating fresh SQLite database')
    db = BACKEND_DIR / 'db.sqlite3'
    if db.exists():
        backup = BACKEND_DIR / f'db.sqlite3.backup_{datetime.now():%Y%m%d_%H%M%S}'
        db.replace(backup)
        print(f'Existing database saved to {backup.name}', flush=True)
    manage(['migrate'])

    log('Loading snapshot into SQLite')
    run([sys.executable, '-u', __file__, '--_load', str(SNAPSHOT)], cwd=BACKEND_DIR)


def load_into_sqlite(snapshot):
    """Child step: runs with SQLite settings, signals off, tables cleared."""
    os.environ.pop('DATABASE_URL', None)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tally.settings')
    sys.path.insert(0, str(BACKEND_DIR))

    import django

    django.setup()

    from django.contrib.auth import get_user_model
    from django.contrib.auth.hashers import make_password
    from django.contrib.contenttypes.models import ContentType
    from django.core.management import call_command
    from django.db import connection
    from django.db.models import signals

    # Several post_save receivers ignore Django's `raw` flag and recreate rows
    # the snapshot already contains -- contributions.sync_contribution_discord_xp_state
    # collides on ContributionDiscordXPState.contribution_id, and the User
    # receivers in users/signals.py and poaps/signals.py fire once per restored
    # user. A full snapshot needs no derived writes, so suppress all of them.
    all_signals = [
        signals.pre_save, signals.post_save,
        signals.pre_delete, signals.post_delete,
        signals.m2m_changed,
    ]
    saved = {}
    for sig in all_signals:
        saved[sig] = sig.receivers
        sig.receivers = []
        sig.sender_receivers_cache.clear()

    # Data migrations seed rows (default projects, contribution types) that
    # collide with the snapshot on natural keys such as slug.
    with connection.cursor() as cur:
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [r[0] for r in cur.fetchall() if r[0] != 'django_migrations']
        cur.execute('PRAGMA foreign_keys = OFF')
        for table in tables:
            cur.execute(f'DELETE FROM "{table}"')
        cur.execute('PRAGMA foreign_keys = ON')
    print(f'Cleared seeded rows from {len(tables)} tables', flush=True)

    try:
        call_command('loaddata', snapshot, verbosity=1)
        ContentType.objects.clear_cache()
        n = get_user_model().objects.update(password=make_password('pass'))
        print(f"Reset password to 'pass' for {n} users", flush=True)
    finally:
        for sig, receivers in saved.items():
            sig.receivers = receivers
            sig.sender_receivers_cache.clear()


def verify():
    log('Verifying')
    import sqlite3

    con = sqlite3.connect(BACKEND_DIR / 'db.sqlite3')
    dangling = con.execute('PRAGMA foreign_key_check').fetchall()
    print(f'Dangling foreign keys: {len(dangling)}', flush=True)
    for table in ('users_user', 'contributions_contribution', 'leaderboard_leaderboardentry'):
        n = con.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
        print(f'{table}: {n}', flush=True)
    con.close()
    return not dangling


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reuse-dump', action='store_true', help='use newest backups/*.sql')
    p.add_argument('--reuse-postgres', action='store_true', help='container already holds the data')
    p.add_argument('--keep-container', action='store_true', help='leave Postgres running')
    p.add_argument('--keep-json', action='store_true', help='keep the intermediate snapshot')
    p.add_argument('--no-leaderboard', action='store_true', help='skip leaderboard rebuild')
    p.add_argument('--_load', help=argparse.SUPPRESS)
    args = p.parse_args()

    if args._load:
        load_into_sqlite(args._load)
        return

    started = time.time()
    if not args.reuse_postgres:
        dump = latest_dump() if args.reuse_dump else dump_production()
        start_postgres()
        restore(dump)
    else:
        start_postgres()

    export_snapshot()
    rebuild_sqlite()

    if not args.no_leaderboard:
        # Leaderboard entries are excluded from the snapshot; rebuild them.
        log('Rebuilding leaderboard')
        manage(['update_leaderboard'])

    ok = verify()

    if not args.keep_json:
        SNAPSHOT.unlink(missing_ok=True)
    if not args.keep_container:
        run(['docker', 'stop', CONTAINER], stdout=subprocess.DEVNULL)
        print(f'Stopped {CONTAINER} (docker start {CONTAINER} to reuse)', flush=True)

    log(f'Done in {(time.time() - started) / 60:.0f} min. All passwords are pass.')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
