#!/usr/bin/env python
"""
Status of perf-patch workflow runs, read from their journal files.

Prints a markdown table with one row per candidate: group, builder verdict, reviewer verdict, the patch files to
apply, and the measured gain. Groups that have not started or are still running are shown as such.
Run it from anywhere; it does not need the app or a server.

Usage:
    python status.py --args relaunch-A.json [--args relaunch-B.json ...] --journal <run dir or journal.jsonl> [--journal ...] [--out STATUS.md]

--args are the JSON files passed to the workflow (they define groups and candidates), --journal the workflow
transcript folders that hold journal.jsonl (or the journal files themselves).
"""
import os
import re
import sys
import json
import argparse


def load_journal(path):
    if os.path.isdir(path):
        path = os.path.join(path, 'journal.jsonl')
    started, results = {}, {}
    if not os.path.isfile(path):
        return started, results
    with open(path, encoding='utf8') as f:
        for line in f:
            # a write cut short (for example by a full disk) leaves a partial entry with the next one appended to it
            for piece in ['{"type"' + x for x in line.split('{"type"')[1:]]:
                try:
                    entry = json.loads(piece)
                except ValueError:
                    key = re.search(r'"key":"([^"]+)"', piece)
                    if key and piece.startswith('{"type":"result"'): # keep the verdicts that survived
                        results[key.group(1)] = {'results': [{'id': i, 'verdict': v, 'notes': 'partial journal entry'} for i, v in re.findall(r'\{"id":"([^"]+)","verdict":"([^"]+)"', piece)]}
                    continue
                if entry.get('type') == 'started':
                    started[entry['key']] = entry.get('label', '')
                elif entry.get('type') == 'result':
                    results[entry['key']] = entry.get('result')
    by_label = {}
    for key, label in started.items():
        by_label[label] = results.get(key, 'running')
    return started, by_label


def short(text, n=110):
    text = ' '.join(str(text or '').split())
    return text if len(text) <= n else text[:n - 1] + '…'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--args', action='append', default=[], help='workflow args file (repeatable)')
    parser.add_argument('--journal', action='append', default=[], help='workflow run folder or journal.jsonl (repeatable)')
    parser.add_argument('--out', default=None, help='write the table to this file as well')
    opts = parser.parse_args()

    groups = []
    for p in opts.args:
        with open(p, encoding='utf8') as f:
            groups.extend(json.load(f).get('groups', []))
    labels = {}
    for j in opts.journal:
        _started, by_label = load_journal(j)
        labels.update(by_label)

    rows, counts = [], {}
    for g in groups:
        build = labels.get('build:' + g['id'])
        review = labels.get('attack:' + g['id'])
        built = {r['id']: r for r in (build.get('results', []) if isinstance(build, dict) else [])}
        reviewed = {r['id']: r for r in (review.get('results', []) if isinstance(review, dict) else [])}
        for c in g['candidates']:
            b, r = built.get(c['id']), reviewed.get(c['id'])
            if build is None:
                state = 'queued'
            elif build == 'running':
                state = 'building'
            elif b is None:
                state = 'no build result'
            elif b.get('verdict') == 'reject':
                state = 'rejected by builder'
            elif review == 'running':
                state = f"built ({b.get('verdict')}), reviewing"
            elif r is None and review is None:
                state = f"built ({b.get('verdict')}), waiting for review"
            elif r is None:
                state = f"built ({b.get('verdict')}), no review result"
            else:
                state = f"{b.get('verdict')} / {r.get('verdict')}"
            counts[state.split(' (')[0].split(',')[0]] = counts.get(state.split(' (')[0].split(',')[0], 0) + 1
            patches = (r or {}).get('final_patch_files') or (b or {}).get('patch_files') or []
            gain = (r or {}).get('measured') if r and r.get('gain_confirmed') else (b or {}).get('gain')
            rows.append(f"| {g['id']} | {c['id']} | {state} | {', '.join(os.path.basename(x) for x in patches)} | {short(gain)} |")

    lines = ['| Group | Candidate | State | Patches | Gain |', '|---|---|---|---|---|', *rows, '', 'Totals: ' + ', '.join(f'{k}={v}' for k, v in sorted(counts.items()))]
    text = '\n'.join(lines)
    print(text)
    if opts.out:
        with open(opts.out, 'w', encoding='utf8') as f:
            f.write(text + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
