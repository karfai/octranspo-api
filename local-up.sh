#!/bin/sh
DATABASE_URL=sqlite://$PWD/octranspo.sqlite3 rackup -p 4567 config.ru