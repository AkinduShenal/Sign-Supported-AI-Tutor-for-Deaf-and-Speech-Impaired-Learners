# Legacy procedural avatar tooling

The runtime avatar path now uses the manifest-backed clip-library architecture in
`avatar-sign-package/` and expects one master file at:

`frontend/public/models/louise_signs_master.glb`

`create_sign_animations.py` is retained only because it contains earlier local
research work. It is deprecated and is not imported, executed, or required by
the backend/frontend runtime.
Do not use it to create or guess Sri Lankan Sign Language lexical motion. New
lexical clips must follow the package review workflow, match a manifest action
ID, and be marked `validated` before production playback.

The old `frontend/public/models/louise_tutor.glb` file is also retained for
reference and is no longer loaded by the tutor interface.
