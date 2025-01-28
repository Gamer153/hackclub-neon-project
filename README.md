# neon reminders
A reminders display on a RGB led board, controllable with MQTT.

MQTT commands:

- Add a reminder: Post a message to the `/add_reminder` topic. It can either be a random string (not starting with `{`), which will be directly using as a reminder (with color white), or a JSON object with the following schema: `{ text: string, color?: number | string (hex, starting with 0x), icon: number[ICON_WIDTH * ICON_HEIGHT], palette: number[] }`. The numbers in `icon` should correspond with an index in `palette`.
  - You can use the `bmp_to_json.py` script to convert a indexed bitmap file to compatible json
- Get reminders: Post any message to the `/get_reminders` topic. Response will be in the `/get_reminders/response` topic.
- Remove a reminder: Post a single integer, the index of the reminder to remove, to `/remove_reminder`.
