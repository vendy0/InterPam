
// Écouter l'événement "push" envoyé par ton script Python
self.addEventListener('push', function(event) {
    if (event.data) {
        // On récupère les données envoyées par pywebpush
        const data = event.data.json(); 

        const options = {
            body: data.body,
            icon: '/static/icon-192.png', // Chemin vers ton icône
            badge: '/static/icon-192.png',
            vibrate: [100, 50, 100],
            data: {
                url: data.url // On stocke l'URL pour ouvrir la page au clic
            }
        };

        // Afficher la notification sur l'écran
        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

// Gérer le clic sur la notification
self.addEventListener('notificationclick', function(event) {
    event.notification.close(); // Fermer la petite fenêtre de notif
    
    // Ouvrir le site InterPam (par exemple la page des matchs)
    event.waitUntil(
        clients.openWindow(event.notification.data.url)
    );
});
