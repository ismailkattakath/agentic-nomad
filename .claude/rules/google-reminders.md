# Trip reminders and prep — follow the `workspace-gtd` skill; travel specifics only here

The operator's work-life system (GTD on Tasks + Calendar, eight Workspace apps, no alarms,
employer as an adapter) is the **`workspace-gtd@kattakath`** plugin, enabled for every
session by nix-config. This rule keeps only what is specific to trips. The research behind the
system is the operator's own write-up in Drive, not in this repo (`no-data-here.md`).

- **One Tasks list per trip** (e.g. "<Trip name> 2027"), subtasks for each paperwork step.
  The trip's actions never go into the general lists.
- **Paperwork deadlines** (arrival forms, visa windows): one Calendar event each, per
  `book-trip` step 9.
- **Travel day:** route steps and the fallback route in the Calendar event's description;
  popups on that real event, never a separate "alarm" event.
- **Documents:** the trip kit lives in Drive. The API cannot mark a file offline — never claim
  it is offline on the phone; the operator (or adb) marks the kit folder offline.
