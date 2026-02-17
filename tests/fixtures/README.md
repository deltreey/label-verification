Place OCR test images here (png/jpg/tif/bmp). For each image, add a JSON file
with the same basename to define expectations. Example:

{
  "text_contains": ["PRODUCT NAME", "750 ML"],
  "allowed_font_weights": ["regular", "bold"],
  "font_weight_by_text": {"PRODUCT NAME": "bold"},
  "quality": {
    "brightness": {"min": 0.2, "max": 0.8},
    "skew_degrees": {"min": -2.0, "max": 2.0}
  }
}
