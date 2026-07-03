#!/bin/sh
set -e

alembic upgrade head
exec gunicorn app.main:app -c gunicorn.conf.py
