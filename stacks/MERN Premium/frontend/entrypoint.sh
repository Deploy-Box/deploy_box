#!/bin/sh

# Enter REACT_APP_BACKEND_URL in config.js
sed -i "s|REACT_APP_BACKEND_URL_PLACEHOLDER|${REACT_APP_BACKEND_URL}|g" /usr/share/nginx/html/config.js

nginx -g 'daemon off;'