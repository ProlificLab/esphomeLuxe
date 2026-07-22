import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import sensor, text_sensor
from esphome.const import (
    CONF_ID,
    ENTITY_CATEGORY_DIAGNOSTIC,
    ICON_COUNTER,
    ICON_RESTART,
    ICON_TIMER,
    UNIT_BYTES,
    UNIT_MILLISECOND,
)


CONF_HEAP_FREE = "heap_free"
CONF_HEAP_MAX_BLOCK = "heap_max_block"
CONF_LOOP_TIME = "loop_time"
CONF_FREE_PSRAM = "free_psram"
CONF_RESET_REASON = "reset_reason"

lean_diagnostics_ns = cg.esphome_ns.namespace("lean_diagnostics")
LeanDiagnostics = lean_diagnostics_ns.class_("LeanDiagnostics", cg.PollingComponent)

DIAGNOSTIC_BYTES = sensor.sensor_schema(
    unit_of_measurement=UNIT_BYTES,
    icon=ICON_COUNTER,
    accuracy_decimals=0,
    entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
)

CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(LeanDiagnostics),
            cv.Required(CONF_HEAP_FREE): DIAGNOSTIC_BYTES,
            cv.Required(CONF_HEAP_MAX_BLOCK): DIAGNOSTIC_BYTES,
            cv.Required(CONF_LOOP_TIME): sensor.sensor_schema(
                unit_of_measurement=UNIT_MILLISECOND,
                icon=ICON_TIMER,
                accuracy_decimals=0,
                entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
            ),
            cv.Required(CONF_FREE_PSRAM): DIAGNOSTIC_BYTES,
            cv.Required(CONF_RESET_REASON): text_sensor.text_sensor_schema(
                icon=ICON_RESTART,
                entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
            ),
        }
    )
    .extend(cv.polling_component_schema("60s"))
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    for key, setter in (
        (CONF_HEAP_FREE, var.set_heap_free_sensor),
        (CONF_HEAP_MAX_BLOCK, var.set_heap_max_block_sensor),
        (CONF_LOOP_TIME, var.set_loop_time_sensor),
        (CONF_FREE_PSRAM, var.set_free_psram_sensor),
    ):
        sens = await sensor.new_sensor(config[key])
        cg.add(setter(sens))
    reset_reason = await text_sensor.new_text_sensor(config[CONF_RESET_REASON])
    cg.add(var.set_reset_reason_sensor(reset_reason))
