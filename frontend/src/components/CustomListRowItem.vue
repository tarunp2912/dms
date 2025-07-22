<template>
  <ListRowItem
    :column="column"
    :row="row"
    :item="item"
    :align="column.align"
  >
    <template
      v-if="column.key === 'title'"
      #prefix
    >
      <img
        v-if="!imgLoaded"
        loading="lazy"
        class="h-[16px] w-[16px]"
        :src="backupLink"
        :draggable="false"
      />
      <img
        v-show="imgLoaded"
        class="h-[16px] w-[16px] object-cover"
        :src="src"
        :draggable="false"
        @error="src = backupLink"
        @load="imgLoaded = true"
      />
    </template>
    <template #default="{ label }">
      <transition
        v-if="column.key === 'title'"
        name="fade-in"
        mode="out-in"
      >
        <div
          :key="label"
          class="truncate text-base"
        >
          {{ column?.getLabel ? column.getLabel({ row }) : label }}
        </div>
      </transition>
      <div
        v-else
        :key="label"
        class="truncate text-base"
      >
        {{ column?.getLabel ? column.getLabel({ row }) : label }}
      </div>

      <template v-if="column.key === 'options'">
        <div
          style="
            display: flex;
            justify-content: flex-end;
            align-items: center;
            width: 100%;
          "
        >
          <Button
            class="!bg-inherit"
            @click="(e) => contextMenu(e, row)"
          >
            <LucideMoreHorizontal class="size-4" />
          </Button>
          <button
            v-if="row.ocr"
            class="ml-1 px-1.5 py-0.5 text-[11px] rounded bg-blue-500 text-white hover:bg-blue-600 min-w-[40px]"
            @click.stop="onView(row)"
            style="margin-left: auto"
          >
            View
          </button>
          <button
            v-if="row.ocr"
            type="button"
            class="ml-1 px-1.5 py-0.5 text-[11px] rounded bg-green-500 text-white hover:bg-green-600 min-w-[55px]"
            @click.stop.prevent="onSummary(row)"
            style="margin-left: 2px"
          >
            Summary
          </button>
        </div>
      </template>
    </template>
    <template
      v-if="idx === 0"
      #suffix
    >
      <div class="flex flex-row grow justify-end gap-2 w-[20px]">
        <LucideStar
          v-if="row.is_favourite && $route.name !== 'Favourites'"
          name="star"
          width="16"
          height="16"
          class="my-auto stroke-amber-500 fill-amber-500"
        />
        <Tooltip
          v-else-if="
            row.is_private &&
            !['Home', 'Shared'].includes($store.state.breadcrumbs[0].name)
          "
          text="This is from your Home."
        >
          <LucideEyeOff
            width="16"
            height="16"
            class="my-auto"
          />
        </Tooltip>
      </div>
    </template>
  </ListRowItem>
  <div
    v-if="showSummary"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-30 summary-overlay"
  >
    <div
      class="relative bg-white rounded-2xl shadow-2xl p-8 max-w-lg w-full mx-4 animate-fade-in max-h-[80vh] flex flex-col summary-card"
      @dblclick.stop
    >
      <button
        @click="closeSummary"
        class="absolute top-4 right-4 text-gray-400 hover:text-gray-700 text-2xl font-bold focus:outline-none z-10"
      >
        ×
      </button>
      <h2 class="text-2xl font-bold mb-4 text-center">Summary</h2>
      <div
        class="overflow-y-auto flex-1 pr-2"
        style="max-height: 60vh"
      >
        <pre
          class="summary-pre whitespace-pre-wrap text-gray-800 text-base leading-relaxed font-sans"
          >{{ summaryText }}</pre
        >
      </div>
    </div>
  </div>
</template>
<script setup>
import { ListRowItem, Tooltip } from "frappe-ui"
import { ref, onUnmounted } from "vue"

const props = defineProps({
  idx: Number,
  column: Object,
  row: Object,
  item: String,
  contextMenu: Function,
})

let src, imgLoaded, thumbnailLink, backupLink, is_image

if (props.column.prefix && props.column.key === "title") {
  ;[thumbnailLink, backupLink, is_image] = props.column.prefix({
    row: props.row,
  })

  src = ref(thumbnailLink || backupLink)
  imgLoaded = ref(false)
}

console.log("CustomListRowItem row.title:", props.row.title, "row:", props.row)

function onView(file) {
  window.open(file.file_url, "_blank")
}

const showSummary = ref(false)
const summaryText = ref("")

function closeSummary() {
  showSummary.value = false
  summaryText.value = ""
}

async function onSummary(file) {
  try {
    const res = await fetch(
      `/api/method/dms.api.ocr.get_result?name=${file.name}`
    )
    const data = await res.json()
    summaryText.value = data.message?.text || "No summary found."
    showSummary.value = true
    document.body.style.overflow = "hidden"
  } catch (e) {
    summaryText.value = "Failed to fetch summary"
    showSummary.value = true
    document.body.style.overflow = "hidden"
  }
}

onUnmounted(() => {
  document.body.style.overflow = ""
})
</script>

<style scoped>
@keyframes fade-in {
  from {
    opacity: 0;
    transform: scale(0.98);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
.animate-fade-in {
  animation: fade-in 0.2s ease;
}
.summary-pre {
  user-select: text !important;
  -webkit-user-select: text !important;
  -moz-user-select: text !important;
  -ms-user-select: text !important;
  cursor: text;
}
.summary-overlay {
  user-select: none;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
}

.summary-card {
  user-select: text;
  -webkit-user-select: text;
  -moz-user-select: text;
  -ms-user-select: text;
}
</style>
