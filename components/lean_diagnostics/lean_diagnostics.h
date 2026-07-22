#pragma once

#include "esphome/components/sensor/sensor.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "esphome/core/component.h"

namespace esphome {
namespace lean_diagnostics {

class LeanDiagnostics : public PollingComponent {
 public:
  void setup() override;
  void loop() override;
  void update() override;

  void set_heap_free_sensor(sensor::Sensor *value) { this->heap_free_sensor_ = value; }
  void set_heap_max_block_sensor(sensor::Sensor *value) { this->heap_max_block_sensor_ = value; }
  void set_loop_time_sensor(sensor::Sensor *value) { this->loop_time_sensor_ = value; }
  void set_free_psram_sensor(sensor::Sensor *value) { this->free_psram_sensor_ = value; }
  void set_reset_reason_sensor(text_sensor::TextSensor *value) { this->reset_reason_sensor_ = value; }

 protected:
  const char *reset_reason_() const;

  sensor::Sensor *heap_free_sensor_{nullptr};
  sensor::Sensor *heap_max_block_sensor_{nullptr};
  sensor::Sensor *loop_time_sensor_{nullptr};
  sensor::Sensor *free_psram_sensor_{nullptr};
  text_sensor::TextSensor *reset_reason_sensor_{nullptr};
  uint32_t last_loop_ms_{0};
  uint32_t max_loop_ms_{0};
};

}  // namespace lean_diagnostics
}  // namespace esphome
