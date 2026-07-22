#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>

#include "esphome/components/speaker/speaker.h"
#include "esphome/core/component.h"

#include "driver/spi_master.h"
#include "driver/gpio.h"

namespace esphome {
namespace offline_media {

enum class RescueClip : uint8_t {
  NONE = 0,
  MODE_READY,
  POWER_OUTAGE,
  CHECKLIST_OUTAGE,
  EVACUATION,
  CHECKLIST_EVACUATION,
  ALL_CLEAR,
};

enum class OfflineMediaStatus : uint8_t {
  STARTING = 0,
  READY,
  NO_CARD,
  PLAYING,
  BUSY,
  INVALID_FILE,
  READ_ERROR,
  STOPPED,
};

struct FatVolume {
  uint32_t partition_start{0};
  uint32_t fat_start{0};
  uint32_t data_start{0};
  uint32_t root_cluster{0};
  uint32_t root_directory_start{0};
  uint32_t root_directory_sectors{0};
  uint32_t sectors_per_fat{0};
  uint8_t sectors_per_cluster{0};
  uint8_t fat_count{0};
  uint8_t fat_bits{0};
};

struct RawFatFile {
  uint32_t first_cluster{0};
  uint32_t current_cluster{0};
  uint32_t size{0};
  uint32_t position{0};
  uint16_t sector_in_cluster{0};
  uint16_t offset_in_sector{0};
};

class OfflineMedia : public Component {
 public:
  void setup() override;
  void dump_config() override;
  float get_setup_priority() const override;

  void set_speaker(speaker::Speaker *speaker) { this->speaker_ = speaker; }
  void set_cs_pin(int pin) { this->cs_pin_ = pin; }
  void set_clk_pin(int pin) { this->clk_pin_ = pin; }
  void set_mosi_pin(int pin) { this->mosi_pin_ = pin; }
  void set_miso_pin(int pin) { this->miso_pin_ = pin; }
  void set_max_clip_seconds(uint32_t seconds) { this->max_clip_seconds_ = seconds; }

  bool mount_card();
  bool play_clip(const std::string &clip_id);
  bool play_next();
  void stop();

  bool is_card_ready() const { return this->card_ready_.load(); }
  bool is_playing() const { return this->playing_.load(); }
  uint32_t get_play_count() const { return this->play_count_.load(); }
  uint32_t get_error_count() const { return this->error_count_.load(); }
  std::string get_status() const;
  std::string get_active_clip() const;

 protected:
  static void playback_task(void *parameter);
  void run_playback();
  void set_error_(OfflineMediaStatus status);
  RescueClip clip_from_id_(const std::string &clip_id) const;
  const char *clip_id_(RescueClip clip) const;
  const char *clip_short_name_(RescueClip clip) const;
  void unmount_card_();

  bool initialize_sd_();
  bool configure_spi_(int clock_hz);
  uint8_t transfer_byte_(uint8_t value);
  void select_card_();
  void deselect_card_();
  uint8_t command_(uint8_t command, uint32_t argument, uint8_t *extra = nullptr, size_t extra_length = 0,
                   bool keep_selected = false);
  bool read_sector_(uint32_t sector, uint8_t *buffer);
  bool parse_volume_();
  bool find_directory_entry_(uint32_t directory_cluster, bool fixed_root, const char short_name[11],
                             uint32_t *first_cluster, uint32_t *size, bool *is_directory);
  bool open_file_(const char short_name[11], RawFatFile *file);
  size_t read_file_(RawFatFile *file, uint8_t *buffer, size_t length);
  uint32_t next_cluster_(uint32_t cluster);
  uint32_t cluster_sector_(uint32_t cluster) const;
  bool end_of_chain_(uint32_t cluster) const;

  speaker::Speaker *speaker_{nullptr};
  int cs_pin_{-1};
  int clk_pin_{-1};
  int mosi_pin_{-1};
  int miso_pin_{-1};
  uint32_t max_clip_seconds_{180};
  spi_device_handle_t spi_device_{nullptr};
  bool spi_initialized_{false};
  bool high_capacity_{false};
  alignas(4) uint8_t sector_rx_[512]{};
  alignas(4) uint8_t sector_clocks_[512]{};
  FatVolume volume_{};

  std::atomic<bool> card_ready_{false};
  std::atomic<bool> playing_{false};
  std::atomic<bool> stop_requested_{false};
  std::atomic<uint32_t> play_count_{0};
  std::atomic<uint32_t> error_count_{0};
  std::atomic<OfflineMediaStatus> status_{OfflineMediaStatus::STARTING};
  std::atomic<RescueClip> active_clip_{RescueClip::NONE};
  uint8_t next_clip_index_{0};
};

}  // namespace offline_media
}  // namespace esphome
