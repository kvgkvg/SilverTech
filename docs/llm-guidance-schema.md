# LLM Guidance Schema

The backend accepts only this shape:

```json
{
  "intent": "string",
  "steps": [
    {
      "step_number": 1,
      "instruction_vi": "string",
      "button_id": "string",
      "expected_result": "string"
    }
  ],
  "safety_note": "string|null"
}
```

Every `button_id` must exist for the selected template. Invalid output is
rejected and logged.
