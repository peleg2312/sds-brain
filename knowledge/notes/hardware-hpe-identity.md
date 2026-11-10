# HPE servers: model, generation and which disk is which

- The reported names (XL420 = Apollo 4200 family, XL170r, XL190r, DL385) are enough to find documentation, not to
  choose firmware. Manuals and Redfish services depend on the **generation**: capture the system product name and
  generation, and never guess the iLO generation from a server name.
- Per server model, `environment.md` should hold: product / model, generation, CPU platform, iLO generation and
  firmware, system ROM, storage controller and its mode, drive model / firmware, network adapter / firmware. Serial
  numbers and management addresses stay out of notes.
- **OSD to physical drive**: an OSD id maps to a logical device, which maps to a physical drive and bay through
  controller / backplane information. A Linux name such as `sdX` can change and is not evidence for a replacement.
  If the controller hides physical disks, the hardware owner provides the verified mapping first.
- **Performance**: correlate errors, queueing, temperatures, power state and link evidence with the incident
  interval. Controller cache state, firmware issues and transport errors are different hypotheses; none follows from
  high disk utilization alone. No load-generating tests on failing media during an incident.
- Read access to iLO and the host only. Firmware downloads, controller mode changes, flashing, iLO resets and power
  cycles are for the hardware owner to run.

Library: hpe/ilo-redfish (iLOrest, Redfish concepts and services). Model-specific service guides are on HPE's support
site: add the exact guide under `docs/hpe/` when hardware work is planned.
