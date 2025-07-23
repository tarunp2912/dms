<template>
  <GenericPage
    :get-entities="{ ...ocrResource, data: filteredFiles }"
    :icon="ocrIcon"
    primary-message="No OCR files yet"
    secondary-message="Upload a file to get started."
    :action-items="ocrActions"
    :delete-ocr-files="deleteOcrFiles"
  />
  <div class="absolute top-2 right-4 z-10">
    <button
      @click="onUploadFileClick"
      class="bg-black hover:bg-gray-800 text-white w-7 h-7 flex items-center justify-center shadow-md rounded"
    >
      <LucidePlus class="w-3.5 h-3.5" />
    </button>
  </div>

  <input
    type="file"
    accept=".doc,.docx,.pdf,.png"
    ref="fileInput"
    @change="onFileChange"
    class="hidden"
  />
</template>

<script setup>
import GenericPage from "@/components/GenericPage.vue"
import { ref, computed, onMounted } from "vue"
import { LucideFileText, LucidePlus, LucideTrash } from "lucide-vue-next"
import dayjs from "dayjs"
import relativeTime from "dayjs/plugin/relativeTime"
dayjs.extend(relativeTime)

// OCR logic
const ocrFiles = ref([])
const search = ref("")
const sortOrder = ref("desc")
const view = ref("grid")
const uploading = ref(false)
const fileInput = ref(null)
const dropdownOpen = ref(false)

const filteredFiles = computed(() => {
  let files = ocrFiles.value
  if (search.value) {
    files = files.filter((f) =>
      f.name.toLowerCase().includes(search.value.toLowerCase())
    )
  }
  files = files.slice().sort((a, b) => {
    if (sortOrder.value === "desc") {
      return new Date(b.modified) - new Date(a.modified)
    } else {
      return new Date(a.modified) - new Date(b.modified)
    }
  })
  return files
})

function toggleSort() {
  sortOrder.value = sortOrder.value === "desc" ? "asc" : "desc"
}

function onUploadFileClick() {
  fileInput.value.click()
}

function onFileChange(e) {
  const file = e.target.files[0]
  if (file) {
    uploadFile(file)
    fileInput.value.value = "" // reset input
  }
}

async function uploadFile(file) {
  uploading.value = true
  const formData = new FormData()
  formData.append("file", file)
  try {
    const response = await fetch("/api/method/dms.api.ocr.upload", {
      method: "POST",
      body: formData,
      headers: {
        "X-Frappe-CSRF-Token":
          window.csrf_token || (window.frappe && frappe.csrf_token),
      },
    })
    if (!response.ok) throw new Error("Upload failed")
    await fetchOcrFiles()
  } catch (err) {
    // handle error
  } finally {
    uploading.value = false
  }
}

async function fetchOcrFiles() {
  try {
    const response = await fetch("/api/method/dms.api.ocr.list")
    if (!response.ok) throw new Error("Failed to fetch OCR files")
    const data = await response.json()
    // Patch: set write: true and add required fields for all files
    ocrFiles.value = (data.message || []).map((f) => ({
      ...f,
      // This is the same as the Team page logic
      title: f.title || "Untitled",
      owner: f.owner || "Unknown",
      modified: f.modified || new Date().toISOString(),
      file_size_pretty: f.file_size_pretty || "—",
      share_count: f.share_count ?? 0,
      write: true,
      relativeModified: f.modified ? dayjs(f.modified).fromNow() : "-",
      ocr: true,
    }))
  } catch (err) {
    ocrFiles.value = []
  }
}

async function deleteOcrFiles(selectedFiles) {
  for (const file of selectedFiles) {
    await fetch("/api/method/dms.api.ocr.delete", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Frappe-CSRF-Token":
          window.csrf_token || (window.frappe && frappe.csrf_token),
      },
      body: JSON.stringify({ name: file.name }),
    })
  }
  await fetchOcrFiles()
}

onMounted(() => {
  document.title = "OCR"
  fetchOcrFiles()
})

// For GenericPage
const ocrResource = {
  get data() {
    return filteredFiles.value
  },
  fetch: fetchOcrFiles,
  fetched: true,
  error: null,
  setData: (data) => {
    ocrFiles.value = data
  },
}
const ocrIcon = LucideFileText

const ocrActions = [
  {
    label: "Upload File",
    icon: LucidePlus,
    action: onUploadFileClick,
  },
  {
    label: "Delete",
    icon: LucideTrash,
    action: (selected) => deleteOcrFiles(selected),
    multi: true,
    important: true,
    danger: true,
    isEnabled: () => true, // or add your own logic
  },
]
</script>
