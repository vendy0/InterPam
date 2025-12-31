// Ta vraie clé publique
const PUBLIC_VAPID_KEY = 'BKgkjvHjsgc-acZX0hqeFQWTOlNg0VMCNcMYy3uK-oA9wicuGf5J2HEvfTKjCJB4sTgaeh24XoT5LAqNk45fAzg';

document.addEventListener('DOMContentLoaded', () => {
    const pushBtn = document.getElementById('btn-push');

    // 1. Vérifier si le navigateur supporte les notifications
    if ('serviceWorker' in navigator && 'PushManager' in window) {
        // On affiche le bouton
        if(pushBtn) {
            pushBtn.style.display = 'block';
            
            pushBtn.addEventListener('click', async () => {
                confirmer = confirm("Voulez vous activer les notifications pour InterPam ?")
                if(confirmer){
                    try {
                        await activerNotifications();
                    } catch (error) {
                        console.error("Erreur d'abonnement :", error);
                    }
                }
            });
        }
    }
});

async function activerNotifications() {
    const pushBtn = document.getElementById('btn-push');

    // 2. Enregistrer le Service Worker
    const registration = await navigator.serviceWorker.register('/sw.js');
    console.log('Service Worker enregistré...');
    
    // 3. Demander la permission à l'utilisateur
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
        alert("Alertes par notifications désactivées.");
        return;
    }

    // 4. Créer l'abonnement
    const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(PUBLIC_VAPID_KEY)
    });

    // 5. Envoyer cet abonnement à ton serveur Python
    await fetch('/save-subscription', {
        method: 'POST',
        body: JSON.stringify(subscription),
        headers: { 'Content-Type': 'application/json' }
    });

    alert("✅ Notifications activées . Rendez vous dans les paramètres pour les désactiver.");
    if(pushBtn) {
        const container = document.querySelector(".subscription")
        pushBtn.disabled = true;
        container.style.bottom = 0
    }
}

// Fonction utilitaire indispensable
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}
