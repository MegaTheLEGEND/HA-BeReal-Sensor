
# BeReal Time – Home Assistant Custom Integration

The **BeReal Time** custom component for [Home Assistant](https://www.home-assistant.io/) creates a sensor that monitors the daily BeReal moment for your region. It fetches data from the BeReal public API and determines whether the current time is:

- Before the moment ("waiting")
- During the 2-minute window ("now")
- After the window ("past")

## Features

- Fetches live data from BeReal's public endpoint
- Shows:
  - `startDate`, `endDate`, and current UTC time
  - BeReal "instance": `waiting`, `now`, or `past`
  - Parsed and raw API data as sensor attributes
- Supports setup via the Home Assistant **UI** (Config Flow)
- Automatically updates every few seconds

---

## Installation

### hacs 

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MegaTheLEGEND&repository=HA-BeReal-Sensor)


### Manual

1. Clone or download this repository
2. Copy the contents to:
```

custom_components/bereal_time/

````

3. Restart Home Assistant
4. Go throught the intgration setup flow for `BeReal Time` on the devices page.

---


## Sensor Output

The integration creates one sensor:

- **`sensor.bereal_time`**
- `state`: One of:
 - `waiting` – Before BeReal moment
 - `now` – Within the 2-minute window
 - `past` – After the window
 - `error` – If API fetch fails

### Attributes

| Attribute           | Description                         |
|---------------------|-------------------------------------|
| `startDate`         | Unix timestamp (ms) of moment start |
| `endDate`           | Unix timestamp (ms) of moment end   |
| `current_time_utc`  | Current UTC timestamp (ms)          |
| `localDateTime`     | Local timestamp of BeReal moment    |
| `api_parsed`        | Parsed JSON data                    |
| `api_raw`           | Raw JSON API response               |

---

## Development Notes

* The integration uses `async_setup_entry()` and `config_entry_only_config_schema`
* It polls the BeReal endpoint every 5 seconds
* The API used: `https://mobile-l7.bereal.com/api/bereal/moments/last/<region>`

---

## Credits

This is an unofficial integration and is not affiliated with BeReal.

---
