# H200S camera reference parameters

The following factory defaults and ranges were read from this device. Actual values may vary with the device firmware or current settings. Manual exposure time and white balance usually cannot be set while their respective automatic modes are enabled. Exposure time is expressed in units of 100 microseconds.

## Parameter ranges and defaults {#parameter-ranges-and-defaults}

| Parameter | Range | Step | Factory default |
|---|---:|---:|---:|
| Brightness | -64–64 | 1 | 0 |
| Contrast | 0–100 | 1 | 37 |
| Hue | -180–180 | 1 | 0 |
| Saturation | 0–128 | 1 | 64 |
| Sharpness | 0–100 | 1 | 90 |
| Gamma | 100–500 | 1 | 300 |
| Gain | 0–128 | 1 | 64 |
| White balance | 2800–6500 K | 10 K | 4600 K |
| Exposure time | 1–10000 | 1 | 166, approximately 1/60 second |
| Backlight compensation | 0–2 | 1 | 1 |

## Dashboard and driver controls {#dashboard-and-driver-controls}

This table describes device/UVC values, not portable OpenCV ranges. In particular, the camera backend may translate `exposure` units; do not copy `166` unchanged across operating systems. Inspect driver readback and the actual image after setting a value, and verify unsupported or ineffective controls on the target system.

The dashboard exposes brightness, contrast, saturation, exposure and gain. It does not expose every item above or generic automatic-exposure/white-balance switches; configure automatic modes with device or operating-system tools. Preview rate controls display only; check capture rate and exposure separately.

See [arena and camera setup](./arena) and [localization and calibration](../guide/localization) for mounting, coverage and calibration.
