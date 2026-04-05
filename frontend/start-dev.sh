#!/bin/sh
export PATH="$PWD/node_modules/.bin:$PATH"
exec "$PWD/node_modules/.bin/vite" --port 5174
