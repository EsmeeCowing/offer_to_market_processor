import typing
from pydantic import BaseModel

#Lists for Custom Types. These contain all of the options for the value of a custom type, including NA.
cities = open("resources/uscities.txt", "r").read().strip().split("    ")
states = open("resources/usstatecodes.txt", "r").read().strip().split("    ")
counties = open("resources/uscounties.txt", "r").read().strip().split("    ")
property_types = open("resources/propertytypes.txt", "r").read().strip().split("    ")
parcelNumberCharacters = open("resources/parcelnumbercharacters.txt", "r").read().strip().split("    ")

#This is where what the blank value for all of the 

class PostalCode(BaseModel):
    tenthousands_place_digit: typing.Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    thousands_place_digit: typing.Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    hundreds_place_digit: typing.Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    tens_place_digit: typing.Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    ones_place_digit: typing.Literal[ "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

class ParcelNumberCharacter(BaseModel):
    value: eval(f"typing.Literal[{", ".join(repr(e) for e in parcelNumberCharacters)}]") 

class RealEstateExtraction(BaseModel):
    property_name: str | None
    owners: str | None
    parcel: list[ParcelNumberCharacter] | None
    street_address: str | None
    city: str | None #the cities file is too big, but I"m leaving this code here in case things change #eval(f"typing.Literal[{", ".join(repr(e) for e in cities)}]")
    state: eval(f"typing.Literal[{", ".join(repr(e) for e in states)}]") | None
    postal_code: PostalCode | None
    county: str | None #the counties file is also too big, but I"m leaving this code here in case things change #eval(f"typing.Literal[{", ".join(repr(e) for e in counties)}]")
    property_type: eval(f"typing.Literal[{", ".join(repr(e) for e in property_types)}]") | None
    zoning: str | None
    parking_spaces: int | None
    rentable_square_feet: float | None
    lot_size: float | None
    tenants: str | None
    total_units: int | None
    years_built: int | None
    sales_price: float | None
    gross_income: float | None
    total_expenses: float | None
    NOI: float | None
    gross_cap_rate: float | None
    net_cap_rate: float | None
    price_per_rentable_square_foot: float | None
    price_per_unit: float | None
    seller: str | None
    sellers_broker: str | None
    property_description: str | None