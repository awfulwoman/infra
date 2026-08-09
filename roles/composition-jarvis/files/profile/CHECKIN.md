# Check-in Prompts

## Handling new emails

- When a new email is received read the subject
- Ignore any emails that are spam or marketing
- If the subject indicates the email is relevant to the user then read the body for more context
- Do NOT mark the email as read
- If an email is time critical then immediately alert the user via Telegram
- If an email is related to a booking then:
  - look for a `.ics` attachment and add it to the users default calendar
  - if no `.ics` is present then use the body text to determine time, date and location before adding it to the default calendar
- If an email contains a task then ask the user via Telegram if they wish to create a reminder

## Idle Check-in

"Can I help you with anything else?"

## Handling calendar events

- Do not remind the user about calendar events - this is handled by the calendar app
