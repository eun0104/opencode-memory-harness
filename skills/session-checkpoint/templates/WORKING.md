# Working State

<!-- Live session state. Rewritten in full by session-checkpoint; closed by session-end.
     After compaction, read this file before any other action.
     Keep it under ~1,200 tokens. Point to files; do not copy them. -->

Updated: YYYY-MM-DD HH:MM · Session NNN · Checkpoint K

## Goal

<The current leaf of the plan, in one or two sentences.>
Plan item: `<plan-file-path>` → <heading or item ID>

## Gates

- [ ] G1 <acceptance criterion>
  CHECK: `<command to run>`
  EXPECT: <what the output must show>
- [x] G2 <acceptance criterion>
  EVIDENCE: <measured value, output excerpt, or file path — observed, not assumed>

## Next action

<The exact next step, specific enough to start without re-reading anything else.>

## Decisions this session

- [decision] <chose X over Y because Z>

## Do not repeat

- <tried X; it failed because Y>

## In flight

- <file edited but not yet verified, or `none`>

## Open questions

- <unresolved question, or `none`>
