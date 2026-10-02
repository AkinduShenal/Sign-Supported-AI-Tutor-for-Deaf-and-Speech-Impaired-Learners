# Technical Validation

The figures below originated in the supplied prototype package; they are not
human sign-language validation. A separate read-only reproducible audit is now
available at `tools/audit_master_motion.py`.

- GLB parsed as glTF 2.0 successfully.
- Embedded animation count: 22.
- File size: 9763852 bytes.
- Main-pose outward elbow failures: 0.
- SHA-256: `31fd3bbd41cf1cac8c808becd9fd285ba605e3981c721c5a4f1c822b4861b24e`

`prototype_pose_report.json` contains representative shoulder, elbow and wrist
positions for every animation.

The independent audit of the current master samples all keyframes and their
interpolation midpoints: 22 actions, no quaternion/endpoint/arm-length check
errors; maximum sampled elbow bend approximately 112.27 degrees. This does not
check mesh intersections, fingers, facial grammar or language meaning.

The browser regression also captures a contact sheet of all 22 action midpoints
for visual inspection. `BALANCE` and `BOTH_SIDES` share identical motion data in
the supplied asset; do not assume that separate labels establish different or
correct signs. Linguistic review remains outstanding for every lexical action.
