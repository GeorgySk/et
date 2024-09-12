#!/bin/bash
###exit 0 # TEMPORARY FOR CI TESTS
nodiff=
if [ "$1" == "--nodiff" ] && [ "$2" == "" ]; then nodiff=$1; elif [ "$1" != "" ]; then echo "Usage: $0 [--nodiff]"; exit 1; fi
$(dirname $0)/../../../common/parsertest.sh $nodiff $(dirname $0)
