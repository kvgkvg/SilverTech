# Failure Flow Cases

- Glare: expect `reduce_glare` or `rescan`.
- Blur: expect `rescan` or `move_closer`.
- Partial panel: expect `scan_wider`.
- Wrong brand: expect `manual_select`.
- Low confidence: expect no highlight.
- Invalid `button_id`: expect backend rejection.
