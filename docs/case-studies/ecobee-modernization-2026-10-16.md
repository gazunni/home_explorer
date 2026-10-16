# Home Explorer — Ecobee Automation Modernization Case Study

**Case ID:** HE-CASE-ECOBEE-2026-10-16  
**Recorded:** October 16, 2026  
**Home Explorer version at observation:** v0.20.0 (read-only)  
**Status:** Actual HA configuration changed by homeowner; static review and limited live event tests; full temperature-cycle validation pending.  
**Purpose:** Durable engineering reference for future Home Explorer Automation Modernization / Control Authority Intelligence, not a claim that Home Explorer made the changes.

## 1. The homeowner's actual objective

Reduce a group of six long-lived Home Assistant Ecobee automations to a smaller, more understandable set **without losing useful behavior**. In parallel, correct two observed operational problems: (a) a 16:00–21:00 weekday shutdown could cancel an intentional high-temperature comfort exception, and (b) the off-hours Alexa warning announced when the thermostat was in Heat mode, although it was meant to warn about electricity-intensive A/C cooling mode. An eight-month wait for warm weather was not acceptable as the sole verification plan.

Homeowner context (explicitly stated): electricity price transitions at approximately 07:00 and 23:00; cheaper overnight electricity motivates cooling at night and daytime fan use. At temperatures **above 80°F**, comfort of people and pets takes priority. The exception cools toward **77°F**, then shuts Ecobee fully **off during the restricted daytime window**. Ecobee eco+ programs can alter behavior; manual overrides are occasionally needed. Homeowner manually selects Heat versus Cool for seasonal operation. No claim is made that Home Explorer can inspect internal eco+ schedules or reliably attribute every thermostat transition.

## 2. Original six configurations (as shown in homeowner YAML screenshots)

| Original alias | Trigger and constraints | Action/role |
|---|---|---|
| `Ecobee - Lower Temperature` | Weekdays at `23:05:05` | `climate.turn_on`, select `cool`, set 73°F |
| `Turn off Ecobee During Weekdays` | Weekdays at `06:55:00` | `climate.turn_off` |
| `Ecobee - Turn Off Between 16:00 and 21:00 Monday to Friday` | `climate.turned_on`; weekdays 16:00–21:00 | `climate.turn_off`, originally regardless of high-temp exception |
| `Ecobee - Turn off Thermostat` | `climate.started_cooling` sustained 8 minutes, weekdays 16:00–21:00; target temperature below 78°F for 2 minutes | `climate.turn_off` |
| `Ecobee - Turn on A/C if Above 80 Degrees F` | `sensor.ecobee_current_temperature` crossing above 80°F; specified weekday overnight-spanning time window (`after 16:00`, `before 06:50`) | Turn on, select Cool, set 77°F |
| `Ecobee - Turned On during Off Hours` | `climate.turned_on` for 5 minutes; weekdays 07:00–21:00 | Alexa `script.announce_with_volume` warning; failed to discriminate Heat from Cool |

**Observed concrete conflict:** high-temperature automation could select Cool, while the 16:00–21:00 auto-shutoff detected the turn-on and turned Ecobee back off. Homeowner independently confirmed this was a real issue, not just an inferred overlap.

**Operational mismatch:** prior warning notified on any thermostat On state, including Heat. Homeowner wants a **proactive Cool-mode** warning, not compressor-on-only, and no warning for cooling intentionally started by the above-80°F exception.

**Preservation note:** the old 80°F trigger was a *threshold crossing* with a time condition; this may miss already-hot cases or other windows. The later replacement uses periodic evaluation as well. Do not assume old and new configurations are exactly behaviorally equivalent.

## 3. Intended design and implementation

### End state: three active Ecobee automations

