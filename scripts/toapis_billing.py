# Copyright (c) 2026 ToAPIs contributors. SPDX-License-Identifier: MIT
"""Key-scoped price matching and confirmed billing, Python standard library only.

Network is injected. Callers retain their existing authenticated transport and
durable submission guard. This module never submits a generation request.
"""
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from urllib.parse import urlencode, quote
import time


def amount(value):
    if value is None or isinstance(value, bool):
        raise ValueError('Missing or invalid monetary amount')
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('Invalid monetary amount') from None
    if not number.is_finite() or number < 0:
        raise ValueError('Invalid monetary amount')
    return number


def current_price(get_json, model, kind, conditions, group=None):
    """Match every catalog condition explicitly; never substitute a public price.

    Multiple automatic route groups are retained. `maximum_unit_price` is a
    conservative rate, NOT a locked quote or final request charge.
    """
    catalog = get_json('pricing?' + urlencode({'model': model, 'type': kind}))
    if catalog.get('currency') != 'USD':
        raise ValueError('Unexpected or missing pricing currency')
    if catalog.get('has_more'):
        raise ValueError('Exact-model catalog unexpectedly paginated')
    def equal(a, b, field):
        if isinstance(a, bool) or isinstance(b, bool):
            return type(a) is type(b) and a == b
        a,b=str(a).casefold(),str(b).casefold()
        if field == 'duration':
            a,b=a.removesuffix('s'),b.removesuffix('s')
        return a == b
    matches = []
    for item in catalog.get('data', []):
        if item.get('id') != model or item.get('type') != kind:
            continue
        for price in item.get('prices', []):
            if group is not None and price.get('group') != group:
                continue
            if all(k in conditions and equal(v, conditions[k], k)
                   for k, v in price.get('conditions', {}).items()):
                amount(price.get('unit_price'))
                matches.append(price)
    if not matches:
        raise ValueError('No exact usable Key-scoped price; do not submit')
    units = {(p.get('unit'), p.get('price_basis'), p.get('charge_type')) for p in matches}
    if len(units) != 1:
        raise ValueError('Ambiguous billing units; do not submit')
    unit, basis, charge_type = next(iter(units))
    return {'model': model, 'type': kind, 'conditions': conditions,
            'currency': 'USD', 'unit': unit, 'price_basis': basis,
            'charge_type': charge_type,
            'maximum_unit_price': str(max(amount(p['unit_price']) for p in matches)),
            'prices': matches, 'queried_at': datetime.now(timezone.utc).isoformat(),
            'is_final_charge': False}


def confirmed_billing(response):
    """Supports task/sync responses and a webhook's data.billing object."""
    billing = response.get('billing')
    if billing is None and isinstance(response.get('data'), dict):
        billing = response['data'].get('billing')
    if not isinstance(billing, dict):
        return {'status': 'unavailable', 'cost_usd': None, 'credits': None}
    status = billing.get('status')
    if status not in ('settled', 'refunded'):
        return {'status': status or 'unavailable', 'cost_usd': None, 'credits': None}
    if status == 'refunded':
        for key in ('credits', 'cost_usd'):
            if key in billing and amount(billing[key]) != 0:
                raise ValueError('Refunded billing must have zero net cost')
        return {'status': 'refunded', 'cost_usd': '0', 'credits': '0'}
    # Both fields are documented as confirmed values; never invent a missing one.
    if billing.get('cost_usd') is None or billing.get('credits') is None:
        return {'status': 'incomplete', 'cost_usd': None, 'credits': None}
    usd, credits = amount(billing['cost_usd']), amount(billing['credits'])
    if abs(usd - credits * Decimal('0.005')) > Decimal('0.000001'):
        raise ValueError('Confirmed credits/USD disagree')
    return {'status': 'settled', 'cost_usd': str(usd), 'credits': str(credits)}


def observe(receipt, response):
    """Retain previous confirmed cost across later missing/pending observations."""
    if receipt.get('task_id') and response.get('id') and receipt['task_id'] != response['id']:
        raise ValueError('Task identity mismatch')
    model = receipt.get('model') or receipt.get('request', {}).get('model')
    if model and response.get('model') and model != response['model']:
        raise ValueError('Returned model mismatch')
    new = confirmed_billing(response)
    old = receipt.get('confirmed_billing', {})
    if old.get('status') in ('settled', 'refunded'):
        if new['status'] in ('settled', 'refunded') and new != old:
            raise ValueError('Billing changed after confirmation; reconcile privately')
    else:
        receipt['confirmed_billing'] = new
    receipt['last_response'] = response
    receipt.setdefault('observations', []).append({
        'at': datetime.now(timezone.utc).isoformat(),
        'status': response.get('status'), 'billing': response.get('billing')})
    if response.get('billing') is not None:
        # Preserve already final billing when the next response is only pending.
        if not (old.get('status') in ('settled', 'refunded') and new['status'] not in ('settled', 'refunded')):
            receipt['billing'] = response['billing']
    if response.get('usage') is not None:
        receipt['usage'] = response['usage']
    return receipt['confirmed_billing']


