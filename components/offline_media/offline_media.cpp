#include "offline_media.h"

#include <algorithm>
#include <cstring>

#include "esphome/components/audio/audio.h"
#include "esphome/core/log.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

namespace esphome {
namespace offline_media {

static const char *const TAG = "offline_media";
static const spi_host_device_t SD_HOST = SPI2_HOST;
static const size_t SECTOR_SIZE = 512;
static const size_t AUDIO_BUFFER_SIZE = 4096;
static const char RESCUE_DIRECTORY[11] = {'R', 'E', 'S', 'C', 'U', 'E', ' ', ' ', ' ', ' ', ' '};

static uint16_t read_u16(const uint8_t *data) {
  return static_cast<uint16_t>(data[0]) | (static_cast<uint16_t>(data[1]) << 8);
}

static uint32_t read_u32(const uint8_t *data) {
  return static_cast<uint32_t>(data[0]) | (static_cast<uint32_t>(data[1]) << 8) |
         (static_cast<uint32_t>(data[2]) << 16) | (static_cast<uint32_t>(data[3]) << 24);
}

float OfflineMedia::get_setup_priority() const { return setup_priority::HARDWARE - 1.0f; }

void OfflineMedia::setup() { this->mount_card(); }

void OfflineMedia::dump_config() {
  ESP_LOGCONFIG(TAG, "Muse offline rescue media:");
  ESP_LOGCONFIG(TAG, "  SPI pins: CS=%d CLK=%d MOSI=%d MISO=%d", this->cs_pin_, this->clk_pin_, this->mosi_pin_,
                this->miso_pin_);
  ESP_LOGCONFIG(TAG, "  Reader: FAT16/32, fixed 8.3 names, no write operations");
  ESP_LOGCONFIG(TAG, "  Maximum clip: %u seconds", this->max_clip_seconds_);
  ESP_LOGCONFIG(TAG, "  Card ready: %s", YESNO(this->is_card_ready()));
}

void OfflineMedia::unmount_card_() {
  if (this->spi_device_ != nullptr) {
    spi_bus_remove_device(this->spi_device_);
    this->spi_device_ = nullptr;
  }
  if (this->spi_initialized_) {
    spi_bus_free(SD_HOST);
    this->spi_initialized_ = false;
  }
  this->card_ready_.store(false);
  this->high_capacity_ = false;
  this->volume_ = {};
}

bool OfflineMedia::configure_spi_(int clock_hz) {
  if (this->spi_device_ != nullptr) {
    spi_bus_remove_device(this->spi_device_);
    this->spi_device_ = nullptr;
  }
  spi_device_interface_config_t device_config{};
  device_config.clock_speed_hz = clock_hz;
  device_config.mode = 0;
  device_config.spics_io_num = -1;
  device_config.queue_size = 1;
  return spi_bus_add_device(SD_HOST, &device_config, &this->spi_device_) == ESP_OK;
}

uint8_t OfflineMedia::transfer_byte_(uint8_t value) {
  spi_transaction_t transaction{};
  transaction.flags = SPI_TRANS_USE_TXDATA | SPI_TRANS_USE_RXDATA;
  transaction.length = 8;
  transaction.tx_data[0] = value;
  if (spi_device_polling_transmit(this->spi_device_, &transaction) != ESP_OK) return 0xFF;
  return transaction.rx_data[0];
}

void OfflineMedia::select_card_() {
  gpio_set_level(static_cast<gpio_num_t>(this->cs_pin_), 0);
  this->transfer_byte_(0xFF);
}

void OfflineMedia::deselect_card_() {
  gpio_set_level(static_cast<gpio_num_t>(this->cs_pin_), 1);
  this->transfer_byte_(0xFF);
}

uint8_t OfflineMedia::command_(uint8_t command, uint32_t argument, uint8_t *extra, size_t extra_length,
                               bool keep_selected) {
  this->deselect_card_();
  this->select_card_();
  this->transfer_byte_(0x40U | command);
  this->transfer_byte_(argument >> 24);
  this->transfer_byte_(argument >> 16);
  this->transfer_byte_(argument >> 8);
  this->transfer_byte_(argument);
  this->transfer_byte_(command == 0 ? 0x95 : (command == 8 ? 0x87 : 0x01));
  uint8_t response = 0xFF;
  for (uint8_t attempt = 0; attempt < 10 && (response & 0x80U); attempt++) response = this->transfer_byte_(0xFF);
  for (size_t index = 0; index < extra_length; index++) extra[index] = this->transfer_byte_(0xFF);
  if (!keep_selected) this->deselect_card_();
  return response;
}

bool OfflineMedia::initialize_sd_() {
  std::memset(this->sector_clocks_, 0xFF, sizeof(this->sector_clocks_));
  gpio_config_t cs_config{};
  cs_config.pin_bit_mask = 1ULL << this->cs_pin_;
  cs_config.mode = GPIO_MODE_OUTPUT;
  cs_config.pull_up_en = GPIO_PULLUP_ENABLE;
  if (gpio_config(&cs_config) != ESP_OK || !this->configure_spi_(400000)) return false;
  this->deselect_card_();
  for (uint8_t index = 0; index < 10; index++) this->transfer_byte_(0xFF);
  if (this->command_(0, 0) != 0x01) return false;

  uint8_t r7[4]{};
  uint8_t cmd8 = this->command_(8, 0x1AA, r7, sizeof(r7));
  bool version_two = cmd8 == 0x01 && r7[2] == 0x01 && r7[3] == 0xAA;
  bool ready = false;
  for (uint16_t attempt = 0; attempt < 500; attempt++) {
    if (this->command_(55, 0) > 0x01) break;
    uint8_t response = this->command_(41, version_two ? 0x40000000U : 0U);
    if (response == 0x00) {
      ready = true;
      break;
    }
    vTaskDelay(pdMS_TO_TICKS(2));
  }
  if (!ready) return false;

  uint8_t ocr[4]{};
  if (this->command_(58, 0, ocr, sizeof(ocr)) != 0x00) return false;
  this->high_capacity_ = version_two && (ocr[0] & 0x40U) != 0;
  if (!this->high_capacity_ && this->command_(16, SECTOR_SIZE) != 0x00) return false;
  return this->configure_spi_(10000000);
}

bool OfflineMedia::mount_card() {
  if (this->playing_.load()) {
    this->set_error_(OfflineMediaStatus::BUSY);
    return false;
  }
  this->unmount_card_();

  spi_bus_config_t bus_config{};
  bus_config.mosi_io_num = this->mosi_pin_;
  bus_config.miso_io_num = this->miso_pin_;
  bus_config.sclk_io_num = this->clk_pin_;
  bus_config.quadwp_io_num = -1;
  bus_config.quadhd_io_num = -1;
  bus_config.max_transfer_sz = AUDIO_BUFFER_SIZE;
  esp_err_t err = spi_bus_initialize(SD_HOST, &bus_config, SPI_DMA_CH_AUTO);
  if (err != ESP_OK) {
    ESP_LOGW(TAG, "SPI initialization failed: %s", esp_err_to_name(err));
    this->set_error_(OfflineMediaStatus::NO_CARD);
    return false;
  }
  this->spi_initialized_ = true;

  if (!this->initialize_sd_() || !this->parse_volume_()) {
    ESP_LOGW(TAG, "No supported read-only FAT16/32 rescue card");
    this->unmount_card_();
    this->set_error_(OfflineMediaStatus::NO_CARD);
    return false;
  }

  this->card_ready_.store(true);
  this->status_.store(OfflineMediaStatus::READY);
  ESP_LOGI(TAG, "Rescue card ready through the fixed read-only FAT reader");
  return true;
}

bool OfflineMedia::read_sector_(uint32_t sector, uint8_t *buffer) {
  uint32_t address = this->high_capacity_ ? sector : sector * SECTOR_SIZE;
  if (this->command_(17, address, nullptr, 0, true) != 0x00) {
    this->deselect_card_();
    return false;
  }
  uint8_t token = 0xFF;
  for (uint32_t attempt = 0; attempt < 100000 && token == 0xFF; attempt++) token = this->transfer_byte_(0xFF);
  if (token != 0xFE) {
    this->deselect_card_();
    return false;
  }
  spi_transaction_t transaction{};
  transaction.length = SECTOR_SIZE * 8;
  transaction.tx_buffer = this->sector_clocks_;
  transaction.rx_buffer = this->sector_rx_;
  if (spi_device_polling_transmit(this->spi_device_, &transaction) != ESP_OK) {
    this->deselect_card_();
    return false;
  }
  std::memcpy(buffer, this->sector_rx_, SECTOR_SIZE);
  this->transfer_byte_(0xFF);
  this->transfer_byte_(0xFF);
  this->deselect_card_();
  return true;
}

bool OfflineMedia::parse_volume_() {
  uint8_t sector[SECTOR_SIZE];
  if (!this->read_sector_(0, sector) || sector[510] != 0x55 || sector[511] != 0xAA) return false;

  uint32_t partition_start = 0;
  if (read_u16(sector + 11) != SECTOR_SIZE) {
    partition_start = read_u32(sector + 446 + 8);
    if (partition_start == 0 || !this->read_sector_(partition_start, sector) || sector[510] != 0x55 ||
        sector[511] != 0xAA)
      return false;
  }
  if (read_u16(sector + 11) != SECTOR_SIZE) return false;

  uint8_t sectors_per_cluster = sector[13];
  uint16_t reserved = read_u16(sector + 14);
  uint8_t fat_count = sector[16];
  uint16_t root_entries = read_u16(sector + 17);
  uint32_t total_sectors = read_u16(sector + 19);
  if (total_sectors == 0) total_sectors = read_u32(sector + 32);
  uint32_t sectors_per_fat = read_u16(sector + 22);
  if (sectors_per_fat == 0) sectors_per_fat = read_u32(sector + 36);
  if (sectors_per_cluster == 0 || (sectors_per_cluster & (sectors_per_cluster - 1)) != 0 || reserved == 0 ||
      fat_count == 0 || sectors_per_fat == 0 || total_sectors == 0)
    return false;

  uint32_t root_sectors = ((static_cast<uint32_t>(root_entries) * 32U) + 511U) / 512U;
  uint32_t data_sectors = total_sectors - reserved - (fat_count * sectors_per_fat) - root_sectors;
  uint32_t clusters = data_sectors / sectors_per_cluster;
  uint8_t fat_bits = clusters < 4085 ? 12 : (clusters < 65525 ? 16 : 32);
  if (fat_bits == 12) return false;

  this->volume_.partition_start = partition_start;
  this->volume_.fat_start = partition_start + reserved;
  this->volume_.root_directory_start = partition_start + reserved + fat_count * sectors_per_fat;
  this->volume_.root_directory_sectors = root_sectors;
  this->volume_.data_start = this->volume_.root_directory_start + root_sectors;
  this->volume_.root_cluster = fat_bits == 32 ? read_u32(sector + 44) : 0;
  this->volume_.sectors_per_fat = sectors_per_fat;
  this->volume_.sectors_per_cluster = sectors_per_cluster;
  this->volume_.fat_count = fat_count;
  this->volume_.fat_bits = fat_bits;
  return fat_bits == 16 || (fat_bits == 32 && this->volume_.root_cluster >= 2);
}

uint32_t OfflineMedia::cluster_sector_(uint32_t cluster) const {
  return this->volume_.data_start + (cluster - 2U) * this->volume_.sectors_per_cluster;
}

bool OfflineMedia::end_of_chain_(uint32_t cluster) const {
  return this->volume_.fat_bits == 16 ? cluster >= 0xFFF8U : cluster >= 0x0FFFFFF8U;
}

uint32_t OfflineMedia::next_cluster_(uint32_t cluster) {
  uint32_t entry_size = this->volume_.fat_bits / 8U;
  uint32_t offset = cluster * entry_size;
  uint8_t sector[SECTOR_SIZE];
  if (!this->read_sector_(this->volume_.fat_start + offset / SECTOR_SIZE, sector)) return 0;
  uint32_t within = offset % SECTOR_SIZE;
  uint32_t next = this->volume_.fat_bits == 16 ? read_u16(sector + within) : read_u32(sector + within);
  return this->volume_.fat_bits == 32 ? next & 0x0FFFFFFFU : next;
}

bool OfflineMedia::find_directory_entry_(uint32_t directory_cluster, bool fixed_root, const char short_name[11],
                                         uint32_t *first_cluster, uint32_t *size, bool *is_directory) {
  uint8_t sector[SECTOR_SIZE];
  uint32_t cluster = directory_cluster;
  uint32_t fixed_sector = this->volume_.root_directory_start;
  uint32_t fixed_remaining = this->volume_.root_directory_sectors;
  while ((fixed_root && fixed_remaining > 0) || (!fixed_root && cluster >= 2 && !this->end_of_chain_(cluster))) {
    uint32_t sector_start = fixed_root ? fixed_sector : this->cluster_sector_(cluster);
    uint32_t sector_count = fixed_root ? fixed_remaining : this->volume_.sectors_per_cluster;
    for (uint32_t index = 0; index < sector_count; index++) {
      if (!this->read_sector_(sector_start + index, sector)) return false;
      for (size_t offset = 0; offset < SECTOR_SIZE; offset += 32) {
        const uint8_t *entry = sector + offset;
        if (entry[0] == 0x00) return false;
        if (entry[0] == 0xE5 || entry[11] == 0x0F || (entry[11] & 0x08) != 0) continue;
        if (std::memcmp(entry, short_name, 11) != 0) continue;
        *first_cluster = (static_cast<uint32_t>(read_u16(entry + 20)) << 16) | read_u16(entry + 26);
        *size = read_u32(entry + 28);
        *is_directory = (entry[11] & 0x10) != 0;
        return true;
      }
    }
    if (fixed_root) {
      fixed_remaining = 0;
    } else {
      cluster = this->next_cluster_(cluster);
      if (cluster == 0) return false;
    }
  }
  return false;
}

bool OfflineMedia::open_file_(const char short_name[11], RawFatFile *file) {
  uint32_t rescue_cluster = 0;
  uint32_t ignored_size = 0;
  bool is_directory = false;
  bool fixed_root = this->volume_.fat_bits == 16;
  if (!this->find_directory_entry_(this->volume_.root_cluster, fixed_root, RESCUE_DIRECTORY, &rescue_cluster,
                                   &ignored_size, &is_directory) ||
      !is_directory || rescue_cluster < 2)
    return false;

  uint32_t first_cluster = 0;
  uint32_t size = 0;
  if (!this->find_directory_entry_(rescue_cluster, false, short_name, &first_cluster, &size, &is_directory) ||
      is_directory || first_cluster < 2 || size < 44)
    return false;
  *file = {first_cluster, first_cluster, size, 0, 0, 0};
  return true;
}

size_t OfflineMedia::read_file_(RawFatFile *file, uint8_t *buffer, size_t length) {
  size_t total = 0;
  uint8_t sector[SECTOR_SIZE];
  while (total < length && file->position < file->size && file->current_cluster >= 2 &&
         !this->end_of_chain_(file->current_cluster)) {
    uint32_t sector_number = this->cluster_sector_(file->current_cluster) + file->sector_in_cluster;
    if (!this->read_sector_(sector_number, sector)) break;
    size_t available = SECTOR_SIZE - file->offset_in_sector;
    size_t remaining_file = file->size - file->position;
    size_t count = std::min({available, length - total, remaining_file});
    std::memcpy(buffer + total, sector + file->offset_in_sector, count);
    total += count;
    file->position += count;
    file->offset_in_sector += count;
    if (file->offset_in_sector == SECTOR_SIZE) {
      file->offset_in_sector = 0;
      file->sector_in_cluster++;
      if (file->sector_in_cluster == this->volume_.sectors_per_cluster) {
        file->sector_in_cluster = 0;
        file->current_cluster = this->next_cluster_(file->current_cluster);
      }
    }
  }
  return total;
}

RescueClip OfflineMedia::clip_from_id_(const std::string &clip_id) const {
  if (clip_id == "mode_ready") return RescueClip::MODE_READY;
  if (clip_id == "power_outage") return RescueClip::POWER_OUTAGE;
  if (clip_id == "checklist_outage") return RescueClip::CHECKLIST_OUTAGE;
  if (clip_id == "evacuation") return RescueClip::EVACUATION;
  if (clip_id == "checklist_evacuation") return RescueClip::CHECKLIST_EVACUATION;
  if (clip_id == "all_clear") return RescueClip::ALL_CLEAR;
  return RescueClip::NONE;
}

const char *OfflineMedia::clip_id_(RescueClip clip) const {
  switch (clip) {
    case RescueClip::MODE_READY: return "mode_ready";
    case RescueClip::POWER_OUTAGE: return "power_outage";
    case RescueClip::CHECKLIST_OUTAGE: return "checklist_outage";
    case RescueClip::EVACUATION: return "evacuation";
    case RescueClip::CHECKLIST_EVACUATION: return "checklist_evacuation";
    case RescueClip::ALL_CLEAR: return "all_clear";
    default: return "none";
  }
}

const char *OfflineMedia::clip_short_name_(RescueClip clip) const {
  switch (clip) {
    case RescueClip::MODE_READY: return "READY   WAV";
    case RescueClip::POWER_OUTAGE: return "POWER   WAV";
    case RescueClip::CHECKLIST_OUTAGE: return "PWRLIST WAV";
    case RescueClip::EVACUATION: return "EVAC    WAV";
    case RescueClip::CHECKLIST_EVACUATION: return "EVACLISTWAV";
    case RescueClip::ALL_CLEAR: return "ALLCLEARWAV";
    default: return nullptr;
  }
}

bool OfflineMedia::play_clip(const std::string &clip_id) {
  RescueClip clip = this->clip_from_id_(clip_id);
  if (clip == RescueClip::NONE) {
    this->set_error_(OfflineMediaStatus::INVALID_FILE);
    return false;
  }
  if (!this->card_ready_.load() || this->playing_.exchange(true)) {
    this->set_error_(this->card_ready_.load() ? OfflineMediaStatus::BUSY : OfflineMediaStatus::NO_CARD);
    return false;
  }
  if (this->speaker_ == nullptr || !this->speaker_->is_stopped()) {
    this->playing_.store(false);
    this->set_error_(OfflineMediaStatus::BUSY);
    return false;
  }
  this->stop_requested_.store(false);
  this->active_clip_.store(clip);
  this->status_.store(OfflineMediaStatus::PLAYING);
  if (xTaskCreatePinnedToCore(playback_task, "muse_rescue_audio", 6144, this, 2, nullptr, 1) != pdPASS) {
    this->playing_.store(false);
    this->active_clip_.store(RescueClip::NONE);
    this->set_error_(OfflineMediaStatus::READ_ERROR);
    return false;
  }
  return true;
}

bool OfflineMedia::play_next() {
  static const char *const CLIPS[] = {"power_outage", "checklist_outage", "evacuation",
                                     "checklist_evacuation", "all_clear"};
  const char *clip = CLIPS[this->next_clip_index_ % 5];
  this->next_clip_index_ = (this->next_clip_index_ + 1) % 5;
  return this->play_clip(clip);
}

void OfflineMedia::stop() {
  this->stop_requested_.store(true);
  if (this->playing_.load() && this->speaker_ != nullptr) this->speaker_->stop();
}

void OfflineMedia::playback_task(void *parameter) {
  auto *component = static_cast<OfflineMedia *>(parameter);
  component->run_playback();
  vTaskDelete(nullptr);
}

void OfflineMedia::run_playback() {
  RawFatFile file;
  const char *short_name = this->clip_short_name_(this->active_clip_.load());
  if (short_name == nullptr || !this->open_file_(short_name, &file)) {
    ESP_LOGW(TAG, "Fixed rescue clip is missing or invalid");
    this->set_error_(OfflineMediaStatus::INVALID_FILE);
    this->playing_.store(false);
    this->active_clip_.store(RescueClip::NONE);
    return;
  }

  uint8_t header[44];
  bool valid = this->read_file_(&file, header, sizeof(header)) == sizeof(header) &&
               std::memcmp(header, "RIFF", 4) == 0 && std::memcmp(header + 8, "WAVEfmt ", 8) == 0 &&
               read_u32(header + 16) == 16 && read_u16(header + 20) == 1 && read_u16(header + 22) == 2 &&
               read_u32(header + 24) == 48000 && read_u16(header + 34) == 16 &&
               std::memcmp(header + 36, "data", 4) == 0;
  uint32_t data_size = valid ? read_u32(header + 40) : 0;
  const uint64_t maximum_bytes = static_cast<uint64_t>(this->max_clip_seconds_) * 48000ULL * 2ULL * 2ULL;
  valid = valid && data_size > 0 && data_size <= maximum_bytes && data_size <= file.size - sizeof(header);
  if (!valid) {
    ESP_LOGW(TAG, "Rejected rescue clip; require canonical PCM s16le, 48 kHz, stereo, <=%us",
             this->max_clip_seconds_);
    this->set_error_(OfflineMediaStatus::INVALID_FILE);
    this->playing_.store(false);
    this->active_clip_.store(RescueClip::NONE);
    return;
  }

  this->speaker_->set_audio_stream_info(audio::AudioStreamInfo(16, 2, 48000));
  this->speaker_->start();
  uint8_t buffer[AUDIO_BUFFER_SIZE];
  uint32_t remaining = data_size;
  bool read_error = false;
  while (remaining > 0 && !this->stop_requested_.load()) {
    size_t requested = std::min<size_t>(sizeof(buffer), remaining);
    size_t received = this->read_file_(&file, buffer, requested);
    if (received == 0) {
      read_error = true;
      break;
    }
    size_t offset = 0;
    while (offset < received && !this->stop_requested_.load()) {
      size_t written = this->speaker_->play(buffer + offset, received - offset, pdMS_TO_TICKS(100));
      if (written == 0) vTaskDelay(pdMS_TO_TICKS(10));
      offset += written;
    }
    remaining -= received;
  }

  if (this->stop_requested_.load()) {
    this->speaker_->stop();
    this->status_.store(OfflineMediaStatus::STOPPED);
  } else if (read_error || remaining != 0) {
    this->speaker_->stop();
    this->set_error_(OfflineMediaStatus::READ_ERROR);
  } else {
    this->speaker_->finish();
    this->play_count_.fetch_add(1);
    this->status_.store(OfflineMediaStatus::READY);
  }
  this->active_clip_.store(RescueClip::NONE);
  this->playing_.store(false);
}

void OfflineMedia::set_error_(OfflineMediaStatus status) {
  this->status_.store(status);
  this->error_count_.fetch_add(1);
}

std::string OfflineMedia::get_status() const {
  switch (this->status_.load()) {
    case OfflineMediaStatus::STARTING: return "starting";
    case OfflineMediaStatus::READY: return "ready";
    case OfflineMediaStatus::NO_CARD: return "no_card";
    case OfflineMediaStatus::PLAYING: return std::string("playing:") + this->get_active_clip();
    case OfflineMediaStatus::BUSY: return "busy";
    case OfflineMediaStatus::INVALID_FILE: return "invalid_file";
    case OfflineMediaStatus::READ_ERROR: return "read_error";
    case OfflineMediaStatus::STOPPED: return "stopped";
    default: return "unknown";
  }
}

std::string OfflineMedia::get_active_clip() const { return this->clip_id_(this->active_clip_.load()); }

}  // namespace offline_media
}  // namespace esphome
