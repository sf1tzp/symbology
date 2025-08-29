# todo:

# Developer experience

# UI experience

- ✅ document urls use full shas currently, short would be nicer
- ✅ Expand homepage content and add disclaimer


# API integration

- Fixed using the wrong fetch by adding fetchFn parameter to all API functions
- Unified API interface with configurable strategy:
  - `VITE_API_STRATEGY=direct` - Client calls API directly (default)
  - `VITE_API_STRATEGY=proxy` - SvelteKit server proxies to API
  - Can be toggled via environment variable for A/B testing
  - Performance tracking included for both strategies

# Build and Deploy

- ✅ update container build for sveletkit

- Test build(s) in staging
  - Update k6 tests for our new urls
  - Update k6 to test a wide variety of content

- Host networking for real ip addresses in nginx logs

