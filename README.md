<p align="center">
  <img src="custom_components/aroma_s6/brand/icon@2x.png" width="112" height="112" alt="Aroma S6 icon">
</p>

<h1 align="center">SO Aroma Diffuser S6 for Home Assistant</h1>

<p align="center">Local Bluetooth control of the SO Aroma Diffuser S6 (bwj.diffuser.s6).</p>

[Русский](README.ru.md) · [MIT License](LICENSE)

## Controls

| Feature | In Home Assistant |
| --- | --- |
| Diffuser | Power, spray duration and interval between sprays |
| Ambient light | On/off and a color wheel |
| Light timer | Set a duration from 1 to 120 minutes, then start or cancel the countdown |
| Battery | Charge level and charging status |

The light timer switches off the ambient light and keeps the selected color for next time. It leaves the diffuser's spray mode alone. The controls can also be used in your own Home Assistant automations.

## Requirements

- SO Aroma Diffuser S6, model **bwj.diffuser.s6**, already paired with **Xiaomi Home**.
- Home Assistant 2026.3 or newer. Tested on Home Assistant Core 2026.11.
- A Home Assistant Bluetooth adapter within reach of the diffuser or an [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy/) with active connections enabled.
- Your diffuser's Bluetooth MAC address and 12-byte device token (24 hexadecimal characters).

### Find your device token

Run [Xiaomi Cloud Tokens Extractor](https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor) locally, sign in to your own Xiaomi account, and select the region where you paired the diffuser. Find the entry with model **bwj.diffuser.s6**. Use its **MAC** and **TOKEN** fields. For this model, the integration uses the 24-character **TOKEN**. The extractor lists a separate **BLE KEY** field.

If the MAC is missing, look for **bwj.diffuser.s6** in Home Assistant's Bluetooth advertisement monitor. Keep the token in your own installation and redact it from logs or screenshots you share. The integration uses Bluetooth after setup and makes no Xiaomi cloud requests.

## Install

**With HACS**

1. In HACS, open the three-dot menu and choose **Custom repositories**.
2. Paste this repository's URL and choose **Integration** as the type.
3. Download **SO Aroma Diffuser S6** and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration**. Select **SO Aroma Diffuser S6**, then enter the MAC address and device token.

**Manual**

Copy the folder **custom_components/aroma_s6** into **custom_components** under your Home Assistant configuration directory. Restart Home Assistant and add the integration as above.

## Use the light

In the diffuser's device page, click **Ambient light**, then the rainbow **Color** control. To switch it off after a delay, enter the number of minutes under **Light timer duration** and press **Start light timer**.

## Troubleshooting

- If the diffuser is unreachable, wake it with its physical button and try again. Some units can stop advertising when off on battery. With the unit on USB power, try again near the adapter or proxy.
- Close the diffuser page in Xiaomi Home if the phone holds the Bluetooth connection.
- If a setting fails to save, wait for the connection to recover before retrying. Only values confirmed by the device are shown as saved.
- The diffuser's LEDs have a limited color range, so the visible shade may differ from the color wheel.

This is a community integration for the S6. Other SO or Xiaomi diffuser models have not been tested.
