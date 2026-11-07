# OpenFn workflow diagram: style sheet (validated)

**Source:** the 9 final `.bpmn` files and 3 `.png` previews in `FLUJOS_MAP/propuestas/` (Demo 1, 2, 3 and the indicator diagrams). **Reference style: Demo 3** (`demo3-propuesta.bpmn` and `demo3-propuesta.png`).

## 1. Page layout (top to bottom)

| Element | Rule | Seen in |
|---|---|---|
| Legend | Top-left. One box per color, 230 × 24, stacked every 30 px, filled with its color, black rounded border, label inside. | All diagrams |
| Title | Below the legend, left-aligned. Format: `<Workflow short name> - <name> (<variant>)`, for example "Demo 3 - Actualiza contacto (propuesta)". Text only, no box. Very large font (about 5-6× the normal text). | Demo 3, indicators |
| Pool | Below the title. One pool per workflow, with its long name written vertically on the left band (30 px wide). | All |
| Lanes | Horizontal, one per system, label written vertically on the left. | All |

## 2. Lanes

| Rule | Seen in |
|---|---|
| Order: the system that **starts or feeds** the flow on top (for example Punto Solidario, SIUBEN Levantamiento), then **"OpenFn Automatización"**, then the target systems, then **"OpenFn Collections"** at the bottom when indicators are used. | All |
| The OpenFn lane is the tallest (about 500 px); the others about 140-200 px. | All |
| The lane names are the systems' real names. A lane appears when a step calls that system, **or when the user says that system is an actor in the process** (it may stay empty, like "Supérate" in Demo 1 and Demo 2). | All |

## 3. Shapes

| Shape | Rule | Size |
|---|---|---|
| Start event | In the OpenFn lane. **Timer** icon for cron, with the schedule as label ("Cada 60 minutos (minuto 10)"). **Message** icon for webhook ("Webhook"). | 36 × 36 |
| Task (step) | Rounded box, black border, label = the exact step name (or its readable form). | 150 × 70 |
| Spacing | Tasks in a straight line, about 200 px apart, left to right in the real order. | |
| Parallel gateway | When one step leads to two steps that run at the same time (for example SMS and WhatsApp). | 50 × 50 |
| End event | Thick black border, **green fill**, label under it ("Ciudadano notificado", "Caso creado en SIUBEN"). One at the end of each branch, plus one in the lane of each external system that receives a result. | 36 × 36 |
| Data object (document) | In the source system's lane, for the data the workflow reads ("Solicitudes nuevas (PS)"). | 36-40 × 50 |
| Data store (cylinder) | In the "OpenFn Collections" lane, blue. | 50 × 50 |

## 4. Lines

| Line | Rule |
|---|---|
| Sequence flow | Solid line with filled arrow, between events, tasks and gateways in the OpenFn lane. |
| Condition label | Text on the line when the edge has a condition, for example "Siempre". |
| Data association | **Dotted** line with open arrow: from the data object to the step that reads it, and from a step to the end event in the external system's lane (for example "Crea caso en SIUBEN" → "Caso creado en SIUBEN"). |

## 5. Colors

| Color | Hex | Used for |
|---|---|---|
| Purple | `#E1E0FF` | Tasks that call **institutional APIs** (PS, SIUBEN…) |
| Orange | `#FDD9A5` | Tasks that call **notification APIs** (SMS, WhatsApp) |
| Green | `#C3F5C5` | **Comments and questions** boxes, and **end events** |
| Blue | `#BDE3FF` | **New steps for indicators** and the Collections data store (only in indicator diagrams, with a 4th legend item "Nuevo: indicadores") |
| Black | `#000000` | All borders and lines |

## 6. Text boxes (annotations)

| Type | Rule |
|---|---|
| API endpoint | Above each task that calls an API, no fill, bracket on the left: `METHOD /path`, for example "GET /PersonaTelefono/GetTelefonosFecha". |
| Suggestions | Green box, first line "[FC] Sugerencias", then numbered items "FC15. …". |
| Questions | Green box, first line "@MAP - Preguntas", then numbered items "P12. …". |
| Data used | Green box in the source lane listing the fields the workflow uses ("Datos que usa de PS…"). |
| Assumptions | Green box starting with "Supuesto: …" (indicator diagrams). |

## 7. Decisions

1. **The `.bpmn` cannot carry everything.** Only tasks, end events and the data store keep their colors in the `.bpmn`. The legend colors, the green fill of comments and the large title only appear in the `.png`. That is accepted: the `.png` is the visual reference to follow when finishing the diagram in Lucid. Both files must always be generated from the same drawing, so they match.
2. **Reference style: Demo 3.** The Demo 1 image (exported from Lucid after manual edits) is not the reference.
3. **Extra lanes for actors:** besides the systems found in the code, add a lane for any actor the user names as part of the process, even if no step uses it yet.
