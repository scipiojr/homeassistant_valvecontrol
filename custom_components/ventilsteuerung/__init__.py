import logging
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change, async_track_event
from homeassistant.const import STATE_ON, STATE_OFF
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

DOMAIN = "ventilsteuerung"
_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required("name"): cv.string,
        vol.Required("ventil_switch"): cv.entity_id,
        vol.Required("pumpe_switch"): cv.entity_id,
        vol.Required("pumpe_user_switch"): cv.entity_id,
        vol.Optional("fahrzeit_oeffnen", default=180): cv.positive_int,
        vol.Optional("fahrzeit_schliessen", default=180): cv.positive_int,
        vol.Optional("grundstellung", default="geschlossen"): vol.In(["offen", "geschlossen"]),
        vol.Optional("enabled", default=True): cv.boolean
    })
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config) -> bool:
    conf = config.get(DOMAIN)
    if not conf or not conf.get("enabled", True):
        _LOGGER.warning("Ventilsteuerung ist deaktiviert oder nicht konfiguriert.")
        return True

    try:
        name = conf["name"]
        ventil_switch = conf["ventil_switch"]
        pumpe_switch = conf["pumpe_switch"]
        pumpe_user_switch = conf["pumpe_user_switch"]
        fahrzeit_oeffnen = conf["fahrzeit_oeffnen"]
        fahrzeit_schliessen = conf["fahrzeit_schliessen"]
        grundstellung = conf["grundstellung"]

        ventil_status = f"input_select.{name}_status"
        pumpe_nachholen = f"input_boolean.{name}_pumpe_nachholen"
        ventil_timer = f"timer.{name}_fahrzeit"

        async def ensure_helpers():
            try:
                if ventil_status not in hass.states.async_entity_ids():
                    await hass.services.async_call("input_select", "set_options", {
                        "entity_id": ventil_status,
                        "options": ["öffnet", "schließt", "offen", "geschlossen"]
                    }, blocking=True)
                    await hass.services.async_call("input_select", "select_option", {
                        "entity_id": ventil_status,
                        "option": "geschlossen"
                    }, blocking=True)

                if pumpe_nachholen not in hass.states.async_entity_ids():
                    await hass.services.async_call("input_boolean", "turn_off", {
                        "entity_id": pumpe_nachholen
                    }, blocking=True)

                if ventil_timer not in hass.states.async_entity_ids():
                    await hass.services.async_call("timer", "start", {
                        "entity_id": ventil_timer,
                        "duration": "00:00:01"
                    }, blocking=True)
                    await hass.services.async_call("timer", "cancel", {
                        "entity_id": ventil_timer
                    }, blocking=True)
            except Exception as e:
                _LOGGER.exception("Fehler beim Anlegen von Helfern: %s", e)

        async def init_state(_):
            try:
                await hass.services.async_call("switch", "turn_off", {"entity_id": pumpe_switch})
                if grundstellung == "offen":
                    await hass.services.async_call("switch", "turn_on", {"entity_id": ventil_switch})
                else:
                    await hass.services.async_call("switch", "turn_off", {"entity_id": ventil_switch})
            except Exception as e:
                _LOGGER.exception("Fehler beim Setzen der Grundstellung: %s", e)

        async def ventil_changed(entity, old_state, new_state):
            try:
                if new_state is None:
                    return
                status = hass.states.get(ventil_status).state
                if new_state.state == STATE_ON and status != "offen":
                    await hass.services.async_call("input_select", "select_option", {
                        "entity_id": ventil_status,
                        "option": "öffnet"
                    }, blocking=True)
                    await hass.services.async_call("switch", "turn_off", {
                        "entity_id": pumpe_switch
                    })
                    await hass.services.async_call("timer", "start", {
                        "entity_id": ventil_timer,
                        "duration": f"00:{fahrzeit_oeffnen // 60:02}:{fahrzeit_oeffnen % 60:02}"
                    })
                elif new_state.state == STATE_OFF and status != "geschlossen":
                    await hass.services.async_call("input_select", "select_option", {
                        "entity_id": ventil_status,
                        "option": "schließt"
                    }, blocking=True)
                    await hass.services.async_call("switch", "turn_off", {
                        "entity_id": pumpe_switch
                    })
                    await hass.services.async_call("timer", "start", {
                        "entity_id": ventil_timer,
                        "duration": f"00:{fahrzeit_schliessen // 60:02}:{fahrzeit_schliessen % 60:02}"
                    })
            except Exception as e:
                _LOGGER.exception("Fehler in ventil_changed: %s", e)

        async def timer_done(event):
            try:
                if event.data.get("entity_id") != ventil_timer:
                    return
                schalter = hass.states.get(ventil_switch).state
                ziel = "offen" if schalter == STATE_ON else "geschlossen"
                await hass.services.async_call("input_select", "select_option", {
                    "entity_id": ventil_status,
                    "option": ziel
                }, blocking=True)

                if hass.states.get(pumpe_nachholen).state == "on":
                    await hass.services.async_call("switch", "turn_on", {
                        "entity_id": pumpe_switch
                    })
                    await hass.services.async_call("input_boolean", "turn_off", {
                        "entity_id": pumpe_nachholen
                    })
            except Exception as e:
                _LOGGER.exception("Fehler in timer_done: %s", e)

        async def pumpe_user_changed(entity, old_state, new_state):
            try:
                if new_state is None or new_state.state != STATE_ON:
                    return
                status = hass.states.get(ventil_status).state
                if status in ["öffnet", "schließt"]:
                    await hass.services.async_call("input_boolean", "turn_on", {
                        "entity_id": pumpe_nachholen
                    })
                else:
                    await hass.services.async_call("switch", "turn_on", {
                        "entity_id": pumpe_switch
                    })
            except Exception as e:
                _LOGGER.exception("Fehler in pumpe_user_changed: %s", e)

        await ensure_helpers()
        async_call_later(hass, 5, init_state)
        async_track_state_change(hass, ventil_switch, ventil_changed)
        async_track_state_change(hass, pumpe_user_switch, pumpe_user_changed)
        hass.bus.async_listen("timer.finished", timer_done)

        _LOGGER.info("Ventilsteuerung '%s' wurde stabil geladen", name)
        return True

    except Exception as e:
        _LOGGER.exception("Fehler im Setup der Ventilsteuerung: %s", e)
        return True