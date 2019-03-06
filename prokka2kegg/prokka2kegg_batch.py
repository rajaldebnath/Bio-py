#!/usr/bin/python3

"""
Description:
KO entries (K numbers in KEGG annotation) assignment *in batch mode*
according to UniProtKB ID in `Prokka` *.gbk files

Usage:

Step1: Download and initialize the cross-reference database provided by UniProt
$ wget ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/idmapping.dat.gz
$ gzip -dc idmapping.dat.gz | awk '{if($2=="KO") print $1,$3}' OFS="\t" | gzip > idmapping_KO.tab.gz
You could choose to remove 'idmapping.dat.gz' now.

Step2: Retrieve K numbers according to the UniProtKB IDs of proteins
$ python3 gbk2kegg_batch.py -i input_dir -d idmapping_KO.tab.gz -o output_dir

This script will produce a json format database in the same folder of
idmapping_KO.tab.gz for reuse, which may speed up the program when
running next time.
"""

import os
import re
import gzip
import curses
import argparse
import json

__author__ = "Heyu Lin"
__contact__ = "heyu.lin(AT)student.unimelb.edu.au"

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--input', metavar='input_dir', dest='i',
                    type=str, required=True,
                    help='specify the directory containing *.gbk files')
parser.add_argument('-o', '--output', metavar='output_dir', dest='o',
                    type=str, required=True,
                    help='output tab files will be produced in this directory')
parser.add_argument('-d', '--data', metavar='idmapping_KO.tab.gz',
                    dest='d', type=str,
                    help='database generated accroding to "step1" instruction')
args = parser.parse_args()


def gbk_parser(gbk):
    """
    gbk: gbk genome file generated by Prokka
    """
    arr = []  # output array containing locus_tag and UniProtKB
    with open(gbk) as input:
        cds = 0
        locus = 0
        pattern_locus = re.compile('"(.*)"')
        pattern_uniprotkb = re.compile('UniProtKB:(.*)"')
        for line in input.readlines():
            if line.startswith(' ' * 5 + 'CDS'):
                cds = 1  # This is a CDS
            if line.startswith(' ' * 21 + '/locus_tag=') and cds == 1:
                locus_tag = pattern_locus.findall(line)[0]
                locus = 1  # locus_tag was read
            if line.startswith(' ' * 21 + '/inference="similar') and locus == 1:
                uniprotkb = pattern_uniprotkb.findall(line)[0]
                arr.append([locus_tag, uniprotkb])
                cds = 0
                locus = 0
            if line.startswith(' ' * 21 + '/codon_start') and locus == 1:
                arr.append([locus_tag, ''])
                cds = 0
                locus = 0
    return arr


def dict_initialize(gzfile):
    dict = {}
    with gzip.open(gzfile) as fi:
        for line in fi.readlines():
            fields = line.decode('utf-8').strip().split('\t')
            if fields[0] not in dict:
                dict[fields[0]] = [fields[1]]
            else:
                dict[fields[0]].append(fields[1])
    return dict


def dict_load(json_file):
    with open(json_file, 'r') as f:
        r = json.load(f)
    return r


def retrieve_KO(arr, dict):
    """
    arr = [
        ['AMLFNMKI_00003', ''],
        ['AMLFNMKI_00004', 'Q24SP7']
    ]
    new_arr = [
        ['AMLFNMKI_00025', 'Q01465', ['K03569']],
        ['AMLFNMKI_00026', 'P15639', ['K00602','K00604']]
        ['AMLFNMKI_00027', '', '']
    ]
    """
    new_arr = []
    id_no_match = []  # record UniProtKB IDs have no corresponding KO numbers
    for cds in arr:
        if cds[1] == '':
            cds.append('')
            new_arr.append(cds)
        else:
            ko = dict.get(cds[1], None)
            if ko is None:
                id_no_match.append(cds[1])
                cds.append('')
                new_arr.append(cds)
            else:
                cds.append(ko)
                new_arr.append(cds)
    # print(json.dumps(new_arr))
    """ Report failure in search K numbers according to UniProtKB IDs
    print("Warning: The following " + str(len(id_no_match))
          + " UniProtKB IDs don't have corresponding K numbers")
    print(' '.join(id_no_match))
    """
    return new_arr


def write_json(content, outfile):
    with open(outfile, 'w') as fo:
        json.dump(content, fo)


def output(arr, outfile):
    """
    arr = [
        ["AMLFNMKI_00025", Q01465, ["K03569"]],
        ["AMLFNMKI_00026", P15639, ["K00602","K00604"]]
        ["AMLFNMKI_00027", "", ""]
    ]
    """
    with open(outfile, 'w') as fo:
        for cds in arr:
            if cds[2] != "":
                for ko in cds[2]:
                    fo.write(cds[0] + "\t" + ko + "\n")
            else:
                fo.write(cds[0] + "\n")


def get_input_files(dir):
    files = []
    for fi in os.listdir(dir):
        fi_path = os.path.join(dir, fi)
        if os.path.isfile(fi_path) and os.path.splitext(fi)[1] == '.gbk':
            files.append(fi)
    return files


def create_dir(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)


def main():
    create_dir(args.o)
    if os.path.exists(args.d + '.json'):
        db_dict = dict_load(args.d + '.json')
    else:
        db_dict = dict_initialize(args.d)
        write_json(db_dict, args.d + '.json')
    gbks = get_input_files(args.i)
    print("{} gbk files have been read.".format(len(gbks)))
    for gbk in gbks:
        print("parsing {}...".format(gbk))
        in_path = os.path.join(args.i, gbk)
        out_path = os.path.join(args.o, gbk) + ".ko.out"
        mapping_array = gbk_parser(in_path)
        final_arr = retrieve_KO(mapping_array, db_dict)
        output(final_arr, out_path)


if __name__ == '__main__':
    main()
