# neon reminders
A reminders display on a RGB led board, controllable with MQTT.

MQTT commands:

- Add a reminder: Post a message in the format `reminder content|color as hex` (content and color split by `|`) to the `/add_reminder` topic. (e.g. `Go shopping|EA7317`)
- Get reminders: Post any message to the `/get_reminders` topic. Response will be in the `/get_reminders/response` topic.
- Remove a reminder: Post a single integer, the index of the reminder to remove, to `remove_reminder`.
