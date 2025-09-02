// MW Design Studio - Service Worker
// Version 1.0.0

const CACHE_NAME = 'mw-intake-v1.0.0';
const OFFLINE_URL = '/offline';

// Assets to cache for offline functionality
const STATIC_CACHE_URLS = [
  '/',
  '/static/manifest.json',
  '/static/mw_logo.png',
  '/static/style.css',
  // Add other critical assets
];

// Dynamic cache for form data when offline
const FORM_CACHE_NAME = 'mw-forms-cache';

// Install event - cache critical resources
self.addEventListener('install', event => {
  console.log('MW Service Worker: Installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('MW Service Worker: Caching static assets');
        return cache.addAll(STATIC_CACHE_URLS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean old caches
self.addEventListener('activate', event => {
  console.log('MW Service Worker: Activating...');
  
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME && cacheName !== FORM_CACHE_NAME) {
            console.log('MW Service Worker: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - handle network requests
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Handle form submissions when offline
  if (request.method === 'POST' && url.pathname === '/submit_form') {
    event.respondWith(handleFormSubmission(request));
    return;
  }

  // Handle GET requests
  if (request.method === 'GET') {
    event.respondWith(handleGetRequest(request));
    return;
  }
});

// Handle form submission (cache when offline, sync when online)
async function handleFormSubmission(request) {
  try {
    // Try to submit immediately
    const response = await fetch(request.clone());
    
    if (response.ok) {
      return response;
    } else {
      throw new Error('Network response was not ok');
    }
  } catch (error) {
    console.log('MW Service Worker: Form submission failed, caching for later');
    
    // Cache form data for background sync
    const formData = await request.formData();
    const cachedSubmission = {
      url: request.url,
      data: Object.fromEntries(formData),
      timestamp: Date.now(),
      method: request.method
    };

    // Store in IndexedDB or cache for background sync
    await cacheFormSubmission(cachedSubmission);

    // Return offline response
    return new Response(
      JSON.stringify({
        message: 'Form saved offline. Will submit when connection is restored.',
        offline: true
      }),
      {
        status: 202,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Handle GET requests with cache-first strategy
async function handleGetRequest(request) {
  try {
    // Try network first for dynamic content
    if (request.url.includes('/admin') || request.url.includes('/api')) {
      const response = await fetch(request);
      return response;
    }

    // Cache-first for static assets
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // Fallback to network
    const response = await fetch(request);
    
    // Cache successful responses
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    
    return response;
    
  } catch (error) {
    console.log('MW Service Worker: Network failed, trying cache');
    
    // Return cached version or offline page
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      const offlineResponse = await caches.match(OFFLINE_URL);
      if (offlineResponse) {
        return offlineResponse;
      }
      
      // Fallback offline HTML
      return new Response(
        `<!DOCTYPE html>
        <html>
        <head>
          <title>MW Design Studio - Offline</title>
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .offline-message { background: #1E3A8A; color: white; padding: 20px; border-radius: 10px; }
          </style>
        </head>
        <body>
          <div class="offline-message">
            <h1>MW Design Studio</h1>
            <p>You are currently offline. Please check your connection and try again.</p>
            <button onclick="window.location.reload()">Try Again</button>
          </div>
        </body>
        </html>`,
        {
          headers: { 'Content-Type': 'text/html' }
        }
      );
    }

    return new Response('Offline', { status: 503 });
  }
}

// Cache form submission for background sync
async function cacheFormSubmission(submission) {
  try {
    const cache = await caches.open(FORM_CACHE_NAME);
    const cacheKey = `form-${submission.timestamp}`;
    
    await cache.put(
      new Request(cacheKey),
      new Response(JSON.stringify(submission))
    );
    
    console.log('MW Service Worker: Form cached for background sync');
    
    // Register background sync if available
    if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
      const registration = await navigator.serviceWorker.ready;
      await registration.sync.register('form-sync');
    }
  } catch (error) {
    console.error('MW Service Worker: Failed to cache form', error);
  }
}

// Background sync event
self.addEventListener('sync', event => {
  if (event.tag === 'form-sync') {
    event.waitUntil(syncCachedForms());
  }
});

// Sync cached forms when online
async function syncCachedForms() {
  try {
    const cache = await caches.open(FORM_CACHE_NAME);
    const requests = await cache.keys();
    
    for (const request of requests) {
      const response = await cache.match(request);
      const submissionData = await response.json();
      
      try {
        // Reconstruct form data
        const formData = new FormData();
        Object.entries(submissionData.data).forEach(([key, value]) => {
          if (Array.isArray(value)) {
            value.forEach(v => formData.append(key, v));
          } else {
            formData.append(key, value);
          }
        });

        // Submit the form
        const submitResponse = await fetch('/submit_form', {
          method: 'POST',
          body: formData
        });

        if (submitResponse.ok) {
          console.log('MW Service Worker: Cached form submitted successfully');
          await cache.delete(request);
          
          // Show notification to user
          self.registration.showNotification('MW Design Studio', {
            body: 'Your form submission has been completed!',
            icon: '/static/mw_logo.png',
            badge: '/static/mw_logo.png'
          });
        }
      } catch (error) {
        console.error('MW Service Worker: Failed to sync form', error);
      }
    }
  } catch (error) {
    console.error('MW Service Worker: Background sync failed', error);
  }
}

// Push notification handling (for future implementation)
self.addEventListener('push', event => {
  if (!event.data) return;

  const options = {
    body: event.data.text(),
    icon: '/static/mw_logo.png',
    badge: '/static/mw_logo.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    }
  };

  event.waitUntil(
    self.registration.showNotification('MW Design Studio', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  event.waitUntil(
    clients.openWindow('/')
  );
});