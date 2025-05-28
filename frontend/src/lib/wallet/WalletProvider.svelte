<!-- WalletProvider.svelte -->
<script>
  import { WagmiProvider } from 'wagmi';
  import { config } from './connector';
</script>

<WagmiProvider config={config}>
  <slot />
</WagmiProvider>