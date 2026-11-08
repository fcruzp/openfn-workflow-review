# lanes.json: what the reviewer gives for each workflow diagram

The program decides positions, sizes and colors (house style, Demo 3). The reviewer only gives the content. Run `rwo diagram WF1 <path to lanes.json>`.

```json
{
  "title": "Demo 3 - Actualiza contacto (propuesta)",
  "pool": "Demo 3 (propuesta): Actualización del contacto del ciudadano",
  "language": "en | es",
  "indicators": false,
  "lanes": ["Punto Solidario", "OpenFn Automatización", "SIUBEN"],
  "openfn_lane": "OpenFn Automatización",
  "start_label": "Webhook",
  "steps": {
    "<step id>": {
      "label": "Text inside the box (defaults to the step name)",
      "kind": "institutional | notification | indicator | internal",
      "endpoint": "POST /api/tramite",
      "result": {"lane": "SIUBEN", "label": "Contacto registrado en SIUBEN"},
      "reads": {"lane": "Punto Solidario", "label": "Teléfonos de contacto (PS)"},
      "writes_store": {"lane": "OpenFn Collections", "label": "indicadores-eventos"}
    }
  },
  "ends": {"<id of a last step>": "Ciudadano notificado"},
  "notes": [
    {"lane": "OpenFn Automatización", "near": "<step id>", "title": "[FC] Suggestions", "lines": ["FC01. ..."]},
    {"lane": "SIUBEN", "title": "@Client - Questions", "lines": ["P1. ..."]}
  ]
}
```

Rules checked by `rwo diagram`:

1. Every step of the workflow has an entry in `steps` (use the step ids from the workflow file); no unknown ids.
2. `openfn_lane`, and every lane used in `result`, `reads`, `writes_store` and `notes`, is one of `lanes`.
3. `kind` is one of the four values. Colors come from the kind: institutional = purple, notification = orange, indicator = blue.
4. Add a lane for every system the code calls, and for any actor the user names as part of the process, even if it stays empty.
5. Never invent steps, systems or arrows: the boxes and arrows come from the workflow file.
