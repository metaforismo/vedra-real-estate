from __future__ import annotations

import math
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PropertyType = Literal['residential','office','commercial','logistics','land','hospitality','unknown']
Condition = Literal['new','good','to_renovate','shell','unknown']
Strategy = Literal['value_add','core_plus','development','conversion']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Criteria(StrictModel):
    online_discovery: bool = False
    location_query: str = Field(default='', max_length=100)
    min_price: float = Field(default=0, ge=0, le=1_000_000_000)
    max_price: float = Field(default=1_500_000, gt=0, le=1_000_000_000)
    min_surface: float = Field(default=0, ge=0, le=1_000_000)
    max_surface: float | None = Field(default=None, gt=0, le=1_000_000)
    property_types: list[PropertyType] = Field(default_factory=list, max_length=7)
    strategies: list[Strategy] = Field(default_factory=list, max_length=4)
    min_discount: float | None = Field(default=None, ge=0, le=100)
    include_auctions: bool = True
    max_listings: int = Field(default=30, ge=1, le=100)

    @field_validator('location_query')
    @classmethod
    def normalize_location(cls, value):
        return ' '.join(value.split())

    @model_validator(mode="after")
    def surface_range(self):
        if self.min_price > self.max_price:
            raise ValueError("Il budget massimo deve essere maggiore o uguale al minimo.")
        if self.max_surface is not None and self.max_surface < self.min_surface:
            raise ValueError("La superficie massima deve essere maggiore della minima.")
        return self


class AgentInput(StrictModel):
    name: str = Field(min_length=2, max_length=100)
    city: str = Field(min_length=2, max_length=100)
    criteria: Criteria = Field(default_factory=Criteria)
    source_ids: list[str] = Field(min_length=1, max_length=5)
    runtime: Literal['local','hermes','llm'] = 'local'
    interval_minutes: int = Field(default=0, ge=0, le=10080)
    active: bool = True

    @field_validator("interval_minutes")
    @classmethod
    def interval(cls, v):
        if v and v < 15:
            raise ValueError("Intervallo minimo 15 minuti; 0 = manuale.")
        return v


class SourceConfig(StrictModel):
    retain_raw_html: bool = True
    search_url: str = Field(default='', max_length=2000)
    listing_selector: str = Field(default='a[href]', max_length=300)
    listing_url_pattern: str = Field(default='', max_length=200)
    next_selector: str = Field(default='', max_length=300)
    fields: dict[str, str] = Field(default_factory=dict)
    max_pages: int = Field(default=2, ge=1, le=5)
    render_js: bool = False
    probe_city: str = Field(default='', max_length=120)
    discovery_mode: Literal['links', 'sitemap'] = 'links'
    detail_refresh_hours: int = Field(default=24, ge=1, le=720)

    @field_validator('listing_selector','next_selector')
    @classmethod
    def selector(cls, v):
        if v:
            import soupsieve
            try:
                soupsieve.compile(v)
            except Exception as exc:
                raise ValueError("Selettore CSS non valido") from exc
        return v

    @field_validator('fields')
    @classmethod
    def field_selectors(cls, v):
        import soupsieve
        allowed = {'title','price','surface','description','city','zone','address','rooms','bathrooms','property_type','condition','area_basis','transaction_type','currency'}
        if set(v) - allowed or len(v) > 16:
            raise ValueError("Campi non supportati")
        for value in v.values():
            if len(value)>300:
                raise ValueError("Selettore troppo lungo")
            soupsieve.compile(value)
        return v


class SourceInput(StrictModel):
    name: str = Field(min_length=2, max_length=100)
    domain: str = Field(min_length=3, max_length=250)
    config: SourceConfig
    permission_note: str = Field(min_length=10, max_length=2000)
    permission_confirmed: bool

    @field_validator('domain')
    @classmethod
    def domain_only(cls, value):
        value=value.lower().strip().strip('.')
        if any(c in value for c in '/:@*') or ' ' in value:
            raise ValueError("Inserisci solo il dominio, senza protocollo o percorso.")
        return value

    @model_validator(mode='after')
    def approval(self):
        if not self.permission_confirmed:
            raise ValueError("Conferma la disponibilità dei diritti di accesso e riuso.")
        parsed = urlsplit(self.config.search_url.replace('{city}','milano'))
        if parsed.scheme not in ('http','https') or parsed.hostname != self.domain:
            raise ValueError("La ricerca deve usare esattamente il dominio della fonte.")
        return self


