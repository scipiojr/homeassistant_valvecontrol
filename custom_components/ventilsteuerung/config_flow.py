import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

class VentilsteuerungConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required("ventil_switch"): cv.entity_id,
            vol.Required("pumpe_switch"): cv.entity_id,
            vol.Required("pumpe_user_switch"): cv.entity_id,
            vol.Required("fahrzeit_oeffnen", default=180): int,
            vol.Required("fahrzeit_schliessen", default=180): int,
            vol.Required("grundstellung", default="geschlossen"): vol.In(["offen", "geschlossen"]),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors
        )