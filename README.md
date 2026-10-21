Wireless M-Bus receiver for ESPHome, trimmed down to a single setup: an M5Stack Unit C6L (ESP32-C6 + SX1262) reading Sensus PolluCom F heat meters. Based on [SzczepanLeon/esphome-components](https://github.com/SzczepanLeon/esphome-components) version 5, which in turn builds on Kuba's [fork](https://github.com/IoTLabs-pl/esphome-components) and the [wmbusmeters](https://github.com/wmbusmeters/wmbusmeters) parser.

Tested against ESPHome 2026.10.0 with the ESP-IDF framework.

## Components

- `wmbus_radio` drives the SX1262 transceiver and passes received frames to the meters.
- `wmbus_meter` decodes frames for one meter and feeds `sensor` / `text_sensor` entities.
- `wmbus_common` is the wmbusmeters library. Only the `pollucomf` driver is kept.

A complete configuration for the M5Stack Unit C6L is in [wm-bus-zentrale.yaml](wm-bus-zentrale.yaml).

```yaml
external_components:
  - source: github://jeremiahpslewis/esphome-components@main
    components: [wmbus_radio, wmbus_meter, wmbus_common]
```

## Radio

```yaml
spi:
  clk_pin: GPIO20
  mosi_pin: GPIO21
  miso_pin: GPIO22

wmbus_radio:
  radio_type: SX1262
  cs_pin: GPIO23
  irq_pin: GPIO7
  busy_pin: GPIO19
  reset_pin: GPIO4
  rx_gain: BOOSTED
  rf_switch: true
  has_tcxo: true
  on_frame:
    - then:
        - logger.log:
            format: "RSSI: %ddBm T: %s"
            args: [ frame->rssi(), frame->as_hex().c_str() ]
```

| Option | Required | Default | Description |
|---|---|---|---|
| `radio_type` | yes | | Must be `SX1262` |
| `cs_pin` | yes | | SPI chip select pin |
| `irq_pin` | yes | | DIO1, raised when a sync word is received |
| `busy_pin` | no | | BUSY pin, recommended for reliable timing |
| `reset_pin` | no | | Reset pin, may sit on an I/O expander |
| `rx_gain` | no | `BOOSTED` | `BOOSTED` (better sensitivity) or `POWER_SAVING` |
| `rf_switch` | no | `false` | Set to `true` if DIO2 controls the RF switch |
| `has_tcxo` | no | `true` | Set to `false` if DIO3 does not drive an external TCXO |
| `on_frame` | no | | Automation run for every received frame, with `frame` in scope. Set `mark_as_handled: true` to suppress the "not handled" warning for frames it consumes. |

The receiver listens on 868.95 MHz for T1 and C1 telegrams. Frames longer than 255 bytes are streamed out of the SX1262 buffer while they are still arriving.

## Meter

```yaml
wmbus_meter:
  - id: heat_meter
    meter_id: 0x12345678
    type: pollucomf
    key: 00112233445566778899AABBCCDDEEFF
    mode:
      - T1
      - C1
```

| Option | Required | Default | Description |
|---|---|---|---|
| `meter_id` | yes | | Meter address. Write it with a `0x` prefix: the ID printed on the meter is hexadecimal, and a bare number is read as decimal. |
| `type` | yes | | Driver name, `pollucomf` |
| `key` | no | | AES key as 32 hex digits, or a 16 character ASCII string |
| `mode` | no | `Any` | Link modes to accept: `T1`, `C1` or `Any` |

## Sensors

```yaml
sensor:
  - platform: wmbus_meter
    parent_id: heat_meter
    field: total_kwh
    name: Heat energy
    device_class: energy
    state_class: total_increasing

text_sensor:
  - platform: wmbus_meter
    parent_id: heat_meter
    field: status
    name: Heat meter status
```

`field` is a wmbusmeters field name followed by its unit. The pollucomf driver provides `total_kwh`, `total_m3`, `power_kw`, `flow_m3h`, `forward_c`, `return_c`, `target_kwh`, `target_m3`, `forward_max_c`, `return_max_c` and `flow_max_m3h` as numbers, and `status` and `target_date` as text. Every meter also has `rssi_dbm` (signal strength of the last telegram) and `timestamp` / `timestamp_zulu`. If `unit_of_measurement` is not set, it is derived from the unit suffix.

## Stack size

Telegrams are decoded in the main loop task, and wmbusmeters needs more stack than ESPHome's default of 8 KB. Raise it in the `esp32` section:

```yaml
esp32:
  variant: esp32c6
  framework:
    type: esp-idf
    advanced:
      loop_task_stack_size: 32768
```

## Updating wmbusmeters

To pull newer wmbusmeters code run:
```bash
git subtree pull --prefix components/wmbus_common https://github.com/wmbusmeters/wmbusmeters.git <REF> --squash
```
Upstream changes to drivers that were deleted here show up as modify/delete conflicts; resolve them by keeping the deletion.
