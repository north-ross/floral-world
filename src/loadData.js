// Helper function to retry loading the family-area-sr.json and add a more helpful message
import {html} from "npm:htl";

// Like a try/except loop with time.sleep (or the `tenacity` library) in Python
export async function loadWithRetry(load, {retries = 2, delay = 1000} = {}) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await load();
    } catch (error) {
      if (attempt >= retries) throw error;
      await new Promise((resolve) => setTimeout(resolve, delay * 2 ** attempt));
    }
  }
}

export function loadErrorMessage() {
  return html`<div class="card" style="border-left: 4px solid #662200;">
    <p><strong>Error loading data.</strong> Try reloading the page.</p>
    <button onclick=${() => location.reload()}>Reload</button>
  </div>`;
} 