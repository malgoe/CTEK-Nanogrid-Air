from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from aiohttp import BasicAuth, ClientError
import asyncio
import logging

DOMAIN = "ctek_nanogrid_air"

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10  # Timeout for API calls

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensors for CTEK Nanogrid Air integration."""
    config = entry.data
    host = config["host"]
    port = config["port"]
    username = config["username"]
    password = config["password"]

    session = async_get_clientsession(hass)
    auth = BasicAuth(username, password)

    # Define the sensors to be added
    sensors = [
        # Status endpoint entities
        CTEKSensor(session, host, port, auth, "device_serial", "Device Serial", "/status", "deviceInfo.serial", icon="mdi:numeric"),
        CTEKSensor(session, host, port, auth, "device_firmware", "Device Firmware", "/status", "deviceInfo.firmware", icon="mdi:update"),
        CTEKSensor(session, host, port, auth, "device_mac", "Device MAC", "/status", "deviceInfo.mac", icon="mdi:router"),
        CTEKSensor(session, host, port, auth, "chargebox_state", "Chargebox State", "/status", "chargeboxInfo.state", icon="mdi:power"),
        CTEKSensor(session, host, port, auth, "wifi_ssid", "WiFi SSID", "/status", "wifiInfo.ssid", icon="mdi:wifi"),
        CTEKSensor(session, host, port, auth, "wifi_rssi", "WiFi Signal Strength", "/status", "wifiInfo.rssi", unit_of_measurement="dBm", icon="mdi:signal"),

        # Meter endpoint entities
        CTEKSensor(session, host, port, auth, "active_power_in", "Active Power In", "/meter", "activePowerIn", unit_of_measurement="W", icon="mdi:meter-electric"),
        CTEKSensor(session, host, port, auth, "active_power_out", "Active Power Out", "/meter", "activePowerOut", unit_of_measurement="W", icon="mdi:flash-off"),
        CTEKSensor(session, host, port, auth, "current_phase_1", "Current Phase 1", "/meter", "current.0", unit_of_measurement="A", icon="mdi:current-ac"),
        CTEKSensor(session, host, port, auth, "current_phase_2", "Current Phase 2", "/meter", "current.1", unit_of_measurement="A", icon="mdi:current-ac"),
        CTEKSensor(session, host, port, auth, "current_phase_3", "Current Phase 3", "/meter", "current.2", unit_of_measurement="A", icon="mdi:current-ac"),
        CTEKSensor(session, host, port, auth, "voltage_phase_1", "Voltage Phase 1", "/meter", "voltage.0", unit_of_measurement="V", icon="mdi:flash"),
        CTEKSensor(session, host, port, auth, "voltage_phase_2", "Voltage Phase 2", "/meter", "voltage.1", unit_of_measurement="V", icon="mdi:flash"),
        CTEKSensor(session, host, port, auth, "voltage_phase_3", "Voltage Phase 3", "/meter", "voltage.2", unit_of_measurement="V", icon="mdi:flash"),
        CTEKSensor(session, host, port, auth, "total_energy_import", "Total Energy Import", "/meter", "totalEnergyActiveImport", unit_of_measurement="Wh", icon="mdi:flash"),
        CTEKSensor(session, host, port, auth, "total_energy_export", "Total Energy Export", "/meter", "totalEnergyActiveExport", unit_of_measurement="Wh", icon="mdi:flash-off"),

        # EVSE endpoint entities
        CTEKSensor(session, host, port, auth, "charger_serial", "Charger Serial", "/evse", "cb_id", icon="mdi:ev-plug-type2"),
        CTEKSensor(session, host, port, auth, "charger_connection_status", "Charger Connection Status", "/evse", "connection_status", icon="mdi:ev-plug-type2"),
        CTEKSensor(session, host, port, auth, "charger_outlet_1_state", "Charger Outlet 1 State", "/evse", "evse.0.state", icon="mdi:ev-plug-type2"),
        CTEKSensor(session, host, port, auth, "charger_outlet_2_state", "Charger Outlet 2 State", "/evse", "evse.1.state", icon="mdi:ev-plug-type2"),
        CTEKSensor(session, host, port, auth, "charger_outlet_1_current", "Charger Outlet 1 Current", "/evse", "evse.0.current", unit_of_measurement="A", icon="mdi:ev-plug-type2"),
        CTEKSensor(session, host, port, auth, "charger_outlet_2_current", "Charger Outlet 2 Current", "/evse", "evse.1.current", unit_of_measurement="A", icon="mdi:ev-plug-type2"),
    ]

    async_add_entities(sensors, True)


class CTEKSensor(SensorEntity):
    """Representation of a single CTEK Nanogrid Air sensor."""

    def __init__(self, session, host, port, auth, sensor_id, name, endpoint, json_path, unit_of_measurement=None, icon=None):
        self._session = session
        self._host = host
        self._port = port
        self._auth = auth
        self._sensor_id = sensor_id
        self._name = name
        self._endpoint = endpoint
        self._json_path = json_path
        self._unit_of_measurement = unit_of_measurement
        self._icon = icon
        self._state = None

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        # Provide a unique ID for the sensor
        return f"{DOMAIN}_{self._sensor_id}"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement

    @property
    def icon(self):
        return self._icon

    async def async_update(self):
        """Fetch data from the API and update the state."""
        url = f"http://{self._host}:{self._port}{self._endpoint}/"
        try:
            async with self._session.get(url, auth=self._auth, timeout=DEFAULT_TIMEOUT) as response:
                if response.status != 200:
                    _LOGGER.error(f"Failed to fetch data for {self._name}, status: {response.status}")
                    self._state = None
                    return

                data = await response.json()
                self._state = self._extract_value(data, self._json_path)

        except asyncio.TimeoutError:
            _LOGGER.error(f"Timeout fetching data for {self._name} from {url}")
            self._state = None

        except ClientError as e:
            _LOGGER.error(f"Client error for {self._name}: {e}")
            self._state = None

        except Exception as e:
            _LOGGER.error(f"Unexpected error for {self._name}: {e}")
            self._state = None

    def _extract_value(self, data, json_path):
        """Extract a value from a nested JSON object using a dotted path."""
        keys = json_path.split(".")
        value = data
        for key in keys:
            if isinstance(value, list):
                value = value[int(key)] if key.isdigit() else None
            else:
                value = value.get(key)
            if value is None:
                return None
        return value