1. **`Ecobee - Energy Management`** — consolidated weekday rate schedule and shutdown rules. Initial four triggers and `choose` branches: 06:55 shutoff; 23:05:05 cooling set to 73°F; 16:00–21:00 unexpected-turn-on restriction; 16:00–21:00 eight-minute actual-cooling restriction with existing sub-78°F target criterion. Added explicit check `input_boolean.ecobee_comfort_override == off` to suppress normal shutdown during a comfort exception. Added season gating and selective Cool-mode gating to prevent winter Heat shutdown.
2. **`Ecobee - Comfort override 80 to 77`** — monitors above-80°F activation and 77°F recovery via threshold triggers, five-minute polling, and HA-start event; uses helper to remember the exception through 79/78°F readings. Its observed `choose` branches set helper On, set Ecobee to Cool and 77°F, then when recovery condition is satisfied, shut down Ecobee if in Cool mode during configured weekday restriction and clear helper. Added `ecobee_cooling_season == on` as a top-level condition. **Full runtime 80→77°F sequence untested.**
3. **`Ecobee - Unexpected cooling mode during expensive hours`** — warn after 5 minutes in `cool` mode (not merely `hvac_action: cooling`), weekdays 07:00–21:00; extra 07:05 trigger for persistent morning Cool mode; checks comfort helper Off and cooling season On; sends existing Alexa announcement script. **Actual warning pathway with these updated conditions not yet live-tested.**

### Helpers

- `input_boolean.ecobee_comfort_override`: remembers a homeowner-approved high-temperature cooling exception until 77°F recovery. Distinct from real HVAC activity; must be reconciled after restart and manual/eco+ changes.
- `input_boolean.ecobee_cooling_season`: remembers that HVAC is being managed for cooling season *even while Ecobee is Off* for electricity savings. **Off is not equivalent to heating season**.

### How seasonal selection was incorporated without adding a fourth active automation

An extra `Ecobee - Automatic Cooling Season` automation was briefly created as a draft and then left disabled after integrating its intended behavior into the consolidated Energy Management automation. Two HA **state** triggers were added (`climate.ecobee` `to: cool` and `to: heat`) and two `choose` branches:

- State changes to Cool → turn `ecobee_cooling_season` On.
- State changes to Heat → turn `ecobee_cooling_season` Off.
- State changes to Off → leave season helper unchanged.

**Exact trigger identifier caveat:** visual editor displayed aliases `cooling_selected`/`heating_selected`; in trace YAML they had generated internal IDs such as `generated-n1wW` / `generated-JeXM`. Traces showed the correct `choose` branches executing. Home Explorer should not conflate a UI alias with stable automation trigger `id` unless source confirms it.

**Meaningful unresolved policy issue:** a state transition to Cool can come from a manual change **or from Home Assistant/equipment/eco+**; the event alone does not prove the homeowner changed seasons. Conversely, moving to Off retains previous season state. Season helper can become stale if homeowner changes intent while Ecobee remains Off. This is an important candidate for state-authority review and user guidance, not proof of a bug in the observed mode tests.

## 4. Change and verification record (October 16, 2026)

| Stage | What happened | Evidence/status |
|---|---|---|
| Initial investigation | Six automation YAML screenshots supplied. Above-80°F cancellation and winter Alexa false-positive discussed. | Homeowner confirmed both operational pain points. |
| Comfort exception | Draft controller and warning were created in HA. First helper name accidentally produced double-prefixed entity ID; homeowner corrected it to `input_boolean.ecobee_comfort_override`. | Correct entity rendered in condition; old unknown-entity error disappeared. |
| Existing rules guarded | Homeowner added helper-Off conditions to the original 16:00–21:00 shutoff, eight-minute shutdown, and 06:55 shutdown. | Screenshots showed conditions present. |
| New pair enabled | Old high-temp and old Alexa warning disabled; new controller and cooling warning enabled. | Automations list/screenshots. |
| Controller idle trace | Five-minute run at 11:05 AM; `Choose: No action executed` and completed in 0.00 sec. | Confirms scheduling and non-action in current conditions only. |
| Consolidation | One Energy Management automation created with four original responsibilities and four `choose` branches. Seasonal Cool/Off and cooling-season helper checks added across branches. | Four branches and conditions shown in screenshots. |
| Cooling season helper | `input_boolean.ecobee_cooling_season` created, initially Off, also added to controller and warning. | Helper settings and automation screenshots. |
| Mode synchronization integrated | Two state triggers and `choose` branches added to Energy Management, resulting in **six triggers / six `choose` branches**. Separate Automatic Cooling Season automation left disabled. | Screenshots of both branches. |
| Heat live test | Homeowner switched Ecobee to Heat ~12:15 PM. HA created `unexpected_on` trace and distinct `heating_selected` trace; `choose` branch called helper Off. | Trace shows branch success. Helper remained Off; last-change timestamp indicated this was *not* a proven On→Off transition. |
| Cool live test | Homeowner selected Cool ~12:20:52 PM. `cooling_selected` trace and branch successful; helper observed On. | Confirmed actual Off→On helper transition. |
| Cool→Off test | Homeowner switched thermostat Off. Cooling season helper stayed On; no matching `heating_selected`/`cooling_selected` trace. | Expected and observed; Off preserves cooling-season memory. |
| Automation inventory | Home Explorer **v0.20.0** screenshot at ~12:39 PM: 323 registered; 190 displayed; 51 sense detections; 31 disabled registrations; 97 with no visible entities; **78 automations, 71 enabled, 7 disabled, 78/78 checked, 35 privacy filtered**, 20 overlap candidates, 4 review findings, 6 confirmed dependency links. | Point-in-time snapshot; counts not asserted to be a guaranteed immediate reflection of subsequent deletions or all HA configurations. |

