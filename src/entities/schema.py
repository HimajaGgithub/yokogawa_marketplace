import datetime
from enum import Enum
from typing import Optional, Dict, Any, Literal

from pydantic import BaseModel, Field, model_validator, field_serializer


class Mode(str, Enum):
    manual = "manual"
    dual = "dual"
    auto = "auto"


class ModeRequest(BaseModel):
    listing_id: Optional[str] = Field(default_factory=str)
    mode: Mode


class BizType(str, Enum):
    EV_Fleet = "ev_fleet"
    Refurbisher = "refurbisher"
    ESS_Operator = "ess"
    OEM = "oem"
    Recycler = "recycler"
    Logistics = "logistics"
    Manufacturer = "manufacturer"


class UserType(str, Enum):
    admin = "admin"
    user = "user"
    agent = "agent"


class UserCreate(BaseModel):
    biz_name: str
    email_id: str
    password: str
    biz_type: BizType
    location: str
    role: Literal["user"]
    preferences: Optional[Dict[str, Any]] = None


class UserLogin(BaseModel):
    email_id: str
    password: str


class UserResponse(BaseModel):
    user_id: str
    biz_name: str
    email_id: str
    location: str
    biz_type: BizType


class ListingType(str, Enum):
    SUPPLY = "supply"
    DEMAND = "demand"


class TransactionType(str, Enum):
    AUCTION = "auction"
    NEGOTIATION = "negotiation"


class MaterialCode(str, Enum):
    Lithium = "Lithium"
    Cobalt = "Cobalt"
    Iron = "Iron"
    Phosphate = "Phosphate"
    Graphite = "Graphite"
    Manganese = "Manganese"
    Nickel = "Nickel"
    Titanium = "Titanium"
    LFP = "LFP"
    NMC = "NMC"
    LTO = "LTO"
    LCO = "LCO"
    lfp_waste = "lfp_waste"
    nmc_waste = "nmc_waste"
    lto_waste = "lto_waste"
    lco_waste = "lco_waste"
    truck = "truck"


class CategoryType(str, Enum):
    TRUCK = "truck"
    NEW_BATTERY = "new battery"
    REFURBISHED_BATTERY = "refurbished battery"
    WASTE_BATTERY = "waste battery"
    RAW_MATERIAL = "raw material"


class StatusType(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    APPROVAL_PENDING = "approval pending"
    COMPLETED = "accepted"
    DELIVERED = "completed"


class UserMessageInput(BaseModel):
    message: str


class FinalListingCreation(BaseModel):
    title: str
    description: str
    listing_type: ListingType
    category: CategoryType
    material_code: MaterialCode
    quantity: float
    quantity_unit: str
    status: StatusType
    location: str
    payload: Dict[str, Any]
    message: Optional[str] = Field(default_factory=str)
    action: Optional[str] = Field(default_factory=str)
    rationale: Optional[str] = Field(default_factory=str)
    analysis: Optional[str] = Field(default_factory=str)
    target_user: Optional[str] = Field(default_factory=str)

    @model_validator(mode='after')
    def validate_mandatory_fields(self):
        """Validate mandatory fields based on listing type and transaction type"""
        payload = self.payload or {}

        float_fields = ['recycled_materials_percent', 'SoH', 'purity']
        for field in float_fields:
            if field in payload and payload[field] is not None:
                try:
                    payload[field] = float(payload[field])
                except (ValueError, TypeError):
                    raise ValueError(f"Field '{field}' must be convertible to float")

        if self.listing_type == ListingType.SUPPLY:
            transaction_type = payload.get('transaction_type')

            if transaction_type == TransactionType.AUCTION.value:
                mandatory_fields = ['end_date', 'reserve_price']
                missing_fields = []

                for field in mandatory_fields:
                    if field not in payload or payload[field] is None:
                        missing_fields.append(field)

                if missing_fields:
                    raise ValueError(f"Missing mandatory fields for auction: {missing_fields}")

            elif transaction_type == TransactionType.NEGOTIATION.value:
                mandatory_fields = ['listing_price', 'target_price']
                missing_fields = []

                for field in mandatory_fields:
                    if field not in payload or payload[field] is None:
                        missing_fields.append(field)

                if missing_fields:
                    raise ValueError(f"Missing mandatory fields for negotiation: {missing_fields}")

        return self


class ListingIdRequest(BaseModel):
    listing_id: str
    message: Optional[str] = Field(default_factory=str)
    action: Optional[str] = Field(default_factory=str)
    rationale: Optional[str] = Field(default_factory=str)


class PendingApproval(BaseModel):
    listing_id: str
    description: str
    winning_user: str
    price: float
    message: Optional[str] = Field(default_factory=str)
    action: Optional[str] = Field(default_factory=str)
    rationale: Optional[str] = Field(default_factory=str)

class Bid(BaseModel):
    listing_id: str
    bidder_name: Optional[str] = Field(default=str)
    time: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    price: float
    message: Optional[str] = Field(default_factory=str)
    action: Optional[str] = Field(default_factory=str)
    rationale: Optional[str] = Field(default_factory=str)
    analysis: Optional[str] = Field(default_factory=str)

    @field_serializer("time")
    def serialize_time(self, dt: datetime.datetime, _info):
        return dt.isoformat()


class NegotiationType(str, Enum):
    OFFER = "offer"
    COUNTER_OFFER = "counter_offer"
    ACCEPT = "accept"
    REJECT = "reject"
    APPROVAL_PENDING = "approval_pending"


class NegotiateMessage(BaseModel):
    listing_id: str
    price: float
    user_name: Optional[str] = Field(default_factory=str)
    replying_to_user: Optional[str] = Field(default_factory=str)
    negotiation_type: NegotiationType
    message: Optional[str] = Field(default_factory=str)
    action: Optional[str] = Field(default_factory=str)
    rationale: Optional[str] = Field(default_factory=str)
    analysis: Optional[str] = Field(default_factory=str)
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))

    @field_serializer("timestamp")
    def serialize_time(self, dt: datetime.datetime, _info):
        return dt.isoformat()


class ScenarioIdRequest(BaseModel):
    scenario_id: str


class RunOrScenarioRequest(BaseModel):
    run_id: Optional[str] = None
    scenario_id: Optional[str] = None

    @model_validator(mode="after")
    def check_one_required(cls, values):
        run_id, scenario_id = values.get("run_id"), values.get("scenario_id")
        if not run_id and not scenario_id:
            raise ValueError("Either run_id or scenario_id must be provided")
        return values
