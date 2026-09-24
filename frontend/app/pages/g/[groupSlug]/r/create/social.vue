<template>
  <v-form ref="form" @submit.prevent="createRecipe">
    <v-card-title class="headline">
      {{ $t("recipe.scrape-social-recipe") }}
    </v-card-title>
    <v-card-text>
      <p>{{ $t("recipe.scrape-social-recipe-description") }}</p>
      <v-text-field
        v-model="recipeUrl"
        :label="$t('new-recipe.recipe-url')"
        :prepend-inner-icon="$globals.icons.link"
        :rules="[validators.url]"
        validate-on="blur"
        autofocus
        clearable
        variant="solo-filled"
        class="rounded-lg mt-2"
        rounded
      />
    </v-card-text>
    <v-checkbox
      v-model="importKeywordsAsTags"
      color="primary"
      hide-details
      :label="$t('recipe.import-original-keywords-as-tags')"
    />
    <v-checkbox
      v-model="stayInEditMode"
      color="primary"
      hide-details
      :label="$t('recipe.stay-in-edit-mode')"
    />
    <v-checkbox
      v-model="parseRecipe"
      color="primary"
      hide-details
      :label="$t('recipe.parse-recipe-ingredients-after-import')"
    />
    <v-card-actions class="justify-center">
      <div class="text-center w-100">
        <BaseButton
          :disabled="!recipeUrl"
          :loading="loading"
          rounded
          type="submit"
        />
        <v-card-text class="py-2">
          {{ status }}&nbsp;
        </v-card-text>
      </div>
    </v-card-actions>
    <v-alert v-if="error" color="error" class="mt-6 white--text">
      {{ error }}
    </v-alert>
  </v-form>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api";
import { useNewRecipeOptions } from "~/composables/use-new-recipe-options";
import { validators } from "~/composables/use-validators";
import type { VForm } from "~/types/auto-forms";

definePageMeta({ key: route => route.path });

const api = useUserApi();
const auth = useMealieAuth();
const route = useRoute();
const router = useRouter();
const groupSlug = computed(() => route.params.groupSlug as string || auth.user.value?.groupSlug || "");
const { importKeywordsAsTags, stayInEditMode, parseRecipe, navigateToRecipe } = useNewRecipeOptions();
const form = ref<VForm | null>(null);
const loading = ref(false);
const status = ref<string | null>(null);
const error = ref("");

function extractUrl(value: unknown) {
  const match = typeof value === "string" ? value.match(/https?:\/\/[^\s]+/) : null;
  return match?.[0] ?? null;
}

const recipeUrl = computed({
  get: () => extractUrl(route.query.recipe_import_url) ?? extractUrl(route.query.recipe_import_text),
  set: (value: string | null) => router.replace({ query: { ...route.query, recipe_import_url: value?.trim() || undefined } }),
});

async function createRecipe() {
  if (!recipeUrl.value || !form.value) return;
  const { valid } = await form.value.validate();
  if (!valid) return;
  loading.value = true;
  error.value = "";
  const result = await api.recipes.createOneBySocialUrl(
    recipeUrl.value,
    importKeywordsAsTags.value,
    false,
    message => status.value = message,
  );
  loading.value = false;
  status.value = null;
  if (!result.response || result.response.status !== 201 || !result.data) {
    error.value = result.error?.message || "Recipe creation failed";
    return;
  }
  navigateToRecipe(result.data, groupSlug.value, `/g/${groupSlug.value}/r/create/social`);
}
</script>
