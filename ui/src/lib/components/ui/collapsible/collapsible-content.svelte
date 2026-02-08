<script lang="ts">
	import { Collapsible as CollapsiblePrimitive } from 'bits-ui';

	let {
		ref = $bindable(null),
		children,
		...restProps
	}: CollapsiblePrimitive.ContentProps = $props();
</script>

<CollapsiblePrimitive.Content bind:ref {...restProps}>
	{@render children?.()}
</CollapsiblePrimitive.Content>
