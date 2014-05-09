#!/bin/bash
# Launch i3 with a config file assembled from:
#     ~/.i3/config
#     ~/.i3/config.d/*.conf (if any)
#     ~/.i3/hostname.conf (if any)

shopt -s nullglob
tmpconf=$(mktemp --tmpdir i3.config.XXXXXXXXXX)

cat ~/.i3/config > $tmpconf
cat ~/.i3/config.d/*.conf >> $tmpconf
if [ -f ~/.i3/$(hostname).conf ]; then
   cat ~/.i3/$(hostname).conf >> $tmpconf
fi

/usr/bin/i3 "$@" -c $tmpconf

