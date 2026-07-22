import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import speaker
from esphome.const import CONF_ID


CONF_SPEAKER = "speaker"
CONF_CS_PIN = "cs_pin"
CONF_CLK_PIN = "clk_pin"
CONF_MOSI_PIN = "mosi_pin"
CONF_MISO_PIN = "miso_pin"
CONF_MAX_CLIP_SECONDS = "max_clip_seconds"

offline_media_ns = cg.esphome_ns.namespace("offline_media")
OfflineMedia = offline_media_ns.class_("OfflineMedia", cg.Component)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(OfflineMedia),
        cv.Required(CONF_SPEAKER): cv.use_id(speaker.Speaker),
        cv.Required(CONF_CS_PIN): cv.int_range(min=0, max=39),
        cv.Required(CONF_CLK_PIN): cv.int_range(min=0, max=39),
        cv.Required(CONF_MOSI_PIN): cv.int_range(min=0, max=39),
        cv.Required(CONF_MISO_PIN): cv.int_range(min=0, max=39),
        cv.Optional(CONF_MAX_CLIP_SECONDS, default=180): cv.int_range(
            min=1, max=300
        ),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    parent = await cg.get_variable(config[CONF_SPEAKER])
    cg.add(var.set_speaker(parent))
    cg.add(var.set_cs_pin(config[CONF_CS_PIN]))
    cg.add(var.set_clk_pin(config[CONF_CLK_PIN]))
    cg.add(var.set_mosi_pin(config[CONF_MOSI_PIN]))
    cg.add(var.set_miso_pin(config[CONF_MISO_PIN]))
    cg.add(var.set_max_clip_seconds(config[CONF_MAX_CLIP_SECONDS]))
