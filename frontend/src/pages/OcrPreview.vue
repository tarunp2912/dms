<template>
  <div class="p-6 w-full h-[90vh] flex flex-col items-center">
    <h2 class="text-xl font-bold mb-4">OCR Preview: {{ fileName }}</h2>
    <div v-if="loading">Loading...</div>
    <div
      v-else
      class="w-full flex flex-col items-center"
    >
      <!-- Zoom Controls -->
      <div class="flex gap-2 mb-2">
        <button
          @click="zoomOut"
          class="px-2 py-1 bg-gray-200 rounded"
        >
          -
        </button>
        <span>Zoom: {{ (zoom * 100).toFixed(0) }}%</span>
        <button
          @click="zoomIn"
          class="px-2 py-1 bg-gray-200 rounded"
        >
          +
        </button>
      </div>
      <!-- Full-page Zoomable Container -->
      <div
        class="preview-scroll-container custom-scroll"
        style="
          width: 80vw;
          height: 80vh;
          overflow: auto;
          margin: 0 auto;
          background: #fff;
          border-radius: 8px;
          border: 1px solid #eee;
        "
      >
        <!-- PDF Preview -->
        <embed
          v-if="isPdf"
          :src="fileUrl"
          type="application/pdf"
          :width="pdfWidth"
          :height="pdfHeight"
          style="display: block"
        />
        <!-- Image Preview -->
        <img
          v-else-if="isImage"
          :src="fileUrl"
          alt="Original"
          :style="{
            width: imgWidth,
            height: imgHeight,
            display: 'block',
            margin: '0 auto',
          }"
        />
        <!-- Word Preview (link to open in Office Online) -->
        <div
          v-else-if="isWord"
          class="p-4"
        >
          <a
            :href="officeViewerUrl"
            target="_blank"
            rel="noopener"
            class="text-blue-600 underline"
          >
            Open Word Document in Office Online
          </a>
          <br />
          <a
            :href="fileUrl"
            download
            class="text-blue-600 underline mt-2 inline-block"
          >
            Download Word Document
          </a>
          <div class="text-red-600 mt-2">
            This file cannot be opened in Office Online because it is not
            publicly accessible. Please download and open it in Microsoft Word.
          </div>
        </div>
      </div>
      <!-- OCR Text -->
      <div class="bg-gray-100 p-4 rounded mt-4 w-full max-w-2xl">
        <pre class="whitespace-pre-wrap">{{ ocrText }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from "vue"
import { useRoute } from "vue-router"

const route = useRoute()
const fileName = route.params.entityName
const ocrText = ref("")
const fileUrl = ref("")
const loading = ref(true)
const zoom = ref(1)

onMounted(async () => {
  try {
    const res = await fetch(
      `/api/method/dms.api.ocr.get_result?name=${fileName}`
    )
    const data = await res.json()
    ocrText.value = data.message.text || ""
    fileUrl.value = data.message.image_url || ""
  } catch (e) {
    ocrText.value = "Failed to load OCR result."
  } finally {
    loading.value = false
  }
})

const isPdf = computed(() => fileUrl.value.toLowerCase().endsWith(".pdf"))
const isWord = computed(
  () =>
    fileUrl.value.toLowerCase().endsWith(".doc") ||
    fileUrl.value.toLowerCase().endsWith(".docx")
)
const isImage = computed(() =>
  /\.(png|jpe?g|gif|bmp|webp)$/i.test(fileUrl.value)
)

const officeViewerUrl = computed(
  () =>
    `https://view.officeapps.live.com/op/view.aspx?src=${encodeURIComponent(
      window.location.origin + fileUrl.value
    )}`
)

// Dynamically set width/height for zoom
const baseWidth = 900
const baseHeight = 1200
const pdfWidth = computed(() => `${baseWidth * zoom.value}px`)
const pdfHeight = computed(() => `${baseHeight * zoom.value}px`)
const imgWidth = computed(() => `${baseWidth * zoom.value}px`)
const imgHeight = computed(() => "auto")

function zoomIn() {
  zoom.value = Math.min(zoom.value + 0.1, 3)
}
function zoomOut() {
  zoom.value = Math.max(zoom.value - 0.1, 0.2)
}
</script>

<style scoped>
pre {
  font-family: inherit;
  font-size: 1rem;
}
.custom-scroll {
  scrollbar-width: thin;
  scrollbar-color: #888 #f1f1f1;
}
.custom-scroll::-webkit-scrollbar {
  width: 12px;
  height: 12px;
}
.custom-scroll::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 6px;
}
.custom-scroll::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 6px;
}
</style>
