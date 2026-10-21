import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import pins, automation
from esphome.components import spi
from esphome.const import (
    CONF_ID,
    CONF_RESET_PIN,
    CONF_IRQ_PIN,
    CONF_TRIGGER_ID,
)

CODEOWNERS = ["@SzczepanLeon", "@kubasaw"]

DEPENDENCIES = ["esp32", "spi"]

AUTO_LOAD = ["wmbus_common"]

MULTI_CONF = True

CONF_RADIO_ID = "radio_id"
CONF_ON_FRAME = "on_frame"
CONF_RADIO_TYPE = "radio_type"
CONF_MARK_AS_HANDLED = "mark_as_handled"
CONF_BUSY_PIN = "busy_pin"
CONF_RX_GAIN = "rx_gain"
CONF_RF_SWITCH = "rf_switch"
CONF_HAS_TCXO = "has_tcxo"

radio_ns = cg.esphome_ns.namespace("wmbus_radio")
RadioComponent = radio_ns.class_("Radio", cg.Component)
RadioTransceiver = radio_ns.class_(
    "RadioTransceiver", spi.SPIDevice, cg.Component)
SX1262 = radio_ns.class_("SX1262", RadioTransceiver)
Frame = radio_ns.class_("Frame")
FramePtr = Frame.operator("ptr")
FrameTrigger = radio_ns.class_(
    "FrameTrigger", automation.Trigger.template(FramePtr))

RxGainMode = radio_ns.enum("RxGainMode")
RX_GAIN_OPTIONS = {
    "BOOSTED": RxGainMode.RX_GAIN_BOOSTED,
    "POWER_SAVING": RxGainMode.RX_GAIN_POWER_SAVING,
}


CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(RadioComponent),
            cv.GenerateID(CONF_RADIO_ID): cv.declare_id(SX1262),
            cv.Required(CONF_RADIO_TYPE): cv.one_of("SX1262", upper=True),
            # Output pin schema so the reset line can sit on an I/O expander
            cv.Optional(CONF_RESET_PIN): pins.gpio_output_pin_schema,
            cv.Required(CONF_IRQ_PIN): pins.internal_gpio_input_pin_schema,
            cv.Optional(CONF_BUSY_PIN): pins.gpio_input_pin_schema,
            # BOOSTED gives better sensitivity at a higher current
            cv.Optional(CONF_RX_GAIN, default="BOOSTED"): cv.enum(
                RX_GAIN_OPTIONS, upper=True
            ),
            # Use DIO2 as RF switch control
            cv.Optional(CONF_RF_SWITCH, default=False): cv.boolean,
            # Use DIO3 to drive an external TCXO
            cv.Optional(CONF_HAS_TCXO, default=True): cv.boolean,
            cv.Optional(CONF_ON_FRAME): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(FrameTrigger),
                    cv.Optional(CONF_MARK_AS_HANDLED, default=False): cv.boolean,
                }
            ),
        }
    )
    .extend(spi.spi_device_schema(default_data_rate=1e6, default_mode="MODE0"))
    .extend(cv.COMPONENT_SCHEMA)
)


async def to_code(config):
    cg.add(cg.LineComment("WMBus RadioTransceiver"))
    radio_var = cg.new_Pvariable(config[CONF_RADIO_ID])

    if CONF_RESET_PIN in config:
        reset_pin = await cg.gpio_pin_expression(config[CONF_RESET_PIN])
        cg.add(radio_var.set_reset_pin(reset_pin))

    irq_pin = await cg.gpio_pin_expression(config[CONF_IRQ_PIN])
    cg.add(radio_var.set_irq_pin(irq_pin))

    if CONF_BUSY_PIN in config:
        busy_pin = await cg.gpio_pin_expression(config[CONF_BUSY_PIN])
        cg.add(radio_var.set_busy_pin(busy_pin))

    cg.add(radio_var.set_rx_gain_mode(config[CONF_RX_GAIN]))
    cg.add(radio_var.set_rf_switch(config[CONF_RF_SWITCH]))
    cg.add(radio_var.set_tcxo(config[CONF_HAS_TCXO]))

    await spi.register_spi_device(radio_var, config)
    await cg.register_component(radio_var, config)

    cg.add(cg.LineComment("WMBus Component"))
    var = cg.new_Pvariable(config[CONF_ID])
    cg.add(var.set_radio(radio_var))

    await cg.register_component(var, config)

    for conf in config.get(CONF_ON_FRAME, []):
        trig = cg.new_Pvariable(
            conf[CONF_TRIGGER_ID], var, conf[CONF_MARK_AS_HANDLED])
        await automation.build_automation(
            trig,
            [(FramePtr, "frame")],
            conf,
        )
