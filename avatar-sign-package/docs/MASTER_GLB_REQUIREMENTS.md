# Master GLB Requirements

Expected deployment file:
`frontend/public/models/louise_signs_master.glb`

It contains the Louise mesh/skeleton and named prototype educational gesture
actions. Action playback approval and language validation are intentionally
tracked separately in the manifest.
Action names must exactly match IDs in `manifest/signs.json`.

Do not create a fake master GLB by renaming the old broken procedural asset.
Prototype actions must pass technical checks. They can only be promoted from
`needs_validation` to `validated` after qualified language review.
