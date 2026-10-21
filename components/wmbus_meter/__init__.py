import esphome.config_validation as cv
import esphome.codegen as cg
from esphome.const import (
    CONF_ID,
    CONF_TYPE,
    CONF_KEY,
    CONF_MODE,
)

from ..wmbus_radio import RadioComponent
from ..wmbus_common import validate_driver

CONF_METER_ID = "meter_id"
CONF_RADIO_ID = "radio_id"

CODEOWNERS = ["@SzczepanLeon", "@kubasaw"]

DEPENDENCIES = ["wmbus_radio"]
AUTO_LOAD = ["sensor", "text_sensor"]

MULTI_CONF = True


wmbus_meter_ns = cg.esphome_ns.namespace("wmbus_meter")
link_mode_enum = cg.global_ns.enum("LinkMode", is_class=True)
Meter = wmbus_meter_ns.class_("Meter", cg.Component)


def hex_key_validator(key):
    try:
        key = cv.bind_key(key)
        return key
    except cv.Invalid as e:
        raise cv.Invalid(e.msg.replace("Bind key", "Key"))


CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(Meter),
        cv.GenerateID(CONF_RADIO_ID): cv.use_id(RadioComponent),
        cv.Required(CONF_METER_ID): cv.hex_int,
        cv.Required(CONF_TYPE): validate_driver,
        cv.Optional(CONF_KEY): cv.Any(
            cv.All(cv.string_strict, lambda s: s.encode().hex(),
                   hex_key_validator),
            hex_key_validator,
        ),
        cv.Optional(CONF_MODE, default="Any"): cv.ensure_list(
            cv.enum(
                {name: getattr(link_mode_enum, name)
                 for name in ("Any", "C1", "T1")}
            )
        ),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    meter = cg.new_Pvariable(config[CONF_ID])
    cg.add(
        meter.set_meter_params(
            str('{:08x}'.format(config[CONF_METER_ID])),
            config[CONF_TYPE],
            config.get(CONF_KEY, ""),
            config[CONF_MODE],
        )
    )

    radio = await cg.get_variable(config[CONF_RADIO_ID])
    cg.add(meter.set_radio(radio))
    await cg.register_component(meter, config)
