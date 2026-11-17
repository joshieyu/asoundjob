<script lang="ts">
	import JobBoard from '$lib/components/JobBoard.svelte';

	let { data } = $props();
</script>

<JobBoard {data} />
