#!/usr/bin/env python3

# Copyright 2019-2021 CERN. See the COPYRIGHT file at the top-level
# directory of this distribution. For licensing information, see the
# COPYING file at the top-level directory of this distribution.

import json
import os
import sys

import numpy as np


def append_bmk(tags,
               tputs,
               helinl,
               proc,
               lang,
               fptype,
               avx,
               tput):
    """
    Append one benchmark result in a given logfile
    For cpp, also add or update the tput for the 'best' SIMD mode (BMK-1047)
    """
    if helinl is None:
        raise Exception('ERROR: helinl is None')
    if proc is None:
        raise Exception('ERROR: proc is None')
    if lang is None:
        raise Exception('ERROR: lang is None')
    if fptype is None:
        raise Exception('ERROR: fptype is None')
    if tput is None:
        raise Exception('ERROR: tput is None')
    cpptag = lambda _proc, _fptype, _helinl, _avx: '%s-sa-cpp-%s-inl%d-%s' % (_proc, _fptype, _helinl, _avx)
    cudatag = lambda _proc, _fptype, _helinl: '%s-sa-cuda-%s-inl%d'  %(_proc, _fptype, _helinl)
    if lang == 'cpp':
        if avx is None:
            raise Exception('ERROR: avx is None for cpp')
        tag = cpptag(proc, fptype, helinl, avx)
        tagbest = cpptag(proc, fptype, helinl, 'best')
    elif lang == 'cuda':
        if avx is not None:
            raise Exception( 'ERROR: avx is not None for cuda' )
        tag = cudatag(proc, fptype, helinl)
        tagbest = None
    else:
        raise Exception('ERROR: lang is neither cpp nor cuda')
    if tag in tags:
        idx = tags.index(tag)
        sys.stderr.write('WARNING: tag "%s" already found: replace old throughput %f with new throughput %f\n' % (tag, tputs[idx], tput))
        del tags[idx]
        del tputs[idx]
    if tagbest is not None:
        if tagbest not in tags:
            tags += (tagbest,)
            tputs += (tput,)
        else:
            idx = tags.index(tagbest)
            if tputs[idx] < tput:
                tputs[idx] = tput
    tags += (tag,)
    tputs += (tput,)
    return tags, tputs


def parse_log_txt(file, debug=False):
    """
    Parse throughput12.sh output
    """
    tags = []
    tputs = []
    helinl = None
    lang = None
    fptype = None
    avx = None
    tput = None
    if debug:
        print(f"FILE: {file}")
    fh = open(file)
    for line in fh.readlines() :
        lline = line.split()
        nlline = len(lline)
        if nlline == 0:
            continue
        if lline[0] == 'Process' :
            if lline[nlline - 2] == '[inlineHel=0]':
                helinl = 0
            elif lline[nlline - 2] == '[inlineHel=1]':
                helinl = 1
            else:
                raise Exception(f'ERROR: cannot decode helinl in "{line}"')
            if lline[2].startswith('SIGMA_SM_EPEM_MUPMUM_'):
                proc = 'eemumu'
            elif lline[2].startswith('SIGMA_SM_GG_TTX_'):
                proc = 'ggtt'
            elif lline[2].startswith('SIGMA_SM_GG_TTXG_'):
                proc = 'ggttg'
            elif lline[2].startswith('SIGMA_SM_GG_TTXGG_'):
                proc = 'ggttgg'
            elif lline[2].startswith('SIGMA_SM_GG_TTXGGG_'):
                proc = 'ggttggg'
            else:
                raise Exception(f'ERROR: cannot decode proc in "{line}"')
            if lline[2].endswith('_CPP'):
                lang = 'cpp'
            elif lline[2].endswith('_CUDA'):
                lang = 'cuda'
            else:
                raise Exception(f'ERROR: cannot decode lang in "{line}"')
        if nlline > 1 and lline[0] == 'FP' and lline[1] == 'precision':
            if nlline > 3 and lline[3] == 'DOUBLE':
                fptype = 'd'
            elif nlline > 3 and lline[3] == 'FLOAT':
                fptype = 'f'
            else:
                raise Exception(f'ERROR: cannot decode fptype in "{line}"')
        if nlline > 2 and lline[0] == 'Internal' and lline[1] == 'loops' and lline[2] == 'fptype_sv':
            if nlline > 5 and lline[5] == "('none':": avx = 'none'
            elif nlline > 5 and lline[5] == "('sse4':": avx = 'sse4'
            elif nlline > 5 and lline[5] == "('avx2':": avx = 'avx2'
            elif nlline > 5 and lline[5] == "('512y':": avx = '512y'
            elif nlline > 5 and lline[5] == "('512z':": avx = '512z'
            else: raise Exception( 'ERROR: cannot decode avx in "%s"'%line )
        if lline[0] == 'EvtsPerSec[MECalcOnly]':
            if nlline > 6 and lline[6] == 'sec^-1':
                tput = float(lline[4]) / 1E6  # units: 10^6 events per second
            else:
                raise Exception(f'ERROR: cannot decode tput in "{line}"')
            # Append bmk and clean up
            accept = True
            if accept:
                tags, tputs = append_bmk(tags,
                                         tputs,
                                         helinl,
                                         proc,
                                         lang,
                                         fptype,
                                         avx,
                                         tput)
            helinl = None
            proc = None
            lang = None
            fptype = None
            avx = None
            tput = None
    if debug:
        for bmk in zip(tags, tputs):
            print(bmk)
    return tags, tputs


