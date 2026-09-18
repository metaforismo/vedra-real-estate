"""Typed, bounded contracts for full-archive queries and collaborative triage."""
from typing import Literal

from pydantic import Field, model_validator

from .product_schemas import ViewFilters, Stage
from .schemas import StrictModel


class CatalogQuery(ViewFilters):
    page: int = Field(default=1, ge=1, le=1_000_000)
    page_size: int = Field(default=50, ge=10, le=100)


class CatalogSelection(StrictModel):
    ids: list[str] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def unique(self):
        if len(set(self.ids)) != len(self.ids) or any(not value or len(value) > 100 for value in self.ids):
            raise ValueError('Seleziona da 1 a 100 annunci distinti.')
        return self


class RevisionRef(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=0)


class BulkReview(StrictModel):
    items: list[RevisionRef] = Field(min_length=1, max_length=100)
    stage: Stage
    note: str = Field(default='', max_length=2000)

    @model_validator(mode='after')
    def validate_items(self):
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError('La selezione contiene duplicati.')
        self.note = self.note.strip()
        if self.stage == 'discarded' and len(self.note) < 5:
            raise ValueError('Per scartare un deal, indica una motivazione di almeno 5 caratteri.')
        return self


class CatalogExport(StrictModel):
    format: Literal['csv', 'xlsx']
    filters: ViewFilters
