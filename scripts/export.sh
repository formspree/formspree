#! /bin/bash
# To set your local env vars, use this like so:
#    scripts/export.sh .env | pbcopy
# then paste into terminal

while read l; do 
	echo export ${l//\"/}
done < $1
