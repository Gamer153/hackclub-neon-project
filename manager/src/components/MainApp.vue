<template>
  <v-card max-width="600px" v-if="!connected" class="pa-4">
    <v-card-title>Connect to MQTT Broker</v-card-title>
    <v-card-text>
      Attention: only MQTT over WebSocket is supported.
    </v-card-text>
    <v-container>
      <v-row>
        <v-col cols="8" sm="10">
          <v-text-field label="MQTT Broker URL" v-model="broker.url">
          </v-text-field>
        </v-col>
        <v-col cols="4" sm="2">
          <v-text-field label="Port" v-model="broker.port">
          </v-text-field>
        </v-col>
        <v-col cols="12" sm="4">
          <v-text-field label="Client-ID" v-model="broker.clientId">
          </v-text-field>
        </v-col>
        <v-col cols="12" sm="4">
          <v-text-field label="Username" v-model="broker.user">
          </v-text-field>
        </v-col>
        <v-col cols="12" sm="4">
          <v-text-field label="Password" v-model="broker.pass" type="password">
          </v-text-field>
        </v-col>
        <v-col cols="6">
          <v-checkbox-btn label="Use TLS (WSS)" v-model="broker.tls"></v-checkbox-btn>
        </v-col>
        <v-col cols="6">
          <v-text-field label="Path (optional)" v-model="broker.path"></v-text-field>
        </v-col>
      </v-row>
    </v-container>
    <v-card-actions>
      <v-btn variant="tonal" @click="handleConnection">Connect</v-btn>
    </v-card-actions>
    <p class="pa-4" style="color: red;" v-if="connectionError != ''">Error when connecting: {{ connectionError }}</p>
    <v-progress-linear indeterminate v-if="connecting"></v-progress-linear>
  </v-card>

  <v-card v-if="connected" style="max-width: fit-content;" class="pa-4">
    <v-card-title>Management Panel</v-card-title>
    <v-container>
      <v-row>
        <v-col>
          <v-btn @click="handleDisconnect" variant="outlined">Disconnect</v-btn>
        </v-col>
        <v-col cols="12" v-if="waitingForReminders">
          <v-progress-circular indeterminate></v-progress-circular>
          Waiting for current reminders...
        </v-col>
      </v-row>
      <v-row>
        <v-card class="ma-2 pa-2" elevation="4">
          <v-card-title>Current reminders</v-card-title>
          <v-col v-for="(reminder, index) in reminders" :key="index">
            <Reminder :reminder="reminder" :flipped="index % 2 == 1" @delete="removeReminder(index)"></Reminder>
          </v-col>
          <v-card-actions>
            <v-btn @click="requestReminders" v-if="!waitingForReminders">Reload</v-btn>
          </v-card-actions>
        </v-card>
      </v-row>
      <v-row>
        <v-card class="ma-2 pa-2" elevation="3">
          <v-card-title>Add reminder</v-card-title>
          <v-container style="min-width: 300px;">
            <v-row>
              <v-col cols="12">
                <v-text-field label="Text" v-model="reminderInput.text"></v-text-field>
              </v-col>
              <v-col cols="12">
                <v-color-picker mode="rgb" :modes="['hex', 'rgb']" v-model="reminderInput.color"></v-color-picker>
              </v-col>
              <v-col cols="3">
                <canvas height="140" width="140" ref="drawingCanvas" @mousedown="drawingCanvasMouseDown"></canvas>
              </v-col>
              <v-col cols="4">
                <v-color-picker mode="rgb" :modes="['hex', 'rgb']" v-model="colorPickerCol"></v-color-picker>
              </v-col>
            </v-row>
          </v-container>
          <v-card-actions>
            <v-btn @click="sendNewReminder" variant="outlined">Send</v-btn>
          </v-card-actions>
        </v-card>
      </v-row>
    </v-container>
  </v-card>
</template>

<script lang="ts" setup>

import mqtt from 'mqtt';
import type { MqttClient } from "mqtt";
import { onMounted, ref, useTemplateRef, watchEffect } from 'vue';
import type { ReminderType } from './Reminder.vue';
import Reminder from './Reminder.vue';

const connected = ref(false);
const connecting = ref(false);
const broker = ref({ url: "", port: "", user: "", pass: "", tls: true, path: "", clientId: `mqttjs_${Math.random().toString(16).slice(2, 8)}` });
const connectionError = ref("");

const mqttClient = ref(null as MqttClient | null);

