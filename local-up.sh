#!/bin/sh
DATABASE_URL=sqlite:///home/don/src/projects/octranspo/octranspo-api/octranspo.sqlite3 rackup -p 4567 config.ru