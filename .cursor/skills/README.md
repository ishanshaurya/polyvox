# Project skills (for Cloud Agents + Desktop)

Cursor **does not sync** Desktop `~/.cursor/skills/` into Cloud Agent VMs.

Skills here are **committed to the repo** so cloud runs can discover them from `.cursor/skills/`.

## Installed

| Skill | Invoke | Source |
|---|---|---|
| caveman | `/caveman` | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) (MIT) |
| grill-me | `/grill-me` | [mattpocock/skills](https://github.com/mattpocock/skills) (MIT) |
| grilling | (used by grill-me) | mattpocock/skills |
| handoff | `/handoff` | mattpocock/skills |
| handsoff | `/handsoff` | alias → handoff |
| improve-codebase-architecture | `/improve-codebase-architecture` | mattpocock/skills |
| improvecodebase | `/improvecodebase` | alias → improve-codebase-architecture |
| codebase-design | (used by architecture skill) | mattpocock/skills |

## Note for this cloud session

Skills added mid-run may not appear in the agent’s initial skill list until a **new** cloud agent starts on a revision that includes this folder. In the current session, ask the agent to `Read` `.cursor/skills/<name>/SKILL.md` and follow it.