class Listing(StrictModel):
    listing_key: str = Field(min_length=1, max_length=500)
    url: str = Field(max_length=2000)
    title: str = Field(min_length=1, max_length=500)
    city: str = Field(default='', max_length=100)
    zone: str = Field(default='', max_length=100)
    address: str | None = Field(default=None, max_length=500)
    property_type: PropertyType = 'unknown'
    condition: Condition = 'unknown'
    price: float | None = Field(default=None, gt=0, le=1_000_000_000)
    surface: float | None = Field(default=None, ge=0.1, le=10_000_000)
    rooms: float | None = Field(default=None, ge=0, le=10000)
    bathrooms: float | None = Field(default=None, ge=0, le=10000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    area_basis: Literal['commercial','net','gross','unknown'] = 'unknown'
    currency: str = Field(default='XXX', pattern=r'^[A-Z]{3}$')
    transaction_type: Literal['sale','rent','unknown'] = 'unknown'
    description: str = Field(default='', max_length=30000)
    is_auction: bool = False
    images: list[str] = Field(default_factory=list, max_length=30)
    evidence: dict = Field(default_factory=dict)
    is_demo: bool = False

    @field_validator('url')
    @classmethod
    def supported_url(cls, v):
        if urlsplit(v).scheme not in ('http','https','import'):
            raise ValueError("Protocollo non supportato")
        return v

    @field_validator('images')
    @classmethod
    def images_urls(cls, value):
        return [u for u in value if len(u)<2000 and urlsplit(u).scheme in ('http','https')][:30]


class BenchmarkInput(StrictModel):
    city: str = Field(min_length=1,max_length=100)
    zone: str = Field(min_length=1,max_length=100)
    property_type: PropertyType
    condition: Condition
    area_basis: Literal['commercial','net','gross']
    currency: str = Field(default='EUR',pattern=r'^[A-Z]{3}$')
    transaction_type: Literal['sale','rent'] = 'sale'
    min_sqm: float = Field(gt=0,le=1_000_000)
    max_sqm: float = Field(gt=0,le=1_000_000)
    period: str = Field(pattern=r'^\d{4}-S[12]$')
    source_label: str = Field(min_length=3,max_length=200)
    source_url: str = Field(min_length=3,max_length=2000)
    is_demo: bool = False

    @model_validator(mode='after')
    def valid_range(self):
        if self.max_sqm < self.min_sqm:
            raise ValueError('Range benchmark invertito')
        if self.condition == 'unknown' or self.property_type == 'unknown':
            raise ValueError('Tipologia e stato benchmark devono essere noti')
        return self


class StrategyEvidence(StrictModel):
    strategy: Strategy
    evidence: str = Field(min_length=5,max_length=700)


class SemanticAnalysis(StrictModel):
    summary: str = Field(max_length=1500)
    strategies: list[StrategyEvidence] = Field(default_factory=list,max_length=4)
    caveats: list[str] = Field(default_factory=list,max_length=8)


class LoginInput(StrictModel):
    email: str = Field(max_length=200)
    password: str = Field(min_length=1,max_length=256)


class UserInput(StrictModel):
    name: str = Field(min_length=2,max_length=100)
    email: str = Field(min_length=5,max_length=200)
    password: str = Field(min_length=12,max_length=256)
    role: Literal['admin','analyst','viewer'] = 'viewer'


class ReviewInput(StrictModel):
    starred: bool | None = None
    review_status: Literal['new','reviewing','shortlisted','due_diligence','negotiation','acquired','discarded'] | None = None


class NoteInput(StrictModel):
    body: str = Field(min_length=1,max_length=4000)


class ImportInput(StrictModel):
    kind: Literal['csv','html','benchmarks']
    content: str = Field(min_length=1,max_length=4_000_000)
    source_url: str = Field(default='',max_length=2000)
    is_demo: bool = False
    permission_confirmed: bool = False
