<template>
  <v-form>
    <v-card max-width="600px" v-if="!connected">
      <v-card-title>Connect to MQTT Broker</v-card-title>
      <v-container>
        <v-row>
          <v-col cols="6">
            <v-text-field label="MQTT Broker URL">
            </v-text-field>
          </v-col>
          <v-col cols="6">
            <v-text-field label="MQTT Websocket Port">
            </v-text-field>
          </v-col>
          <v-col cols="6">
            <v-text-field label="Username">
            </v-text-field>
          </v-col>
          <v-col cols="6">
            <v-text-field label="Password">
            </v-text-field>
          </v-col>
        </v-row>
      </v-container>
      <v-card-actions>
        <v-btn variant="tonal" @click="handleConnection">Connect</v-btn>
      </v-card-actions>
    </v-card>
  </v-form>
</template>

<script lang="ts" setup>
import { ref } from 'vue';

  const connected = ref(false);

  function handleConnection() {
    connected.value = true;
  }
</script>
