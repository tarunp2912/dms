<template>
  <div
    class="h-[65%] flex items-center justify-center rounded-t-[calc(theme(borderRadius.lg)-1px)] overflow-hidden"
  >
    <template v-if="is_image || !getThumbnail?.data">
      <img
        v-show="!imgLoaded"
        loading="lazy"
        :class="'h-10 w-auto'"
        :src="backupLink"
        :draggable="false"
      />
      <img
        v-show="imgLoaded"
        :class="
          src === backupLink
            ? 'h-10 w-auto'
            : 'h-full min-w-full object-cover rounded-t-[calc(theme(borderRadius.lg)-1px)]'
        "
        :src="src"
        :draggable="false"
        @error="src = backupLink"
        @load="imgLoaded = true"
      />
    </template>
    <!-- Direct padding doesn't work -->
    <div
      v-else
      class="overflow-hidden text-ellipsis whitespace-nowrap h-full w-[calc(100%-1rem)] object-cover rounded-t-[calc(theme(borderRadius.lg)-1px)] py-2"
    >
      <div
        class="prose prose-sm pointer-events-none scale-[.39] ml-0 origin-top-left"
        v-html="getThumbnail.data"
      />
    </div>
  </div>
  <div
    class="p-2 h-[35%] border-t border-gray-100 flex flex-col justify-evenly"
  >
    <div class="truncate w-full w-fit text-base font-medium text-ink-gray-8">
      {{ file.title }}
    </div>
    <div class="truncate w-full w-fit text-xs text-ink-gray-5">
      {{ file.name }}
    </div>
    <div class="mt-[5px] text-xs text-ink-gray-5">
      <div class="flex items-center justify-start gap-1">
        <img
          v-if="
            file.file_type !== 'Unknown' &&
            !file.is_group &&
            ((imgLoaded && src !== backupLink) || !is_image)
          "
          loading="lazy"
          class="h-4 w-auto"
          :src="getIconUrl(file.file_type) || '/dms'"
          :draggable="false"
        />
        <p class="truncate">
          {{ file.is_group ? childrenSentence + "∙" : "" }}
          {{ file.file_type !== "Unknown" ? file.file_type + "∙" : "" }}
          {{ file.relativeModified }}
        </p>
      </div>
      <!-- <p class="mt-1">
        {{ file.file_size_pretty }}
      </p> -->
    </div>
    <div
      class="mt-2 flex gap-1 items-center w-full"
      style="justify-content: flex-end"
    >
      <button
        v-if="file.ocr"
        class="px-1.5 py-0.5 text-[11px] rounded bg-blue-500 text-white hover:bg-blue-600 min-w-[40px]"
        @click.stop="onView(file)"
        style="margin-left: auto"
      >
        View
      </button>
      <button
        v-if="file.ocr"
        class="px-1.5 py-0.5 text-[11px] rounded bg-green-500 text-white hover:bg-green-600 min-w-[55px]"
        @click.stop="onSummary(file)"
        style="margin-left: 2px"
      >
        Summary
      </button>
    </div>
  </div>
</template>
<script setup>
import { getIconUrl, getThumbnailUrl } from "@/utils/getIconUrl"
import { createResource } from "frappe-ui"
import { ref, computed } from "vue"
const props = defineProps({ file: Object })

const [thumbnailLink, backupLink, is_image] = getThumbnailUrl(
  props.file.name,
  props.file.file_type
)
const src = ref(thumbnailLink || backupLink)
const imgLoaded = ref(false)

let getThumbnail
if (!is_image) {
  getThumbnail = createResource({
    url: thumbnailLink,
    cache: ["thumbnail", props.file.name],
    auto: true,
  })
}

const childrenSentence = computed(() => {
  if (!props.file.children) return "Empty"
  return props.file.children + " item" + (props.file.children === 1 ? "" : "s")
})

function onView(file) {
  window.open(file.file_url, "_blank")
}

async function onSummary(file) {
  try {
    const res = await fetch(
      `/api/method/dms.api.ocr.get_result?name=${file.name}`
    )
    const data = await res.json()
    alert(data.message?.text || "No summary found.")
  } catch (e) {
    alert("Failed to fetch summary")
  }
}
</script>
