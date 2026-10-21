#pragma once
#include "esphome/components/spi/spi.h"
#include "esphome/core/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <cstdint>
#include <initializer_list>

#define BYTE(x, n) ((uint8_t)(x >> (n * 8)))

namespace esphome {
namespace wmbus_radio {

// RX Gain modes for SX1262
enum RxGainMode {
  RX_GAIN_BOOSTED,      // Better sensitivity, higher current
  RX_GAIN_POWER_SAVING  // Lower current, reduced sensitivity
};

class RadioTransceiver
    : public Component,
      public spi::SPIDevice<spi::BIT_ORDER_MSB_FIRST, spi::CLOCK_POLARITY_LOW,
                            spi::CLOCK_PHASE_LEADING, spi::DATA_RATE_1MHZ> {
public:
  virtual void setup() override = 0;
  void dump_config() override;

  // DIO1 goes high when the sync word has been received
  template <typename T>
  void attach_data_interrupt(void (*callback)(T *), T *arg) {
    this->irq_pin_->attach_interrupt(callback, arg, gpio::INTERRUPT_RISING_EDGE);
  }

  virtual void restart_rx() = 0;
  virtual int8_t get_rssi() = 0;
  virtual const char *get_name() = 0;

  // Read `length` bytes of the packet being received, starting at `offset`
  virtual bool read_in_task(uint8_t *buffer, size_t length, uint32_t offset) = 0;

  void set_reset_pin(GPIOPin *reset_pin);
  void set_irq_pin(InternalGPIOPin *irq_pin);
  void set_busy_pin(GPIOPin *busy_pin);
  void set_rx_gain_mode(RxGainMode mode);
  void set_rf_switch(bool enable);
  void set_tcxo(bool enable);

protected:
  GPIOPin *reset_pin_{nullptr};
  InternalGPIOPin *irq_pin_{nullptr};
  GPIOPin *busy_pin_{nullptr};
  RxGainMode rx_gain_mode_{RX_GAIN_BOOSTED};
  bool rf_switch_{false};  // Use DIO2 as RF switch control
  bool has_tcxo_{true}; // Use DIO3 as driver for temperature-compensated crystal oscillator

  void reset();
  void common_setup();

  // Wait for BUSY pin to go low (no-op if busy_pin not set)
  bool wait_busy(uint32_t timeout_ms = 100);

  // Command-based SPI operations, waiting for BUSY first
  uint8_t spi_command(uint8_t command, std::initializer_list<uint8_t> data);
  void spi_read_frame(uint8_t command, std::initializer_list<uint8_t> data,
                      uint8_t *buffer, size_t length);
};

} // namespace wmbus_radio
} // namespace esphome