## 5. Observed configuration state at last visible automation list

- Three replacement Ecobee automations enabled: Energy Management, Comfort override 80 to 77, Unexpected cooling mode during expensive hours.
- Six original Ecobee automations disabled and available for rollback at the time of list screenshot.
- A seventh disabled draft `Ecobee - Automatic Cooling Season` existed. User discussed deleting originals after a backup; **no later screenshot in this record verifies deletion**, so do not claim deletion occurred.
- Mode state observed: Cool→helper On, Cool→Off leaves helper On, Heat trigger executes helper-Off branch.
- Comfort exception: no live temperature crossing test; HVAC/equipment and Ecobee eco+ behavior not validated.

## 6. Risks, edge cases, unresolved questions

1. **High-temperature safety and intended season**: the top-level cooling-season gate suppresses controller during heating season; whether an extreme warm day in the heating season should still trigger an alert or exception is a homeowner policy decision. The override is a comfort strategy, **not a certified pet/life-safety protection**.
2. **Cool-mode control authority**: automatic programmatic switch to Cool can mark `ecobee_cooling_season` On; a user-invoked Cool transition is not distinguishable from another automation by a simple state trigger.
3. **Off-state seasonal ambiguity**: Off is deliberately permitted in summer; using Off to determine heating season would break overnight restart. Yet an Off thermostat followed by seasonal change without a Heat/Cool selection cannot be inferred.
4. **Winter startup and stale helper**: no verified startup reconciliation for `ecobee_cooling_season`; availability and stale values require consideration.
5. **Concurrent triggers**: real mode and turned-on events can be observed in the same second. The `mode: queued` Energy Management automation, action ordering, and helper state transitions deserve stress testing. Treat automation aliases/IDs and simultaneous traces carefully.
6. **Overnight cooling restart**: selecting Off before overnight and requiring season On allows restart; merely requiring `climate.ecobee == cool` would fail. The cooling-season helper is a solution with its own state-management costs.
7. **Alert semantics**: alert should target thermostat set to Cool, irrespective of compressor actually running, and only when comfort helper Off and cooling season On. The 07:05 special-case trigger checks state at that time; exact five-minute persistence across other temporal edges deserves review.
8. **Electricity schedule scope**: actual Ontario tariff may include more complex periods; this exercise **preserved homeowner's existing times** and did not verify rate tables or optimize tariffs.
9. **Old/new semantic differences**: e.g., new afternoon immediate shutdown explicitly requires Cool rather than any On state; season gating adds new behavior; polling and override 77°F release alter previous logic. These are deliberate/proposed changes rather than bit-for-bit refactors.
10. **Recovery at exactly 77°F**: screenshots show a numeric-state threshold crossing **below 77.01**, an implementation trick to approximate 77°F with reported sensor granularity. Verify sensor precision and edge behavior before claiming exact equality semantics.
11. **No HA service control by Home Explorer**: manual homeowner edits were done in HA. Home Explorer remained read-only throughout.

