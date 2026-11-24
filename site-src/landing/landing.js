// Types out the terminal transcript. Without JS, or with reduced motion,
// the full transcript in the HTML stays as it is.
(function () {
  "use strict";
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  var blocks = Array.prototype.slice.call(document.querySelectorAll(".term-block"));
  if (!blocks.length) return;

  var texts = blocks.map(function (b) { return b.textContent; });
  // Reserve exactly the content height: line count x line-height, so the
  // blocks never grow while typing and never leave a gap beyond the text.
  blocks.forEach(function (b, i) {
    var cs = window.getComputedStyle(b);
    var lh = parseFloat(cs.lineHeight);
    if (!(lh > 0)) lh = 1.5 * parseFloat(cs.fontSize);
    var lines = texts[i].replace(/\n+$/, "").split("\n").length;
    b.style.minHeight = (lines * lh + parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom)) + "px";
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
