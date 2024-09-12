# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level
# directory of this distribution. For licensing information, see the
# COPYING file at the top-level directory of this distribution.

parseResultsDir=$(cd $(dirname ${BASH_SOURCE}); pwd) # needed to locate parseResults.py

# Function parseResults must be defined in each benchmark (or in a separate file parseResults.sh)
# Logfiles have been stored in process-specific working directories <basewdir>/proc_<1...NCOPIES>
# please store here the overall json summary file for all NCOPIES processes combined
function parseResults(){
  echo "[parseResults] current directory: $(pwd)"
  #-----------------------
  # Parse results (python)
  #-----------------------
  echo -e "\n[parseResults] python parser starting using $(python3 -V &> /dev/stdout)"
  local resJSON # declare 'local' separately to avoid masking $? (https://stackoverflow.com/a/4421282)
  resJSON=$(PYTHONPATH=${parseResultsDir} python3 -c "from parseResults import *; parse_bmk_dir('.')") # same directory as parseResults.sh
  pystatus=$?
  if [ "$pystatus" == "0" ]; then
    echo $resJSON > $baseWDir/parser_output.json
    cat $baseWDir/parser_output.json
  fi
  echo "[parseResults] python parser completed (status=$pystatus)"
  return $pystatus
}