## 7. Proposed Home Explorer feature requirements (not implemented in v0.20.0)

**Modernization Intelligence** should:

- Map an *automation family* by actual HA entity/device relationships, action targets, schedules, trigger IDs, `choose` paths, and state/condition logic; distinguish config references from actual appliance and homeowner intent.
- Identify a **specific action conflict**, e.g. `turn_on`→`turn_off` for the same `climate.ecobee` during 16:00–21:00, while distinguishing a **deliberate exception** from an accidental collision. Use evidence with explicit uncertainty and impact; do not simply label any multiple references a conflict.
- Separate **cooling mode** (`climate.ecobee == cool`) from **actual compressor cooling** (`hvac_action`), and thermostat On events from Cool state changes. Show how trigger families overlap in time.
- Support modernization suggestions that retain branch-specific constraints and warn when consolidation changes `mode`, timing, persistence, priority, or alert logic. A lower count must not be treated as success on its own.
- Represent **intent/priority** as homeowner-confirmed annotations, e.g. energy saving, comfort threshold (80→77°F), pet comfort, alert-only, seasonal control. Never deduce safety priority with certainty from names alone.
- Model *stateful helpers* and producer/consumer automations; visualize conditions and recovery transitions, persistence across Off, restart, and seasonal changes.
- Surface **control authority ambiguity** among HA automations, Ecobee's own schedule/eco+ programs, thermostat/manual changes. Attribution is unavailable unless trustworthy traces/logs support it.
- Provide a **read-only hypothetical test plan** or offline simulator (no live service calls): at 81°F expect helper On and request Cool→77°F; at 79°F stay active; at 77°F release and turn Off during restriction; at Heat avoid A/C intervention; Cool while override off during warning hours ⇒ warn; Off from Cool retains cooling season. Mark which results are simulated vs actually observed.
- Respect security design: automation secrets, internal identifiers, precise schedule/threshold data should not be exposed in general browser summary payloads without a deliberate vetted privacy model. The user opted to show screenshots and YAML in this chat; that does **not** authorize exposing full HA automation YAML broadly in Home Explorer.
- Produce **concrete navigation and reversible change plans**, showing originals vs replacements, `enabled` flags, backup/rollback readiness and what remains untested. Never directly mutate devices or automations in the read-only application.
- Make versioned change history / observed-inventory snapshots possible, since registered automation count changed during cleanup and other household modernization. Snapshot differences alone don't prove functional coverage.

### Proposed acceptance scenarios for a future Home Explorer prototype

| Scenario | Expected inference/output |
|---|---|
| Two rules turn same thermostat on/off in same weekday window | Flag grounded potential conflict with exact relevant conditions, then seek trace evidence and homeowner intent. |
| >80°F comfort exception conflicts with time shutdown | Prioritize homeowner-confirmed exception in recommended design; indicate original conflict as confirmed by homeowner. |
| Heating mode triggers off-hours cooling warning | Explain missing Cool-only condition and report actual owner-observed false positive. |
| Homeowner combines four into one `choose` tree | Show before/after semantic mapping, changes in timing and guards, not merely count reduction. |
| Cool→Off while cooling-season helper On | Do **not** infer winter; preserve stateful season intention. |
| Cool selected by automation vs manually | Flag attribution as unknown without evidence. |
| Simulated 81→79→77°F | No real service calls; separate simulated outcome from live tests. |
| Sensitive automation YAML | Browser overview sanitized; never reveal private entities, identifiers, schedules or actions inadvertently. |

## 8. Suggested next project step

Preserve this case as the **first design fixture / regression scenario** for a future Home Explorer Automation Modernization Intelligence phase. Before writing code, obtain a *sanitized, consented* sample of the relevant flow structures (without raw notification targets or other sensitive payloads), define expected model outputs, and then build an offline test fixture. Home Explorer v0.20.0 should not be described as already having this intelligence.

**Evidence boundary:** This reference is based on the homeowner's screenshots, stated intent and interactions in this conversation. No direct HA database access, trace export, eco+ event attribution, or completed live 80°F→77°F cooling cycle was available. Configuration screenshots support installation facts; only actual traces support executed-branch facts.