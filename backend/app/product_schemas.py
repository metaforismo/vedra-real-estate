from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from .schemas import StrictModel

Stage = Literal['new', 'reviewing', 'shortlisted', 'due_diligence', 'negotiation', 'acquired', 'discarded']


class Checklist(StrictModel):
    source_checked: bool = False
    area_checked: bool = False
    occupancy_checked: bool = False
    planning_checked: bool = False
    costs_checked: bool = False


class DealWorkInput(StrictModel):
    owner_id: str | None = Field(default=None, max_length=100)
    due_date: date | None = None
    checklist: Checklist = Field(default_factory=Checklist)
    version: int = Field(ge=0)
    stage: Stage | None = None


class ScenarioInputs(StrictModel):
    purchase: float = Field(gt=0, le=1e9)
    sale: float = Field(gt=0, le=1e10)
    works: float = Field(default=0, ge=0, le=1e9)
    acquisition_costs: float = Field(default=0, ge=0, le=1e9)
    contingency_pct: float = Field(default=10, ge=0, le=100)
    selling_pct: float = Field(default=3, ge=0, le=99.99)
    holding_monthly: float = Field(default=0, ge=0, le=1e7)
    months: int = Field(default=12, ge=1, le=120)


class ScenarioInput(StrictModel):
    name: str = Field(default='Scenario base', min_length=1, max_length=80)
    inputs: ScenarioInputs


class ViewFilters(StrictModel):
    availability: Literal['open','all','sold','rented','withdrawn','review','unknown','listed'] = 'open'
    q: str = Field(default='', max_length=200)
    city: str = Field(default='', max_length=100)
    type: str = Field(default='', max_length=40)
    strategy: str = Field(default='', max_length=40)
    status: str = Field(default='', max_length=40)
    agent_id: str = Field(default='', max_length=100)
    qualified: bool = False
    starred: bool = False
    sort: Literal['score','price','latest','quality','newest','due'] = 'score'
    source_id: str = Field(default='', max_length=100)
    currency: str = Field(default='', max_length=3)
    min_price: float | None = Field(default=None, ge=0, le=1e12)
    max_price: float | None = Field(default=None, ge=0, le=1e12)
    min_surface: float | None = Field(default=None, ge=0, le=1e9)
    max_surface: float | None = Field(default=None, ge=0, le=1e9)
    focus: Literal['all','new','stale','unbenchmarked','overdue','unassigned'] = 'all'

    @model_validator(mode='after')
    def coherent_ranges(self):
        for name in ('price','surface'):
            low, high = getattr(self, 'min_' + name), getattr(self, 'max_' + name)
            if low is not None and high is not None and low > high:
                raise ValueError('Il minimo non può superare il massimo.')
        if (self.min_price is not None or self.max_price is not None) and not self.currency:
            raise ValueError('Seleziona la valuta per filtrare un intervallo di prezzo.')
        if self.currency and (len(self.currency) != 3 or not self.currency.isascii() or not self.currency.isalpha()):
            raise ValueError('Valuta non valida: usa un codice di tre lettere.')
        self.currency = self.currency.upper()
        return self


class SavedViewInput(StrictModel):
    name: str = Field(min_length=1, max_length=60)
    filters: ViewFilters


class DuplicateInput(StrictModel):
    a: str = Field(min_length=1, max_length=100)
    b: str = Field(min_length=1, max_length=100)
    decision: Literal['same_asset', 'distinct']


class PasswordInput(StrictModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)
