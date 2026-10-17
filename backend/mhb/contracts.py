from datetime import date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

class ReturnSnapshot(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id: str
    amount_minor: int=Field(gt=0,strict=True)
    booked_date: date
    reporting_date: date
    revision: int=Field(gt=0,strict=True)

class PaymentSnapshot(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id: str
    tenant_id: str
    owner_id: str
    source_id: str
    destination_id: str | None
    beneficiary_id: str | None
    kind: Literal['OUTBOUND','INTERNAL']
    amount_minor: int=Field(gt=0,le=100000000,strict=True)
    currency: Literal['CAD']
    business_date: date
    status: Literal['RECEIVED','VALIDATED','POSTED','SETTLED','PARTIALLY_RETURNED','RETURNED','REVERSED']
    version: int=Field(gt=0,strict=True)
    returned_minor: int=Field(ge=0,strict=True)
    correlation_id: UUID
    scope: str
    created_at: datetime
    returns: list[ReturnSnapshot]
    @model_validator(mode='after')
    def money(self):
        total=sum(r.amount_minor for r in self.returns)
        if len({r.id for r in self.returns})!=len(self.returns) or total!=self.returned_minor or total>self.amount_minor: raise ValueError('RETURN_CONTROL_MISMATCH')
        if self.status=='RETURNED' and total!=self.amount_minor: raise ValueError('RETURNED_REQUIRES_FULL_AMOUNT')
        if self.status=='PARTIALLY_RETURNED' and not 0<total<self.amount_minor: raise ValueError('INVALID_PARTIAL_RETURN')
        if self.created_at.tzinfo is None: raise ValueError('UTC_OFFSET_REQUIRED')
        if any(r.booked_date<self.business_date or r.reporting_date<self.business_date for r in self.returns): raise ValueError('RETURN_BEFORE_PAYMENT')
        return self

class Envelope(BaseModel):
    model_config=ConfigDict(extra='forbid')
    schema_version: Literal[1]
    source_system: Literal['mhb-core']
    event_type: Literal['payment.snapshot']
    reason: str
    event_id: UUID
    aggregate_id: str
    aggregate_version: int=Field(gt=0,strict=True)
    tenant_id: str
    event_time: datetime
    correlation_id: UUID
    causation_id: UUID
    currency: Literal['CAD']
    currency_exponent: Literal[2]
    payload: PaymentSnapshot
    @model_validator(mode='after')
    def keys(self):
        if (self.aggregate_id,self.aggregate_version,self.tenant_id)!=(self.payload.id,self.payload.version,self.payload.tenant_id): raise ValueError('AGGREGATE_IDENTITY_MISMATCH')
        if self.event_time.tzinfo is None: raise ValueError('UTC_OFFSET_REQUIRED')
        return self
