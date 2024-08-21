import typing
from pydantic import BaseModel

#Custom Types
cities = open('Resources/USCities.txt', 'r').read().strip().split('\t')
states = open('Resources/USStateCodes.txt', 'r').read().strip().split('\t')

class RealEstateExtraction(BaseModel):
    propertyName: str = None
    owners: str = None
    parcel: str = None
    streetAddress: str = None
    city: str = None
    state: str = None
    postalCode: int = None
    county: str = None
    propertyType: str = None
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