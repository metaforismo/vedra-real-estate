"""Explicit, unlevered scenario arithmetic; no market-price prediction."""
from decimal import Decimal, ROUND_HALF_UP

from ..product_schemas import ScenarioInputs


def calculate(inputs: ScenarioInputs) -> dict:
    values = inputs.model_dump()
    d = {key: Decimal(str(value)) for key, value in values.items()}
    hundred = Decimal(100)

    def profit(sale_shift=0, works_shift=0):
        sale = d['sale'] * (1 + Decimal(sale_shift) / hundred)
        works = d['works'] * (1 + Decimal(works_shift) / hundred)
        invested = (d['purchase'] + d['acquisition_costs']
                    + works * (1 + d['contingency_pct'] / hundred)
                    + d['holding_monthly'] * d['months'])
        result = sale * (1 - d['selling_pct'] / hundred) - invested
        return invested, result

    def money(value):
        return float(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    invested, result = profit()
    return {
        'version': 'unlevered-scenario/1.0',
        'invested': money(invested), 'profit': money(result),
        'roi_pct': money(result / invested * hundred),
        'breakeven_sale': money(invested / (1 - d['selling_pct'] / hundred)),
        'selling_costs': money(d['sale'] * d['selling_pct'] / hundred),
        'contingency': money(d['works'] * d['contingency_pct'] / hundred),
        'sensitivity': [
            {'sale_change_pct': s, 'works_change_pct': w, 'profit': money(profit(s,w)[1])}
            for s in (-10,0,10) for w in (0,20)
        ],
        'notice': 'Ipotesi utente. Nessun debito, flusso intermedio o imposta non inserita nei costi. ROI non annualizzato.',
    }
