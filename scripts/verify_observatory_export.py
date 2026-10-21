#!/usr/bin/env python3
"""Independently verify a seed-42/four-instruction public smoke export. No app imports."""
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path


def verify(data):
    assert data['format'] == 'mhb-public-evidence-v1', 'export contract'
    events, bronze, journals = data['events'], data['bronze'], data['journals']
    assert len(events) == len(bronze) == 17, 'source/archive completeness'
    assert len({e['envelope']['event_id'] for e in events}) == 17, 'unique event identities'
    archive = {b['event']['envelope']['event_id']: b for b in bronze}
    latest, versions, balances = {}, defaultdict(list), defaultdict(int)
    for event in events:
        envelope = event['envelope']
        canonical = json.dumps(envelope, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        assert event['checksum'] == digest, 'source payload checksum'
        receipt = archive[envelope['event_id']]
        assert receipt['event']['envelope'] == envelope, 'archive payload fidelity'
        assert receipt['event']['checksum'] == digest, 'archive checksum'
        assert receipt['received_at'] and receipt['ingestion_run_id'], 'receipt provenance'
        assert event['acknowledged_at'], 'pending acknowledgement'
        assert (envelope['currency'], envelope['currency_exponent']) == ('CAD', 2), 'currency'
        aggregate = envelope['aggregate_id']
        versions[aggregate].append(envelope['aggregate_version'])
        latest[aggregate] = envelope['payload']
    for history in versions.values():
        assert history == list(range(1, len(history)+1)), 'aggregate version continuity'
    for line in journals:
        assert type(line['amount_minor']) is int and line['amount_minor'] > 0, 'exact money'
        balances[line['id']] += line['amount_minor'] * (1 if line['direction'] == 'DEBIT' else -1)
    assert all(value == 0 for value in balances.values()), 'balanced journal groups'
    lines = sum(line['kind'] != 'OPENING' for line in journals)
    assert lines == 18, 'non-opening journal lines'
    run = data['workloads'][0]
    assert (run['seed'], run['count'], run['cursor'], run['status'], run['duplicate_requests']) == (42, 4, 4, 'COMPLETED', 1), 'workload cursor'
    assert [latest[pid]['amount_minor'] for pid in run['payment_ids']] == [685, 416, 1087, 826], 'seeded amounts'
    totals = data['publication']['totals']
    assert sum(p['amount_minor'] for p in latest.values()) == totals['instruction_minor'] == 3014, 'instruction totals'
    assert sum(p['returned_minor'] for p in latest.values()) == totals['return_minor'] == 271, 'return totals'
    assert len(latest) == totals['instruction_count'] == 4, 'instruction grain'
    assert data['publication']['cutoff'] == data['publication']['source_count'] == 17, 'publication cutoff'
    assert any(r['id'] == data['publication']['run_id'] and r['status'] == 'SUCCEEDED' for r in data['runs']), 'publication run'
    return {'event_checksums_verified': 17, 'archive_records': 17, 'unique_instructions': 4, 'non_opening_ledger_lines': lines, 'balanced_journal_groups': len(balances), 'instruction_minor': 3014, 'return_minor': 271, 'duplicate_requests': 1, 'pending_deliveries': 0, 'publication_id': data['publication']['id'], 'publication_run_id': data['publication']['run_id'], 'scenario': data['scenario'], 'workload_id': run['id']}


if __name__ == '__main__':
    print(json.dumps(verify(json.loads(Path(sys.argv[1]).read_text())), indent=2))
