#!/bin/sh
git push heroku master
heroku db:push sqlite://$PWD/octranspo.sqlite3 --confirm octranspo-api
