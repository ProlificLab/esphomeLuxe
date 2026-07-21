# Privacy and safety

- The red privacy LED and software microphone mute are visible controls, not a
  hardware power disconnect.
- Continuous listening always has a visible LED and five-minute timeout.
- Acoustic and video announcements are opt-in, local, allowlisted and rate
  limited. Facial identity is not announced.
- Do not enable a camera audio role without room consent and a retention review.
- Voice cannot directly disarm, unlock, reboot infrastructure or change Victron
  limits. Critical actions need bounded scripts and explicit confirmation.
- Never use voiceprints as authentication or commit API, Wi-Fi, camera or MQTT
  credentials.
