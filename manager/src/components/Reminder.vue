<template>
  <div class="pa-2" :style="{ backgroundColor: flipped ? '#3a3a3a' : ''}">
    <div style="display: flex; align-items: center;">
      <span v-if="!reminder.icon || reminder.icon.length > 0" style="display: flex; align-items: center;" class="pe-2">
        <canvas height="21" width="21" ref="canvas"></canvas>
      </span>
      <span class="pe-4" :style="{ color: rgbColor }" style="font-size: larger;">{{ reminder.text }}</span>
      <span style="height: 20px; width: 20px; border-radius: 3px;" :style="{ backgroundColor: rgbColor }">&emsp;&nbsp;</span>&nbsp;{{ rgbColor }}
      <span><v-btn class="ms-4 bg-red" density="comfortable" icon="mdi-delete" @click="$emit('delete')"></v-btn></span>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, useTemplateRef } from 'vue';

export interface ReminderType {
  text: string,
  color: number,
  icon: number[],
  palette: number[]
}

function toRGBString(color: number) {
  const r = (color >> 16) & 0xFF;
  const g = (color >> 8) & 0xFF;
  const b = color & 0xFF;
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`.toUpperCase();
}

const { reminder, flipped } = defineProps<{ reminder: ReminderType, flipped?: boolean }>();
const rgbColor = computed(() => toRGBString(reminder.color));
const canvas = useTemplateRef("canvas");

onMounted(() => {
  if (canvas.value) {
    let cx = 0, cy = 0;
    const ICON_HEIGHT = 7, ICON_WIDTH = 7;
    const SCALE = 3;
    canvas.value.width = SCALE * ICON_WIDTH;
    canvas.value.height = SCALE * ICON_HEIGHT;
    const context = canvas.value!.getContext("2d");
    reminder.icon?.forEach((px, i) => {
      if (context) {
        const x = (i % ICON_WIDTH) * SCALE;
        const y = Math.floor(i / ICON_WIDTH) * SCALE;
        context.fillStyle = toRGBString(reminder.palette[px]);
        context.fillRect(y, x, SCALE, SCALE);
      }
      cx++; cy++;
    });
  }
});
</script>
