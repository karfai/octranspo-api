#!/bin/sh
heroku db:push sqlite://$PWD/octranspo.sqlite3 --confirm octranspo-api