def parse_bmk_dir(resdir, debug=False):
    """
    Parse the full log directory of a benchmarking test
    """
    if not os.path.isdir(resdir):
        raise Exception(f"ERROR! unknown directory {resdir}")
    resdir = os.path.realpath(resdir)
    if debug:
        print(f"Iterating over {resdir}")
    curlist = os.listdir(resdir)
    curlist.sort()
    all_tputs = []
    for d in curlist:
        if d.find('proc_') != 0:
            continue
        ijob = d[5:]
        logfile = resdir + '/' + d + '/' + 'out_' + ijob + '.log'
        if not os.path.isfile(logfile):
            if debug:
                print(f"WARNING: {logfile} not found")
            continue
        if debug:
            print(f"Parsing {logfile}")
        tags, tputs = parse_log_txt(logfile, debug)
        all_tputs.append(tputs)
    if all_tputs == []:
        raise Exception("ERROR! no logs found in directory {resdir}")
    all_tputs = np.transpose(all_tputs)  # [[cpp-d-inl0-none(1), cpp-d-inl0-none(2), ...], [cpp-d-inl0-sse4(1), cpp-d-inl0-sse4(2), ...], ...]
    if debug:
        print(all_tputs)

    # OrderedDict was used here but with the supported Python versions there
    # is no need for it
    wl_scores = dict(zip(tags, (round(np.sum(s), 6) for s in all_tputs)))
    wl_stats = dict(zip(tags, (get_stats(s) for s in all_tputs)))

    dic_scores = f'"wl-scores" : {json.dumps(wl_scores)}'
    if debug:
        print(dic_scores, end='\n')
    dic_stats = f'"wl-stats" : {json.dumps(wl_stats)}'
    if debug:
        print(dic_stats)
    dic_data = f'{dic_scores} , {dic_stats}'

    dic_data = {"wl-scores": wl_scores,
                "wl-stats": wl_stats}
    print(json.dumps(dic_data))
    return dic_data


def get_stats(s):
    return {"avg": round(np.mean(s), 6),
            "median": round(np.median(s), 6),
            "min": round(np.min(s), 6),
            "max": round(np.max(s), 6),
            "count": len(s)}


#-----------------------------------------------------------------------------------------

# Try the following for a realistic test: python3 -c "from parseResults import *; parseBmkDir('jobs/good_1')"
if __name__ == '__main__':

    # STANDALONE TESTS
    parse_log_txt('jobs/good_1/proc_1/out_1.log', debug=True)
    ###parseBmkDir('jobs/good_1', debug=True)
