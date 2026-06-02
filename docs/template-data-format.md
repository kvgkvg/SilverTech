# Template Data Format

Each official template must include:

- `brand`
- `appliance_type`
- `template_code`
- `template_image_url`
- optional `logo_bbox`
- optional `panel_bbox`
- `version`
- `status=official`
- buttons with stable `button_id`, label, Vietnamese name, function description,
  template-coordinate bounding box, optional polygon, and button type.

Runtime guidance must use only official templates and valid `button_id` values.
