"""Constants shared by API schemas and prediction helpers."""

REQUEST_COLUMNS = [
    "bedrooms",
    "bathrooms",
    "sqft_living",
    "sqft_lot",
    "floors",
    "sqft_above",
    "sqft_basement",
]
UNKNOWN_ZIP = "98009"  # real Bellevue zipcode, deliberately absent from DEMOGRAPHICS_PATH