def refresh_settlement(get_json, receipt, kind, save=lambda: None,
                       timeout=60, interval=5, sleep=time.sleep, clock=time.monotonic):
    """Bounded GET-only refresh of an existing task. Safe to repeat later."""
    if kind not in ('image', 'video') or not receipt.get('task_id'):
        raise ValueError('An existing image/video task is required')
    deadline = clock() + timeout
    while receipt.get('confirmed_billing', {}).get('status') not in ('settled', 'refunded'):
        if clock() >= deadline:
            break
        path = ('images' if kind == 'image' else 'videos') + '/generations/' + quote(receipt['task_id'], safe='')
        response = get_json(path)
        observe(receipt, response); save()
        if receipt['confirmed_billing']['status'] in ('settled', 'refunded'):
            break
        sleep(min(interval, max(0, deadline - clock())))
    return receipt.get('confirmed_billing', {'status': 'unavailable', 'cost_usd': None, 'credits': None})


def usage_priced_image_cost(receipt, saved_price):
    """Calculate from a saved matched rate and confirmed request units.

    This is a computed cost, never a final billing receipt. Fixed image requests
    are supported here; token tiers, extras and ambiguous routes are not guessed.
    """
    if receipt.get('last_response', {}).get('status') != 'completed':
        return None
    if (not saved_price or saved_price.get('currency') != 'USD' or
            saved_price.get('type') != 'image' or
            saved_price.get('model') != receipt.get('model') or
            saved_price.get('charge_type') != 'per_request' or
            saved_price.get('unit') != 'request' or
            saved_price.get('price_basis') != 'request'):
        return None
    usage = receipt.get('usage', {})
    quantity = usage.get('requests')
    if (usage.get('charge_type') != 'per_request' or
            isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1):
        return None
    prices = saved_price.get('prices', [])
    if not prices:
        return None
    extras = ('input_unit_price', 'input_image_unit_price', 'minimum_charge_usd',
              'image_token_prices', 'pricing_period', 'pricing_peak_windows')
    if any(any(k in price for k in extras) for price in prices):
        return None
    if any((p.get('unit'), p.get('price_basis'), p.get('charge_type')) !=
           ('request', 'request', 'per_request') for p in prices):
        return None
    rates = {amount(p.get('unit_price')) for p in prices}
    if len(rates) != 1:
        return None
    rate = rates.pop()
    return {'calculated_cost_usd': str(rate * quantity),
            'calculated_cost_status': 'calculated_not_settled',
            'calculation_source': 'saved_key_rate_times_task_usage_requests',
            'confirmed_billable_requests': quantity,
            'saved_unit_price_usd': str(rate),
            'saved_rate_queried_at': saved_price.get('queried_at'),
            'calculation_note': 'Rate snapshot is not a price lock; final billing, '
                                'refunds and later adjustments take precedence.'}


def cost_summary(receipt, output_seconds=None, saved_price=None):
    """Allowlist for case publishing; no task IDs, private URLs or account fields."""
    result = {'model': receipt.get('model') or receipt.get('request', {}).get('model'),
              'billing_status': receipt.get('confirmed_billing', {}).get('status', 'unavailable'),
              'actual_cost_usd': receipt.get('confirmed_billing', {}).get('cost_usd'),
              'actual_credits': receipt.get('confirmed_billing', {}).get('credits')}
    if result['actual_cost_usd'] is None and saved_price is not None:
        calculated = usage_priced_image_cost(receipt, saved_price)
        if calculated is not None:
            result.update(calculated)
    if output_seconds is not None:
        seconds = amount(output_seconds)
        if seconds <= 0:
            raise ValueError('Decoded output duration must be positive')
        result['output_seconds'] = str(seconds)
        result['actual_usd_per_second'] = str(amount(result['actual_cost_usd']) / seconds) if result['actual_cost_usd'] is not None else None
    return result
