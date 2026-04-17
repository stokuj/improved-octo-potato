<script>
    import ItemTable from '$lib/components/ItemTable.svelte';
</script>

<ItemTable apiEndpoint="/user-items/me" requireAuth={true} showOnlySaved={true} />
