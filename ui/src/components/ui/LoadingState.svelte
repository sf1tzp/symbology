<script lang="ts">
  const { message = 'Loading...', size = 'normal' } = $props<{
    message?: string;
    size?: 'small' | 'normal' | 'large';
  }>();
</script>

<div class="loading-container">
  <div class="loading-spinner {size}"></div>
  <p class="loading-message">{message}</p>
</div>