const testrm = { text: "hello", color: 0xFFFFFF, "icon": [0, 0, 0, 0, 0, 0, 0, 0, 0, 17, 0, 18, 0, 0, 0, 0, 0, 18, 0, 0, 0, 0, 0, 18, 0, 17, 0, 0, 0, 18, 0, 0, 0, 17, 0, 18, 0, 0, 0, 0, 0, 17, 19, 19, 19, 19, 19, 18, 18], "palette": [0, 2236468, 4532284, 6699313, 9393723, 14643494, 14262374, 15647642, 16511542, 10085712, 6995504, 3642478, 4942127, 5393188, 3292217, 4145012, 3170434, 5992161, 6527999, 6278628] };

const waitingForReminders = ref(false);
const reminders = ref([] as ReminderType[]);
const colorPickerCol = ref("#000000");


const savedBrokerData = window.localStorage.getItem("conn_details_saved");
if (savedBrokerData) {
  broker.value = JSON.parse(savedBrokerData);
}

async function handleConnection() {
  if (connecting.value) return;
  const br = broker.value;

  connecting.value = true;
  connectionError.value = "";
  try {
    mqttClient.value = await mqtt.connectAsync(`ws${br.tls ? "s" : ""}://${br.url}:${br.port}${br.path ? br.path : ""}`, {
      username: br.user != "" ? br.user : undefined,
      password: br.pass != "" ? br.pass : undefined,
      connectTimeout: 10000,
      clientId: br.clientId,
      clean: true,
    });
    mqttClient.value.on("error", (err) => {
      connectionError.value = `${err.message}`;
      connecting.value = false;
    })
  } catch (e) {
    connecting.value = false;
    connectionError.value = `${e}`;
    return;
  }

  window.localStorage.setItem("conn_details_saved", JSON.stringify(br))

  connecting.value = false;
  connected.value = true;

  mqttClient.value!.subscribe("/get_reminders/response")
  mqttClient.value!.on("message", (topic, payload) => {
    if (topic == "/get_reminders/response") {
      const msg = payload.toString("utf-8").split("\n");
      if (msg.length > 1 || (msg.length == 1 && msg[0].startsWith("{"))) {
        try {
          reminders.value = msg.map((line) => JSON.parse(line));
        } catch {}
      }
      waitingForReminders.value = false;
    }
  })

  requestReminders();
}

async function requestReminders() {
  reminders.value = [];
  waitingForReminders.value = true;
  await mqttClient.value?.publishAsync("/get_reminders", "get");
}

function handleDisconnect() {
  mqttClient.value!.end();
  connected.value = false;
}

const CANVAS_SCALE = 20;
function drawingCanvasMouseDown(evt: MouseEvent) {
  const context = drawingCanvas.value!.getContext("2d");
  const x = Math.floor(evt.offsetX / CANVAS_SCALE) * CANVAS_SCALE;
  const y = Math.floor(evt.offsetY / CANVAS_SCALE) * CANVAS_SCALE;
  context!.fillStyle = colorPickerCol.value;
  context!.fillRect(x, y, CANVAS_SCALE, CANVAS_SCALE);
}

const reminderInput = ref({ text: "", color: "#FFFFFF" });

function sendNewReminder() {
  const reminder = { text: reminderInput.value.text, color: Number.parseInt(`${reminderInput.value.color.substring(1)}`, 16), icon: [] as number[], palette: [] as number[] };
  const context = drawingCanvas.value?.getContext("2d");
  for (let x = 0; x < (context!.canvas.width / CANVAS_SCALE); x++) {
    for (let y = 0; y < (context!.canvas.height / CANVAS_SCALE); y++) {
      const pixel = context!.getImageData(x * CANVAS_SCALE, y * CANVAS_SCALE, 1, 1).data;
      const rgb = (pixel[0] << 16) | (pixel[1] << 8) | pixel[2];
      let colIndex = reminder.palette.indexOf(rgb);
      if (colIndex == -1) {
        reminder.palette.push(rgb);
        colIndex = reminder.palette.length - 1;
      }
      reminder.icon.push(colIndex);
    }
  }
  console.log(reminder)

  mqttClient.value!.publish("/add_reminder", JSON.stringify(reminder));
  reminders.value.push(reminder);
}

function removeReminder(index: number) {
  mqttClient.value?.publish('/remove_reminder', `${index}`);
  reminders.value = reminders.value.filter((_, i) => i != index);
}

const drawingCanvas = useTemplateRef("drawingCanvas");
watchEffect(() => {
  if (drawingCanvas.value) {
    const context = drawingCanvas.value.getContext("2d");
    context!.fillRect(0, 0, drawingCanvas.value.width, drawingCanvas.value.height);
  }
});

</script>
