# Clip folder

Put validated, same-rig animation assets here using the exact IDs in `manifest/signs.json`.

Examples:
- `SUBTRACTION.glb`
- `EQUATION.glb`
- `BALANCE.glb`
- `NUMBER_3.glb`

For production, it is better to merge approved same-rig actions into one master:
`frontend/public/models/louise_signs_master.glb`

Do not treat the presence of a file as language validation. Update the manifest
`validation_status` to `validated` only after reviewer/interpreter approval.
