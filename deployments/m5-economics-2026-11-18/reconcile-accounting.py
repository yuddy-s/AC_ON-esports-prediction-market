"""Check saved Sepolia observations offline; this makes no RPC calls or transactions."""
import json
from decimal import Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'deployments/sepolia-2026-11-02'
DESTINATION = Path(__file__).resolve().parent
FILES = ['market-0-void-settlement-evidence.json', 'market-0-void-payout-evidence.json', 'market-0-creator-surplus-evidence.json']
settlement, payout, surplus = [json.loads((SOURCE / name).read_text()) for name in FILES]
def require(condition, message):
    if not condition:
        raise AssertionError(message)
def amount(value):
    with localcontext() as context:
        context.prec = 80
        return format(Decimal(str(value)) / Decimal(10**18), 'f')

for evidence in [settlement, payout, surplus]:
    require(evidence['chain_id'] == 11155111 and evidence['market_id'] == 0, 'Wrong chain or market')
    require(evidence['contract_address'].lower() == settlement['contract_address'].lower(), 'Contract mismatch')
    require(all(evidence['checks'].values()), 'A previously recorded receipt check failed')
s, p, w = settlement['after'], payout['after'], surplus['after']
collateral = s['market']['collateralBalance']
liability = int(s['remaining_liability'])
refund = int(settlement['amounts_acon']['bond_refunded']) * 10**18
paid = int(payout['received_payout_base_units'])
withdrawn = int(surplus['received_withdrawal_base_units'])
shares = s['market']['yesQuantity'] + s['market']['noQuantity']
require(liability == (shares + 1) // 2, 'VOID reserve is not ceiling half shares')
require(paid == shares // 2 == liability, 'Combined VOID claim mismatch')
require(collateral == paid + withdrawn, 'Payout and surplus do not exhaust collateral')
require(int(settlement['before']['contract_token_balance']) == refund + collateral, 'Bond/collateral split mismatch')
require(int(s['contract_token_balance']) == collateral, 'Bond refund changed market collateral')
require(p['market']['collateralBalance'] == withdrawn and p['remaining_liability'] == 0, 'Post-claim reserve mismatch')
require(p['yes_position'] == p['no_position'] == p['market']['yesQuantity'] == p['market']['noQuantity'] == 0, 'Claim failed to clear positions or quantities')
require(p['has_claimed'] and p['claimable'] == 0, 'Claim-consumption mismatch')
require(p['claimant_acon_balance'] - payout['before']['claimant_acon_balance'] == paid, 'Payout recipient delta mismatch')
require(w['creator_acon_balance'] - surplus['before']['creator_acon_balance'] == withdrawn, 'Surplus recipient delta mismatch')
require(all(w[k] == 0 for k in ['contract_acon_balance','remaining_liability','withdrawable_surplus','total_collateral','total_challenge_bonds','creator_yes_position','creator_no_position','creator_claimable']), 'Final recorded balances are not zero')
require(w['market']['collateralBalance'] == w['market']['yesQuantity'] == w['market']['noQuantity'] == 0, 'Final market accounting mismatch')
require(w['creator_acon_balance'] == 1000 * 10**18, 'Creator balance mismatch')
duplicate = payout['duplicate_claim_simulation']
repeat = surplus['repeat_withdrawal_simulation']
require(duplicate['method'] == repeat['method'] == 'eth_call', 'Read-only scope mismatch')
require(duplicate['reverted'] and duplicate['error_name'] == 'AlreadyClaimed' and not duplicate['transaction_submitted'], 'Duplicate check mismatch')
require(repeat['reverted'] and repeat['error_name'] == 'NoSurplus' and not repeat['transaction_submitted'], 'Repeat surplus check mismatch')

result = {
    'schema': 'acon.m5-accounting-reconciliation.v1',
    'validation': 'pass',
    'scope': 'Offline arithmetic and consistency validation of saved public Sepolia receipts and observations; no new RPC verification or transactions',
    'recorded_observation_date_et': '2026-11-17',
    'chain_id': 11155111, 'market_id': 0,
    'contract_address': settlement['contract_address'],
    'amounts_acon': {'collateral_before_settlement': amount(collateral), 'bond_refunded': amount(refund), 'void_liability': amount(liability), 'payout': amount(paid), 'creator_surplus': amount(withdrawn), 'creator_final_balance': amount(w['creator_acon_balance'])},
    'stages': [
        {'stage': 'Before VOID settlement', 'collateral': amount(collateral), 'bond_escrow': amount(refund), 'remaining_liability': amount(liability), 'contract_token_balance': amount(collateral + refund), 'liability_note': 'Computed prospective VOID reserve; market was not yet terminal'},
        {'stage': 'After VOID settlement', 'collateral': amount(collateral), 'bond_escrow': '0', 'remaining_liability': amount(liability), 'contract_token_balance': amount(collateral)},
        {'stage': 'After payout', 'collateral': amount(withdrawn), 'bond_escrow': '0', 'remaining_liability': '0', 'contract_token_balance': amount(withdrawn)},
        {'stage': 'After creator surplus withdrawal', 'collateral': '0', 'bond_escrow': '0', 'remaining_liability': '0', 'contract_token_balance': '0'},
    ],
    'transactions': [{'operation': label, 'hash': e['transaction_hash'], 'url': e['transaction_url'], 'block': e['block_number']} for label, e in [('VOID settlement and bond refund', settlement), ('VOID payout', payout), ('Creator surplus withdrawal', surplus)]],
    'read_only_rejections': {'duplicate_claim': duplicate, 'repeat_surplus': repeat},
    'source_files': [str((SOURCE / name).relative_to(ROOT)) for name in FILES],
    'public_cross_layer_status': 'Separate November 18 verification passed shared Supabase and local API/UI; hosted API/UI acceptance pending. This offline script does not verify those environments.',
    'cross_layer_evidence': 'supabase-local-api-verification.json',
    'issue_56_status': 'incomplete; real callback, committee, votes and disputed settlement remain unverified',
}
(DESTINATION / 'accounting-reconciliation.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS: saved bond, VOID liability, payout, surplus, wallet deltas, zero final balances, and read-only rejection evidence reconcile exactly')
