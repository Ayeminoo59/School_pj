/* ==========================================================================
   SCOPE — front-end enhancements
   (mobile navigation, confirm dialogs, flash auto-dismiss, module picker)
   ========================================================================== */
document.addEventListener("DOMContentLoaded", function () {
  /* --- Mobile navigation toggle ------------------------------------------ */
  var toggle = document.querySelector(".nav-toggle");
  var links = document.getElementById("navLinks");

  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  /* --- Confirmation dialogs ---------------------------------------------- */
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.getAttribute("data-confirm"))) {
        event.preventDefault();
      }
    });
  });

  /* --- Flash messages: close button + auto dismiss ------------------------ */
  document.querySelectorAll(".alert").forEach(function (alertEl) {
    var closeBtn = alertEl.querySelector(".alert-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        alertEl.remove();
      });
    }
    setTimeout(function () {
      alertEl.classList.add("alert-hide");
      setTimeout(function () {
        alertEl.remove();
      }, 350);
    }, 6000);
  });

  /* --- Module selection counter ------------------------------------------- */
  var counter = document.getElementById("selectedCount");
  var moduleBoxes = document.querySelectorAll('.module-card input[type="checkbox"]');

  if (counter && moduleBoxes.length > 0) {
    var updateCounter = function () {
      var selected = 0;
      moduleBoxes.forEach(function (box) {
        if (box.checked) selected += 1;
      });
      counter.textContent = selected;
    };

    moduleBoxes.forEach(function (box) {
      box.addEventListener("change", function () {
        var card = box.closest(".module-card");
        if (card) card.classList.toggle("selected", box.checked);
        updateCounter();
      });
    });

    updateCounter();
  }
});
