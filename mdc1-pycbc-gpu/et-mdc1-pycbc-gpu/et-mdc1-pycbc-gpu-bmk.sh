#!/bin/bash

# Copyright 2019-2022 CERN. See the COPYRIGHT file at the top-level
# directory of this distribution. For licensing information, see the
# COPYING file at the top-level directory of this distribution.

#set -x # enable debug printouts

#set -e # immediate exit on error

# Function doOne must be defined in each benchmark
# Input argument $1: process index (between 1 and $NCOPIES)
# Return value: please return 0 if this workload copy was successful, 1 otherwise
# The following variables are guaranteed to be defined and exported: NCOPIES, NTHREADS, NEVENTS_THREAD, EXTRA_ARGS, BMKDIR, DEBUG
# The function is started in process-specific working directory <basewdir>/proc_$1:
# please store here the individual log files for each of the NCOPIES processes
function doOne(){
  if [ "$1" == "" ] || [ "$2" != "" ]; then echo "[doOne] INTERNAL ERROR! Invalid arguments '$@' to doOne"; return 1; fi
  echo "[doOne ($1)] $(date) starting in $(pwd)"
  workDir=$(pwd)
  # Choose whether to run benchmarks on CPU only, GPU only or both
  # Based on EXTRA_ARGS passed via '--extra-args'
  echo "[doOne ($1)] $(date) EXTRA_ARGS='$EXTRA_ARGS'"
  status=0
  cpuorgpus=
  flts=
  inls=
  for arg in $EXTRA_ARGS; do
    if [ "${arg}" == "--cpu" ] && [ "${cpuorgpus}" == "" ]; then
      cpuorgpus=${arg}
    elif [ "${arg}" == "--gpu" ] && [ "${cpuorgpus}" == "" ]; then
      cpuorgpus=${arg}
    elif [ "${arg}" == "--both" ] && [ "${cpuorgpus}" == "" ]; then
      cpuorgpus=${arg}
    elif [ "${arg}" == "-dbl" ] && [ "${flts/dbl }" == "${flts}" ]; then
      flts="${arg} ${flts}"
    elif [ "${arg}" == "-flt" ] && [ "${flts/flt }" == "${flts}" ]; then
      flts="${arg} ${flts}"
    elif [ "${arg}" == "-inl0" ] && [ "${inls/inl0 }" == "${inls}" ]; then
      inls="${arg} ${inls}"
    elif [ "${arg}" == "-inl1" ] && [ "${inls/inl1 }" == "${inls}" ]; then
      inls="${arg} ${inls}"
    else
      echo "[doOne ($1)] $(date) ERROR! Invalid argument '${arg}'"
      echo "[doOne ($1)] $(date) Usage: --extra-args '[--cpu|--gpu|-both] [-dbl][-flt] [-inl0][-inl1]'"
      status=1; echo "[doOne ($1)] $(date) completed (status=${status})"; return ${status}
    fi
  done
  if [ "${cpuorgpus}" == "" ]; then
    cpuorgpus="--both" # default is both CPU and GPU benchmarks
    echo "[doOne ($1)] $(date) No --cpu, --gpu or --both was specified in EXTRA_ARGS: run default cpuorgpus='--both' (CPU and GPU benchmarks)"
  else
    echo "[doOne ($1)] $(date) From EXTRA_ARGS: cpuorgpus='${cpuorgpus}'"
  fi
  if [ "${flts}" == "" ]; then
    echo "[doOne ($1)] $(date) No -dbl or -flt was specified in EXTRA_ARGS: run both double and single precision benchmarks"
    flts="-dbl -flt" # default is both dbl and flt
  else
    fltsold="${flts}"; flts=""; for flt in ${fltsold}; do flts="${flt} ${flts}"; done # reverse list
    echo "[doOne ($1)] $(date) From EXTRA_ARGS: flts='${flts}'"
  fi
  if [ "${inls}" == "" ]; then
    echo "[doOne ($1)] $(date) No -inl0 or -inl1 was specified in EXTRA_ARGS: run only benchmarks without inlining"
    inls="-inl0" # default is inl0 only
  else
    inlsold="${inls}"; inls=""; for inl in ${inlsold}; do inls="${inl} ${inls}"; done # reverse list
    echo "[doOne ($1)] $(date) From EXTRA_ARGS: inls='${inls}'"
  fi
  if [ "${cpuorgpus}" != "--cpu" ]; then
    # Test if a GPU exists
    # [NB: if a GPU physically exists but nvidia-smi fails, then /dev will still contain nvidia*]
    # See https://docs.nvidia.com/datacenter/tesla/mig-user-guide/#device-nodes
    if ls /dev | grep nvidia > /dev/null; then
      echo "[doOne ($1)] $(date) cpuorgpus=${cpuorgpus} and a GPU is installed on this system (/dev/nvidia* found)"
      if [ "$NCOPIES" != "1" ]; then
        # Issue a warning not an error: the GPU can be shared across many processes/copies, but throughput is slower, eg lose 10% on 4 copies
        echo "[doOne ($1)] $(date) WARNING! NCOPIES=$NCOPIES slows down madgraph4gpu 'sa' benchmarks on one GPU: a single copy ('-c 1') is recommended"
      fi
    else
      echo "[doOne ($1)] $(date) WARNING! cpuorgpus=${cpuorgpus} but no GPU is installed on this system (no /dev/nvidia* found)"
      if [ "${cpuorgpus}" == "--both" ]; then
        echo "[doOne ($1)] $(date) WARNING! cpuorgpus=${cpuorgpus} but there is no GPU: run only the CPU benchmarks"
      else
        echo "[doOne ($1)] $(date) ERROR! cpuorgpus=${cpuorgpus} but there is no GPU: there is no benchmark to run"
        status=1; echo "[doOne ($1)] $(date) completed (status=${status})"; return ${status}
      fi
    fi
    # Set up CUDA
    export CUDA_HOME=/usr/local/cuda-12.2
    export PATH=${CUDA_HOME}/bin:${PATH}
  fi
  # Configure WL copy
  if [ ! -d /bmk/build/et ]; then
    echo "[doOne ($1)] $(date) ERROR! et workload not found in /bmk/build/et"
    status=1; echo "[doOne ($1)] $(date) completed (status=${status})"; return ${status}
  else
    echo "[doOne ($1)] $(date) et workload found in /bmk/build/et"
    echo "[doOne ($1)] $(date) copy /bmk/build/et into ${workDir}/et"
    ln -sf /bmk/build/et ${workDir}/et # faster than copying
  fi
  # Setup WL copy
  echo "[doOne ($1)] $(date) Reinterpret \$NEVENTS_THREAD=${NEVENTS_THREAD} as a multiplier (BMKMULTIPLIER) for process-dependent predefined numbers of events"
  # Generate templates if not generated yet
  if [ ! -f "template.csv" ]; then
    echo "[doOne ($1)] $(date) template.csv not found. Generating file..."
    python3 /bmk/build/et/template_generator.py
    if [ -f "template.csv" ]; then
      echo "[doOne ($1)] $(date) template.csv has been successfully generated."
    else
      echo "[doOne ($1)] $(date) Failed to generate template.csv."
    fi
  else
    echo "[doOne ($1)] $(date) template.csv already exists."
  fi
  # Execute sub-actions of WL copy one by one
  for flt in $flts; do
    for inl in $inls; do
      # Sleep at most for 1000 steps of 0.1 seconds each, i.e. 100 seconds in total
      syncprocesses $1 --workDir $workDir --status $status --sleepstep 0.1 --sleepstepsleft 1000
      status=${?}
      # Execute one action
      action="${flt} ${inl}"
      if [ "$status" != "0" ]; then
        # This process failed setup or a previous action, or it received ABORT from a failure in another process
        echo "[doOne ($1)] $(date) current status=$status: skip next action '${action}'"
      else
        echo "[doOne ($1)] $(date) current status=$status: execute next action '${action}'"
        # TODO: add passing ${action} to job.py
        echo "[doOne ($1)] $(date) Will execute 'python3 /bmk/build/et/job.py ${action}'"
        echo "[doOne ($1)] $(date) Will execute 'python3 /bmk/build/et/job.py ${action}'" \
          >> ${workDir}/out_$1.log 2> >(tee -a ${workDir}/out_$1.log >&2)
        python3 /bmk/build/et/job.py \
          >> ${workDir}/out_$1.log 2> >(tee -a ${workDir}/out_$1.log >&2)
        status=${?}
        echo "[doOne ($1)] $(date) current status=$status: completed action '${action}'"
      fi
    done
  done
  # Clean up
  \rm -rf ${workDir}/et
  echo "[doOne ($1)] $(date) completed (status=${status})"
  # Return 0 if this workload copy was successful, 1 otherwise
  return ${status}
}

