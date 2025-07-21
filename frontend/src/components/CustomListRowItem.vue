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
            class="ml-1 px-1.5 py-0.5 text-[11px] rounded bg-green-500 text-white hover:bg-green-600 min-w-[55px]"
            @click.stop="onSummary(row)"
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
</template>
<script setup>
import { ListRowItem, Tooltip } from "frappe-ui"
import { ref } from "vue"

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
