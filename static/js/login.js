document.addEventListener("DOMContentLoaded", () => {
  // --- 1. GESTION DE L'AFFICHAGE DU MOT DE PASSE ---
  const toggleIcons = document.querySelectorAll(".toggle-password-icon");
  
  const icons = {
    show: `<svg width="20px" height="20px" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2 12C2 12 5 5 12 5C19 5 22 12 22 12C22 12 19 19 12 19C5 19 2 12 2 12Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    hide: `<svg width="20px" height="20px" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2 12C2 12 5 5 12 5C19 5 22 12 22 12C22 12 19 19 12 19C5 19 2 12 2 12Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><line x1="3" y1="3" x2="21" y2="21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`
  };

  toggleIcons.forEach(icon => {
    icon.addEventListener("click", function() {
      const input = this.previousElementSibling;
      if (input && input.tagName === 'INPUT') {
        const isVisible = input.type === "text";
        input.type = isVisible ? "password" : "text";
        this.innerHTML = isVisible ? icons.show : icons.hide;
        
        // Garde le focus et place le curseur à la fin
        input.focus();
        const valLen = input.value.length;
        input.setSelectionRange(valLen, valLen);
      }
    });
  });

  // --- 2. VALIDATION FORMULAIRE (INSCRIPTION) ---
  const regForm = document.getElementById("registerForm");
  if (regForm) {
    regForm.addEventListener("submit", (e) => {
      const mdp = document.getElementById("mdp_input");
      const check = document.getElementById("conditions_input");
      
      if (check && !check.checked) {
        e.preventDefault();
        check.closest('.checkbox-container').classList.add("shake");
        setTimeout(() => check.closest('.checkbox-container').classList.remove("shake"), 300);
      }
      
      if (mdp && mdp.value.length < 8) {
        e.preventDefault();
        alert("Minimum 8 caractères pour le mot de passe.");
        mdp.style.border = "1px solid #d32f2f";
      }
    });
  }
});

// Fonctions de transition globale
function showSection(id) {
  document.querySelectorAll(".sections").forEach(s => {
    s.classList.add("hidden");
    s.classList.remove("fade-in");
  });
  const target = document.getElementById(id);
  if (target) {
    target.classList.remove("hidden");
    setTimeout(() => target.classList.add("fade-in"), 10);
  }
}
function showRegister() { showSection("register-section"); }
function showLogin() { showSection("login-section"); }
function showForget() { showSection("forget-section"); }
