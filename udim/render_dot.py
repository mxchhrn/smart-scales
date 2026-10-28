#!/usr/bin/env python3
# check the udim graph json files and write one graphviz dot file per graph
# usage: python3 render_dot.py [graph.json ...]   (default: all s*.json next to this script)
# render: dot -Tsvg -o s1_liorque_cs20a.svg s1_liorque_cs20a.dot

import glob
import json
import os
import sys

NODE_TYPES = ('dev', 'usr', 'env')
SUBGRAPHS = ('alpha', 'beta', 'gamma')
EDGE_COLOR = {'alpha': '#377EB8', 'beta': '#4DAF4A', 'gamma': '#FF7F00'}
SUBGRAPH_TITLE = {'alpha': 'Proximity (α)', 'beta': 'Internal network (β)', 'gamma': 'External network (γ)'}


def check_graph(in_graph, in_name):
    # check ids, types, subgraph membership and edge consistency
    ids = [n['id'] for n in in_graph['nodes']]
    if len(ids) != len(set(ids)):
        print(in_name + ': duplicate node ids')
        sys.exit(1)
    if 'd' not in ids:
        print(in_name + ': central device d missing')
        sys.exit(1)
    by_id = {n['id']: n for n in in_graph['nodes']}
    for n in in_graph['nodes']:
        if n['type'] not in NODE_TYPES:
            print(in_name + ': bad node type ' + n['type'])
            sys.exit(1)
        if not n['subgraphs'] or any(s not in SUBGRAPHS for s in n['subgraphs']):
            print(in_name + ': bad subgraph list on ' + n['id'])
            sys.exit(1)
    for e in in_graph['edges']:
        if e['from'] not in by_id or e['to'] not in by_id:
            print(in_name + ': edge endpoint missing ' + e['from'] + ' ' + e['to'])
            sys.exit(1)
        if e['subgraph'] not in SUBGRAPHS:
            print(in_name + ': bad edge subgraph ' + e['subgraph'])
            sys.exit(1)
        # both endpoints must belong to the subgraph the edge is assigned to
        for v in (e['from'], e['to']):
            if e['subgraph'] not in by_id[v]['subgraphs']:
                print(in_name + ': edge ' + e['from'] + '-' + e['to'] + ' in ' + e['subgraph'] + ' but ' + v + ' is not')
                sys.exit(1)


def node_style(in_node):
    # get the dot attributes for a node by type
    tmp_label = in_node.get('label', in_node['id']).replace('"', '\\"')
    tmp_label = in_node['id'] + '\\n' + tmp_label
    if in_node['type'] == 'env':
        return 'shape=box style="rounded,dashed" label="' + tmp_label + '"'
    elif in_node['type'] == 'usr':
        return 'shape=ellipse label="' + tmp_label + '"'
    elif in_node['id'] == 'd':
        return 'shape=box style="rounded,bold" peripheries=2 label="' + tmp_label + '"'
    return 'shape=box style=rounded label="' + tmp_label + '"'


def home_subgraph(in_node):
    # pick the cluster a node is drawn in: innermost of alpha < beta < gamma
    for s in SUBGRAPHS:
        if s in in_node['subgraphs']:
            return s
    return 'gamma'


def write_dot(in_graph, in_path):
    # write the nested cluster layout: alpha inside beta, gamma beside
    tmp_dev = in_graph['device']
    tmp_title = 'UDIM: ' + tmp_dev['vendor'] + ' ' + tmp_dev['model']
    tmp_lines = ['digraph udim {',
                 '  graph [rankdir=LR fontname="Helvetica" fontsize=11 label="' + tmp_title + '" labelloc=t]',
                 '  node [fontname="Helvetica" fontsize=9]',
                 '  edge [fontname="Helvetica" fontsize=8 penwidth=1.3]']
    tmp_home = {n['id']: home_subgraph(n) for n in in_graph['nodes']}
    tmp_lines.append('  subgraph cluster_beta { label="' + SUBGRAPH_TITLE['beta'] + '" style=dashed color="' + EDGE_COLOR['beta'] + '"')
    tmp_lines.append('    subgraph cluster_alpha { label="' + SUBGRAPH_TITLE['alpha'] + '" style=dashed color="' + EDGE_COLOR['alpha'] + '"')
    for n in in_graph['nodes']:
        if tmp_home[n['id']] == 'alpha':
            tmp_lines.append('      ' + n['id'] + ' [' + node_style(n) + ']')
    tmp_lines.append('    }')
    for n in in_graph['nodes']:
        if tmp_home[n['id']] == 'beta':
            tmp_lines.append('    ' + n['id'] + ' [' + node_style(n) + ']')
    tmp_lines.append('  }')
    tmp_lines.append('  subgraph cluster_gamma { label="' + SUBGRAPH_TITLE['gamma'] + '" style=dashed color="' + EDGE_COLOR['gamma'] + '"')
    for n in in_graph['nodes']:
        if tmp_home[n['id']] == 'gamma':
            tmp_lines.append('    ' + n['id'] + ' [' + node_style(n) + ']')
    tmp_lines.append('  }')
    for e in in_graph['edges']:
        tmp_dir = 'both' if e.get('bidirectional') else 'forward'
        tmp_lines.append('  ' + e['from'] + ' -> ' + e['to'] + ' [dir=' + tmp_dir + ' color="' + EDGE_COLOR[e['subgraph']] + '"]')
    tmp_lines.append('}')
    with open(in_path, 'w') as f:
        f.write('\n'.join(tmp_lines) + '\n')


def main():
    tmp_here = os.path.dirname(os.path.abspath(__file__))
    in_files = sys.argv[1:] or sorted(glob.glob(os.path.join(tmp_here, 's*.json')))
    if not in_files:
        print('no graph json files found')
        sys.exit(1)
    for in_file in in_files:
        with open(in_file) as f:
            tmp_graph = json.load(f)
        check_graph(tmp_graph, os.path.basename(in_file))
        tmp_out = os.path.splitext(in_file)[0] + '.dot'
        write_dot(tmp_graph, tmp_out)
        print('ok ' + os.path.basename(in_file) + ' -> ' + os.path.basename(tmp_out)
              + ' (' + str(len(tmp_graph['nodes'])) + ' nodes, ' + str(len(tmp_graph['edges'])) + ' edges)')


if __name__ == '__main__':
    main()
