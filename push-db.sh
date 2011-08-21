#!/bin/sh
heroku db:push sqlite://$PWD/octranspo.sqlite3 --confirm furious-autumn-660