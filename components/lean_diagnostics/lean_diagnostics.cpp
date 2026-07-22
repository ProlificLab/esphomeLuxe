#include "lean_diagnostics.h"

#include "esphome/core/hal.h"

#include <esp_heap_caps.h>
#include <esp_system.h>

namespace esphome {
namespace lean_diagnostics {

void LeanDiagnostics::setup() {
  this->last_loop_ms_ = millis();
  this->reset_reason_sensor_->publish_state(this->reset_reason_());
}

void LeanDiagnostics::loop() {
  const uint32_t now = millis();
  const uint32_t elapsed = now - this->last_loop_ms_;
  if (elapsed > this->max_loop_ms_)
    this->max_loop_ms_ = elapsed;
  this->last_loop_ms_ = now;
}

void LeanDiagnostics::update() {
  this->heap_free_sensor_->publish_state(heap_caps_get_free_size(MALLOC_CAP_INTERNAL));
  this->heap_max_block_sensor_->publish_state(heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL));
  this->free_psram_sensor_->publish_state(heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
  this->loop_time_sensor_->publish_state(this->max_loop_ms_);
  this->max_loop_ms_ = 0;
}

const char *LeanDiagnostics::reset_reason_() const {
  switch (esp_reset_reason()) {
    case ESP_RST_POWERON:
      return "Power on";
    case ESP_RST_EXT:
      return "External";
    case ESP_RST_SW:
      return "Software";
    case ESP_RST_PANIC:
      return "Panic";
    case ESP_RST_INT_WDT:
      return "Interrupt WDT";
    case ESP_RST_TASK_WDT:
      return "Task WDT";
    case ESP_RST_WDT:
      return "Watchdog";
    case ESP_RST_DEEPSLEEP:
      return "Deep sleep";
    case ESP_RST_BROWNOUT:
      return "Brownout";
    case ESP_RST_SDIO:
      return "SDIO";
    default:
      return "Unknown";
  }
}

}  // namespace lean_diagnostics
}  // namespace esphome
