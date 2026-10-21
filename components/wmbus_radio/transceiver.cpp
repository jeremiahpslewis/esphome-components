#include "transceiver.h"

#include "esphome/core/log.h"

namespace esphome {
namespace wmbus_radio {
static const char *TAG = "wmbus.transceiver";

void RadioTransceiver::set_reset_pin(GPIOPin *reset_pin) {
  this->reset_pin_ = reset_pin;
}

void RadioTransceiver::set_irq_pin(InternalGPIOPin *irq_pin) {
  this->irq_pin_ = irq_pin;
}

void RadioTransceiver::set_busy_pin(GPIOPin *busy_pin) {
  this->busy_pin_ = busy_pin;
}

void RadioTransceiver::set_rx_gain_mode(RxGainMode mode) {
  this->rx_gain_mode_ = mode;
}

void RadioTransceiver::set_rf_switch(bool enable) {
  this->rf_switch_ = enable;
}

void RadioTransceiver::set_tcxo(bool enable) {
  this->has_tcxo_ = enable;
}

bool RadioTransceiver::wait_busy(uint32_t timeout_ms) {
  if (this->busy_pin_ == nullptr) {
    return true;  // No BUSY pin configured, assume ready
  }

  uint32_t start = millis();
  while (this->busy_pin_->digital_read()) {
    if (millis() - start > timeout_ms) {
      ESP_LOGE(TAG, "BUSY pin timeout after %" PRIu32 " ms", timeout_ms);
      this->mark_failed();
      return false;
    }
    delayMicroseconds(100);  // Small delay to avoid busy-spinning
  }
  return true;
}

void RadioTransceiver::reset() {
  if (this->reset_pin_ == nullptr)
    return;
  this->reset_pin_->digital_write(0);
  delay(5);
  this->reset_pin_->digital_write(1);
  delay(5);

  // Wait for BUSY to go low after reset (no-op if busy_pin not configured)
  this->wait_busy(100);
}

void RadioTransceiver::common_setup() {
  if (this->reset_pin_ != nullptr) {
    this->reset_pin_->setup();
  }
  this->irq_pin_->setup();
  if (this->busy_pin_ != nullptr) {
    this->busy_pin_->setup();
  }
  this->spi_setup();
}

uint8_t RadioTransceiver::spi_command(uint8_t command,
                                      std::initializer_list<uint8_t> data) {
  this->wait_busy();

  this->delegate_->begin_transaction();
  auto rval = this->delegate_->transfer(command);
  for (auto byte : data)
    rval = this->delegate_->transfer(byte);
  this->delegate_->end_transaction();
  return rval;
}

void RadioTransceiver::spi_read_frame(uint8_t command,
                                      std::initializer_list<uint8_t> data,
                                      uint8_t *buffer, size_t length) {
  this->wait_busy();

  this->delegate_->begin_transaction();
  this->delegate_->transfer(command);
  for (auto byte : data)
    this->delegate_->transfer(byte);
  for (size_t i = 0; i < length; i++)
    *buffer++ = this->delegate_->transfer(0x55);
  this->delegate_->end_transaction();
}

void RadioTransceiver::dump_config() {
  ESP_LOGCONFIG(TAG, "Transceiver: %s", this->get_name());
  LOG_PIN("  Reset Pin: ", this->reset_pin_);
  LOG_PIN("  IRQ Pin: ", this->irq_pin_);
  if (this->busy_pin_ != nullptr) {
    LOG_PIN("  BUSY Pin: ", this->busy_pin_);
  }
  ESP_LOGCONFIG(TAG, "  RX Gain: %s",
                this->rx_gain_mode_ == RX_GAIN_BOOSTED ? "Boosted" : "Power Saving");
  if (this->rf_switch_) {
    ESP_LOGCONFIG(TAG, "  RF Switch: DIO2");
  }
  if (this->has_tcxo_) {
    ESP_LOGCONFIG(TAG, "  TCXO: DIO3");
  }
}
} // namespace wmbus_radio
} // namespace esphome
