"""Weather API helpers with validation and retry handling."""
import json, os, time, urllib.parse, urllib.request
import requests

class WeatherAPIError(RuntimeError):
    """Raised after a weather API request fails."""

def request_json(url, params=None, timeout=8, retries=3, user_agent=None):
    """Request JSON with timeout, status checking, capped retries and backoff."""
    headers={"User-Agent": user_agent or os.getenv("WEATHER_USER_AGENT","Advent2026Notebook/1.0 (set your real email)")}
    last=None
    for attempt in range(retries):
        try:
            r=requests.get(url,params=params,headers=headers,timeout=timeout)
            r.raise_for_status()
            try: payload=r.json()
            except ValueError as e: raise WeatherAPIError("Response was not valid JSON") from e
            return payload, {"status_code":r.status_code,"content_type":r.headers.get("Content-Type",""),
                             "elapsed_seconds":r.elapsed.total_seconds(),"url":r.url}
        except (requests.RequestException,WeatherAPIError) as e:
            last=e
            if isinstance(e,requests.HTTPError) and e.response is not None and 400<=e.response.status_code<500 and e.response.status_code!=429: break
            if attempt+1<retries: time.sleep(min(.25*(2**attempt),1.0))
    raise WeatherAPIError(f"GET failed after {retries} attempt(s): {last}") from last

def geocode_urllib(name,timeout=8):
    """Geocode using urllib.request, urllib.parse.urlencode and json."""
    query=urllib.parse.urlencode({"name":name,"count":10,"language":"en","format":"json"})
    req=urllib.request.Request("https://geocoding-api.open-meteo.com/v1/search?"+query,
      headers={"User-Agent":os.getenv("WEATHER_USER_AGENT","Advent2026Notebook/1.0")})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r: data=json.loads(r.read().decode("utf-8"))
    except Exception as e: raise WeatherAPIError(f"urllib request failed: {e}") from e
    return data.get("results",[]) or []

def geocode(name,timeout=8):
    """Return all geocoding candidates; an empty list means no results."""
    data,_=request_json("https://geocoding-api.open-meteo.com/v1/search",
      {"name":name,"count":10,"language":"en","format":"json"},timeout=timeout)
    return data.get("results",[]) or []

def get_forecast(lat,lon,days=7,timeout=8):
    """Fetch daily temperature, precipitation, wind and WMO weather codes."""
    if not -90<=float(lat)<=90: raise ValueError("latitude must be between -90 and 90")
    if not -180<=float(lon)<=180: raise ValueError("longitude must be between -180 and 180")
    if not 1<=int(days)<=16: raise ValueError("days must be between 1 and 16")
    data,_=request_json("https://api.open-meteo.com/v1/forecast",
      {"latitude":lat,"longitude":lon,"daily":"temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,weather_code",
       "forecast_days":days,"timezone":"auto"},timeout=timeout)
    return data

WEATHER_CODES={0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",45:"Fog",48:"Depositing rime fog",
  51:"Light drizzle",53:"Moderate drizzle",55:"Dense drizzle",56:"Light freezing drizzle",57:"Dense freezing drizzle",
  61:"Slight rain",63:"Moderate rain",65:"Heavy rain",66:"Light freezing rain",67:"Heavy freezing rain",
  71:"Slight snow",73:"Moderate snow",75:"Heavy snow",77:"Snow grains",80:"Slight rain showers",
  81:"Moderate rain showers",82:"Violent rain showers",85:"Slight snow showers",86:"Heavy snow showers",
  95:"Thunderstorm",96:"Thunderstorm with slight hail",99:"Thunderstorm with heavy hail"}

def forecast_to_records(payload):
    """Convert Open-Meteo daily JSON into rows with units and readable conditions."""
    daily=payload.get("daily") or {}; dates=daily.get("time") or []; rows=[]
    fields=[("temperature_2m_max","Maximum temperature (°C)"),("temperature_2m_min","Minimum temperature (°C)"),
            ("precipitation_sum","Precipitation (mm)"),("wind_speed_10m_max","Maximum wind speed (km/h)"),("weather_code","Weather code")]
    for i,day in enumerate(dates):
        row={"Date":day}
        for key,label in fields:
            vals=daily.get(key,[]); row[label]=vals[i] if i<len(vals) else None
        row["Weather description"]=WEATHER_CODES.get(row["Weather code"],"Unknown code")
        rows.append(row)
    return rows

def select_location(candidates,choice=0):
    """Pick a candidate by index and validate empty/out-of-range choices."""
    if not candidates: raise ValueError("No locations found; try a more specific name.")
    if not 0<=choice<len(candidates): raise IndexError("choice outside candidate list")
    return candidates[choice]

def met_norway_forecast(lat,lon,user_agent,timeout=8):
    """Call MET Norway; its policy requires an identifiable contact in User-Agent."""
    if not user_agent or "@" not in user_agent: raise ValueError("Use a real contact email in User-Agent")
    data,_=request_json("https://api.met.no/weatherapi/locationforecast/2.0/compact",
      {"lat":lat,"lon":lon},timeout=timeout,user_agent=user_agent)
    return data
