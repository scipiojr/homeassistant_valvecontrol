from homeassistant.helpers.entity import Entity
from homeassistant.const import TIME_MINUTES
from .const import DOMAIN

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    return

async def async_setup_entry(hass, config_entry, async_add_entities):
    name = config_entry.data["name"]
    timer_entity_id = f"timer.{name}_fahrzeit"
    async_add_entities([VentilRestzeitSensor(hass, name, timer_entity_id)])

class VentilRestzeitSensor(Entity):
    def __init__(self, hass, name, timer_entity_id):
        self._hass = hass
        self._name = f"{name.capitalize()} Rest-Verfahrzeit"
        self._entity_id = timer_entity_id
        self._state = None

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        timer = self._hass.states.get(self._entity_id)
        if timer and "remaining" in timer.attributes:
            remaining = timer.attributes["remaining"]
            if isinstance(remaining, str) and ":" in remaining:
                return remaining
        return "0:00"

    @property
    def unique_id(self):
        return f"{self._entity_id}_restzeit"

    @property
    def unit_of_measurement(self):
        return TIME_MINUTES

    @property
    def should_poll(self):
        return True

    @property
    def device_class(self):
        return "duration"