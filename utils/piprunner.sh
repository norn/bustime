#!/bin/bash

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOOT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHONPATH="$ROOOT_DIR/coroutines:$ROOOT_DIR:$ROOOT_DIR/bustime"

export PYTHONPATH=$PYTHONPATH

cd $ROOOT_DIR
source $ROOOT_DIR/.venv/bin/activate
$ROOOT_DIR/.venv/bin/python $SCRIPT_DIR/$@