# Optional function usage_detailed may be defined in each benchmark
# Input arguments: none
# Return value: none
function usage_detailed(){
  echo "Optional EXTRA_ARGS: [--cpu|--gpu|-both] [-dbl][-flt] [-inl0][-inl1]"
  echo "  --cpu   : (CPU or GPU?)     run only the C++ benchmarks on CPU (1 or more copies)"
  echo "  --gpu   : (CPU or GPU?)     run only the CUDA benchmarks on GPU (1 copy)"
  echo "  --both  : (CPU or GPU?)     run both the C++ benchamrks on CPU and the CUDA benchmarks on GPU (1 copy)"
  echo "  -dbl    : (float precision) double precision 'd' benchmarks"
  echo "  -flt    : (float precision) single precision 'f' benchmarks"
  echo "  -inl0   : (C++ inlining)    benchmarks without C++ aggressive inlining"
  echo "  -inl1   : (C++ inlining)    benchmarks with C++ aggressive inlining"
  echo "DEFAULT is '--both -dbl -flt -inl0' (both CPU and GPU, both d and f, inl0 only)"
  echo ""
  echo "If you start the benchmark by mistake and need to kill all associated processes, run the following command:"
  echo "  kill \$(ps -ef | egrep '(et-mdc1-pycbc-gpu-bmk.sh|job.py|check.exe)' | grep -v grep | awk '{print \$2}')"
}

# Default values for NCOPIES, NTHREADS, NEVENTS_THREAD must be set in each benchmark
#NCOPIES=$(nproc)
NCOPIES=1
NTHREADS=1 # cannot be changed by user input (single-threaded single-process WL)
NEVENTS_THREAD=1 # multiplier for a process-dependent predefined number of events

# Source the common benchmark driver
if [ -f $(dirname $0)/bmk-driver.sh ]; then
  . $(dirname $0)/bmk-driver.sh
else
  . $(dirname $0)/../../../common/bmk-driver.sh
fi
