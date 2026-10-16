import json
from pathlib import Path
import pytest
from src.weather_client import forecast_to_records,select_location,get_forecast
S=json.loads((Path(__file__).parents[1]/"data"/"sample_forecast.json").read_text())
def test_parser_rows_and_units():
    r=forecast_to_records(S); assert len(r)==2 and r[0]["Maximum temperature (°C)"]==15.2
def test_weather_code_mapping(): assert forecast_to_records(S)[1]["Weather description"]=="Slight rain"
def test_missing_daily_data(): assert forecast_to_records({})==[]
def test_empty_location_raises():
    with pytest.raises(ValueError): select_location([])
def test_choice_range():
    with pytest.raises(IndexError): select_location([{"name":"x"}],2)
def test_invalid_latitude_before_network():
    with pytest.raises(ValueError): get_forecast(95,0)
