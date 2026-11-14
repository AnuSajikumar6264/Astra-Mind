from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field
Domain=Literal["cardiovascular","musculoskeletal","immune","behavioral","radiation"]
class ObservationIn(BaseModel):
    astronaut_id:str="crew-01"
    domain:Domain
    metric:str=Field(min_length=1,max_length=80)
    value:float
    unit:str=Field(min_length=1,max_length=24)
    observed_at:datetime|None=None
    source:str="manual-entry"
    provenance:Literal["SYNTHETIC","SPACEFLIGHT_REAL","GROUND_HUMAN","SPACE_ANALOG"]="SYNTHETIC"
    quality:float=Field(default=1.0,ge=0,le=1)
class SimulationIn(BaseModel):
    scenario:Literal["nominal","sleep_disruption","cardiovascular_strain","exercise_decline","radiation_increase"]="nominal"
    samples:int=Field(default=1,ge=1,le=24)
class SyncIn(BaseModel):
    event_id:str
    astronaut_id:str="crew-01"
    observations:list[ObservationIn]
