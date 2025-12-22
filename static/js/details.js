// 1. On déclare la fonction de calcul en dehors pour qu'elle soit globale
function calculerGain() {
    const miseInput = document.getElementById('mise-input');
    const displayGain = document.getElementById('display-gain');
    
    // Si les éléments n'existent pas sur la page, on arrête
    if (!miseInput || !displayGain) return;

    const mise = parseFloat(miseInput.value) || 0;
    let coteTotale = 1.0;
    let uneOptionSelectionnee = false;

    // On récupère tous les boutons radio cochés
    const selectedRadios = document.querySelectorAll('.radio-input:checked');
    
    selectedRadios.forEach(radio => {
        // On cherche le label associé pour trouver la cote
        const label = radio.nextElementSibling;
        if (label) {
            const coteText = label.querySelector('.label-cote').innerText;
            const cote = parseFloat(coteText);
            
            if (!isNaN(cote)) {
                coteTotale *= cote;
                uneOptionSelectionnee = true;
            }
        }
    });

    // Calcul final
    const resultat = uneOptionSelectionnee ? (mise * coteTotale) : 0;
    displayGain.innerText = resultat.toFixed(2);
}

// 2. Gestion du clic et du décochage
document.querySelectorAll('input[type="radio"]').forEach(radio => {
    radio.addEventListener('click', (e) => {
        if (radio.dataset.wasChecked === 'true') {
            radio.checked = false;
            radio.dataset.wasChecked = 'false';
            // Appel immédiat après décochage
            calculerGain(); 
        } else {
            const name = radio.name;
            document.querySelectorAll(`input[name="${name}"]`).forEach(r => {
                r.dataset.wasChecked = 'false';
            });
            radio.dataset.wasChecked = 'true';
            // Appel immédiat après cochage
            calculerGain();
        }
    });
});

// 3. Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    const miseInput = document.getElementById('mise-input');
    
    if (miseInput) {
        // Recalcule quand on tape un chiffre
        miseInput.addEventListener('input', calculerGain);
    }
});

// 4. Fenêtre de confirmation avant envoi
function confirmerMonPari() {
    const mise = document.getElementById('mise-input').value;
    const gain = document.getElementById('display-gain').innerText;
    const selectedOptions = document.querySelectorAll('.radio-input:checked');

    if (selectedOptions.length === 0) {
        alert("Veuillez choisir au moins une option avant de parier.");
        return false;
    }

    const message = `Confirmation de votre pari :\n\n` +
                    `- Mise : ${mise} HTG\n` +
                    `- Gain potentiel : ${gain} HTG\n\n` +
                    `Voulez-vous valider cette fiche ?`;

    return confirm(message);
}
