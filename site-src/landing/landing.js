// Types out the terminal transcript. Without JS, or with reduced motion,
// the full transcript in the HTML stays as it is.
(function () {
  "use strict";
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  var blocks = Array.prototype.slice.call(document.querySelectorAll(".term-block"));
  if (!blocks.length) return;

  var texts = blocks.map(function (b) { return b.textContent; });
  blocks.forEach(function (b) {
    b.style.minHeight = b.offsetHeight + "px";
    b.textContent = "";
  });

  var CHAR_MS = 22, PAUSE_MS = 500;

  function type(i) {
    if (i >= blocks.length) return;
    var block = blocks[i], text = texts[i], n = 0;
    block.classList.add("is-typing");
    (function step() {
      n += 1;
      block.textContent = text.slice(0, n);
      if (n < text.length) {
        window.setTimeout(step, CHAR_MS);
      } else {
        block.classList.remove("is-typing");
        window.setTimeout(function () { type(i + 1); }, PAUSE_MS);
      }
    })();
  }
  type(0);
})();
