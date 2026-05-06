# Reaper115 Telegram bot UI kit

The crawler's user-facing surface is a Telegram bot that delivers magnet links and accepts a small set of slash commands.

## What's here

- `index.html` — iPhone frame, Telegram chat with @reaper115_bot
- `telegram-kit.css` — chat bubbles, message meta, command palette, inline buttons
- `chat.jsx` — the conversation tree (system + user + bot messages, slash command palette)

## Conversation modeled

Mirrors what the bot actually does in the codebase:

1. `/start` welcome card — what the bot does, how to subscribe
2. `/subscribe 新作品` confirmation
3. Auto-push of a new post — title, code, size, tags, magnet (mono), inline "Copy magnet" / "Mute thread" buttons
4. `/today` digest — list of 4 latest posts with deep links
5. `/help` — slash-command list

## How to read

Open `index.html` directly. The phone frame is real (starter component) — the chat content is the deliverable. Tap-targets aren't wired; this is a static fidelity reference for the bot's voice and bubble layout.
