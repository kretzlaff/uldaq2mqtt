# Uldaq2Mqtt

This project sends the current state of a digital input to an MQTT broker.

I use this project to send the state of my wall switches to [Home Assistant](https://www.home-assistant.io/).

## Supported Device

-   [USB-1024 Series](https://www.mccdaq.com/usb-data-acquisition/USB-1024-Series.aspx)
-   It might support similar devices, your mileage may vary

## MQTT Formating

The messages are published to the MQTT broker with the following formatting

```
uldaq2mqtt/<UniqueDeviceId>/<port>/<bit> = 0|1
```

## Usage
