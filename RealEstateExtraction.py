import typing
from pydantic import BaseModel

#Lists for Custom Types. These contain all of the options for the value of a custom type, including NA.
cities = open("resources/uscities.txt", "r").read().strip().split("    ")
states = open("resources/usstatecodes.txt", "r").read().strip().split("    ")
counties = open("resources/uscounties.txt", "r").read().strip().split("    ")
property_types = open("resources/propertytypes.txt", "r").read().strip().split("    ")
parcelNumberCharacters = open("resources/parcelnumbercharacters.txt", "r").read().strip().split("    ")
 
class PostalCode(BaseModel):
    tenthousands_place_digit: typing.Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    thousands_place_digit: typing.Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    hundreds_place_digit: typing.Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    tens_place_digit: typing.Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    ones_place_digit: typing.Literal[ "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

class ParcelNumberCharacter(BaseModel):
    value: eval(f"typing.Literal[{", ".join(repr(e) for e in parcelNumberCharacters)}]")


class RealEstateExtraction(BaseModel):
    property_name: str | typing.Literal[""]
    owners: str | typing.Literal[""]
    parcel: list[ParcelNumberCharacter] | typing.Literal[""]
    street_address: str | typing.Literal[""]
    city: str | typing.Literal[""] #the cities file is too big, but I"m leaving this code here in case things change #eval(f"typing.Literal[{", ".join(repr(e) for e in cities)}]")
    state: eval(f"typing.Literal[{", ".join(repr(e) for e in states)}]") | typing.Literal[""]
    postal_code: PostalCode | typing.Literal[""]
    county: str | typing.Literal[""] #the counties file is also too big, but I"m leaving this code here in case things change #eval(f"typing.Literal[{", ".join(repr(e) for e in counties)}]")
    property_type: eval(f"typing.Literal[{", ".join(repr(e) for e in property_types)}]") | typing.Literal[""]
    zoning: str | typing.Literal[""]
    parking_spaces: int | typing.Literal[""]
    rentable_square_feet: float | typing.Literal[""]
    lot_size: float | typing.Literal[""]
    tenants: str | typing.Literal[""]
    total_units: int | typing.Literal[""]
    year_built: int | typing.Literal[""]
    sales_price: float | typing.Literal[""]
    gross_income: float | typing.Literal[""]
    total_expenses: float | typing.Literal[""]
    NOI: float | typing.Literal[""]
    gross_cap_rate: float | typing.Literal[""]
    net_cap_rate: float | typing.Literal[""]
    price_per_rentable_square_foot: float | typing.Literal[""]
    price_per_unit: float | typing.Literal[""]
    seller: str | typing.Literal[""]
    sellers_broker: str | typing.Literal[""]
    property_description: str | typing.Literal[""]