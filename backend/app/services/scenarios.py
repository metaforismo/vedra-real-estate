"""Explicit, unlevered scenario arithmetic; no market-price prediction."""
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR

from ..product_schemas import ScenarioInputs


def calculate(inputs: ScenarioInputs) -> dict:
    values = inputs.model_dump()
    d = {key: Decimal(str(value)) for key, value in values.items()}
    hundred = Decimal(100)

    def profit(sale_shift=0, works_shift=0, delay=0):
        sale = d['sale'] * (1 + Decimal(str(sale_shift)) / hundred)
        works = d['works'] * (1 + Decimal(str(works_shift)) / hundred)
        invested = (d['purchase'] + d['acquisition_costs']
                    + works * (1 + d['contingency_pct'] / hundred)
                    + d['holding_monthly'] * (d['months']+Decimal(str(delay))))
        result = sale * (1 - d['selling_pct'] / hundred) - invested
        return invested, result

    def money(value):
        return float(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    invested, result = profit()
    stressed_invested,stressed_profit=profit(-d['stress_sale_pct'],d['stress_works_pct'],d['stress_delay_months'])
    def ceiling(investment,net_sale):
        # Fixed acquisition costs stay fixed; the user must update them if price changes.
        return net_sale/(1+d['target_roi_pct']/hundred)-(investment-d['purchase'])
    max_purchase=ceiling(invested,invested+result)
    stress_max=ceiling(stressed_invested,stressed_invested+stressed_profit)
    return {
        'version': 'unlevered-scenario/1.1',
        'inputs':values,
        'target_roi_pct':values['target_roi_pct'],
        'target_met':result/invested*hundred>=d['target_roi_pct'],
        'max_purchase':float(max_purchase.quantize(Decimal('0.01'),rounding=ROUND_FLOOR)),
        'price_reduction_needed':money(max(Decimal(0),d['purchase']-max_purchase)),
        'stress':{'invested':money(stressed_invested),'profit':money(stressed_profit),
                  'roi_pct':money(stressed_profit/stressed_invested*hundred),
                  'max_purchase':float(stress_max.quantize(Decimal('0.01'),rounding=ROUND_FLOOR)),
                  'breakeven_sale':money(stressed_invested/(1-d['selling_pct']/hundred)),
                  'target_met':stressed_profit/stressed_invested*hundred>=d['target_roi_pct']},
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
