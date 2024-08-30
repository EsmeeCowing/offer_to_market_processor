import typing
from pydantic import BaseModel

#Lists for Custom Types
cities = open("Resources/uscities.txt", "r").read().strip().split("    ")
states = open("Resources/usstatecodes.txt", "r").read().strip().split("    ")
counties = open("Resources/uscounties.txt", "r").read().strip().split("    ")
propertyTypes = open("Resources/propertytypes.txt", "r").read().strip().split("    ")

class PostalCode(BaseModel):
    onesPlaceDigit: typing.Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    tensPlaceDigit: typing.Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    hundredsPlaceDigit: typing.Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    thousandsPlaceDigit: typing.Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    tenthousandsPlaceDigit: typing.Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

class RealEstateExtraction(BaseModel):
    propertyName: str = None
    owners: str = None
    parcel: str = None
    streetAddress: str = None
    city: str = None #the cities file is too big, but I"m leaving this code here in case things change #eval(f"typing.Literal[{", ".join(repr(e) for e in cities)}]") = None
    state: eval(f"typing.Literal[{", ".join(repr(e) for e in states)}]") = None
    postalCode: PostalCode 
    county: str = None #the counties file is also too big, but I"m leaving this code here in case things change #eval(f"typing.Literal[{", ".join(repr(e) for e in counties)}]") = None
    propertyType: eval(f"typing.Literal[{", ".join(repr(e) for e in propertyTypes)}]") = None
    zoning: str = None
    parkingSpaces: int = None
    rentableSquareFeet: float = None
    lotSize: float = None
    tenants: str = None
    totalUnits: int = None
    yearBuilt: int = None
    salesPrice: float = None
    grossIncome: float = None
    totalExpenses: float = None
    NOI: float = None
    grossCapRate: float = None
    NetCapeRate: float = None
    pricePerRentableSquareFoot: float = None
    pricePerUnit: float = None
    seller: str = None
    sellersBroker: str = None
    propertyDescription: str = None