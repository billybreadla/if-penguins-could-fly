# Lachlan's Voice Lines — Recording Guide

The game plays real recordings of Lachlan calling the action, radio-chatter
style. Drop files into the `audio/` folder with these **exact** filenames.
`.mp3` is preferred; `.m4a` (what iPhone Voice Memos exports) also works —
the game probes `audio/<name>.mp3` first, then `.m4a`.

Record one line per file, keep each under ~3 seconds, and leave about half a
second of quiet at the start so nothing gets clipped.

## Files to record

| File | When it plays | Suggested script |
|------|---------------|------------------|
| `story_1.mp3` | Flight-log page 1 turns | "Tower to Penguin One... penguins can't fly. Nobody told THIS pilot. Buckle up!" |
| `story_2.mp3` | Flight-log page 2 turns | "Penguin One, the Flying Fish Festival needs you! One tiny plane... one VERY determined penguin." |
| `story_3.mp3` | Flight-log page 3 turns | "Your mission: thread the golden rings, grab those fish, and watch out for Captain Albatross!" |
| `boss_here.mp3` | A boss battle begins | "Uh oh — Penguin One, BIG BOGEY on your tail! It's boss time!" |
| `boss_down.mp3` | The boss crashes | "Direct hit! Boss down! Great flying, Penguin One!" |
| `world_clear.mp3` | Right after the boss falls | "Tower to Penguin One — world cleared! You're a legend! Headed home for fish snacks." |
| `new_best.mp3` | New high score on game over | "WOW! New best score ever! Everybody dance!" |

## How to record on an iPad/iPhone

1. Open **Voice Memos**, hit record, say the line (a few takes are fine!).
2. Tap the recording → share → **Save to Files** (or AirDrop to the computer).
3. Rename it to exactly one of the filenames above — keep the `.m4a`
   extension, or convert to `.mp3` if you like.
4. Put it in this game's `audio/` folder. That's it — no code changes needed.

Notes:
- A missing file is totally fine: the game stays silent for that moment until
  the recording shows up.
- Each line can't spam — the same line won't replay within 4 seconds.
- Lines respect the speaker-button mute in the top-right corner.
