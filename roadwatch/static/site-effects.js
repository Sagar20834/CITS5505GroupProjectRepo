(function () {
  "use strict";

  function revealImmediately(items) {
    items.forEach(function (item) {
      item.classList.add("is-visible");
    });
  }

  function bootReveal() {
    var items = Array.prototype.slice.call(document.querySelectorAll(".rw-reveal"));
    if (!items.length) return;

    items.forEach(function (item, index) {
      var groupIndex = index % 6;
      item.style.setProperty("--rw-reveal-delay", groupIndex * 70 + "ms");
    });

    var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced || !("IntersectionObserver" in window)) {
      revealImmediately(items);
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, {
      rootMargin: "0px 0px -8% 0px",
      threshold: 0.12,
    });

    items.forEach(function (item) {
      observer.observe(item);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootReveal);
  } else {
    bootReveal();
  }
})();
